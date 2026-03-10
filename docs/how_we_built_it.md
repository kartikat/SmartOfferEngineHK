# How We Built SmartRewards

> A record of the collaboration between Kartika and Claude Code across 3 sessions to build SmartRewards from scratch for the Albertsons hackathon.

---

## The Starting Point

The project began with a simple brief: build an AI-powered personalised offer engine on top of the Albertsons *for U* loyalty program for a hackathon demo.

What existed at the start:
- A basic Python scoring engine (`scoring.py`) reading from CSVs
- A simple data generator (`generate_data.py`) producing synthetic customers and offers
- A stub FastAPI (`main.py`)
- No UI, no database, no real data

What we needed to build:
- A proper PostgreSQL schema mirroring the real Albertsons C360 data model
- A Streamlit demo UI good enough to present to judges
- Real or realistic data to make the demo credible
- A scoring engine that reflected how Albertsons actually thinks about offer relevance

---

## Session 1 — The UI First

**Date: 2026-03-05**

The first decision was to build the demo UI before worrying about the database. The reasoning: a working UI that judges can click through is worth more than a perfect backend they can't see. We could always swap the data layer later.

### What we built

We started by studying the existing codebase — the scoring rules, data shape, offer categories — and then built the full Streamlit UI in one session:

**Login screen** — a customer selector dropdown showing tier, channel, and points balance. Judges could sign in as different customers to see personalisation in action.

**My Offers page** — ranked offer cards with score bars, channel pills (colour-coded), clip/unclip buttons, and an optional score breakdown expander showing each of the 5 weighted rules.

**My Profile page** — loyalty metrics: tier badge, points balance, days since last transaction, channel preference, eCommerce orders.

**Segment Explorer** — 4 segment cards (Fuel Redeemers, 4U+, High Points, Active This Week) with a drilldown table and a "view their offers" jump button.

**Compare Customers** — side-by-side view of two customers' profiles and top 3 offers, with a score distribution bar chart. This became one of the most compelling demo screens because it made personalisation immediately visible.

**My Clipped Offers tab** — active clips that would apply at checkout. Grocery Reward offers allowed multiple clips (a deliberate business rule).

**Demo Script** — a 6-step guided walkthrough with narration panels, Previous/Next navigation, and content that changed with each step. This meant a presenter could run the entire demo from a single screen.

**Albertsons branding** — SVG logo embedded in the header and login screen, Albertsons blue (#00529B) and red (#E31837) throughout.

### A key technical constraint

Streamlit 1.55.0 doesn't support `st.markdown(unsafe_allow_html=True)` the way older versions did. We discovered this when the offer cards — which relied on custom HTML — threw a rendering error. The fix was switching to `st.html()` throughout. This became a standing rule for the rest of the project.

### The eCommerce nudge

One of the more interesting scoring decisions came up while building the offers page: what score should a Fuel redeemer get on an eCommerce offer? A zero score would mean they'd never see digital offers. A full score would be dishonest about their preferences.

We settled on a partial score of 0.6 — enough to surface online offers in their recommendations without overriding their natural Fuel affinity. This was documented as an intentional business rule, not a bug.

---

## Session 2 — The Database Design

**Date: 2026-03-05**

With the UI working, the next task was designing the database. A teammate had provided the real Albertsons C360 BigQuery schema — ~90 views covering customer, offer, transaction, and loyalty data. We scoped it down to the 18 tables relevant to offer scoring.

### Schema design decisions

This session was less about writing code and more about making the right design calls. Several issues came up:

**The UPC primary key problem.** The same UPC can appear multiple times on a receipt (e.g. two different pack sizes of the same product). Using `(txn_id, upc_id)` as the primary key on `c360_txn_upc` would silently drop duplicate rows. We changed it to `(txn_id, receipt_line_nbr)`.

**The offer-UPC join path.** The source schema had both `client_offer_id` and `oms_offer_id` as potential join keys between offers and their UPCs. We resolved this by making `client_offer_id` the explicit foreign key on `c360_offer_upcs` — one consistent join path throughout the system.

**Offer targeting levels.** Offers in the real system can target at three levels of specificity: a specific product SKU (ITEM), any product in a category (CATEGORY), or the whole basket (BASKET). This wasn't surfaced cleanly in the source schema, so we added `target_level_cd` to `c360_offer` to make it explicit. It became important for scoring — an item-level match should score higher than a category-level match.

**Grocery Reward offers.** This required the most thought. Grocery Reward offers are fundamentally different from standard offers — the customer *spends* accumulated points to get a dollar discount, rather than earning rewards from a purchase. Treating them with the same scoring logic would be wrong. We designed a completely separate scoring path (Path 2) with:
- A hard eligibility gate (balance must reach the minimum threshold)
- Tiered scoring based on which discount tier the customer can reach
- A points expiry multiplier (customers with expiring points are more motivated to spend them)

**J4U attributes snapshot.** The `c360_j4u_hh_attributes` table stores multiple historical snapshots. Without a filter, querying it would return duplicate rows per household. We added `is_current_ind` and documented that all queries must filter `WHERE is_current_ind = TRUE`.

**FreshPass offers.** Added `is_freshpass_offer_ind` to `c360_offer` and built a hard filter so FreshPass-exclusive offers only surface for active subscribers.

### The inventory question

Partway through the session, the question came up: do offers have items associated with them? The answer was yes — item-level offers link to specific UPCs via `c360_offer_upcs`. This matters for scoring: if a customer has bought a specific UPC before, an offer targeting that exact UPC should score higher than one targeting the whole category.

This confirmed the need for `c360_offer_upcs` and the `target_level_cd` field.

---

## Session 3 — Real Data and the Full Stack

**Date: 2026-03-07**

The final session completed the stack. Three things happened: we got real data, built the data generator, and migrated every component from CSVs to PostgreSQL.

### Getting real data from Safeway

The team explored whether we could pull real product data from Safeway.com rather than inventing everything. After some investigation, the Safeway search API (`/abs/pub/xapi/wcax/pathway/search`) returned structured product data including real UPCs, prices, categories, brands, and linked offer data.

The user pasted a full API response — ~4,000 lines of JSON — containing 30 Dairy products and 6 associated offers. This became the anchor for the data generator:

**30 real Dairy UPCs:** Lucerne, Fairlife, Chobani, Challenge, Tillamook, FAGE, Greek Gods, O Organics, Vital Farms, Tropicana, Coffee Mate, Daisy, Frigo, SToK.

**6 real offer records** with real offer IDs:
- Club Card price on Lucerne Milk + Challenge Butter (`ITEM_DISCOUNT`, channel `CC`)
- Earn 4X Points on participating Dairy items (`REWARDS_ACCUMULATION`, channel `DO`, clippable)
- Buy Oreo → save $0.50 on Milk (`BUYX_GETY`, channel `DO`, clippable)
- Earn 2X Points in-store (`REWARDS_ACCUMULATION`, channel `IS`, no clip needed)
- Schedule & Save 5% on Creamer (`ITEM_DISCOUNT`, subscription)
- FreshPass exclusive free delivery (`FREE_DELIVERY`)

The Safeway API uses its own channel codes (`CC`, `DO`, `IS`, `EC`). We mapped these to our schema's delivery channels (`J4U`, `Weekly Ad`, `Auto Clip`) during import.

### Building the data generator

With real products and offers as an anchor, we built a full correlated data generator for all 18 tables. The key design principle: data had to be *consistent*, not just random. A customer flagged as an eCommerce user should have delivery transactions. A fuel redeemer should have fuel station spend. A 4U+ member should be eligible for exclusive offers.

This correlation is what makes the scoring engine produce believable, differentiated results per customer.

### Migrating the scoring engine

The CSV-based scoring engine had two problems: it used invented field names (`customer_id`, `tier`, `points_balance`) rather than the real C360 names, and it had no concept of Grocery Reward offers.

The rewrite:
- Connected to PostgreSQL via SQLAlchemy
- Used real C360 field names throughout (`household_id`, `clv_tier_level_id`, `current_point_balance`, `fav_channel`)
- Computed `days_since_last_txn` live from `c360_txn` rather than storing it
- Implemented Path 1 (Standard) and Path 2 (Grocery Reward) as separate scoring functions
- Applied FreshPass and 4U+ business rule filters before scoring
- Wrote results to `c360_scored_offers` with full component breakdown per offer

### Migrating the API

The FastAPI rewrite was mostly field name updates, plus a few new endpoints: `GET /segments` for a summary table across all tiers, and `GET /segments/high-churn` to surface reactivation candidates. The `POST /clip` endpoint now writes directly to `c360_clips`.

### Migrating the Streamlit UI

The UI migration was the largest single change — every data reference in ~1,100 lines needed updating. The old CSV schema used simple invented names; the new PostgreSQL schema used real C360 field names. Beyond field names, two things changed structurally:

**Score components** — in the CSV version, component scores were stored as a JSON string in a single column and parsed with `ast.literal_eval`. In PostgreSQL they're flat columns (`transaction_affinity`, `redemption_match`, etc.), which is cleaner but required removing all the dict-parsing logic.

**Boost flags** — similarly, `boosts_applied` was a JSON dict (`{"recency_boost": true, ...}`). In PostgreSQL it's two separate boolean columns: `recency_boost_applied` and `tier_multiplier_applied`.

The `format_discount()` function was also rewritten — instead of a pre-formatted string from the CSV, it now derives the display text from `discount_value` and `discount_type_cd` (e.g. `AMT_OFF` → `$X.XX off`, `POINTS_MULTIPLIER` → `X× Points`).

The Segment Explorer gained a fifth card — **High Churn Risk** — surfacing customers flagged by `churn_segment_cd` for potential reactivation campaigns.

---

## How Claude Code Was Used

Throughout the project, the collaboration followed a consistent pattern:

**Kartika provided direction and domain knowledge.** The Albertsons loyalty program, C360 schema, and business rules (Grocery Reward scoring, FreshPass targeting, the eCommerce nudge) all came from the team's understanding of how the real system works. Design decisions — like choosing household-level scoring over individual-level, or deciding which tables to include in scope — were Kartika's calls.

**Claude Code provided implementation and caught design issues.** The scoring logic, SQL queries, Streamlit layout, FastAPI endpoints, and data generator were written by Claude. Design issues like the UPC primary key problem, the offer join path ambiguity, and the Grocery Reward scoring path were flagged during implementation and resolved through discussion.

**Iteration was fast and targeted.** Rather than writing a spec and then code, the pattern was: try it, run it, see what breaks, fix it. The CSS brace-escaping bug in the Streamlit f-string, the `points_cost` field that was invented and then corrected, the Streamlit `unsafe_allow_html` deprecation — all were found by running the code and fixed immediately.

**Documentation was built alongside the code.** The five docs files in `docs/` (data model, scoring engine, technical integration, customer touchpoints, ML roadmap) were written during the sessions, not after. The CLAUDE.md and CHECKPOINT.md files mean that any new session — or any new team member — can pick up exactly where the project left off without re-reading the conversation history.

---

## What the Demo Shows

The final demo tells two stories through the UI:

**Story 1 — The Fuel Redeemer.** An offline-only loyalist who has never shopped online. SmartRewards surfaces J4U digital offers in their ranked list despite their offline preference — the eCommerce nudge at work. The idea: show them relevant online offers, let them discover eCommerce naturally.

**Story 2 — The 4U+ Subscriber.** A premium tier member who sees exclusive offers unavailable to Standard customers. Their scores on J4U-exclusive offers are boosted 50% by the tier multiplier. The Compare Customers screen shows both stories side by side — same offer catalog, completely different ranked results.

The "How Offers Are Scored" page and Demo Script mean a presenter can walk judges through both the business logic and the technology in a structured way, without needing to explain the code.

---

## What Comes Next

The rule-based engine was designed to be a placeholder. The ML roadmap (see `docs/ml_roadmap.md`) describes a 4-layer model:

- **XGBoost** trained on `c360_redemptions` (positive labels) vs clipped-not-redeemed (negative labels)
- **Embeddings** from co-redemption patterns for collaborative filtering
- **SHAP values** to replace the manual score breakdown with ML-generated explanations
- **Blended ranking** combining propensity scores and embedding similarity

The local PostgreSQL schema mirrors C360 field names exactly, so the transition to the real BigQuery data requires only changing the SQLAlchemy connection string.

---

*Built at the Albertsons AI Hackathon, March 2026.*
