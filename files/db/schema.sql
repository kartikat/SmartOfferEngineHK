-- SmartRewards — Local PostgreSQL Schema
-- Mirrors Albertsons C360 BigQuery views using real field names.
-- Scoped to views/columns relevant to the SmartRewards offer engine.

-- ─── CUSTOMER PROFILE ─────────────────────────────────────────────────────────
-- Source: C360_CUSTOMER_PROFILE + C360_HH_HEALTH_CURR
CREATE TABLE IF NOT EXISTS c360_customer_profile (
    retail_customer_uuid        TEXT PRIMARY KEY,
    club_card_nbr               TEXT,
    household_id                TEXT,
    head_household_ind          BOOLEAN,

    -- Identity
    first_nm                    TEXT,
    last_nm                     TEXT,
    email_id                    TEXT,
    birth_dt                    DATE,
    birth_month                 INTEGER,
    zipcode                     TEXT,
    city                        TEXT,
    state                       TEXT,

    -- Loyalty
    b4u_profile_ind             BOOLEAN,
    b4u_sign_up_dt              DATE,
    current_point_balance       INTEGER,
    points_expiring_next_month  INTEGER,
    lifetime_savings_amt        NUMERIC(12,2),
    clv_tier_level_id           TEXT,             -- e.g. '4U+', 'Standard'
    tier                        TEXT,             -- from C360_HH_HEALTH_CURR

    -- Engagement
    eng_mode_p3m                TEXT,             -- 'eCommerce', 'In-Store', 'Both'
    eng_mode_p6m                TEXT,
    eng_mode_p12m               TEXT,
    fav_channel                 TEXT,             -- from C360_HH_HEALTH_CURR
    fav_departments             TEXT,
    shopping_days               TEXT,
    deal_engagement             TEXT,

    -- Store behaviour
    customer_most_used_store_id TEXT,
    customer_last_used_store_id TEXT,
    prim_b4u_region_id          TEXT,
    pref_division_id            TEXT,

    -- Category purchase indicators (6M)
    gas_rewards_ind_6m          BOOLEAN,
    fuel_station_purchase_ind_6m BOOLEAN,
    grocery_purchase_ind_6m     BOOLEAN,
    dairy_purchase_ind_6m       BOOLEAN,
    bakery_purchase_ind_6m      BOOLEAN,
    produce_purchase_ind_6m     BOOLEAN,
    meat_purchase_ind_6m        BOOLEAN,
    seafood_purchase_ind_6m     BOOLEAN,
    pharmacy_purchase_ind_6m    BOOLEAN,
    alcohol_purchase_ind_6m     BOOLEAN,
    pet_product_purchase_ind_6m BOOLEAN,
    baby_product_purchase_ind_6m BOOLEAN,
    frozen_grocery_purchase_ind_6m BOOLEAN,
    own_brand_ind_6m            BOOLEAN,
    starbucks_purchase_ind_6m   BOOLEAN,
    doordash_txn_ind_6m         BOOLEAN,
    instacart_txn_ind_6m        BOOLEAN,
    uber_txn_ind_6m             BOOLEAN,

    -- Demographics (from C360_HH_HEALTH_CURR)
    customer_age                TEXT,
    household_size              INTEGER,
    num_of_children             INTEGER,
    pet_owner                   BOOLEAN,
    customer_income             TEXT,
    diet_preference             TEXT,
    snap_customers              BOOLEAN,

    -- Communication opt-ins
    email_opt_in                BOOLEAN,
    sms_opt_in                  BOOLEAN,
    push_enabled_ind            BOOLEAN,
    mobile_app_download_flg     BOOLEAN,

    -- Registration
    customer_created_dt         DATE,
    reg_store_id                TEXT,
    customer_status_cd          TEXT,

    -- Segments (from C360_CUSTOMER_SEGMENTS)
    shopstyles_segment_cd       TEXT,
    myneed_segment_cd           TEXT,
    churn_risk_score_nbr        NUMERIC(5,4),
    churn_segment_cd            TEXT,
    tribe                       TEXT,

    -- DW metadata
    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

-- ─── OFFER CATALOG ────────────────────────────────────────────────────────────
-- Source: C360_OFFER
CREATE TABLE IF NOT EXISTS c360_offer (
    client_offer_id             TEXT PRIMARY KEY,
    oms_offer_id                TEXT,
    incentive_id                TEXT,
    offer_nbr                   TEXT,

    -- Description
    offer_dsc                   TEXT,
    title_dsc1                  TEXT,
    headline_txt                TEXT,
    description_txt             TEXT,
    categories_txt              TEXT,

    -- Dates
    start_dt                    DATE,
    end_dt                      DATE,
    display_start_dt            DATE,
    display_end_dt              DATE,

    -- Type & channel
    offer_type                  TEXT,
    offer_type_dsc              TEXT,
    offer_form                  TEXT,
    delivery_channel_cd         TEXT,           -- 'J4U', 'Weekly Ad', 'Auto Clip'
    delivery_channel_dsc        TEXT,
    program_type                TEXT,
    program_subtype             TEXT,
    program_cd                  TEXT,
    program_cd_dsc              TEXT,

    -- Discount
    discount_type_cd            TEXT,           -- 'PCT_OFF', 'AMT_OFF', 'FUEL_CENTS'
    discount_dsc                TEXT,
    discount_value              NUMERIC(10,2),
    savings_value_txt           TEXT,
    min_purch_qty               INTEGER,
    min_purch_amt               NUMERIC(10,2),

    -- Tiered discounts
    tier_1_discount             NUMERIC(10,2),
    tier_1_threshold            NUMERIC(10,2),
    tier_2_discount             NUMERIC(10,2),
    tier_2_threshold            NUMERIC(10,2),
    tier_3_discount             NUMERIC(10,2),
    tier_3_threshold            NUMERIC(10,2),

    -- Points
    points_program_id           TEXT,
    points_program_nm           TEXT,
    -- Points earned (for earn-type offers)
    tier_1_points               INTEGER,
    tier_2_points               INTEGER,
    tier_3_points               INTEGER,
    -- Points thresholds (for Grocery Reward offers — customer spends points)
    -- Min: 50 pts. Other values are multiples of 100 (100, 200, 300, ...)
    -- NULL for non-Grocery-Reward offers
    tier_1_points_threshold     INTEGER,
    tier_2_points_threshold     INTEGER,
    tier_3_points_threshold     INTEGER,

    -- Targeting
    target_level_cd             TEXT,           -- 'ITEM', 'CATEGORY', 'BASKET'
    is_appliable_to_j4u_ind     BOOLEAN,        -- exclusive to for U (4U+)
    is_freshpass_offer_ind      BOOLEAN,        -- exclusive to FreshPass subscribers
    customer_segment_dsc        TEXT,
    is_employee_offer_ind       BOOLEAN,
    allocation_cd               TEXT,
    allocation_nm               TEXT,
    offer_status_cd             TEXT,
    is_in_weekly_ad             BOOLEAN,

    -- DW metadata
    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

-- ─── TRANSACTIONS ─────────────────────────────────────────────────────────────
-- Source: C360_TXN
CREATE TABLE IF NOT EXISTS c360_txn (
    txn_id                      TEXT PRIMARY KEY,
    store_id                    TEXT,
    txn_dte                     DATE,
    txn_ts                      TIMESTAMP,
    division_id                 TEXT,
    b4u_region_id               TEXT,
    household_id                TEXT,
    card_nbr                    TEXT,

    -- Financials
    net_sales                   NUMERIC(12,2),
    gross_amt                   NUMERIC(12,2),
    item_qty                    INTEGER,
    markdown_amt                NUMERIC(12,2),
    item_mkdn_amt               NUMERIC(12,2),
    wod_mkdn_amt                NUMERIC(12,2),
    pod_mkdn_amt                NUMERIC(12,2),

    -- Channel
    ecom_ind                    BOOLEAN,        -- TRUE = eCommerce transaction
    fulfillment_type_cd         TEXT,           -- 'DELIVERY', 'PICKUP', NULL (in-store)
    tender_type                 TEXT,
    device_type_nm              TEXT,
    slot_type_nm                TEXT,
    order_id                    TEXT,

    -- DW metadata
    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_txn_household ON c360_txn(household_id);
CREATE INDEX IF NOT EXISTS idx_txn_date ON c360_txn(txn_dte);

-- ─── CLIPS ────────────────────────────────────────────────────────────────────
-- Source: C360_CLIPS
CREATE TABLE IF NOT EXISTS c360_clips (
    clip_id                     TEXT PRIMARY KEY,
    client_offer_id             TEXT REFERENCES c360_offer(client_offer_id),
    oms_offer_id                TEXT,
    incentive_id                TEXT,

    household_id                TEXT,
    retail_customer_uuid        TEXT,           -- FK to c360_customer_profile
    card_nbr                    TEXT,
    customer_guid               TEXT,           -- legacy alias for retail_customer_uuid

    clip_ts                     TIMESTAMP,
    clip_dt                     DATE,
    clip_tm                     TIME,

    -- Source
    clip_source_cd              TEXT,           -- 'WEB', 'MOBILE', 'AUTO'
    clip_source_application_id  TEXT,
    mobile_ind                  BOOLEAN,
    clip_type_cd                TEXT,

    -- Location
    store_id                    TEXT,
    b4u_region_id               TEXT,
    b4u_region_nm               TEXT,
    division_id                 TEXT,
    division_nm                 TEXT,
    postal_cd                   TEXT,

    offer_type                  TEXT,

    -- DW metadata
    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_clips_household ON c360_clips(household_id);
CREATE INDEX IF NOT EXISTS idx_clips_offer ON c360_clips(client_offer_id);

-- ─── REDEMPTIONS ──────────────────────────────────────────────────────────────
-- Source: C360_REDEMPTIONS  — ML training labels (positive examples)
CREATE TABLE IF NOT EXISTS c360_redemptions (
    txn_id                      TEXT,
    txn_dte                     DATE,
    store_id                    TEXT,
    household_id                TEXT,
    card_nbr                    TEXT,
    receipt_line                INTEGER,

    -- Offer linkage
    client_offer_id             TEXT,
    oms_offer_id                TEXT,
    incentive_id                TEXT,
    coupon_id                   TEXT,
    promotion_id                TEXT,

    -- Financials
    net_sales                   NUMERIC(12,2),
    markdown_amt                NUMERIC(12,2),
    item_mkdn_amt               NUMERIC(12,2),

    -- Offer metadata
    offer_type                  TEXT,
    offer_form                  TEXT,
    program_type                TEXT,
    program_subtype             TEXT,
    discount_dsc                TEXT,

    -- Product
    upc_id                      TEXT,
    category_id                 TEXT,
    department_nm               TEXT,
    brand                       TEXT,
    vendor_nm                   TEXT,

    -- Rewards
    rwds_points_issued          INTEGER,
    redemptions                 INTEGER,        -- redemption count

    -- Region
    b4u_region_id               TEXT,
    division_id                 TEXT,

    -- DW metadata
    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE,

    PRIMARY KEY (txn_id, receipt_line, client_offer_id)
);

CREATE INDEX IF NOT EXISTS idx_redemptions_household ON c360_redemptions(household_id);
CREATE INDEX IF NOT EXISTS idx_redemptions_offer ON c360_redemptions(client_offer_id);

-- ─── CATEGORY AFFINITY ────────────────────────────────────────────────────────
-- Source: C360_CAT_AFFINITY (pre-computed in C360)
-- Extended with household-level spend proportions for scoring
CREATE TABLE IF NOT EXISTS c360_cat_affinity (
    household_id                TEXT,
    category_id                 TEXT,
    category_nm                 TEXT,
    affinity_score              NUMERIC(6,4),   -- 0.0 – 1.0 spend proportion
    affinity_rank               INTEGER,        -- rank within household

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,

    PRIMARY KEY (household_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_affinity_household ON c360_cat_affinity(household_id);

-- ─── SCORED OFFERS ────────────────────────────────────────────────────────────
-- Output table — written by the scoring engine, read by the API.
-- Scored at household level (grocery offers apply to the whole household).
-- retail_customer_uuid identifies the individual who will see the offer in the app.
CREATE TABLE IF NOT EXISTS c360_scored_offers (
    household_id                TEXT,           -- household-level scoring unit
    retail_customer_uuid        TEXT,           -- individual viewing the offer (head of HH or member)
    client_offer_id             TEXT,
    offer_dsc                   TEXT,
    delivery_channel_cd         TEXT,
    discount_value              NUMERIC(10,2),
    discount_type_cd            TEXT,

    score                       NUMERIC(6,2),
    rank                        INTEGER,

    -- Score components (for explainability)
    transaction_affinity        NUMERIC(5,4),
    redemption_match            NUMERIC(5,4),
    points_eligibility          NUMERIC(5,4),
    cart_affinity               NUMERIC(5,4),
    demographic_match           NUMERIC(5,4),

    -- Boosts applied
    recency_boost_applied       BOOLEAN,
    tier_multiplier_applied     BOOLEAN,

    scored_at                   TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (household_id, client_offer_id)
);

CREATE INDEX IF NOT EXISTS idx_scored_household ON c360_scored_offers(household_id);

-- ─── TRANSACTION LINE ITEMS ────────────────────────────────────────────────────
-- Source: C360_TXN_UPC
CREATE TABLE IF NOT EXISTS c360_txn_upc (
    txn_id                      TEXT,
    upc_id                      TEXT,
    plu_cd                      TEXT,
    store_id                    TEXT,
    txn_dte                     DATE,
    household_id                TEXT,
    card_nbr                    TEXT,

    net_sales                   NUMERIC(12,2),
    gross_amt                   NUMERIC(12,2),
    item_qty                    INTEGER,
    markdown_amt                NUMERIC(12,2),

    ecom_ind                    BOOLEAN,
    fulfillment_type_cd         TEXT,

    division_id                 TEXT,
    b4u_region_id               TEXT,

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE,

    receipt_line_nbr            INTEGER,        -- line position on receipt

    PRIMARY KEY (txn_id, receipt_line_nbr)
);

CREATE INDEX IF NOT EXISTS idx_txn_upc_household ON c360_txn_upc(household_id);
CREATE INDEX IF NOT EXISTS idx_txn_upc_upc ON c360_txn_upc(upc_id);

-- ─── PRODUCT CATALOG ──────────────────────────────────────────────────────────
-- Source: C360_UPC
CREATE TABLE IF NOT EXISTS c360_upc (
    upc_id                      TEXT PRIMARY KEY,
    upc_dsc                     TEXT,
    department_id               TEXT,
    department_nm               TEXT,
    category_id                 TEXT,
    category_nm                 TEXT,
    sub_category_id             TEXT,
    sub_category_nm             TEXT,
    brand                       TEXT,
    vendor_nm                   TEXT,
    own_brands_ind              BOOLEAN,
    fresh_vs_center_flag        TEXT,           -- 'Fresh', 'Center Store'

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

-- ─── OFFER UPC LINKAGE ────────────────────────────────────────────────────────
-- Source: C360_OFFER_UPCS
CREATE TABLE IF NOT EXISTS c360_offer_upcs (
    client_offer_id             TEXT,           -- explicit FK to c360_offer
    oms_offer_id                TEXT,
    incentive_id                TEXT,
    upc_id                      TEXT,
    dept_section_id             TEXT,
    any_product_ind             BOOLEAN,        -- TRUE = applies to any product in dept/section

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE,

    PRIMARY KEY (client_offer_id, upc_id)
);

CREATE INDEX IF NOT EXISTS idx_offer_upcs_upc ON c360_offer_upcs(upc_id);
CREATE INDEX IF NOT EXISTS idx_offer_upcs_offer ON c360_offer_upcs(client_offer_id);

-- ─── HOUSEHOLD WEEKLY CATEGORY TRANSACTIONS ────────────────────────────────────
-- Source: C360_HOUSEHOLD_WEEKLY_CATEGORY_TXNS
CREATE TABLE IF NOT EXISTS c360_hh_weekly_cat_txns (
    fiscal_year_id              INTEGER,
    fiscal_week_id              INTEGER,
    household_id                TEXT,
    category_id                 TEXT,
    category_nm                 TEXT,
    department_nm               TEXT,
    primary_store_id            TEXT,

    net_sales                   NUMERIC(12,2),
    item_qty                    INTEGER,
    txn_cnt                     INTEGER,

    digital_engaged_last_12_weeks_ind BOOLEAN,

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,

    PRIMARY KEY (fiscal_year_id, fiscal_week_id, household_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_hh_weekly_cat_household ON c360_hh_weekly_cat_txns(household_id);

-- ─── CUSTOMER LIFETIME TRANSACTION AGGREGATES ─────────────────────────────────
-- Source: C360_CUSTOMER_LIFETIME_TRANSACTION_AGGREGATE
CREATE TABLE IF NOT EXISTS c360_customer_ltv_txn_agg (
    retail_customer_uuid        TEXT PRIMARY KEY,
    household_id                TEXT,

    -- Sales by department
    grocery_sales_amt           NUMERIC(12,2),
    dairy_sales_amt             NUMERIC(12,2),
    bakery_sales_amt            NUMERIC(12,2),
    produce_sales_amt           NUMERIC(12,2),
    meat_sales_amt              NUMERIC(12,2),
    seafood_sales_amt           NUMERIC(12,2),
    pharmacy_sales_amt          NUMERIC(12,2),
    fuel_station_sales_amt      NUMERIC(12,2),
    floral_sales_amt            NUMERIC(12,2),
    deli_sales_amt              NUMERIC(12,2),
    frozen_sales_amt            NUMERIC(12,2),

    -- Channel aggregates
    in_store_sales_amt          NUMERIC(12,2),
    in_store_txn_cnt            INTEGER,
    online_sales_amt            NUMERIC(12,2),
    online_txn_cnt              INTEGER,

    -- Totals
    total_sales_amt             NUMERIC(12,2),
    total_txn_cnt               INTEGER,
    total_item_qty              INTEGER,

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP
);

-- ─── DEALS ENGAGEMENT AGGREGATES ──────────────────────────────────────────────
-- Source: C360_DEALS_ENGAGEMENT_AGGR
CREATE TABLE IF NOT EXISTS c360_deals_engagement_aggr (
    fiscal_period_id            TEXT,
    division_id                 TEXT,
    b4u_region_id               TEXT,

    households_clipped_any_deals        INTEGER,
    clipped_and_redeemed_count          INTEGER,
    clipped_not_redeemed_count          INTEGER,
    households_redeemed_instore         INTEGER,
    households_redeemed_online          INTEGER,
    total_redemptions                   INTEGER,
    total_markdown_amt                  NUMERIC(12,2),

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,

    PRIMARY KEY (fiscal_period_id, division_id, b4u_region_id)
);

-- ─── STORE CATALOG ────────────────────────────────────────────────────────────
-- Source: C360_STORE
CREATE TABLE IF NOT EXISTS c360_store (
    store_id                    TEXT PRIMARY KEY,
    store_nm                    TEXT,
    city                        TEXT,
    state                       TEXT,
    zip                         TEXT,
    address                     TEXT,

    division_id                 TEXT,
    division_nm                 TEXT,
    banner_nm                   TEXT,           -- 'Albertsons', 'Safeway', 'Vons', etc.
    b4u_region_id               TEXT,
    b4u_region_nm               TEXT,

    latitude                    NUMERIC(10,6),
    longitude                   NUMERIC(10,6),

    -- Capabilities
    ecom_ind                    BOOLEAN,        -- offers eCommerce
    dug_ind                     BOOLEAN,        -- Drive Up & Go
    grocery_rewards_program_ind BOOLEAN,
    gas_rewards_program_ind     BOOLEAN,
    fuel_partner_nm             TEXT,           -- e.g. 'Shell', 'Chevron'
    pharmacy_ind                BOOLEAN,
    starbucks_ind               BOOLEAN,

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

-- ─── FRESHPASS SUBSCRIPTIONS ──────────────────────────────────────────────────
-- Source: C360_FRESHPASS
CREATE TABLE IF NOT EXISTS c360_freshpass (
    retail_customer_uuid        TEXT PRIMARY KEY,
    household_id                TEXT,

    freshpass_status            TEXT,           -- 'ACTIVE', 'CANCELLED', 'EXPIRED'
    subscription_plan_type_nm   TEXT,           -- 'Monthly', 'Annual'
    fp_subscription_dt          DATE,
    fp_renewal_dt               DATE,
    fp_cancellation_dt          DATE,

    life_delivery_order_cnt     INTEGER,
    life_pickup_order_cnt       INTEGER,
    lifetime_total_savings_amt  NUMERIC(12,2),
    lifetime_delivery_fee_savings NUMERIC(12,2),

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,
    dw_logical_delete_ind       BOOLEAN DEFAULT FALSE,
    dw_current_version_ind      BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_freshpass_household ON c360_freshpass(household_id);

-- ─── J4U HOUSEHOLD ATTRIBUTES ─────────────────────────────────────────────────
-- Source: C360_J4U_HH_ATTRIBUTES
-- Stores binary attribute flags used for J4U offer targeting
CREATE TABLE IF NOT EXISTS c360_j4u_hh_attributes (
    run_id                      TEXT,           -- snapshot ID; filter on is_current_ind = TRUE
    household_id                TEXT,
    attribute_id                TEXT,
    attribute_nm                TEXT,
    attribute_flag              BOOLEAN,
    is_current_ind              BOOLEAN DEFAULT FALSE,  -- TRUE = latest run

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,

    PRIMARY KEY (run_id, household_id, attribute_id)
);

CREATE INDEX IF NOT EXISTS idx_j4u_hh_attr_household ON c360_j4u_hh_attributes(household_id);

-- ─── OFFER PERFORMANCE SUMMARY ────────────────────────────────────────────────
-- Source: C360_OFFER_SUMMARY
-- Pre-aggregated offer performance metrics (used for ML features)
CREATE TABLE IF NOT EXISTS c360_offer_summary (
    client_offer_id             TEXT PRIMARY KEY,
    oms_offer_id                TEXT,

    clips                       INTEGER,                -- total clips
    redeeming_hhs               INTEGER,                -- unique households that redeemed
    redemptions                 INTEGER,                -- total redemption count
    red_pct                     NUMERIC(6,4),           -- redemption rate = redemptions / clips
    hh_clip_red_pct             NUMERIC(6,4),           -- HH redemption rate

    markdown_amt                NUMERIC(12,2),
    promo_sales                 NUMERIC(12,2),

    rep_category_id             TEXT,                   -- representative category
    rep_category_nm             TEXT,
    rep_brand                   TEXT,

    repeat_hhs                  INTEGER,                -- HHs who redeemed 2+ times

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP
);

-- ─── REWARDS REDEEMED ─────────────────────────────────────────────────────────
-- Source: C360_REWARDS_REDEEMED
-- Points/fuel rewards redemption events
CREATE TABLE IF NOT EXISTS c360_rewards_redeemed (
    txn_id                      TEXT,
    txn_dte                     DATE,
    store_id                    TEXT,
    household_id                TEXT,
    card_nbr                    TEXT,
    incentive_id                TEXT,

    rewards_redeemed            NUMERIC(12,2),   -- dollar value redeemed
    mkdn_amt                    NUMERIC(12,2),
    gallons_redeemed            NUMERIC(10,3),   -- for fuel rewards
    net_sales                   NUMERIC(12,2),

    src                         TEXT,            -- 'Fuel', 'Grocery', 'OWN'

    division_id                 TEXT,
    b4u_region_id               TEXT,

    dw_create_ts                TIMESTAMP,
    dw_last_update_ts           TIMESTAMP,

    PRIMARY KEY (txn_id, incentive_id)
);

CREATE INDEX IF NOT EXISTS idx_rewards_redeemed_household ON c360_rewards_redeemed(household_id);
