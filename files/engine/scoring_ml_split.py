"""
SmartOfferEngine — Split XGBoost Propensity Scoring Engine

Trains TWO separate XGBoost models:
  1. propensity_standard  — for standard/fuel/points-multiplier offers
  2. propensity_gr        — for Grocery Reward offers (points-focused features)

Each model:
  - Uses the same 19 features, but GR model emphasizes points_gap, points_expiring
  - Trains only on (household, offer) pairs matching its offer type
  - Predicts P(redemption | customer, offer) → scaled 0–100
  - Applies hard business rules (FreshPass, 4U+ filters)

Writes to c360_scored_offers with model_type='propensity_standard' or 'propensity_gr'.

Run:              python3 files/engine/scoring_ml_split.py
Run (retrain):    python3 files/engine/scoring_ml_split.py --retrain
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sqlalchemy import create_engine, text
import xgboost as xgb

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
engine = create_engine(DB_URL)

TOP_N_OFFERS = 15
MODEL_STANDARD_PATH = os.path.join(os.path.dirname(__file__), "model_standard.pkl")
MODEL_GR_PATH = os.path.join(os.path.dirname(__file__), "model_gr.pkl")

FEATURE_COLS = [
    # Customer
    "current_point_balance", "points_expiring_next_month",
    "is_4uplus", "gas_rewards", "doordash", "instacart", "uber",
    "household_size", "num_children", "churn_risk", "days_since_last_txn",
    # Offer
    "discount_value", "is_j4u_exclusive", "is_freshpass_offer",
    "redemption_rate", "days_until_expiry",
    # Interaction
    "channel_match", "category_affinity", "points_gap",
]


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

def load_customers() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            cp.retail_customer_uuid,
            cp.household_id,
            cp.clv_tier_level_id,
            cp.current_point_balance,
            cp.points_expiring_next_month,
            cp.fav_channel,
            CASE WHEN cp.clv_tier_level_id = '4U+' THEN 1 ELSE 0 END AS is_4uplus,
            COALESCE(cp.gas_rewards_ind_6m::int, 0)    AS gas_rewards,
            COALESCE(cp.doordash_txn_ind_6m::int, 0)   AS doordash,
            COALESCE(cp.instacart_txn_ind_6m::int, 0)  AS instacart,
            COALESCE(cp.uber_txn_ind_6m::int, 0)       AS uber,
            COALESCE(cp.household_size, 1)             AS household_size,
            COALESCE(cp.num_of_children, 0)            AS num_children,
            COALESCE(cp.churn_risk_score_nbr, 0.5)     AS churn_risk,
            COALESCE((CURRENT_DATE - MAX(t.txn_dte))::int, 999) AS days_since_last_txn
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.head_household_ind = TRUE
        GROUP BY cp.retail_customer_uuid, cp.household_id, cp.clv_tier_level_id, cp.current_point_balance,
                 cp.points_expiring_next_month, cp.fav_channel, cp.gas_rewards_ind_6m,
                 cp.doordash_txn_ind_6m, cp.instacart_txn_ind_6m, cp.uber_txn_ind_6m,
                 cp.household_size, cp.num_of_children, cp.churn_risk_score_nbr
    """, engine)


def load_offers() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            o.client_offer_id,
            o.offer_dsc,
            o.delivery_channel_cd,
            o.discount_value,
            o.discount_type_cd,
            o.program_type,
            o.tier_1_points_threshold,
            o.is_appliable_to_j4u_ind::int     AS is_j4u_exclusive,
            o.is_freshpass_offer_ind::int       AS is_freshpass_offer,
            (o.end_dt - CURRENT_DATE)::int      AS days_until_expiry,
            COALESCE(os.red_pct, 0)             AS redemption_rate,
            os.rep_category_nm                  AS category_nm
        FROM c360_offer o
        LEFT JOIN c360_offer_summary os ON os.client_offer_id = o.client_offer_id
        WHERE o.offer_status_cd = 'ACTIVE'
    """, engine)


def load_affinity() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT household_id, category_nm, affinity_score
        FROM c360_cat_affinity
    """, engine)


def load_feature_weights() -> dict:
    """Load feature weights for scaling (if available)"""
    weights_file = os.path.join(os.path.dirname(__file__), "feature_weights.json")
    if os.path.exists(weights_file):
        try:
            with open(weights_file, 'r', encoding='utf-8') as f:
                weights = json.load(f)
            print(f"✅ Loaded {len([w for w in weights.values() if w != 1.0])} custom feature weights")
            return weights
        except Exception as e:
            print(f"⚠️  Could not load feature weights: {e}")
    return {feat: 1.0 for feat in FEATURE_COLS}


def load_freshpass_hhs() -> set:
    df = pd.read_sql("""
        SELECT DISTINCT household_id FROM c360_freshpass
        WHERE freshpass_status = 'ACTIVE'
    """, engine)
    return set(df["household_id"])


# ─── FEATURE ENGINEERING ──────────────────────────────────────────────────────

def build_features(pairs: pd.DataFrame, customers: pd.DataFrame,
                   offers: pd.DataFrame, affinity: pd.DataFrame, feature_weights: dict = None) -> pd.DataFrame:
    """Build feature matrix for (customer, offer) pairs."""
    df = pairs.merge(customers, on="household_id", how="left")
    df = df.merge(offers, on="client_offer_id", how="left")

    # Category affinity for this offer's category
    df = df.merge(
        affinity.rename(columns={"affinity_score": "category_affinity"}),
        on=["household_id", "category_nm"],
        how="left",
    )
    df["category_affinity"] = df["category_affinity"].fillna(0)

    # Channel match
    df["channel_match"] = (df["fav_channel"] == df["delivery_channel_cd"]).astype(int)

    # Points gap (how far above the GR threshold the customer is)
    df["points_gap"] = (
        df["current_point_balance"] - df["tier_1_points_threshold"].fillna(0)
    ).clip(lower=0)

    df["discount_value"] = df["discount_value"].fillna(0)
    df["days_until_expiry"] = df["days_until_expiry"].fillna(30)

    features = df[FEATURE_COLS].fillna(0).copy()
    
    # Apply feature weights if provided
    if feature_weights:
        for feat in FEATURE_COLS:
            if feat in feature_weights:
                features[feat] = features[feat] * feature_weights[feat]

    return features


# ─── TRAINING ─────────────────────────────────────────────────────────────────

def build_training_data_split(customers: pd.DataFrame, offers: pd.DataFrame,
                              affinity: pd.DataFrame, feature_weights: dict = None):
    """
    Build labeled feature matrices for both standard and GR offers separately.
    Returns (X_standard, y_standard, X_gr, y_gr)
    """
    # Load all clip-based labels
    clip_based = pd.read_sql("""
        SELECT
            cl.household_id,
            cl.client_offer_id,
            MAX(CASE WHEN r.txn_id IS NOT NULL THEN 1 ELSE 0 END) AS label
        FROM c360_clips cl
        LEFT JOIN c360_redemptions r
            ON cl.household_id = r.household_id
            AND cl.client_offer_id = r.client_offer_id
        GROUP BY cl.household_id, cl.client_offer_id
    """, engine)

    # Load implicit negatives
    implicit_negatives = pd.read_sql("""
        SELECT
            so.household_id,
            so.client_offer_id,
            0 AS label
        FROM c360_scored_offers so
        WHERE so.model_type = 'rule_based'
          AND NOT EXISTS (
            SELECT 1 FROM c360_clips cl
            WHERE cl.household_id = so.household_id
              AND cl.client_offer_id = so.client_offer_id
          )
    """, engine)

    labeled = pd.concat([clip_based, implicit_negatives], ignore_index=True)
    
    # Merge with offer type info
    labeled = labeled.merge(
        offers[["client_offer_id", "program_type"]],
        on="client_offer_id",
        how="left"
    )

    # Split by offer type: GR vs Standard
    is_gr = labeled["program_type"] == "Grocery Reward"
    
    labeled_standard = labeled[~is_gr].copy()
    labeled_gr = labeled[is_gr].copy()

    print(f"\n📊 Training data split:")
    print(f"   Standard offers: {len(labeled_standard)} pairs ({labeled_standard['label'].sum()} pos)")
    print(f"   GR offers:       {len(labeled_gr)} pairs ({labeled_gr['label'].sum()} pos)")

    # Build features for each
    X_standard = build_features(labeled_standard, customers, offers, affinity, feature_weights)
    y_standard = labeled_standard["label"].values

    X_gr = build_features(labeled_gr, customers, offers, affinity, feature_weights)
    y_gr = labeled_gr["label"].values

    return X_standard, y_standard, X_gr, y_gr


def train_model(X: pd.DataFrame, y: np.ndarray, model_name: str) -> tuple:
    """Train XGBoost and return model + metadata dict."""
    if len(y) == 0:
        print(f"⚠️  No training data for {model_name}")
        return None, None

    n_neg = int((y == 0).sum())
    n_pos = int(y.sum())
    
    if n_pos == 0:
        print(f"⚠️  No positive examples for {model_name}")
        return None, None

    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
    )

    # Cross-validated AUC
    if len(np.unique(y)) > 1:
        cv_auc = cross_val_score(model, X, y, cv=min(5, len(y)//10), scoring="roc_auc").mean()
    else:
        cv_auc = 0.5

    # Fit on full data
    model.fit(X, y)

    # Feature importances
    importances = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    metadata = {
        "model_type": model_name,
        "n_train": int(len(y)),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "scale_pos_weight": round(scale_pos_weight, 3),
        "auc_cv": round(float(cv_auc), 4),
        "top_features": top_features,
    }

    return model, metadata


# ─── SCORING ALL PAIRS ────────────────────────────────────────────────────────

def score_all_pairs(model: xgb.XGBClassifier, customers: pd.DataFrame,
                    offers: pd.DataFrame, affinity: pd.DataFrame,
                    freshpass_hhs: set, is_gr: bool) -> pd.DataFrame:
    """Score customer-offer pairs. If is_gr=True, score only GR offers. Otherwise, score standard offers."""
    if is_gr:
        offer_meta = offers[offers["program_type"] == "Grocery Reward"][
            ["client_offer_id", "offer_dsc", "delivery_channel_cd",
             "discount_value", "discount_type_cd", "program_type",
             "is_j4u_exclusive", "is_freshpass_offer"]
        ]
        model_label = "Grocery Reward"
    else:
        offer_meta = offers[offers["program_type"] != "Grocery Reward"][
            ["client_offer_id", "offer_dsc", "delivery_channel_cd",
             "discount_value", "discount_type_cd", "program_type",
             "is_j4u_exclusive", "is_freshpass_offer"]
        ]
        model_label = "Standard"

    if len(offer_meta) == 0:
        print(f"⚠️  No {model_label} offers found")
        return pd.DataFrame()

    pairs = customers[["household_id", "retail_customer_uuid"]].merge(offer_meta, how="cross")

    # Apply hard business rules
    mask_freshpass = (pairs["is_freshpass_offer"] == 1) & \
                     (~pairs["household_id"].isin(freshpass_hhs))
    mask_j4u = (pairs["is_j4u_exclusive"] == 1) & \
               (~pairs["household_id"].isin(
                   set(customers[customers["is_4uplus"] == 1]["household_id"])
               ))
    pairs = pairs[~mask_freshpass & ~mask_j4u].copy()

    # Feature engineering on filtered pairs
    pairs_ids = pairs[["household_id", "client_offer_id"]].copy()
    X = build_features(pairs_ids, customers, offers, affinity)

    # Score
    probs = model.predict_proba(X)[:, 1]
    pairs["score"] = (probs * 100).round(2)

    # Rank top N per household
    pairs["rank"] = pairs.groupby("household_id")["score"].rank(method="first", ascending=False).astype(int)
    pairs = pairs[pairs["rank"] <= TOP_N_OFFERS].copy()

    return pairs[[
        "household_id", "retail_customer_uuid", "client_offer_id", "offer_dsc",
        "delivery_channel_cd", "discount_value", "discount_type_cd", "score", "rank",
    ]]


# ─── WRITE ────────────────────────────────────────────────────────────────────

def write_results(pairs_standard: pd.DataFrame, pairs_gr: pd.DataFrame,
                  metadata_standard: dict, metadata_gr: dict,
                  model_standard: xgb.XGBClassifier, model_gr: xgb.XGBClassifier):
    """Write both model results to database and metadata to JSON."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM c360_scored_offers WHERE model_type IN ('propensity_standard', 'propensity_gr');"))
        conn.commit()

    # Add model_type columns
    if len(pairs_standard) > 0:
        pairs_standard["model_type"] = "propensity_standard"
        pairs_standard["scored_at"] = pd.Timestamp.now()
        pairs_standard.to_sql("c360_scored_offers", engine, if_exists="append",
                            index=False, method="multi", chunksize=500)
        print(f"✅ {len(pairs_standard)} propensity_standard scores written")

    if len(pairs_gr) > 0:
        pairs_gr["model_type"] = "propensity_gr"
        pairs_gr["scored_at"] = pd.Timestamp.now()
        pairs_gr.to_sql("c360_scored_offers", engine, if_exists="append",
                       index=False, method="multi", chunksize=500)
        print(f"✅ {len(pairs_gr)} propensity_gr scores written")

    # Save models
    if model_standard:
        joblib.dump(model_standard, MODEL_STANDARD_PATH)
        print(f"💾 Saved: {MODEL_STANDARD_PATH}")
    if model_gr:
        joblib.dump(model_gr, MODEL_GR_PATH)
        print(f"💾 Saved: {MODEL_GR_PATH}")

    # Combine metadata
    combined_metadata = {
        "trained_at": pd.Timestamp.now().isoformat(),
        "propensity_standard": metadata_standard,
        "propensity_gr": metadata_gr,
    }

    meta_path = os.path.join(os.path.dirname(__file__), "model_metadata_split.json")
    with open(meta_path, "w") as f:
        json.dump(combined_metadata, f, indent=2, default=str)
    print(f"📝 Metadata: {meta_path}")


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def run(force_retrain=False):
    print("🔍 Loading data from PostgreSQL...")
    customers = load_customers()
    offers = load_offers()
    affinity = load_affinity()
    freshpass = load_freshpass_hhs()
    
    # Load feature weights (if available)
    feature_weights = load_feature_weights()

    print(f"  {len(customers)} households  |  {len(offers)} active offers")

    # Check if saved models exist (skip if not forcing retrain)
    if not force_retrain and os.path.exists(MODEL_STANDARD_PATH) and os.path.exists(MODEL_GR_PATH):
        print(f"Loading saved models (use --retrain to force retraining)...")
        model_standard = joblib.load(MODEL_STANDARD_PATH)
        model_gr = joblib.load(MODEL_GR_PATH)
        with open(os.path.join(os.path.dirname(__file__), "model_metadata_split.json")) as f:
            combined_metadata = json.load(f)
            metadata_standard = combined_metadata.get("propensity_standard", {})
            metadata_gr = combined_metadata.get("propensity_gr", {})
    else:
        print("🏗️  Building training data...")
        X_standard, y_standard, X_gr, y_gr = build_training_data_split(customers, offers, affinity, feature_weights)

        print("🤖 Training XGBoost (Standard)...")
        model_standard, metadata_standard = train_model(X_standard, y_standard, "propensity_standard")

        print("🤖 Training XGBoost (GR)...")
        model_gr, metadata_gr = train_model(X_gr, y_gr, "propensity_gr")

    if model_standard is None or model_gr is None:
        print("❌ Training failed")
        return

    print("\n🎯 Scoring all household-offer pairs...")
    pairs_standard = score_all_pairs(model_standard, customers, offers, affinity, freshpass, is_gr=False)
    pairs_gr = score_all_pairs(model_gr, customers, offers, affinity, freshpass, is_gr=True)

    print("\n📤 Writing results...")
    write_results(pairs_standard, pairs_gr, metadata_standard, metadata_gr, model_standard, model_gr)

    # Print summary
    print(f"\n✨ Split propensity models complete!")
    print(f"\nMetrics:")
    print(f"  Standard: AUC={metadata_standard['auc_cv']:.4f}  ({metadata_standard['n_pos']} pos / {metadata_standard['n_neg']} neg)")
    print(f"  GR:       AUC={metadata_gr['auc_cv']:.4f}  ({metadata_gr['n_pos']} pos / {metadata_gr['n_neg']} neg)")
    print(f"\nTop features (Standard): {', '.join(f[0] for f in metadata_standard['top_features'][:3])}")
    print(f"Top features (GR):       {', '.join(f[0] for f in metadata_gr['top_features'][:3])}")


if __name__ == "__main__":
    force_retrain = "--retrain" in sys.argv
    run(force_retrain=force_retrain)
