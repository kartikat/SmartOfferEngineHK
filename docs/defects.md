# SmartOfferEngine — Defects Log

All bugs identified and fixed across sessions. Ordered by session, then severity.

---

## Session 11 — 2026-03-18

### DEF-015 · Compare Models — Propensity (Standard) column empty
- **Severity:** High (silent — no error, just empty column)
- **Symptom:** Compare Models page showed no offers in the Propensity (Standard) column.
- **Root cause:** `render_model_comparison()` filtered `model_type == "propensity_standard"`, but DB stores `model_type = 'propensity'`. DEF-011 fixed the same bug on My Offers but missed this second occurrence.
- **Fix:** Changed filter to `model_type == "propensity"`.
- **File:** `files/app.py`

---

## Session 10 — 2026-03-18

### DEF-010 · Propensity (GR) model toggle misplaced on My Offers page
- **Severity:** Medium
- **Symptom:** My Offers had a `🎯 Propensity (GR)` radio option, which showed GR (Grocery Reward) offers in the standard offers list — a page intended for standard/fuel/points-multiplier offers only.
- **Root cause:** Model toggle on My Offers was designed before My Rewards page existed. GR model option was never removed when My Rewards became its own page.
- **Fix:** Removed GR option from My Offers radio. Added a `🎯 Propensity (XGBoost)` | `📋 Rule-Based` toggle directly on My Rewards where it belongs. `load_gr_scored_offers()` gained a `model_type` parameter.
- **File:** `files/app.py`

### DEF-011 · My Offers propensity model showed no results
- **Severity:** High (silent — no error, just empty page)
- **Symptom:** Selecting `🤖 Propensity (Standard)` on My Offers showed no offers.
- **Root cause:** Radio mapped `"(Standard)"` → `selected_model = "propensity_standard"`, but `c360_scored_offers` stores `model_type = 'propensity'`. Query returned zero rows silently.
- **Fix:** Changed mapping to `selected_model = "propensity"`.
- **File:** `files/app.py`

### DEF-012 · Sidebar buttons invisible (white on white)
- **Severity:** High (UI unusable)
- **Symptom:** Sign Out button and Auto Clip toggle buttons in the sidebar appeared blank/white. Text only visible on mouse hover.
- **Root cause:** Global sidebar CSS used `section[data-testid="stSidebar"] * { color: white !important }`. The `*` wildcard applied to all descendants including `<p>` and `<span>` inside `<button>` elements — white text on the default white button background.
- **Fix:** Replaced wildcard with targeted selectors (`p:not(button p)`, `span:not(button span)`, `label`, etc.). Added explicit ghost-button styling for sidebar buttons: semi-transparent white background, white border, white text.
- **File:** `files/app.py`

### DEF-013 · "None" displayed as category on My Rewards offer cards
- **Severity:** Low (cosmetic)
- **Symptom:** Category field on every Grocery Reward card showed the text "None" instead of an emoji icon.
- **Root cause:** `load_gr_scored_offers()` queried `o.categories_txt AS category`. The `categories_txt` column in `c360_offer` is NULL for all offers. The same bug had already been fixed for My Offers (via `c360_offer_summary.rep_category_nm`) but was not applied to the GR query.
- **Fix:** Added `LEFT JOIN c360_offer_summary` and switched to `COALESCE(os.rep_category_nm, '')`.
- **File:** `files/app.py`

### DEF-014 · Score breakdown expander crash on toggle
- **Severity:** High (page crash)
- **Symptom:** `TypeError: LayoutsMixin.expander() got an unexpected keyword argument 'open'` when toggling "Show Score Breakdown" on My Offers.
- **Root cause:** `st.expander(open=False)` uses the `open=` parameter introduced in Streamlit 1.58+. Project runs Streamlit 1.55.0 where the parameter is named `expanded=`.
- **Fix:** `st.expander(open=False)` → `st.expander(expanded=False)`.
- **File:** `files/app.py`

---

## Session 9 — 2026-03-15

### DEF-008 · DB connection fails on macOS after teammate's commit
- **Severity:** Critical (app won't start)
- **Symptom:** `sqlalchemy.exc.OperationalError: FATAL: role "postgres" does not exist` on app startup.
- **Root cause:** Teammate's "Feature Engineer UI" commit changed the default `DB_URL` in `app.py` and `api/main.py` to `postgresql://postgres@localhost/smartrewards`. The `postgres` superuser role exists on Windows PostgreSQL installs but not on macOS Homebrew PostgreSQL (which uses the OS username).
- **Fix:** Reverted both files to `postgresql://localhost/smartrewards` (no explicit user). `DATABASE_URL` env var override still works for both platforms.
- **Files:** `files/app.py`, `files/api/main.py`

### DEF-009 · Feature Engineer retrains disconnected model — no effect on UI
- **Severity:** High (feature non-functional)
- **Symptom:** Clicking "Apply Changes & Retrain Models" on the Feature Engineer page completed without error but My Offers / My Rewards rankings were unchanged.
- **Root cause:** Feature Engineer was wired to `scoring_ml_split.py` (teammate's experimental engine). `scoring_ml_split.py` writes to a separate model; the UI reads from `c360_scored_offers` which is populated by `scoring_ml.py`. The two engines are completely independent.
- **Fix:** Rewired Feature Engineer to read `FEATURE_COLS_STANDARD`/`FEATURE_COLS_GR` from `scoring_ml.py`, write changes back to `scoring_ml.py`, and run `scoring_ml.py --retrain` via subprocess. `load_model_metadata()` updated to read `model_metadata.json` + `model_gr_metadata.json` instead of `model_metadata_split.json`.
- **File:** `files/app.py`

---

## Session 8 — 2026-03-15

### DEF-007 · Category icons not resolving — all offers showed default icon
- **Severity:** Low (cosmetic)
- **Symptom:** Every offer card showed the default `🛒` icon regardless of category.
- **Root cause:** `category_icon()` was called with `row.get("categories_txt")` from `c360_offer`. The `categories_txt` column is NULL for all offers in the DB.
- **Fix:** Added `LEFT JOIN c360_offer_summary` to `load_scored()` and pulled `rep_category_nm` as `category_nm` instead (e.g. "Dairy", "Produce", "Bakery"). Column is populated for all offers.
- **File:** `files/app.py`

---

## Session 7 — 2026-03-10

### DEF-005 · High-balance customers got 0 standard offers (GR crowding)
- **Severity:** High (core feature broken for key demo customers)
- **Symptom:** Customers with 2,900+ pts (e.g. HH00118) saw 0 standard offers on My Offers. All 15 scored slots were occupied by GR offers.
- **Root cause:** `scoring.py` and `scoring_ml.py` both used a single `TOP_N_OFFERS=15` pool. High-balance customers were eligible for all 8 GR tiers × 3 offer types = potentially many GR offers, which outscored standard offers and filled all 15 slots.
- **Fix:** Replaced `TOP_N_OFFERS=15` with `TOP_N_STANDARD=10` + `TOP_N_GR=5`. Both engines now split scored offers by `discount_type_cd` and rank standard and GR pools independently. Every household guaranteed up to 10 standard + 5 GR offers.
- **Files:** `files/engine/scoring.py`, `files/engine/scoring_ml.py`

### DEF-006 · Feature Weight Studio showed non-zero rank deltas at 100% default weights
- **Severity:** Medium (confusing demo behaviour)
- **Symptom:** On the Rule-Based tab of Feature Weight Studio, with all sliders at 100% (default), offers showed rank changes like ▲6 — as if weights had already been adjusted.
- **Root cause:** `orig_rank` used the stored `rank` column from `c360_scored_offers`, which was an absolute rank across all 15 offers (including GR ranked above standard). After filtering to standard-only offers, offer #7 (absolute) might become #1 in the standard-only subset — creating a false delta.
- **Fix:** After filtering to standard-only offers, re-numbered `orig_rank` as 1, 2, 3… within the subset before merging with custom scores. Delta = 0 at default weights.
- **File:** `files/app.py`

### DEF-004 · Points features in standard propensity model (noise / data leakage)
- **Severity:** Medium (model quality)
- **Symptom:** `current_point_balance`, `points_expiring_next_month`, and `points_gap` were present in `FEATURE_COLS_STANDARD`. Standard offers don't require points to redeem, so these signals are meaningless for predicting standard offer redemption.
- **Root cause:** `points_gap` for a standard offer = `current_point_balance - 0` (NULL threshold filled with 0), a meaningless duplicate of `current_point_balance`. All three were copied from the original combined feature set without filtering.
- **Fix:** Removed all three from `FEATURE_COLS_STANDARD`. Standard model reduced from 19 → 16 features. AUC improved from 0.522 (combined) to 0.626.
- **File:** `files/engine/scoring_ml.py`

---

## Session 5 — 2026-03-08

### DEF-003 · Rule-based GR scoring used wrong formula (channel match instead of points signals)
- **Severity:** High (GR offers mispriced)
- **Symptom:** GR offer scores did not reflect customer points balance — a customer with 100 pts and one with 2,900 pts received similar GR scores.
- **Root cause:** GR offers were scored through Path 1 (standard formula: channel match 25%, cart affinity 15%, demographic 10%) rather than a points-weighted formula. GR redemption requires spending points, not channel alignment.
- **Fix:** Added Path 2 scoring in `scoring.py` for `program_type = 'Grocery Reward'`: hard gate on `current_point_balance < tier_1_points_threshold`, then points eligibility 40% / category affinity 25% / value-per-point 15% / GR history 15% / recency 5%. Expiry multiplier ×1.3.
- **File:** `files/engine/scoring.py`

---

## Session 3 — 2026-03-07

### DEF-001 · App crashed on missing CSV files after PostgreSQL migration
- **Severity:** Critical
- **Symptom:** All four components (generator, scoring, API, UI) failed to start after migration to PostgreSQL — still referencing CSV file paths.
- **Root cause:** Migration was incomplete; data loading logic still used `pd.read_csv()` and local file paths.
- **Fix:** Rewrote all four components to use SQLAlchemy + `pd.read_sql()` against the `smartrewards` PostgreSQL DB.
- **Files:** `files/data/generate_data.py`, `files/engine/scoring.py`, `files/api/main.py`, `files/app.py`

### DEF-002 · `retail_customer_uuid` used as scoring unit instead of `household_id`
- **Severity:** Medium (incorrect offer personalisation)
- **Symptom:** Each member of a household received different offers instead of household-level offers. Scoring was fragmented across individual UUIDs.
- **Root cause:** Initial implementation joined on `retail_customer_uuid` rather than `household_id`. Albertsons C360 scores at the household level — individual members share one offer set.
- **Fix:** All scoring queries changed to filter `head_household_ind = TRUE` and join/group on `household_id`. `c360_scored_offers` PK changed to `(household_id, client_offer_id, model_type)`.
- **Files:** `files/engine/scoring.py`, `files/engine/scoring_ml.py`, `files/app.py`

---

## Summary

| ID | Session | Severity | Component | Description |
|---|---|---|---|---|
| DEF-001 | 3 | Critical | All | CSV paths after PostgreSQL migration |
| DEF-002 | 3 | Medium | Scoring, UI | Wrong scoring unit (`uuid` vs `household_id`) |
| DEF-003 | 5 | High | Rule-based engine | GR offers scored with standard formula |
| DEF-004 | 7 | Medium | ML model | Points features in standard propensity model |
| DEF-005 | 7 | High | Scoring engines | GR crowding out standard offers (single pool) |
| DEF-006 | 7 | Medium | UI | Feature Weight Studio false rank deltas at default weights |
| DEF-007 | 8 | Low | UI | Category icons not resolving (`categories_txt` NULL) |
| DEF-008 | 9 | Critical | DB connection | `postgres` role missing on macOS |
| DEF-009 | 9 | High | Feature Engineer | Retraining disconnected engine (`scoring_ml_split.py`) |
| DEF-010 | 10 | Medium | UI | GR model toggle on wrong page (My Offers vs My Rewards) |
| DEF-011 | 10 | High | UI | Propensity model type mismatch — empty results |
| DEF-012 | 10 | High | UI | Sidebar buttons invisible (CSS wildcard) |
| DEF-013 | 10 | Low | UI | "None" category on My Rewards cards |
| DEF-014 | 10 | High | UI | `expander(open=)` crash on Streamlit 1.55.0 |
| DEF-015 | 11 | High | UI | Compare Models Propensity (Standard) column empty — `propensity_standard` model_type mismatch |
