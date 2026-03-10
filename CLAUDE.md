# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SmartRewards** — personalised loyalty offer ranking engine for Albertsons / Safeway *for U* program. Two scoring models run side by side: a rule-based engine and an XGBoost propensity model. Results served via FastAPI and an interactive Streamlit demo UI. All data in PostgreSQL mirroring the Albertsons C360 BigQuery schema.

## Setup & Run

```bash
# Dependencies
pip install fastapi uvicorn pandas numpy sqlalchemy psycopg2-binary streamlit xgboost scikit-learn
brew install libomp  # required for xgboost on macOS

# PostgreSQL (Homebrew)
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
# Database name: smartrewards

# 1. Seed the database (run once, or to reset)
python3 files/data/generate_data.py

# 2. Run rule-based scoring → writes model_type='rule_based' rows
python3 files/engine/scoring.py

# 3. Train + run propensity model → writes model_type='propensity' rows
python3 files/engine/scoring_ml.py           # uses saved model.pkl if exists
python3 files/engine/scoring_ml.py --retrain # force retrain from scratch

# 4. Start API  →  http://localhost:8000/docs
uvicorn files.api.main:app --reload --port 8000

# 5. Start UI   →  http://localhost:8501
streamlit run files/app.py --server.headless true
```

Override DB connection:
```bash
export DATABASE_URL="postgresql://localhost/smartrewards"
```

Re-render architecture diagrams to PNG:
```bash
python3 docs/render_diagrams.py
```

## Architecture

```
files/
  data/generate_data.py    — Seeds all 18 PostgreSQL tables in dependency order
  engine/scoring.py        — Rule-based batch engine; writes model_type='rule_based'
  engine/scoring_ml.py     — XGBoost propensity engine; writes model_type='propensity'
  engine/model_metadata.json — AUC, feature importances written after each ML training run
  engine/model.pkl           — Saved XGBoost model (joblib); delete to force retrain
  api/main.py              — FastAPI REST API (port 8000)
  app.py                   — Streamlit demo UI (port 8501)
  db/schema.sql            — Full 18-table PostgreSQL schema
docs/
  propensity_model.md      — Full ML training documentation (features, labels, evaluation)
  architecture.md          — 5 Mermaid diagrams (system, scoring, DB, ML, stories)
  data_model.md            — 18-table schema reference
  scoring_engine.md        — Rule-based scoring paths with formulas
  ml_roadmap.md            — Phase 4 ML upgrade plan
```

## Database — 18 C360 Tables

Seeded in dependency order:
`c360_store` → `c360_upc` → `c360_customer_profile` → `c360_offer` → `c360_offer_upcs` → `c360_freshpass` → `c360_j4u_hh_attributes` → `c360_txn` → `c360_txn_upc` → `c360_clips` → `c360_redemptions` → `c360_rewards_redeemed` → `c360_cat_affinity` → `c360_customer_ltv_txn_agg` → `c360_hh_weekly_cat_txns` → `c360_offer_summary` → `c360_deals_engagement_aggr` → `c360_scored_offers` (output)

**Live write behaviour** — only these tables are written by the UI at runtime:
- `c360_clips` — every clip/unclip action
- `c360_rewards_redeemed` — GR offer redemptions (points spend)
- `c360_customer_profile.current_point_balance` — decremented on GR clip
- `c360_customer_profile.auto_clip_ind` — toggled by Auto Clip button

`c360_redemptions` is **seeded only** by `generate_data.py` — it is never written by the UI. New redemptions require a teammate-built transaction flow to INSERT into it.

**Key identifiers:**
- Scoring unit: `household_id` (not `retail_customer_uuid`)
- Offer key: `client_offer_id` (not `oms_offer_id`)
- Filter `head_household_ind = TRUE` for one row per household
- `c360_scored_offers` PK is `(household_id, client_offer_id, model_type)` — both models coexist

**Catalog sizes:** 71 UPCs (30 real Dairy + 41 synthetic across 10 departments), 64 offers (6 real + 58 synthetic), 120 households.

**Departments:** `Dairy Eggs Cheese`, `Grocery`, `Produce`, `Bakery`, `Meat`, `Frozen`, `Household`, `Fuel`, `Seafood`, `Deli` — all 10 in `ALL_CATEGORIES` and `dept_weights` for transaction generation.

## Two Scoring Models

Both write to `c360_scored_offers` with `TOP_N_OFFERS = 15` per household. The UI separates GR and standard offers; the extra 5 slots ensure 10 standard offers remain after filtering GR out.

### Rule-Based (`model_type = 'rule_based'`) — `files/engine/scoring.py`

**Path 1 — Standard offers:**

| Rule | Weight | Key fields |
|---|---|---|
| Transaction Affinity | 30% | `c360_cat_affinity.affinity_score` |
| Redemption Match | 25% | `fav_channel` vs `delivery_channel_cd` |
| Points Eligibility | 20% | `current_point_balance` |
| Cart & Browse Affinity | 15% | `doordash_txn_ind_6m`, `instacart_txn_ind_6m`, `uber_txn_ind_6m` |
| Demographic Match | 10% | `customer_age`, `num_of_children`, `diet_preference` |

Multipliers: ×1.2 Recency Boost (`days_since_last_txn ≤ 7`), ×1.5 Tier Multiplier (`clv_tier_level_id = '4U+'` AND `is_appliable_to_j4u_ind = TRUE`). Score capped at 100.

**Path 2 — Grocery Reward** (`program_type = 'Grocery Reward'`):
- Hard gate: `current_point_balance < tier_1_points_threshold` → excluded
- `points_score = min(balance / threshold / 2, 1.0)` — graduated by surplus above threshold
- Weighted: points eligibility 40%, category affinity 25%, value/point 15%, GR history 15% (floor 0.3), recency 5%
- ×1.3 expiry multiplier if `points_expiring_next_month >= tier_1_points_threshold`

### Propensity Model (`model_type = 'propensity'`) — `files/engine/scoring_ml.py`

XGBoost classifier trained on `c360_clips` + `c360_redemptions`:
- **Positive (label=1):** clips with a matching redemption (418)
- **Negative (label=0):** clips with no redemption + eligible pairs never clipped (1,957)
- **Total training examples:** 2,375 — `scale_pos_weight = 4.682` handles class imbalance
- **19 features:** 11 customer + 5 offer + 3 interaction (channel match, category affinity, points gap)
- **CV AUC:** 0.522 — top features: `channel_match`, `discount_value`, `category_affinity`
- Output: `P(redemption) × 100` as score
- Metadata (AUC, feature importances) written to `files/engine/model_metadata.json`
- See `docs/propensity_model.md` for full training documentation

### Business Rules (applied by both models before scoring)

- `is_freshpass_offer_ind = TRUE` → excluded for non-FreshPass subscribers
- `is_appliable_to_j4u_ind = TRUE` → excluded for Standard tier households
- `auto_clip_ind = TRUE` → all `program_type = 'Grocery Reward'` offers excluded (Auto Clip replaces GR path)
- eCommerce nudge: Fuel redeemers get partial channel match on J4U offers

## Grocery Reward Tiers

8 tiers (100 / 200 / 300 / 400 / 500 / 700 / 1000 / 1200 pts). Each tier has up to 3 offer types, all with `program_type = 'Grocery Reward'` and `tier_1_points_threshold` set:

| `discount_type_cd` | `program_subtype` | Description |
|---|---|---|
| `GROCERY_REWARD` | `NULL` | $ off basket (e.g. "$4 Off Basket — 300 pts") |
| `DEPT_REWARD` | `Department` | $ off a specific department (e.g. "$7 Off Meat — 400 pts") |
| `FREE_ITEM` | `Free Item` | Free specific product (e.g. "FREE Bacon 48-oz — 700 pts") |

Dept discounts exist at tiers 100 (Bakery), 200 (Produce), 300 (Bakery), 400 (Meat), 500 (Produce). Tiers 700/1000/1200 are basket-only. Free items exist at tiers 100–700 (2 per tier).

**GR offers are excluded from the standard ranked list** (`My Offers`). They appear only in the dedicated **`My Rewards`** page (tier tab UX) and as a teaser banner at the bottom of `My Offers`.

**Auto Clip** — opt-in toggle on My Rewards page. When ON: `auto_clip_ind = TRUE` in `c360_customer_profile`; GR tier tabs replaced with a single card showing `floor(balance/100)` cash off applied automatically at checkout; My Offers teaser banner switches to green Auto Clip status banner. Toggle writes to DB via `toggle_auto_clip(hid, enable)` and clears `load_customers` cache.

## Streamlit UI

**Navigation pages:** My Offers · **My Rewards** · My Clipped Offers · My Profile · Segment Explorer · Compare Customers · **Compare Models** · How Offers Are Scored · Demo Script

**My Offers:** Standard + Fuel + Points-multiplier offers only (GR filtered out). Shows top N from `scored_df` filtered by `program_type != 'Grocery Reward'`. Gold teaser banner at bottom shows eligible GR tier count.

**My Rewards:** Auto Clip toggle at top. If Auto Clip OFF: tier tab UX — only tiers the customer can afford are shown, each tab has basket discount card + dept discount card + free item cards (3-col grid), "Use XXX pts" button clips the offer. If Auto Clip ON: tier tabs replaced with single cash-off card. Queries `c360_offer` directly via `load_gr_offers(balance)`, not `c360_scored_offers`.

**Model toggle on My Offers:** `📋 Rule-Based` | `🤖 Propensity (XGBoost)` — filters `scored_df` by `model_type`.

**Compare Models page:** Side-by-side ranking from both models for the same customer, with rank-change deltas (▲▼) and feature importance display.

**Sidebar customer switcher:** Dropdown replaces static household ID — select any customer without signing out.

**Key UI rules:**
- Use `st.html()` not `st.markdown(unsafe_allow_html=True)` — Streamlit 1.55.0 requires this
- CSS braces in f-strings must be doubled (`{{` / `}}`)
- `@st.cache_data(ttl=300)` on all data load functions
- Clip button writes to `c360_clips` via `gen_random_uuid()::text` as PK
- Offer expiry: red badge ≤3 days, amber badge ≤7 days
- `get_clipped(hid)` seeds from DB on first access per session (page refresh safe) — do not replace with a plain session state read
- `toggle_auto_clip(hid, enable)` updates `auto_clip_ind` in DB and clears `load_customers` cache

**Field name reference:**
- `clv_tier_level_id` (values: `Standard`, `4U+`)
- `delivery_channel_cd` (values: `J4U`, `Weekly Ad`, `Auto Clip`)
- `discount_type_cd` (values: `AMT_OFF`, `PCT_OFF`, `GROCERY_REWARD`, `DEPT_REWARD`, `FREE_ITEM`, `FUEL_CENTS`, `POINTS_MULTIPLIER`, `FREE_DELIVERY`)
- Boost flags are flat booleans (`recency_boost_applied`, `tier_multiplier_applied`), not dicts
- Score components are flat numeric columns, not JSON

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/offers/{household_id}` | Top N ranked offers (rule-based) |
| GET | `/customer/{household_id}` | Profile with live `days_since_last_txn` |
| POST | `/clip/{household_id}/{offer_id}` | Write clip to `c360_clips` |
| GET | `/segments` | Tier-level summary |
| GET | `/segments/fuel-redeemers` | `gas_rewards_ind_6m = TRUE` |
| GET | `/segments/4uplus` | `clv_tier_level_id = '4U+'` |
| GET | `/segments/high-churn` | `churn_segment_cd = 'High Risk'` |

## Session Conventions

- **`/checkpoint`** — write/update `CHECKPOINT.md` with session summary, decisions, next steps
- **`/documentation`** — update all files in `docs/` to reflect current codebase state
