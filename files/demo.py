"""
SmartOfferEngine — End-to-End Demo Runner
Run this to see the full pipeline in action without needing FastAPI.
Usage: python demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.generate_data import (
    generate_customers, generate_transactions,
    generate_offers, compute_category_affinity
)
from engine.scoring import rank_offers_for_customer, run_batch_scoring

# ─── COLOURS FOR TERMINAL OUTPUT ─────────────────────────────────────────────
GOLD  = "\033[93m"
TEAL  = "\033[96m"
GREEN = "\033[92m"
BOLD  = "\033[1m"
RESET = "\033[0m"
DIM   = "\033[2m"


def banner(text):
    print(f"\n{BOLD}{GOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}{GOLD}  {text}{RESET}")
    print(f"{BOLD}{GOLD}{'─' * 60}{RESET}")


def section(text):
    print(f"\n{TEAL}{BOLD}{text}{RESET}")
    print(f"{DIM}{'─' * 40}{RESET}")


# ─── MAIN DEMO ───────────────────────────────────────────────────────────────

def run_demo():
    banner("SmartOfferEngine — AI Powered Personalised Offer Engine")

    # Step 1: Generate data
    section("STEP 1 — Generating Synthetic Data")
    customers_df    = generate_customers(500)
    transactions_df = generate_transactions(customers_df)
    offers_df       = generate_offers(20)
    affinity_df     = compute_category_affinity(transactions_df)

    print(f"  ✅ {len(customers_df)} customers")
    print(f"  ✅ {len(transactions_df)} transactions")
    print(f"  ✅ {len(offers_df)} available offers")

    # Build affinity lookup
    affinity_lookup = {
        (row["customer_id"], row["category"]): row["affinity_score"]
        for _, row in affinity_df.iterrows()
    }

    # Step 2: Show customer segments
    section("STEP 2 — Customer Segments")

    fuel_redeemers = customers_df[customers_df["primary_redemption_channel"] == "Fuel"]
    premium        = customers_df[customers_df["tier"] == "4U+"]
    high_points    = customers_df[customers_df["points_balance"] >= 1000]

    print(f"  ⛽  Fuel Redeemers:           {len(fuel_redeemers):>4} customers")
    print(f"  ★   4U+ Subscribers:          {len(premium):>4} customers")
    print(f"  ⭐  High Points (1000+):       {len(high_points):>4} customers")
    print(f"  📦  Total:                     {len(customers_df):>4} customers")

    # Step 3: Score a Fuel Redeemer — show eCommerce nudge
    section("STEP 3 — Demo: Fuel Redeemer → eCommerce Nudge")

    fuel_customer = fuel_redeemers.iloc[0].to_dict()
    print(f"\n  Customer:  {fuel_customer['customer_id']}")
    print(f"  Tier:      {fuel_customer['tier']}")
    print(f"  Channel:   {fuel_customer['primary_redemption_channel']} (offline)")
    print(f"  Points:    {fuel_customer['points_balance']}")
    print(f"  Last txn:  {fuel_customer['days_since_last_txn']} days ago")

    ranked = rank_offers_for_customer(fuel_customer, offers_df, affinity_lookup, top_n=3)
    print(f"\n  {GOLD}Top 3 Personalised Offers:{RESET}")
    for r in ranked:
        channel_tag = f"{TEAL}[eCommerce]{RESET}" if r["channel"] == "eCommerce" else f"[{r['channel']}]"
        print(f"    #{r['offer_id']} {r['offer_name']:30s} Score: {GOLD}{r['score']:5.1f}{RESET}  {channel_tag}")
        for comp, val in r["components"].items():
            print(f"       {DIM}{comp:30s} {val:.3f}{RESET}")

    # Step 4: Score a 4U+ subscriber
    section("STEP 4 — Demo: 4U+ Subscriber with Tier Multiplier")

    premium_customer = premium.iloc[0].to_dict()
    print(f"\n  Customer:  {premium_customer['customer_id']}")
    print(f"  Tier:      {GOLD}4U+{RESET} (tier multiplier active)")
    print(f"  Channel:   {premium_customer['primary_redemption_channel']}")
    print(f"  Points:    {premium_customer['points_balance']}")

    ranked_4u = rank_offers_for_customer(premium_customer, offers_df, affinity_lookup, top_n=3)
    print(f"\n  {GOLD}Top 3 Personalised Offers:{RESET}")
    for r in ranked_4u:
        boosts = []
        if r["boosts_applied"]["tier_multiplier"]:
            boosts.append(f"{GOLD}4U+ boost{RESET}")
        if r["boosts_applied"]["recency_boost"]:
            boosts.append(f"{TEAL}recency boost{RESET}")
        boost_str = f"  ← {', '.join(boosts)}" if boosts else ""
        print(f"    #{r['offer_id']} {r['offer_name']:30s} Score: {GOLD}{r['score']:5.1f}{RESET}{boost_str}")

    # Step 5: Batch scoring
    section("STEP 5 — Batch Scoring All Customers")

    print("  Running batch scoring...")
    results_df = run_batch_scoring(customers_df, offers_df, affinity_df)

    # Save results
    os.makedirs("data", exist_ok=True)
    results_df.to_csv("data/scored_offers.csv", index=False)
    customers_df.to_csv("data/customers.csv", index=False)
    offers_df.to_csv("data/offers.csv", index=False)
    affinity_df.to_csv("data/category_affinity.csv", index=False)

    print(f"  ✅ {len(results_df)} offer recommendations generated")
    print(f"  ✅ Results saved to data/scored_offers.csv")

    # Summary stats
    section("STEP 6 — Summary Statistics")

    avg_score = results_df["score"].mean()
    top_channel = results_df[results_df["rank"] == 1]["channel"].value_counts().idxmax()
    ecom_nudges = results_df[
        (results_df["channel"] == "eCommerce") &
        (results_df["primary_channel"] == "Fuel") &
        (results_df["rank"] == 1)
    ]

    print(f"  Average offer score:          {avg_score:.1f}")
    print(f"  Most recommended channel:     {top_channel}")
    print(f"  Fuel → eCommerce nudges:      {len(ecom_nudges)} customers")
    print(f"  Data files ready for API:     data/")

    banner("Demo Complete — Ready to Serve via API")
    print(f"\n  To start the API server:")
    print(f"  {TEAL}pip install fastapi uvicorn{RESET}")
    print(f"  {TEAL}uvicorn api.main:app --reload --port 8000{RESET}")
    print(f"\n  API endpoints:")
    print(f"  {GOLD}GET /offers/{{customer_id}}{RESET}         → Top N personalised offers")
    print(f"  {GOLD}GET /segments/fuel-redeemers{RESET}    → Fuel redeemer segment")
    print(f"  {GOLD}GET /segments/4uplus{RESET}            → 4U+ subscriber segment")
    print(f"  {GOLD}GET /customer/{{customer_id}}/profile{RESET} → Customer profile")
    print(f"  {GOLD}GET /docs{RESET}                       → Interactive API docs\n")


if __name__ == "__main__":
    run_demo()
