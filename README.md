# SmartRewards

**AI-powered personalised loyalty offer engine for the Albertsons *for U* program.**

SmartRewards scores every active offer against every loyalty household and returns a ranked list of the most relevant offers per customer. It mirrors the Albertsons C360 BigQuery data model locally in PostgreSQL and serves results via a FastAPI REST API and an interactive Streamlit demo UI.

---

## What It Does

- **Scores** every customer–offer pair using a weighted rule engine (5 rules, 2 scoring paths)
- **Ranks** offers per household and writes results to `c360_scored_offers`
- **Serves** ranked offers via a REST API
- **Demos** personalisation through an interactive Streamlit UI with login, offer cards, clip/unclip, segment explorer, and a guided demo script

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│           PostgreSQL 16 — smartrewards DB             │
│       18 tables mirroring Albertsons C360 schema      │
└──────────┬───────────────────────┬───────────────────┘
           │                       │
           ▼                       ▼
  ┌─────────────────┐    ┌──────────────────────────┐
  │  scoring.py     │    │  FastAPI  (port 8000)     │
  │  Batch scores   │───▶│  REST API                 │
  │  all households │    │  /offers/{household_id}   │
  └─────────────────┘    └─────────────┬────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │  Streamlit  (port 8501) │
                          │  Demo UI                │
                          └────────────────────────┘
```

**Data flow:**
1. `generate_data.py` — seeds all 18 PostgreSQL tables (real Safeway UPCs + synthetic)
2. `scoring.py` — reads C360 tables, writes `c360_scored_offers`
3. `main.py` — FastAPI reads `c360_scored_offers`, serves ranked offers
4. `app.py` — Streamlit reads directly from PostgreSQL

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16

```bash
# macOS (Homebrew)
brew install postgresql@16
brew services start postgresql@16
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create the database

```bash
createdb smartrewards
psql -d smartrewards -f files/db/schema.sql
```

### 3. Seed the database

```bash
python3 files/data/generate_data.py
```

Generates and loads:
- 12 stores across 5 divisions (Safeway, Vons, Albertsons, Tom Thumb)
- 51 products — 30 real Safeway UPCs (Dairy) + 21 synthetic across 7 departments
- 26 offers — 6 real Safeway offers + 20 synthetic (including Grocery Rewards and Fuel)
- 300 customers across 120 households with correlated transaction history
- All derived tables: category affinity, LTV aggregates, clip/redemption events

### 4. Score all households

```bash
python3 files/engine/scoring.py
```

Produces 1,200 scored offers (120 households × 10 offers each) in `c360_scored_offers`.

### 5. Start the services

```bash
# API
uvicorn files.api.main:app --reload --port 8000

# Demo UI (in a separate terminal)
streamlit run files/app.py --server.headless true
```

| Service | URL |
|---|---|
| Streamlit Demo | http://localhost:8501 |
| FastAPI | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## Configuration

All components read the database URL from an environment variable:

```bash
export DATABASE_URL="postgresql://localhost/smartrewards"
```

Defaults to `postgresql://localhost/smartrewards` if not set.

---

## Scoring Model

### Path 1 — Standard Offers

Five weighted rules produce a base score (0–100):

| Rule | Weight | Data Signal |
|---|---|---|
| Transaction Affinity | 30% | `c360_cat_affinity.affinity_score` — historical spend in offer's category |
| Redemption Match | 25% | `fav_channel` vs `delivery_channel_cd` |
| Points Eligibility | 20% | `current_point_balance` |
| Cart & Browse Affinity | 15% | `doordash_txn_ind_6m`, `instacart_txn_ind_6m`, `uber_txn_ind_6m` |
| Demographic Match | 10% | `customer_age`, `num_of_children`, `diet_preference` |

**Multipliers applied after weighted sum:**

| Multiplier | Factor | Condition |
|---|---|---|
| Recency Boost | ×1.2 | `days_since_last_txn ≤ 7` |
| Tier Multiplier | ×1.5 | `clv_tier_level_id = '4U+'` AND `is_appliable_to_j4u_ind = TRUE` |

Score capped at 100.

### Path 2 — Grocery Reward Offers

Customers *spend* accumulated points for a dollar discount. Separate scoring path:

1. **Hard gate** — excluded if `current_point_balance < tier_1_points_threshold`
2. **Weighted score** — points eligibility (40%), category affinity (25%), value per point (15%), redemption history (15%), recency (5%)
3. **Expiry multiplier** — ×1.3 if points are expiring next month

### Business Rules

- **FreshPass filter** — `is_freshpass_offer_ind = TRUE` offers only shown to active FreshPass subscribers
- **4U+ filter** — `is_appliable_to_j4u_ind = TRUE` offers only shown to `clv_tier_level_id = '4U+'` households
- **eCommerce nudge** — Fuel redeemers receive a partial channel match score on J4U digital offers, intentionally surfacing online offers to offline loyalists

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB row counts + last scored timestamp |
| GET | `/offers/{household_id}` | Top N ranked offers for a household |
| GET | `/customer/{household_id}` | Customer profile with live `days_since_last_txn` |
| POST | `/clip/{household_id}/{offer_id}` | Record a clip event to `c360_clips` |
| GET | `/offers` | Offer catalog (filter by channel, program_type, exclusive_4u) |
| GET | `/segments` | Tier-level segment summary |
| GET | `/segments/fuel-redeemers` | Households with `gas_rewards_ind_6m = TRUE` |
| GET | `/segments/4uplus` | Premium tier households |
| GET | `/segments/high-churn` | High churn risk households |

Full interactive docs at `http://localhost:8000/docs`.

---

## Demo UI — Pages

| Page | Description |
|---|---|
| **Login** | Select a household to sign in |
| **My Offers** | Ranked offer cards with score bar, clip/unclip, score breakdown toggle |
| **My Clipped Offers** | Active clips — all will apply at checkout |
| **My Profile** | Points balance, tier, channel, engagement mode, expiring points alert |
| **Segment Explorer** | 5 segments with drilldown table and jump-to-customer |
| **Compare Customers** | Side-by-side profiles + offers + score distribution chart |
| **How Offers Are Scored** | Visual breakdown of all 5 rules, multipliers, and business rules |
| **Demo Script** | 7-step guided walkthrough with narration panels |

---

## Database — 18 C360 Tables

Mirrors the Albertsons C360 BigQuery schema (`gcp-abs-udco-bqvw-prod-prj-01.udco_ds_cust`). Field names are preserved exactly from the source.

| # | Table | Purpose |
|---|---|---|
| 1 | `c360_store` | Store catalog — location, capabilities |
| 2 | `c360_upc` | Product catalog — SKU level with category and brand |
| 3 | `c360_customer_profile` | Customer identity, tier, demographics, segments |
| 4 | `c360_offer` | Offer catalog — targeting, discounts, points, dates |
| 5 | `c360_offer_upcs` | Offer → UPC linkage (item-level offers) |
| 6 | `c360_freshpass` | FreshPass subscription status |
| 7 | `c360_j4u_hh_attributes` | Binary J4U targeting flags per household |
| 8 | `c360_txn` | Transaction headers |
| 9 | `c360_txn_upc` | Line-item transactions (one row per receipt line) |
| 10 | `c360_clips` | Offer clip events |
| 11 | `c360_redemptions` | Redemption events — ML training labels |
| 12 | `c360_rewards_redeemed` | Points/fuel reward redemptions |
| 13 | `c360_cat_affinity` | Pre-computed category affinity scores |
| 14 | `c360_customer_ltv_txn_agg` | Lifetime spend aggregates by department |
| 15 | `c360_hh_weekly_cat_txns` | Weekly category spend per household |
| 16 | `c360_offer_summary` | Pre-aggregated offer performance (clips, redemption rate) |
| 17 | `c360_deals_engagement_aggr` | Clip/redemption aggregates by region and period |
| 18 | `c360_scored_offers` | **Output table** — written by scoring engine, read by API and UI |

See [`docs/data_model.md`](docs/data_model.md) for full field reference and relationships.

---

## Project Structure

```
HackathonProject/
├── requirements.txt
├── README.md
├── docs/
│   ├── data_model.md             # 18-table schema reference
│   ├── scoring_engine.md         # Both scoring paths with formulas
│   ├── technical_integration.md  # Architecture and data flow
│   ├── customer_touchpoints.md   # 7 customer touchpoints
│   └── ml_roadmap.md            # Phase 4 ML upgrade plan
└── files/
    ├── app.py                    # Streamlit demo UI
    ├── db/
    │   └── schema.sql            # PostgreSQL schema — all 18 tables
    ├── data/
    │   └── generate_data.py      # Synthetic data generator
    ├── engine/
    │   └── scoring.py            # Rule-based scoring engine
    ├── api/
    │   └── main.py               # FastAPI REST API
    └── static/
        └── logo.svg              # Albertsons logo
```

---

## Roadmap — Phase 4 ML Upgrade

The rule-based engine is designed to be replaced by a 4-layer ML model:

| Layer | Description | Status |
|---|---|---|
| Layer 1 | Feature engineering pipeline | Planned |
| Layer 2 | XGBoost propensity model — P(redemption \| customer, offer) | Planned |
| Layer 3 | Embedding similarity (collaborative filtering) | Planned |
| Layer 4 | Blended ranking + hard business rules on top | Planned |

Training labels: `c360_redemptions` (positive) vs clipped-not-redeemed from `c360_clips` (negative).
SHAP values will replace the manual score breakdown in the UI.

See [`docs/ml_roadmap.md`](docs/ml_roadmap.md) for full details.

---

## Production Path

The local PostgreSQL schema mirrors C360 field names exactly. Moving to production requires only changing the SQLAlchemy connection string — no query rewrites needed:

```
BigQuery project : gcp-abs-udco-bqvw-prod-prj-01
Dataset          : udco_ds_cust
Auth             : Service account / ADC (google-cloud-bigquery)
```
