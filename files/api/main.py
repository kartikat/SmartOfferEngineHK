"""
SmartOfferEngine — REST API (PostgreSQL)
Serves pre-scored personalised offers per customer from c360_scored_offers.

Run:  uvicorn files.api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
engine = create_engine(DB_URL, pool_pre_ping=True)

app = FastAPI(
    title="SmartOfferEngine API",
    description="Personalised offer recommendations for Albertsons loyalty customers",
    version="2.0.0",
)


def query(sql: str, params: dict = None) -> list[dict]:
    """Run a SQL query and return rows as list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


# ─── RESPONSE MODELS ──────────────────────────────────────────────────────────

class OfferRecommendation(BaseModel):
    rank:                    int
    client_offer_id:         str
    offer_dsc:               str
    delivery_channel_cd:     str
    discount_value:          Optional[float]
    discount_type_cd:        Optional[str]
    score:                   float
    transaction_affinity:    float
    redemption_match:        float
    points_eligibility:      float
    cart_affinity:           float
    demographic_match:       float
    recency_boost_applied:   bool
    tier_multiplier_applied: bool


class CustomerRecommendations(BaseModel):
    household_id:   str
    tier:           str
    fav_channel:    str
    points_balance: int
    offers:         List[OfferRecommendation]


class CustomerProfile(BaseModel):
    retail_customer_uuid:      str
    household_id:              str
    clv_tier_level_id:         str
    current_point_balance:     int
    points_expiring_next_month: int
    fav_channel:               str
    eng_mode_p6m:              Optional[str]
    days_since_last_txn:       Optional[int]
    customer_age:              Optional[str]
    churn_risk_score_nbr:      Optional[float]
    churn_segment_cd:          Optional[str]


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"service": "SmartOfferEngine API", "version": "2.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    rows = query("""
        SELECT
            (SELECT COUNT(*) FROM c360_customer_profile) AS customers,
            (SELECT COUNT(*) FROM c360_scored_offers)    AS scored_offers,
            (SELECT COUNT(*) FROM c360_offer WHERE offer_status_cd = 'ACTIVE') AS active_offers,
            (SELECT MAX(scored_at) FROM c360_scored_offers) AS last_scored_at
    """)
    return {"status": "ok", **rows[0]}


# ─── RECOMMENDATIONS ──────────────────────────────────────────────────────────

@app.get("/offers/{household_id}", response_model=CustomerRecommendations, tags=["Recommendations"])
def get_offers(
    household_id: str,
    top_n: int = Query(default=5, ge=1, le=10, description="Number of offers to return"),
    channel: Optional[str] = Query(default=None, description="Filter by delivery_channel_cd (J4U, Weekly Ad, Auto Clip)"),
):
    """
    Get personalised ranked offers for a household from c360_scored_offers.
    """
    # Fetch customer profile
    profile = query("""
        SELECT
            retail_customer_uuid, household_id, clv_tier_level_id,
            current_point_balance, fav_channel
        FROM c360_customer_profile
        WHERE household_id = :hh AND head_household_ind = TRUE
        LIMIT 1
    """, {"hh": household_id})

    if not profile:
        raise HTTPException(status_code=404, detail=f"Household {household_id} not found")

    cust = profile[0]

    # Fetch pre-scored offers
    channel_filter = "AND so.delivery_channel_cd = :channel" if channel else ""
    offers = query(f"""
        SELECT
            so.rank, so.client_offer_id, so.offer_dsc,
            so.delivery_channel_cd, so.discount_value, so.discount_type_cd,
            so.score,
            COALESCE(so.transaction_affinity, 0)  AS transaction_affinity,
            COALESCE(so.redemption_match, 0)       AS redemption_match,
            COALESCE(so.points_eligibility, 0)     AS points_eligibility,
            COALESCE(so.cart_affinity, 0)          AS cart_affinity,
            COALESCE(so.demographic_match, 0)      AS demographic_match,
            COALESCE(so.recency_boost_applied, FALSE)   AS recency_boost_applied,
            COALESCE(so.tier_multiplier_applied, FALSE) AS tier_multiplier_applied
        FROM c360_scored_offers so
        WHERE so.household_id = :hh
        {channel_filter}
        ORDER BY so.rank
        LIMIT :top_n
    """, {"hh": household_id, "channel": channel, "top_n": top_n})

    if not offers:
        raise HTTPException(status_code=404, detail=f"No scored offers found for household {household_id}")

    return CustomerRecommendations(
        household_id=cust["household_id"],
        tier=cust["clv_tier_level_id"],
        fav_channel=cust["fav_channel"],
        points_balance=cust["current_point_balance"],
        offers=[OfferRecommendation(**o) for o in offers],
    )


# ─── CUSTOMER ─────────────────────────────────────────────────────────────────

@app.get("/customer/{household_id}", response_model=CustomerProfile, tags=["Customers"])
def get_customer(household_id: str):
    """Customer profile with loyalty attributes and derived days_since_last_txn."""
    rows = query("""
        SELECT
            cp.retail_customer_uuid,
            cp.household_id,
            cp.clv_tier_level_id,
            cp.current_point_balance,
            COALESCE(cp.points_expiring_next_month, 0) AS points_expiring_next_month,
            cp.fav_channel,
            cp.eng_mode_p6m,
            (CURRENT_DATE - MAX(t.txn_dte))::int       AS days_since_last_txn,
            cp.customer_age,
            cp.churn_risk_score_nbr,
            cp.churn_segment_cd
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.household_id = :hh AND cp.head_household_ind = TRUE
        GROUP BY
            cp.retail_customer_uuid, cp.household_id, cp.clv_tier_level_id,
            cp.current_point_balance, cp.points_expiring_next_month,
            cp.fav_channel, cp.eng_mode_p6m, cp.customer_age,
            cp.churn_risk_score_nbr, cp.churn_segment_cd
        LIMIT 1
    """, {"hh": household_id})

    if not rows:
        raise HTTPException(status_code=404, detail=f"Household {household_id} not found")
    return CustomerProfile(**rows[0])


@app.post("/clip/{household_id}/{offer_id}", tags=["Actions"])
def clip_offer(household_id: str, offer_id: str):
    """Record a clip event for a household-offer pair."""
    import uuid
    from datetime import datetime

    # Verify offer exists
    offer = query("SELECT client_offer_id, oms_offer_id, incentive_id, offer_type FROM c360_offer WHERE client_offer_id = :oid",
                  {"oid": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

    cust = query("""
        SELECT retail_customer_uuid, club_card_nbr, customer_most_used_store_id
        FROM c360_customer_profile
        WHERE household_id = :hh AND head_household_ind = TRUE LIMIT 1
    """, {"hh": household_id})
    if not cust:
        raise HTTPException(status_code=404, detail=f"Household {household_id} not found")

    o = offer[0]
    c = cust[0]
    clip_id = f"CLIP-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now()

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO c360_clips (
                clip_id, client_offer_id, oms_offer_id, incentive_id,
                household_id, retail_customer_uuid, card_nbr,
                clip_ts, clip_dt, clip_source_cd, mobile_ind, offer_type,
                dw_create_ts, dw_last_update_ts
            ) VALUES (
                :clip_id, :offer_id, :oms_offer_id, :incentive_id,
                :hh, :uuid, :card_nbr,
                :now, :today, 'API', FALSE, :offer_type,
                :now, :now
            )
            ON CONFLICT DO NOTHING
        """), {
            "clip_id": clip_id, "offer_id": offer_id,
            "oms_offer_id": o["oms_offer_id"], "incentive_id": o["incentive_id"],
            "hh": household_id, "uuid": c["retail_customer_uuid"],
            "card_nbr": c["club_card_nbr"],
            "now": now, "today": now.date(), "offer_type": o["offer_type"],
        })
        conn.commit()

    return {"status": "clipped", "clip_id": clip_id, "household_id": household_id, "offer_id": offer_id}


# ─── OFFERS CATALOG ───────────────────────────────────────────────────────────

@app.get("/offers", tags=["Offers"])
def list_offers(
    channel: Optional[str] = None,
    exclusive_4u: Optional[bool] = None,
    program_type: Optional[str] = None,
):
    """List active offers from the catalog with optional filters."""
    filters = ["offer_status_cd = 'ACTIVE'", "dw_logical_delete_ind = FALSE"]
    params = {}

    if channel:
        filters.append("delivery_channel_cd = :channel")
        params["channel"] = channel
    if exclusive_4u is not None:
        filters.append("is_appliable_to_j4u_ind = :excl")
        params["excl"] = exclusive_4u
    if program_type:
        filters.append("program_type = :pt")
        params["pt"] = program_type

    where = " AND ".join(filters)
    rows = query(f"""
        SELECT client_offer_id, offer_dsc, delivery_channel_cd, program_type,
               discount_type_cd, discount_value, target_level_cd,
               is_appliable_to_j4u_ind, is_freshpass_offer_ind, is_in_weekly_ad
        FROM c360_offer
        WHERE {where}
        ORDER BY client_offer_id
    """, params)

    return {"count": len(rows), "offers": rows}


# ─── SEGMENTS ─────────────────────────────────────────────────────────────────

@app.get("/segments", tags=["Segments"])
def segments_summary():
    """High-level segment breakdown across all customers."""
    rows = query("""
        SELECT
            clv_tier_level_id                                       AS tier,
            COUNT(DISTINCT household_id)                            AS households,
            ROUND(AVG(current_point_balance))                       AS avg_points,
            COUNT(*) FILTER (WHERE gas_rewards_ind_6m)             AS fuel_redeemers,
            COUNT(*) FILTER (WHERE eng_mode_p6m = 'eCommerce')     AS ecommerce_only,
            COUNT(*) FILTER (WHERE eng_mode_p6m = 'Both')          AS omnichannel,
            COUNT(*) FILTER (WHERE churn_segment_cd = 'High Risk') AS high_churn_risk
        FROM c360_customer_profile
        WHERE head_household_ind = TRUE
        GROUP BY clv_tier_level_id
        ORDER BY tier
    """)
    return {"segments": rows}


@app.get("/segments/fuel-redeemers", tags=["Segments"])
def fuel_redeemers(limit: int = Query(default=20, ge=1, le=100)):
    """Fuel-primary customers — candidates for eCommerce migration nudge."""
    rows = query("""
        SELECT
            cp.household_id, cp.clv_tier_level_id AS tier,
            cp.current_point_balance,
            cp.fav_channel,
            (CURRENT_DATE - MAX(t.txn_dte))::int AS days_since_last_txn
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.gas_rewards_ind_6m = TRUE
          AND cp.head_household_ind = TRUE
        GROUP BY cp.household_id, cp.clv_tier_level_id,
                 cp.current_point_balance, cp.fav_channel
        ORDER BY cp.current_point_balance DESC
        LIMIT :lim
    """, {"lim": limit})
    return {"segment": "Fuel Redeemers", "count": len(rows), "customers": rows}


@app.get("/segments/4uplus", tags=["Segments"])
def four_u_plus(limit: int = Query(default=20, ge=1, le=100)):
    """4U+ premium tier customers — highest-value segment."""
    rows = query("""
        SELECT
            cp.household_id, cp.current_point_balance,
            cp.fav_channel, cp.eng_mode_p6m,
            cp.churn_risk_score_nbr,
            (CURRENT_DATE - MAX(t.txn_dte))::int AS days_since_last_txn
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.clv_tier_level_id = '4U+'
          AND cp.head_household_ind = TRUE
        GROUP BY cp.household_id, cp.current_point_balance,
                 cp.fav_channel, cp.eng_mode_p6m, cp.churn_risk_score_nbr
        ORDER BY cp.current_point_balance DESC
        LIMIT :lim
    """, {"lim": limit})
    return {"segment": "4U+ Subscribers", "count": len(rows), "customers": rows}


@app.get("/segments/high-churn", tags=["Segments"])
def high_churn(limit: int = Query(default=20, ge=1, le=100)):
    """High churn-risk customers — candidates for reactivation offers."""
    rows = query("""
        SELECT
            cp.household_id, cp.clv_tier_level_id AS tier,
            cp.current_point_balance, cp.churn_risk_score_nbr,
            (CURRENT_DATE - MAX(t.txn_dte))::int AS days_since_last_txn
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.churn_segment_cd = 'High Risk'
          AND cp.head_household_ind = TRUE
        GROUP BY cp.household_id, cp.clv_tier_level_id,
                 cp.current_point_balance, cp.churn_risk_score_nbr
        ORDER BY cp.churn_risk_score_nbr DESC
        LIMIT :lim
    """, {"lim": limit})
    return {"segment": "High Churn Risk", "count": len(rows), "customers": rows}
