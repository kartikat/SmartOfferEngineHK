# Data Model — SmartRewards

> 18 PostgreSQL tables mirroring the Albertsons C360 BigQuery schema.

---

## Source

All tables mirror views from the Albertsons C360 BigQuery project:
```
gcp-abs-udco-bqvw-prod-prj-01.udco_ds_cust
```
Field names are preserved exactly from the source schema.

---

## Table Inventory

| # | Table | Source C360 View | Purpose |
|---|---|---|---|
| 1 | `c360_customer_profile` | C360_CUSTOMER_PROFILE + C360_HH_HEALTH_CURR | Customer identity, loyalty tier, demographics, segments |
| 2 | `c360_offer` | C360_OFFER | Offer catalog — targeting, discounts, points, dates |
| 3 | `c360_txn` | C360_TXN | Transaction headers — store, date, channel, basket value |
| 4 | `c360_txn_upc` | C360_TXN_UPC | Line-item transactions — one row per receipt line |
| 5 | `c360_clips` | C360_CLIPS | Offer clip events — when/how a customer activated an offer |
| 6 | `c360_redemptions` | C360_REDEMPTIONS | Redemption events — ML training labels (positive examples) |
| 7 | `c360_rewards_redeemed` | C360_REWARDS_REDEEMED | Points/fuel reward redemption events |
| 8 | `c360_cat_affinity` | C360_CAT_AFFINITY | Pre-computed category affinity scores per household |
| 9 | `c360_upc` | C360_UPC | Product catalog — SKU-level with category, brand, vendor |
| 10 | `c360_offer_upcs` | C360_OFFER_UPCS | Offer → UPC linkage (item-level offer targeting) |
| 11 | `c360_store` | C360_STORE | Store catalog — location, capabilities, fuel/rewards flags |
| 12 | `c360_freshpass` | C360_FRESHPASS | FreshPass subscription status and order history |
| 13 | `c360_j4u_hh_attributes` | C360_J4U_HH_ATTRIBUTES | Binary J4U targeting attribute flags per household |
| 14 | `c360_offer_summary` | C360_OFFER_SUMMARY | Pre-aggregated offer performance (clips, redemptions, rates) |
| 15 | `c360_hh_weekly_cat_txns` | C360_HOUSEHOLD_WEEKLY_CATEGORY_TXNS | Weekly category spend per household |
| 16 | `c360_customer_ltv_txn_agg` | C360_CUSTOMER_LIFETIME_TRANSACTION_AGGREGATE | Lifetime spend aggregates by department |
| 17 | `c360_deals_engagement_aggr` | C360_DEALS_ENGAGEMENT_AGGR | Clip/redemption aggregates by region and period |
| 18 | `c360_scored_offers` | *(output table)* | Scoring engine output — read by API and UI |

---

## Key Relationships

```
c360_customer_profile (retail_customer_uuid, household_id)
    ├── c360_freshpass              via retail_customer_uuid
    ├── c360_customer_ltv_txn_agg   via retail_customer_uuid
    ├── c360_j4u_hh_attributes      via household_id
    ├── c360_clips                  via household_id + retail_customer_uuid
    ├── c360_cat_affinity           via household_id
    ├── c360_hh_weekly_cat_txns     via household_id
    └── c360_scored_offers          via household_id (scoring output)

c360_offer (client_offer_id, oms_offer_id)
    ├── c360_offer_upcs             via client_offer_id → upc_id
    ├── c360_clips                  via client_offer_id
    ├── c360_redemptions            via client_offer_id
    └── c360_offer_summary          via client_offer_id

c360_txn (txn_id, household_id, store_id)
    ├── c360_txn_upc                via txn_id + receipt_line_nbr
    ├── c360_redemptions            via txn_id
    └── c360_rewards_redeemed       via txn_id

c360_upc (upc_id)
    ├── c360_txn_upc                via upc_id
    └── c360_offer_upcs             via upc_id

c360_store (store_id)
    ├── c360_txn                    via store_id
    └── c360_clips                  via store_id
```

---

## Data Generation — Dependency Order

Tables must be seeded in this order to maintain referential integrity:

```
1.  c360_store                   standalone — no dependencies
2.  c360_upc                     standalone — no dependencies
3.  c360_customer_profile        references store (reg_store_id)
4.  c360_offer                   standalone — no dependencies
5.  c360_offer_upcs              requires offer + upc
6.  c360_freshpass               requires customer_profile
7.  c360_j4u_hh_attributes       requires customer_profile
8.  c360_txn                     requires customer_profile + store
9.  c360_txn_upc                 requires txn + upc
10. c360_clips                   requires customer_profile + offer
11. c360_redemptions             requires clips + txn + upc
12. c360_rewards_redeemed        requires redemptions
13. c360_cat_affinity            derived from txn_upc + upc
14. c360_customer_ltv_txn_agg    derived from txn_upc
15. c360_hh_weekly_cat_txns      derived from txn_upc by fiscal week
16. c360_offer_summary           derived from clips + redemptions
17. c360_deals_engagement_aggr   aggregate from clips + redemptions
18. c360_scored_offers           written by scoring engine (last)
```

---

## Key Fields Reference

### Customer Identification
| Field | Table | Description |
|---|---|---|
| `retail_customer_uuid` | customer_profile | Individual customer PK |
| `household_id` | customer_profile, txn, clips, etc. | Household-level scoring unit |
| `club_card_nbr` | customer_profile | Physical loyalty card number |

### Loyalty & Tier
| Field | Table | Description |
|---|---|---|
| `clv_tier_level_id` | customer_profile | `'4U+'` or `'Standard'` |
| `current_point_balance` | customer_profile | Points available to spend |
| `points_expiring_next_month` | customer_profile | Expiry nudge signal |
| `b4u_profile_ind` | customer_profile | Enrolled in for U program |

### Offer Targeting
| Field | Table | Description |
|---|---|---|
| `target_level_cd` | offer | `'ITEM'`, `'CATEGORY'`, `'BASKET'` |
| `is_appliable_to_j4u_ind` | offer | 4U+ exclusive |
| `is_freshpass_offer_ind` | offer | FreshPass subscribers only |
| `delivery_channel_cd` | offer | `'J4U'`, `'Weekly Ad'`, `'Auto Clip'` |
| `tier_1_points_threshold` | offer | Min points to redeem (Grocery Reward) |

### Transaction Channel
| Field | Table | Description |
|---|---|---|
| `ecom_ind` | txn, txn_upc | `TRUE` = eCommerce transaction |
| `fulfillment_type_cd` | txn | `'DELIVERY'`, `'PICKUP'`, NULL (in-store) |
| `fav_channel` | customer_profile | Customer's preferred channel |
| `eng_mode_p6m` | customer_profile | `'eCommerce'`, `'In-Store'`, `'Both'` |

### Scoring Output
| Field | Table | Description |
|---|---|---|
| `score` | scored_offers | Final 0–100 score |
| `rank` | scored_offers | Rank within household |
| `transaction_affinity` | scored_offers | Component score (0–1) |
| `recency_boost_applied` | scored_offers | Whether ×1.2 boost was applied |
| `tier_multiplier_applied` | scored_offers | Whether ×1.5 boost was applied |

---

## Schema Design Decisions

| Decision | Rationale |
|---|---|
| `c360_txn_upc` PK = `(txn_id, receipt_line_nbr)` | Same UPC can appear multiple times on a receipt |
| `c360_offer_upcs` PK = `(client_offer_id, upc_id)` | Join via `client_offer_id` not `oms_offer_id` |
| `c360_scored_offers` is household-level | Grocery offers apply to the whole household, not individuals |
| `is_current_ind` on `c360_j4u_hh_attributes` | Table stores multiple snapshots; filter `WHERE is_current_ind = TRUE` |
| `target_level_cd` added to `c360_offer` | Makes offer scope explicit for scoring engine |
| `c360_store.pharmacy_ind` + `starbucks_ind` | Demo extensions — not in source C360 schema |
