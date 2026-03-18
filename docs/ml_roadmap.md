# ML Roadmap — SmartRewards Phase 4

> Upgrading from rule-based scoring to a 4-layer ML model.

---

## Current State (Rule-Based)

The current engine uses 5 hand-tuned weighted rules. Weights are fixed and do not learn from data. While effective for a demo, real-world performance requires learning from historical redemption patterns.

**Limitations of the current approach:**
- Weights are manually set — not optimised for actual redemption rates
- No cross-customer learning (collaborative filtering)
- Score components are independent — no interaction effects captured
- Cannot adapt to new offer types automatically

---

## Target State — 4-Layer Model

### Layer 1 — Feature Engineering

Build a rich feature vector for every customer-offer pair.

**Customer features** (from `c360_customer_profile`, `c360_cat_affinity`, `c360_txn`):
- Points balance, days since last transaction, tier
- Engagement mode (eCommerce / In-Store / Both)
- Category spend proportions (top 5 categories by affinity score)
- eCommerce order count, DoorDash/Instacart/Uber usage flags
- Household size, number of children, diet preference
- Churn risk score

**Offer features** (from `c360_offer`, `c360_offer_summary`):
- `target_level_cd` (ITEM / CATEGORY / BASKET)
- Delivery channel, discount type, discount value
- `is_appliable_to_j4u_ind`, `is_freshpass_offer_ind`
- Historical redemption rate (`red_pct` from `c360_offer_summary`)
- Offer age (days since `start_dt`)

**Interaction features** (customer × offer):
- Channel match: customer `fav_channel` == offer `delivery_channel_cd`
- Points gap: `current_point_balance` − `tier_1_points_threshold` (Grocery Rewards)
- Category affinity score for offer's category
- UPC-level purchase history match (for ITEM-level offers)
- Recency × discount value interaction

---

### Layer 2 — XGBoost Propensity Model

Predicts P(redemption | customer, offer) for each pair.

**Training labels:**
- Positive (1): rows in `c360_redemptions` — customer redeemed the offer
- Negative (0): offers that were clipped but not redeemed (from `c360_clips` LEFT JOIN `c360_redemptions`)

**Why XGBoost:**
- Handles mixed feature types (boolean flags, numeric, categorical)
- Captures non-linear interactions (e.g. high points + expiring = strong signal)
- Fast to train and score
- SHAP values provide per-prediction explainability

**Output:** P(redemption) score per customer-offer pair

**Explainability:** SHAP values replace the manual score breakdown in the UI — customers and analysts see *why* each offer was ranked where it was.

---

### Layer 3 — Embedding Similarity (Collaborative Filtering)

Captures "customers like you also redeemed..." patterns.

**Approach:** Two-tower model or matrix factorisation
- Customer embedding: derived from co-redemption patterns in `c360_redemptions`
- Offer embedding: derived from which customer segments tend to redeem it
- Cosine similarity between customer and offer embeddings → affinity score

**Why this complements Layer 2:**
- XGBoost learns from explicit features; embeddings learn latent patterns
- Surfaces offers the customer hasn't seen yet but similar customers love
- Especially powerful for new customers with sparse transaction history

**Training data:** `c360_redemptions` — household × offer co-occurrence matrix

---

### Layer 4 — Final Ranking & Blending

Combines propensity score + embedding similarity into a final ranked list.

```
final_score = α × propensity_score + (1 − α) × embedding_similarity
```

Where α is tuned per customer segment (e.g. high for active customers, lower for new customers).

**Hard business rules applied on top** (not learned — intentional):
- Tier multiplier ×1.5 for 4U+ on exclusive offers
- Recency boost ×1.2 for customers active in last 7 days
- eCommerce nudge for Fuel redeemers
- Grocery Reward eligibility gate (points balance < threshold → exclude)
- FreshPass filter
- Score cap at 100

---

## Data Requirements

| Data | Table | Use |
|---|---|---|
| Redemption events | `c360_redemptions` | Positive training labels |
| Clip events | `c360_clips` | Negative examples (clipped not redeemed) |
| Transaction history | `c360_txn`, `c360_txn_upc` | Feature engineering |
| Category affinity | `c360_cat_affinity` | Direct feature |
| Offer performance | `c360_offer_summary` | Offer-level features |
| Rewards redeemed | `c360_rewards_redeemed` | Grocery Reward history feature |

---

## Metrics

| Metric | Description |
|---|---|
| AUC-ROC | Overall propensity model quality |
| Precision@K | Are the top K offers actually redeemed? |
| Redemption lift | Scored offers vs random baseline |
| Click-through rate | Clip rate on surfaced offers |
| Points utilisation | % of expiring points redeemed via SmartRewards |

---

## Phased Delivery

| Phase | Deliverable | Status | Dependency |
|---|---|---|---|
| 4a | Feature engineering pipeline | ✅ Done | PostgreSQL seeded with real data |
| 4b | XGBoost model — Standard + GR split | ✅ Done | `c360_redemptions` + `c360_clips` data |
| 4c | Embedding model (Layer 3) | 🔵 Next | Sufficient redemption history (>10k events) |
| 4d | Blended ranking (Layer 4) | 🔵 Backlog | Layers 2 + 3 complete |
| 4e | SHAP values in UI | 🔵 Backlog | Layer 2 complete + team familiar with SHAP theory |

> **Note on 4e:** SHAP values are deprioritised until the team has reviewed the theory. SHAP (SHapley Additive exPlanations) attributes each feature's contribution to an individual prediction — requires understanding of cooperative game theory concepts before building the UI. Revisit after 4c/4d.
