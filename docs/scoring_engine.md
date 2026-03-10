# Scoring Engine — SmartRewards

> How every customer-offer pair is scored and ranked.

---

## Overview

The SmartRewards scoring engine evaluates every active offer against every customer and produces a ranked list of the most relevant offers per household. Two separate scoring paths exist — one for standard offers and one for Grocery Reward offers.

---

## Path 1 — Standard Offer Scoring

Applies to all offers where `program_type != 'Grocery Reward'`.

### Step 1 — Weighted Component Scores

Each component produces a score between 0.0 and 1.0.

| Component | Weight | Signal | Description |
|---|---|---|---|
| Transaction Affinity | 30% | `c360_cat_affinity.affinity_score` | How much the customer spends in the offer's category |
| Redemption Match | 25% | `fav_channel` vs `delivery_channel_cd` | Alignment between offer channel and customer's preferred channel |
| Points Eligibility | 20% | `current_point_balance` | Whether the customer has enough points to benefit |
| Cart & Browse Affinity | 15% | `ecom_ind`, `doordash_txn_ind_6m` etc. | Online engagement signals for eCommerce offers |
| Demographic Match | 10% | `customer_age`, `num_of_children`, `diet_preference` | Life stage fit for the offer type |

### Step 2 — Weighted Sum

```
weighted_sum = (
    0.30 × transaction_affinity +
    0.25 × redemption_match     +
    0.20 × points_eligibility   +
    0.15 × cart_affinity        +
    0.10 × demographic_match
) × 100
```

### Step 3 — Multipliers

Applied sequentially after the weighted sum.

| Multiplier | Factor | Condition |
|---|---|---|
| Recency Boost | ×1.2 | `days_since_last_txn ≤ 7` |
| Tier Multiplier | ×1.5 | `clv_tier_level_id = '4U+'` AND `is_appliable_to_j4u_ind = TRUE` |

### Step 4 — Business Rules

| Rule | Effect |
|---|---|
| Score cap | `min(score, 100)` |
| eCommerce nudge | Fuel redeemers get `redemption_match = 0.6` on eCommerce offers (migration strategy) |
| FreshPass filter | `is_freshpass_offer_ind = TRUE` offers only shown to active FreshPass subscribers |
| Offer targeting level | ITEM-level UPC match → higher affinity boost than CATEGORY-level |

---

## Path 2 — Grocery Reward Scoring

Applies to offers where `program_type = 'Grocery Reward'`.

Grocery Reward offers are fundamentally different — the customer **spends accumulated points** to get a dollar discount. The scoring reflects this: points balance is the primary signal, not channel alignment.

### Step 1 — Hard Eligibility Gate

```
if current_point_balance < tier_1_points_threshold (min: 50 pts):
    score = 0  → offer not surfaced
```

### Step 2 — Best Reachable Tier

```
tier_reached = highest tier where current_point_balance >= tier_N_points_threshold
```

The tier reached determines both the score and which discount to display in the UI.

### Step 3 — Weighted Component Scores

| Component | Weight | Signal | Description |
|---|---|---|---|
| Points Eligibility | 40% | `current_point_balance` vs thresholds | Graduated: tier 1 = 0.4, tier 2 = 0.7, tier 3 = 1.0 |
| Category Affinity | 25% | `c360_cat_affinity.affinity_score` | Customer's spend proportion in this offer's category |
| Value Per Point | 15% | `tier_N_discount / tier_N_points_threshold` | Dollar value earned per point spent at best reachable tier |
| Grocery Reward History | 15% | `c360_rewards_redeemed` where `src = 'Grocery'` | Frequency of past Grocery Reward redemptions |
| Recency | 5% | `days_since_last_txn` | Active customers act on offers faster |

### Step 4 — Points Expiry Multiplier

```
if points_expiring_next_month >= tier_1_points_threshold:
    score × 1.3   ("use them before you lose them" nudge)
```

### Step 5 — Portfolio Conflict Penalty

```
if another Grocery Reward offer has already consumed most of the customer's balance:
    score × 0.7   (avoid surfacing unaffordable offers)
```

### Step 6 — Score cap at 100

---

## Offer Targeting Levels

| Level | `target_level_cd` | How affinity is computed |
|---|---|---|
| Item-specific | `'ITEM'` | Match customer's purchase history for specific UPCs via `c360_offer_upcs` |
| Category-wide | `'CATEGORY'` | Match `c360_cat_affinity` for the offer's department/category |
| Basket | `'BASKET'` | Apply flat affinity boost — offer applies to any purchase |

---

## Output

Results written to `c360_scored_offers`:

```
household_id, retail_customer_uuid, client_offer_id,
score, rank,
transaction_affinity, redemption_match, points_eligibility,
cart_affinity, demographic_match,
recency_boost_applied, tier_multiplier_applied,
scored_at
```

The UI reads this table to render ranked offer cards with score breakdowns.

---

## Planned: Phase 4 ML Upgrade

The rule-based engine will be replaced by a 4-layer ML model. See `ml_roadmap.md` for details.
