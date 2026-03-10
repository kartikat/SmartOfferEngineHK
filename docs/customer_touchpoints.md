# Customer Touchpoints — SmartRewards

> Where and how customers interact with personalised offers across the Albertsons ecosystem.

---

## 1. Mobile App (Primary)

The for U app is the main surface for SmartRewards offers.

| Action | Description |
|---|---|
| Browse offers | Customer sees personalised ranked offer list |
| Clip offer | Activates the offer — discount applies at checkout |
| Unclip offer | Deactivates the offer |
| View points balance | See current balance + expiring points |
| Grocery Reward redemption | Choose points tier to redeem at checkout |
| Push notification | Personalised nudge — expiring points, new offers, exclusive deals |

**Signals captured:**
- `clip_source_cd = 'MOBILE'`
- `mobile_ind = TRUE`
- `push_enabled_ind` — whether the customer allows push notifications
- `mobile_app_download_flg`

---

## 2. Website (albertsons.com)

| Action | Description |
|---|---|
| Browse & clip offers | Same clip/unclip flow as the app |
| Weekly Ad | Digital version of the weekly circular — `is_in_weekly_ad = TRUE` offers |
| Account dashboard | View points, tier status, clipped offers |
| eCommerce cart | Clipped offers auto-apply at checkout for delivery/pickup orders |

**Signals captured:**
- `clip_source_cd = 'WEB'`
- `eng_mode_p3m / p6m / p12m` — tracks if customer engages via eCommerce

---

## 3. In-Store Checkout

| Action | Description |
|---|---|
| Offer activation | Pre-clipped offers automatically apply when loyalty card is scanned |
| Grocery Reward redemption | Cashier prompts customer to choose points redemption tier |
| Receipt | Shows applied discounts, points earned, updated balance |
| Auto-clip | Some offers clip automatically at checkout — `clip_source_cd = 'AUTO'` |

**Signals captured:**
- `c360_redemptions` — records each offer redeemed at checkout
- `c360_txn` — transaction header (store, date, basket value)
- `c360_txn_upc` — item-level detail (which UPCs were purchased)

---

## 4. Fuel Station

| Action | Description |
|---|---|
| Fuel reward redemption | Customer enters loyalty card number at pump, chooses cents-per-gallon reward |
| Grocery points → fuel | Points earned from grocery spend can be redeemed for fuel discount |

**Signals captured:**
- `c360_rewards_redeemed.src = 'Fuel'`
- `gas_rewards_ind_6m` — customer has used fuel rewards in last 6 months
- `fuel_station_purchase_ind_6m`
- `gallons_redeemed`

---

## 5. Email

| Action | Description |
|---|---|
| Weekly offer digest | Personalised email with top ranked offers |
| Points expiry alert | Nudge when points are expiring next month |
| Exclusive 4U+ offers | Email blast for premium tier customers only |
| Reactivation | Targeted email for customers with high churn risk score |

**Signals captured:**
- `email_opt_in` — customer has consented to marketing emails
- `email_id` — delivery address
- `churn_risk_score_nbr` — used to trigger reactivation campaigns
- `churn_segment_cd`

---

## 6. eCommerce — Delivery & Pickup

| Action | Description |
|---|---|
| Online checkout | Clipped offers apply automatically to delivery/pickup orders |
| DoorDash / Instacart / Uber | Third-party delivery integrations — transactions tracked |
| Drive Up & Go (DUG) | Click-and-collect — store must have `dug_ind = TRUE` |
| FreshPass | Subscription service — exclusive delivery offers, fee waivers |

**Signals captured:**
- `ecom_ind = TRUE` on `c360_txn`
- `fulfillment_type_cd` — `'DELIVERY'` or `'PICKUP'`
- `doordash_txn_ind_6m`, `instacart_txn_ind_6m`, `uber_txn_ind_6m`
- `c360_freshpass` — subscription status and order history

---

## 7. SMS

| Action | Description |
|---|---|
| Offer alert | Text message when a high-relevance offer becomes available |
| Points expiry reminder | SMS nudge before points expire |

**Signals captured:**
- `sms_opt_in` — customer has consented to SMS marketing

---

## Touchpoint Summary

| Touchpoint | Clip | Redeem | Points | Channel Signal |
|---|---|---|---|---|
| Mobile App | ✅ | ✅ | ✅ | `mobile_ind` |
| Website | ✅ | ✅ (ecom) | ✅ | `eng_mode_p6m` |
| In-Store Checkout | Auto-clip | ✅ | ✅ | `ecom_ind = FALSE` |
| Fuel Station | — | ✅ | ✅ | `gas_rewards_ind_6m` |
| Email | — | — | — | `email_opt_in` |
| Delivery / Pickup | ✅ | ✅ | ✅ | `fulfillment_type_cd` |
| SMS | — | — | — | `sms_opt_in` |
