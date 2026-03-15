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

---

## Session 8 — 2026-03-15

### What was done

#### 1. UI Visual Refresh — complete

Six items planned and built:

**Item 1 — Category icons + discount badge colouring**
- `CATEGORY_ICONS` dict — 14 categories mapped to emojis (🧀 🥦 🍞 🥩 🐟 🥪 🛒 ❄️ 🧹 ⛽ etc.)
- `DISCOUNT_COLORS` dict — 8 discount types mapped to hex colours: green (AMT_OFF/PCT_OFF), orange (FUEL_CENTS), purple (POINTS_MULTIPLIER), blue (FREE_DELIVERY), red (GR/FREE_ITEM)
- `category_icon(category_nm)` and `discount_color(discount_type_cd)` helper functions added
- `load_scored()` updated to LEFT JOIN `c360_offer_summary` and pull `rep_category_nm` as `category_nm` — resolves icons correctly from DB

**Item 2 — Login page card**
- Replaced plain `st.selectbox` form with centred white card (drop shadow, rounded corners)
- Larger logo, product tagline, "Sign In →" primary button, "no password required" hint

**Item 3 — Sidebar tier badge**
- Replaced `st.caption(f"Tier: ...")` with `tier_badge_sidebar()` — styled card block
- 4U+: gold star + blue gradient + points balance; Standard: slate blue + points balance

**Item 4 — Offer card redesign — My Offers**
- New two-column layout: category icon block (left) + offer name/pills/score (right)
- Discount badge coloured by `discount_type_cd` (green/orange/purple/blue/red)
- Channel + boost pills on their own row below offer name
- Score demoted to quiet metadata line above bar; discount value leads visually

**Items 5 & 6 — Expiry pills + My Rewards cards**
- Expiry pills absorbed into card redesign: ≤3d → red `⏰ Expires in Xd`, ≤7d → amber, >7d → hidden
- My Rewards cards redesigned to match My Offers: same icon block (amber bg), same discount badge, pts pill + expiry pill row, amber score bar gradient
- `render_rewards` loop updated with `idx` counter for rank display

---

## Session 7 — 2026-03-10 (continued)

### What was done

#### 1. Split propensity model into Standard and GR models

- **Before:** single XGBoost model trained on all offers mixed together (AUC 0.522)
- **After:** two separate models trained on filtered clip/redemption data:
  - `model_type='propensity'` — standard offers only, 16 features, **AUC 0.626**
  - `model_type='propensity_gr'` — GR offers only, 12 features, **AUC 0.572**
- Standard model top features: `channel_match`, `instacart`, `redemption_rate`, `category_affinity`, `is_4uplus`
- GR model top features: `discount_value`, `num_children`, `points_gap`, `points_expiring_next_month`, `category_affinity`
- Saved models: `model_standard.pkl` / `model_gr.pkl`; metadata: `model_metadata.json` / `model_gr_metadata.json`

#### 2. Removed points features from standard propensity model

- **Bug/design issue:** `current_point_balance`, `points_expiring_next_month`, and `points_gap` were in `FEATURE_COLS_STANDARD` — but standard offers don't require points to redeem, so these signals are noise
- `points_gap` for a standard offer = `current_point_balance - 0` (NULL threshold filled with 0) — meaningless duplicate
- **Fix:** removed all 3 from `FEATURE_COLS_STANDARD`; standard model now 19 → **16 features**
- Points features remain correctly in `FEATURE_COLS_GR` (12 features) where they belong

#### 3. My Rewards page — score-based GR ranking

- **Before:** static tier tab UX (100 pts / 200 pts / … tabs), queries `c360_offer` directly
- **After:** single ranked card list from `propensity_gr` model, gated by `pts_threshold <= balance`, ordered by `score DESC`
- Added `load_gr_scored_offers(hid, balance)` — queries `c360_scored_offers WHERE model_type='propensity_gr'`
- Each card shows: badge, offer description, pts cost pill, category, expiry, match score bar
- "Use XXX pts" button preserved; points deduction logic unchanged
- Caption: "X rewards available — ranked by your personalised score"

#### 4. Feature Weight Studio — new page

- Business user page for exploring how feature weights affect offer ranking
- **Rule-Based tab** (5 sliders): adjusts the 5 scoring components stored in `c360_scored_offers`; applies same recency/tier boosts; custom score = weighted sum of components
- **Propensity tab** (16 sliders): fetches raw feature matrix at runtime via `load_propensity_feature_matrix(hid)`; groups features into 7 labelled sections; min-max normalises per customer's offers; inverts features where lower = better (`days_since_last_txn`, `churn_risk`)
- Side-by-side comparison in both tabs: original rank vs custom rank with ▲▼ deltas and score bars
- Session-only state (`st.session_state`) — never written to DB; resets on logout/refresh
- Reset button on each tab

#### 5. Separate scoring pools — standard vs GR (bug fix)

- **Bug:** Standard and GR offers competed in the same `TOP_N_OFFERS=15` pool in `scoring.py`. High-balance customers (eligible for many GR tiers) had all 15 slots taken by GR offers — 0 standard offers in scored results.
- **Fix `scoring.py`:** Replaced `TOP_N_OFFERS=15` with `TOP_N_STANDARD=10` and `TOP_N_GR=5`. `run_batch_scoring` now splits scored offers into separate lists by `discount_type_cd` and ranks them independently. Every household always gets up to 10 standard + 5 GR offers.
- **Fix `scoring_ml.py`:** Same pool split applied to propensity models — added `top_n` parameter to `_score_pairs`; `score_standard_pairs` passes `TOP_N_STANDARD=10`, `score_gr_pairs` passes `TOP_N_GR=5`.
- **Result:** `rule_based` 1797 rows, `propensity` 1200 rows (120×10), `propensity_gr` 600 rows (120×5)
- HH00118 (previously 4 standard, 11 GR) → now 10 standard + 5 GR ✅

#### 6. Feature Weight Studio — orig_rank delta bug fix

- **Bug:** `orig_rank` in the comparison table used the absolute stored rank (which included GR offers ranked above standard). Even at 100% default weights, deltas were non-zero (e.g. ▲6 for Strawberries because 5 GR offers were ranked above it).
- **Fix:** After filtering to standard-only offers, re-number `orig_rank` as 1,2,3… within the subset before merging. Delta now correctly shows 0 at default weights and only moves when sliders are adjusted.
- **Verified:** All 10 deltas = 0 at 100% weights; rank swaps appear correctly when Transaction Affinity boosted to 200%.

#### 7. Root-cause investigation: $7 Off Produce showing first for HH00005

- `discount_value` is the #1 GR model feature; $7 Off Produce has the highest discount_value in the 500pt tier
- HH00005's true top affinity is Deli (0.139) but no Deli dept reward exists in the catalog
- Model is correct — the catalog gap is the issue → added to backlog

---

## Current State

**Full stack running. 64 offers across 10 departments. Three scoring models live.**

```
generate_data.py  →  PostgreSQL (18 tables, 64 offers, 71 UPCs)
                          ↓
scoring.py        →  c360_scored_offers (1,797 rows — 10 standard + 5 GR per household, rule_based)
scoring_ml.py     →  c360_scored_offers (1,800 rows — propensity: 1,200 + propensity_gr: 600)
                          ↓
app.py (UI)       →  reads PostgreSQL directly   (port 8501)
main.py (API)     →  serves from c360_scored_offers  (port 8000)
```

**Standard propensity model:** 1,167 training examples (229 pos / 938 neg), CV AUC 0.626, 16 features, top: `channel_match`, `instacart`, `redemption_rate`
**GR propensity model:** 1,208 training examples (189 pos / 1,019 neg), CV AUC 0.572, 12 features, top: `discount_value`, `points_gap`, `points_expiring_next_month`

---

## How to Resume

```bash
cd /Users/KartikaT/HackathonProject
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Verify DB
psql smartrewards -c "SELECT model_type, COUNT(*) FROM c360_scored_offers GROUP BY model_type;"
# expect: rule_based≈1797, propensity=1200, propensity_gr=600

# Re-seed if needed (wipes everything):
python3 files/data/generate_data.py
python3 files/engine/scoring.py
python3 files/engine/scoring_ml.py --retrain

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
| Points features removed from standard propensity model | Standard offers don't require points to redeem — `points_gap` was just a noisy copy of `current_point_balance` |
| Separate scoring pools: 10 standard + 5 GR | Prevents GR offers from crowding out standard offers for high-balance customers; previously customers with 2,900+ pts had 0 standard offers in their top 15 |
| `orig_rank` re-numbered within standard-only subset in Feature Weight Studio | Absolute stored rank includes GR offers above standard — delta would be non-zero even at 100% default weights, confusing users |
| Separate GR model (propensity_gr) | GR redemption is driven by different signals (points surplus, expiry urgency) than standard offer redemption |
| My Rewards uses propensity_gr score not tier tabs | Score-based ranking is more personalised; customers see their best-value GR offers first regardless of tier |
| Feature Weight Studio uses linear re-scoring (not XGBoost re-weighting) | Transparent, interpretable, real-time — no model retraining needed; clearly labelled as "what-if" exploration |
| Feature Weight Studio is session-only | Demo tool for business exploration — no need for persistence; avoids DB complexity |
| GR offers excluded from standard ranked list | Different product — you *spend* points, not receive discounts |
| My Rewards as separate page | Matches real Safeway app UX; cleaner demo story |
| Points deduct on clip (not checkout) | Demo has no checkout flow; "Use XXX pts" implies immediate redemption |
| TOP_N_OFFERS = 15 | Ensures 10 standard offers remain after filtering GR from My Offers |
| `gr_score` floor 0.3 | Prevents new-to-GR customers from being penalised on 15% of score |

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
    │   ├── scoring_ml.py            # Two XGBoost models → c360_scored_offers
    │   ├── model_standard.pkl       # Saved standard propensity model
    │   ├── model_gr.pkl             # Saved GR propensity model
    │   ├── model_metadata.json      # Standard model AUC + feature importances
    │   └── model_gr_metadata.json   # GR model AUC + feature importances
    └── api/main.py                  # FastAPI REST API — port 8000
```

---

## Next Steps

- [ ] **SHAP values** — per-prediction feature contribution on Compare Models page (Phase 4c)
- [ ] **More GR tier screenshots** — only 100–1200 pts modelled; real app may have more variants per tier
- [ ] **Transfer to office laptop** — `smartrewards_dump.sql` exists at project root

### Backlog (time permitting)

- [ ] **Expand Dept Reward Catalog to Match Affinity**
  - Add dept rewards for Deli, Seafood, Dairy, Frozen, Grocery (currently only Bakery/Produce/Meat have dept rewards)
  - Root cause: $7 Off Produce ranks first for HH00005 because `discount_value` dominates and no Deli dept reward exists despite Deli being HH00005's top affinity category
  - Requires adding new offer templates to `generate_data.py`, re-seeding, and retraining both models

- [ ] **Offer Management System — Dynamic Offers**
  - **Admin UI**: Streamlit page for business users to create/edit/deactivate offers (CRUD on `c360_offer`)
  - **Dynamic Trigger Engine**: Auto-generate personalised offers based on DB signals (win-back, churn prevention, lapsed category, points expiry, FreshPass upsell)
  - **Offer Performance Dashboard**: clip rate, redemption rate, revenue impact per offer

- [ ] **Split Propensity Model — persist to Feature Weight Studio**
  - Feature Weight Studio currently session-only
  - Future: allow saving a named weight configuration to DB and re-running scoring with custom weights

- [ ] **Login Dropdown — Real Customer Names**
  - Replace `household_id` prefix with `full_name` in login page and sidebar switcher

- [ ] **LTV Aggregate Refresh Job**
  - `c360_customer_ltv_txn_agg` is computed once at seed time; needs a refresh job once real transaction flow exists

- [ ] **Transaction Flow → Redemption Pipeline** *(teammate build)*
  - Checkout flow writing to `c360_txn`, `c360_txn_upc`, `c360_redemptions`
  - Integration point: `c360_redemptions` schema already in place

- [x] **UI Visual Refresh — Phase 1 complete**
  - Category icons (emoji), discount badge colouring, login card, sidebar tier badge, offer card redesign, expiry pills, My Rewards card alignment
  - Remaining: real product images (requires image hosting decision — deferred)

---

## Previous Sessions

### Session 8 — 2026-03-15
- UI Visual Refresh: category icons, discount badge colouring, login page card, sidebar tier badge, offer card redesign (My Offers + My Rewards), expiry pills

### Session 6 — 2026-03-10
- Split propensity model (standard + GR), My Rewards score-ranked, Feature Weight Studio built (rule-based only)

### Session 5 — 2026-03-08
- Expanded grocery catalog (Seafood + Deli departments, 64 offers, 71 UPCs)
- Full GR tier structure (25 real-structure offers, 8 tiers)
- Rule-based scoring fix for GR offers, My Rewards page, points deduction, sidebar customer switcher

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
