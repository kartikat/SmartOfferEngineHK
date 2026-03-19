# SmartRewards — Session Checkpoint

> Updated after each `/checkpoint` command. Reflects the latest state of the project.

---

## Project
**SmartRewards** — AI-powered personalised loyalty offer engine for Albertsons *for U* program.
- Stack: Python, FastAPI, Streamlit 1.55.0, PostgreSQL 16 (Homebrew)
- Purpose: Hackathon demo

---

## Session 11 — 2026-03-18

### What was done

#### 1. Login dropdown — real customer names

- **Login page**: dropdown now shows `"Full Name (HH00001) | tier | pts"` format; `household_id` extracted from the `(...)` portion via `choice.split("(")[1].split(")")[0]`
- **Sidebar customer switcher**: updated from `"HH00001 | tier | Full Name"` to `"Full Name (HH00001) | tier | pts"` — consistent with login
- **Compare Customers dropdowns**: replaced raw `household_id` list with `"Full Name (HH00001)"` labels; `hid` resolved from label via `cmp_hid_map`
- **Compare Customers column headers**: `st.html('<div class="compare-header">...')` now shows name label instead of raw `hid_a`/`hid_b`
- **Segment Explorer "Sign in as"**: picker now shows `"Full Name (HH00001)"` labels; `full_name` also added as `Name` column in segment table display
- No DB changes needed — `full_name` (`first_nm || ' ' || last_nm`) was already in `load_customers()` query

#### 2. Fixed Compare Models — Propensity (Standard) column empty (DEF-015)

- `render_model_comparison()` was filtering `model_type == "propensity_standard"` — DB stores `model_type = 'propensity'`
- Same root cause as DEF-011 (fixed on My Offers in Session 10) but missed in the Compare Models function
- **Fix:** Changed filter to `model_type == "propensity"`
- **File:** `files/app.py`

#### 3. Unit tests — rule-based scoring engine

- Created `tests/test_scoring.py` — 59 tests, no DB required
- Covers all pure scoring functions: `score_transaction_affinity`, `score_redemption_match`, `score_points_eligibility`, `score_cart_affinity`, `score_demographic_match`, `score_standard_offer`, `score_grocery_reward`, `passes_business_rules`, `run_batch_scoring`
- All 59 passing (`python3 -m pytest tests/test_scoring.py -v`)

#### 4. Customer / Analyst persona toggle

- Sidebar gains two buttons: `🛒 Customer` and `📊 Analyst` — active persona shown as filled (primary), inactive as ghost
- **Customer View nav:** My Offers · My Rewards · My Clipped Offers · My Profile
- **Analyst View nav:** Segment Explorer · Compare Customers · Compare Models · Feature Weight Studio · Feature Engineer · How Offers Are Scored · Demo Script
- Coloured pill in page header reflects active persona (blue = Customer, purple = Analyst)
- Persona stored in `st.session_state.persona`; switching resets to first page of that view
- **File:** `files/app.py`

#### 5. Productionalization roadmap

- Created `docs/productionalization.md` — what needs to change to serve millions of customers
- Covers: BigQuery migration, distributed batch scoring (Dataflow/Spark), Vertex AI model training, Cloud Run API, frontend split (React Native + Retool), real-time triggers, monitoring, CCPA compliance
- Phased delivery plan P1→P5 with effort estimates and dependencies
- Key clarification: `c360_scored_offers` is a POC-built table, not an existing C360 asset

- `render_model_comparison()` was filtering `model_type == "propensity_standard"` — DB stores `model_type = 'propensity'`
- Same root cause as DEF-011 (fixed on My Offers in Session 10) but missed in the Compare Models function
- **Fix:** Changed filter to `model_type == "propensity"`
- **File:** `files/app.py`

---

## Session 10 — 2026-03-18

### What was done

#### 1. Moved Propensity (GR) model toggle to My Rewards

- `"🎯 Propensity (GR)"` option removed from My Offers radio — GR offers don't belong on the standard offers page
- My Offers radio is now just `📋 Rule-Based` | `🤖 Propensity (XGBoost)` (standard offers only)
- Fixed latent bug: radio was mapping `"(Standard)"` → `"propensity_standard"` but DB stores `model_type='propensity'` — nothing would have shown
- GR filter on My Offers is now unconditional (was previously guarded by `selected_model != "propensity_gr"`)
- **My Rewards** gains its own model toggle: `🎯 Propensity (XGBoost)` (default) | `📋 Rule-Based`, with model info banner
- `load_gr_scored_offers(hid, balance, model_type="propensity_gr")` — added `model_type` param so My Rewards can switch between `propensity_gr` and `rule_based`
- Caption on My Rewards updates to reflect active model ("personalised score" vs "rule-based score")

#### 2. Fixed white/invisible sidebar buttons

- **Root cause:** `section[data-testid="stSidebar"] * { color: white !important }` wildcard was overriding button text to white — white text on white button background = invisible
- Previous partial fix still caught `p` inside button elements
- **Fix:** added `:not(button p)` / `:not(button span)` to exclude button children from white text rule; explicitly styled sidebar buttons as ghost buttons: `rgba(255,255,255,0.15)` background, white border, white text, brightens on hover

#### 3. Fixed "None" category on My Rewards cards

- `load_gr_scored_offers` was using `o.categories_txt AS category` — NULL for all offers
- Fixed with `LEFT JOIN c360_offer_summary` + `COALESCE(os.rep_category_nm, '')` — same fix already in `load_scored()` for My Offers

#### 4. Fixed score breakdown expander crash

- `st.expander(open=False)` → `st.expander(expanded=False)` — `open=` not available in Streamlit 1.55.0

---

## Session 9 — 2026-03-15

### What was done

#### 1. Fixed DB connection string broken by teammate's commit

- Teammate's "Feature Engineer UI" commit changed the default `DB_URL` in `app.py` and `api/main.py` to `postgresql://postgres@localhost/smartrewards`
- `postgres` role doesn't exist on macOS Homebrew PostgreSQL — causes `OperationalError: role "postgres" does not exist`
- **Fix:** reverted both files to `postgresql://localhost/smartrewards` (no explicit user — uses OS username by default)
- Windows teammates can still override via `DATABASE_URL` env var

#### 2. Merged teammate's Feature Engineer UI (conflict resolution)

- Teammate pushed "Feature Engineer UI" commit while we had Session 8 (UI Visual Refresh) locally
- 6 conflicts resolved:
  - `CHECKPOINT.md` — kept both session entries
  - `scoring_ml.py` — kept our split-model `write_results` signature and GR scoring code (teammate's version had stale single-model calls)
  - `files/app.py` — merged nav menus: kept both "Feature Weight Studio" (ours) and "Feature Engineer" (teammate's)
  - Binary `.pkl` + `model_metadata.json` — kept our retrained model files
- Merged via `git pull --rebase` + manual conflict resolution

#### 3. Fixed Feature Engineer to use `scoring_ml.py` (production engine)

- **Root cause:** teammate's Feature Engineer was wired to `scoring_ml_split.py` — a separate, disconnected engine. Retraining via the UI had zero effect on what customers saw in My Offers / My Rewards.
- **`read_feature_cols()`** — now reads `FEATURE_COLS_STANDARD` (16) and `FEATURE_COLS_GR` (12) from `scoring_ml.py` using regex; returns `{"standard": [...], "gr": [...]}`
- **`write_feature_cols(selected_std, selected_gr)`** — now writes both lists back to `scoring_ml.py` via regex replacement; signature changed from single `selected_features` list
- **`load_model_metadata()`** — now reads `model_metadata.json` + `model_gr_metadata.json` (the actual production outputs) instead of `model_metadata_split.json`
- **`get_feature_categories()`** — reorganised from Customer/Offer/Interaction into **Standard Only / GR Only / Both Models** groups, reflecting the real split model design; 20 feature definitions with correct model applicability
- **`render_feature_engineer()`** — each feature now has separate **Standard** and **GR** checkboxes; 4-metric header (Standard AUC, GR AUC, Standard feature count, GR feature count); subprocess now runs `scoring_ml.py --retrain`
- Added `import sys` at top of `app.py` (needed for `sys.executable` in subprocess call)

#### 4. CLAUDE.md updated

- Added Feature Engineer to navigation page list
- Documented Feature Engineer: read/write flow, Standard Only / GR Only / Both Models grouping, permanent-vs-session-only distinction from Feature Weight Studio, warning that `scoring_ml_split.py` is disconnected

---

## Current State

**Full stack running. 64 offers across 10 departments. Three scoring models live. Feature Engineer now wired to production engine.**

```
generate_data.py  →  PostgreSQL (18 tables, 64 offers, 71 UPCs)
                          ↓
scoring.py        →  c360_scored_offers (1,797 rows — 10 standard + 5 GR per HH, rule_based)
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
| Feature Engineer wired to `scoring_ml.py` not `scoring_ml_split.py` | `scoring_ml.py` is the production engine whose output (`c360_scored_offers`) the UI reads; `scoring_ml_split.py` is a teammate's disconnected experiment |
| Feature Engineer shows Standard Only / GR Only / Both Models groups | Reflects real split model design; prevents confusion about which features apply to which model |
| DB_URL default uses no explicit user (`postgresql://localhost/smartrewards`) | Homebrew PostgreSQL uses OS username; `postgres` role doesn't exist on macOS. Windows teammates override via `DATABASE_URL` env var |
| Points features removed from standard propensity model | Standard offers don't require points to redeem — `points_gap` was just a noisy copy of `current_point_balance` |
| Separate scoring pools: 10 standard + 5 GR | Prevents GR offers from crowding out standard offers for high-balance customers |
| Feature Weight Studio is session-only | "What-if" exploration tool — no retraining, no DB writes; contrast with Feature Engineer which does real retraining |
| My Rewards uses propensity_gr score not tier tabs | Score-based ranking is more personalised; customers see their best-value GR offers first regardless of tier |
| GR offers excluded from standard ranked list | Different product — you *spend* points, not receive discounts |
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
│   ├── architecture.md              # 5 Mermaid diagrams (updated Session 9)
│   ├── propensity_model.md          # Full ML training documentation
│   ├── scoring_engine.md            # Both scoring paths with formulas
│   ├── data_model.md                # 18-table schema reference
│   ├── ml_roadmap.md                # Phase 4 ML upgrade plan
│   ├── productionalization.md       # What needs to change for production at scale
│   └── images/                      # Rendered PNG diagrams
├── tests/
│   └── test_scoring.py              # 59 unit tests for rule-based scoring (no DB)
└── files/
    ├── app.py                       # Streamlit UI — port 8501
    ├── db/schema.sql                # All 18 table definitions
    ├── data/generate_data.py        # Seeds all 18 tables
    ├── engine/
    │   ├── scoring.py               # Rule-based engine → c360_scored_offers
    │   ├── scoring_ml.py            # Two XGBoost models → c360_scored_offers (PRODUCTION)
    │   ├── scoring_ml_split.py      # Teammate's experimental engine — NOT used by UI
    │   ├── model_standard.pkl       # Saved standard propensity model
    │   ├── model_gr.pkl             # Saved GR propensity model
    │   ├── model_metadata.json      # Standard model AUC + feature importances
    │   └── model_gr_metadata.json   # GR model AUC + feature importances
    └── api/main.py                  # FastAPI REST API — port 8000
```

---

## Next Steps

- [ ] **Embedding model (Phase 4c)** — two-tower / matrix factorisation on `c360_redemptions`; blocked on >10k real redemption events (teammate transaction flow build)
- [ ] **Transfer to office laptop** — `smartrewards_dump.sql` exists at project root
- [ ] **SHAP values (Phase 4e)** — deprioritised; revisit after team reviews SHAP theory (SHapley Additive exPlanations)

### Backlog (time permitting)

- [ ] **Expand Dept Reward Catalog to Match Affinity**
  - Add dept rewards for Deli, Seafood, Dairy, Frozen, Grocery (currently only Bakery/Produce/Meat have dept rewards)
  - Root cause: $7 Off Produce ranks first for HH00005 because `discount_value` dominates and no Deli dept reward exists despite Deli being HH00005's top affinity category
  - Requires adding new offer templates to `generate_data.py`, re-seeding, and retraining both models

- [ ] **Offer Management System — Dynamic Offers**
  - **Admin UI**: Streamlit page for business users to create/edit/deactivate offers (CRUD on `c360_offer`)
  - **Dynamic Trigger Engine**: Auto-generate personalised offers based on DB signals (win-back, churn prevention, lapsed category, points expiry, FreshPass upsell)
  - **Offer Performance Dashboard**: clip rate, redemption rate, revenue impact per offer

- [x] **Login Dropdown — Real Customer Names**
  - Login, sidebar, Compare Customers, Segment Explorer all show `"Full Name (HH00001)"` format

- [ ] **LTV Aggregate Refresh Job**
  - `c360_customer_ltv_txn_agg` is computed once at seed time; needs a refresh job once real transaction flow exists

- [ ] **Transaction Flow → Redemption Pipeline** *(teammate build)*
  - Checkout flow writing to `c360_txn`, `c360_txn_upc`, `c360_redemptions`
  - Integration point: `c360_redemptions` schema already in place

- [x] **UI Visual Refresh — Phase 1 complete**
  - Category icons (emoji), discount badge colouring, login card, sidebar tier badge, offer card redesign, expiry pills, My Rewards card alignment

- [x] **Feature Engineer — wired to production engine**
  - Now reads/writes `FEATURE_COLS_STANDARD` + `FEATURE_COLS_GR` from `scoring_ml.py`; retrains the models that actually feed the UI

---

## Previous Sessions

### Session 11 — 2026-03-18
- Login dropdown, sidebar switcher, Compare Customers dropdowns/headers, Segment Explorer picker — all now show real customer names in `"Full Name (HH00001)"` format
- Fixed Compare Models Propensity (Standard) column empty — `propensity_standard` model_type mismatch (DEF-015)
- Added 59 unit tests for rule-based scoring engine (`tests/test_scoring.py`) — no DB required, all passing
- Customer / Analyst persona toggle in sidebar with coloured header pill
- Created `docs/productionalization.md` — full production roadmap (infra, ML, API, frontend, monitoring, compliance)

### Session 10 — 2026-03-18
- Moved Propensity (GR) toggle from My Offers to My Rewards; fixed `propensity_standard` → `propensity` model_type bug
- Fixed invisible sidebar buttons (CSS wildcard override); fixed "None" category on My Rewards cards; fixed `expander(open=)` crash

### Session 9 — 2026-03-15
- Fixed DB_URL `postgres` role error (teammate's commit broke macOS)
- Resolved 6-way merge conflict from teammate's Feature Engineer UI commit
- Fixed Feature Engineer to use `scoring_ml.py` (was wired to disconnected `scoring_ml_split.py`)
- CLAUDE.md updated with Feature Engineer documentation

### Session 8 — 2026-03-15
- UI Visual Refresh: category icons, discount badge colouring, login page card, sidebar tier badge, offer card redesign (My Offers + My Rewards), expiry pills

### Session 7 (teammate) — 2026-03-10
- Feature Engineer UI page: business-friendly feature management, retraining via UI (initially wired to `scoring_ml_split.py`)

### Session 6 — 2026-03-10 (us)
- Split propensity model (standard + GR), My Rewards score-ranked, Feature Weight Studio built (rule-based + propensity tabs), separate scoring pools bug fix

### Session 5 — 2026-03-08
- Expanded grocery catalog (Seafood + Deli departments, 64 offers, 71 UPCs)
- Full GR tier structure (25 real-structure offers, 8 tiers)
- Rule-based scoring fix for GR offers, My Rewards page, points deduction, sidebar customer switcher

### Session 4 — 2026-03-07
- Architecture diagrams (5 Mermaid), README, docs/how_we_built_it.md, docs/project_phases.md

### Session 3 — 2026-03-07
- Full stack migrated from CSVs → PostgreSQL
- Rewrote all 4 components: data generator, scoring engine, FastAPI, Streamlit UI

### Sessions 1–2 — 2026-03-05
- Schema design (18 tables), Streamlit UI foundation, Albertsons branding, Demo Script, real Safeway product data
