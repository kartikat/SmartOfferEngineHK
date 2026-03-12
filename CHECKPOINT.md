# SmartRewards — Session Checkpoint

> Updated after each `/checkpoint` command. Reflects the latest state of the project.

---

## Project
**SmartRewards** — AI-powered personalised loyalty offer engine for Albertsons *for U* program.
- Stack: Python, FastAPI, Streamlit 1.55.0, PostgreSQL 16
- Purpose: Hackathon demo

---

## Session 6 — 2026-03-10

### What was done

#### 1. Feature Engineer UI — Business-friendly feature management page
- **New Streamlit page**: "Feature Engineer" (sidebar navigation)
- Business users can now:
  - View all 19 features organized by category (Customer 11 / Offer 5 / Interaction 3)
  - See current importance % for each feature (from last training)
  - **Change target importance %** instead of complex multipliers
  - Enable/disable features with checkboxes (pre-selected for currently used)
  - Click **"Apply Changes & Retrain Models"** to train with new emphasis
  - Watch progress spinner while retraining
  - See new importance scores after training completes

#### 2. Feature importance visualization
- **Top section**: Clean table showing all currently used features
  - Feature name, Standard model %, GR model %
  - Visible on page load (no expanding needed)
- **Individual feature sections**: Expandable cards showing:
  - ✅ or ☐ status icon (in use or available)
  - Description of what the feature measures
  - Current % for Standard and GR models (if applicable)
  - Input field: "Target %" (0–100%)
  - Auto-calculated multiplier showing what weight will be applied
  - Info: "New feature — will get importance after training" for unused features

#### 3. Backend infrastructure for feature weights
- `files/engine/feature_weights.json` — Stores user-specified target importance multipliers
- `load_feature_weights()` in scoring_ml_split.py — Reads weights on startup
- `build_features()` updated to apply weights: `feature_value × weight`
- Weights applied **only during training**, not during scoring/inference
- Models retrain on weighted features, new importance recalculated

#### 4. Feature selection & tracking
- Read current FEATURE_COLS from `scoring_ml_split.py` using regex
- Track changes: added features, removed features, adjusted importance
- Summary display with visual indicators:
  - ⚠️ "Removing X feature(s): `feat1`, `feat2`"
  - ✅ "Adding X new feature(s): `feat3`, `feat4`"
  - 🎯 "Adjusting importance for: ↑ `feat5`: 4.2% → 12.0%"
- Minimum 5 features enforced (validation)
- Disable Apply button if < 5 features selected

#### 5. Encoding fixes
- Added `encoding='utf-8'` to all file operations in Feature Engineer
  - `read_feature_cols()` — reads scoring_ml_split.py
  - `write_feature_cols()` — writes modified FEATURE_COLS back
  - `load_feature_weights()` — loads from feature_weights.json
- Fixes Windows UnicodeDecodeError ('charmap' codec can't decode)

#### 6. Retraining trigger
- UI collects feature selections and weights
- Saves weights to `feature_weights.json`
- Calls subprocess: `python files/engine/scoring_ml_split.py --retrain`
- Subprocess loads weights, retrains both models with custom emphasis
- Updates database with 1,800 new scores per model
- Writes new feature importance to `model_metadata_split.json`
- UI clears caches and shows success message

---

## Current State

**Feature Engineer page fully functional.** Users can now adjust which features matter to the propensity models without touching code.

```
Feature Engineer UI:
  ├─ View current features & importance (19 features, two models)
  ├─ Adjust target % for any feature
  ├─ Remove/add features with checkboxes
  └─ Click Apply → retrain both models with custom weights

Backend:
  ├─ read_feature_cols() — parse FEATURE_COLS from scoring_ml_split.py
  ├─ load_feature_weights() — read user preferences from JSON
  ├─ build_features(..., feature_weights) — apply weights during training
  └─ write_feature_cols() — update source code with new feature list
```

**Models**: propensity_standard (AUC 0.653), propensity_gr (AUC 0.582)
**Features**: 19 total, all adjustable via UI (currently all enabled)

---

## Files Modified

- `files/app.py` — Added ~400 lines:
  - `read_feature_cols()` — Parse FEATURE_COLS with regex
  - `get_feature_categories()` — Return feature metadata + descriptions
  - `get_feature_importance()` — Extract importance from model_metadata
  - `write_feature_cols()` — Modify FEATURE_COLS in source via regex
  - `render_feature_engineer()` — Main UI page with all interactions
  - Navigation updated to include "Feature Engineer"
  - Page routing added for new page

- `files/engine/scoring_ml_split.py` — Added ~40 lines:
  - `load_feature_weights()` — Load JSON preferences
  - `build_features(..., feature_weights)` — Apply weights to features
  - `build_training_data_split(..., feature_weights)` — Pass weights to feature builder
  - `run(...)` — Load weights on startup, pass through pipeline

- `files/engine/feature_weights.json` — NEW, created on first Apply

---

## How to Use

1. **Start Streamlit app** (already running):
   ```bash
   streamlit run files/app.py
   ```

2. **Navigate to Feature Engineer** (sidebar menu)

3. **View current features** — See importance table at top

4. **Adjust any feature**:
   - Expand feature card
   - Check/uncheck to enable/disable
   - Enter new target % (0–100%)
   - See auto-calculated multiplier

5. **Click Apply & Retrain**:
   - Feature selection saved to `FEATURE_COLS`
   - Weights saved to `feature_weights.json`
   - Models retrain (2–5 minutes)
   - New scores written to database
   - UI refreshes with new importance

---

## Testing Checklist

- ✅ Feature Engineer page loads without errors
- ✅ Currently used features display in table (19 features)
- ✅ Checkboxes pre-selected for currently used features
- ✅ Can uncheck and set target %
- ✅ Change summary shows added/removed/adjusted features
- ✅ Apply button disabled if < 5 features
- ✅ Weights saved to JSON
- ✅ Models retrain successfully
- ✅ New scores written to database
- ✅ Feature importance updates in metadata
- ✅ UI auto-refreshes after retraining
- ⏳ **Next**: Test with real weight adjustments (e.g., boost discount_value, reduce channel_match)

---

## Known Limitations

1. **Feature weighting is multiplicative** — If a feature currently has 0% importance in a model, it can't be boosted past 0% (multiply by infinity doesn't help). Workaround: Add it as a new feature and train from scratch.

2. **No feature statistics** — UI doesn't show statistical significance, p-values, or correlation with targets. Purely experimentation-based.

3. **Long retraining** — Full retrain takes 2–5 minutes. No incremental learning. UI shows spinner but doesn't stream live logs.

4. **No A/B testing** — Can't run two configurations in parallel. Need to fully retrain to compare.

---

## Next Steps

**Phase 5 ideas:**
1. Add ability to create new synthetic features (formula builder)
2. Show feature correlations / collinearity detection
3. A/B test framework: save model snapshots, compare live
4. Feature interaction analysis (which feature pairs work best together?)
5. Automated feature optimization (genetic algorithm to find best weights)

---

## Resume Command

```bash
cd c:\Users\ktang06\SmartOfferEngineHK
$env:PYTHONIOENCODING = "utf-8"
$env:DATABASE_URL = "postgresql://postgres@localhost/smartrewards"
python -m streamlit run files/app.py
```

Navigate to **Feature Engineer** page to manage models without code. 🚀

### What was done

#### 1. Expanded grocery offer catalog
- Added **Seafood** and **Deli** as new departments (UPCs, affinity, transaction weights)
- Added 21 new synthetic UPCs: salmon, cod, shrimp, canned tuna, rotisserie chicken, Boar's Head meats, salami, pasta, olive oil, avocados, broccoli, apples, pork tenderloin, sirloin, ice cream, frozen burritos, sourdough, tortillas
- Added 15 new offer templates for Seafood, Deli, Produce, Meat, Frozen, Pantry
- `seafood_sales_amt` and `deli_sales_amt` in `c360_customer_ltv_txn_agg` now computed from real transaction data
- Offers: 26 → **64** total (6 real + 58 synthetic)
- UPCs: 52 → **71** (30 real + 41 synthetic)

#### 2. Full Grocery Reward tier structure (business inputs from real Safeway app)
- Replaced 2 GR placeholder offers with **25 real-structure GR offers** across 8 tiers
- Tiers: 100 / 200 / 300 / 400 / 500 / 700 / 1000 / 1200 pts
- Three offer types per tier:
  - `GROCERY_REWARD` — $ off basket (8 offers, one per tier)
  - `DEPT_REWARD` — $ off department: Bakery (100/300), Produce (200/500), Meat (400)
  - `FREE_ITEM` — free own-brand product (12 offers, 2 per tier 100–700)
- `pts_threshold` encoded as `tier_1_points_threshold` on each offer
- `program_subtype` set to `"Department"` / `"Free Item"` for UI display
- Template format extended to 8-tuple to carry `pts_threshold`

#### 3. Rule-based scoring fix for GR offers
- **Bug**: `points_score` was always 0.4 because `t2/t3` defaulted to 999999 (NULL in DB)
- **Fix**: `points_score = min(balance / threshold / 2, 1.0)` — graduated by surplus above threshold
- **Fix**: `gr_score` floor of 0.3 so first-time GR customers aren't penalised
- Result: GR offers now surface correctly for high-balance customers

#### 4. GR / standard offer separation in UI
- `TOP_N_OFFERS` raised from 10 → **15** in both scoring engines (ensures 10 standard after GR filtered)
- **My Offers** — GR offers filtered out entirely (`program_type != 'Grocery Reward'`)
- Gold teaser banner at bottom of My Offers shows eligible tier count and points balance
- **My Rewards** (new page) — tier tab UX matching real Safeway app:
  - Only tiers customer can afford shown as tabs
  - Each tab: basket discount card + dept discount card + free item cards (3-col grid)
  - "Use XXX pts" button on every card

#### 5. Points deduction on GR redemption
- Clicking "Use XXX pts" now:
  1. Writes to `c360_clips`
  2. Decrements `current_point_balance` by tier threshold (`GREATEST(..., 0)`)
  3. Writes to `c360_rewards_redeemed`
  4. Clears `load_customers` and `load_gr_offers` caches → balance and tabs update immediately

#### 6. Sidebar customer switcher
- Replaced static household ID display with a dropdown
- Select any customer without signing out

#### 7. CLAUDE.md updated
- New departments, GR tier table, discount_type_cd additions, TOP_N change, My Rewards page, propensity model updated counts

---

## Current State

**Full stack running. 64 offers across 10 departments. Full GR tier system live.**

```
generate_data.py  →  PostgreSQL (18 tables, 64 offers, 71 UPCs)
                          ↓
scoring.py        →  c360_scored_offers (1,800 rows — 15 per household, rule_based)
scoring_ml.py     →  c360_scored_offers (1,800 rows — 15 per household, propensity)
                          ↓
app.py (UI)       →  reads PostgreSQL directly   (port 8501)
main.py (API)     →  serves from c360_scored_offers  (port 8000)
```

**Propensity model:** 2,375 training examples (418 pos / 1,957 neg), CV AUC 0.522, top features: `channel_match`, `discount_value`, `category_affinity`

---

## How to Resume

```bash
cd /Users/KartikaT/HackathonProject
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Verify DB
psql smartrewards -c "SELECT COUNT(*) FROM c360_scored_offers;"  # expect 3,600

# Re-seed if needed (wipes everything):
python3 files/data/generate_data.py
python3 files/engine/scoring.py
python3 files/engine/scoring_ml.py

# Start UI (already running on 8501):
streamlit run files/app.py --server.headless true

# Good demo customers (high points):
# HH00118 — 2,977 pts, 4U+  (eligible for all 8 GR tiers)
# HH00116 — 2,916 pts, 4U+
# HH00017 — 2,907 pts, Standard
```

---

## Key Decisions

| Decision | Rationale |
|---|---|
| GR offers excluded from standard ranked list | Different product — you *spend* points, not receive discounts |
| My Rewards as separate page with tier tabs | Matches real Safeway app UX; cleaner demo story |
| Points deduct on clip (not checkout) | Demo has no checkout flow; "Use XXX pts" implies immediate redemption |
| TOP_N_OFFERS = 15 | Ensures 10 standard offers remain after filtering GR from My Offers |
| `points_score = min(ratio/2, 1.0)` | Single threshold per offer (not 3 tiers); rewards customers well above threshold |
| `gr_score` floor 0.3 | Prevents new-to-GR customers from being penalised on 15% of score |
| Seafood/Deli in transaction dept_weights | Without this, new UPCs would never appear in transactions or affinity |
| `pts_threshold` as 8th template tuple element | Keeps offer template format compact; None for non-GR offers |

---

## File Map

```
HackathonProject/
├── CLAUDE.md                        # Architecture + commands (always read this first)
├── CHECKPOINT.md                    # This file
├── README.md                        # Project overview, quick start, API reference
├── requirements.txt                 # Pinned Python dependencies
├── docs/
│   ├── architecture.md              # 5 Mermaid diagrams
│   ├── propensity_model.md          # Full ML training documentation
│   ├── scoring_engine.md            # Both scoring paths with formulas
│   ├── data_model.md                # 18-table schema reference
│   ├── ml_roadmap.md                # Phase 4 ML upgrade plan
│   └── images/                      # Rendered PNG diagrams
└── files/
    ├── app.py                       # Streamlit UI — port 8501
    ├── db/schema.sql                # All 18 table definitions
    ├── data/generate_data.py        # Seeds all 18 tables
    ├── engine/
    │   ├── scoring.py               # Rule-based engine → c360_scored_offers
    │   ├── scoring_ml.py            # XGBoost propensity engine → c360_scored_offers
    │   └── model_metadata.json      # AUC + feature importances (written after each ML run)
    └── api/main.py                  # FastAPI REST API — port 8000
```

---

## Next Steps

- [ ] **SHAP values** — per-prediction feature contribution on Compare Models page (Phase 4c)
- [ ] **More GR tier screenshots** — only 100–1200 pts modelled; real app may have more variants per tier
- [ ] **Transfer to office laptop** — `smartrewards_dump.sql` exists at project root

### Backlog (time permitting)

- [ ] **Offer Management System — Dynamic Offers**
  - **Admin UI**: Streamlit page for business users to create/edit/deactivate offers (CRUD on `c360_offer`); new offers surface in scoring immediately with no code changes
  - **Dynamic Trigger Engine**: Auto-generate personalised offers based on DB signals:
    - Win-back: `days_since_last_txn > 14` → % off top category
    - Churn prevention: `churn_segment_cd = 'High Risk'` → double points offer
    - Lapsed category: no dept txn in 60 days → dept-specific discount
    - Points expiry: `points_expiring_next_month > 0` → "use your points" nudge
    - FreshPass upsell: non-FreshPass + high eCommerce usage → free delivery trial
  - **Offer Performance Dashboard**: clip rate, redemption rate, revenue impact per offer — retire underperforming offers

- [ ] **Split Propensity Model — Standard vs GR**
  - Train two separate XGBoost models: one on standard offer clips/redemptions, one on GR clips only
  - GR model features should emphasise `points_gap`, `current_point_balance`, `points_expiring_next_month` over channel/demographic signals
  - Standard model keeps current 19 features
  - Both write to `c360_scored_offers` under `model_type = 'propensity_standard'` and `model_type = 'propensity_gr'`
  - UI Compare Models page updated to reflect the split

- [ ] **Login Dropdown — Real Customer Names**
  - Currently: `HH00118  |  4U+  |  J4U  |  2,977 pts`
  - Target: `Sarah Johnson  |  4U+  |  J4U  |  2,977 pts`
  - Replace `household_id` prefix with `full_name` in the login page dropdown and sidebar switcher
  - `household_id` still used internally (parsing `choice.split("|")[0].strip()` must be updated to extract `household_id` differently — e.g. store as tuple or use index lookup)

- [ ] **LTV Aggregate Refresh Job**
  - `c360_customer_ltv_txn_agg` is computed once at seed time and never updated
  - Once the transaction flow (below) feeds real data into `c360_txn` + `c360_txn_upc`, this table drifts from actual spend
  - Build a refresh job that recalculates all dept `sales_amt` columns, channel split, and totals from live transaction data
  - Also refreshes `c360_cat_affinity` (affinity scores) and `c360_offer_summary` (redemption rates) in the same run
  - Depends on: Transaction Flow → Redemption Pipeline below

- [ ] **Transaction Flow → Redemption Pipeline** *(teammate build)*
  - Build a checkout/transaction flow that writes completed transactions to `c360_txn` and `c360_txn_upc`
  - On transaction completion, write redemption rows to `c360_redemptions` for any clipped offers that matched purchased UPCs
  - For GR offers, also write to `c360_rewards_redeemed` and deduct `current_point_balance`
  - Once live, run `scoring_ml.py --retrain` to incorporate real redemption signals into the propensity model
  - Integration point: `c360_redemptions` schema already in place — teammate just needs to INSERT with `(redemption_id, txn_id, client_offer_id, household_id, redemption_ts)`
  - Downstream benefit: `c360_offer_summary.red_pct` and `c360_customer_ltv_txn_agg` recalculate from real data

- [ ] **UI Visual Refresh — Branding & Offer Images**
  - General visual polish: improved card design, better typography, spacing, colour hierarchy
  - Add product/offer images to offer cards — sourced from Safeway product API or static assets per category
  - Category fallback images (e.g. dairy icon, produce icon) for offers without a specific product image
  - Consider image storage: static `files/static/images/` folder keyed by `upc_id` or `client_offer_id`, or fetch from Safeway CDN at render time
  - Apply consistently across My Offers, My Rewards, My Clipped Offers pages

- [ ] **My Rewards UI — Score-Based GR Ranking**
  - Currently: GR offers shown in tabs grouped by points threshold (100pts / 200pts / 300pts …)
  - Target: single consolidated list ranked by propensity score (from `propensity_gr` model above), same card UX as My Offers
  - Eligibility gate still applies (`current_point_balance >= pts_threshold`) — ineligible tiers not shown
  - Removes the tab structure; customer sees their best-value GR offers first regardless of tier
  - Depends on: Split Propensity Model backlog item above

---

## Previous Sessions

### Session 4 — 2026-03-07
- Architecture diagrams (5 Mermaid), README, docs/how_we_built_it.md, docs/project_phases.md
- ML learning plan mapped across 5 paradigms

### Session 3 — 2026-03-07
- Full stack migrated from CSVs → PostgreSQL
- Rewrote all 4 components: data generator, scoring engine, FastAPI, Streamlit UI

### Session 2 — 2026-03-05
- Built `files/db/schema.sql` (18 tables, real C360 field names)
- Resolved 7 schema design issues
- Added "How Offers Are Scored" page and Demo Script
- Retrieved real Safeway product/offer data from API

### Session 1 — 2026-03-05
- Studied codebase, created CLAUDE.md
- Built full Streamlit UI: login, profile, offers, segment explorer, clip/unclip, compare customers, demo script, Albertsons branding
