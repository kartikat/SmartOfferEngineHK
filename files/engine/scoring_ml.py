"""
SmartOfferEngine — XGBoost Propensity Scoring Engine (Split: Standard + GR)

Trains two separate XGBoost models:
  - Standard model: trained on standard offer clips/redemptions (19 features)
  - GR model:       trained on Grocery Reward clips only (12 points-focused features)

Standard model → model_type = 'propensity'     (UI toggle, backward compatible)
GR model       → model_type = 'propensity_gr'  (ready for score-based My Rewards UI)

Run:              python3 files/engine/scoring_ml.py          # uses saved models if exist
Run (retrain):    python3 files/engine/scoring_ml.py --retrain  # forces full retrain
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

TOP_N_STANDARD = 10    # standard offers stored per household
TOP_N_GR       = 5     # GR offers stored per household
TOP_N_OFFERS   = max(TOP_N_STANDARD, TOP_N_GR)  # used as single cap in _score_pairs; standard/GR scored separately
ENGINE_DIR = os.path.dirname(__file__)
MODEL_STANDARD_PATH = os.path.join(ENGINE_DIR, "model_standard.pkl")
MODEL_GR_PATH       = os.path.join(ENGINE_DIR, "model_gr.pkl")

# Standard offer features — all 19
FEATURE_COLS_STANDARD = [
    # Customer — no points features; standard offers don't require points to redeem
    "is_4uplus", "gas_rewards", "doordash", "instacart", "uber",
    "household_size", "num_children", "churn_risk", "days_since_last_txn",
    # Offer
    "discount_value", "is_j4u_exclusive", "is_freshpass_offer",
    "redemption_rate", "days_until_expiry",
    # Interaction
    "channel_match", "category_affinity",
]

# GR offer features — 12, focused on points and affinity signals
# Drops channel_match, is_j4u_exclusive, is_freshpass_offer, gas_rewards, doordash, instacart, uber
FEATURE_COLS_GR = [
    # Customer — points focused
    "current_point_balance", "points_expiring_next_month",
    "is_4uplus", "household_size", "num_children", "churn_risk", "days_since_last_txn",
    # Offer
    "discount_value", "redemption_rate", "days_until_expiry",
    # Interaction — points focused
    "category_affinity", "points_gap",
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
                   offers: pd.DataFrame, affinity: pd.DataFrame,
                   feature_cols: list) -> pd.DataFrame:
    """
    pairs must have columns: household_id, client_offer_id.
    Returns feature matrix with columns = feature_cols.
    """
    df = pairs.merge(customers, on="household_id", how="left")
    df = df.merge(offers, on="client_offer_id", how="left")

    df = df.merge(
        affinity.rename(columns={"affinity_score": "category_affinity"}),
        on=["household_id", "category_nm"],
        how="left",
    )
    df["category_affinity"] = df["category_affinity"].fillna(0)
    df["channel_match"] = (df["fav_channel"] == df["delivery_channel_cd"]).astype(int)
    df["points_gap"] = (
        df["current_point_balance"] - df["tier_1_points_threshold"].fillna(0)
    ).clip(lower=0)
    df["discount_value"] = df["discount_value"].fillna(0)
    df["days_until_expiry"] = df["days_until_expiry"].fillna(30)

    return df[feature_cols].fillna(0)


# ─── TRAINING ─────────────────────────────────────────────────────────────────

def build_training_data(customers: pd.DataFrame, offers: pd.DataFrame,
                        affinity: pd.DataFrame, feature_cols: list,
                        gr: bool = False):
    """
    Build labeled feature matrix filtered to standard OR GR offers.
    gr=False → standard offers only (program_type != 'Grocery Reward')
    gr=True  → GR offers only (program_type = 'Grocery Reward')
    """
    gr_filter = "= 'Grocery Reward'" if gr else "!= 'Grocery Reward'"

    clip_based = pd.read_sql(f"""
        SELECT
            cl.household_id,
            cl.client_offer_id,
            MAX(CASE WHEN r.txn_id IS NOT NULL THEN 1 ELSE 0 END) AS label
        FROM c360_clips cl
        JOIN c360_offer o ON o.client_offer_id = cl.client_offer_id
        LEFT JOIN c360_redemptions r
            ON cl.household_id = r.household_id
            AND cl.client_offer_id = r.client_offer_id
        WHERE o.program_type {gr_filter}
        GROUP BY cl.household_id, cl.client_offer_id
    """, engine)

    implicit_negatives = pd.read_sql(f"""
        SELECT so.household_id, so.client_offer_id, 0 AS label
        FROM c360_scored_offers so
        JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
        WHERE so.model_type = 'rule_based'
          AND o.program_type {gr_filter}
          AND NOT EXISTS (
            SELECT 1 FROM c360_clips cl
            WHERE cl.household_id = so.household_id
              AND cl.client_offer_id = so.client_offer_id
          )
    """, engine)

    labeled = pd.concat([clip_based, implicit_negatives], ignore_index=True)
    X = build_features(labeled, customers, offers, affinity, feature_cols)
    y = labeled["label"].values
    return X, y


def train_model(X: pd.DataFrame, y: np.ndarray,
                model_name: str) -> tuple[xgb.XGBClassifier, dict]:
    """Train XGBoost and return model + metadata dict."""
    n_neg = int((y == 0).sum())
    n_pos = int(y.sum())
    scale_pos_weight = n_neg / max(n_pos, 1)

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

    cv_auc = cross_val_score(model, X, y, cv=5, scoring="roc_auc").mean()
    model.fit(X, y)

    feature_cols = list(X.columns)
    importances = dict(zip(feature_cols, model.feature_importances_.tolist()))
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


# ─── SCORING ──────────────────────────────────────────────────────────────────

def _apply_business_rules(pairs: pd.DataFrame, customers: pd.DataFrame,
                          freshpass_hhs: set) -> pd.DataFrame:
    """Apply FreshPass and 4U+ hard filters."""
    mask_freshpass = (pairs["is_freshpass_offer"] == 1) & \
                     (~pairs["household_id"].isin(freshpass_hhs))
    mask_j4u = (pairs["is_j4u_exclusive"] == 1) & \
               (~pairs["household_id"].isin(
                   set(customers[customers["is_4uplus"] == 1]["household_id"])
               ))
    return pairs[~mask_freshpass & ~mask_j4u].copy()


def _score_pairs(model: xgb.XGBClassifier, pairs: pd.DataFrame,
                 customers: pd.DataFrame, offers: pd.DataFrame,
                 affinity: pd.DataFrame, feature_cols: list,
                 model_type: str, top_n: int = TOP_N_STANDARD) -> pd.DataFrame:
    """Score a set of pairs and return ranked results."""
    pairs_ids = pairs[["household_id", "client_offer_id"]].copy()
    X = build_features(pairs_ids, customers, offers, affinity, feature_cols)
    pairs = pairs.copy()
    pairs["score"] = (model.predict_proba(X)[:, 1] * 100).round(2)
    pairs["rank"] = pairs.groupby("household_id")["score"] \
                         .rank(method="first", ascending=False).astype(int)
    pairs = pairs[pairs["rank"] <= top_n].copy()
    pairs["retail_customer_uuid"] = None
    pairs["model_type"] = model_type
    pairs["scored_at"] = pd.Timestamp.now()
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


def score_standard_pairs(model: xgb.XGBClassifier, customers: pd.DataFrame,
                         offers: pd.DataFrame, affinity: pd.DataFrame,
                         freshpass_hhs: set) -> pd.DataFrame:
    """Score standard (non-GR) offers with the standard model."""
    standard_offers = offers[offers["program_type"] != "Grocery Reward"]
    offer_meta = standard_offers[["client_offer_id", "offer_dsc", "delivery_channel_cd",
                                  "discount_value", "discount_type_cd", "program_type",
                                  "is_j4u_exclusive", "is_freshpass_offer"]]
    pairs = customers[["household_id"]].merge(offer_meta, how="cross")
    pairs = _apply_business_rules(pairs, customers, freshpass_hhs)
    return _score_pairs(model, pairs, customers, offers, affinity,
                        FEATURE_COLS_STANDARD, model_type="propensity", top_n=TOP_N_STANDARD)


def score_gr_pairs(model: xgb.XGBClassifier, customers: pd.DataFrame,
                   offers: pd.DataFrame, affinity: pd.DataFrame,
                   freshpass_hhs: set) -> pd.DataFrame:
    """Score Grocery Reward offers with the GR model."""
    gr_offers = offers[offers["program_type"] == "Grocery Reward"]
    offer_meta = gr_offers[["client_offer_id", "offer_dsc", "delivery_channel_cd",
                             "discount_value", "discount_type_cd", "program_type",
                             "is_j4u_exclusive", "is_freshpass_offer"]]
    pairs = customers[["household_id"]].merge(offer_meta, how="cross")
    pairs = _apply_business_rules(pairs, customers, freshpass_hhs)
    return _score_pairs(model, pairs, customers, offers, affinity,
                        FEATURE_COLS_GR, model_type="propensity_gr", top_n=TOP_N_GR)


# ─── WRITE ────────────────────────────────────────────────────────────────────

def write_results(scored: pd.DataFrame, metadata: dict,
                  model: xgb.XGBClassifier, model_path: str,
                  meta_filename: str):
    model_type = metadata["model_type"]
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM c360_scored_offers WHERE model_type = '{model_type}';"))
        conn.commit()

    scored.to_sql("c360_scored_offers", engine, if_exists="append",
                  index=False, method="multi", chunksize=500)

    joblib.dump(model, model_path)

    meta_path = os.path.join(ENGINE_DIR, meta_filename)
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✅ {len(scored)} scores written  |  model_type='{model_type}'  |"
          f"  CV AUC: {metadata['auc_cv']:.4f}  |"
          f"  {metadata['n_pos']} pos / {metadata['n_neg']} neg")
    print(f"     Top features: {', '.join(f[0] for f in metadata['top_features'][:5])}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run(force_retrain: bool = False):
    print("Loading data...")
    customers = load_customers()
    offers    = load_offers()
    affinity  = load_affinity()
    freshpass = load_freshpass_hhs()
    print(f"  {len(customers)} households  |  {len(offers)} active offers")

    # ── Standard model ────────────────────────────────────────────────────────
    print("\n── Standard Propensity Model ──────────────────────────────────────")
    if not force_retrain and os.path.exists(MODEL_STANDARD_PATH):
        print(f"  Loading saved model from model_standard.pkl ...")
        model_std = joblib.load(MODEL_STANDARD_PATH)
        with open(os.path.join(ENGINE_DIR, "model_metadata.json")) as f:
            meta_std = json.load(f)
    else:
        print("  Building training data (standard offers only)...")
        X_std, y_std = build_training_data(customers, offers, affinity,
                                           FEATURE_COLS_STANDARD, gr=False)
        print(f"  {len(y_std)} examples  |  {y_std.sum()} positive  |  {(y_std==0).sum()} negative")
        print("  Training XGBoost...")
        model_std, meta_std = train_model(X_std, y_std, model_name="propensity")

    print("  Scoring standard pairs...")
    scored_std = score_standard_pairs(model_std, customers, offers, affinity, freshpass)
    write_results(scored_std, meta_std, model_std, MODEL_STANDARD_PATH, "model_metadata.json")

    # ── GR model ──────────────────────────────────────────────────────────────
    print("\n── Grocery Reward Propensity Model ────────────────────────────────")
    if not force_retrain and os.path.exists(MODEL_GR_PATH):
        print(f"  Loading saved model from model_gr.pkl ...")
        model_gr = joblib.load(MODEL_GR_PATH)
        with open(os.path.join(ENGINE_DIR, "model_gr_metadata.json")) as f:
            meta_gr = json.load(f)
    else:
        print("  Building training data (GR offers only)...")
        X_gr, y_gr = build_training_data(customers, offers, affinity,
                                         FEATURE_COLS_GR, gr=True)
        print(f"  {len(y_gr)} examples  |  {y_gr.sum()} positive  |  {(y_gr==0).sum()} negative")
        print("  Training XGBoost...")
        model_gr, meta_gr = train_model(X_gr, y_gr, model_name="propensity_gr")

    print("  Scoring GR pairs...")
    scored_gr = score_gr_pairs(model_gr, customers, offers, affinity, freshpass)
    write_results(scored_gr, meta_gr, model_gr, MODEL_GR_PATH, "model_gr_metadata.json")


if __name__ == "__main__":
    force_retrain = "--retrain" in sys.argv
    run(force_retrain=force_retrain)
