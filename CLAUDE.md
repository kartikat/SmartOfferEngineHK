# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SmartOfferEngine** — personalised loyalty offer ranking engine for Albertsons / Safeway *for U* program. Three scoring models run side by side: a rule-based engine, an XGBoost standard propensity model, and an XGBoost GR propensity model. Results served via FastAPI and an interactive Streamlit demo UI. All data in PostgreSQL mirroring the Albertsons C360 BigQuery schema.

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

# 3. Train + run propensity models → writes model_type='propensity' and 'propensity_gr' rows
python3 files/engine/scoring_ml.py           # uses saved model_standard.pkl / model_gr.pkl if they exist
python3 files/engine/scoring_ml.py --retrain # force retrain both models from scratch

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
  data/generate_data.py      — Seeds all 18 PostgreSQL tables in dependency order
  engine/scoring.py          — Rule-based batch engine; writes model_type='rule_based'
  engine/scoring_ml.py       — Two XGBoost models; writes model_type='propensity' and 'propensity_gr'
  engine/model_standard.pkl  — Saved standard XGBoost model (joblib); delete to force retrain
  engine/model_gr.pkl        — Saved GR XGBoost model (joblib); delete to force retrain
  engine/model_metadata.json     — AUC + feature importances for standard model
  engine/model_gr_metadata.json  — AUC + feature importances for GR model
  api/main.py                — FastAPI REST API (port 8000)
  app.py                     — Streamlit demo UI (port 8501)
  db/schema.sql              — Full 18-table PostgreSQL schema
docs/
  propensity_model.md      — Full ML training documentation (features, labels, evaluation)
  architecture.md          — 5 Mermaid diagrams (system, scoring, DB, ML, stories)
  data_model.md            — 18-table schema reference
  scoring_engine.md        — Rule-based scoring paths with formulas
  ml_roadmap.md            — Phase 4 ML upgrade plan
  images/exec_architecture.png  — Executive-level architecture diagram (matplotlib-generated)
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
- `c360_scored_offers` PK is `(household_id, client_offer_id, model_type)` — all three models coexist
- `days_since_last_txn` is **not** a column on `c360_customer_profile` — compute via `CURRENT_DATE - MAX(t.txn_dte)::date` with a join to `c360_txn`

**Catalog sizes:** 71 UPCs (30 real Dairy + 41 synthetic across 10 departments), 64 offers (6 real + 58 synthetic), 120 households.

**Departments:** `Dairy Eggs Cheese`, `Grocery`, `Produce`, `Bakery`, `Meat`, `Frozen`, `Household`, `Fuel`, `Seafood`, `Deli` — all 10 in `ALL_CATEGORIES` and `dept_weights` for transaction generation.

## Three Scoring Models

Standard and GR offers are scored into **separate pools** — `TOP_N_STANDARD = 10` standard offers + `TOP_N_GR = 5` GR offers per household. This prevents GR offers from crowding out standard offers for high-balance customers. `scoring.py` splits by `discount_type_cd` after scoring; `scoring_ml.py` achieves this naturally since `score_standard_pairs` and `score_gr_pairs` are separate calls each with their own `top_n`.

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

### Standard Propensity Model (`model_type = 'propensity'`) — `files/engine/scoring_ml.py`

XGBoost classifier trained on standard offer clips + redemptions only (`program_type != 'Grocery Reward'`):
- **16 features** — no points features (standard offers don't require points to redeem)
- Customer (9): `is_4uplus`, `gas_rewards`, `doordash`, `instacart`, `uber`, `household_size`, `num_children`, `churn_risk`, `days_since_last_txn`
- Offer (5): `discount_value`, `is_j4u_exclusive`, `is_freshpass_offer`, `redemption_rate`, `days_until_expiry`
- Interaction (2): `channel_match`, `category_affinity`
- **CV AUC: 0.626** — top features: `channel_match`, `instacart`, `redemption_rate`, `category_affinity`, `is_4uplus`
- Model saved to `model_standard.pkl`; metadata to `model_metadata.json`

### GR Propensity Model (`model_type = 'propensity_gr'`) — `files/engine/scoring_ml.py`

XGBoost classifier trained on GR offer clips + redemptions only (`program_type = 'Grocery Reward'`):
- **12 features** — points-focused; drops channel/eCommerce signals irrelevant to GR redemption
- Customer (7): `current_point_balance`, `points_expiring_next_month`, `is_4uplus`, `household_size`, `num_children`, `churn_risk`, `days_since_last_txn`
- Offer (3): `discount_value`, `redemption_rate`, `days_until_expiry`
- Interaction (2): `category_affinity`, `points_gap`
- **CV AUC: 0.572** — top features: `discount_value`, `num_children`, `points_gap`, `points_expiring_next_month`, `category_affinity`
- Model saved to `model_gr.pkl`; metadata to `model_gr_metadata.json`
- Used by **My Rewards** page to rank GR offers by personalised score instead of static tier tabs

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

**GR offers are excluded from the standard ranked list** (`My Offers`). They appear only in the dedicated **`My Rewards`** page and as a teaser banner at the bottom of `My Offers`.

**My Rewards page** — score-ranked 3-column grid from `c360_scored_offers WHERE model_type='propensity_gr'`, filtered to `pts_threshold <= balance`, ordered by `score DESC`. Cards match My Offers layout: amber "Reward" badge + blue discount value, product info + category image, divider, points cost pill + expiry. "Use X pts" button clips and deducts points.

**Auto Clip** — opt-in toggle on My Rewards page. When ON: `auto_clip_ind = TRUE`; GR scored list replaced with a single cash-off card; My Offers teaser banner switches to green Auto Clip status banner. Toggle writes to DB via `toggle_auto_clip(hid, enable)` and clears `load_customers` cache.

## Streamlit UI

**Navigation pages:** My Offers · My Rewards · My Clipped Offers · My Profile · Problem Exploration · Segment Explorer · Compare Customers · Compare Models · **Feature Weight Studio** · How Offers Are Scored · **Feature Engineer** · Demo Script

**Personas:** Customer View and Analyst View, toggled in the sidebar. Analyst view has **two separate radio groups** — "Customer View" (My Offers, My Rewards, My Clipped Offers, My Profile) and "Analyst Tools" (analyst-only pages). Each radio uses an `on_change` callback updating `st.session_state.nav_page` directly to avoid interference between the two groups.

**Customer switcher:** Selectbox rendered in a `st.columns([1,1])` right-column, placed directly below the blue header ribbon. CSS `:has(.abs-header) + stVerticalBlockBorderWrapper` makes it appear visually inside the ribbon. Selectbox updates `st.session_state.household_id` and triggers `st.rerun()`.

**My Offers:** Standard + Fuel + Points-multiplier offers only (GR filtered out). 3-column grid (`st.columns(3, gap="medium")`). Card layout: blue "for U" badge + blue discount value top row; offer text + category image (76×76) middle; divider; ✓ Clipped + expiry bottom. Clip button (`type="primary"`) is blue; Simulate button (top-level, outside columns) is orange. CSS distinguishes them: primary buttons inside `stHorizontalBlock` = blue, top-level primary = orange. Gold teaser banner at bottom shows eligible GR tier count.

**My Rewards:** 3-column grid matching My Offers layout. Amber "Reward" badge replaces "for U" badge. Points cost pill (`300 pts`) and expiry in bottom row. "Use X pts" button below card. Auto Clip toggle at top.

**Customer feature tags:** `customer_feature_tags(customer)` returns coloured pill HTML rendered above the offer grid on My Offers. Tags derived from `c360_customer_profile` purchase indicator columns: `meat_purchase_ind_6m`, `produce_purchase_ind_6m`, `bakery_purchase_ind_6m`, `seafood_purchase_ind_6m`, `frozen_grocery_purchase_ind_6m`, plus `clv_tier_level_id`, `churn_segment_cd`, `diet_preference`, `doordash/instacart/uber_txn_ind_6m`, `gas_rewards_ind_6m`, `num_of_household_members`.

**Model toggle on My Offers:** `📋 Rule-Based` | `🤖 Propensity (XGBoost)` — filters `scored_df` by `model_type`.

**Compare Models page:** Side-by-side ranking from rule-based and standard propensity models for the same customer, with rank-change deltas (▲▼) and feature importance display.

**Feature Weight Studio:** Business user page for exploring how feature importance affects rankings. Two tabs:
- `📋 Rule-Based` — 5 sliders (0–200% of default weight) mapped to the 5 scoring components stored in `c360_scored_offers`. Custom score = weighted sum of components + recency/tier boosts. `_STUDIO_FEATURES` in `app.py`.
- `🤖 Propensity` — 16 sliders grouped by category (Personalisation, Offer Quality, Loyalty, Engagement, Channels, Demographics, Offer Fit). Features normalised to [0,1] per customer's offer set; features marked `invert=True` (e.g. `days_since_last_txn`, `churn_risk`) are flipped. Custom score = weighted sum, rescaled 0–100. `_PROPENSITY_FEATURES` in `app.py`. Data loaded via `load_propensity_feature_matrix(hid)` (cached).
- Both tabs share `_render_ranking_comparison(merged, orig_score_col, custom_score_col, orig_rank_col, custom_rank_col, orig_label, model_color)` — the side-by-side card renderer with ▲▼ deltas.
- `orig_rank` is re-numbered 1…N within the standard-only subset before comparison.
- Session-only state — weights reset on logout/refresh, never written to DB.

**Feature Engineer:** Admin page for permanently changing which features the propensity models train on.
- Reads `FEATURE_COLS_STANDARD` and `FEATURE_COLS_GR` from `scoring_ml.py` via `read_feature_cols()`
- Displays features grouped as **Standard Only / GR Only / Both Models** — each feature has a separate Standard and GR checkbox
- AUC metrics sourced from `model_metadata.json` + `model_gr_metadata.json` (production outputs of `scoring_ml.py`)
- "Apply & Retrain" button: calls `write_feature_cols(selected_std, selected_gr)` which regex-replaces both lists in `scoring_ml.py`, then runs `scoring_ml.py --retrain` via subprocess
- Changes are **permanent** (modifies source file + triggers real retrain) — contrast with Feature Weight Studio which is session-only
- `scoring_ml_split.py` is a teammate's separate file — do **not** wire Feature Engineer to it; it's disconnected from the UI's data path

**Key UI rules:**
- Use `st.html()` not `st.markdown(unsafe_allow_html=True)` — Streamlit 1.55.0 requires this
- CSS braces in f-strings must be doubled (`{{` / `}}`)
- `@st.cache_data(ttl=300)` on all data load functions
- Clip button writes to `c360_clips` via `gen_random_uuid()::text` as PK
- Offer expiry: red border/badge ≤3 days, amber ≤7 days
- `get_clipped(hid)` seeds from DB on first access per session (page refresh safe) — do not replace with a plain session state read
- `toggle_auto_clip(hid, enable)` updates `auto_clip_ind` in DB and clears `load_customers` cache

**Field name reference:**
- `clv_tier_level_id` (values: `Standard`, `4U+`)
- `delivery_channel_cd` (values: `J4U`, `Weekly Ad`, `Auto Clip`)
- `discount_type_cd` (values: `AMT_OFF`, `PCT_OFF`, `GROCERY_REWARD`, `DEPT_REWARD`, `FREE_ITEM`, `FUEL_CENTS`, `POINTS_MULTIPLIER`, `FREE_DELIVERY`)
- Boost flags are flat booleans (`recency_boost_applied`, `tier_multiplier_applied`), not dicts
- Score components are flat numeric columns, not JSON

## Demo Presentation System

`DEMO_STEPS` is a list of 8 step dicts in `app.py`. Each step has: `tag`, `title`, `narration`, `talking_points`, `customer` (key into `cust_map`), `highlight` (renders visual content), `nav_page` (auto-navigates left pane), `persona`.

**`render_demo_script()`** — renders the visual content for the current step. In `demo_mode=True` (presenter panel open), only renders the visual; talking points are in the right panel. In `demo_mode=False`, shows full script with narration and nav controls.

**`render_demo_panel()`** — the right-side presenter panel (50/50 split). Shows step dots, tag, title, narration, talking points, nav badge. ← Back / Next → buttons auto-navigate left pane and switch persona. ◀ collapse button at top-right.

**Highlight types** and what they render:

| `highlight` | Renders |
|---|---|
| `before` | App + web screenshots of current Albertsons for U |
| `stats` | Segment metrics (st.metric grid) + Segment Explorer |
| `compare` | Side-by-side top-3 offers for fuel vs premium customers |
| `compare_models` | `render_model_comparison()` for premium customer |
| `model_story` | Exec-friendly Rules vs AI comparison: Jessica Miller (Vegan) + Stephanie White (Organic) |
| `so_what` | Business impact cards (redemption lift, churn, eCommerce) + exec architecture diagram |
| `roadmap` | Phase delivery plan |
| `criteria` | `render_allocation_criteria()` |

**Best demo customers for propensity model story** (Step 6 — `model_story`):
- **HH00077 Jessica Miller** — Vegan, Produce buyer. Rule: Dave's Killer Bread #1 → AI: Fresh Vegetables #3
- **HH00112 Stephanie White** — Organic, High Churn. Rule: Coca-Cola #1 → AI: Beef Sirloin #2

**Good demo customers for GR / points story:**
- HH00118 — 2,977 pts, 4U+ (eligible for all 8 GR tiers)
- HH00116 — 2,916 pts, 4U+

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
