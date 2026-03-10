"""
SmartRewards — XGBoost Propensity Scoring Engine

Trains XGBoost on:
  Positive labels: c360_redemptions (customer redeemed an offer)
  Negative labels: c360_clips LEFT JOIN c360_redemptions WHERE no match (clipped, not redeemed)

Predicts P(redemption | customer, offer) → scaled 0–100.
Applies same hard business rules as rule-based engine (FreshPass, 4U+ filters).
Writes results to c360_scored_offers with model_type = 'propensity'.

Run:              python3 files/engine/scoring_ml.py          # uses saved model if exists
Run (retrain):    python3 files/engine/scoring_ml.py --retrain  # forces full retrain
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine, text
import xgboost as xgb

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
engine = create_engine(DB_URL)

TOP_N_OFFERS = 15
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

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
        GROUP BY cp.household_id, cp.clv_tier_level_id, cp.current_point_balance,
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


def load_freshpass_hhs() -> set:
    df = pd.read_sql("""
        SELECT DISTINCT household_id FROM c360_freshpass
        WHERE freshpass_status = 'ACTIVE'
    """, engine)
    return set(df["household_id"])


# ─── FEATURE ENGINEERING ──────────────────────────────────────────────────────

def build_features(pairs: pd.DataFrame, customers: pd.DataFrame,
                   offers: pd.DataFrame, affinity: pd.DataFrame) -> pd.DataFrame:
    """
    pairs must have columns: household_id, client_offer_id.
    Returns feature matrix aligned to pairs index.
    """
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

    return df[FEATURE_COLS].fillna(0)


# ─── TRAINING ─────────────────────────────────────────────────────────────────

def build_training_data(customers: pd.DataFrame, offers: pd.DataFrame,
                        affinity: pd.DataFrame):
    """
    Build labeled feature matrix from three sources:
      1. Clip + redeemed          → label = 1  (explicit positive)
      2. Clip + not redeemed      → label = 0  (explicit negative)
      3. Eligible, never clipped  → label = 0  (implicit negative)
    """
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

    X = build_features(labeled, customers, offers, affinity)
    y = labeled["label"].values
    return X, y


def train_model(X: pd.DataFrame, y: np.ndarray) -> tuple[xgb.XGBClassifier, dict]:
    """Train XGBoost and return model + metadata dict."""
    n_neg = int((y == 0).sum())
    n_pos = int(y.sum())
    scale_pos_weight = n_neg / n_pos  # compensates for class imbalance

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
    cv_auc = cross_val_score(model, X, y, cv=5, scoring="roc_auc").mean()

    # Fit on full data for scoring
    model.fit(X, y)

    # Feature importances
    importances = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    metadata = {
        "model_type": "propensity",
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
                    freshpass_hhs: set) -> pd.DataFrame:
    """Score every head-of-household × active offer pair."""
    offer_meta = offers[["client_offer_id", "offer_dsc", "delivery_channel_cd",
                         "discount_value", "discount_type_cd", "program_type",
                         "is_j4u_exclusive", "is_freshpass_offer"]]

    pairs = customers[["household_id"]].merge(offer_meta, how="cross")

    # Apply same hard business rules as rule-based engine
    mask_freshpass = (pairs["is_freshpass_offer"] == 1) & \
                     (~pairs["household_id"].isin(freshpass_hhs))
    mask_j4u = (pairs["is_j4u_exclusive"] == 1) & \
               (~pairs["household_id"].isin(
                   set(customers[customers["is_4uplus"] == 1]["household_id"])
               ))
    pairs = pairs[~mask_freshpass & ~mask_j4u].copy()

    # Build features on ID-only pairs to avoid duplicate columns in merge
    pairs_ids = pairs[["household_id", "client_offer_id"]].copy()
    X = build_features(pairs_ids, customers, offers, affinity)
    pairs["score"] = (model.predict_proba(X)[:, 1] * 100).round(2)

    # Rank top N per household
    pairs["rank"] = pairs.groupby("household_id")["score"] \
                         .rank(method="first", ascending=False).astype(int)
    pairs = pairs[pairs["rank"] <= TOP_N_OFFERS].copy()

    pairs["retail_customer_uuid"] = None
    pairs["model_type"] = "propensity"
    pairs["scored_at"] = pd.Timestamp.now()

    # Component scores are not applicable for propensity model
    for col in ["transaction_affinity", "redemption_match", "points_eligibility",
                "cart_affinity", "demographic_match"]:
        pairs[col] = None
    pairs["recency_boost_applied"] = False
    pairs["tier_multiplier_applied"] = False

    return pairs[[
        "household_id", "retail_customer_uuid", "client_offer_id", "offer_dsc",
        "delivery_channel_cd", "discount_value", "discount_type_cd", "score", "rank",
        "transaction_affinity", "redemption_match", "points_eligibility",
        "cart_affinity", "demographic_match", "recency_boost_applied",
        "tier_multiplier_applied", "model_type", "scored_at",
    ]]


# ─── WRITE ────────────────────────────────────────────────────────────────────

def write_results(scored: pd.DataFrame, metadata: dict):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM c360_scored_offers WHERE model_type = 'propensity';"))
        conn.commit()

    scored.to_sql("c360_scored_offers", engine, if_exists="append",
                  index=False, method="multi", chunksize=500)

    # Persist model to disk
    joblib.dump(model, MODEL_PATH)

    # Persist metadata for the UI to read
    meta_path = os.path.join(os.path.dirname(__file__), "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ {len(scored)} propensity scores written to c360_scored_offers")
    print(f"   CV AUC: {metadata['auc_cv']:.4f}  |  "
          f"Training: {metadata['n_pos']} positive / {metadata['n_neg']} negative")
    print(f"   Top features: {', '.join(f[0] for f in metadata['top_features'][:5])}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run(force_retrain: bool = False):
    print("Loading data...")
    customers = load_customers()
    offers    = load_offers()
    affinity  = load_affinity()
    freshpass = load_freshpass_hhs()

    print(f"  {len(customers)} households  |  {len(offers)} active offers")

    if not force_retrain and os.path.exists(MODEL_PATH):
        print(f"Loading saved model from {MODEL_PATH} (use --retrain to force retraining)...")
        model = joblib.load(MODEL_PATH)
        # Load existing metadata so write_results can persist it
        meta_path = os.path.join(os.path.dirname(__file__), "model_metadata.json")
        with open(meta_path) as f:
            metadata = json.load(f)
    else:
        print("Building training data...")
        X_train, y_train = build_training_data(customers, offers, affinity)
        print(f"  {len(y_train)} examples  |  {y_train.sum()} positive  |  {(y_train==0).sum()} negative")

        print("Training XGBoost...")
        model, metadata = train_model(X_train, y_train)

    print("Scoring all household-offer pairs...")
    scored = score_all_pairs(model, customers, offers, affinity, freshpass)

    print("Writing results...")
    write_results(scored, metadata)


if __name__ == "__main__":
    force_retrain = "--retrain" in sys.argv
    run(force_retrain=force_retrain)
