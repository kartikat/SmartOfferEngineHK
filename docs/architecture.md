# SmartRewards — Architecture Diagrams

---

## 1. System Overview

End-to-end data flow across all four components.

```mermaid
flowchart TD
    subgraph SEED["Data Seeding (one-time)"]
        GEN["generate_data.py\n71 UPCs (30 real Dairy + 41 synthetic)\n64 offers · 10 departments\n300 customers / 120 HHs"]
    end

    subgraph DB["PostgreSQL — smartrewards"]
        direction TB
        REF["Reference Tables\nc360_store · c360_upc · c360_offer\nc360_offer_upcs"]
        CUST["Customer Tables\nc360_customer_profile (auto_clip_ind)\nc360_freshpass · c360_j4u_hh_attributes"]
        TXN["Transaction Tables\nc360_txn · c360_txn_upc\nc360_clips · c360_redemptions\nc360_rewards_redeemed"]
        AGG["Aggregate Tables\nc360_cat_affinity · c360_customer_ltv_txn_agg\nc360_hh_weekly_cat_txns\nc360_offer_summary · c360_deals_engagement_aggr"]
        OUT["Output Table\nc360_scored_offers\n3,597 rows — rule_based(1,797) + propensity(1,200) + propensity_gr(600)"]
    end

    subgraph ENGINE["Scoring Engines (batch)"]
        SCORE["scoring.py\nRule-based: Path 1 Standard + Path 2 GR\nWrites model_type='rule_based'"]
        SCOREML["scoring_ml.py\nXGBoost propensity model\nmodel.pkl (joblib) — --retrain to refresh\nWrites model_type='propensity'"]
    end

    subgraph API["REST API — port 8000"]
        FAST["FastAPI / main.py\n/offers/{household_id}\n/customer/{household_id}\n/segments/*"]
    end

    subgraph UI["Demo UI — port 8501"]
        APP["Streamlit / app.py\nLogin · My Offers · My Rewards\nMy Clipped Offers · My Profile\nSegment Explorer · Compare Customers\nCompare Models · Demo Script"]
    end

    GEN -->|"seeds all 18 tables"| DB
    CUST --> ENGINE
    TXN --> ENGINE
    AGG --> ENGINE
    REF --> ENGINE
    ENGINE -->|"writes scored offers"| OUT
    OUT --> API
    CUST --> UI
    OUT --> UI
    REF --> UI

    style SEED fill:#f0f4ff,stroke:#4a90d9
    style DB fill:#e8f5e9,stroke:#2e7d32
    style ENGINE fill:#fff3e0,stroke:#e65100
    style API fill:#fce4ec,stroke:#c62828
    style UI fill:#f3e5f5,stroke:#6a1b9a
```

---

## 2. Scoring Engine — Decision Flow

How every customer–offer pair is scored.

```mermaid
flowchart TD
    START(["For each household × active offer"])

    AC{"Auto Clip ON?\nauto_clip_ind = TRUE"}
    SKIP_GR(["Exclude GR offers entirely\n(Auto Clip replaces GR path)"])

    BR{"Business Rules\n(hard filters)"}
    FP{"FreshPass only?\nis_freshpass_offer_ind"}
    FP_CHECK{"Customer has\nactive FreshPass?"}
    J4U{"4U+ exclusive?\nis_appliable_to_j4u_ind"}
    J4U_CHECK{"Customer is 4U+?"}
    SKIP(["Skip — not eligible"])

    GR{"Grocery Reward?\nprogram_type =\n'Grocery Reward'"}

    subgraph PATH1["Path 1 — Standard Offers"]
        direction TB
        W1["Transaction Affinity\n30% · c360_cat_affinity.affinity_score"]
        W2["Redemption Match\n25% · fav_channel vs delivery_channel_cd"]
        W3["Points Eligibility\n20% · current_point_balance"]
        W4["Cart & Browse Affinity\n15% · DoorDash / Instacart / Uber flags"]
        W5["Demographic Match\n10% · age, children, diet_preference"]
        SUM1["Weighted Sum → 0–100"]
        R1{"days_since_last_txn ≤ 7?"}
        M1["× 1.2 Recency Boost"]
        R2{"4U+ AND J4U offer?"}
        M2["× 1.5 Tier Multiplier"]
        CAP1["Cap at 100"]
    end

    subgraph PATH2["Path 2 — Grocery Reward Offers"]
        direction TB
        GATE{"current_point_balance\n≥ tier_1_points_threshold?"}
        NOELIG(["Exclude entirely"])
        GW1["Points Eligibility\n40% · min(balance/threshold/2, 1.0)"]
        GW2["Category Affinity\n25%"]
        GW3["Value per Point\n15%"]
        GW4["GR History\n15% · floor 0.3"]
        GW5["Recency\n5%"]
        SUM2["Weighted Sum → 0–100"]
        EXP{"points_expiring_next_month\n≥ tier_1_threshold?"}
        M3["× 1.3 Expiry Multiplier"]
        CAP2["Cap at 100"]
    end

    WRITE(["Write to c360_scored_offers\nRank top 15 per household"])

    START --> AC
    AC -->|"Yes + GR offer"| SKIP_GR
    AC -->|"No"| BR
    BR --> FP
    FP -->|"Yes"| FP_CHECK
    FP -->|"No"| J4U
    FP_CHECK -->|"No"| SKIP
    FP_CHECK -->|"Yes"| J4U
    J4U -->|"Yes"| J4U_CHECK
    J4U -->|"No"| GR
    J4U_CHECK -->|"No"| SKIP
    J4U_CHECK -->|"Yes"| GR

    GR -->|"No"| PATH1
    GR -->|"Yes"| PATH2

    W1 & W2 & W3 & W4 & W5 --> SUM1
    SUM1 --> R1
    R1 -->|"Yes"| M1
    R1 -->|"No"| R2
    M1 --> R2
    R2 -->|"Yes"| M2
    R2 -->|"No"| CAP1
    M2 --> CAP1

    GATE -->|"No"| NOELIG
    GATE -->|"Yes"| GW1 & GW2 & GW3 & GW4 & GW5
    GW1 & GW2 & GW3 & GW4 & GW5 --> SUM2
    SUM2 --> EXP
    EXP -->|"Yes"| M3
    EXP -->|"No"| CAP2
    M3 --> CAP2

    CAP1 --> WRITE
    CAP2 --> WRITE

    style PATH1 fill:#fff8e1,stroke:#f9a825
    style PATH2 fill:#e8f5e9,stroke:#388e3c
    style SKIP fill:#ffebee,stroke:#c62828
    style NOELIG fill:#ffebee,stroke:#c62828
    style SKIP_GR fill:#ffebee,stroke:#c62828
```

---

## 3. Database — Table Groups & Key Relationships

```mermaid
erDiagram
    c360_store {
        string store_id PK
        string store_name
        string division_cd
        string city
        string state
        bool fuel_station_ind
        bool pickup_ind
        bool delivery_ind
    }

    c360_upc {
        string upc_id PK
        string product_dsc
        string brand_name
        string category_cd
        string department_cd
        float unit_price
    }

    c360_customer_profile {
        string retail_customer_uuid PK
        string household_id
        bool head_household_ind
        string clv_tier_level_id
        int current_point_balance
        int points_expiring_next_month
        string fav_channel
        string eng_mode_p6m
        bool gas_rewards_ind_6m
        string churn_segment_cd
        bool auto_clip_ind
    }

    c360_offer {
        string client_offer_id PK
        string offer_dsc
        string program_type
        string program_subtype
        string delivery_channel_cd
        string discount_type_cd
        float discount_value
        string target_level_cd
        bool is_appliable_to_j4u_ind
        bool is_freshpass_offer_ind
        date start_dt
        date end_dt
        int tier_1_points_threshold
    }

    c360_offer_upcs {
        string client_offer_id FK
        string upc_id FK
    }

    c360_freshpass {
        string household_id FK
        string freshpass_status
    }

    c360_j4u_hh_attributes {
        string household_id FK
        bool is_current_ind
        string clv_tier_level_id
    }

    c360_txn {
        string txn_id PK
        string retail_customer_uuid FK
        string store_id FK
        date txn_dte
        string channel_cd
    }

    c360_txn_upc {
        string txn_id FK
        int receipt_line_nbr
        string upc_id FK
        float purchase_price
        int qty
    }

    c360_clips {
        string clip_id PK
        string household_id FK
        string client_offer_id FK
        timestamp clip_ts
    }

    c360_redemptions {
        string redemption_id PK
        string txn_id FK
        string client_offer_id FK
        string household_id
    }

    c360_rewards_redeemed {
        string txn_id PK
        date txn_dte
        string household_id FK
        string incentive_id
        float rewards_redeemed
        float mkdn_amt
    }

    c360_cat_affinity {
        string household_id FK
        string category_nm
        float affinity_score
    }

    c360_scored_offers {
        string household_id FK
        string client_offer_id FK
        string model_type
        int rank
        float score
        float transaction_affinity
        float redemption_match
        float points_eligibility
        float cart_affinity
        float demographic_match
        bool recency_boost_applied
        bool tier_multiplier_applied
    }

    c360_customer_profile ||--o{ c360_txn : "retail_customer_uuid"
    c360_customer_profile ||--o{ c360_freshpass : "household_id"
    c360_customer_profile ||--o{ c360_j4u_hh_attributes : "household_id"
    c360_customer_profile ||--o{ c360_cat_affinity : "household_id"
    c360_customer_profile ||--o{ c360_clips : "household_id"
    c360_customer_profile ||--o{ c360_scored_offers : "household_id"
    c360_customer_profile ||--o{ c360_rewards_redeemed : "household_id"
    c360_offer ||--o{ c360_offer_upcs : "client_offer_id"
    c360_offer ||--o{ c360_clips : "client_offer_id"
    c360_offer ||--o{ c360_redemptions : "client_offer_id"
    c360_offer ||--o{ c360_scored_offers : "client_offer_id"
    c360_txn ||--o{ c360_txn_upc : "txn_id"
    c360_txn ||--o{ c360_redemptions : "txn_id"
    c360_store ||--o{ c360_txn : "store_id"
    c360_upc ||--o{ c360_txn_upc : "upc_id"
    c360_upc ||--o{ c360_offer_upcs : "upc_id"
```

---

## 4. ML Architecture — Current & Planned

```mermaid
flowchart LR
    subgraph INPUT_STD["Standard Training Data"]
        POS_S["Positive labels (label=1)\n229 examples\nclips + redemptions (standard offers)"]
        NEG_S["Negative labels (label=0)\n938 examples\nclips without redemption + implicit negatives"]
    end

    subgraph INPUT_GR["GR Training Data"]
        POS_G["Positive labels (label=1)\n189 examples\nclips + redemptions (GR offers)"]
        NEG_G["Negative labels (label=0)\n1,019 examples\nclips without redemption + implicit negatives"]
    end

    subgraph L1S["Standard Feature Engineering (16 features)"]
        CUST_S["Customer (9)\ntier · churn risk · recency · household size\ngas / DoorDash / Instacart / Uber flags"]
        OFFER_S["Offer (5)\ndiscount value · J4U exclusive\nFreshPass only · redemption rate · days until expiry"]
        INT_S["Interaction (2)\nchannel_match · category_affinity"]
    end

    subgraph L1G["GR Feature Engineering (12 features)"]
        CUST_G["Customer — points-focused (7)\npoints balance · expiring pts · tier\nchurn risk · recency · household size · children"]
        OFFER_G["Offer (3)\ndiscount value · redemption rate · days until expiry"]
        INT_G["Interaction (2)\ncategory_affinity · points_gap"]
    end

    subgraph L2["Layer 2 — XGBoost Models ✅ LIVE"]
        STD["propensity (Standard)\n1,167 training examples\nscale_pos_weight=4.10\nCV AUC: 0.626\nTop: channel_match, instacart, redemption_rate\nmodel_standard.pkl"]
        GRM["propensity_gr (GR)\n1,208 training examples\nscale_pos_weight=5.39\nCV AUC: 0.572\nTop: discount_value, points_gap, points_expiring\nmodel_gr.pkl"]
    end

    subgraph L3["Layer 3 — Planned: Blended Ranking"]
        BLEND["final_score = α × P(redemption)\n+ (1-α) × embedding_sim\nα tuned per segment"]
        RULES["Hard Business Rules\n× 1.5 Tier Multiplier\n× 1.2 Recency Boost\nFreshPass / 4U+ / Auto Clip filters"]
    end

    OUT_S["c360_scored_offers\nmodel_type='propensity'\n1,200 rows (120 HH × 10)"]
    OUT_G["c360_scored_offers\nmodel_type='propensity_gr'\n600 rows (120 HH × 5)"]

    POS_S & NEG_S --> L1S
    POS_G & NEG_G --> L1G
    CUST_S & OFFER_S & INT_S --> STD
    CUST_G & OFFER_G & INT_G --> GRM
    STD --> RULES --> OUT_S
    GRM --> OUT_G
    L2 -->|"future"| L3

    style INPUT_STD fill:#f0f4ff,stroke:#4a90d9
    style INPUT_GR fill:#e8f5e9,stroke:#2e7d32
    style L1S fill:#fff8e1,stroke:#f9a825
    style L1G fill:#fff8e1,stroke:#f9a825
    style L2 fill:#fce4ec,stroke:#c62828
    style L3 fill:#f3e5f5,stroke:#6a1b9a
```

**Milestones:**

| # | Deliverable | Status |
|---|---|---|
| 4a | Feature engineering pipeline | ✅ Done — 16 features (standard) + 12 features (GR) |
| 4b | XGBoost models + scoring | ✅ Done — standard AUC 0.626, GR AUC 0.572; separate pools |
| 4c | SHAP values in UI | 🔵 Next — per-prediction feature contributions |
| 4d | Split Standard / GR models | ✅ Done — propensity + propensity_gr |
| 4e | Score-based GR UI ranking | ✅ Done — My Rewards uses propensity_gr scores |
| 4f | Embedding model | 🔵 Future — needs >10k redemption events |

---

## 5. Offer Personalisation — Three Customer Stories

```mermaid
flowchart TD
    CATALOG["64 Active Offers\n10 departments · 2 scoring models"]

    subgraph FUEL["Story 1 — Fuel Redeemer"]
        F_PROF["Profile\nfav_channel: Weekly Ad\ngas_rewards_ind_6m: TRUE\ntier: Standard"]
        F_SCORE["High score: Fuel offers\nPartial score: J4U offers\n(eCommerce nudge applied)\nGR tiers if balance qualifies"]
        F_OUT["Ranked list\n#1 Fuel discount\n#2 Club Card prices\n#3 J4U digital offer 👈 nudge"]
    end

    subgraph PREM["Story 2 — 4U+ Subscriber"]
        P_PROF["Profile\nfav_channel: J4U\nis_freshpass: ACTIVE\ntier: 4U+"]
        P_SCORE["High score: Exclusive J4U offers\n× 1.5 Tier Multiplier applied\nFreshPass exclusive visible\nMy Rewards: all 8 GR tiers eligible"]
        P_OUT["Ranked list\n#1 FreshPass exclusive 🔒\n#2 4X Points (J4U)\n#3 BuyXGetY digital"]
    end

    subgraph AUTO["Story 3 — Auto Clip Customer"]
        A_PROF["Profile\nauto_clip_ind: TRUE\nfav_channel: J4U\ntier: Standard"]
        A_SCORE["Standard offers scored normally\nGR offers excluded from scoring\nAuto Clip: floor(balance/100) cash off\napplied automatically at checkout"]
        A_OUT["My Offers: standard ranked list\nMy Rewards: single cash-off card\n(no tier tabs — GR replaced)"]
    end

    CATALOG --> F_PROF
    CATALOG --> P_PROF
    CATALOG --> A_PROF
    F_PROF --> F_SCORE --> F_OUT
    P_PROF --> P_SCORE --> P_OUT
    A_PROF --> A_SCORE --> A_OUT

    style FUEL fill:#fff3e0,stroke:#e65100
    style PREM fill:#e8eaf6,stroke:#3949ab
    style AUTO fill:#f0fdf4,stroke:#16a34a
```
