# Scoring Engine — SmartOfferEngine

> How every customer-offer pair is scored and ranked. Three models, two scoring paths.

---

## Overview

Three models coexist in `c360_scored_offers`, each identified by `model_type`:

| `model_type` | Engine | Offers | Rows/HH |
|---|---|---|---|
| `rule_based` | `scoring.py` | Standard (10) + GR (5) | 15 |
| `propensity` | `scoring_ml.py` | Standard only | 10 |
| `propensity_gr` | `scoring_ml.py` | GR only | 5 |

Standard and GR offers are scored into **separate pools** to prevent GR from crowding out standard offers for high-balance customers. See `propensity_model.md` for the ML models.

---

## Rule-Based Engine — `files/engine/scoring.py`

### Path 1 — Standard Offer Scoring

Applies to all offers where `program_type != 'Grocery Reward'`.

#### Step 1 — Weighted Component Scores

Each component produces a score between 0.0 and 1.0, stored in `c360_scored_offers` for UI breakdown display.

| Component | Weight | Signal | Description |
|---|---|---|---|
| Transaction Affinity | 30% | `c360_cat_affinity.affinity_score` | Customer's historical spend in the offer's category |
| Redemption Match | 25% | `fav_channel` vs `delivery_channel_cd` | Channel alignment — offer channel matches preferred channel |
| Points Eligibility | 20% | `current_point_balance` | Whether the customer has enough points to benefit |
| Cart & Browse Affinity | 15% | `doordash_txn_ind_6m`, `instacart_txn_ind_6m`, `uber_txn_ind_6m` | Online engagement signals for eCommerce offers |
| Demographic Match | 10% | `customer_age`, `num_of_children`, `diet_preference` | Life stage fit for the offer type |

#### Step 2 — Weighted Sum

```
weighted_sum = (
    0.30 × transaction_affinity +
    0.25 × redemption_match     +
    0.20 × points_eligibility   +
    0.15 × cart_affinity        +
    0.10 × demographic_match
) × 100
```

#### Step 3 — Multipliers

Applied sequentially after the weighted sum. Flags stored as booleans in `c360_scored_offers`.

| Multiplier | Factor | Condition |
|---|---|---|
| Recency Boost | ×1.2 | `days_since_last_txn ≤ 7` |
| Tier Multiplier | ×1.5 | `clv_tier_level_id = '4U+'` AND `is_appliable_to_j4u_ind = TRUE` |

#### Step 4 — Business Rules

| Rule | Effect |
|---|---|
| Score cap | `min(score, 100)` |
| eCommerce nudge | Fuel redeemers get `redemption_match = 0.6` on eCommerce offers (channel migration strategy) |
| FreshPass filter | `is_freshpass_offer_ind = TRUE` offers excluded for non-subscribers |
| 4U+ filter | `is_appliable_to_j4u_ind = TRUE` offers excluded for Standard tier customers |
| Auto Clip filter | GR offers excluded for `auto_clip_ind = TRUE` customers |

#### Step 5 — Pool Ranking

After scoring, standard and GR offers are split by `discount_type_cd` and ranked independently:
- **Standard pool:** top `TOP_N_STANDARD = 10` per household
- **GR pool:** top `TOP_N_GR = 5` per household

---

### Path 2 — Grocery Reward Scoring

Applies to offers where `program_type = 'Grocery Reward'`. Customers **spend accumulated points** to get a dollar discount — scoring prioritises points signals over channel alignment.

#### Step 1 — Hard Eligibility Gate

```
if current_point_balance < tier_1_points_threshold:
    offer excluded — not surfaced
```

#### Step 2 — Weighted Component Scores

| Component | Weight | Signal | Description |
|---|---|---|---|
| Points Eligibility | 40% | `current_point_balance` vs threshold | `min(balance / threshold / 2, 1.0)` — graduated by surplus above threshold |
| Category Affinity | 25% | `c360_cat_affinity.affinity_score` | Customer's spend affinity for the offer's category |
| Value Per Point | 15% | `discount_value / tier_1_points_threshold` | Dollar value per point at the threshold |
| GR History | 15% (floor 0.3) | `c360_rewards_redeemed` | Frequency of past GR redemptions; floor prevents penalising new-to-GR customers |
| Recency | 5% | `days_since_last_txn` | Active customers act on offers sooner |

#### Step 3 — Points Expiry Multiplier

```
if points_expiring_next_month >= tier_1_points_threshold:
    score × 1.3   ("use them before you lose them" nudge)
```

#### Step 4 — Score cap at 100

---

## Offer Targeting Levels

| Level | `target_level_cd` | Affinity computation |
|---|---|---|
| Item-specific | `ITEM` | Match via `c360_offer_upcs` for specific UPCs |
| Category-wide | `CATEGORY` | `c360_cat_affinity` for the offer's department |
| Basket | `BASKET` | Flat affinity boost — offer applies to any purchase |

---

## Output Schema

Results written to `c360_scored_offers`:

```
household_id, retail_customer_uuid, client_offer_id, offer_dsc,
delivery_channel_cd, discount_value, discount_type_cd,
score, rank, model_type, scored_at,
transaction_affinity, redemption_match, points_eligibility,
cart_affinity, demographic_match,
recency_boost_applied, tier_multiplier_applied
```

Component scores (`transaction_affinity` … `demographic_match`) and boost flags are `NULL` / `FALSE` for propensity model rows — they are only populated by the rule-based engine and used by the Feature Weight Studio and score breakdown expander in the UI.

---

## Feature Weight Studio

The UI **Feature Weight Studio** page lets business users re-weight scoring components interactively:

- **Rule-Based tab** — sliders for the 5 components (0–200% of default weight). Custom score = weighted sum of stored components + recency/tier boosts. Session-only.
- **Propensity tab** — sliders for all 16 standard model features. Features fetched from DB at runtime, min-max normalised per customer's offer set, weighted sum rescaled 0–100. Session-only.

Neither tab writes to the DB or affects live scoring.
