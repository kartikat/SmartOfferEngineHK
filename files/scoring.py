"""
SmartRewards — Rule-Based Offer Scoring Engine
Scores and ranks offers for each customer based on weighted rules.
"""

import pandas as pd
import numpy as np


# ─── WEIGHTS ─────────────────────────────────────────────────────────────────
WEIGHTS = {
    "transaction_affinity": 0.30,
    "redemption_match":     0.25,
    "points_eligibility":   0.20,
    "cart_affinity":        0.15,
    "demographic_match":    0.10,
}

RECENCY_BOOST      = 1.20   # customer transacted within last 7 days
TIER_MULTIPLIER    = 1.50   # 4U+ customers on exclusive offers
TOP_N_OFFERS       = 3      # number of offers to return per customer


# ─── INDIVIDUAL SCORING RULES ────────────────────────────────────────────────

def score_transaction_affinity(customer: dict, offer: dict, affinity_lookup: dict) -> float:
    """
    How much does the customer historically spend in the offer's category?
    Returns a 0-1 affinity score from transaction history.
    """
    key = (customer["customer_id"], offer["category"])
    return affinity_lookup.get(key, 0.0)


def score_redemption_match(customer: dict, offer: dict) -> float:
    """
    Does the offer's redemption channel match the customer's primary channel?
    Full score for exact match, partial for 'Both', zero for mismatch.
    """
    primary = customer["primary_redemption_channel"]
    channel = offer["redemption_channel"]

    if channel == "Both":
        return 0.7
    elif channel == "eCommerce":
        # eCommerce offers are used to nudge Fuel redeemers online — give partial score
        if primary == "Fuel":
            return 0.6   # intentional nudge score
        return 0.9       # already an eCommerce user
    elif channel == primary:
        return 1.0
    else:
        return 0.1


def score_points_eligibility(customer: dict, offer: dict) -> float:
    """
    Does the customer have enough points to redeem this offer?
    Full score if eligible, zero if not.
    """
    return 1.0 if customer["points_balance"] >= offer["min_points_required"] else 0.0


def score_cart_affinity(customer: dict, offer: dict) -> float:
    """
    Proxy for browsing/cart behaviour — uses ecommerce_orders as a signal.
    Higher online activity = higher affinity for eCommerce offers.
    """
    orders = customer.get("ecommerce_orders", 0)
    max_orders = 5
    base = min(orders / max_orders, 1.0)

    if offer["redemption_channel"] == "eCommerce":
        return base
    else:
        return 1.0 - (base * 0.3)   # slight penalty for heavy online users on offline offers


def score_demographic_match(customer: dict, offer: dict) -> float:
    """
    Simple demographic fit heuristic.
    Can be extended with richer rules as data matures.
    """
    score = 0.5   # base score

    # Fuel offers skew toward older, high-frequency drivers
    if offer["category"] == "Fuel" and customer["age_group"] in ["35-44", "45-54", "55+"]:
        score += 0.3

    # Fresh/grocery offers skew toward families (broader age range)
    if offer["category"] in ["Grocery", "Produce", "Dairy"] and customer["age_group"] in ["25-34", "35-44"]:
        score += 0.3

    return min(score, 1.0)


# ─── COMPOSITE SCORER ────────────────────────────────────────────────────────

def score_offer(customer: dict, offer: dict, affinity_lookup: dict) -> dict:
    """
    Compute a composite relevance score for a customer-offer pair.
    Returns a score dict with component breakdown for explainability.
    """
    components = {
        "transaction_affinity": score_transaction_affinity(customer, offer, affinity_lookup),
        "redemption_match":     score_redemption_match(customer, offer),
        "points_eligibility":   score_points_eligibility(customer, offer),
        "cart_affinity":        score_cart_affinity(customer, offer),
        "demographic_match":    score_demographic_match(customer, offer),
    }

    # Weighted base score (0-100)
    base_score = sum(WEIGHTS[k] * v for k, v in components.items()) * 100

    # Apply multipliers
    if customer.get("days_since_last_txn", 99) <= 7:
        base_score *= RECENCY_BOOST

    if customer.get("tier") == "4U+" and offer.get("exclusive_4u_plus"):
        base_score *= TIER_MULTIPLIER

    final_score = round(min(base_score, 100), 2)

    return {
        "offer_id":     offer["offer_id"],
        "offer_name":   offer["offer_name"],
        "category":     offer["category"],
        "channel":      offer["redemption_channel"],
        "discount":     f"{offer['discount_value']}{offer['discount_type']}",
        "score":        final_score,
        "components":   {k: round(v, 3) for k, v in components.items()},
        "boosts_applied": {
            "recency_boost":    customer.get("days_since_last_txn", 99) <= 7,
            "tier_multiplier":  customer.get("tier") == "4U+" and offer.get("exclusive_4u_plus"),
        }
    }


# ─── RANK OFFERS FOR A SINGLE CUSTOMER ───────────────────────────────────────

def rank_offers_for_customer(customer: dict, offers_df: pd.DataFrame, affinity_lookup: dict, top_n: int = TOP_N_OFFERS) -> list:
    """
    Score all available offers for a customer and return the top N ranked.
    """
    scored = [score_offer(customer, offer, affinity_lookup) for offer in offers_df.to_dict("records")]
    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
    return ranked[:top_n]


# ─── BATCH SCORING ───────────────────────────────────────────────────────────

def run_batch_scoring(customers_df: pd.DataFrame, offers_df: pd.DataFrame, affinity_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run full batch scoring for all customers.
    Returns a flat DataFrame of top-N offers per customer.
    """
    # Build affinity lookup for fast access: {(customer_id, category): score}
    affinity_lookup = {
        (row["customer_id"], row["category"]): row["affinity_score"]
        for _, row in affinity_df.iterrows()
    }

    results = []
    for _, customer in customers_df.iterrows():
        customer_dict = customer.to_dict()
        ranked = rank_offers_for_customer(customer_dict, offers_df, affinity_lookup)
        for rank, rec in enumerate(ranked, start=1):
            results.append({
                "customer_id":   customer_dict["customer_id"],
                "tier":          customer_dict["tier"],
                "primary_channel": customer_dict["primary_redemption_channel"],
                "rank":          rank,
                **rec,
            })

    return pd.DataFrame(results)


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")

    print("Loading data...")
    customers_df  = pd.read_csv(f"{DATA_DIR}/customers.csv")
    offers_df     = pd.read_csv(f"{DATA_DIR}/offers.csv")
    affinity_df   = pd.read_csv(f"{DATA_DIR}/category_affinity.csv")

    print(f"Scoring {len(customers_df)} customers against {len(offers_df)} offers...")
    results_df = run_batch_scoring(customers_df, offers_df, affinity_df)

    output_path = f"{DATA_DIR}/scored_offers.csv"
    results_df.to_csv(output_path, index=False)

    print(f"\n✅ Batch scoring complete — {len(results_df)} records written to {output_path}")
    print("\nSample output (first customer):")
    first = results_df[results_df["customer_id"] == results_df["customer_id"].iloc[0]]
    print(first[["customer_id", "tier", "rank", "offer_name", "category", "channel", "score"]].to_string(index=False))
