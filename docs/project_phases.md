# SmartRewards — Project Phases

> End-to-end delivery plan across 4 phases: data infrastructure, demo UI, polish, and ML upgrade.

---

## Overview

| Phase | Name | Status |
|---|---|---|
| Phase 1 | Data Infrastructure — PostgreSQL | ✅ Complete |
| Phase 2 | Demo UI — Streamlit | ✅ Complete |
| Phase 3 | Scoring Engine Polish | ✅ Complete |
| Phase 4 | ML Algorithm Upgrade | 🔵 Planned |

---

## Phase 1 — Data Infrastructure

**Goal:** Replace CSV-based synthetic data with a proper PostgreSQL database mirroring the Albertsons C360 BigQuery schema. Seed it with realistic, correlated data.

### What was built

**Schema (`files/db/schema.sql`)**

18 tables mirroring the Albertsons C360 BigQuery views (`gcp-abs-udco-bqvw-prod-prj-01.udco_ds_cust`). Field names preserved exactly from the source so that transitioning to production BigQuery requires only a connection string change.

Seven design decisions made during schema review:

| Issue | Resolution |
|---|---|
| `c360_txn_upc` PK | Changed to `(txn_id, receipt_line_nbr)` — same UPC can appear twice on one receipt |
| `c360_offer_upcs` join path | Made `client_offer_id` the explicit FK — one consistent join key throughout |
| Offer targeting scope | Added `target_level_cd` (`ITEM` / `CATEGORY` / `BASKET`) to `c360_offer` |
| Grocery Reward thresholds | Added `tier_1/2/3_points_threshold` to `c360_offer` — points the customer *spends* |
| FreshPass-only offers | Added `is_freshpass_offer_ind` to `c360_offer` |
| Household attribute snapshots | Added `is_current_ind` to `c360_j4u_hh_attributes` — filter for latest run only |
| Clip source | Added `retail_customer_uuid` explicitly to `c360_clips` (was only `customer_guid`) |

**Data generator (`files/data/generate_data.py`)**

Seeds all 18 tables in dependency order. Anchored to real data from the Safeway API:

- **30 real Safeway UPCs** — Dairy category (Lucerne, Fairlife, Chobani, Challenge, Tillamook, FAGE, O Organics, Vital Farms, Tropicana, Daisy, Coffee Mate, Frigo, SToK, Greek Gods)
- **21 synthetic UPCs** — Grocery, Produce, Bakery, Meat, Frozen, Household
- **6 real offer records** — extracted from live Safeway API response (Club Card price, 4X Points, BuyXGetY, 2X Points, Schedule & Save, FreshPass exclusive)
- **20 synthetic offers** — including 2 Grocery Reward (points-spend) offers and 2 Fuel offers
- **300 customers** across 120 households, 12 stores, 5 divisions
- Data is correlated: eCommerce customers have delivery transactions, fuel customers have fuel spend, Grocery Reward offers have `tier_N_points_threshold` set

Generated volumes:

| Table | Rows |
|---|---|
| c360_store | 12 |
| c360_upc | 51 |
| c360_customer_profile | 300 |
| c360_offer | 26 |
| c360_txn | 4,304 |
| c360_txn_upc | 36,521 |
| c360_clips | 819 |
| c360_redemptions | 453 |
| c360_cat_affinity | 840 |

### How to run

```bash
# Create DB and apply schema (once)
createdb smartrewards
psql -d smartrewards -f files/db/schema.sql

# Seed all 18 tables
python3 files/data/generate_data.py
```

---

## Phase 2 — Demo UI

**Goal:** Build an interactive Streamlit demo UI good enough to present to hackathon judges. Prioritised before the database so the demo surface existed early.

### What was built

**Login screen** — household selector showing tier, channel, and points balance. Judges can sign in as different customers and immediately see personalised results.

**My Offers** — ranked offer cards showing:
- Offer name, channel pill (colour-coded by J4U / Weekly Ad / Auto Clip)
- Score bar (0–100 gradient)
- Discount formatted from `discount_value` + `discount_type_cd`
- Boost badges (⚡ Recency, ★ for U+) where applied
- Clip / Unclip buttons. Grocery Reward offers allow multiple clips.
- Optional score breakdown expander showing all 5 component scores with weights

**My Clipped Offers** — active clips with count badges for multi-clipped Grocery Rewards

**My Profile** — loyalty metrics: tier badge, points balance, expiring points alert (red), favourite channel, engagement mode, days since last transaction, household size, churn risk

**Segment Explorer** — 5 segment cards (Fuel Redeemers, 4U+ Subscribers, High Points, Active This Week, High Churn Risk) with drilldown table, segment stats, and jump-to-customer

**Compare Customers** — side-by-side profiles + top 3 offers + score distribution bar chart. Makes personalisation immediately visible by showing the same catalog producing completely different results for two different customers.

**How Offers Are Scored** — visual breakdown of all 5 scoring rules (weight bars, data signal tags), multipliers, and business rules. Allows a non-technical audience to understand the engine logic.

**Demo Script** — 7-step guided walkthrough with narration panels and Previous / Next / Restart navigation:

| Step | Tag | Content |
|---|---|---|
| 1 | Overview | System stats — households, segments, avg score |
| 2 | Scoring Engine | How offers are scored (rules, multipliers, business rules) |
| 3 | Story 1 of 2 | Fuel Redeemer — profile view |
| 4 | Story 1 of 2 | Fuel Redeemer — offers + eCommerce nudge visible |
| 5 | Story 2 of 2 | 4U+ Subscriber — profile view |
| 6 | Story 2 of 2 | 4U+ Subscriber — exclusive offers + tier multiplier visible |
| 7 | Head-to-Head | Side-by-side comparison of both customers |

### Key constraints resolved

- **Streamlit 1.55.0**: Uses `st.html()` throughout — `st.markdown(unsafe_allow_html=True)` is not supported in this version
- **CSS in f-strings**: All CSS braces must be doubled (`{{` / `}}`) to avoid Python f-string interpolation errors
- **Channel pills**: Colour-coded — J4U (blue), Weekly Ad (green), Auto Clip (purple)

### How to run

```bash
streamlit run files/app.py --server.headless true
# → http://localhost:8501
```

---

## Phase 3 — Scoring Engine Polish

**Goal:** Migrate all components from CSV to PostgreSQL, implement the Grocery Reward scoring path, and wire the full stack end-to-end.

### What was built

**Scoring engine — Path 1 (Standard offers)**

Five weighted rules producing a 0–100 score per customer–offer pair:

| Rule | Weight | Signal |
|---|---|---|
| Transaction Affinity | 30% | `c360_cat_affinity.affinity_score` for the offer's category |
| Redemption Match | 25% | `fav_channel` vs `delivery_channel_cd` |
| Points Eligibility | 20% | `current_point_balance` vs offer thresholds |
| Cart & Browse Affinity | 15% | `doordash_txn_ind_6m`, `instacart_txn_ind_6m`, `uber_txn_ind_6m` |
| Demographic Match | 10% | `customer_age`, `num_of_children`, `diet_preference` |

Multipliers applied after the weighted sum:

| Multiplier | Factor | Condition |
|---|---|---|
| Recency Boost | ×1.2 | `days_since_last_txn ≤ 7` |
| Tier Multiplier | ×1.5 | `clv_tier_level_id = '4U+'` AND `is_appliable_to_j4u_ind = TRUE` |

Business rules (hard filters, not learned):
- FreshPass filter — FreshPass-only offers excluded for non-subscribers
- 4U+ filter — exclusive offers excluded for Standard tier
- eCommerce nudge — Fuel redeemers get partial channel match on J4U offers
- Score cap at 100

**Scoring engine — Path 2 (Grocery Reward offers)**

Grocery Reward offers are fundamentally different: the customer *spends* accumulated points for a dollar discount. Separate scoring path:

1. **Hard eligibility gate** — `current_point_balance < tier_1_points_threshold` → excluded entirely
2. **Best reachable tier** — determines which discount tier the customer can reach
3. **Weighted components** — points eligibility (40%), category affinity (25%), value per point (15%), GR redemption history (15%), recency (5%)
4. **Points expiry multiplier** — ×1.3 if `points_expiring_next_month ≥ tier_1_points_threshold`
5. Score cap at 100

**FastAPI (`files/api/main.py`)**

All endpoints migrated to PostgreSQL. Updated to C360 field names. New endpoints added:

| Endpoint | Description |
|---|---|
| `GET /health` | DB row counts + `last_scored_at` timestamp |
| `GET /offers/{household_id}` | Top N ranked offers, optional channel filter |
| `GET /customer/{household_id}` | Profile with live `days_since_last_txn` |
| `POST /clip/{household_id}/{offer_id}` | Writes clip event to `c360_clips` |
| `GET /segments` | Tier-level summary across all households |
| `GET /segments/fuel-redeemers` | `gas_rewards_ind_6m = TRUE` households |
| `GET /segments/4uplus` | `clv_tier_level_id = '4U+'` households |
| `GET /segments/high-churn` | `churn_segment_cd = 'High Risk'` households |

**Streamlit UI — PostgreSQL migration**

Three `@st.cache_data(ttl=300)` load functions replacing CSV reads:
- `load_customers()` — includes live `days_since_last_txn` from SQL join with `c360_txn`
- `load_scored()` — flat score component columns (not parsed JSON dicts)
- `load_offers()` — active offers from `c360_offer`

Field name updates throughout: `customer_id` → `household_id`, `tier` → `clv_tier_level_id`, `points_balance` → `current_point_balance`, `channel` → `delivery_channel_cd`, `offer_name` → `offer_dsc`.

### How to run

```bash
# Score all households → writes to c360_scored_offers
python3 files/engine/scoring.py

# Start API
uvicorn files.api.main:app --reload --port 8000

# Start UI (already running from Phase 2)
streamlit run files/app.py --server.headless true
```

---

## Phase 4 — ML Algorithm Upgrade

**Goal:** Replace the rule-based scoring engine with a 4-layer ML model that learns from historical redemption data.

**Status:** Planned. Requires sufficient redemption history in `c360_redemptions` and `c360_clips`.

### Why upgrade?

The rule-based engine has four fundamental limitations:

| Limitation | Impact |
|---|---|
| Weights are manually set | Not optimised for actual redemption rates — we're guessing |
| No cross-customer learning | Missing "customers like you also redeemed..." signals |
| Components are independent | Non-linear interactions (e.g. high points + expiring soon) not captured |
| Cannot adapt to new offer types | Every new category or channel requires a manual rule change |

### Layer 1 — Feature Engineering

Build a rich feature vector for every customer–offer pair.

**Customer features** (from `c360_customer_profile`, `c360_cat_affinity`, `c360_txn`):
- Points balance, days since last transaction, tier
- Engagement mode (eCommerce / In-Store / Both)
- Category spend proportions — top 5 categories by affinity score
- eCommerce platform flags (DoorDash, Instacart, Uber)
- Household size, number of children, diet preference
- Churn risk score

**Offer features** (from `c360_offer`, `c360_offer_summary`):
- `target_level_cd` (ITEM / CATEGORY / BASKET)
- Delivery channel, discount type, discount value
- `is_appliable_to_j4u_ind`, `is_freshpass_offer_ind`
- Historical redemption rate (`red_pct` from `c360_offer_summary`)
- Offer age (days since `start_dt`)

**Interaction features** (customer × offer):
- Channel match: `fav_channel` == `delivery_channel_cd`
- Points gap: `current_point_balance` − `tier_1_points_threshold`
- Category affinity score for the offer's category
- UPC-level purchase history match (for ITEM-level offers)
- Recency × discount value interaction term

### Layer 2 — XGBoost Propensity Model

Predicts P(redemption | customer, offer) for every customer–offer pair.

**Training labels:**
- Positive (1): rows in `c360_redemptions` — customer redeemed the offer
- Negative (0): offers clipped but not redeemed — `c360_clips LEFT JOIN c360_redemptions WHERE redemptions.txn_id IS NULL`

**Why XGBoost:**
- Handles mixed feature types (booleans, numeric, categorical) without preprocessing overhead
- Captures non-linear interactions naturally (e.g. high points + expiring = much stronger signal than either alone)
- Fast to train and score at batch scale
- SHAP values provide per-prediction explainability — each offer's score can be decomposed into feature contributions

**Output:** P(redemption) score (0–1) per customer–offer pair

**Explainability:** SHAP values replace the manual score breakdown in the UI. Instead of "Transaction Affinity: 0.72", customers and analysts see which specific features drove each offer's ranking.

**Evaluation metrics:**

| Metric | Description |
|---|---|
| AUC-ROC | Overall model quality — can it distinguish redeemers from non-redeemers? |
| Precision@K | Of the top K offers shown, how many were actually redeemed? |
| Redemption lift | Scored offers vs random baseline — how much better are we doing? |

### Layer 3 — Embedding Similarity (Collaborative Filtering)

Captures latent patterns that explicit features can't — "customers like you also redeemed...".

**Approach:** Two-tower model or matrix factorisation
- Customer embedding: derived from co-redemption patterns in `c360_redemptions`
- Offer embedding: derived from which customer segments tend to redeem each offer
- Score: cosine similarity between customer and offer embedding vectors

**Why this complements Layer 2:**
- XGBoost learns from explicit features; embeddings learn latent patterns that no feature directly encodes
- Surfaces offers the customer hasn't seen yet but similar customers frequently redeem
- Especially powerful for new customers with sparse transaction history — cold start problem

**Training data:** `c360_redemptions` — household × offer co-occurrence matrix. Requires >10k redemption events for meaningful embeddings.

### Layer 4 — Final Ranking & Blending

Combines the propensity score (Layer 2) and embedding similarity (Layer 3) into a single ranked list.

```
final_score = α × propensity_score + (1 − α) × embedding_similarity
```

Where α is tuned per customer segment:
- **Active customers** (high transaction history): higher α — rely more on propensity model
- **New customers** (sparse history): lower α — rely more on collaborative filtering

**Hard business rules applied on top (not learned — intentional):**
- Tier multiplier ×1.5 for 4U+ on exclusive offers
- Recency boost ×1.2 for customers active in last 7 days
- eCommerce nudge for Fuel redeemers
- Grocery Reward eligibility gate (points balance < threshold → exclude)
- FreshPass filter
- Score cap at 100

These rules remain hard-coded because they represent deliberate business strategy, not patterns to be learned from data.

### Delivery Milestones

| Milestone | Deliverable | Dependency |
|---|---|---|
| 4a | Feature engineering pipeline | PostgreSQL seeded with real data ✅ |
| 4b | XGBoost model trained + scoring | `c360_redemptions` + `c360_clips` data |
| 4c | SHAP values in UI | Layer 2 complete |
| 4d | Embedding model | >10k redemption events in `c360_redemptions` |
| 4e | Blended ranking | Layers 2 + 3 complete |

### Data Requirements

| Data | Table | Use |
|---|---|---|
| Redemption events | `c360_redemptions` | Positive training labels |
| Clip events | `c360_clips` | Negative examples (clipped, not redeemed) |
| Transaction history | `c360_txn`, `c360_txn_upc` | Feature engineering |
| Category affinity | `c360_cat_affinity` | Direct feature |
| Offer performance | `c360_offer_summary` | Offer-level features (`red_pct`, `clips`) |
| Grocery Reward history | `c360_rewards_redeemed` | GR redemption frequency feature |

### Production Path

The PostgreSQL schema mirrors C360 field names exactly. In production, the feature engineering pipeline and model training would run directly against C360 BigQuery views:

```
BigQuery project : gcp-abs-udco-bqvw-prod-prj-01
Dataset          : udco_ds_cust
Auth             : Service account / ADC (google-cloud-bigquery)
```

The transition requires only changing the SQLAlchemy connection string — no feature or query rewrites.

---

## What Stays the Same Across All Phases

Regardless of whether the scoring engine is rule-based or ML-driven, these remain constant:

- **Scoring unit** — `household_id` (not individual `retail_customer_uuid`). Grocery offers apply to the whole household.
- **Output table** — `c360_scored_offers`. The API and UI always read from here — the scoring engine is interchangeable.
- **Business rules** — tier multiplier, FreshPass filter, Grocery Reward eligibility gate, eCommerce nudge. These are strategic decisions, not learned behaviours.
- **Explainability** — every offer ranking must be explainable. Rule-based: component score breakdown. ML: SHAP values. The UI surface stays the same, only the source of the explanation changes.
