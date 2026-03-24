"""
SmartOfferEngine — Rule-Based Offer Scoring Engine (PostgreSQL)

Reads from: c360_customer_profile, c360_offer, c360_cat_affinity,
            c360_txn, c360_redemptions, c360_rewards_redeemed, c360_freshpass
Writes to:  c360_scored_offers

Two scoring paths:
  Path 1 — Standard offers  (program_type != 'Grocery Reward')
  Path 2 — Grocery Rewards  (program_type = 'Grocery Reward')

Run: python3 files/engine/scoring.py
"""

import os
from datetime import date

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
engine = create_engine(DB_URL)

TODAY = date.today()

# ─── WEIGHTS (Path 1 — Standard) ─────────────────────────────────────────────
WEIGHTS = {
    "transaction_affinity": 0.30,
    "redemption_match":     0.25,
    "points_eligibility":   0.20,
    "cart_affinity":        0.15,
    "demographic_match":    0.10,
}

RECENCY_BOOST   = 1.20   # ×1.2 if transacted within last 7 days
TIER_MULTIPLIER = 1.50   # ×1.5 for 4U+ on exclusive offers
TOP_N_STANDARD  = 10     # standard (non-GR) offers stored per household
TOP_N_GR        = 5      # Grocery Reward offers stored per household


# ─── DATA LOADING ────────────────────────────────────────────────────────────

def load_data():
    customers = pd.read_sql("""
        SELECT
            cp.retail_customer_uuid,
            cp.household_id,
            cp.head_household_ind,
            cp.clv_tier_level_id,
            cp.current_point_balance,
            cp.points_expiring_next_month,
            cp.fav_channel,
            cp.eng_mode_p6m,
            cp.customer_age,
            cp.num_of_children,
            cp.household_size,
            cp.diet_preference,
            cp.gas_rewards_ind_6m,
            cp.fuel_station_purchase_ind_6m,
            cp.doordash_txn_ind_6m,
            cp.instacart_txn_ind_6m,
            cp.uber_txn_ind_6m,
            cp.dairy_purchase_ind_6m,
            cp.produce_purchase_ind_6m,
            cp.bakery_purchase_ind_6m,
            cp.meat_purchase_ind_6m,
            cp.frozen_grocery_purchase_ind_6m,
            cp.own_brand_ind_6m,
            -- Days since last transaction (derived)
            COALESCE(
                (CURRENT_DATE - MAX(t.txn_dte))::int,
                999
            ) AS days_since_last_txn
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.head_household_ind = TRUE
        GROUP BY
            cp.retail_customer_uuid, cp.household_id, cp.head_household_ind,
            cp.clv_tier_level_id, cp.current_point_balance, cp.points_expiring_next_month,
            cp.fav_channel, cp.eng_mode_p6m, cp.customer_age, cp.num_of_children,
            cp.household_size, cp.diet_preference, cp.gas_rewards_ind_6m,
            cp.fuel_station_purchase_ind_6m, cp.doordash_txn_ind_6m,
            cp.instacart_txn_ind_6m, cp.uber_txn_ind_6m, cp.dairy_purchase_ind_6m,
            cp.produce_purchase_ind_6m, cp.bakery_purchase_ind_6m, cp.meat_purchase_ind_6m,
            cp.frozen_grocery_purchase_ind_6m, cp.own_brand_ind_6m
    """, engine)

    offers = pd.read_sql("""
        SELECT
            o.client_offer_id,
            o.oms_offer_id,
            o.offer_dsc,
            o.delivery_channel_cd,
            o.program_type,
            o.discount_type_cd,
            o.discount_value,
            o.target_level_cd,
            o.is_appliable_to_j4u_ind,
            o.is_freshpass_offer_ind,
            o.tier_1_points_threshold,
            o.tier_2_points_threshold,
            o.tier_3_points_threshold,
            o.tier_1_discount,
            o.tier_2_discount,
            o.tier_3_discount,
            os.rep_category_nm          AS offer_category,
            os.red_pct                  AS historical_red_pct,
            COALESCE(os.clips, 0)       AS total_clips
        FROM c360_offer o
        LEFT JOIN c360_offer_summary os ON os.client_offer_id = o.client_offer_id
        WHERE o.offer_status_cd = 'ACTIVE'
          AND o.dw_logical_delete_ind = FALSE
    """, engine)

    affinity = pd.read_sql("""
        SELECT household_id, category_nm, affinity_score
        FROM c360_cat_affinity
    """, engine)

    # Grocery Reward redemption history per household
    gr_history = pd.read_sql("""
        SELECT household_id, COUNT(*) AS gr_redemption_count
        FROM c360_rewards_redeemed
        WHERE src = 'Grocery'
        GROUP BY household_id
    """, engine)

    # FreshPass active subscribers
    freshpass_hhs = pd.read_sql("""
        SELECT DISTINCT household_id
        FROM c360_freshpass
        WHERE freshpass_status = 'ACTIVE'
    """, engine)

    return customers, offers, affinity, gr_history, freshpass_hhs


# ─── PATH 1 — STANDARD OFFER SCORING ─────────────────────────────────────────

def score_transaction_affinity(customer: dict, offer: dict, affinity_lookup: dict) -> float:
    """Category spend proportion from c360_cat_affinity."""
    key = (customer["household_id"], offer["offer_category"])
    return affinity_lookup.get(key, 0.0)


def score_redemption_match(customer: dict, offer: dict) -> float:
    """Channel alignment: customer fav_channel vs offer delivery_channel_cd."""
    fav = customer.get("fav_channel", "")
    channel = offer.get("delivery_channel_cd", "")

    if channel == "Auto Clip":
        return 0.7        # auto-clip is channel-neutral

    if channel == "J4U":
        # Digital/app offer — rewards eCommerce and app users
        if fav == "J4U":
            return 1.0
        elif customer.get("eng_mode_p6m") == "Both":
            return 0.7
        elif customer.get("gas_rewards_ind_6m"):
            # Fuel redeemers: intentional eCommerce nudge
            return 0.6
        else:
            return 0.3

    if channel == "Weekly Ad":
        if fav == "Weekly Ad":
            return 1.0
        elif customer.get("eng_mode_p6m") in ["In-Store", "Both"]:
            return 0.8
        else:
            return 0.3

    return 0.5


def score_points_eligibility(customer: dict, offer: dict) -> float:
    """Whether customer can benefit from the offer's points requirement."""
    balance = customer.get("current_point_balance", 0)
    threshold = offer.get("tier_1_points_threshold") or 0

    if threshold == 0:
        # Not a points-cost offer — score based on having any points (reward opportunity)
        return min(balance / 500, 1.0)

    if balance < threshold:
        return 0.0
    elif offer.get("tier_2_points_threshold") and balance >= (offer.get("tier_2_points_threshold") or 999999):
        return 0.85
    else:
        return 0.5


def score_cart_affinity(customer: dict, offer: dict) -> float:
    """eCommerce engagement signals for digital/delivery offers."""
    is_ecom_offer = offer.get("delivery_channel_cd") in ["J4U", "Auto Clip"]
    ecom_signals = sum([
        bool(customer.get("doordash_txn_ind_6m")),
        bool(customer.get("instacart_txn_ind_6m")),
        bool(customer.get("uber_txn_ind_6m")),
        customer.get("eng_mode_p6m") == "eCommerce",
    ])
    ecom_score = min(ecom_signals / 3, 1.0)

    if is_ecom_offer:
        return ecom_score
    else:
        # In-store offers — slight penalty for heavy online-only users
        return 1.0 - (ecom_score * 0.3)


def score_demographic_match(customer: dict, offer: dict) -> float:
    """Life-stage fit heuristics."""
    score = 0.5
    category = offer.get("offer_category", "")
    age = customer.get("customer_age", "")
    n_children = customer.get("num_of_children", 0) or 0

    # Fuel skews toward middle-aged drivers
    if "Fuel" in category and age in ["35-44", "45-54", "55-64"]:
        score += 0.3

    # Dairy/Produce/Bakery skew toward families
    if category in ["Dairy Eggs Cheese", "Produce", "Bakery"] and (
        age in ["25-34", "35-44"] or n_children > 0
    ):
        score += 0.3

    # Health-conscious offers match diet preference
    if customer.get("own_brand_ind_6m") and "Organic" in (offer.get("offer_dsc") or ""):
        score += 0.2

    return min(score, 1.0)


def score_standard_offer(customer: dict, offer: dict, affinity_lookup: dict) -> dict:
    """Compute composite score for a standard offer. Returns component breakdown."""
    components = {
        "transaction_affinity": score_transaction_affinity(customer, offer, affinity_lookup),
        "redemption_match":     score_redemption_match(customer, offer),
        "points_eligibility":   score_points_eligibility(customer, offer),
        "cart_affinity":        score_cart_affinity(customer, offer),
        "demographic_match":    score_demographic_match(customer, offer),
    }

    base_score = sum(WEIGHTS[k] * v for k, v in components.items()) * 100

    recency_applied = customer.get("days_since_last_txn", 999) <= 7
    tier_applied = (
        customer.get("clv_tier_level_id") == "4U+"
        and bool(offer.get("is_appliable_to_j4u_ind"))
    )

    if recency_applied:
        base_score *= RECENCY_BOOST
    if tier_applied:
        base_score *= TIER_MULTIPLIER

    return {
        **components,
        "score":                   round(min(base_score, 100), 2),
        "recency_boost_applied":   recency_applied,
        "tier_multiplier_applied": tier_applied,
    }


# ─── PATH 2 — GROCERY REWARD SCORING ─────────────────────────────────────────

def score_grocery_reward(customer: dict, offer: dict, affinity_lookup: dict, gr_redemption_count: int) -> dict:
    """Separate scoring path for Grocery Reward offers (customer spends points)."""
    balance = customer.get("current_point_balance", 0)
    t1 = offer.get("tier_1_points_threshold") or 0
    t2 = offer.get("tier_2_points_threshold") or 999999
    t3 = offer.get("tier_3_points_threshold") or 999999

    # Step 1 — Hard eligibility gate
    if not t1 or balance < t1:
        return None   # not eligible — exclude from ranked list

    # Step 2 — Points eligibility score: how far above the threshold is the customer?
    # ratio=1.0 (just eligible) → 0.5; ratio=2.0 (2x threshold) → 1.0; capped at 1.0
    ratio = balance / t1
    points_score = min(ratio / 2.0, 1.0)

    # Step 3 — Category affinity
    key = (customer["household_id"], offer.get("offer_category", ""))
    cat_score = affinity_lookup.get(key, 0.2)

    # Step 4 — Value per point (discount / threshold)
    best_discount = offer.get("tier_1_discount") or offer.get("discount_value") or 0
    value_per_pt = min((best_discount / t1) * 10, 1.0) if t1 else 0.0

    # Step 5 — Grocery Reward history (frequency of past GR redemptions)
    # Floor of 0.3 so first-time GR customers aren't penalised
    gr_score = max(0.3, min(gr_redemption_count / 5, 1.0))

    # Step 6 — Recency
    days = customer.get("days_since_last_txn", 999)
    recency_score = max(0.0, 1.0 - (days / 90))

    # Weighted composite (weights sum to 1.0)
    base_score = (
        0.40 * points_score +
        0.25 * cat_score +
        0.15 * value_per_pt +
        0.15 * gr_score +
        0.05 * recency_score
    ) * 100

    # Points expiry multiplier
    expiring = customer.get("points_expiring_next_month", 0) or 0
    expiry_applied = expiring >= t1
    if expiry_applied:
        base_score *= 1.3

    # Score cap
    final_score = round(min(base_score, 100), 2)

    return {
        "transaction_affinity":    round(cat_score, 4),
        "redemption_match":        round(points_score, 4),
        "points_eligibility":      round(points_score, 4),
        "cart_affinity":           round(value_per_pt, 4),
        "demographic_match":       round(gr_score, 4),
        "score":                   final_score,
        "recency_boost_applied":   expiry_applied,
        "tier_multiplier_applied": False,
    }


# ─── BUSINESS RULES ──────────────────────────────────────────────────────────

def passes_business_rules(customer: dict, offer: dict, freshpass_hh_set: set) -> bool:
    """Hard filters applied before scoring. Returns False to exclude offer."""
    hh_id = customer["household_id"]

    # FreshPass-only offers require active subscription
    if offer.get("is_freshpass_offer_ind") and hh_id not in freshpass_hh_set:
        return False

    # 4U+ exclusive offers require premium tier
    if offer.get("is_appliable_to_j4u_ind") and customer.get("clv_tier_level_id") != "4U+":
        return False

    return True


# ─── BATCH SCORING ────────────────────────────────────────────────────────────

def run_batch_scoring(customers, offers, affinity, gr_history, freshpass_hhs):
    # Build lookup structures
    affinity_lookup = {
        (row["household_id"], row["category_nm"]): row["affinity_score"]
        for _, row in affinity.iterrows()
    }
    gr_lookup = dict(zip(gr_history["household_id"], gr_history["gr_redemption_count"]))
    freshpass_hh_set = set(freshpass_hhs["household_id"].tolist())

    offer_list = offers.to_dict("records")
    results = []

    for _, customer in customers.iterrows():
        cust = customer.to_dict()
        hh_id = cust["household_id"]
        gr_count = gr_lookup.get(hh_id, 0)

        scored_offers = []

        for offer in offer_list:
            # Business rules gate
            if not passes_business_rules(cust, offer, freshpass_hh_set):
                continue

            is_grocery_reward = (offer.get("program_type") or "").strip() == "Grocery Reward"

            if is_grocery_reward:
                result = score_grocery_reward(cust, offer, affinity_lookup, gr_count)
                if result is None:
                    continue  # below points threshold
            else:
                result = score_standard_offer(cust, offer, affinity_lookup)

            scored_offers.append({
                "household_id":            hh_id,
                "retail_customer_uuid":    cust["retail_customer_uuid"],
                "client_offer_id":         offer["client_offer_id"],
                "offer_dsc":               offer["offer_dsc"],
                "delivery_channel_cd":     offer["delivery_channel_cd"],
                "discount_value":          offer["discount_value"],
                "discount_type_cd":        offer["discount_type_cd"],
                **result,
            })

        # Rank standard and GR offers separately into their own pools
        standard_offers = [o for o in scored_offers if (o.get("discount_type_cd") or "") not in ("GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM")]
        gr_offers        = [o for o in scored_offers if (o.get("discount_type_cd") or "") in ("GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM")]

        standard_offers.sort(key=lambda x: x["score"], reverse=True)
        gr_offers.sort(key=lambda x: x["score"], reverse=True)

        for rank, rec in enumerate(standard_offers[:TOP_N_STANDARD], start=1):
            results.append({**rec, "rank": rank})
        for rank, rec in enumerate(gr_offers[:TOP_N_GR], start=1):
            results.append({**rec, "rank": rank})

    return pd.DataFrame(results)


# ─── WRITE TO POSTGRES ────────────────────────────────────────────────────────

def write_scored_offers(results_df):
    if results_df.empty:
        print("⚠️  No scored offers to write.")
        return

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM c360_scored_offers WHERE model_type = 'rule_based';"))
        conn.commit()

    results_df["model_type"] = "rule_based"
    results_df["scored_at"] = pd.Timestamp.now()
    results_df.to_sql("c360_scored_offers", engine, if_exists="append", index=False,
                      method="multi", chunksize=500)
    print(f"✅ {len(results_df)} scored offers written to c360_scored_offers")


# ─── PUBLIC API (importable) ──────────────────────────────────────────────────

def score_for_household(household_id: str) -> list[dict]:
    """Score offers for a single household. Returns ranked list of dicts."""
    customers, offers, affinity, gr_history, freshpass_hhs = load_data()
    customers = customers[customers["household_id"] == household_id]
    if customers.empty:
        return []
    results = run_batch_scoring(customers, offers, affinity, gr_history, freshpass_hhs)
    return results.to_dict("records")


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Loading data from PostgreSQL...")
    customers, offers, affinity, gr_history, freshpass_hhs = load_data()
    print(f"   {len(customers)} head-of-household customers")
    print(f"   {len(offers)} active offers ({offers[offers.program_type == 'Grocery Reward'].shape[0]} Grocery Rewards)")
    print(f"   {len(affinity)} affinity rows across {affinity['household_id'].nunique()} households")

    print("\n⚙️  Scoring...")
    results_df = run_batch_scoring(customers, offers, affinity, gr_history, freshpass_hhs)
    print(f"   {len(results_df)} customer-offer pairs scored")

    write_scored_offers(results_df)

    print("\n📊 Sample — top 5 offers for first household:")
    sample_hh = results_df["household_id"].iloc[0]
    sample = results_df[results_df["household_id"] == sample_hh].sort_values("rank")
    print(sample[["rank", "offer_dsc", "delivery_channel_cd", "score",
                   "recency_boost_applied", "tier_multiplier_applied"]].to_string(index=False))
