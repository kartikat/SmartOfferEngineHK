# Technical Integration — SmartOfferEngine

> How the SmartOfferEngine engine connects to data sources, APIs, and front-end surfaces.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Albertsons C360 (BigQuery)              │
│   gcp-abs-udco-bqvw-prod-prj-01.udco_ds_cust           │
│   ~90 views — customer, offer, txn, clips, redemptions  │
└────────────────────────┬────────────────────────────────┘
                         │ schema mirror (synthetic data for demo)
                         ▼
┌─────────────────────────────────────────────────────────┐
│            PostgreSQL 16 — smartrewards DB              │
│            18 tables mirroring C360 field names         │
│            /opt/homebrew/opt/postgresql@16/bin          │
└──────────┬──────────────────────┬───────────────────────┘
           │                      │
           ▼                      ▼
┌─────────────────┐    ┌──────────────────────────────────┐
│  Scoring Engine │    │         FastAPI (main.py)         │
│  scoring.py     │───▶│  REST API — port 8000            │
│                 │    │  Reads c360_scored_offers         │
│  Writes to      │    │  Serves ranked offers per customer│
│  c360_scored_   │    └──────────────┬───────────────────┘
│  offers         │                   │
└─────────────────┘                   ▼
                          ┌───────────────────────┐
                          │   Streamlit UI (app.py)│
                          │   port 8501 / 8502     │
                          │   Customer demo surface│
                          └───────────────────────┘
```

---

## Components

### 1. PostgreSQL Database
- **Database**: `smartrewards`
- **Version**: PostgreSQL 16 (Homebrew)
- **Path**: `/opt/homebrew/opt/postgresql@16/bin`
- **Tables**: 18 (mirroring C360 BigQuery views)
- **Connection**: `psql -d smartrewards`

### 2. Data Generator (`files/data/generate_data.py`)
- Generates synthetic data for all 18 tables in dependency order
- Seeds PostgreSQL directly via SQLAlchemy
- Maintains referential integrity across all tables
- **Status**: To be rewritten for PostgreSQL (currently CSV-only)

### 3. Scoring Engine (`files/engine/scoring.py`)
- Reads customer + offer + affinity data from PostgreSQL
- Produces scored and ranked offers per customer
- Writes results to `c360_scored_offers`
- Two scoring paths: standard offers + Grocery Reward offers
- **Status**: To be refactored from CSV to PostgreSQL

### 4. FastAPI (`files/api/main.py`)
- REST API serving pre-scored offers from `c360_scored_offers`
- **Port**: 8000
- **Key endpoints**:

| Endpoint | Description |
|---|---|
| `GET /offers/{customer_id}` | Top N ranked offers for a customer |
| `GET /customer/{customer_id}` | Customer profile |
| `GET /segments` | Segment summary stats |
| `POST /clip/{customer_id}/{offer_id}` | Record a clip event |

- **Status**: To be refactored from CSV to PostgreSQL

### 5. Streamlit UI (`files/app.py`)
- **Port**: 8501 (or 8502 if 8501 is occupied)
- **Run**: `streamlit run files/app.py --server.headless true`
- Reads directly from CSVs (to be updated to query FastAPI or PostgreSQL)

---

## Data Flow

```
1. generate_data.py
   └── Seeds all 18 PostgreSQL tables in dependency order

2. scoring.py
   ├── Reads: c360_customer_profile, c360_offer, c360_cat_affinity
   │          c360_txn, c360_redemptions, c360_rewards_redeemed
   └── Writes: c360_scored_offers (one row per household × offer)

3. main.py (FastAPI)
   └── Reads: c360_scored_offers, c360_customer_profile

4. app.py (Streamlit)
   └── Reads: c360_scored_offers, c360_customer_profile, c360_offer
       Writes: c360_clips (clip/unclip events from UI)
```

---

## Key Database Relationships

```
c360_customer_profile (retail_customer_uuid)
    ├── c360_freshpass         (retail_customer_uuid)
    ├── c360_j4u_hh_attributes (household_id)
    └── c360_clips             (household_id, retail_customer_uuid)
            └── c360_redemptions (household_id, client_offer_id)
                    └── c360_rewards_redeemed (household_id)

c360_offer (client_offer_id)
    ├── c360_offer_upcs        (client_offer_id → upc_id)
    ├── c360_clips             (client_offer_id)
    ├── c360_redemptions       (client_offer_id)
    └── c360_offer_summary     (client_offer_id)

c360_txn (txn_id)
    └── c360_txn_upc           (txn_id, receipt_line_nbr)
            └── c360_upc       (upc_id)

c360_scored_offers (household_id, client_offer_id)  ← output table
```

---

## Environment Setup

```bash
# PostgreSQL
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
psql -d smartrewards

# Python dependencies
pip install fastapi uvicorn pandas numpy sqlalchemy psycopg2-binary streamlit

# Run Streamlit
streamlit run files/app.py --server.headless true
# → http://localhost:8501

# Run FastAPI
uvicorn files.api.main:app --reload --port 8000

# Run scoring engine
python3 files/engine/scoring.py
```

---

## Future: BigQuery Integration (Production)

In production, the scoring engine would run directly against C360 BigQuery views:

```
BigQuery project : gcp-abs-udco-bqvw-prod-prj-01
Dataset          : udco_ds_cust
Auth             : Service account / ADC (google-cloud-bigquery)
```

The local PostgreSQL schema mirrors C360 field names exactly, so the transition requires only changing the SQLAlchemy connection string — no query rewrites.
