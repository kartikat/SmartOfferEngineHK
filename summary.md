# SmartOfferEngine — Complete Project Summary

**Project:** AI-powered personalised loyalty offer ranking engine for Albertsons / Safeway *for U* program
**Stack:** Python · FastAPI · Streamlit · PostgreSQL 16 · XGBoost
**Purpose:** Hackathon demo — end-to-end personalisation system mirroring the real Albertsons C360 data architecture

---

## Session 1 — 2026-03-05 | Foundation & UI

### Goal
Build a working demo UI from scratch.

### What was built
- **Streamlit UI** with full Albertsons branding (logo, red/white colour scheme)
- **Login page** — household selector with tier and name display
- **My Offers page** — personalised ranked offer cards with score bar, channel pill, expiry badge, clip/unclip button
- **My Profile page** — household metrics, points balance, tier badge, shopping behaviour flags
- **Segment Explorer** — browse all households by tier, churn risk, fuel usage
- **Compare Customers** — side-by-side offer comparison for any two households
- **How Offers Are Scored** — explainer page showing scoring criteria and weights
- **Demo Script** — step-by-step guided walkthrough for presenting to judges
- Fixed Streamlit 1.55.0 compatibility (`st.html()` instead of `st.markdown(unsafe_allow_html=True)`)

---

## Session 2 — 2026-03-05 | Database Schema & Real Data

### Goal
Design the full database schema and embed real Safeway data.

### What was built
- **`files/db/schema.sql`** — 18-table PostgreSQL schema mirroring real Albertsons C360 BigQuery views
  - Tables: `c360_store`, `c360_upc`, `c360_customer_profile`, `c360_offer`, `c360_offer_upcs`, `c360_freshpass`, `c360_j4u_hh_attributes`, `c360_txn`, `c360_txn_upc`, `c360_clips`, `c360_redemptions`, `c360_rewards_redeemed`, `c360_cat_affinity`, `c360_customer_ltv_txn_agg`, `c360_hh_weekly_cat_txns`, `c360_offer_summary`, `c360_deals_engagement_aggr`, `c360_scored_offers`
- **30 real Safeway Dairy UPCs** pulled from the Safeway API (Lucerne, Fairlife, Tillamook, Chobani, Challenge, FAGE, Vital Farms, O Organics)
- **6 real Safeway offers** embedded (butter Club Card price, 4X Points on Dairy, Oreo+Milk bundle, 2X Points, Schedule & Save Creamer, FreshPass Free Delivery)
- Resolved 7 schema design decisions: PKs, `target_level_cd`, `is_freshpass_offer_ind`, `is_current_ind` filter on j4u attributes, scoring at `household_id` (not individual), `client_offer_id` as offer key, Grocery Reward as separate scoring path
- Added **Grocery Reward scoring path** documentation

---

## Session 3 — 2026-03-07 | Full PostgreSQL Migration

### Goal
Migrate from CSV-based prototype to a fully PostgreSQL-backed system.

### What was built
- **`files/data/generate_data.py`** — full synthetic data generator seeding all 18 tables in dependency order
  - 120 households, 300 customers, 12 stores across 5 Albertsons divisions (Safeway, Vons, Tom Thumb, Albertsons)
  - Realistic customer flags: FreshPass, 4U+ tier, fuel redeemer, eCommerce channels, churn risk, diet preference
  - Transaction generation with category-biased purchasing behaviour per customer profile
- **`files/engine/scoring.py`** — rule-based batch scoring engine
  - Path 1 (Standard): 5-rule weighted scoring with ×1.2 Recency Boost and ×1.5 Tier Multiplier
  - Path 2 (Grocery Reward): separate points-based scoring with hard eligibility gate
  - Writes `model_type='rule_based'` rows to `c360_scored_offers`
- **FastAPI** (`files/api/main.py`) rewritten to query PostgreSQL
- **Streamlit UI** rewritten to read from PostgreSQL — no CSVs in any data path
- Clip button wired to `c360_clips` via `gen_random_uuid()::text` as PK
- `CLAUDE.md` created with full architecture documentation

---

## Session 4 — 2026-03-07 | Documentation & ML Planning

### Goal
Create comprehensive documentation and plan the ML upgrade.

### What was built
- **`docs/architecture.md`** — 5 Mermaid diagrams:
  - System Overview (end-to-end data flow)
  - Scoring Engine Decision Flow (both paths, all business rules)
  - Database ER Diagram (all 18 tables with FK relationships)
  - Phase 4 ML Upgrade Architecture
  - Two Customer Stories (Fuel Redeemer vs 4U+ Subscriber)
- **`docs/render_diagrams.py`** — renders Mermaid diagrams to PNG via mermaid.ink API
- **`README.md`** — full project README with architecture, quick start, API reference
- **`docs/how_we_built_it.md`** — narrative of all build sessions and Claude Code usage
- **`docs/project_phases.md`** — all 4 phases with full technical detail
- **ML learning plan** — mapped 5 paradigms: Propensity (XGBoost), Learning to Rank, Collaborative Filtering, Two-Tower Neural Networks, Contextual Bandits + Uplift Modelling

---

## Session 5 — 2026-03-08 | Grocery Expansion & Rewards System

### Goal
Expand the offer catalog to cover real grocery departments, implement the full Grocery Reward tier system from the real Safeway app, and separate GR from standard offers in the UI.

### What was built

#### Expanded Offer Catalog
- Added **Seafood** and **Deli** as new departments
  - New UPCs: Atlantic Salmon, Cod, Shrimp, Canned Tuna, Rotisserie Chicken, Boar's Head Turkey/Ham/Salami
  - `seafood_sales_amt` and `deli_sales_amt` in the LTV table now computed from real transactions
- Added more Produce (avocados, apples, broccoli), Meat (pork tenderloin, sirloin), Frozen (ice cream, burritos), Bakery (sourdough, tortillas), Pantry (pasta, olive oil)
- **Catalog grew from 26 → 64 offers and 52 → 71 products across 10 departments**

#### Full Grocery Reward Tier System
Implemented from real Safeway app screenshots:

| Tier | Basket Discount | Dept Discount | Dept | Free Items |
|---|---|---|---|---|
| 100 pts | $1 off | $2 off | Bakery | Canned Veg, Tuna |
| 200 pts | $2 off | $3 off | Produce | Cream Cheese, Frozen Veg |
| 300 pts | $4 off | $5 off | Bakery | Orange Juice, Ice Cream Sandwiches |
| 400 pts | $5 off | $7 off | Meat | Rotisserie Chicken, Breakfast Sandwiches |
| 500 pts | $7 off | $7 off | Produce | Chunk Cheese 32oz, Whole Roasted Chicken |
| 700 pts | $10 off | — | — | Bacon 48oz, Sea Scallops |
| 1000 pts | $15 off | — | — | — |
| 1200 pts | $20 off | — | — | — |

Three new `discount_type_cd` values: `GROCERY_REWARD` (basket), `DEPT_REWARD` (department), `FREE_ITEM` (free product)

#### Rule-Based Scoring Fix
- **Bug:** GR offers weren't surfacing — `points_score` was always 0.4 due to NULL tier thresholds defaulting to 999999
- **Fix:** `points_score = min(balance / threshold / 2, 1.0)` — graduated by surplus; `gr_score` floor of 0.3 for first-time GR customers

#### XGBoost Propensity Model
Added implicit negatives to training set, improving model quality:
- Training examples: 819 → 2,375
- `scale_pos_weight = 4.682` to handle class imbalance
- Top features: `channel_match`, `discount_value`, `category_affinity`

#### UI: GR / Standard Separation
- `TOP_N_OFFERS` raised 10 → 15 in both engines (ensures 10 standard offers after GR filtered)
- **My Offers** — GR offers removed from ranked list; gold teaser banner shows eligible tier count
- **My Rewards** (new page) — tier tab UX matching the real Safeway app:
  - Only eligible tiers shown as tabs
  - Basket discount card + dept discount card + free item grid per tier
  - "Use XXX pts" button deducts points immediately, writes to `c360_rewards_redeemed`, refreshes balance

#### Other UI Improvements
- **Sidebar customer switcher** — change household without signing out
- **Compare Models page** — side-by-side rule-based vs propensity ranking with rank-change deltas (▲▼)

---

## Session 6 — 2026-03-09 | Auto Clip, Model Persistence & Bug Fixes

### Goal
Add Auto Clip business feature, persist the XGBoost model to disk, fix clip state not surviving page refreshes, and keep project documentation current.

### What was built

#### Auto Clip Feature
- New business rule: customers can toggle Auto Clip ON on the **My Rewards** page
- When ON: `auto_clip_ind = TRUE` in `c360_customer_profile` (new column, `ALTER TABLE` applied live)
- Auto Clip converts all points to flat cash at **$1 off per 100 pts**, applied automatically at checkout — GR tier selection becomes irrelevant
- **My Rewards page**: Auto Clip toggle at top with ON/OFF button + inline status; when ON, tier tabs replaced with a single card showing `floor(balance/100)` cash off
- **My Offers page**: bottom banner swaps — green "Auto Clip Active — $X off at next checkout" when ON, gold GR teaser when OFF
- `toggle_auto_clip(hid, enable)` — writes to DB, clears `load_customers` cache, `st.rerun()` for immediate UI update

#### Model Persistence
- XGBoost model now saved to `files/engine/model.pkl` via `joblib.dump` after every training run
- `scoring_ml.py` loads from disk by default — skips retraining, goes straight to scoring (fast)
- `--retrain` flag forces full retrain from scratch: `python3 files/engine/scoring_ml.py --retrain`
- `joblib==1.5.1` added to `requirements.txt`
- Retrain when: new clips have accumulated and you want the model to learn from them

#### Clip Persistence Fix
- **Bug**: clipped offers disappeared after page refresh — `get_clipped()` read from `st.session_state` which resets on refresh
- **Fix**: `get_clipped(hid)` now seeds from `c360_clips` DB on first access per household per session; subsequent calls use in-memory list (fast)
- Clip/unclip still update both session state and DB as before

#### Fresh Data Dump
- `smartrewards_dump.sql` refreshed (11 MB, up from 9.6 MB) — includes expanded catalog, GR tiers, session clips/redemptions

#### Documentation
- `CLAUDE.md` updated: model persistence commands, `model.pkl` path, Auto Clip behaviour, `get_clipped` DB-seeding note
- `requirements.txt` updated: added `xgboost==3.2.0`, `scikit-learn==1.8.0`, `joblib==1.5.1`
- `CHECKPOINT.md` backlog updated: removed completed items (model persistence, clip→API), added Split Propensity Model and Score-Based GR Ranking items

---

## Current System State

```
generate_data.py  →  PostgreSQL (18 tables)
                      64 offers · 71 products · 120 households · 10 departments
                      auto_clip_ind on c360_customer_profile
                              ↓
scoring.py        →  c360_scored_offers  (1,800 rows — rule_based, 15/household)
scoring_ml.py     →  c360_scored_offers  (1,800 rows — propensity, 15/household)
                      model.pkl saved after training (--retrain to refresh)
                              ↓
app.py (UI)       →  http://localhost:8501
api/main.py       →  http://localhost:8000/docs
```

### Navigation Pages
My Offers · My Rewards · My Clipped Offers · My Profile · Segment Explorer · Compare Customers · Compare Models · How Offers Are Scored · Demo Script

### Two Scoring Models
| | Rule-Based | Propensity (XGBoost) |
|---|---|---|
| Weights | Manually set | Learned from 2,375 clip/redemption events |
| GR handling | Separate Path 2 with points gate | Scored via `discount_value` + `points_gap` features |
| Explainability | Per-offer score breakdown | Feature importances (global) |
| Top signal | Category affinity + channel match | `channel_match` (importance: 0.123) |

---

## Key Demo Customers

| Household | Points | Tier | Why good for demo |
|---|---|---|---|
| HH00118 | 2,977 | 4U+ | Eligible for all 8 GR tiers; strong fuel + seafood affinity |
| HH00116 | 2,916 | 4U+ | Similar to above, good Compare Models contrast |
| HH00017 | 2,907 | Standard | High points but Standard tier — shows tier gate on 4U+ exclusive offers |
