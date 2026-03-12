# Propensity Model Scoring Explained

## Overview

The propensity models use **XGBoost machine learning** to predict the probability that a customer will redeem (clip & later convert) an offer.

**Score Range**: 0–100  
**Higher score** = Higher likelihood of redemption

---

## How Scores Are Calculated

### 1. **Data Input: 19 Features**

For each customer-offer pair, the model receives:

#### Customer Features (11)
- `current_point_balance` — Points available
- `points_expiring_next_month` — Urgent points (expiry flag)
- `is_4uplus` — Premium tier status (0 or 1)
- `gas_rewards` — Fuel rewards participation in last 6 months
- `doordash`, `instacart`, `uber` — Delivery app adoption signals
- `household_size` — Number of people in household
- `num_children` — Presence of kids (affects offer relevance)
- `churn_risk` — Predicted churn score (0–1)
- `days_since_last_txn` — Days since last purchase (recency)

#### Offer Features (5)
- `discount_value` — Dollar amount off (or item value for free offers)
- `is_j4u_exclusive` — J4U only? (1 if yes)
- `is_freshpass_offer` — FreshPass subscription required? (1 if yes)
- `redemption_rate` — Historical redemption % for this offer
- `days_until_expiry` — Offer expiration countdown

#### Interaction Features (3 - NEW for split models)
- `channel_match` — Does delivery channel match customer preference? (1 if yes)
- `category_affinity` — Customer's historical spend in this category (0–1)
- `points_gap` — How far above the GR tier threshold? (important for GR model)

### 2. **XGBoost Magic**

**What XGBoost does:**
1. Receives all 19 features
2. Builds decision trees to learn non-linear patterns
3. Outputs a **probability** (0 to 1):
   - 0 = Very unlikely to redeem
   - 0.5 = 50/50 chance
   - 1 = Very likely to redeem
4. Scales to 0–100: **`Score = Probability × 100`**

**Example:**
```
Features → XGBoost → Probability 0.76 → Score 76
(Model learned: "Customers with high category affinity + 
 matching delivery channel + recent transaction = 76% likely to redeem")
```

### 3. **Business Rules Applied AFTER Scoring**

Even if a customer gets a high score, offers are **filtered out** if they don't pass business rules:

| Rule | Condition | Action |
|------|-----------|--------|
| **FreshPass Gate** | `is_freshpass_offer = 1` AND customer not FreshPass subscriber | Remove from results |
| **4U+ Exclusive** | `is_j4u_exclusive = 1` AND customer not 4U+ tier | Remove from results |

---

## Key Differences: Split Propensity Models

### **Propensity (Standard)**
- **Trained on**: 1,167 standard offer pairs (52 offers × households)
- **Top Feature #1**: `channel_match` (16.3% importance)
  - Why? Standard offers (produce, meat, dry goods) succeed when delivery channel matches customer preference
- **Top Features #2–3**: `points_expiring_next_month` (6.7%), `category_affinity` (6.2%)

**What it learned:**
> "Customers redeem standard offers when they match their preferred shopping channel AND have relevant category history."

---

### **Propensity (GR)**
- **Trained on**: 1,208 Grocery Reward offer pairs (25 GR offers × households)
- **Top Feature #1**: `discount_value` (10.8% importance)
  - Why? GR offers have fixed basket/$department/item value, so basket size matters
- **Top Features #2–3**: `points_gap` (6.6%), `channel_match` (6.6%)

**What it learned:**
> "Customers redeem GR offers based on immediate value + how far above the tier threshold they are + channel match."

**Key insight:** `points_gap` (#2, 6.6%) is much more important for GR than standard (would be buried in standard model's top-10).

---

## Training Data Comparison

### Standard Model Training
```
Total pairs:     1,167
Redeemed:        229 (19.6%)
Not redeemed:    938 (80.4%)
Class imbalance: 4.1:1 (heavily negative)
```

Model learned: "Redemption is rare for standard offers. What makes it happen?"
- Channel match is THE differentiator (16.3%)
- Category history matters (6.2%)
- Recency matters

### GR Model Training
```
Total pairs:     1,208
Redeemed:        189 (15.6%)
Not redeemed:    1,019 (84.4%)
Class imbalance: 5.4:1 (more imbalanced than standard)
```

Model learned: "Redemption is rarer for GR. Why do some customers redeem?"
- Basket value + points gap matter most (10.8% + 6.6%)
- Channel still matters (6.6%) but less than value proposition
- Different customer psychology (financial transaction vs. impulse buy)

---

## How Scores Compare Across Models

### Example: Customer HH00123 viewing "$10 Off Bakery — 400 pts" (GR Offer)

| Model | Score | Reasoning |
|-------|-------|-----------|
| **Rule-Based** | 62 | "5 rules applied: category fit (0.8 weight), points balance (0.5), demographic (0.4) → combined 62" |
| **Propensity (Standard)** | N/A | "Not applicable — only scores standard offers" |
| **Propensity (GR)** | 71 | "XGBoost: This customer has 500 pts (100-pt gap from threshold) + matches J4U channel + Bakery affinity 0.7 → 71% likely to redeem" |

The GR propensity model rates it **higher** (71) than rule-based (62) because it learned that **points_gap** (100 pts surplus) is strong signal.

---

## From Score to Ranking

1. **Score each household-offer pair** with selected model
   - Standard model: 52 offers × 120 households = 6,240 possible scores
   - GR model: 25 offers × 120 households = 3,000 possible scores

2. **Rank within each household** (ascending, ties broken by order seen)
   - Highest score = Rank #1

3. **Keep top 15 per household** (TOP_N_OFFERS)
   - Ensures diverse offer portfolio

4. **Result**: 1,800 scored offers per model (15 × 120 households)

---

## Why Split Models Score Better (22.8% AUC Improvement)

### Before (Unified Model)
- Single model learned average pattern: "Standard offers are similar to GR offers"
- Feature importance: `channel_match` (11.1%), `discount_value` (7.8%), etc.
- Result: Awkward compromise, underperforms on both types
- AUC: **0.531** (barely better than random guessing)

### After (Split Models)
- **Standard model** focuses: "Channel match is THE signal" → emphasizes `channel_match` (16.3% vs 11.1%)
- **GR model** focuses: "Value + gap matters most" → emphasizes `discount_value` (10.8%) + `points_gap` (6.6%)
- Result: Specialized, accurate predictions for each domain
- Standard AUC: **0.653** (+22.8%)
- GR AUC: **0.582** (+9.6%)

---

## In the UI

### Streamlit Compare Models Page (3 Columns)

| Rule-Based | Propensity (Standard) | Propensity (GR) |
|---|---|---|
| **Score Calculation**: 5 weighted rules | **Score Calculation**: XGBoost P(redemption) × 100 | **Score Calculation**: XGBoost P(redemption) × 100 |
| Rules are pre-defined by team | Learned from 1,167 training pairs | Learned from 1,208 training pairs |
| **Top Signals**: Categories, channels, demographics (fixed) | **Top Signals**: channel_match (16.3%), points_expiring (6.7%), affinity (6.2%) | **Top Signals**: discount_value (10.8%), points_gap (6.6%), channel_match (6.6%) |
| Example rank #1: $10 Off Bakery = 68 | Example rank #1: $10 Off Bakery = 73 | Example rank #1: $10 Off Bakery = 76 |

---

## Debugging Scores

### Why is Score X for Offer Y?

**Check feature importance first:**
- Go to **Compare Models** → See top 3 features for each model
- Hover over metadata boxes for full feature rankings

**Then ask:**
1. **For Standard offers**: Is `channel_match = 1`? (customer's fav channel = offer channel?)
2. **For GR offers**: Is `points_gap > 0`? (customer above tier point threshold?)
3. **For all**: Is `category_affinity` high? (customer shops this category?)

**Real example:**
```
HH00005 + "$7 Off Produce Dept — 500 pts" (GR offer)

Features:
  - points_gap: 250 (customer has 750 pts, tier is 500) ✅ Strong signal
  - category_affinity: 0.85 (high produce shopper) ✅ Positive
  - channel_match: 1 (customer prefers J4U, offer is J4U) ✅ Positive
  - discount_value: 7 (moderate value) ⚠️ Neutral
  
Result: propensity_gr = 75 (learned: gap + affinity + channel = high redemption)
```

---

## See It in Action

1. **My Offers page**:
   - Switch between `📋 Rule-Based`, `🤖 Propensity (Standard)`, `🎯 Propensity (GR)`
   - Notice different rankings: same customer, same offers, different models

2. **Compare Models page**:
   - Side-by-side rankings
   - Rank deltas show how much models disagree (▲ green = propensity ranked higher)
   - Feature importance tables reveal what each model learned

3. **My Rewards page** (Grocery Rewards):
   - Uses `propensity_gr` scores behind the scenes
   - Tier tabs filtered by customer's points balance
   - "Use XXX pts" button clips the offer

