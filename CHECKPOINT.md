# SmartOfferEngine — Session Checkpoint

> Updated after each `/checkpoint` command. Reflects the latest state of the project.

---

## Project
**SmartOfferEngine** — AI-powered personalised loyalty offer engine for Albertsons *for U* program.
- Stack: Python, FastAPI, Streamlit 1.55.0, PostgreSQL 16 (Homebrew)
- Purpose: Hackathon demo

---

## Session 16 — 2026-03-23

### What was done

#### 1. Analyst View — Customer tabs added

- Analyst view sidebar now shows two separate radio groups:
  - **Customer View**: My Offers · My Rewards · My Clipped Offers · My Profile
  - **Analyst Tools**: Problem Exploration · Segment Explorer · Compare Customers · Compare Models · Feature Weight Studio · Feature Engineer · How Offers Are Scored · Demo Script
- Each radio uses `on_change` callback to update `st.session_state.nav_page` directly — avoids interference between the two groups
- Analyst can now browse both customer-facing and analyst pages without switching personas

#### 2. My Offers — Redesigned to match real Albertsons "Recommended for U" layout

- **3-column grid**: offers grouped in rows of 3 using `st.columns(3, gap="medium")`
- **Card design** matches real Albertsons for U site:
  - `for U` badge (blue) + discount value in blue (`$1.00 off`) at top
  - Product name + category text on left, category image (76×76) on right
  - "Offer Details" link text
  - Divider line + "✓ Clipped" bottom-left + "Unlimited use / Expires Xd" bottom-right
- **Removed** from cards: rank number (#1 #2), score bar, channel pill
- **Clip button**: `"Add"` → `"Clip"` (blue, `type="primary"`, inside column grid)
- Default offers shown changed from 5 → 6 (slider: 3/6/9 step)
- Header changed: `"My Personalised Offers"` → removed (no subheader)

#### 3. Customer switcher — moved into blue ribbon

- Removed from sidebar
- Placed as second row of blue header ribbon (directly below top row)
- Uses CSS `:has(.abs-header) + stVerticalBlockBorderWrapper` to apply blue background, white label, semi-transparent select box
- Right-aligned using `st.columns([1, 1])` — selectbox in right column

#### 4. Customer feature tags

- Added `customer_feature_tags(customer)` function — returns coloured pill HTML chips
- Rendered at top of My Offers page above the offer grid
- Tags derived from `c360_customer_profile` fields:
  - ⭐ for U+ · 🔁 Frequent Buyer · 🛒 Regular Shopper · 📱 Online/eCommerce · ⛽ Fuel Rewards
  - 🥩 Meat · 🥛 Dairy · 🥦 Produce · 🐟 Seafood · 🍞 Bakery · 🧊 Frozen Buyer
  - 👨‍👩‍👧 Family · 🌱 [diet] · ⚠️ Churn Risk
- Added 6 purchase indicator columns to `load_customers()` query: `meat_purchase_ind_6m`, `produce_purchase_ind_6m`, `bakery_purchase_ind_6m`, `seafood_purchase_ind_6m`, `frozen_grocery_purchase_ind_6m`, `grocery_purchase_ind_6m`

#### 5. Button colour changes

- **Clip button** (offer grid): blue (`#00529B`) — inside `stHorizontalBlock` columns
- **Simulate Purchase button**: orange (`#EA580C`) — outside columns, caught by default primary rule
- CSS logic: primary buttons default to orange; primary buttons inside `stHorizontalBlock` override to blue

---

## Session 15 — 2026-03-23

### What was done

#### 1. Presentation UI Polish — text sizing and spacing

- **Enlarged demo slide images**: Increased proportional height from 400px to 500px for App View (prod_screenshot.png) and Web View (webView.jpg)
- **Fixed text truncation in presenter panel**: Removed 300-char limit on narration; CSS word-wrap added; panel height increased 420px → 600px
- **Problem Exploration page condensed**: Reduced bullet verbosity 30–40%

#### 2. Top-of-page whitespace reduction

- Aggressive CSS rules: `.main { margin-top: -40px }`, `stMain { margin-top: -50px }`, first `stVerticalBlockBorderWrapper { margin-top: -50px }`
- ~50% reduction in white space above main content

#### 3. Hide button repositioning

- Moved to top-right of presenter panel using `margin-top: -48px` negative margin

---

## Session 14 — 2026-03-20

### What was done

#### 1. Tech stack pills in demo panel

- Six frosted-glass pills: 🐍 Python · ⚡ FastAPI · 🎈 Streamlit · 🤖 XGBoost · 🐘 PostgreSQL · ☁️ C360 Schema

#### 2. Architecture diagram on Step 5

- `docs/images/01_system_overview.png` renders below business impact cards on the last demo slide

#### 3. Problem Exploration page

- First item in Analyst View nav
- Two-column persona layout: Customer (Alex) + Business User (Jordan) with pain points and needs
- Gap banner: *"The data to personalise at scale already exists. SmartOfferEngine adds one new table: `c360_scored_offers`."*
- First bullet updated to: "Scripts manually rank hundreds of offers monthly — time-consuming and still feels like guessing"

---

## Session 13 — 2026-03-20

### What was done

#### 1. Persistent demo panel — 50% width, collapsible

- `🎬 Present` sidebar button → 50/50 split: live app left, dark-blue presenter panel right
- Panel shows: step dots, tag, title, narration, 3 talking points, navigate badge, tech stack pills
- `← Back` / `Next →` auto-navigates left pane and switches persona
- `◀ Hide` collapses; `▶` re-expands

#### 2. One-click Simulate Purchase CTA

- `🛒 Simulate: Customer just bought Meat ($45)` — inserts `c360_txn` + `c360_txn_upc`, boosts Meat affinity +0.30, re-runs `scoring.py`, shows rank delta banner

---

## Current State

**Full stack running. 64 offers across 10 departments. Three scoring models live.**

```
generate_data.py  →  PostgreSQL (18 tables, 64 offers, 71 UPCs)
                          ↓
scoring.py        →  c360_scored_offers (rule_based)
scoring_ml.py     →  c360_scored_offers (propensity + propensity_gr)
                          ↓
app.py (UI)       →  reads PostgreSQL directly   (port 8501)
main.py (API)     →  serves from c360_scored_offers  (port 8000)
```

**Standard propensity model:** CV AUC 0.626, 16 features, top: `channel_match`, `instacart`, `redemption_rate`
**GR propensity model:** CV AUC 0.572, 12 features, top: `discount_value`, `points_gap`, `points_expiring_next_month`

---

## How to Resume

```bash
cd /Users/KartikaT/HackathonProject
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Verify DB
psql smartrewards -c "SELECT model_type, COUNT(*) FROM c360_scored_offers GROUP BY model_type;"
# expect: rule_based≈1797, propensity=1200, propensity_gr=600

# Re-seed if needed:
python3 files/data/generate_data.py
python3 files/engine/scoring.py
python3 files/engine/scoring_ml.py --retrain

# Start UI:
streamlit run files/app.py --server.headless true

# Good demo customers:
# HH00118 — 2,977 pts, 4U+  (eligible for all 8 GR tiers)
# HH00116 — 2,916 pts, 4U+
# HH00017 — 2,907 pts, Standard
```

---

## Key Decisions

| Decision | Rationale |
|---|---|
| Offer cards match real Albertsons for U design | Demo authenticity — judges recognise the real UI pattern |
| Feature tags from raw profile fields, not model features | Easier to explain to non-technical audience; model uses aggregated signals |
| Clip buttons blue, Simulate button orange | Visual distinction: blue = core action, orange = demo/simulation action |
| Customer switcher inside blue ribbon | Cleaner layout — account context always visible with the header |
| Analyst view includes customer tabs | Analyst needs to see what the customer sees without switching persona |
| Feature Engineer wired to `scoring_ml.py` not `scoring_ml_split.py` | `scoring_ml.py` is the production engine whose output the UI reads |
| DB_URL default uses no explicit user | Homebrew PostgreSQL uses OS username; `postgres` role doesn't exist on macOS |
| Points features removed from standard propensity model | Standard offers don't require points to redeem |
| Separate scoring pools: 10 standard + 5 GR | Prevents GR offers crowding out standard offers for high-balance customers |

---

## File Map

```
HackathonProject/
├── CLAUDE.md                        # Architecture + commands (always read this first)
├── CHECKPOINT.md                    # This file
├── README.md                        # Project overview, quick start, API reference
├── requirements.txt                 # Pinned Python dependencies
├── docs/
│   ├── architecture.md
│   ├── propensity_model.md
│   ├── scoring_engine.md
│   ├── data_model.md
│   ├── ml_roadmap.md
│   ├── productionalization.md
│   └── images/
├── files/assets/
│   ├── prod_screenshot.png
│   ├── albertsons_icon.png
│   ├── category_images.py           # 9 real Albertsons dept photos, base64
│   └── categories/                  # Source JPEGs
├── tests/
│   └── test_scoring.py              # 59 unit tests (no DB)
└── files/
    ├── app.py                       # Streamlit UI — port 8501
    ├── db/schema.sql
    ├── data/generate_data.py
    ├── engine/
    │   ├── scoring.py               # Rule-based engine
    │   ├── scoring_ml.py            # Two XGBoost models (PRODUCTION)
    │   ├── scoring_ml_split.py      # Teammate's experimental — NOT used by UI
    │   ├── model_standard.pkl
    │   ├── model_gr.pkl
    │   ├── model_metadata.json
    │   └── model_gr_metadata.json
    └── api/main.py                  # FastAPI REST API — port 8000
```

---

## Next Steps

- [ ] **Embedding model (Phase 4c)** — deferred; needs 10k+ co-redemption rows; plan: expand `generate_data.py` to 500 households
- [ ] **Transfer to office laptop** — `smartrewards_dump.sql` exists at project root
- [ ] **SHAP values (Phase 4e)** — deprioritised

### Backlog

- [ ] Expand Dept Reward Catalog to match affinity (add Deli, Seafood, Dairy, Frozen, Grocery dept rewards)
- [ ] Offer Management System — Admin UI for CRUD on `c360_offer`
- [ ] LTV Aggregate Refresh Job
- [ ] Transaction Flow → Redemption Pipeline (teammate build)

### Completed

- [x] Offer card redesign — matches real Albertsons for U layout (3-col grid, for U badge, blue discount text)
- [x] Customer feature tags (14 tag types from profile fields)
- [x] Customer switcher inside blue ribbon, right-aligned
- [x] Analyst view includes customer tabs
- [x] Button colours: Clip=blue, Simulate=orange
- [x] Login Dropdown — real customer names
- [x] Compare Models Propensity column fix (DEF-015)
- [x] 59 unit tests for rule-based scoring
- [x] Demo script rebuilt for 3-min pitch
- [x] Persona toggle (Customer / Analyst)
- [x] Real Albertsons category photos (9 departments)
- [x] Feature Engineer wired to production engine
- [x] Productionalization roadmap doc
