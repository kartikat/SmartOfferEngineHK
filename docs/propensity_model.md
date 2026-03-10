# SmartRewards — Propensity Model

> How the XGBoost model was built, what data it uses, and how it differs from the rule-based engine.

---

## What It Does

Predicts **P(redemption | customer, offer)** — the probability that a specific customer will redeem a specific offer — then scales that probability to a 0–100 score, identical in shape to the rule-based score so both can be displayed side by side in the UI.

---

## Training Data

### Label Construction

Training labels come from three sources, unioned together:

```sql
-- Source 1 & 2: clip-based labels
SELECT
    cl.household_id,
    cl.client_offer_id,
    MAX(CASE WHEN r.txn_id IS NOT NULL THEN 1 ELSE 0 END) AS label
FROM c360_clips cl
LEFT JOIN c360_redemptions r
    ON cl.household_id = r.household_id
    AND cl.client_offer_id = r.client_offer_id
GROUP BY cl.household_id, cl.client_offer_id

UNION ALL

-- Source 3: implicit negatives — eligible but never clipped
SELECT so.household_id, so.client_offer_id, 0 AS label
FROM c360_scored_offers so
WHERE so.model_type = 'rule_based'
  AND NOT EXISTS (
    SELECT 1 FROM c360_clips cl
    WHERE cl.household_id = so.household_id
      AND cl.client_offer_id = so.client_offer_id
  )
```

| Label | Source | Count |
|---|---|---|
| **1 (Positive)** | Clips with a matching row in `c360_redemptions` | 453 |
| **0 (Negative — explicit)** | Clips with no matching redemption (clipped, not redeemed) | 366 |
| **0 (Negative — implicit)** | Eligible (household, offer) pairs never clipped and never redeemed | 819 |
| **Total** | | **1,638** |

The implicit negatives teach the model what "complete disengagement" looks like — a customer who saw an offer and never interacted with it at all. Without these, the model only learned from customers who clipped something, which biases it toward the engaged population.

### Class Imbalance Handling

Adding implicit negatives shifts the class ratio from ~55% positive (819 examples) to ~28% positive (1,638 examples). XGBoost's `scale_pos_weight` parameter compensates:

```
scale_pos_weight = n_negative / n_positive = 1185 / 453 = 2.616
```

This tells XGBoost to treat each positive example as 2.6× more important during training, restoring effective balance without discarding negatives.

### Remaining Gap

| Gap | Description | Impact |
|---|---|---|
| Unclipped redemptions | Offers redeemed without explicit clipping (Auto Clip, Club Card) | 0 in this dataset — all redemptions have clips. Would matter in production. |

---

## Feature Engineering

19 features across three groups, built for every (household, offer) pair.

### Customer Features (11)
Sourced from `c360_customer_profile` + `c360_txn`:

| Feature | Source Field | Description |
|---|---|---|
| `current_point_balance` | `cp.current_point_balance` | Raw points balance |
| `points_expiring_next_month` | `cp.points_expiring_next_month` | Urgency signal |
| `is_4uplus` | `cp.clv_tier_level_id = '4U+'` | Binary tier flag |
| `gas_rewards` | `cp.gas_rewards_ind_6m` | Fuel redeemer flag |
| `doordash` | `cp.doordash_txn_ind_6m` | DoorDash usage flag |
| `instacart` | `cp.instacart_txn_ind_6m` | Instacart usage flag |
| `uber` | `cp.uber_txn_ind_6m` | Uber Eats usage flag |
| `household_size` | `cp.household_size` | Number of people in household |
| `num_children` | `cp.num_of_children` | Number of children |
| `churn_risk` | `cp.churn_risk_score_nbr` | Churn probability (0–1) |
| `days_since_last_txn` | `MAX(txn_dte)` from `c360_txn` | Recency signal (999 if no transactions) |

### Offer Features (5)
Sourced from `c360_offer` + `c360_offer_summary`:

| Feature | Source Field | Description |
|---|---|---|
| `discount_value` | `o.discount_value` | Dollar / points value of the offer |
| `is_j4u_exclusive` | `o.is_appliable_to_j4u_ind` | Exclusive to 4U+ tier |
| `is_freshpass_offer` | `o.is_freshpass_offer_ind` | FreshPass subscribers only |
| `redemption_rate` | `os.red_pct` from `c360_offer_summary` | Historical % of clips that were redeemed |
| `days_until_expiry` | `o.end_dt - CURRENT_DATE` | Days until offer expires |

### Interaction Features (3)
Computed at join time — one value per (customer, offer) pair:

| Feature | Computation | Description |
|---|---|---|
| `channel_match` | `fav_channel == delivery_channel_cd` | 1 if offer channel matches customer's preferred channel |
| `category_affinity` | Join to `c360_cat_affinity` on `(household_id, category_nm)` | Customer's historical spend affinity for the offer's category |
| `points_gap` | `max(0, current_point_balance − tier_1_points_threshold)` | How far above the Grocery Reward eligibility threshold the customer is |

---

## Model

**Algorithm:** XGBoost (`XGBClassifier`)

**Why XGBoost over logistic regression or a neural net:**
- Handles mixed feature types (booleans, integers, floats) without normalisation
- Captures non-linear interactions (e.g. high points + expiring = stronger signal than either alone)
- Fast to train on small datasets
- Feature importances are directly interpretable

**Hyperparameters:**

| Parameter | Value | Reason |
|---|---|---|
| `n_estimators` | 200 | Enough trees for a dataset of ~800 examples |
| `max_depth` | 4 | Prevents overfitting on a small dataset |
| `learning_rate` | 0.05 | Low learning rate + more trees = better generalisation |
| `subsample` | 0.8 | Row sampling per tree — reduces variance |
| `colsample_bytree` | 0.8 | Feature sampling per tree — reduces variance |
| `random_state` | 42 | Reproducibility |

---

## Training Procedure

```
1.  Load customers (head_household_ind = TRUE only — 120 households)
2.  Load active offers (offer_status_cd = 'ACTIVE' — 26 offers)
3.  Load category affinity (c360_cat_affinity)
4.  Build clip-based labels from c360_clips LEFT JOIN c360_redemptions (819 examples)
5.  Add implicit negatives — eligible pairs never clipped (819 examples)
6.  Combine → 1,638 labeled examples (453 pos / 1,185 neg)
7.  Compute scale_pos_weight = 1185 / 453 = 2.616
8.  Build 19-feature matrix for all 1,638 pairs
9.  Cross-validate AUC with 5-fold CV
10. Fit final model on all 1,638 examples
11. Score all 120 × 26 eligible pairs (with FreshPass + 4U+ filters applied)
12. Scale P(redemption) × 100 → score
13. Rank top 10 per household
14. Write to c360_scored_offers with model_type = 'propensity'
15. Write metadata to files/engine/model_metadata.json
```

**To retrain:**
```bash
python3 files/engine/scoring_ml.py
```

---

## Evaluation

**Cross-validated AUC (5-fold):** `0.5351` *(improved from 0.5248 before implicit negatives)*

Slightly above random (0.5). Expected reasons:
- **Small dataset** — 1,638 examples is still limited for 19 features
- **Synthetic data** — correlations may not perfectly mirror real redemption patterns
- **No cold-start handling** — customers with sparse history get `days_since_last_txn = 999`

In production with real C360 data (millions of clip + redemption events), AUC of 0.70–0.80 would be a realistic target.

**Feature importances (current run):**

| Rank | Feature | Importance | Note |
|---|---|---|---|
| 1 | `channel_match` | 0.111 | Jumped to #1 after implicit negatives added |
| 2 | `category_affinity` | 0.062 | |
| 3 | `is_freshpass_offer` | 0.058 | |
| 4 | `household_size` | 0.054 | |
| 5 | `redemption_rate` | 0.052 | Was #1 before implicit negatives |
| 6 | `is_4uplus` | 0.052 | |
| 7 | `churn_risk` | 0.052 | |
| 8 | `doordash` | 0.051 | |
| 9 | `points_expiring_next_month` | 0.051 | |
| 10 | `instacart` | 0.051 | |

`channel_match` moved from mid-table to #1 after implicit negatives were added. This makes intuitive sense — the implicit negatives include many cases where a customer's preferred channel didn't match the offer channel, and they ignored it entirely. The model learned that channel mismatch is the strongest predictor of non-engagement.

---

## Business Rules Applied (Hard-Coded, Not Learned)

The same filters as the rule-based engine are applied **before** scoring. These are intentional business decisions, not patterns to be learned:

| Rule | Effect |
|---|---|
| FreshPass filter | `is_freshpass_offer_ind = TRUE` offers excluded for non-subscribers |
| 4U+ filter | `is_appliable_to_j4u_ind = TRUE` offers excluded for Standard tier customers |

These are applied as a hard pre-filter on the candidate pairs before the model scores anything.

---

## Output

Writes to `c360_scored_offers` with `model_type = 'propensity'`:

| Column | Value |
|---|---|
| `score` | `P(redemption) × 100`, rounded to 2 decimal places |
| `rank` | 1–10 per household (top 10 offers) |
| `model_type` | `'propensity'` |
| `transaction_affinity` … `demographic_match` | `NULL` — not applicable to this model |
| `recency_boost_applied`, `tier_multiplier_applied` | `FALSE` — multipliers not used |

Model metadata (AUC, feature importances, training counts) is also written to `files/engine/model_metadata.json` and displayed live in the UI.

---

## How It Differs From the Rule-Based Engine

| Dimension | Rule-Based | Propensity (XGBoost) |
|---|---|---|
| **Weight source** | Manually set by team | Learned from 819 clip/redemption events |
| **Non-linear interactions** | No — each rule is independent | Yes — e.g. high points + expiring = amplified signal |
| **Cross-customer learning** | No | Yes — patterns from all customers inform each prediction |
| **Explainability** | Per-offer component score breakdown | Feature importances (global); SHAP values planned (Phase 4c) |
| **Adaptability** | Manual rule change required for new offer types | Retrains automatically as new redemption data accumulates |
| **Score range** | 30–100 (rule weighted sum + multipliers) | 0–100 (P(redemption) × 100) |

---

## Known Limitations & Next Steps

| Limitation | Status | Next Step |
|---|---|---|
| Implicit negatives not used | ✅ Fixed — 819 implicit negatives added, training set doubled to 1,638 | — |
| Unclipped redemptions missing | ⚪ Not applicable — all redemptions have clips in this dataset | Monitor in production |
| No SHAP values in UI | 🔵 Planned | Phase 4c — per-prediction SHAP explanations |
| Model not persisted to disk | 🔵 Open | Add `joblib.dump(model, 'model.pkl')` to avoid retraining on each run |
| Single model for all segments | 🔵 Open | Train separate models per segment (Fuel Redeemers, 4U+, High Churn) |
| AUC 0.535 on synthetic data | Expected | Will improve significantly on real C360 redemption history |
