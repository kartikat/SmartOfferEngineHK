# SmartOfferEngine — Session Checkpoint

> Updated after each `/checkpoint` command. Reflects the latest state of the project.

---

## Project
**SmartOfferEngine** — AI-powered personalised loyalty offer engine for Albertsons *for U* program.
- Stack: Python, FastAPI, Streamlit 1.55.0, PostgreSQL 16 (Homebrew)
- Purpose: Hackathon demo

---

## Session 14 — 2026-03-20

### What was done

#### 1. Tech stack pills in demo panel

- Added "Built with" section at the bottom of the presenter panel, separated by a subtle divider line
- Six frosted-glass pills always visible on every demo step: 🐍 Python · ⚡ FastAPI · 🎈 Streamlit · 🤖 XGBoost · 🐘 PostgreSQL · ☁️ C360 Schema

#### 2. Architecture diagram on Step 5 (last demo slide)

- `docs/images/01_system_overview.png` (1904×1289) renders below the business impact cards on the "What This Unlocks" slide
- "System Architecture" label in small caps above the image
- Visible in both demo mode (left 50% column) and normal Demo Script view

#### 3. Problem Exploration page — new Analyst View nav item

- First item in Analyst View nav, leads the story before any live demo
- Two-column persona layout:
  - **Left — Customer (Alex, for U+)**: blue card with 5 pain points + 4 needs (527 offers overwhelming, same Bakery promo for everyone, 2,800 points expiring unnoticed, clips 3–4 and ignores the rest, no signal 4U+ matters)
  - **Right — Business User (Jordan, Loyalty Manager)**: purple card with 5 pain points + 4 needs (manual weekly ranking, no redemption signal, ~30% points breakage, lapsed = loyal same campaign, C360 data unused)
- Bottom: Albertsons blue gap banner — *"The data to personalise at scale already exists. SmartOfferEngine adds one new table: `c360_scored_offers`."*
- `render_problem_exploration()` function; dispatch added to `_dispatch_page()`

---

## Session 13 — 2026-03-20

### What was done

#### 1. Persistent demo panel — 50% width, collapsible

- `🎬 Present` button in sidebar (above Sign Out) enters presentation mode
- Content area splits 50/50: live app on left, dark-blue presenter panel on right
- Panel shows: `🎬 PRESENTING` badge, step dots, step tag, title, narration excerpt, 3 talking points, `📍 Navigate to:` badge
- `← Back` / `Next →` buttons auto-navigate the left pane AND switch persona:
  - Step 1 → Demo Script (production screenshot)
  - Step 2 → Segment Explorer (live C360 stats)
  - Step 3 → Compare Customers (side-by-side rankings)
  - Step 4 → Compare Models (AI vs rule-based deltas)
  - Step 5 → Demo Script (business impact cards)
- `◀ Hide` button in panel collapses it to full-width; small `▶` button top-right re-expands
- `⏹ Exit Presentation` restores normal full-width layout
- `demo_panel_open` resets to True on every new presentation start
- `render_demo_script()` in demo mode renders only visual content — narration/talking points move to panel; full script preserved in non-demo mode
- DEMO_STEPS updated with `nav_page` and `persona` fields per step
- Sidebar radios made index-controlled from `st.session_state.nav_page` so panel Next/Prev can drive navigation

#### 2. One-click Simulate Purchase CTA on My Offers

- Pre-scripted: `🛒 Simulate: Customer just bought Meat ($45)` — single blue primary button at top of My Offers page
- On click:
  1. Inserts `c360_txn` header record (txn_dte, net_sales, gross_amt, item_qty, ecom_ind)
  2. Inserts `c360_txn_upc` line item (upc_id from Meat department, household_id, store_id)
  3. Updates `c360_cat_affinity` — boosts Meat affinity by +0.30 (capped at 1.0); inserts row if none exists
  4. Re-runs `files/engine/scoring.py` via subprocess (~1.1s for 120 households)
  5. Clears `load_scored` cache — page rerenders with fresh rankings
- Green delta banner shows after rerender: which offers moved up (▲) and down (▼) with rank changes
- `↺ Reset simulation` button clears the delta state
- Demo story: *"Watch the engine react — Meat offers jump to #1 and #2 the moment this customer makes a purchase. This is the real-time trigger from the C360 transaction stream."*
- Bug fixed: initial version used wrong column names (`upc_cd`, `dept_dsc`, `unit_price_amt`) — corrected to actual schema (`upc_id`, `department_nm`; transaction tables use `txn_dte`, `net_sales`, `gross_amt`, `item_qty`, `ecom_ind`)
- Session state keys: `sim_before_{hid}`, `sim_done_{hid}` — scoped per household so switching customers resets state

---

## Session 12 — 2026-03-20

### What was done

#### 1. Real Albertsons category images — replaced all emoji icons

- Fetched 9 real department photos from the Albertsons CDN (`images.albertsons-media.com`) using browser-like request headers
- Categories covered: Produce, Meat, Bakery, Deli, Frozen, Seafood, Dairy, Grocery, Household
- Fuel has no accessible image on the CDN — falls back to ⛽ emoji
- Each image center-cropped to square and resized to 56×56 JPEG thumbnail
- All 9 images encoded as base64 JPEG and stored in `files/assets/category_images.py`
  - File loaded at startup via `importlib.util.spec_from_file_location` (keeps app.py clean)
  - Stored as `CATEGORY_IMG_B64: dict[str, str]`
- `CATEGORY_ICONS` dict replaced with `CATEGORY_KEY_MAP` — maps category keywords to image keys (or emoji fallback)
- `category_icon(category_nm, size=36)` now returns `<img src="data:image/jpeg;base64,..." width="36" height="36" style="border-radius:6px;" />` HTML for all 9 categories with real images
- Raw source photos saved in `files/assets/categories/` (bakery.jpg, dairy.jpg, deli.jpg, frozen.jpg, grocery.jpg, household.jpg, meat.jpg, produce.jpg, seafood.jpg)
- Both offer card renderers (My Offers line ~1003, My Rewards line ~1270) automatically pick up real images via `category_icon()` — no other changes needed

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

#### 4. Demo Script — rebuilt for 3-minute presentation

- Redesigned from 12 steps → 5 tight steps, ~45s each
- **Key message woven throughout:** "Your C360 data already has everything this needs"
- **Step 1:** Real Albertsons for U production screenshot (527 clipped offers) — "manually ranked, not personalised"
- **Step 2:** Problem framing with C360 stats (households, offers, scored pairs, models)
- **Step 3:** Same catalog, different rankings — Fuel vs for U+ live side-by-side Compare page
- **Step 4:** AI vs rule-based — Compare Models live with rank-change deltas
- **Step 5:** Business impact cards (redemption lift, breakage, one C360 table)
- Each step has tight narration + 3 presenter talking points
- Navigation: progress bar + step picker dropdown (jump to any step)
- Production screenshot saved to `files/assets/prod_screenshot.png`

#### 5. Customer / Analyst persona toggle

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
├── files/assets/
│   ├── prod_screenshot.png          # Real Albertsons for U app screenshot (Step 1 of demo)
│   ├── albertsons_icon.png          # Albertsons favicon (128×128) — used in browser tab, header, sidebar
│   ├── category_images.py           # 9 real Albertsons dept photos, 56×56 JPEG base64 thumbnails
│   └── categories/                  # Source images (bakery/dairy/deli/frozen/grocery/household/meat/produce/seafood.jpg)
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

- [ ] **Embedding model (Phase 4c)** — two-tower / matrix factorisation on `c360_redemptions`; can unblock by expanding `generate_data.py` with 500 households + 10k+ correlated synthetic redemptions (Option 1); teammate transaction flow not required for this
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

- [x] **UI Visual Refresh — Phase 2 complete**
  - Session 8: Category icons (emoji), discount badge colouring, login card, sidebar tier badge, offer card redesign, expiry pills
  - Session 12: Real Albertsons category photos replacing emoji icons (9 categories), My Rewards card alignment

- [x] **Feature Engineer — wired to production engine**
  - Now reads/writes `FEATURE_COLS_STANDARD` + `FEATURE_COLS_GR` from `scoring_ml.py`; retrains the models that actually feed the UI

---

## Previous Sessions

### Session 14 — 2026-03-20
- Tech stack pills in demo panel (Python · FastAPI · Streamlit · XGBoost · PostgreSQL · C360 Schema)
- Architecture diagram on Step 5 last slide (`01_system_overview.png`)
- Problem Exploration page — two persona cards (Customer + Business User) with pain points, needs, and gap banner

### Session 13 — 2026-03-20
- Persistent demo panel (50% width, collapsible) — `🎬 Present` sidebar button, auto-navigation per step
- One-click `🛒 Simulate Purchase` on My Offers — records Meat transaction, boosts affinity, re-scores (~1.1s), shows rank delta banner

### Session 12 — 2026-03-20
- Replaced all emoji category icons with real Albertsons department photos (9 categories from CDN)
- `category_icon()` now returns `<img>` HTML with base64-embedded 56×56 JPEG thumbnails

### Session 11 — 2026-03-18
- Login dropdown, sidebar switcher, Compare Customers dropdowns/headers, Segment Explorer picker — all now show real customer names in `"Full Name (HH00001)"` format
- Fixed Compare Models Propensity (Standard) column empty — `propensity_standard` model_type mismatch (DEF-015)
- Added 59 unit tests for rule-based scoring engine (`tests/test_scoring.py`) — no DB required, all passing
- Demo script rebuilt for 3-min pitch: 5 steps, real prod screenshot, talking points, progress bar, step picker
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
