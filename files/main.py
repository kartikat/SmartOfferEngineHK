"""
SmartRewards — REST API
Serves pre-scored personalized offers per customer.
Install: pip install fastapi uvicorn pandas
Run:     uvicorn api.main:app --reload --port 8000
Docs:    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import os
import json

# ─── SETUP ───────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")

app = FastAPI(
    title="SmartRewards API",
    description="Personalized offer recommendations for loyalty customers",
    version="1.0.0",
)

# Load data at startup
customers_df = None
scored_df    = None
offers_df    = None


@app.on_event("startup")
def load_data():
    global customers_df, scored_df, offers_df
    try:
        customers_df = pd.read_csv(f"{DATA_DIR}/customers.csv")
        scored_df    = pd.read_csv(f"{DATA_DIR}/scored_offers.csv")
        offers_df    = pd.read_csv(f"{DATA_DIR}/offers.csv")
        print(f"✅ Loaded {len(customers_df)} customers, {len(scored_df)} scored offers")
    except FileNotFoundError as e:
        print(f"⚠️  Data files not found: {e}")
        print("   Run: python data/generate_data.py && python engine/scoring.py first")


# ─── RESPONSE MODELS ─────────────────────────────────────────────────────────

class ScoreComponents(BaseModel):
    transaction_affinity: float
    redemption_match:     float
    points_eligibility:   float
    cart_affinity:        float
    demographic_match:    float


class OfferRecommendation(BaseModel):
    rank:          int
    offer_id:      str
    offer_name:    str
    category:      str
    channel:       str
    discount:      str
    score:         float


class CustomerRecommendations(BaseModel):
    customer_id:     str
    tier:            str
    primary_channel: str
    offers:          List[OfferRecommendation]
    scored_at:       str


class CustomerProfile(BaseModel):
    customer_id:                str
    tier:                       str
    points_balance:             int
    primary_redemption_channel: str
    days_since_last_txn:        int
    ecommerce_orders:           int
    age_group:                  str


# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "SmartRewards API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "customers_loaded": len(customers_df) if customers_df is not None else 0,
        "offers_loaded":    len(offers_df) if offers_df is not None else 0,
    }


@app.get("/offers/{customer_id}", response_model=CustomerRecommendations, tags=["Recommendations"])
def get_offers(
    customer_id: str,
    top_n: int = Query(default=3, ge=1, le=10, description="Number of offers to return"),
    channel: Optional[str] = Query(default=None, description="Filter by channel: Fuel, Grocery, eCommerce"),
):
    """
    Get personalised ranked offers for a customer.
    Returns top N pre-scored offers, optionally filtered by redemption channel.
    """
    if scored_df is None:
        raise HTTPException(status_code=503, detail="Scoring data not loaded. Run batch scoring first.")

    # Check customer exists
    customer_row = customers_df[customers_df["customer_id"] == customer_id]
    if customer_row.empty:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    customer = customer_row.iloc[0].to_dict()

    # Get pre-scored offers
    customer_offers = scored_df[scored_df["customer_id"] == customer_id].copy()

    if customer_offers.empty:
        raise HTTPException(status_code=404, detail=f"No scored offers found for {customer_id}")

    # Optional channel filter
    if channel:
        customer_offers = customer_offers[
            customer_offers["channel"].str.lower() == channel.lower()
        ]

    # Sort and take top N
    customer_offers = customer_offers.sort_values("score", ascending=False).head(top_n)

    offers = [
        OfferRecommendation(
            rank=int(row["rank"]),
            offer_id=str(row["offer_id"]),
            offer_name=str(row["offer_name"]),
            category=str(row["category"]),
            channel=str(row["channel"]),
            discount=str(row["discount"]),
            score=float(row["score"]),
        )
        for _, row in customer_offers.iterrows()
    ]

    return CustomerRecommendations(
        customer_id=customer_id,
        tier=str(customer["tier"]),
        primary_channel=str(customer["primary_redemption_channel"]),
        offers=offers,
        scored_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.get("/customer/{customer_id}/profile", response_model=CustomerProfile, tags=["Customers"])
def get_customer_profile(customer_id: str):
    """
    Get a customer's profile and loyalty attributes.
    """
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    row = customers_df[customers_df["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    c = row.iloc[0].to_dict()
    return CustomerProfile(
        customer_id=c["customer_id"],
        tier=c["tier"],
        points_balance=int(c["points_balance"]),
        primary_redemption_channel=c["primary_redemption_channel"],
        days_since_last_txn=int(c["days_since_last_txn"]),
        ecommerce_orders=int(c["ecommerce_orders"]),
        age_group=c["age_group"],
    )


@app.get("/segments/fuel-redeemers", tags=["Segments"])
def get_fuel_redeemers(
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Return customers identified as Fuel-only redeemers —
    primary candidates to be nudged toward eCommerce.
    """
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    fuel_customers = customers_df[
        customers_df["primary_redemption_channel"] == "Fuel"
    ].head(limit)

    return {
        "segment": "Fuel Redeemers",
        "count": len(fuel_customers),
        "customers": fuel_customers[["customer_id", "tier", "points_balance", "days_since_last_txn"]].to_dict("records")
    }


@app.get("/segments/4uplus", tags=["Segments"])
def get_4uplus_customers(
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Return 4U+ high-tier subscribers — initial target segment for SmartRewards.
    """
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    premium = customers_df[customers_df["tier"] == "4U+"].head(limit)

    return {
        "segment": "4U+ Subscribers",
        "count": len(premium),
        "customers": premium[["customer_id", "points_balance", "primary_redemption_channel", "days_since_last_txn"]].to_dict("records")
    }


@app.get("/offers", tags=["Offers"])
def list_offers(
    channel: Optional[str] = None,
    exclusive_4u: Optional[bool] = None,
):
    """
    List all available offers, with optional filters.
    """
    if offers_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    filtered = offers_df.copy()
    if channel:
        filtered = filtered[filtered["redemption_channel"].str.lower() == channel.lower()]
    if exclusive_4u is not None:
        filtered = filtered[filtered["exclusive_4u_plus"] == exclusive_4u]

    return {
        "count": len(filtered),
        "offers": filtered.to_dict("records")
    }
