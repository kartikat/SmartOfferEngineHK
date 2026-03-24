"""
SmartOfferEngine — Synthetic Data Generator
Generates mock customers, transactions, and offers for demo/hackathon use.
"""

import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.dirname(__file__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
N_CUSTOMERS = 500
N_TRANSACTIONS_PER_CUSTOMER = (5, 30)
N_OFFERS = 20

CATEGORIES = ["Fuel", "Grocery", "Bakery", "Dairy", "Beverages", "Snacks", "Produce", "Household"]
TIERS = ["Standard", "Standard", "Standard", "4U+"]  # weighted — more standard
REDEMPTION_CHANNELS = ["Fuel", "Grocery"]
GENDERS = ["M", "F", "Other"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]


# ─── GENERATE CUSTOMERS ───────────────────────────────────────────────────────
def generate_customers(n):
    customers = []
    for i in range(n):
        tier = random.choice(TIERS)
        primary_channel = random.choice(REDEMPTION_CHANNELS)
        points = random.randint(0, 5000)
        days_since_last_txn = random.randint(0, 90)

        customers.append({
            "customer_id": f"CUST{i+1:04d}",
            "age_group": random.choice(AGE_GROUPS),
            "gender": random.choice(GENDERS),
            "tier": tier,
            "points_balance": points,
            "primary_redemption_channel": primary_channel,
            "days_since_last_txn": days_since_last_txn,
            "total_transactions": random.randint(*N_TRANSACTIONS_PER_CUSTOMER),
            "ecommerce_orders": random.randint(0, 5) if primary_channel == "Grocery" else 0,
            "registered_months": random.randint(1, 60),
        })
    return pd.DataFrame(customers)


# ─── GENERATE TRANSACTION HISTORY (category affinity) ─────────────────────────
def generate_transactions(customers_df):
    transactions = []
    for _, cust in customers_df.iterrows():
        n_txns = cust["total_transactions"]
        primary = cust["primary_redemption_channel"]

        # Bias category spend toward primary channel
        weights = []
        for cat in CATEGORIES:
            if primary == "Fuel" and cat == "Fuel":
                weights.append(5)
            elif primary == "Grocery" and cat in ["Grocery", "Bakery", "Dairy", "Produce"]:
                weights.append(4)
            else:
                weights.append(1)

        total_w = sum(weights)
        probs = [w / total_w for w in weights]

        for _ in range(n_txns):
            category = np.random.choice(CATEGORIES, p=probs)
            days_ago = random.randint(0, 365)
            transactions.append({
                "customer_id": cust["customer_id"],
                "category": category,
                "amount": round(random.uniform(5, 150), 2),
                "date": (datetime.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "channel": random.choice(["in-store", "online"]),
            })
    return pd.DataFrame(transactions)


# ─── GENERATE OFFERS ─────────────────────────────────────────────────────────
def generate_offers(n):
    offers = []
    for i in range(n):
        category = random.choice(CATEGORIES)
        channel = "Fuel" if category == "Fuel" else random.choice(["Grocery", "eCommerce", "Both"])
        min_points = random.choice([0, 100, 200, 500, 1000])
        exclusive_4u = random.random() < 0.25  # 25% are 4U+ exclusive

        offers.append({
            "offer_id": f"OFFER{i+1:03d}",
            "offer_name": f"{category} Reward #{i+1}",
            "category": category,
            "redemption_channel": channel,
            "discount_type": random.choice(["% off", "$ off", "Free item", "Fuel cents/L"]),
            "discount_value": random.choice([5, 10, 15, 20, 25, 50]),
            "min_points_required": min_points,
            "exclusive_4u_plus": exclusive_4u,
            "valid_days": random.randint(7, 30),
        })
    return pd.DataFrame(offers)


# ─── GENERATE CATEGORY AFFINITY ──────────────────────────────────────────────
def compute_category_affinity(transactions_df):
    """For each customer, compute spend proportion per category."""
    affinity = (
        transactions_df.groupby(["customer_id", "category"])["amount"]
        .sum()
        .reset_index()
    )
    total = transactions_df.groupby("customer_id")["amount"].sum().reset_index()
    total.columns = ["customer_id", "total_spend"]
    affinity = affinity.merge(total, on="customer_id")
    affinity["affinity_score"] = affinity["amount"] / affinity["total_spend"]
    return affinity[["customer_id", "category", "affinity_score"]]


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating synthetic data...")

    customers_df = generate_customers(N_CUSTOMERS)
    transactions_df = generate_transactions(customers_df)
    offers_df = generate_offers(N_OFFERS)
    affinity_df = compute_category_affinity(transactions_df)

    customers_df.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
    transactions_df.to_csv(f"{OUTPUT_DIR}/transactions.csv", index=False)
    offers_df.to_csv(f"{OUTPUT_DIR}/offers.csv", index=False)
    affinity_df.to_csv(f"{OUTPUT_DIR}/category_affinity.csv", index=False)

    print(f"✅ {len(customers_df)} customers generated")
    print(f"✅ {len(transactions_df)} transactions generated")
    print(f"✅ {len(offers_df)} offers generated")
    print(f"✅ Category affinity table computed")
    print(f"\nFiles saved to: {OUTPUT_DIR}")
