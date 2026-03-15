# SmartRewards — Propensity Models

> Two separate XGBoost models: one for standard offers, one for Grocery Reward offers.

---

## Overview

Two XGBoost classifiers predict **P(redemption | customer, offer)** — scaled to 0–100 scores compatible with the rule-based engine. Standard and GR offers are trained and scored separately because they are driven by fundamentally different customer signals.

| Model | `model_type` | Trained on | Features | AUC |
|---|---|---|---|---|
| Standard | `propensity` | Standard offer clips + redemptions | 16 | 0.626 |
| GR | `propensity_gr` | GR offer clips + redemptions | 12 | 0.572 |

---

## Training Data

### Label Construction

Labels come from two sources per model, filtered by offer type:

```sql
-- Clip-based labels (positive = clipped + redeemed, negative = clipped + not redeemed)
SELECT cl.household_id, cl.client_offer_id,
    MAX(CASE WHEN r.txn_id IS NOT NULL THEN 1 ELSE 0 END) AS label
FROM c360_clips cl
JOIN c360_offer o ON o.client_offer_id = cl.client_offer_id
LEFT JOIN c360_redemptions r
    ON cl.household_id = r.household_id AND cl.client_offer_id = r.client_offer_id
WHERE o.program_type {= / != 'Grocery Reward'}
GROUP BY cl.household_id, cl.client_offer_id

UNION ALL

-- Implicit negatives — eligible pairs never clipped
SELECT so.household_id, so.client_offer_id, 0 AS label
FROM c360_scored_offers so
JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
WHERE so.model_type = 'rule_based'
  AND o.program_type {= / != 'Grocery Reward'}
  AND NOT EXISTS (SELECT 1 FROM c360_clips cl
                  WHERE cl.household_id = so.household_id
                    AND cl.client_offer_id = so.client_offer_id)
```

### Training Set Sizes

| Model | Positive | Negative | Total | `scale_pos_weight` |
|---|---|---|---|---|
| Standard | 229 | 938 | 1,167 | 4.10 |
| GR | 189 | 1,019 | 1,208 | 5.39 |

---

## Feature Engineering

### Standard Model — 16 Features

Points features are intentionally **excluded** — standard offers don't require points to redeem, so `current_point_balance`, `points_expiring_next_month`, and `points_gap` would be noise.

**Customer (9)** — from `c360_customer_profile` + `c360_txn`:

| Feature | Description |
|---|---|
| `is_4uplus` | Binary loyalty tier flag |
| `gas_rewards` | Fuel redeemer flag (6m) |
| `doordash` | DoorDash usage flag (6m) |
| `instacart` | Instacart usage flag (6m) |
| `uber` | Uber Eats usage flag (6m) |
| `household_size` | Number of people in household |
| `num_children` | Number of children |
| `churn_risk` | Churn probability 0–1 |
| `days_since_last_txn` | Recency (999 if no transactions) |

**Offer (5)** — from `c360_offer` + `c360_offer_summary`:

| Feature | Description |
|---|---|
| `discount_value` | Dollar / % value of the offer |
| `is_j4u_exclusive` | Exclusive to 4U+ tier |
| `is_freshpass_offer` | FreshPass subscribers only |
| `redemption_rate` | Historical redemption % from `c360_offer_summary` |
| `days_until_expiry` | Days until offer expires |

**Interaction (2)** — computed per (customer, offer) pair:

| Feature | Computation |
|---|---|
| `channel_match` | `fav_channel == delivery_channel_cd` (0/1) |
| `category_affinity` | Join to `c360_cat_affinity` on `(household_id, category_nm)` |

**Top features (current run):** `channel_match`, `instacart`, `redemption_rate`, `category_affinity`, `is_4uplus`

---

### GR Model — 12 Features

Points signals are the primary driver for GR redemption. Channel/eCommerce features dropped.

**Customer — points-focused (7):**

| Feature | Description |
|---|---|
| `current_point_balance` | Raw points balance — primary gate signal |
| `points_expiring_next_month` | Urgency: spend before losing points |
| `is_4uplus` | Loyalty tier |
| `household_size` | Household size |
| `num_children` | Children in household |
| `churn_risk` | Churn probability 0–1 |
| `days_since_last_txn` | Recency |

**Offer (3):**

| Feature | Description |
|---|---|
| `discount_value` | Dollar value of the GR reward |
| `redemption_rate` | Historical redemption % |
| `days_until_expiry` | Days until offer expires |

**Interaction (2):**

| Feature | Computation |
|---|---|
| `category_affinity` | Customer's spend affinity for the offer's category |
| `points_gap` | `max(0, current_point_balance − tier_1_points_threshold)` |

**Top features (current run):** `discount_value`, `num_children`, `points_gap`, `points_expiring_next_month`, `category_affinity`

---

## Model

**Algorithm:** XGBoost (`XGBClassifier`) — same hyperparameters for both models.

| Parameter | Value | Reason |
|---|---|---|
| `n_estimators` | 200 | Enough trees for ~1,200 examples |
| `max_depth` | 4 | Prevents overfitting on small datasets |
| `learning_rate` | 0.05 | Low rate + more trees = better generalisation |
| `subsample` | 0.8 | Row sampling per tree — reduces variance |
| `colsample_bytree` | 0.8 | Feature sampling per tree — reduces variance |
| `random_state` | 42 | Reproducibility |

---

## Training Procedure

```
For each model (standard, GR):
1.  Load customers (head_household_ind = TRUE — 120 households)
2.  Load active offers filtered by program_type
3.  Load category affinity (c360_cat_affinity)
4.  Load FreshPass subscribers (c360_freshpass)
5.  Build clip-based labels from c360_clips LEFT JOIN c360_redemptions
6.  Add implicit negatives — eligible pairs never clipped
7.  Build feature matrix for all labeled pairs
8.  Cross-validate AUC with 5-fold CV
9.  Fit final model on full labeled set
10. Score all eligible (household, offer) pairs with business rules applied
11. Rank top 10 (standard) / top 5 (GR) per household
12. Scale P(redemption) × 100 → score
13. Write to c360_scored_offers with model_type = 'propensity' / 'propensity_gr'
14. Write metadata to model_metadata.json / model_gr_metadata.json
15. Save model to model_standard.pkl / model_gr.pkl
```

**To retrain both models:**
```bash
python3 files/engine/scoring_ml.py --retrain
```

**To score with existing saved models:**
```bash
python3 files/engine/scoring_ml.py
```

---

## Output

### Scoring Pools

Standard and GR offers are kept in **separate pools** — not ranked against each other:

| Pool | `model_type` | Rows per household | Total rows |
|---|---|---|---|
| Standard | `propensity` | 10 | 1,200 |
| GR | `propensity_gr` | 5 | 600 |

This prevents GR offers from crowding out standard offers for high-balance customers.

### Schema

Both models write to `c360_scored_offers`:

| Column | Value |
|---|---|
| `score` | `P(redemption) × 100`, rounded to 2 dp |
| `rank` | 1–10 (standard) or 1–5 (GR) per household within their pool |
| `model_type` | `'propensity'` or `'propensity_gr'` |
| `transaction_affinity` … `demographic_match` | `NULL` — not applicable |
| `recency_boost_applied`, `tier_multiplier_applied` | `FALSE` — multipliers not used |

Metadata written to `files/engine/model_metadata.json` (standard) and `files/engine/model_gr_metadata.json` (GR).

---

## Business Rules Applied Before Scoring

| Rule | Effect |
|---|---|
| FreshPass filter | `is_freshpass_offer_ind = TRUE` offers excluded for non-subscribers |
| 4U+ filter | `is_appliable_to_j4u_ind = TRUE` offers excluded for Standard tier customers |
| Auto Clip filter | GR offers excluded for customers with `auto_clip_ind = TRUE` |

---

## How It Differs From the Rule-Based Engine

| Dimension | Rule-Based | Propensity (XGBoost) |
|---|---|---|
| **Weight source** | Manually set by team | Learned from clip/redemption events |
| **Non-linear interactions** | No | Yes — e.g. high points + expiring = amplified GR signal |
| **Cross-customer learning** | No | Yes |
| **Explainability** | Per-offer component score breakdown | Feature importances (global); SHAP planned |
| **Adaptability** | Manual rule change required | Retrains as new redemption data accumulates |
| **GR handling** | Separate scoring path with points-weighted formula | Separate `propensity_gr` model with points-focused features |

---

## Known Limitations & Next Steps

| Limitation | Status | Next Step |
|---|---|---|
| AUC 0.626 / 0.572 on synthetic data | Expected — synthetic correlations weaker than real C360 data | Will improve on real redemption history |
| No SHAP values in UI | Planned | Phase 4c — per-prediction SHAP on Compare Models page |
| Single standard model for all segments | Open | Train per-segment models (Fuel Redeemers, 4U+, High Churn) |
| GR model `num_children` as top feature | Unexpected — likely synthetic data artifact | Monitor with real data |
