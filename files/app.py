"""
SmartOfferEngine — Albertsons Loyalty Demo
Streamlit UI: Customer Login → Profile → Personalised Offers → Segment Explorer
Run: streamlit run files/app.py
"""

import base64
import json
import os
import sys
import streamlit as st
import pandas as pd
from PIL import Image
from sqlalchemy import create_engine, text

# Category images — real Albertsons photos, 56×56 JPEG thumbnails
_cat_img_path = os.path.join(os.path.dirname(__file__), "assets", "category_images.py")
if os.path.exists(_cat_img_path):
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("category_images", _cat_img_path)
    _mod  = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    CATEGORY_IMG_B64: dict = _mod.CATEGORY_IMG_B64
else:
    CATEGORY_IMG_B64: dict = {}

# ─── CONFIG ──────────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
_engine = create_engine(DB_URL, pool_pre_ping=True)

def _logo_b64() -> str:
    with open(os.path.join(STATIC_DIR, "logo.svg"), "rb") as f:
        return base64.b64encode(f.read()).decode()

LOGO_B64 = _logo_b64()

_icon_path = os.path.join(os.path.dirname(__file__), "assets", "albertsons_icon.png")
_page_icon = Image.open(_icon_path) if os.path.exists(_icon_path) else "🛒"

def _icon_b64() -> str:
    if os.path.exists(_icon_path):
        with open(_icon_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

ICON_B64 = _icon_b64()

st.set_page_config(
    page_title="SmartOfferEngine | Albertsons",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── BRANDING ─────────────────────────────────────────────────────────────────

BLUE  = "#00529B"
RED   = "#E31837"
LIGHT = "#F0F4FA"

st.markdown(f"""
<style>
    /* Aggressive global top removal */
    * {{ margin: 0; padding: 0; }}
    html, body {{ margin: 0; padding: 0; }}
    .main {{ background-color: #FFFFFF; padding-top: 0 !important; margin-top: -40px !important; }}
    [data-testid="stAppViewContainer"] {{ padding-top: 0 !important; margin-top: -40px !important; }}
    [data-testid="stVerticalBlockBorderWrapper"]:first-of-type {{ margin-top: -50px !important; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ margin-top: -10px !important; }}
    [data-testid="stApp"] {{ margin-top: 0; padding-top: 0; }}
    .stApp {{ margin-top: 0; padding-top: 0; }}
    section[data-testid="stMain"] {{ padding-top: 0 !important; margin-top: -50px !important; }}
    div[class*="viewerMainContainer"] {{ margin-top: 0; padding-top: 0; }}

    /* Header bar */
    .abs-header {{
        background: {BLUE};
        padding: 18px 32px;
        border-radius: 10px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    h2 {{ margin-top: -4px !important; }}
    [data-testid="stMetricContainer"] {{ margin-top: -8px; }}
    .abs-header h1 {{ color: white; margin: 0; font-size: 1.6rem; }}
    .abs-header span {{ color: #A8C8F0; font-size: 0.9rem; }}

    /* Metric cards */
    .metric-card {{
        background: {LIGHT};
        border-left: 4px solid {BLUE};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
    .metric-card .label {{ color: #666; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .metric-card .value {{ color: {BLUE}; font-size: 1.5rem; font-weight: 700; }}

    /* Tier badge */
    .badge-4u {{
        background: linear-gradient(135deg, {BLUE}, #0070CC);
        color: white;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }}
    .badge-standard {{
        background: #E0E0E0;
        color: #555;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }}

    /* Ribbon — top row only, seamlessly connects to switcher row below */
    .abs-header {{
        border-radius: 10px 10px 0 0 !important;
        margin-bottom: 0 !important;
        padding-bottom: 12px !important;
    }}

    /* Customer switcher row — extends the ribbon downward */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.abs-header)
        + div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {BLUE};
        border-radius: 0 0 10px 10px;
        padding: 0 32px 14px !important;
        margin-bottom: 12px;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.abs-header)
        + div[data-testid="stVerticalBlockBorderWrapper"] label {{
        color: rgba(255,255,255,0.65) !important;
        font-size: 0.72rem !important;
        font-weight: 500 !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.abs-header)
        + div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] {{
        background: rgba(255,255,255,0.13) !important;
        border-color: rgba(255,255,255,0.3) !important;
        border-radius: 6px !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.abs-header)
        + div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] div,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.abs-header)
        + div[data-testid="stVerticalBlockBorderWrapper"] [data-baseweb="select"] span {{
        color: white !important;
    }}

    /* Offer cards */
    .offer-card {{
        border: 1px solid #DDE4EE;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 14px;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .offer-rank {{ color: {RED}; font-weight: 800; font-size: 1.1rem; }}
    .offer-name {{ font-weight: 700; font-size: 1rem; color: #222; }}
    .offer-discount {{ color: {RED}; font-weight: 700; font-size: 1.1rem; }}

    /* Primary buttons default to orange (Simulate, Sign In, etc.) */
    div[data-testid="stButton"] > button[kind="primary"] {{
        background-color: #EA580C !important;
        border-color: #EA580C !important;
        color: white !important;
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        background-color: #C2410C !important;
        border-color: #C2410C !important;
    }}

    /* Clip buttons inside offer grid columns → blue */
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="primary"] {{
        background-color: {BLUE} !important;
        border-color: {BLUE} !important;
    }}
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[kind="primary"]:hover {{
        background-color: #003d75 !important;
        border-color: #003d75 !important;
    }}

    /* Channel pills */
    .pill-j4u       {{ background:#D6EAF8; color:#1A5276; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-weeklyadd {{ background:#D1F2EB; color:#1A7A5E; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-autoclip  {{ background:#EDE7F6; color:#4A235A; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-other     {{ background:#FFF3CD; color:#856404; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}

    /* Score bar */
    .score-bar-bg {{ background:#EEF2F7; border-radius:6px; height:10px; margin-top:6px; }}
    .score-bar-fill {{ height:10px; border-radius:6px; background: linear-gradient(90deg, {BLUE}, {RED}); }}

    /* Login */
    .login-box {{
        max-width: 480px;
        margin: 60px auto;
        background: white;
        border-radius: 16px;
        padding: 40px;
        box-shadow: 0 4px 24px rgba(0,82,155,0.12);
        text-align: center;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{ background: {BLUE}; }}
    section[data-testid="stSidebar"] p:not(button p),
    section[data-testid="stSidebar"] span:not(button span),
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] .stRadio label {{ color: white !important; }}
    section[data-testid="stSidebar"] button {{
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(255,255,255,0.5) !important;
        color: white !important;
    }}
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button span {{ color: white !important; }}
    section[data-testid="stSidebar"] button:hover {{
        background: rgba(255,255,255,0.25) !important;
        border-color: white !important;
    }}

    /* Comparison view */
    .compare-header {{
        background: {BLUE};
        color: white;
        padding: 10px 16px;
        border-radius: 8px 8px 0 0;
        font-weight: 700;
        font-size: 1rem;
        text-align: center;
    }}
    .compare-card {{
        border: 2px solid {BLUE};
        border-radius: 0 0 8px 8px;
        padding: 16px;
        background: {LIGHT};
        margin-bottom: 16px;
    }}

    /* Allocation criteria */
    .criteria-card {{
        border: 1px solid #DDE4EE;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 12px;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .criteria-weight {{
        background: #00529B;
        color: white;
        padding: 3px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }}
    .criteria-title {{
        font-weight: 700;
        font-size: 1rem;
        color: #222;
    }}
    .criteria-desc {{
        color: #555;
        font-size: 0.88rem;
        margin-top: 6px;
        line-height: 1.5;
    }}
    .criteria-signals {{
        margin-top: 8px;
        font-size: 0.8rem;
        color: #888;
    }}
    .criteria-signals span {{
        background: #F0F4FA;
        border-radius: 6px;
        padding: 2px 8px;
        margin-right: 4px;
        display: inline-block;
        margin-top: 4px;
    }}
    .multiplier-card {{
        border-left: 4px solid #E31837;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        background: #FFF8F8;
    }}
    .rule-card {{
        border-left: 4px solid #856404;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        background: #FFFDF0;
    }}
    .section-heading {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #00529B;
        border-bottom: 2px solid #DDE4EE;
        padding-bottom: 8px;
        margin: 24px 0 14px 0;
    }}

    /* Demo script */
    .demo-step {{
        background: linear-gradient(135deg, {BLUE}, #0070CC);
        color: white;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 20px;
    }}
    .demo-step h3 {{ color: white; margin: 0 0 8px 0; }}
    .demo-step p  {{ color: #D0E8FF; margin: 0; font-size: 0.95rem; line-height: 1.5; }}
    .demo-step .step-tag {{
        background: {RED};
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 10px;
    }}
</style>
""", unsafe_allow_html=True)


# ─── DATA LOADING ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_customers() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            cp.household_id,
            cp.retail_customer_uuid,
            cp.first_nm || ' ' || cp.last_nm   AS full_name,
            cp.clv_tier_level_id,
            cp.current_point_balance,
            cp.points_expiring_next_month,
            cp.fav_channel,
            cp.eng_mode_p6m,
            cp.customer_age,
            cp.household_size,
            cp.num_of_children,
            cp.diet_preference,
            cp.churn_risk_score_nbr,
            cp.churn_segment_cd,
            cp.gas_rewards_ind_6m,
            cp.dairy_purchase_ind_6m,
            cp.meat_purchase_ind_6m,
            cp.produce_purchase_ind_6m,
            cp.bakery_purchase_ind_6m,
            cp.seafood_purchase_ind_6m,
            cp.frozen_grocery_purchase_ind_6m,
            cp.grocery_purchase_ind_6m,
            cp.doordash_txn_ind_6m,
            cp.instacart_txn_ind_6m,
            cp.uber_txn_ind_6m,
            cp.email_opt_in,
            cp.mobile_app_download_flg,
            cp.customer_created_dt,
            COALESCE(cp.auto_clip_ind, FALSE) AS auto_clip_ind,
            COALESCE(
                (CURRENT_DATE - MAX(t.txn_dte))::int,
                999
            ) AS days_since_last_txn,
            COALESCE(
                (cp.doordash_txn_ind_6m::int +
                 cp.instacart_txn_ind_6m::int +
                 cp.uber_txn_ind_6m::int), 0
            ) AS ecom_platform_count
        FROM c360_customer_profile cp
        LEFT JOIN c360_txn t ON t.household_id = cp.household_id
        WHERE cp.head_household_ind = TRUE
        GROUP BY
            cp.household_id, cp.retail_customer_uuid, cp.first_nm, cp.last_nm,
            cp.clv_tier_level_id, cp.current_point_balance, cp.points_expiring_next_month,
            cp.fav_channel, cp.eng_mode_p6m, cp.customer_age, cp.household_size,
            cp.num_of_children, cp.diet_preference, cp.churn_risk_score_nbr,
            cp.churn_segment_cd, cp.gas_rewards_ind_6m,
            cp.dairy_purchase_ind_6m, cp.meat_purchase_ind_6m, cp.produce_purchase_ind_6m,
            cp.bakery_purchase_ind_6m, cp.seafood_purchase_ind_6m,
            cp.frozen_grocery_purchase_ind_6m, cp.grocery_purchase_ind_6m,
            cp.email_opt_in, cp.mobile_app_download_flg, cp.customer_created_dt,
            cp.doordash_txn_ind_6m, cp.instacart_txn_ind_6m, cp.uber_txn_ind_6m,
            cp.auto_clip_ind
        ORDER BY cp.household_id
    """, _engine)


@st.cache_data(ttl=300)
def load_scored() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            so.household_id,
            so.client_offer_id,
            so.offer_dsc,
            so.delivery_channel_cd,
            so.discount_value,
            so.discount_type_cd,
            so.score,
            so.rank,
            so.model_type,
            COALESCE(so.transaction_affinity, 0) AS transaction_affinity,
            COALESCE(so.redemption_match, 0)      AS redemption_match,
            COALESCE(so.points_eligibility, 0)    AS points_eligibility,
            COALESCE(so.cart_affinity, 0)         AS cart_affinity,
            COALESCE(so.demographic_match, 0)     AS demographic_match,
            COALESCE(so.recency_boost_applied, FALSE)   AS recency_boost_applied,
            COALESCE(so.tier_multiplier_applied, FALSE) AS tier_multiplier_applied,
            o.program_type,
            o.end_dt,
            (o.end_dt - CURRENT_DATE)::int              AS days_left,
            COALESCE(os.rep_category_nm, '')            AS category_nm
        FROM c360_scored_offers so
        JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
        LEFT JOIN c360_offer_summary os ON os.client_offer_id = so.client_offer_id
        ORDER BY so.household_id, so.rank
    """, _engine)


def load_model_metadata() -> dict:
    """Load propensity model metadata from scoring_ml.py outputs."""
    meta = {}
    engine_dir = os.path.join(os.path.dirname(__file__), "engine")

    std_path = os.path.join(engine_dir, "model_metadata.json")
    if os.path.exists(std_path):
        try:
            with open(std_path) as f:
                meta["propensity_standard"] = json.load(f)
        except Exception:
            pass

    gr_path = os.path.join(engine_dir, "model_gr_metadata.json")
    if os.path.exists(gr_path):
        try:
            with open(gr_path) as f:
                meta["propensity_gr"] = json.load(f)
        except Exception:
            pass

    return meta


@st.cache_data(ttl=300)
def load_offers() -> pd.DataFrame:
    return pd.read_sql("""
        SELECT client_offer_id, offer_dsc, delivery_channel_cd, program_type,
               discount_type_cd, discount_value, target_level_cd,
               is_appliable_to_j4u_ind, is_freshpass_offer_ind
        FROM c360_offer
        WHERE offer_status_cd = 'ACTIVE'
        ORDER BY client_offer_id
    """, _engine)


customers_df = load_customers()
scored_df    = load_scored()
offers_df    = load_offers()


# ─── SIMULATION ───────────────────────────────────────────────────────────────

# Pre-scripted transaction: customer buys $45 of Meat
_SIM_CATEGORY = "Meat"
_SIM_SPEND    = 45.0
_SIM_QTY      = 3
_SIM_LABEL    = "🛒 Simulate: Customer just bought Meat ($45)"


def simulate_purchase(hid: str) -> dict:
    """Insert a synthetic Meat transaction and boost Meat affinity for this household.
    Returns {"before": [(offer_dsc, score)], scores updated in DB after call}.
    """
    import subprocess, sys, uuid as _uuid

    with _engine.begin() as conn:
        # 1. Grab a Meat UPC (fall back to any UPC if none found)
        row = conn.execute(text("""
            SELECT upc_id
            FROM c360_upc
            WHERE LOWER(department_nm) LIKE '%meat%'
            LIMIT 1
        """)).fetchone()
        upc_id = row[0] if row else "00000000001"

        # 2. Pick a store this household has visited before
        store_row = conn.execute(text("""
            SELECT store_id FROM c360_txn
            WHERE household_id = :hid
            LIMIT 1
        """), {"hid": hid}).fetchone()
        store_id = store_row[0] if store_row else conn.execute(
            text("SELECT store_id FROM c360_store LIMIT 1")
        ).fetchone()[0]

        # 3. Insert transaction header
        txn_id = str(_uuid.uuid4())
        conn.execute(text("""
            INSERT INTO c360_txn
                (txn_id, household_id, store_id, txn_dte, txn_ts,
                 net_sales, gross_amt, item_qty, ecom_ind)
            VALUES
                (:txn_id, :hid, :store, CURRENT_DATE, NOW(),
                 :total, :total, :qty, FALSE)
        """), {"txn_id": txn_id, "hid": hid, "store": store_id,
               "total": _SIM_SPEND, "qty": _SIM_QTY})

        # 4. Insert line item
        conn.execute(text("""
            INSERT INTO c360_txn_upc
                (txn_id, receipt_line_nbr, upc_id, household_id,
                 store_id, txn_dte, net_sales, gross_amt, item_qty)
            VALUES (:txn_id, 1, :upc, :hid, :store, CURRENT_DATE,
                    :total, :total, :qty)
        """), {"txn_id": txn_id, "upc": upc_id, "hid": hid,
               "store": store_id, "total": _SIM_SPEND, "qty": _SIM_QTY})

        # 5. Boost Meat affinity (+0.30, capped at 1.0)
        updated = conn.execute(text("""
            UPDATE c360_cat_affinity
            SET affinity_score = LEAST(affinity_score + 0.30, 1.0)
            WHERE household_id = :hid
              AND LOWER(category_nm) LIKE '%meat%'
        """), {"hid": hid}).rowcount

        if updated == 0:
            # No existing Meat row — insert one
            conn.execute(text("""
                INSERT INTO c360_cat_affinity
                    (household_id, category_nm, affinity_score, rank_in_hh, is_current_ind)
                VALUES (:hid, 'Meat', 0.80, 1, TRUE)
            """), {"hid": hid})

    # 6. Re-score all households (fast: ~120 HHs × 64 offers ≈ 1–2 s)
    scoring_path = os.path.join(os.path.dirname(__file__), "engine", "scoring.py")
    subprocess.run([sys.executable, scoring_path], capture_output=True, timeout=30)

    # 7. Clear score cache so the page reloads fresh data
    load_scored.clear()


# ─── SESSION STATE ────────────────────────────────────────────────────────────

if "household_id" not in st.session_state:
    st.session_state.household_id = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "clipped_offers" not in st.session_state:
    # { household_id: [client_offer_id, ...] }
    st.session_state.clipped_offers = {}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

# ─── CATEGORY ICONS ───────────────────────────────────────────────────────────

# Maps category keyword → key in CATEGORY_IMG_B64 (or emoji fallback)
CATEGORY_KEY_MAP = {
    "dairy eggs cheese": "dairy",
    "dairy":             "dairy",
    "produce":           "produce",
    "bakery":            "bakery",
    "meat":              "meat",
    "seafood":           "seafood",
    "deli":              "deli",
    "grocery":           "grocery",
    "frozen":            "frozen",
    "household":         "household",
    "fuel":              "⛽",      # no image available — emoji fallback
    "beverage":          "grocery",
    "snacks":            "grocery",
    "health":            "grocery",
}

DISCOUNT_COLORS = {
    "AMT_OFF":          "#16A34A",   # green
    "PCT_OFF":          "#16A34A",   # green
    "FUEL_CENTS":       "#D97706",   # orange
    "POINTS_MULTIPLIER":"#7C3AED",   # purple
    "FREE_DELIVERY":    "#1D4ED8",   # blue
    "GROCERY_REWARD":   "#E31837",   # red
    "DEPT_REWARD":      "#E31837",   # red
    "FREE_ITEM":        "#E31837",   # red
}


def category_icon(category_nm: str, size: int = 36) -> str:
    """Return an <img> tag with a real Albertsons category photo, or an emoji fallback."""
    key = (category_nm or "").strip().lower()
    for k, mapped in CATEGORY_KEY_MAP.items():
        if k in key:
            if mapped in CATEGORY_IMG_B64:
                b64 = CATEGORY_IMG_B64[mapped]
                return (
                    f'<img src="data:image/jpeg;base64,{b64}" '
                    f'width="{size}" height="{size}" '
                    f'style="border-radius:6px;object-fit:cover;vertical-align:middle;" />'
                )
            return mapped  # emoji fallback (e.g. ⛽)
    return "🏷️"


def discount_color(discount_type_cd: str) -> str:
    return DISCOUNT_COLORS.get(discount_type_cd or "", "#E31837")


# ─── UI HELPERS ───────────────────────────────────────────────────────────────

def channel_pill(channel: str) -> str:
    mapping = {
        "J4U":        ("pill-j4u",       "for U App"),
        "Weekly Ad":  ("pill-weeklyadd", "Weekly Ad"),
        "Auto Clip":  ("pill-autoclip",  "Auto Clip"),
    }
    css, label = mapping.get(channel, ("pill-other", channel))
    return f'<span class="{css}">{label}</span>'


def customer_feature_tags(customer: dict) -> str:
    """Return HTML chips summarising the customer's shopping profile."""
    tags = []

    def _chip(icon, label, bg, color):
        return (
            f'<span style="background:{bg}; color:{color}; font-size:0.75rem; font-weight:600;'
            f' padding:3px 10px; border-radius:999px; white-space:nowrap;">{icon} {label}</span>'
        )

    # Loyalty tier
    if customer.get("clv_tier_level_id") == "4U+":
        tags.append(_chip("⭐", "for U+", "#FEF9C3", "#854D0E"))

    # Frequent buyer
    days = customer.get("days_since_last_txn") or 999
    if days <= 7:
        tags.append(_chip("🔁", "Frequent Buyer", "#DCFCE7", "#166534"))
    elif days <= 30:
        tags.append(_chip("🛒", "Regular Shopper", "#DCFCE7", "#166534"))

    # Online / eCommerce
    is_online = any(customer.get(k) for k in
                    ["doordash_txn_ind_6m", "instacart_txn_ind_6m", "uber_txn_ind_6m"])
    if is_online:
        tags.append(_chip("📱", "Online / eCommerce", "#DBEAFE", "#1D4ED8"))

    # Fuel
    if customer.get("gas_rewards_ind_6m"):
        tags.append(_chip("⛽", "Fuel Rewards", "#FEF3C7", "#92400E"))

    # Department purchase indicators
    dept_map = [
        ("meat_purchase_ind_6m",          "🥩", "Meat Buyer"),
        ("dairy_purchase_ind_6m",          "🥛", "Dairy Buyer"),
        ("produce_purchase_ind_6m",        "🥦", "Produce Buyer"),
        ("seafood_purchase_ind_6m",        "🐟", "Seafood Buyer"),
        ("bakery_purchase_ind_6m",         "🍞", "Bakery Buyer"),
        ("frozen_grocery_purchase_ind_6m", "🧊", "Frozen Buyer"),
    ]
    for field, icon, label in dept_map:
        if customer.get(field):
            tags.append(_chip(icon, label, "#F3F4F6", "#374151"))

    # Family
    if (customer.get("num_of_children") or 0) > 0:
        tags.append(_chip("👨‍👩‍👧", "Family", "#FDF4FF", "#7E22CE"))

    # Diet preference
    diet = (customer.get("diet_preference") or "").strip()
    if diet and diet.lower() not in ("none", ""):
        tags.append(_chip("🌱", diet, "#ECFDF5", "#065F46"))

    # Churn risk
    if customer.get("churn_segment_cd") == "High Risk":
        tags.append(_chip("⚠️", "Churn Risk", "#FEE2E2", "#991B1B"))

    if not tags:
        return ""
    chips = " ".join(tags)
    return f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 4px;">{chips}</div>'


def tier_badge(tier: str) -> str:
    if tier == "4U+":
        return '<span class="badge-4u">★ for U+</span>'
    return '<span class="badge-standard">Standard</span>'


def tier_badge_sidebar(tier: str, points: int) -> str:
    """Richer tier badge for the sidebar — includes points balance."""
    if tier == "4U+":
        return (
            f'<div style="background:linear-gradient(135deg,#00529B,#0070CC);'
            f'border-radius:10px;padding:10px 14px;margin-bottom:8px;">'
            f'<div style="color:#FFD700;font-weight:800;font-size:0.9rem;">★ for U+ Member</div>'
            f'<div style="color:#A8C8F0;font-size:0.82rem;margin-top:2px;">{points:,} pts</div>'
            f'</div>'
        )
    return (
        f'<div style="background:#3B5998;border-radius:10px;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="color:#E0E0E0;font-weight:700;font-size:0.9rem;">Standard Member</div>'
        f'<div style="color:#A8C8F0;font-size:0.82rem;margin-top:2px;">{points:,} pts</div>'
        f'</div>'
    )


def score_bar(score: float) -> str:
    pct = min(score, 100)
    return f"""
    <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:{pct}%"></div>
    </div>"""


def format_discount(discount_value, discount_type_cd) -> str:
    v = discount_value or 0
    t = discount_type_cd or ""
    if t == "AMT_OFF":
        return f"${v:.2f} off"
    elif t == "PCT_OFF":
        return f"{v:.0f}% off"
    elif t == "GROCERY_REWARD":
        return f"${v:.0f} off basket"
    elif t == "DEPT_REWARD":
        return f"${v:.0f} off dept"
    elif t == "FREE_ITEM":
        return "FREE"
    elif t == "FUEL_CENTS":
        return f"{int(v * 100)}¢/gal off"
    elif t == "POINTS_MULTIPLIER":
        return f"{v:.0f}× Points"
    elif t == "FREE_DELIVERY":
        return "Free Delivery"
    return f"${v:.2f} off"


def is_grocery_reward(row) -> bool:
    return (row.get("program_type") or "").strip() == "Grocery Reward"


@st.cache_data(ttl=300)
def load_gr_offers(balance: int) -> pd.DataFrame:
    """Load all Grocery Reward offers the customer is eligible for (balance >= threshold)."""
    with _engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT
                o.client_offer_id, o.offer_dsc, o.discount_type_cd, o.discount_value,
                o.tier_1_points_threshold AS pts_threshold,
                o.program_subtype,
                o.categories_txt AS category,
                (o.end_dt - CURRENT_DATE)::int AS days_left
            FROM c360_offer o
            WHERE o.program_type = 'Grocery Reward'
              AND o.offer_status_cd = 'ACTIVE'
              AND o.tier_1_points_threshold IS NOT NULL
              AND o.tier_1_points_threshold <= :balance
            ORDER BY o.tier_1_points_threshold, o.discount_type_cd
        """), conn, params={"balance": int(balance)})


@st.cache_data(ttl=300)
def load_gr_scored_offers(hid: str, balance: int, model_type: str = "propensity_gr") -> pd.DataFrame:
    """Load GR offers for a household filtered to eligible tiers, ordered by score."""
    with _engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT
                so.client_offer_id, so.offer_dsc, so.score, so.rank,
                o.discount_type_cd, o.discount_value,
                o.tier_1_points_threshold AS pts_threshold,
                o.program_subtype,
                COALESCE(os.rep_category_nm, '') AS category,
                (o.end_dt - CURRENT_DATE)::int AS days_left
            FROM c360_scored_offers so
            JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
            LEFT JOIN c360_offer_summary os ON so.client_offer_id = os.client_offer_id
            WHERE so.model_type = :model_type
              AND so.household_id = :hid
              AND o.tier_1_points_threshold <= :balance
            ORDER BY so.score DESC
        """), conn, params={"hid": hid, "balance": int(balance), "model_type": model_type})


def logout():
    st.session_state.household_id = None
    st.session_state.page = "login"


def get_clipped(hid: str) -> list:
    if hid not in st.session_state.clipped_offers:
        # Seed from DB on first access per household per session
        try:
            with _engine.connect() as conn:
                rows = pd.read_sql(
                    text("SELECT client_offer_id FROM c360_clips WHERE household_id = :hid"),
                    conn, params={"hid": hid}
                )
            st.session_state.clipped_offers[hid] = rows["client_offer_id"].tolist()
        except Exception:
            st.session_state.clipped_offers[hid] = []
    return st.session_state.clipped_offers.get(hid, [])

def clip_count(hid: str, offer_id: str) -> int:
    return get_clipped(hid).count(offer_id)

def is_clipped(hid: str, offer_id: str) -> bool:
    return offer_id in get_clipped(hid)

def clip_offer_local(hid: str, offer_id: str, grocery_reward: bool, pts_threshold: int = None):
    clipped = st.session_state.clipped_offers.setdefault(hid, [])
    if grocery_reward or offer_id not in clipped:
        clipped.append(offer_id)
    try:
        with _engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO c360_clips (clip_id, household_id, client_offer_id, clip_ts)
                VALUES (gen_random_uuid()::text, :hid, :oid, NOW())
            """), {"hid": hid, "oid": offer_id})
            if pts_threshold:
                # Deduct points from balance
                conn.execute(text("""
                    UPDATE c360_customer_profile
                    SET current_point_balance = GREATEST(current_point_balance - :pts, 0)
                    WHERE household_id = :hid
                """), {"pts": pts_threshold, "hid": hid})
                # Record redemption
                conn.execute(text("""
                    INSERT INTO c360_rewards_redeemed
                        (txn_id, txn_dte, household_id, incentive_id, rewards_redeemed, mkdn_amt, dw_create_ts)
                    SELECT gen_random_uuid()::text, CURRENT_DATE, :hid, o.incentive_id,
                           o.discount_value, o.discount_value, NOW()
                    FROM c360_offer o WHERE o.client_offer_id = :oid
                """), {"hid": hid, "oid": offer_id})
            conn.commit()
        if pts_threshold:
            load_customers.clear()
            load_gr_offers.clear()
    except Exception:
        pass  # don't let a DB write failure break the UI

def toggle_auto_clip(hid: str, enable: bool):
    try:
        with _engine.connect() as conn:
            conn.execute(text("""
                UPDATE c360_customer_profile
                SET auto_clip_ind = :val
                WHERE household_id = :hid
            """), {"val": enable, "hid": hid})
            conn.commit()
        load_customers.clear()
    except Exception:
        pass

def unclip_offer_local(hid: str, offer_id: str):
    clipped = st.session_state.clipped_offers.get(hid, [])
    if offer_id in clipped:
        clipped.remove(offer_id)
    try:
        with _engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM c360_clips
                WHERE household_id = :hid AND client_offer_id = :oid
            """), {"hid": hid, "oid": offer_id})
            conn.commit()
    except Exception:
        pass


# ─── PAGE: LOGIN ──────────────────────────────────────────────────────────────

def page_login():
    # Centred card layout
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.html(f"""
        <div style="background:white; border-radius:20px; padding:44px 40px 36px 40px;
                    box-shadow:0 8px 40px rgba(0,82,155,0.13); text-align:center; margin-top:8px;">
            <img src="data:image/png;base64,{ICON_B64}" width="60"
                 style="margin-bottom:20px; display:block; margin-left:auto; margin-right:auto;"/>
            <div style="font-size:1.35rem; font-weight:800; color:#00529B; margin-bottom:4px;">
                SmartOfferEngine
            </div>
            <div style="font-size:0.92rem; color:#6B7280; margin-bottom:32px;">
                AI-Powered Personalised Loyalty Offers &nbsp;·&nbsp; <i>for U</i> Program
            </div>
        </div>
        """)

        st.html("""<div style="height:16px;"></div>""")

        display = customers_df.apply(
            lambda r: (
                f"{r['full_name']}  ({r['household_id']})  |  "
                f"{r['clv_tier_level_id']}  |  {r['current_point_balance']:,} pts"
            ),
            axis=1
        )
        options = ["— Select a customer —"] + display.tolist()

        st.markdown(
            '<p style="font-weight:600; color:#374151; margin-bottom:4px; font-size:0.9rem;">Select a customer account</p>',
            unsafe_allow_html=True
        )
        choice = st.selectbox("Customer", options, label_visibility="collapsed")

        st.html("""<div style="height:8px;"></div>""")
        if st.button("Sign In →", use_container_width=True, type="primary"):
            if choice == "— Select a customer —":
                st.warning("Please select a customer to continue.")
            else:
                # Extract household_id from "(HH00001)" portion
                hid = choice.split("(")[1].split(")")[0].strip()
                st.session_state.household_id = hid
                st.session_state.page = "dashboard"
                st.rerun()

        st.html("""<div style="height:6px;"></div>""")
        st.markdown(
            '<p style="text-align:center; color:#9CA3AF; font-size:0.78rem;">No password required — hackathon demo</p>',
            unsafe_allow_html=True
        )


# ─── PAGE: DASHBOARD ──────────────────────────────────────────────────────────

def page_dashboard():
    hid      = st.session_state.household_id
    customer = customers_df[customers_df["household_id"] == hid].iloc[0].to_dict()

    with st.sidebar:
        st.html(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <img src="data:image/png;base64,{ICON_B64}" height="32"
                 style="filter: brightness(0) invert(1);"/>
            <span style="color:white; font-size:1.2rem; font-weight:700;">SmartOfferEngine</span>
        </div>
        """)

        st.html(tier_badge_sidebar(customer["clv_tier_level_id"], customer["current_point_balance"]))
        clipped_count = len(get_clipped(hid))
        if clipped_count:
            st.markdown(f"✂️ **{clipped_count} offer{'s' if clipped_count > 1 else ''} clipped**")
        st.markdown("---")

        # ── Persona toggle ──────────────────────────────────────────────────
        if "persona" not in st.session_state:
            st.session_state.persona = "customer"

        col_cust, col_biz = st.columns(2)
        with col_cust:
            if st.button("Customer", use_container_width=True,
                         type="primary" if st.session_state.persona == "customer" else "secondary"):
                st.session_state.persona = "customer"
                st.session_state.page = "dashboard"
                st.rerun()
        with col_biz:
            if st.button("📊 Analyst", use_container_width=True,
                         type="primary" if st.session_state.persona == "business" else "secondary"):
                st.session_state.persona = "business"
                st.session_state.page = "dashboard"
                st.rerun()

        st.markdown("---")

        _customer_options = ["My Offers", "My Rewards", "My Clipped Offers", "My Profile"]
        _analyst_only_options = ["Problem Exploration", "Segment Explorer", "Compare Customers", "Compare Models",
                                 "Feature Weight Studio", "Feature Engineer", "How Offers Are Scored", "Offer Management", "Demo Script"]
        _current_nav = st.session_state.get("nav_page", "My Offers")

        if st.session_state.persona == "customer":
            st.html('<p style="color:rgba(255,255,255,0.55); font-size:0.72rem; margin:0 0 6px 0; text-transform:uppercase; letter-spacing:0.05em;">Customer View</p>')
            _idx = _customer_options.index(_current_nav) if _current_nav in _customer_options else 0
            nav  = st.radio("Navigate", _customer_options, index=_idx,
                            key="nav_customer", label_visibility="collapsed")
        else:
            def _set_nav_cust():
                st.session_state.nav_page = st.session_state.nav_analyst_cust
            def _set_nav_anal():
                st.session_state.nav_page = st.session_state.nav_analyst_tools

            st.html('<p style="color:rgba(255,255,255,0.55); font-size:0.72rem; margin:0 0 6px 0; text-transform:uppercase; letter-spacing:0.05em;">Customer View</p>')
            _cust_idx = _customer_options.index(_current_nav) if _current_nav in _customer_options else 0
            st.radio("Navigate customer", _customer_options,
                     index=_cust_idx, key="nav_analyst_cust",
                     label_visibility="collapsed", on_change=_set_nav_cust)
            st.html('<p style="color:rgba(255,255,255,0.55); font-size:0.72rem; margin:8px 0 6px 0; text-transform:uppercase; letter-spacing:0.05em;">Analyst Tools</p>')
            _anal_idx = _analyst_only_options.index(_current_nav) if _current_nav in _analyst_only_options else 0
            st.radio("Navigate analyst", _analyst_only_options,
                     index=_anal_idx, key="nav_analyst_tools",
                     label_visibility="collapsed", on_change=_set_nav_anal)
            nav = _current_nav

        # Keep nav_page in sync with manual sidebar selection (only when not in demo_mode)
        if not st.session_state.get("demo_mode", False):
            st.session_state.nav_page = nav

        st.markdown("---")

        # Demo mode toggle
        if st.session_state.get("demo_mode", False):
            if st.button("⏹ Exit Presentation", use_container_width=True):
                st.session_state.demo_mode = False
                st.rerun()
        else:
            if st.button("🎬 Present", use_container_width=True, type="primary"):
                st.session_state.demo_mode = True
                st.session_state.demo_panel_open = True
                st.session_state.demo_step = 0
                first = DEMO_STEPS[0]
                st.session_state.nav_page = first.get("nav_page", "Demo Script")
                st.session_state.persona  = first.get("persona", "business")
                st.rerun()

        st.markdown("---")
        if st.button("Sign Out"):
            logout()
            st.rerun()

    persona = st.session_state.get("persona", "customer")
    if persona == "customer":
        persona_pill = f'<span style="background:#E0F2FE; color:#0369A1; font-size:0.75rem; font-weight:600; padding:3px 10px; border-radius:999px;"><img src="data:image/png;base64,{ICON_B64}" height="12" style="vertical-align:middle; margin-right:4px;"/> Customer View</span>'
    else:
        persona_pill = '<span style="background:#EDE9FE; color:#6D28D9; font-size:0.75rem; font-weight:600; padding:3px 10px; border-radius:999px;">📊 Analyst View</span>'

    st.html("""<div style="margin-top: -50px;"></div>""")
    st.html(f"""
    <div class="abs-header" style="margin-top: 0;">
        <img src="data:image/png;base64,{ICON_B64}" height="40" style="filter: brightness(0) invert(1);"/>
        <span style="color:#A8C8F0; font-size:0.9rem;">Personalised Offers Engine &nbsp;|&nbsp; <i>for U</i> Loyalty Program</span>
        &nbsp;&nbsp;{persona_pill}
    </div>
    """)

    # ── Customer switcher — visually inside the blue ribbon ───────────────────
    _sw_options = customers_df.apply(
        lambda r: (
            r["household_id"],
            f"{r['full_name']}  ({r['household_id']})  |  {r['clv_tier_level_id']}  |  {r['current_point_balance']:,} pts"
        ), axis=1
    ).tolist()
    _sw_idx = next((i for i, (h, _) in enumerate(_sw_options) if h == hid), 0)
    _, _sw_right = st.columns([1, 1])
    with _sw_right:
        _sw_label = st.selectbox(
            "Viewing account",
            options=[l for _, l in _sw_options],
            index=_sw_idx,
            key="main_customer_switcher",
        )
    _sw_hid = next(h for h, l in _sw_options if l == _sw_label)
    if _sw_hid != hid:
        st.session_state.household_id = _sw_hid
        st.rerun()

    def _dispatch_page(nav):
        if nav == "My Profile":
            render_profile(customer)
        elif nav == "My Offers":
            render_offers(customer, hid)
        elif nav == "My Rewards":
            render_rewards(customer, hid)
        elif nav == "My Clipped Offers":
            render_clipped_offers(hid)
        elif nav == "Compare Customers":
            render_comparison(hid)
        elif nav == "Compare Models":
            render_model_comparison(hid)
        elif nav == "Feature Weight Studio":
            render_weight_studio(hid)
        elif nav == "How Offers Are Scored":
            render_allocation_criteria()
        elif nav == "Feature Engineer":
            render_feature_engineer()
        elif nav == "Offer Management":
            render_oms()
        elif nav == "Demo Script":
            render_demo_script()
        elif nav == "Problem Exploration":
            render_problem_exploration()
        else:
            render_segments()

    if st.session_state.get("demo_mode", False):
        panel_open = st.session_state.get("demo_panel_open", True)
        demo_nav = st.session_state.get("nav_page", "Problem Exploration")
        if panel_open:
            main_col, panel_col = st.columns([1, 1], gap="medium")
            with panel_col:
                render_demo_panel()
            with main_col:
                _dispatch_page(demo_nav)
        else:
            # Panel collapsed — full width content + small expand button top-right
            _, btn_col = st.columns([11, 1])
            with btn_col:
                if st.button("▶", help="Show presenter panel", use_container_width=True):
                    st.session_state.demo_panel_open = True
                    st.rerun()
            _dispatch_page(demo_nav)
    else:
        _dispatch_page(nav)


def render_profile(customer: dict):
    st.subheader("My Profile")
    tier_html = tier_badge(customer["clv_tier_level_id"])
    hid = customer["household_id"]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.html(f"""
        <div class="metric-card">
            <div class="label">Household ID</div>
            <div class="value" style="font-size:1.1rem;">{hid}</div>
        </div>
        <div class="metric-card">
            <div class="label">Loyalty Tier</div>
            <div style="margin-top:6px;">{tier_html}</div>
        </div>
        <div class="metric-card">
            <div class="label">Points Balance</div>
            <div class="value">{customer['current_point_balance']:,} pts</div>
        </div>
        """)

    with col2:
        expiring = customer.get("points_expiring_next_month") or 0
        expiry_html = (
            f'<div class="metric-card" style="border-left-color:#E31837;">'
            f'<div class="label">Points Expiring Next Month</div>'
            f'<div class="value" style="color:#E31837;">{expiring:,} pts</div></div>'
        ) if expiring > 0 else ""

        st.html(f"""
        <div class="metric-card">
            <div class="label">Favourite Channel</div>
            <div class="value" style="font-size:1.1rem;">{customer['fav_channel']}</div>
        </div>
        <div class="metric-card">
            <div class="label">Days Since Last Transaction</div>
            <div class="value">{customer['days_since_last_txn']} days</div>
        </div>
        <div class="metric-card">
            <div class="label">Engagement Mode (6M)</div>
            <div class="value" style="font-size:1.1rem;">{customer.get('eng_mode_p6m', '—')}</div>
        </div>
        {expiry_html}
        """)

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Age Group",       customer.get("customer_age", "—"))
    c2.metric("Household Size",  customer.get("household_size", "—"))
    c3.metric("Churn Risk",      customer.get("churn_segment_cd", "—"))
    c4.metric("eCommerce Platforms Used", customer.get("ecom_platform_count", 0))


def render_offers(customer: dict, hid: str):

    # ── Simulate Purchase CTA ────────────────────────────────────────────────
    sim_key_before = f"sim_before_{hid}"
    sim_key_done   = f"sim_done_{hid}"

    # Capture "before" rankings just before running the simulation
    _pre_offers = scored_df[
        (scored_df["household_id"] == hid) &
        (scored_df["model_type"] == "rule_based") &
        (scored_df["program_type"] != "Grocery Reward")
    ].sort_values("score", ascending=False).head(10)
    _pre_list = [(r["offer_dsc"], round(float(r["score"]), 1))
                 for _, r in _pre_offers.iterrows()]

    if st.button(_SIM_LABEL, type="primary", key="simulate_purchase_btn"):
        st.session_state[sim_key_before] = _pre_list
        with st.spinner("Recording transaction · Updating affinity · Re-scoring…"):
            simulate_purchase(hid)
        st.session_state[sim_key_done] = True
        st.rerun()

    # Show before/after delta after simulation
    if st.session_state.get(sim_key_done):
        before = st.session_state.get(sim_key_before, [])
        before_rank = {name: i + 1 for i, (name, _) in enumerate(before)}

        # Reload fresh scores after simulation
        fresh = load_scored()
        after_offers = fresh[
            (fresh["household_id"] == hid) &
            (fresh["model_type"] == "rule_based") &
            (fresh["program_type"] != "Grocery Reward")
        ].sort_values("score", ascending=False).head(10)

        deltas = []
        for new_rank, (_, row) in enumerate(after_offers.iterrows(), 1):
            name = row["offer_dsc"]
            old_rank = before_rank.get(name)
            if old_rank is not None and old_rank != new_rank:
                diff = old_rank - new_rank  # positive = moved up
                deltas.append((diff, name, old_rank, new_rank))
        deltas.sort(key=lambda x: -abs(x[0]))

        moved_up   = [d for d in deltas if d[0] > 0]
        moved_down = [d for d in deltas if d[0] < 0]

        up_lines   = " &nbsp;·&nbsp; ".join(
            f'<b>{n}</b> ▲{d}' for d, n, _, _ in moved_up[:3]
        )
        down_lines = " &nbsp;·&nbsp; ".join(
            f'<b>{n}</b> ▼{abs(d)}' for d, n, _, _ in moved_down[:2]
        )

        st.html(f"""
        <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:10px;
                    padding:12px 18px; margin-bottom:14px;">
            <div style="font-weight:700; color:#15803D; margin-bottom:6px;">
                ✅ Transaction recorded — offers re-ranked
            </div>
            <div style="font-size:0.85rem; color:#166534;">
                🛒 &nbsp;Meat purchase ($45) added to transaction history
                &nbsp;·&nbsp; Meat category affinity boosted
            </div>
            {"<div style='margin-top:8px; font-size:0.85rem; color:#15803D;'>▲ Moved up: " + up_lines + "</div>" if up_lines else ""}
            {"<div style='font-size:0.85rem; color:#B45309;'>▼ Moved down: " + down_lines + "</div>" if down_lines else ""}
        </div>
        """)

        if st.button("↺ Reset simulation", key=f"sim_reset_{hid}"):
            del st.session_state[sim_key_done]
            del st.session_state[sim_key_before]
            st.rerun()

    # Model toggle — standard offers only; GR model lives on My Rewards
    model_choice = st.radio(
        "Scoring model",
        ["📋 Rule-Based", "🤖 Propensity (XGBoost)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    selected_model = "rule_based" if "Rule-Based" in model_choice else "propensity"

    meta = load_model_metadata()

    if selected_model == "propensity" and "propensity_standard" in meta:
        meta_data = meta["propensity_standard"]
        st.html(f"""
        <div style="background:#EEF2FF; border:1px solid #C7D2FE; border-radius:8px;
                    padding:10px 16px; margin-bottom:12px; font-size:0.85rem;">
            🤖 <b>XGBoost Propensity (Standard Offers)</b> &nbsp;|&nbsp;
            Trained on <b>{meta_data.get('n_train', '—')}</b> offer pairs
            ({meta_data.get('n_pos', '—')} redeemed / {meta_data.get('n_neg', '—')} not redeemed)
            &nbsp;|&nbsp; CV AUC: <b>{meta_data.get('auc_cv', '—')}</b>
            &nbsp;|&nbsp; Top signals:
            <b>{', '.join(f[0].replace('_', ' ') for f in meta_data.get('top_features', [])[:3])}</b>
        </div>
        """)
    else:
        st.html("""
        <div style="background:#F0F9FF; border:1px solid #BAE6FD; border-radius:8px;
                    padding:10px 16px; margin-bottom:12px; font-size:0.85rem;">
            📋 <b>Rule-Based Engine</b> &nbsp;|&nbsp;
            5 weighted rules + multipliers. Weights manually set by the team.
            Score breakdown available per offer.
        </div>
        """)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        channel_filter = st.selectbox(
            "Filter by Channel",
            ["All Channels", "J4U", "Weekly Ad", "Auto Clip"]
        )
    with col2:
        top_n = st.slider("Number of Offers", min_value=3, max_value=9, value=6, step=3)
    with col3:
        # Only show toggle for rule-based model
        if selected_model == "rule_based":
            show_scores = st.toggle("Show Score Breakdown", value=False)
        else:
            show_scores = False
            st.caption("*(ML models don't show breakdowns)*")

    # Filter by model type
    cust_offers = scored_df[
        (scored_df["household_id"] == hid) &
        (scored_df["model_type"] == selected_model)
    ].copy()
    
    # GR offers are always excluded from My Offers — they belong on My Rewards
    cust_offers = cust_offers[cust_offers["program_type"] != "Grocery Reward"].copy()
    if channel_filter != "All Channels":
        cust_offers = cust_offers[cust_offers["delivery_channel_cd"] == channel_filter]
    cust_offers = cust_offers.sort_values("score", ascending=False).head(top_n)

    if cust_offers.empty:
        st.info("No offers found for the selected filters.")
        return

    tags_html = customer_feature_tags(customer)
    if tags_html:
        st.html(tags_html)
    st.markdown("")

    # ── 3-column grid matching Albertsons for U design ────────────────────────
    offers_list = list(cust_offers.iterrows())
    for row_start in range(0, len(offers_list), 3):
        batch = offers_list[row_start:row_start + 3]
        grid_cols = st.columns(3, gap="medium")

        for col_idx, (_, row) in enumerate(batch):
            with grid_cols[col_idx]:
                offer_id  = row["client_offer_id"]
                gr        = is_grocery_reward(row)
                clipped   = is_clipped(hid, offer_id)
                n_clipped = clip_count(hid, offer_id)

                disc_label = format_discount(row["discount_value"], row["discount_type_cd"])
                icon       = category_icon(row.get("category_nm", ""), size=76)

                days_left = int(row["days_left"]) if row["days_left"] is not None else None
                if days_left is not None and days_left <= 3:
                    expiry_line = f'<span style="color:#DC2626; font-weight:600;">Expires in {days_left}d</span>'
                elif days_left is not None and days_left <= 7:
                    expiry_line = f'<span style="color:#D97706;">Expires in {days_left}d</span>'
                elif days_left is not None:
                    expiry_line = f"Expires in {days_left}d"
                else:
                    expiry_line = "No expiry info"

                border_color = "#16A34A" if clipped else "#DDE4EE"
                bg_color     = "#F0FBF6" if clipped else "white"

                boosts = []
                if row.get("recency_boost_applied"):
                    boosts.append("⚡")
                if row.get("tier_multiplier_applied"):
                    boosts.append("★")
                boost_badge = (
                    f'<span style="font-size:0.75rem; color:#92400E; margin-left:4px;">'
                    + " ".join(boosts) + "</span>"
                ) if boosts else ""

                clipped_bottom = (
                    f'<span style="color:#16A34A; font-weight:700; font-size:0.88rem;">'
                    f'✓ Clipped{"  ×" + str(n_clipped) if n_clipped > 1 else ""}</span>'
                ) if clipped else ""

                st.html(f"""
                <div style="border:1.5px solid {border_color}; border-radius:12px;
                            padding:15px 15px 12px; background:{bg_color};
                            box-shadow:0 1px 6px rgba(0,0,0,0.07);
                            display:flex; flex-direction:column; min-height:210px;">

                    <!-- for U badge + discount value -->
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:11px;">
                        <span style="background:#00529B; color:white; font-size:0.58rem;
                                     font-weight:800; padding:2px 6px; border-radius:4px;
                                     letter-spacing:0.03em; flex-shrink:0;">for U</span>
                        <span style="color:#1a56db; font-weight:800; font-size:1.05rem; flex:1;">
                            {disc_label}
                        </span>
                        {boost_badge}
                    </div>

                    <!-- Product info + category image -->
                    <div style="display:flex; gap:10px; align-items:flex-start; flex:1;">
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:700; font-size:0.9rem; color:#111827;
                                        margin-bottom:3px; line-height:1.35;
                                        overflow:hidden; display:-webkit-box;
                                        -webkit-line-clamp:2; -webkit-box-orient:vertical;">
                                {row['offer_dsc']}
                            </div>
                            <div style="font-size:0.78rem; color:#6B7280; margin-bottom:8px;">
                                {row.get('category_nm', '')}
                            </div>
                            <span style="color:#1a56db; font-size:0.78rem; cursor:pointer;">
                                Offer Details
                            </span>
                        </div>
                        <div style="flex-shrink:0; width:76px; height:76px; background:#F3F4F6;
                                    border-radius:8px; display:flex; align-items:center;
                                    justify-content:center; overflow:hidden;">
                            {icon}
                        </div>
                    </div>

                    <!-- Divider -->
                    <div style="border-top:1px solid #E5E7EB; margin:10px 0 8px;"></div>

                    <!-- Clipped status + expiry -->
                    <div style="display:flex; justify-content:space-between; align-items:center; min-height:28px;">
                        <div>{clipped_bottom}</div>
                        <div style="text-align:right; font-size:0.7rem; color:#9CA3AF; line-height:1.5;">
                            Unlimited use<br/>{expiry_line}
                        </div>
                    </div>
                </div>
                """)

                # Clip / Unclip actions below the card
                if clipped:
                    if st.button("Unclip", key=f"unclip_{hid}_{offer_id}", use_container_width=True):
                        unclip_offer_local(hid, offer_id)
                        st.rerun()
                else:
                    if st.button("Clip", key=f"clip_{hid}_{offer_id}", type="primary",
                                 use_container_width=True):
                        clip_offer_local(hid, offer_id, gr)
                        st.rerun()

                if show_scores:
                    with st.expander("📊 Score breakdown", expanded=False):
                        labels = {
                            "transaction_affinity": ("Transaction Affinity", "30%"),
                            "redemption_match":     ("Redemption Match",     "25%"),
                            "points_eligibility":   ("Points Eligibility",   "20%"),
                            "cart_affinity":        ("Cart / Browse",        "15%"),
                            "demographic_match":    ("Demographic",          "10%"),
                        }
                        for key, (label, weight) in labels.items():
                            val = float(row[key])
                            st.caption(f"**{label}** ({weight})")
                            st.progress(val, text=f"{val:.1%}")

    # ── Grocery Rewards teaser / Auto Clip status ─────────────────────────────
    balance = customer.get("current_point_balance", 0) or 0
    auto_clip = customer.get("auto_clip_ind", False) or False
    st.markdown("---")
    if auto_clip:
        cash_value = balance // 100
        st.html(f"""
        <div style="background:linear-gradient(135deg,#F0FDF4,#DCFCE7); border:1.5px solid #16A34A;
                    border-radius:12px; padding:16px 20px; display:flex;
                    justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:1rem; font-weight:700; color:#14532D;">
                    ✂️ Auto Clip Active
                </div>
                <div style="font-size:0.85rem; color:#166534; margin-top:4px;">
                    Your <b>{balance:,} pts</b> will automatically apply
                    <b>${cash_value}</b> off at your next checkout.
                </div>
            </div>
            <div style="font-size:1.8rem;">💵</div>
        </div>
        """)
        st.caption("Manage Auto Clip in **My Rewards**.")
    else:
        gr_df = load_gr_offers(balance)
        if not gr_df.empty:
            n_eligible = gr_df["pts_threshold"].nunique()
            st.html(f"""
            <div style="background:linear-gradient(135deg,#FFF7ED,#FEF3C7); border:1.5px solid #F59E0B;
                        border-radius:12px; padding:16px 20px; display:flex;
                        justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:1rem; font-weight:700; color:#92400E;">
                        🎁 Grocery Rewards Available
                    </div>
                    <div style="font-size:0.85rem; color:#78350F; margin-top:4px;">
                        You qualify for <b>{n_eligible} reward tier{'s' if n_eligible > 1 else ''}</b>
                        with your <b>{balance:,} pts</b> balance
                        — free items, basket discounts &amp; department savings.
                    </div>
                </div>
                <div style="font-size:1.8rem;">🏆</div>
            </div>
            """)
            st.caption("Go to **My Rewards** in the sidebar to redeem your points.")


def render_rewards(customer: dict, hid: str):
    """My Rewards page — Auto Clip toggle + tier tab UX for Grocery Reward offers."""
    balance = customer.get("current_point_balance", 0) or 0
    auto_clip = customer.get("auto_clip_ind", False) or False

    st.subheader("My Rewards")

    # ── Auto Clip toggle ──────────────────────────────────────────────────────
    st.markdown("#### Auto Clip")
    st.caption("Turn on Auto Clip to automatically receive $1 off for every 100 points at checkout. Replaces Grocery Reward tiers.")
    col_toggle, col_status = st.columns([1, 3])
    with col_toggle:
        if auto_clip:
            if st.button("Turn Off Auto Clip", type="secondary", use_container_width=True):
                toggle_auto_clip(hid, False)
                st.rerun()
        else:
            if st.button("Turn On Auto Clip", type="primary", use_container_width=True):
                toggle_auto_clip(hid, True)
                st.rerun()
    with col_status:
        if auto_clip:
            cash_value = balance // 100
            st.html(f"""
            <div style="background:#F0FDF4; border:1.5px solid #16A34A; border-radius:8px;
                        padding:10px 16px; display:inline-block;">
                <span style="color:#14532D; font-weight:700;">✂️ Active</span>
                &nbsp;—&nbsp;
                <span style="color:#166534;">{balance:,} pts = <b>${cash_value} off</b> at next checkout</span>
            </div>
            """)
        else:
            st.html("""
            <div style="background:#F9FAFB; border:1.5px solid #D1D5DB; border-radius:8px;
                        padding:10px 16px; display:inline-block;">
                <span style="color:#6B7280;">Off — choose a Grocery Reward tier below instead</span>
            </div>
            """)

    st.markdown("---")

    # ── If Auto Clip is ON, GR tiers are replaced ─────────────────────────────
    if auto_clip:
        cash_value = balance // 100
        st.html(f"""
        <div style="background:linear-gradient(135deg,#F0FDF4,#DCFCE7); border:1.5px solid #16A34A;
                    border-radius:12px; padding:24px; text-align:center;">
            <div style="font-size:1.5rem; font-weight:800; color:#14532D; margin-bottom:8px;">
                ${cash_value} off your next purchase
            </div>
            <div style="font-size:0.9rem; color:#166534;">
                Based on your <b>{balance:,} pts</b> balance at $1 per 100 pts.
                Discount applied automatically at checkout — no action needed.
            </div>
        </div>
        """)
        st.info("Grocery Reward tiers are not available while Auto Clip is on. Turn off Auto Clip above to access them.")
        return

    # Points balance banner
    st.html(f"""
    <div style="background:linear-gradient(135deg,#FFF7ED,#FEF3C7); border:1.5px solid #F59E0B;
                border-radius:12px; padding:16px 24px; margin-bottom:20px;
                display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-size:0.85rem; color:#92400E; font-weight:600; text-transform:uppercase;
                        letter-spacing:0.05em;">Your Points Balance</div>
            <div style="font-size:2.2rem; font-weight:800; color:#78350F;">{balance:,} pts</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.8rem; color:#92400E;">Tier</div>
            <div style="font-size:1.1rem; font-weight:700; color:#92400E;">
                {customer.get('clv_tier_level_id', 'Standard')}
            </div>
        </div>
    </div>
    """)

    # Model toggle
    gr_model_choice = st.radio(
        "GR scoring model",
        ["🎯 Propensity (XGBoost)", "📋 Rule-Based"],
        horizontal=True,
        label_visibility="collapsed",
    )
    gr_model = "propensity_gr" if "Propensity" in gr_model_choice else "rule_based"

    meta = load_model_metadata()
    if gr_model == "propensity_gr" and "propensity_gr" in meta:
        meta_data = meta["propensity_gr"]
        st.html(f"""
        <div style="background:#F0FDF4; border:1px solid #BBDBB5; border-radius:8px;
                    padding:10px 16px; margin-bottom:12px; font-size:0.85rem;">
            🎯 <b>XGBoost Propensity (Grocery Reward)</b> &nbsp;|&nbsp;
            Trained on <b>{meta_data.get('n_train', '—')}</b> GR offer pairs
            ({meta_data.get('n_pos', '—')} redeemed / {meta_data.get('n_neg', '—')} not redeemed)
            &nbsp;|&nbsp; CV AUC: <b>{meta_data.get('auc_cv', '—')}</b>
            &nbsp;|&nbsp; Top signals:
            <b>{', '.join(f[0].replace('_', ' ') for f in meta_data.get('top_features', [])[:3])}</b>
        </div>
        """)
    else:
        st.html("""
        <div style="background:#F0F9FF; border:1px solid #BAE6FD; border-radius:8px;
                    padding:10px 16px; margin-bottom:12px; font-size:0.85rem;">
            📋 <b>Rule-Based Engine (GR Path)</b> &nbsp;|&nbsp;
            Points eligibility 40% · category affinity 25% · value/pt 15% · GR history 15% · recency 5%.
            ×1.3 expiry boost when points expire next month.
        </div>
        """)

    gr_df = load_gr_scored_offers(hid, balance, model_type=gr_model)
    if gr_df.empty:
        st.info("You don't have enough points for any Grocery Rewards yet. Keep shopping to earn points!")
        return

    model_label = "personalised score" if gr_model == "propensity_gr" else "rule-based score"
    st.caption(f"**{len(gr_df)} rewards available** — ranked by your {model_label}. Highest value for you shown first.")
    st.markdown("")

    gr_list = list(gr_df.iterrows())
    for row_start in range(0, len(gr_list), 3):
        batch = gr_list[row_start:row_start + 3]
        grid_cols = st.columns(3, gap="medium")
        for col_idx, (_, row) in enumerate(batch):
            tier      = int(row["pts_threshold"])
            disc_type = row["discount_type_cd"]
            days_left = int(row["days_left"]) if row["days_left"] is not None else None
            offer_id  = row["client_offer_id"]
            disc_label = format_discount(row["discount_value"], disc_type)
            clipped   = offer_id in get_clipped(hid)

            # Category image (same logic as My Offers)
            cat_nm = row.get("category", "") or ""
            cat_img = CATEGORY_IMG_B64.get(cat_nm, "")
            if cat_img:
                icon = f'<img src="data:image/jpeg;base64,{cat_img}" width="76" height="76" style="object-fit:cover; border-radius:6px;"/>'
            else:
                icon = f'<span style="font-size:2rem;">{category_icon(cat_nm)}</span>'

            # Expiry line
            if days_left is not None and days_left <= 3:
                expiry_line = f'<span style="color:#DC2626; font-weight:700;">Expires {days_left}d</span>'
                border_color = "#FCA5A5"
                bg_color = "#FFF5F5"
            elif days_left is not None and days_left <= 7:
                expiry_line = f'<span style="color:#D97706;">Expires {days_left}d</span>'
                border_color = "#FCD34D"
                bg_color = "#FFFBEB"
            else:
                expiry_line = f"Expires {days_left}d" if days_left else "No expiry"
                border_color = "#E5E7EB"
                bg_color = "#FFFFFF"

            # Clipped badge
            clipped_bottom = (
                '<span style="color:#16A34A; font-size:0.75rem; font-weight:700;">✓ Clipped</span>'
            ) if clipped else ""

            # Points cost badge (bottom-left alongside clipped)
            pts_badge = f'<span style="background:#FEF3C7; color:#92400E; font-size:0.7rem; font-weight:700; padding:2px 7px; border-radius:99px; margin-right:4px;">{tier:,} pts</span>'

            with grid_cols[col_idx]:
                st.html(f"""
                <div style="border:1.5px solid {border_color}; border-radius:12px;
                            padding:15px 15px 12px; background:{bg_color};
                            box-shadow:0 1px 6px rgba(0,0,0,0.07);
                            display:flex; flex-direction:column; min-height:210px;">

                    <!-- GR badge + discount value -->
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:11px;">
                        <span style="background:#D97706; color:white; font-size:0.58rem;
                                     font-weight:800; padding:2px 6px; border-radius:4px;
                                     letter-spacing:0.03em; flex-shrink:0;">Reward</span>
                        <span style="color:#1a56db; font-weight:800; font-size:1.05rem; flex:1;">
                            {disc_label}
                        </span>
                    </div>

                    <!-- Product info + category image -->
                    <div style="display:flex; gap:10px; align-items:flex-start; flex:1;">
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:700; font-size:0.9rem; color:#111827;
                                        margin-bottom:3px; line-height:1.35;
                                        overflow:hidden; display:-webkit-box;
                                        -webkit-line-clamp:2; -webkit-box-orient:vertical;">
                                {row['offer_dsc']}
                            </div>
                            <div style="font-size:0.78rem; color:#6B7280; margin-bottom:8px;">
                                {cat_nm}
                            </div>
                            <span style="color:#1a56db; font-size:0.78rem; cursor:pointer;">
                                Offer Details
                            </span>
                        </div>
                        <div style="flex-shrink:0; width:76px; height:76px; background:#F3F4F6;
                                    border-radius:8px; display:flex; align-items:center;
                                    justify-content:center; overflow:hidden;">
                            {icon}
                        </div>
                    </div>

                    <!-- Divider -->
                    <div style="border-top:1px solid #E5E7EB; margin:10px 0 8px;"></div>

                    <!-- Points cost + expiry -->
                    <div style="display:flex; justify-content:space-between; align-items:center; min-height:28px;">
                        <div>{pts_badge}{clipped_bottom}</div>
                        <div style="text-align:right; font-size:0.7rem; color:#9CA3AF; line-height:1.5;">
                            Single use<br/>{expiry_line}
                        </div>
                    </div>
                </div>
                """)
                if clipped:
                    st.button("Unclip", key=f"gr_unclip_{hid}_{offer_id}", use_container_width=True)
                else:
                    st.button(f"Use {tier:,} pts", key=f"gr_ranked_{hid}_{offer_id}",
                              use_container_width=True, type="primary",
                              on_click=clip_offer_local, args=(hid, offer_id, True, tier))


def render_clipped_offers(hid: str):
    st.subheader("My Clipped Offers")
    clipped = get_clipped(hid)

    if not clipped:
        st.info("You haven't clipped any offers yet. Go to **My Offers** to clip offers.")
        return

    seen_counts = {}
    for oid in clipped:
        seen_counts[oid] = seen_counts.get(oid, 0) + 1

    clipped_rows = []
    shown = set()
    for oid in clipped:
        if oid in shown:
            continue
        shown.add(oid)
        matches = scored_df[(scored_df["household_id"] == hid) & (scored_df["client_offer_id"] == oid)]
        if matches.empty:
            continue
        clipped_rows.append((oid, matches.iloc[0], seen_counts[oid]))

    st.success(f"**{len(clipped)} clip{'s' if len(clipped) > 1 else ''}** active — discounts will apply at checkout.")
    st.markdown("")

    for offer_id, row, count in clipped_rows:
        card_col, btn_col = st.columns([5, 1])
        with card_col:
            count_html = f'<span style="color:#856404; font-weight:700;"> &times;{count} clips</span>' if count > 1 else ""
            st.html(f"""
            <div class="offer-card" style="border-color:#1A7A5E; background:#F0FBF6;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <span style="color:#1A7A5E; font-weight:800;">&#9986;</span>&nbsp;&nbsp;
                        <span class="offer-name">{row['offer_dsc']}</span>
                        &nbsp;&nbsp;{channel_pill(row['delivery_channel_cd'])}
                        {count_html}
                    </div>
                    <div style="text-align:right;">
                        <span class="offer-discount">{format_discount(row['discount_value'], row['discount_type_cd'])}</span><br>
                        <span style="color:#888; font-size:0.8rem;">Score: <b>{row['score']}</b> / 100</span>
                    </div>
                </div>
                <div style="margin-top:8px; color:#1A7A5E; font-size:0.82rem; font-weight:600;">
                    Active &mdash; discount will apply at checkout
                </div>
            </div>
            """)
        with btn_col:
            st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
            if st.button("Unclip", key=f"unclip_clipped_{hid}_{offer_id}", width="stretch"):
                unclip_offer_local(hid, offer_id)
                st.rerun()


# ─── COMPARE CUSTOMERS ────────────────────────────────────────────────────────

def _customer_summary_html(hid: str) -> str:
    c = customers_df[customers_df["household_id"] == hid].iloc[0].to_dict()
    tier_html = tier_badge(c["clv_tier_level_id"])
    return f"""
    <div class="compare-card">
        <div style="margin-bottom:10px;">{tier_html}</div>
        <div class="metric-card"><div class="label">Points Balance</div>
            <div class="value">{c['current_point_balance']:,} pts</div></div>
        <div class="metric-card"><div class="label">Favourite Channel</div>
            <div class="value" style="font-size:1rem;">{c['fav_channel']}</div></div>
        <div class="metric-card"><div class="label">Days Since Last Txn</div>
            <div class="value">{c['days_since_last_txn']} days</div></div>
        <div class="metric-card"><div class="label">Age Group</div>
            <div class="value" style="font-size:1rem;">{c.get('customer_age', '—')}</div></div>
    </div>"""


def render_model_comparison(hid: str):
    st.subheader("Compare Models")
    st.caption("Same customer, same offers — ranked differently by each model.")

    meta = load_model_metadata()

    col_rb, col_std, col_gr = st.columns(3)

    # ─── RULE-BASED COLUMN ────
    with col_rb:
        st.html("""<div style="background:#F0F9FF; border:1px solid #BAE6FD;
                    border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <b>📋 Rule-Based Engine</b><br>
                    <span style="font-size:0.82rem; color:#555;">
                    5 manually-weighted rules. No learning from data.</span></div>""")

        rb_offers = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "rule_based")
        ].sort_values("rank")

        rb_rank = {row["client_offer_id"]: int(row["rank"])
                   for _, row in rb_offers.iterrows()}

        for _, row in rb_offers.iterrows():
            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:6px; border-radius:6px;
                        background:#F8FAFC; border:1px solid #E2E8F0;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#64748B; font-size:0.78rem; font-weight:700;">
                        #{int(row['rank'])}</span>
                    &nbsp;<span style="font-size:0.88rem;">{row['offer_dsc'][:20]}</span>
                </div>
                <span style="font-weight:700; color:{BLUE}; font-size:0.9rem;">
                    {row['score']:.1f}</span>
            </div>""")

    # ─── PROPENSITY STANDARD COLUMN ────
    with col_std:
        auc_txt = f"CV AUC: {meta.get('propensity_standard', {}).get('auc_cv', '—')}"
        st.html(f"""<div style="background:#EEF2FF; border:1px solid #C7D2FE;
                    border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <b>🤖 Propensity (Standard)</b><br>
                    <span style="font-size:0.82rem; color:#555;">
                    Trained on {meta.get('propensity_standard', {}).get('n_train','—')} offers. {auc_txt}.</span></div>""")

        std_offers = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "propensity")
        ].sort_values("rank")

        std_rank = {row["client_offer_id"]: int(row["rank"])
                    for _, row in std_offers.iterrows()}

        for _, row in std_offers.iterrows():
            oid = row["client_offer_id"]
            std_r = int(row["rank"])
            rb_r = rb_rank.get(oid)
            if rb_r is not None:
                delta = rb_r - std_r
                if delta > 0:
                    delta_html = f'<span style="color:#16A34A; font-size:0.75rem;">▲{delta}</span>'
                elif delta < 0:
                    delta_html = f'<span style="color:#DC2626; font-size:0.75rem;">▼{abs(delta)}</span>'
                else:
                    delta_html = '<span style="color:#94A3B8; font-size:0.75rem;">—</span>'
            else:
                delta_html = '<span style="color:#94A3B8; font-size:0.75rem;">new</span>'

            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:6px; border-radius:6px;
                        background:#F0F4FF; border:1px solid #D9E5FF;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#4F46E5; font-size:0.78rem; font-weight:700;">
                        #{std_r}</span>
                    &nbsp;<span style="font-size:0.88rem;">{row['offer_dsc'][:20]}</span>
                    &nbsp;{delta_html}
                </div>
                <span style="font-weight:700; color:#4F46E5; font-size:0.9rem;">
                    {row['score']:.1f}</span>
            </div>""")

    # ─── PROPENSITY GR COLUMN ────
    with col_gr:
        auc_txt_gr = f"CV AUC: {meta.get('propensity_gr', {}).get('auc_cv', '—')}"
        st.html(f"""<div style="background:#F0FDF4; border:1px solid #BBDBB5;
                    border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <b>🎯 Propensity (GR)</b><br>
                    <span style="font-size:0.82rem; color:#555;">
                    Trained on {meta.get('propensity_gr', {}).get('n_train','—')} offers. {auc_txt_gr}.</span></div>""")

        gr_offers = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "propensity_gr")
        ].sort_values("rank")

        gr_rank = {row["client_offer_id"]: int(row["rank"])
                   for _, row in gr_offers.iterrows()}

        for _, row in gr_offers.iterrows():
            oid = row["client_offer_id"]
            gr_r = int(row["rank"])
            rb_r = rb_rank.get(oid)
            if rb_r is not None:
                delta = rb_r - gr_r
                if delta > 0:
                    delta_html = f'<span style="color:#16A34A; font-size:0.75rem;">▲{delta}</span>'
                elif delta < 0:
                    delta_html = f'<span style="color:#DC2626; font-size:0.75rem;">▼{abs(delta)}</span>'
                else:
                    delta_html = '<span style="color:#94A3B8; font-size:0.75rem;">—</span>'
            else:
                delta_html = '<span style="color:#94A3B8; font-size:0.75rem;">new</span>'

            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:6px; border-radius:6px;
                        background:#FAFCE8; border:1px solid #D9E5A0;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#7C7016; font-size:0.78rem; font-weight:700;">
                        #{gr_r}</span>
                    &nbsp;<span style="font-size:0.88rem;">{row['offer_dsc'][:20]}</span>
                    &nbsp;{delta_html}
                </div>
                <span style="font-weight:700; color:#7C7016; font-size:0.9rem;">
                    {row['score']:.1f}</span>
            </div>""")

    # ─── FEATURE IMPORTANCE COMPARISON ────
    st.markdown("---")
    st.markdown("#### 🔍 Feature Importance — What Each Model Learned")
    
    fi_col1, fi_col2, fi_col3 = st.columns(3)
    
    with fi_col1:
        st.markdown("**📋 Rule-Based**")
        st.caption("No learning — rules are pre-defined by team")
    
    with fi_col2:
        st.markdown("**🤖 Propensity (Standard)**")
        if meta.get("propensity_standard", {}).get("top_features"):
            for feat, imp in meta["propensity_standard"]["top_features"][:5]:
                st.caption(f"• {feat.replace('_', ' ').title()}: {imp:.3f}")
    
    with fi_col3:
        st.markdown("**🎯 Propensity (GR)**")
        if meta.get("propensity_gr", {}).get("top_features"):
            for feat, imp in meta["propensity_gr"]["top_features"][:5]:
                st.caption(f"• {feat.replace('_', ' ').title()}: {imp:.3f}")

    st.markdown("---")
    st.caption(
        "▲ green = ranked higher vs rule-based &nbsp;|&nbsp;"
        "▼ red = ranked lower &nbsp;|&nbsp; — = same rank"
    )


def render_comparison(current_hid: str):
    st.subheader("Compare Customers")
    st.caption("Select two households to compare their profiles and personalised offers side by side.")

    cmp_options = customers_df.apply(
        lambda r: (r["household_id"], f"{r['full_name']}  ({r['household_id']})"), axis=1
    ).tolist()
    cmp_labels  = [l for _, l in cmp_options]
    cmp_hid_map = {l: h for h, l in cmp_options}
    cmp_label_map = {h: l for h, l in cmp_options}
    current_label = cmp_label_map.get(current_hid, cmp_labels[0])

    col1, col2 = st.columns(2)
    with col1:
        label_a = st.selectbox("Customer A", cmp_labels,
                               index=cmp_labels.index(current_label), key="compare_a")
    with col2:
        default_label_b = cmp_labels[1] if cmp_labels[0] == label_a else cmp_labels[0]
        label_b = st.selectbox("Customer B", cmp_labels,
                               index=cmp_labels.index(default_label_b), key="compare_b")

    hid_a = cmp_hid_map[label_a]
    hid_b = cmp_hid_map[label_b]

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.html(f'<div class="compare-header">{label_a}</div>')
        st.html(_customer_summary_html(hid_a))
    with col_b:
        st.html(f'<div class="compare-header">{label_b}</div>')
        st.html(_customer_summary_html(hid_b))

    st.markdown("#### Top 3 Personalised Offers")
    col_a, col_b = st.columns(2)

    for col, hid in [(col_a, hid_a), (col_b, hid_b)]:
        offers = scored_df[scored_df["household_id"] == hid].sort_values("score", ascending=False).head(3)
        with col:
            for rank, (_, row) in enumerate(offers.iterrows(), 1):
                st.html(f"""
                <div class="offer-card">
                    <div style="display:flex; justify-content:space-between;">
                        <span><span class="offer-rank">#{rank}</span>&nbsp;
                        <span class="offer-name">{row['offer_dsc']}</span>&nbsp;
                        {channel_pill(row['delivery_channel_cd'])}</span>
                        <span class="offer-discount">{format_discount(row['discount_value'], row['discount_type_cd'])}</span>
                    </div>
                    {score_bar(row['score'])}
                    <div style="font-size:0.78rem; color:#555; margin-top:4px;">
                        Score: <b>{row['score']}</b> / 100
                    </div>
                </div>
                """)

    st.markdown("#### Score Distribution")
    offers_a = scored_df[scored_df["household_id"] == hid_a][["offer_dsc", "score"]].set_index("offer_dsc").rename(columns={"score": hid_a})
    offers_b = scored_df[scored_df["household_id"] == hid_b][["offer_dsc", "score"]].set_index("offer_dsc").rename(columns={"score": hid_b})
    chart_df = offers_a.join(offers_b, how="inner").sort_values(hid_a, ascending=False).head(8)
    st.bar_chart(chart_df)


# ─── ALLOCATION CRITERIA ──────────────────────────────────────────────────────

SCORING_RULES = [
    {
        "title":   "Transaction Affinity",
        "weight":  "30%",
        "desc":    "Measures how much a customer has historically spent in the category this offer belongs to. A customer who regularly buys Produce gets a higher score for Produce offers.",
        "signals": ["Category spend history", "Transaction frequency", "c360_cat_affinity", "c360_txn_upc"],
    },
    {
        "title":   "Redemption Match",
        "weight":  "25%",
        "desc":    "Aligns the offer's delivery channel with the customer's preferred redemption channel. A Weekly Ad shopper scores higher on in-store offers; an app user scores higher on J4U digital offers.",
        "signals": ["fav_channel", "eng_mode_p6m", "delivery_channel_cd", "gas_rewards_ind_6m"],
    },
    {
        "title":   "Points Eligibility",
        "weight":  "20%",
        "desc":    "Rewards customers with a high points balance — they are more motivated to redeem point-based offers. Customers nearing expiry get an additional nudge.",
        "signals": ["current_point_balance", "points_expiring_next_month", "clv_tier_level_id"],
    },
    {
        "title":   "Cart & Browse Affinity",
        "weight":  "15%",
        "desc":    "Captures online engagement signals — DoorDash, Instacart, Uber usage. Customers who shop online are better candidates for J4U and Auto Clip delivery offers.",
        "signals": ["doordash_txn_ind_6m", "instacart_txn_ind_6m", "uber_txn_ind_6m", "eng_mode_p6m"],
    },
    {
        "title":   "Demographic Match",
        "weight":  "10%",
        "desc":    "Uses age group, household size, presence of children, and diet preferences to match offers that fit the customer's life stage. Baby product offers score higher for households with children.",
        "signals": ["customer_age", "household_size", "num_of_children", "diet_preference", "snap_customers"],
    },
]

MULTIPLIERS = [
    {
        "title":  "Recency Boost  ×1.2",
        "desc":   "Applied when a customer has shopped in the last 7 days. Recent shoppers are more likely to act on an offer immediately — their final score is boosted by 20%.",
        "field":  "days_since_last_txn ≤ 7",
    },
    {
        "title":  "Tier Multiplier  ×1.5",
        "desc":   "Applied to for U+ (4U+) members on exclusive offers. Premium members receive a 50% score boost on J4U-exclusive offers, rewarding loyalty and creating clear upgrade incentives.",
        "field":  "clv_tier_level_id = '4U+' AND is_appliable_to_j4u_ind = TRUE",
    },
]

BUSINESS_RULES = [
    {
        "title": "Score Cap — 100",
        "desc":  "All scores are capped at 100 regardless of boost stacking. This keeps the scale consistent and prevents a single customer-offer pair from dominating the ranking.",
    },
    {
        "title": "eCommerce Nudge",
        "desc":  "Fuel redeemers receive a partial channel match score on J4U digital offers (instead of a near-zero natural score). This intentionally surfaces online offers to offline loyalists — a migration strategy to gradually shift behaviour without forcing it.",
    },
    {
        "title": "Clipping Activation",
        "desc":  "An offer must be clipped by the customer before it activates at checkout. Clipping is a signal of intent — only clipped offers trigger discounts. Most offers can only be clipped once; Grocery Reward offers allow multiple clips.",
    },
    {
        "title": "FreshPass Targeting",
        "desc":  "Offers marked is_freshpass_offer_ind = TRUE are only surfaced to active FreshPass subscribers. These are typically delivery fee waivers, exclusive pickup discounts, or free delivery thresholds.",
    },
    {
        "title": "Offer Targeting Level",
        "desc":  "Offers operate at three levels of granularity: ITEM (specific UPCs), CATEGORY (any product in a department), or BASKET (whole-shop offers). Item-level matches get a higher affinity boost than category-level.",
    },
]


# ─── FEATURE WEIGHT STUDIO ────────────────────────────────────────────────────

# Propensity model — 19 features with business-friendly labels
# invert=True means higher raw value = worse for customer (score will be 1 - normalised)
# Standard propensity model — 16 features (no points; standard offers don't require points)
_PROPENSITY_FEATURES = [
    {"col": "category_affinity",  "label": "Category Affinity",          "group": "Personalisation", "invert": False},
    {"col": "channel_match",      "label": "Channel Preference Match",   "group": "Personalisation", "invert": False},
    {"col": "discount_value",     "label": "Offer Discount Value",       "group": "Offer Quality",   "invert": False},
    {"col": "redemption_rate",    "label": "Historical Redemption Rate", "group": "Offer Quality",   "invert": False},
    {"col": "days_until_expiry",  "label": "Days Until Offer Expires",   "group": "Offer Quality",   "invert": False},
    {"col": "is_4uplus",          "label": "for U+ Member",              "group": "Loyalty",         "invert": False},
    {"col": "days_since_last_txn","label": "Recency (days since visit)", "group": "Engagement",      "invert": True},
    {"col": "churn_risk",         "label": "Churn Risk Score",           "group": "Engagement",      "invert": True},
    {"col": "doordash",           "label": "DoorDash User",              "group": "Channels",        "invert": False},
    {"col": "instacart",          "label": "Instacart User",             "group": "Channels",        "invert": False},
    {"col": "uber",               "label": "Uber Eats User",             "group": "Channels",        "invert": False},
    {"col": "gas_rewards",        "label": "Gas Rewards User",           "group": "Channels",        "invert": False},
    {"col": "household_size",     "label": "Household Size",             "group": "Demographics",    "invert": False},
    {"col": "num_children",       "label": "Number of Children",         "group": "Demographics",    "invert": False},
    {"col": "is_j4u_exclusive",   "label": "for U+ Exclusive Offer",     "group": "Offer Fit",       "invert": False},
    {"col": "is_freshpass_offer",  "label": "FreshPass Exclusive",        "group": "Offer Fit",       "invert": False},
]

_GROUP_COLORS = {
    "Personalisation": "#00529B",
    "Offer Quality":   "#2E9E6B",
    "Loyalty":         "#F59E0B",
    "Engagement":      "#E31837",
    "Channels":        "#7C3AED",
    "Demographics":    "#0891B2",
    "Offer Fit":       "#64748B",
}


@st.cache_data(ttl=300)
def load_propensity_feature_matrix(hid: str) -> pd.DataFrame:
    """Return per-offer feature matrix + original propensity score for one household."""
    with _engine.connect() as conn:
        cust = pd.read_sql(text("""
            SELECT
                cp.household_id,
                cp.clv_tier_level_id,
                cp.current_point_balance,
                cp.points_expiring_next_month,
                cp.fav_channel,
                CASE WHEN cp.clv_tier_level_id = '4U+' THEN 1 ELSE 0 END  AS is_4uplus,
                COALESCE(cp.gas_rewards_ind_6m::int, 0)                    AS gas_rewards,
                COALESCE(cp.doordash_txn_ind_6m::int, 0)                   AS doordash,
                COALESCE(cp.instacart_txn_ind_6m::int, 0)                  AS instacart,
                COALESCE(cp.uber_txn_ind_6m::int, 0)                       AS uber,
                COALESCE(cp.household_size, 1)                             AS household_size,
                COALESCE(cp.num_of_children, 0)                            AS num_children,
                COALESCE(cp.churn_risk_score_nbr, 0.5)                     AS churn_risk,
                COALESCE((CURRENT_DATE - MAX(t.txn_dte))::int, 999)        AS days_since_last_txn
            FROM c360_customer_profile cp
            LEFT JOIN c360_txn t ON t.household_id = cp.household_id
            WHERE cp.household_id = :hid AND cp.head_household_ind = TRUE
            GROUP BY cp.household_id, cp.clv_tier_level_id, cp.current_point_balance,
                     cp.points_expiring_next_month, cp.fav_channel, cp.gas_rewards_ind_6m,
                     cp.doordash_txn_ind_6m, cp.instacart_txn_ind_6m, cp.uber_txn_ind_6m,
                     cp.household_size, cp.num_of_children, cp.churn_risk_score_nbr
        """), conn, params={"hid": hid})

        offers_raw = pd.read_sql(text("""
            SELECT
                so.client_offer_id,
                so.offer_dsc,
                so.score AS propensity_score,
                so.rank  AS propensity_rank,
                o.delivery_channel_cd,
                o.discount_value,
                o.tier_1_points_threshold,
                o.is_appliable_to_j4u_ind::int    AS is_j4u_exclusive,
                o.is_freshpass_offer_ind::int      AS is_freshpass_offer,
                (o.end_dt - CURRENT_DATE)::int     AS days_until_expiry,
                COALESCE(os.red_pct, 0)            AS redemption_rate,
                os.rep_category_nm                 AS category_nm
            FROM c360_scored_offers so
            JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
            LEFT JOIN c360_offer_summary os ON os.client_offer_id = so.client_offer_id
            WHERE so.household_id = :hid
              AND so.model_type = 'propensity'
              AND o.program_type != 'Grocery Reward'
        """), conn, params={"hid": hid})

        affinity = pd.read_sql(text("""
            SELECT category_nm, affinity_score AS category_affinity
            FROM c360_cat_affinity
            WHERE household_id = :hid
        """), conn, params={"hid": hid})

    if cust.empty or offers_raw.empty:
        return pd.DataFrame()

    c = cust.iloc[0].to_dict()
    df = offers_raw.copy()

    # Merge affinity
    df = df.merge(affinity, on="category_nm", how="left")
    df["category_affinity"] = df["category_affinity"].fillna(0)

    # Interaction features
    df["channel_match"] = (c["fav_channel"] == df["delivery_channel_cd"]).astype(int)
    df["points_gap"] = (c["current_point_balance"] - df["tier_1_points_threshold"].fillna(0)).clip(lower=0)

    # Broadcast customer features
    for col in ["current_point_balance", "points_expiring_next_month", "is_4uplus",
                "gas_rewards", "doordash", "instacart", "uber",
                "household_size", "num_children", "churn_risk", "days_since_last_txn"]:
        df[col] = c[col]

    df["discount_value"] = df["discount_value"].fillna(0)
    df["days_until_expiry"] = df["days_until_expiry"].fillna(30)

    return df


# Business-friendly labels + default weights (matching scoring.py WEIGHTS)
_STUDIO_FEATURES = [
    {
        "col":     "transaction_affinity",
        "label":   "Purchase History Match",
        "desc":    "How well this offer aligns with what the customer actually buys. Based on historical category affinity scores.",
        "default": 30,
        "color":   "#00529B",
    },
    {
        "col":     "redemption_match",
        "label":   "Channel Preference Match",
        "desc":    "Whether the offer's delivery channel (in-store, online, auto-clip) matches how the customer prefers to shop.",
        "default": 25,
        "color":   "#0073C4",
    },
    {
        "col":     "points_eligibility",
        "label":   "Points Balance Fit",
        "desc":    "How well the customer's current loyalty points balance positions them for this offer.",
        "default": 20,
        "color":   "#2E9E6B",
    },
    {
        "col":     "cart_affinity",
        "label":   "Online Shopping Affinity",
        "desc":    "Likelihood to engage based on the customer's history with DoorDash, Instacart, and Uber Eats delivery platforms.",
        "default": 15,
        "color":   "#F59E0B",
    },
    {
        "col":     "demographic_match",
        "label":   "Lifestyle & Demographics",
        "desc":    "Fit based on age group, household size, children, and dietary preferences.",
        "default": 10,
        "color":   "#E31837",
    },
]


def _render_ranking_comparison(merged: pd.DataFrame, orig_score_col: str,
                               custom_score_col: str, orig_rank_col: str,
                               custom_rank_col: str, orig_label: str, model_color: str):
    """Shared side-by-side ranking table used by both model tabs."""
    merged = merged.copy()
    merged["rank_delta"] = merged[orig_rank_col] - merged[custom_rank_col]

    header_l, header_r = st.columns(2)
    with header_l:
        st.html(f"""<div style="background:#F0F9FF; border:1px solid #BAE6FD; border-radius:8px;
                    padding:8px 14px; margin-bottom:8px; font-size:0.85rem;">
                    <b>{orig_label}</b> &nbsp;(default weights)</div>""")
    with header_r:
        st.html("""<div style="background:#F0FFF4; border:1px solid #BBF7D0; border-radius:8px;
                    padding:8px 14px; margin-bottom:8px; font-size:0.85rem;">
                    <b>🎛️ Custom Ranking</b> &nbsp;(your weights)</div>""")

    for _, row in merged.sort_values(custom_rank_col).iterrows():
        delta = int(row["rank_delta"])
        if delta > 0:
            delta_html = f'<span style="color:#16A34A; font-weight:700;">▲{delta}</span>'
        elif delta < 0:
            delta_html = f'<span style="color:#DC2626; font-weight:700;">▼{abs(delta)}</span>'
        else:
            delta_html = '<span style="color:#94A3B8;">—</span>'

        orig_bar = min(int(row[orig_score_col]), 100)
        cust_bar = min(int(row[custom_score_col]), 100)

        col_l, col_r = st.columns(2)
        with col_l:
            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:5px; border-radius:6px;
                        background:#F8FAFC; border:1px solid #E2E8F0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="color:#64748B; font-size:0.78rem; font-weight:700;">#{int(row[orig_rank_col])}</span>
                        &nbsp;<span style="font-size:0.85rem;">{row['offer_dsc']}</span>
                    </div>
                    <span style="font-size:0.8rem; font-weight:700; color:{model_color};">{orig_bar:.0f}</span>
                </div>
                <div style="background:#EEF2F7; border-radius:3px; height:4px; margin-top:5px;">
                    <div style="width:{orig_bar}%; height:4px; border-radius:3px; background:{model_color};"></div>
                </div>
            </div>""")
        with col_r:
            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:5px; border-radius:6px;
                        background:#F0FFF4; border:1px solid #BBF7D0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="color:#15803D; font-size:0.78rem; font-weight:700;">#{int(row[custom_rank_col])}</span>
                        &nbsp;{delta_html}
                        &nbsp;<span style="font-size:0.85rem;">{row['offer_dsc']}</span>
                    </div>
                    <span style="font-size:0.8rem; font-weight:700; color:#15803D;">{cust_bar:.0f}</span>
                </div>
                <div style="background:#DCFCE7; border-radius:3px; height:4px; margin-top:5px;">
                    <div style="width:{cust_bar}%; height:4px; border-radius:3px; background:#16A34A;"></div>
                </div>
            </div>""")


def render_weight_studio(hid: str):
    st.subheader("Feature Weight Studio")
    st.caption("Adjust how much each factor influences the offer ranking. Changes are session-only — they don't affect the live scoring engine.")

    tab_rb, tab_ml = st.tabs(["📋 Rule-Based (5 features)", "🤖 Propensity / XGBoost (19 features)"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — RULE-BASED
    # ══════════════════════════════════════════════════════════════════════════
    with tab_rb:
        st.caption("The rule-based engine uses 5 manually-weighted scoring components. Adjust their relative importance below.")

        # initialise weights
        for feat in _STUDIO_FEATURES:
            if f"ws_{feat['col']}" not in st.session_state:
                st.session_state[f"ws_{feat['col']}"] = 100

        st.html("""<div style="font-size:0.8rem; color:#888; margin-bottom:8px;">
            0% = ignore &nbsp;|&nbsp; 100% = default &nbsp;|&nbsp; 200% = double importance</div>""")

        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3, col1, col2]
        for i, feat in enumerate(_STUDIO_FEATURES):
            with cols[i]:
                pct = st.slider(
                    feat["label"],
                    min_value=0, max_value=200, step=5,
                    value=st.session_state[f"ws_{feat['col']}"],
                    key=f"ws_slider_{feat['col']}",
                    help=feat["desc"],
                )
                st.session_state[f"ws_{feat['col']}"] = pct
                effective_w = round(feat["default"] * pct / 100, 1)
                bar_pct = min(int(pct / 2), 100)
                st.html(f"""<div style="font-size:0.75rem; color:#555; margin-top:-8px; margin-bottom:4px;">
                    Effective: <b style="color:{feat['color']};">{effective_w}%</b>
                    <div style="background:#EEF2F7; border-radius:3px; height:4px; margin-top:3px;">
                        <div style="width:{bar_pct}%; height:4px; border-radius:3px; background:{feat['color']};"></div>
                    </div></div>""")

        _, reset_col = st.columns([4, 1])
        with reset_col:
            if st.button("Reset", key="ws_rb_reset", use_container_width=True):
                for feat in _STUDIO_FEATURES:
                    st.session_state[f"ws_{feat['col']}"] = 100
                st.rerun()

        # compute
        cust_rb = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "rule_based") &
            (scored_df["program_type"] != "Grocery Reward")
        ].copy()

        if cust_rb.empty:
            st.info("No rule-based scores for this customer.")
        else:
            custom_score = sum(
                cust_rb[f["col"]] * (f["default"] * st.session_state[f"ws_{f['col']}"] / 100)
                for f in _STUDIO_FEATURES
            )
            cust_rb["custom_score"] = custom_score
            cust_rb.loc[cust_rb["recency_boost_applied"] == True, "custom_score"] *= 1.2
            cust_rb.loc[cust_rb["tier_multiplier_applied"] == True, "custom_score"] *= 1.5
            cust_rb["custom_score"] = cust_rb["custom_score"].clip(upper=100)
            cust_rb = cust_rb.sort_values("custom_score", ascending=False).reset_index(drop=True)
            cust_rb["custom_rank"] = cust_rb.index + 1

            orig = scored_df[
                (scored_df["household_id"] == hid) &
                (scored_df["model_type"] == "rule_based") &
                (scored_df["program_type"] != "Grocery Reward")
            ][["client_offer_id", "rank", "score"]].sort_values("rank").reset_index(drop=True)
            # Re-rank within standard-only subset so orig_rank is 1,2,3... not absolute position
            orig["orig_rank"] = orig.index + 1
            orig = orig.rename(columns={"score": "orig_score"}).drop(columns=["rank"])
            merged = cust_rb.merge(orig, on="client_offer_id")

            st.html('<div class="section-heading" style="margin-top:20px;">Ranking Comparison</div>')
            _render_ranking_comparison(merged, "orig_score", "custom_score",
                                       "orig_rank", "custom_rank",
                                       "📋 Original Ranking", "#00529B")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — PROPENSITY
    # ══════════════════════════════════════════════════════════════════════════
    with tab_ml:
        st.caption("The XGBoost model uses 19 raw features. Here each feature contributes proportionally to a custom linear score — letting you explore what the model would rank differently if each signal were amplified or suppressed.")

        feat_matrix = load_propensity_feature_matrix(hid)
        if feat_matrix.empty:
            st.info("No propensity scores for this customer.")
        else:
            # initialise weights
            for feat in _PROPENSITY_FEATURES:
                if f"ws_ml_{feat['col']}" not in st.session_state:
                    st.session_state[f"ws_ml_{feat['col']}"] = 100

            st.html("""<div style="font-size:0.8rem; color:#888; margin-bottom:8px;">
                0% = ignore &nbsp;|&nbsp; 100% = equal weight &nbsp;|&nbsp; 200% = double importance
                &nbsp;&nbsp;<i>(features marked ↓ are inverted — lower raw value is better)</i></div>""")

            # group sliders by group label
            groups = {}
            for feat in _PROPENSITY_FEATURES:
                groups.setdefault(feat["group"], []).append(feat)

            for group_name, feats in groups.items():
                color = _GROUP_COLORS.get(group_name, "#64748B")
                st.html(f'<div style="font-size:0.8rem; font-weight:700; color:{color}; '
                        f'margin-top:12px; margin-bottom:4px; border-left:3px solid {color}; '
                        f'padding-left:8px;">{group_name}</div>')
                cols_ml = st.columns(min(len(feats), 4))
                for i, feat in enumerate(feats):
                    with cols_ml[i % 4]:
                        label = feat["label"] + (" ↓" if feat["invert"] else "")
                        pct = st.slider(
                            label,
                            min_value=0, max_value=200, step=5,
                            value=st.session_state[f"ws_ml_{feat['col']}"],
                            key=f"ws_ml_slider_{feat['col']}",
                        )
                        st.session_state[f"ws_ml_{feat['col']}"] = pct

            _, reset_col_ml = st.columns([4, 1])
            with reset_col_ml:
                if st.button("Reset", key="ws_ml_reset", use_container_width=True):
                    for feat in _PROPENSITY_FEATURES:
                        st.session_state[f"ws_ml_{feat['col']}"] = 100
                    st.rerun()

            # normalise features and compute custom score
            fm = feat_matrix.copy()
            custom_score = pd.Series(0.0, index=fm.index)
            for feat in _PROPENSITY_FEATURES:
                col = feat["col"]
                col_min, col_max = fm[col].min(), fm[col].max()
                if col_max > col_min:
                    norm = (fm[col] - col_min) / (col_max - col_min)
                else:
                    norm = pd.Series(0.5, index=fm.index)
                if feat["invert"]:
                    norm = 1.0 - norm
                weight = st.session_state[f"ws_ml_{feat['col']}"] / 100.0
                custom_score += norm * weight

            fm["custom_score_raw"] = custom_score
            # scale to 0–100 for display
            s_min, s_max = custom_score.min(), custom_score.max()
            if s_max > s_min:
                fm["custom_score"] = (custom_score - s_min) / (s_max - s_min) * 100
            else:
                fm["custom_score"] = 50.0

            fm = fm.sort_values("custom_score", ascending=False).reset_index(drop=True)
            fm["custom_rank"] = fm.index + 1
            # scale original propensity score 0-100 for display
            p_min, p_max = fm["propensity_score"].min(), fm["propensity_score"].max()
            if p_max > p_min:
                fm["orig_score_disp"] = (fm["propensity_score"] - p_min) / (p_max - p_min) * 100
            else:
                fm["orig_score_disp"] = 50.0

            st.html('<div class="section-heading" style="margin-top:20px;">Ranking Comparison</div>')
            _render_ranking_comparison(fm, "orig_score_disp", "custom_score",
                                       "propensity_rank", "custom_rank",
                                       "🤖 Original XGBoost Ranking", "#7C3AED")


def render_allocation_criteria():
    st.subheader("How Offers Are Scored")
    st.caption("Every customer-offer pair is scored using a weighted combination of 5 rules, then boosted by multipliers and filtered through business rules.")

    st.html('<div class="section-heading">Scoring Rules — Weighted Sum (0–100)</div>')

    weight_values = [30, 25, 20, 15, 10]
    for rule, w in zip(SCORING_RULES, weight_values):
        signals_html = "".join(f"<span>{s}</span>" for s in rule["signals"])
        bar_pct = w * 2
        st.html(f"""
        <div class="criteria-card">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:6px;">
                <span class="criteria-weight">{rule['weight']}</span>
                <span class="criteria-title">{rule['title']}</span>
            </div>
            <div style="background:#EEF2F7; border-radius:4px; height:6px; margin-bottom:10px;">
                <div style="width:{bar_pct}%; height:6px; border-radius:4px; background:linear-gradient(90deg,#00529B,#E31837);"></div>
            </div>
            <div class="criteria-desc">{rule['desc']}</div>
            <div class="criteria-signals">Data signals: {signals_html}</div>
        </div>
        """)

    st.html('<div class="section-heading">Multipliers — Applied After Weighted Sum</div>')

    for m in MULTIPLIERS:
        st.html(f"""
        <div class="multiplier-card">
            <div style="font-weight:700; color:#E31837; font-size:0.95rem; margin-bottom:4px;">{m['title']}</div>
            <div style="font-size:0.88rem; color:#555; line-height:1.5;">{m['desc']}</div>
            <div style="margin-top:6px; font-size:0.78rem; color:#888;">Condition: <code>{m['field']}</code></div>
        </div>
        """)

    st.html('<div class="section-heading">Business Rules</div>')

    for rule in BUSINESS_RULES:
        st.html(f"""
        <div class="rule-card">
            <div style="font-weight:700; color:#856404; font-size:0.95rem; margin-bottom:4px;">{rule['title']}</div>
            <div style="font-size:0.88rem; color:#555; line-height:1.5;">{rule['desc']}</div>
        </div>
        """)

    st.markdown("---")
    st.markdown("#### Final Score Formula")
    st.code(
        "weighted_sum = (\n"
        "    0.30 × transaction_affinity +\n"
        "    0.25 × redemption_match     +\n"
        "    0.20 × points_eligibility   +\n"
        "    0.15 × cart_affinity        +\n"
        "    0.10 × demographic_match\n"
        ") × 100\n\n"
        "score = min(weighted_sum × recency_boost × tier_multiplier, 100)",
        language="python"
    )


# ─── DEMO SCRIPT ─────────────────────────────────────────────────────────────

DEMO_STEPS = [
    {
        "tag": "Step 1 of 8",
        "title": "The Problem Landscape",
        "narration": (
            "Every Albertsons customer faces similar friction: 500+ offers with minimal personalization. "
            "Loyal Produce shoppers see Bakery promos. for U+ members feel no tier advantage. "
            "Points expire unnoticed. The business uses scripts to rank the offers every week/month. There is no centralized Engine that learns based on customer redemption pattern. "
            "But the data to solve this already exists in C360. We're about to show you how to use it."
        ),
        "talking_points": [
            "Customer pain: 500+ offers, no relevance signal, expiring points unnoticed, tier feels invisible",
            "Business pain: ~30% points breakage liability, manual weekly ranking, no redemption insight",
            "Solution: Use existing C360 data — transaction history, affinity, points, churn — to rank offers per household",
        ],
        "customer": None,
        "highlight": "before",
        "nav_page": "Problem Exploration",
        "persona": "both",
    },
    {
        "tag": "Step 2 of 8",
        "title": "Today — 500+ Offers, Some Personalization",
        "narration": (
            "This is what every Albertsons customer sees today. "
            "The same catalog — with a ranking the business curates manually. "
            "A Produce loyalist and a Meat shopper see the same offers in the same order. "
            "The data to personalise this already exists in C360. It's just not being used yet."
        ),
        "talking_points": [
            "527 offers clipped — customers are overwhelmed, not guided",
            "Ranking is curated by the business using scripts - Simple personalization of ordering offers.",
            "C360 already has transaction history, category affinity, points balance — unused for ranking",
        ],
        "customer": None,
        "highlight": "before",
        "nav_page": "Demo Script",
        "persona": "business",
    },
    {
        "tag": "Step 3 of 8",
        "title": "The Problem — And Why C360 Already Has the Answer",
        "narration": (
            "Today, every Albertsons customer gets the same weekly offer email — "
            "a Fuel loyalist gets the same Bakery coupon as a Produce shopper. "
            "The data to do better already exists: Albertsons C360 has transaction history, "
            "channel preferences, points balances, churn scores, and redemption patterns "
            "for every household. SmartOfferEngine turns that data into personalised, ranked offers."
        ),
        "talking_points": [
            "Built on 18 real Albertsons C360 tables — zero new data sources required",
            "Scores every customer-offer pair individually, not at segment level",
            "Adds one new asset to C360: c360_scored_offers — a ranked offer table per household",
        ],
        "customer": None,
        "highlight": "stats",
        "nav_page": "Segment Explorer",
        "persona": "business",
    },
    {
        "tag": "Step 4 of 8",
        "title": "Same Catalog. Completely Different Rankings.",
        "narration": (
            "Here's personalisation in action. Two households, same 64-offer catalog — "
            "completely different ranked results. "
            "A Fuel redeemer sees digital offers nudged to the top to encourage eCommerce migration. "
            "A for U+ subscriber sees exclusive offers boosted by a 1.5× tier multiplier. "
            "The ranking comes entirely from C360 signals: channel preference, category affinity, "
            "points balance, redemption history."
        ),
        "talking_points": [
            "C360 signals used: fav_channel, cat_affinity, current_point_balance, clv_tier_level_id",
            "Fuel redeemers get a deliberate J4U nudge — migrate to digital without disrupting their habit",
            "for U+ members see exclusive offers unavailable to Standard tier — visible reward for loyalty",
        ],
        "customer": "both",
        "highlight": "compare",
        "nav_page": "Compare Customers",
        "persona": "business",
    },
    {
        "tag": "Step 5 of 8",
        "title": "The AI Layer — What the Rules Miss",
        "narration": (
            "On top of the rule-based engine, we trained an XGBoost model on C360 redemption history. "
            "It learns which signals actually predict whether a customer redeems — not just clips. "
            "The rank-change deltas show where the AI and the rules disagree. "
            "Those disagreements are where machine learning adds the most value: "
            "signals the rules don't capture, interactions too complex to hand-tune."
        ),
        "talking_points": [
            "Training data: c360_redemptions (positive) vs c360_clips without redemption (negative)",
            "Top signal discovered by XGBoost: channel_match — validates the rule-based weight",
            "CV AUC 0.626 on synthetic data — will improve significantly on real C360 redemption volume",
        ],
        "customer": "premium",
        "highlight": "compare_models",
        "nav_page": "Compare Models",
        "persona": "business",
    },
    {
        "tag": "Step 6 of 8",
        "title": "Rules vs AI — Where It Makes a Real Difference",
        "narration": (
            "Here's where the AI earns its place. Two real customers, same offer catalog. "
            "The rule-based engine ranks by channel fit and discount size — it doesn't know "
            "Jessica is Vegan or that Stephanie is an Organic shopper. "
            "The AI learned those patterns from purchase history, and ranks completely differently as a result. "
            "These aren't edge cases. This is every customer, every week."
        ),
        "talking_points": [
            "Rules rank by offer mechanics — channel match, discount size, points balance",
            "AI ranks by what this customer will actually redeem — learned from their history",
            "The diff is the value: offers the customer actually wants, not offers the business thinks they want",
        ],
        "customer": None,
        "highlight": "model_story",
        "nav_page": "Compare Models",
        "persona": "business",
    },
    {
        "tag": "Step 7 of 8",
        "title": "What This Unlocks for Albertsons",
        "narration": (
            "SmartOfferEngine adds one new table to C360 — c360_scored_offers. "
            "That single table becomes a shared asset across the business: "
            "the app reads it to surface personalised offers, analytics reads it to measure redemption lift, "
            "marketing reads it to plan targeted campaigns, and ML reads it to monitor model drift. "
            "No new data. No new infrastructure today. Just the C360 investment finally being fully used."
        ),
        "talking_points": [
            "15–30% redemption lift from personalised vs generic offers (industry benchmark)",
            "Points expiry surfacing reduces breakage liability and drives incremental basket visits",
            "One pipeline. One new C360 table. Every team — app, analytics, marketing, ML — benefits",
        ],
        "customer": None,
        "highlight": "so_what",
        "nav_page": "Demo Script",
        "persona": "business",
    },
    {
        "tag": "Step 8 of 8",
        "title": "The Roadmap — What's Next",
        "narration": (
            "Phase 4 will upgrade the ML models with production C360 data and real redemption signals. "
            "We'll move from synthetic to real customer behavior to train on actual patterns. "
            "Real-time scoring will enable offers to update as customer points balance and preferences shift. "
            "Finally, automated A/B testing will measure which algorithm variant drives the most redemption lift. "
            "The foundation is ready. The next phase scales it to production volume and validates ROI at Albertsons scale."
        ),
        "talking_points": [
            "Phase 4: Retrain on production C360 data — CV AUC currently 0.626 will improve significantly",
            "Real-time scoring — offers refresh hourly as customer signals change (points balance, recency)",
            "A/B test rule-based vs propensity models — measure actual redemption and ROI lift with real traffic",
        ],
        "customer": None,
        "highlight": "roadmap",
        "nav_page": "Demo Script",
        "persona": "business",
    },
]

if "demo_step" not in st.session_state:
    st.session_state.demo_step = 0
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "My Offers"
if "demo_panel_open" not in st.session_state:
    st.session_state.demo_panel_open = True


_ANALYST_PAGES = {
    "Segment Explorer", "Compare Customers", "Compare Models",
    "Feature Weight Studio", "Feature Engineer", "How Offers Are Scored", "Demo Script",
}


def render_demo_panel():
    """Right-side presenter panel: talking points + Prev/Next navigation."""
    step_idx = st.session_state.demo_step
    step     = DEMO_STEPS[step_idx]
    total    = len(DEMO_STEPS)

    # Step dots
    dots = "".join(
        f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
        f'background:{"#FFD700" if i == step_idx else "rgba(255,255,255,0.3)"};'
        f'margin:0 3px;"></span>'
        for i in range(total)
    )

    # Talking points
    points_html = "".join(
        f'<li style="margin-bottom:10px; line-height:1.5;">{p}</li>'
        for p in step.get("talking_points", [])
    )

    nav_page = step.get("nav_page", "")
    nav_badge = (
        f'<div style="background:rgba(255,255,255,0.15); border-radius:8px; '
        f'padding:6px 10px; font-size:0.78rem; color:#A8D8FF; margin-top:14px;">'
        f'📍 {nav_page}</div>'
    ) if nav_page else ""

    # Collapse button — top right, before the panel
    _, hide_col = st.columns([5.5, 0.5])
    with hide_col:
        if st.button("◀", help="Collapse presenter panel", use_container_width=True, key="hide_panel"):
            st.session_state.demo_panel_open = False
            st.rerun()

    st.html(f"""
    <div style="background:linear-gradient(160deg,#00529B,#003870); border-radius:14px;
                padding:12px 16px 18px 16px; color:white; font-family:sans-serif; min-height:600px;
                display:flex; flex-direction:column; gap:4px; margin-top:-4px;">

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
            <span style="background:#E31837; color:white; font-size:0.68rem; font-weight:700;
                         padding:3px 8px; border-radius:99px; letter-spacing:0.06em;">
                🎬 PRESENTING
            </span>
            <span style="font-size:0.78rem; color:rgba(255,255,255,0.6);">
                {step_idx + 1} / {total}
            </span>
        </div>

        <div style="margin-bottom:2px;">{dots}</div>

        <div style="font-size:0.72rem; color:#A8D8FF; font-weight:600; letter-spacing:0.04em;
                    text-transform:uppercase; margin-top:6px;">
            {step.get("tag", "")}
        </div>

        <div style="font-size:1.0rem; font-weight:700; line-height:1.3; margin-bottom:4px;
                    word-wrap:break-word; overflow-wrap:break-word;">
            {step["title"]}
        </div>

        <div style="font-size:0.82rem; color:rgba(255,255,255,0.8); line-height:1.55;
                    border-left:3px solid rgba(255,255,255,0.2); padding-left:10px; margin-bottom:6px;
                    word-wrap:break-word; overflow-wrap:break-word;">
            {step["narration"]}
        </div>

        <ul style="font-size:0.80rem; color:rgba(255,255,255,0.9); padding-left:16px;
                   margin:0; flex:1;">
            {points_html}
        </ul>

        {nav_badge}

        <!-- Tech stack -->
        <div style="margin-top:16px; border-top:1px solid rgba(255,255,255,0.15); padding-top:12px;">
            <div style="font-size:0.68rem; color:rgba(255,255,255,0.45); text-transform:uppercase;
                        letter-spacing:0.06em; margin-bottom:8px;">Built with</div>
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    🐍 Python
                </span>
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    ⚡ FastAPI
                </span>
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    🎈 Streamlit
                </span>
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    🤖 XGBoost
                </span>
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    🐘 PostgreSQL
                </span>
                <span style="background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
                             border-radius:6px; padding:3px 8px; font-size:0.72rem; color:#E0F0FF;">
                    ☁️ C360 Schema
                </span>
            </div>
        </div>

    </div>
    """)

    # Prev / Next buttons
    st.markdown("")
    prev_col, next_col = st.columns(2)
    with prev_col:
        prev_disabled = step_idx == 0
        if st.button("← Back", use_container_width=True, disabled=prev_disabled):
            st.session_state.demo_step -= 1
            prev_step = DEMO_STEPS[st.session_state.demo_step]
            st.session_state.nav_page = prev_step.get("nav_page", st.session_state.nav_page)
            st.session_state.persona  = prev_step.get("persona", st.session_state.persona)
            st.rerun()
    with next_col:
        if step_idx < total - 1:
            if st.button("Next →", use_container_width=True, type="primary"):
                st.session_state.demo_step += 1
                next_step = DEMO_STEPS[st.session_state.demo_step]
                st.session_state.nav_page = next_step.get("nav_page", st.session_state.nav_page)
                st.session_state.persona  = next_step.get("persona", st.session_state.persona)
                st.rerun()
        else:
            if st.button("↺ Restart", use_container_width=True, type="primary"):
                st.session_state.demo_step = 0
                first_step = DEMO_STEPS[0]
                st.session_state.nav_page = first_step.get("nav_page", "Demo Script")
                st.session_state.persona  = first_step.get("persona", "business")
                st.rerun()


def render_demo_script():
    """Demo Script page.
    In demo_mode=True: only renders the visual content for the current step
                       (talking points live in the right panel).
    In demo_mode=False: renders the full script with narration, talking points, and nav.
    """
    step_idx  = st.session_state.demo_step
    step      = DEMO_STEPS[step_idx]
    total     = len(DEMO_STEPS)
    demo_mode = st.session_state.get("demo_mode", False)

    if not demo_mode:
        # ── Full script view (non-presentation) ─────────────────────────────
        st.progress((step_idx) / (total - 1) if total > 1 else 1.0)

        step_labels = [f"{i+1}. {s['title']}" for i, s in enumerate(DEMO_STEPS)]
        chosen = st.selectbox("Jump to step", step_labels, index=step_idx,
                              label_visibility="collapsed")
        chosen_idx = step_labels.index(chosen)
        if chosen_idx != step_idx:
            st.session_state.demo_step = chosen_idx
            st.rerun()

        st.markdown("")

        points_html = "".join(
            f'<li style="margin-bottom:6px;">{p}</li>'
            for p in step.get("talking_points", [])
        )
        st.html(f"""
        <div class="demo-step">
            <div class="step-tag">Step {step_idx + 1} of {total} &nbsp;·&nbsp; {step['tag']}</div>
            <h3 style="margin:8px 0 12px;">{step['title']}</h3>
            <p style="line-height:1.7; color:#D0E8FF;">{step['narration']}</p>
            <ul style="margin-top:14px; padding-left:18px; color:rgba(255,255,255,0.9);
                       line-height:1.6; font-size:0.88rem;">
                {points_html}
            </ul>
        </div>
        """)

        prev_col, _, next_col = st.columns([1, 4, 1])
        with prev_col:
            if step_idx > 0:
                if st.button("← Previous"):
                    st.session_state.demo_step -= 1
                    st.rerun()
        with next_col:
            if step_idx < total - 1:
                if st.button("Next →", type="primary"):
                    st.session_state.demo_step += 1
                    st.rerun()
            else:
                if st.button("Restart", type="primary"):
                    st.session_state.demo_step = 0
                    st.rerun()

        st.markdown("---")

    # ── Visual content for current step ─────────────────────────────────────
    # (rendered in both demo_mode and full script mode)
    fuel_rows    = customers_df[customers_df["gas_rewards_ind_6m"] == True]
    premium_rows = customers_df[customers_df["clv_tier_level_id"] == "4U+"]
    gr_rows      = customers_df[customers_df["current_point_balance"] >= 1000].sort_values(
                       "current_point_balance", ascending=False)
    churn_rows   = customers_df[customers_df["churn_segment_cd"] == "High Risk"]

    fuel_cust    = fuel_rows.iloc[0].to_dict()    if not fuel_rows.empty    else customers_df.iloc[0].to_dict()
    premium_cust = premium_rows.iloc[0].to_dict() if not premium_rows.empty else customers_df.iloc[1].to_dict()
    gr_cust      = gr_rows.iloc[0].to_dict()      if not gr_rows.empty      else customers_df.iloc[2].to_dict()
    churn_cust   = churn_rows.iloc[0].to_dict()   if not churn_rows.empty   else customers_df.iloc[3].to_dict()

    highlight = step["highlight"]
    customer  = step["customer"]

    cust_map = {
        "fuel":    fuel_cust,
        "premium": premium_cust,
        "gr":      gr_cust,
        "churn":   churn_cust,
    }
    cust = cust_map.get(customer)

    # ── Highlight renderers ─────────────────────────────────────────────────
    if highlight == "before":
        screenshot_path = os.path.join(os.path.dirname(__file__), "assets", "prod_screenshot.png")
        webview_path = os.path.join(os.path.dirname(__file__), "assets", "webView.jpg")
        
        st.html("""
        <div style="background:#FEF2F2; border:2px solid #FECACA; border-radius:10px;
                    padding:10px 16px; margin-bottom:12px; display:flex; align-items:center; gap:10px;">
            <span style="font-size:1.3rem;">⚠️</span>
            <span style="font-weight:600; color:#991B1B; font-size:0.92rem;">
                Current State — Albertsons for U Today (App & Web)
            </span>
        </div>
        """)
        
        col_app, col_web = st.columns(2, gap="medium")
        
        with col_app:
            st.subheader("📱 App View", divider=False)
            if os.path.exists(screenshot_path):
                img_app = Image.open(screenshot_path)
                # Resize to target height of 500px while maintaining aspect ratio
                target_height = 500
                ratio = target_height / img_app.height
                new_width = int(img_app.width * ratio)
                img_app_resized = img_app.resize((new_width, target_height), Image.Resampling.LANCZOS)
                st.image(img_app_resized, width=new_width)
            else:
                st.warning("App screenshot not found")
        
        with col_web:
            st.subheader("🖥️ Web View", divider=False)
            if os.path.exists(webview_path):
                img_web = Image.open(webview_path)
                # Resize to same target height of 500px to match app view
                target_height = 500
                ratio = target_height / img_web.height
                new_width = int(img_web.width * ratio)
                img_web_resized = img_web.resize((new_width, target_height), Image.Resampling.LANCZOS)
                st.image(img_web_resized, width=new_width)
            else:
                st.warning("Web view image not found at files/assets/webView.jpg")
        
        st.html("""
        <div style="text-align:center; color:#9CA3AF; font-size:0.78rem; margin-top:8px;">
            500+ offers in both views · Same list for every customer · Scripted ranking, not centralized
        </div>
        """)

    elif highlight == "criteria":
        render_allocation_criteria()

    elif highlight == "stats":
        fuel_count    = int(customers_df["gas_rewards_ind_6m"].sum())
        premium_count = len(customers_df[customers_df["clv_tier_level_id"] == "4U+"])
        high_pts      = len(customers_df[customers_df["current_point_balance"] >= 1000])
        churn_count   = len(customers_df[customers_df["churn_segment_cd"] == "High Risk"])
        model_count   = scored_df["model_type"].nunique()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Households",    f"{len(customers_df):,}")
        c2.metric("Offers in Catalog",   f"{len(offers_df)}")
        c3.metric("for U+ Subscribers",  f"{premium_count}")
        c4.metric("High Churn Risk",      f"{churn_count}")
        c5.metric("Scoring Models",       f"{model_count}")
        st.markdown("")
        c6, c7, c8 = st.columns(3)
        c6.metric("Fuel Redeemers",      f"{fuel_count}")
        c7.metric("High Points (1000+)", f"{high_pts}")
        c8.metric("Scored Pairs",        f"{len(scored_df):,}")

    elif highlight == "profile":
        render_profile(cust)

    elif highlight == "offers":
        render_offers(cust, cust["household_id"])

    elif highlight == "rewards":
        render_rewards(cust, cust["household_id"])

    elif highlight == "compare_models":
        render_model_comparison(cust["household_id"])

    elif highlight == "compare":
        hid_a = fuel_cust["household_id"]
        hid_b = premium_cust["household_id"]
        name_a = f"{fuel_cust.get('full_name', hid_a)}"
        name_b = f"{premium_cust.get('full_name', hid_b)}"

        col_a, col_b = st.columns(2)
        with col_a:
            st.html(f'<div class="compare-header">⛽ {name_a} — Fuel Redeemer</div>')
            st.html(_customer_summary_html(hid_a))
        with col_b:
            st.html(f'<div class="compare-header">★ {name_b} — for U+ Subscriber</div>')
            st.html(_customer_summary_html(hid_b))

        st.markdown("#### Their Top 3 Offers")
        col_a, col_b = st.columns(2)
        for col, hid in [(col_a, hid_a), (col_b, hid_b)]:
            offers = scored_df[scored_df["household_id"] == hid].sort_values("score", ascending=False).head(3)
            with col:
                for rank, (_, row) in enumerate(offers.iterrows(), 1):
                    boosts = []
                    if row["tier_multiplier_applied"]:
                        boosts.append("★ for U+ Boost")
                    if row["recency_boost_applied"]:
                        boosts.append("⚡ Recency")
                    boost_html = " ".join(
                        [f'<span style="color:{RED}; font-size:0.75rem; font-weight:700;">{b}</span>' for b in boosts]
                    )
                    st.html(f"""
                    <div class="offer-card">
                        <div style="display:flex; justify-content:space-between;">
                            <span><span class="offer-rank">#{rank}</span>&nbsp;
                            <span class="offer-name">{row['offer_dsc']}</span></span>
                            <span class="offer-discount">{format_discount(row['discount_value'], row['discount_type_cd'])}</span>
                        </div>
                        <div>{channel_pill(row['delivery_channel_cd'])} {boost_html}</div>
                        {score_bar(row['score'])}
                        <div style="font-size:0.78rem; color:#555; margin-top:4px;">
                            Score: <b>{row['score']}</b> / 100
                        </div>
                    </div>
                    """)

    elif highlight == "so_what":
        st.html("""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:8px;">

            <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:18px;">
                <div style="font-size:1.4rem; font-weight:800; color:#16A34A;">15–30%</div>
                <div style="font-weight:600; color:#15803D; margin-bottom:6px;">Redemption Lift</div>
                <div style="font-size:0.85rem; color:#555;">Personalised offers historically drive higher redemption rates vs generic broadcast offers.</div>
            </div>

            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:18px;">
                <div style="font-size:1.4rem; font-weight:800; color:#1D4ED8;">↑ Points Utilisation</div>
                <div style="font-weight:600; color:#1E40AF; margin-bottom:6px;">Reduce Breakage</div>
                <div style="font-size:0.85rem; color:#555;">Surfacing expiring-points GR offers drives basket visits and reduces points breakage liability.</div>
            </div>

            <div style="background:#FFF7ED; border:1px solid #FED7AA; border-radius:10px; padding:18px;">
                <div style="font-size:1.4rem; font-weight:800; color:#EA580C;">eCommerce Migration</div>
                <div style="font-weight:600; color:#C2410C; margin-bottom:6px;">Nudge, Don't Push</div>
                <div style="font-size:0.85rem; color:#555;">The Fuel redeemer nudge strategy surfaces digital offers without disrupting offline habits.</div>
            </div>

            <div style="background:#FDF4FF; border:1px solid #E9D5FF; border-radius:10px; padding:18px;">
                <div style="font-size:1.4rem; font-weight:800; color:#7C3AED;">Churn Prevention</div>
                <div style="font-weight:600; color:#6D28D9; margin-bottom:6px;">Win-Back at Scale</div>
                <div style="font-size:0.85rem; color:#555;">High churn risk customers get high-value personalised offers automatically — no manual campaign needed.</div>
            </div>

            <div style="background:#F0F9FF; border:1px solid #BAE6FD; border-radius:10px; padding:18px; grid-column:1/-1;">
                <div style="font-size:1.1rem; font-weight:800; color:#0369A1;">One Pipeline. One Table. Every Team Benefits.</div>
                <div style="font-size:0.88rem; color:#555; margin-top:6px; line-height:1.6;">
                    <b>c360_scored_offers</b> is a new C360 asset — it doesn't exist today.
                    The app reads it to show personalised offers. Analytics reads it to measure lift.
                    Marketing reads it to plan campaigns. ML reads it to track model drift.
                    SmartOfferEngine turns the existing C360 data investment into a personalisation engine.
                </div>
            </div>

        </div>
        """)

        # Architecture diagram
        arch_path = os.path.join(os.path.dirname(__file__), "..", "docs", "images", "exec_architecture.png")
        if os.path.exists(arch_path):
            st.markdown("")
            st.image(arch_path, use_container_width=True)

    elif highlight == "model_story":
        # ── Step 6: Rules vs AI — exec-friendly comparison ──────────────────
        st.html("""
        <div style="background:linear-gradient(135deg,#EFF6FF,#F5F3FF); border-radius:12px;
                    padding:14px 20px; margin-bottom:18px; display:flex; align-items:center; gap:12px;">
            <span style="font-size:1.5rem;">🤔</span>
            <div>
                <div style="font-weight:700; color:#1E3A5F; font-size:1rem;">
                    Same offers. Same customers. Completely different rankings.
                </div>
                <div style="font-size:0.85rem; color:#475569; margin-top:2px;">
                    The AI learns from purchase behaviour — the rules can't.
                </div>
            </div>
        </div>
        """)

        # ── Jessica Miller ──────────────────────────────────────────────────
        with st.container():
            st.html("""
            <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.06em; color:#6B7280; margin-bottom:6px;">
                Customer 1 — Jessica Miller &nbsp;|&nbsp; Vegan &nbsp;·&nbsp; Produce buyer &nbsp;·&nbsp; Instacart + DoorDash
            </div>
            """)
            col_rb, col_ai = st.columns(2, gap="medium")
            with col_rb:
                st.html("""
                <div style="background:#FEF2F2; border:2px solid #FECACA; border-radius:10px; padding:16px;">
                    <div style="font-weight:700; color:#991B1B; font-size:0.9rem; margin-bottom:12px;">
                        📋 Rule-Based Engine
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                        <span style="background:#DC2626; color:white; font-weight:800; font-size:0.8rem;
                                     width:24px; height:24px; border-radius:50%; display:inline-flex;
                                     align-items:center; justify-content:center;">#1</span>
                        <div>
                            <div style="font-weight:600; font-size:0.88rem; color:#1F2937;">
                                Save $1 on Dave's Killer Bread
                            </div>
                            <div style="font-size:0.77rem; color:#6B7280;">
                                High redemption rate · Good channel match
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.82rem; color:#7F1D1D; background:#FEE2E2;
                                border-radius:8px; padding:8px 10px; margin-top:6px;">
                        ⚠️ Doesn't know she's Vegan. Doesn't know she buys Produce weekly.
                        Scores by offer mechanics, not customer behaviour.
                    </div>
                </div>
                """)
            with col_ai:
                st.html("""
                <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:10px; padding:16px;">
                    <div style="font-weight:700; color:#15803D; font-size:0.9rem; margin-bottom:12px;">
                        🤖 AI (Propensity Model)
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                        <span style="background:#16A34A; color:white; font-weight:800; font-size:0.8rem;
                                     width:24px; height:24px; border-radius:50%; display:inline-flex;
                                     align-items:center; justify-content:center;">#3</span>
                        <div>
                            <div style="font-weight:600; font-size:0.88rem; color:#1F2937;">
                                $1 off any Fresh Vegetable Purchase
                            </div>
                            <div style="font-size:0.77rem; color:#6B7280;">
                                Strong produce affinity · Matches Vegan profile
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.82rem; color:#14532D; background:#DCFCE7;
                                border-radius:8px; padding:8px 10px; margin-top:6px;">
                        ✅ Learned from her transaction history: she buys produce every week.
                        Bread drops to #9. Vegetables rise to #3.
                    </div>
                </div>
                """)

        st.html('<div style="margin:16px 0 12px; border-top:1px solid #E5E7EB;"></div>')

        # ── Stephanie White ─────────────────────────────────────────────────
        with st.container():
            st.html("""
            <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.06em; color:#6B7280; margin-bottom:6px;">
                Customer 2 — Stephanie White &nbsp;|&nbsp; Organic shopper &nbsp;·&nbsp; High Churn Risk &nbsp;·&nbsp; Instacart user
            </div>
            """)
            col_rb2, col_ai2 = st.columns(2, gap="medium")
            with col_rb2:
                st.html("""
                <div style="background:#FEF2F2; border:2px solid #FECACA; border-radius:10px; padding:16px;">
                    <div style="font-weight:700; color:#991B1B; font-size:0.9rem; margin-bottom:12px;">
                        📋 Rule-Based Engine
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                        <span style="background:#DC2626; color:white; font-weight:800; font-size:0.8rem;
                                     width:24px; height:24px; border-radius:50%; display:inline-flex;
                                     align-items:center; justify-content:center;">#1</span>
                        <div>
                            <div style="font-weight:600; font-size:0.88rem; color:#1F2937;">
                                Save $2 on Coca-Cola 12 Pack
                            </div>
                            <div style="font-size:0.77rem; color:#6B7280;">
                                Top redemption rate · Channel match
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.82rem; color:#7F1D1D; background:#FEE2E2;
                                border-radius:8px; padding:8px 10px; margin-top:6px;">
                        ⚠️ Doesn't know she's an Organic buyer with no soft-drink history.
                        Broad rule — wrong person.
                    </div>
                </div>
                """)
            with col_ai2:
                st.html("""
                <div style="background:#F0FDF4; border:2px solid #86EFAC; border-radius:10px; padding:16px;">
                    <div style="font-weight:700; color:#15803D; font-size:0.9rem; margin-bottom:12px;">
                        🤖 AI (Propensity Model)
                    </div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                        <span style="background:#16A34A; color:white; font-weight:800; font-size:0.8rem;
                                     width:24px; height:24px; border-radius:50%; display:inline-flex;
                                     align-items:center; justify-content:center;">#2</span>
                        <div>
                            <div style="font-weight:600; font-size:0.88rem; color:#1F2937;">
                                $2 off Beef Sirloin per lb
                            </div>
                            <div style="font-size:0.77rem; color:#6B7280;">
                                High-value offer · Instacart affinity · Category match
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.82rem; color:#14532D; background:#DCFCE7;
                                border-radius:8px; padding:8px 10px; margin-top:6px;">
                        ✅ Coca-Cola drops to #10. AI finds a high-value offer that fits her
                        Organic + Instacart profile — far more likely to redeem.
                    </div>
                </div>
                """)

        st.html("""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px;
                    padding:14px 18px; margin-top:18px; display:flex; align-items:center; gap:12px;">
            <span style="font-size:1.4rem;">💡</span>
            <div style="font-size:0.88rem; color:#374151; line-height:1.6;">
                <strong>The business impact:</strong> Every misranked offer is a missed redemption.
                At Albertsons scale — millions of customers, weekly offer cycles —
                closing that gap drives measurable lift in basket size and loyalty engagement.
            </div>
        </div>
        """)


# ─── PAGE: PROBLEM EXPLORATION ────────────────────────────────────────────────

def render_problem_exploration():
    st.subheader("Problem Exploration")
    st.caption("Who is affected by the current state — and what do they need?")
    st.markdown("")

    col_cust, col_biz = st.columns(2, gap="large")

    # ── Customer Persona ────────────────────────────────────────────────────
    with col_cust:
        st.html("""
        <div style="background:linear-gradient(135deg,#EFF6FF,#DBEAFE); border:2px solid #93C5FD;
                    border-radius:16px; padding:24px; height:100%;">

            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="font-size:2.4rem;">🛒</div>
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#1E3A5F;">The Customer</div>
                    <div style="font-size:0.82rem; color:#3B82F6; font-weight:600;">Alex — for U+ Member, weekly shopper</div>
                </div>
            </div>

            <div style="font-size:0.78rem; font-weight:700; color:#1D4ED8; text-transform:uppercase;
                        letter-spacing:0.05em; margin-bottom:10px;">Pain Points Today</div>
            <ul style="font-size:0.88rem; color:#1E3A5F; line-height:1.6; padding-left:18px; margin:0 0 14px 0;">
                <li>Sees 527 offers with no guidance on what's relevant</li>
                <li>Receives same generic offers as everyone else</li>
                <li>2,800 points expiring soon — unaware of eligible rewards</li>
                <li>Clips only 3–4 offers; the list feels irrelevant</li>
                <li>for U+ tier doesn't feel like added value</li>
            </ul>

            <div style="font-size:0.78rem; font-weight:700; color:#1D4ED8; text-transform:uppercase;
                        letter-spacing:0.05em; margin-bottom:10px;">What They Need</div>
            <ul style="font-size:0.88rem; color:#1E3A5F; line-height:1.6; padding-left:18px; margin:0;">
                <li>Ranked offers matching their shopping habits</li>
                <li>Timely alerts for expiring points with relevant rewards</li>
                <li>Exclusive for U+ offers</li>
                <li>Personalized recommendations they'll actually use</li>
            </ul>
        </div>
        """)

    # ── Business User Persona ───────────────────────────────────────────────
    with col_biz:
        st.html("""
        <div style="background:linear-gradient(135deg,#F5F3FF,#EDE9FE); border:2px solid #A78BFA;
                    border-radius:16px; padding:24px; height:100%;">

            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="font-size:2.4rem;">📊</div>
                <div>
                    <div style="font-size:1.1rem; font-weight:800; color:#2E1065;">The Business User</div>
                    <div style="font-size:0.82rem; color:#7C3AED; font-weight:600;">Jordan — Loyalty &amp; Offers Manager</div>
                </div>
            </div>

            <div style="font-size:0.78rem; font-weight:700; color:#6D28D9; text-transform:uppercase;
                        letter-spacing:0.05em; margin-bottom:10px;">Pain Points Today</div>
            <ul style="font-size:0.88rem; color:#2E1065; line-height:1.6; padding-left:18px; margin:0 0 14px 0;">
                <li>Scripts manually rank hundreds of offers monthly — time-consuming and still feels like guessing</li>
                <li>No insight into why customers don't redeem</li>
                <li>30% of loyalty points expire unused</li>
                <li>No segment-based campaigns or personalization</li>
                <li>C360 data underutilized for ranking</li>
            </ul>

            <div style="font-size:0.78rem; font-weight:700; color:#6D28D9; text-transform:uppercase;
                        letter-spacing:0.05em; margin-bottom:10px;">What They Need</div>
            <ul style="font-size:0.88rem; color:#2E1065; line-height:1.6; padding-left:18px; margin:0;">
                <li>Automated ranking to focus on strategy, not curation</li>
                <li>Segment insights: churn, expiring points, upgrade-ready</li>
                <li>Feedback loop from redemption data</li>
                <li>One centralized output table for all teams</li>
            </ul>
        </div>
        """)

    # ── Shared gap ──────────────────────────────────────────────────────────
    st.markdown("")
    st.html("""
    <div style="background:linear-gradient(135deg,#00529B,#003870); border-radius:14px;
                padding:20px 28px; color:white; text-align:center;">
        <div style="font-size:1.05rem; font-weight:800; margin-bottom:8px;">
            The Gap — and Why It Exists
        </div>
        <div style="font-size:0.88rem; color:rgba(255,255,255,0.85); line-height:1.6; max-width:700px; margin:0 auto;">
            C360 already holds transaction history, category affinity, points balances, churn scores, and channel preferences for every household.
            The data exists — it just isn't being used to rank offers.
            <br/><br/>
            <b>SmartOfferEngine adds <code style="background:rgba(255,255,255,0.15); padding:2px 6px; border-radius:4px;">c360_scored_offers</code></b> —
            a nightly-rebuilt, personalized offer ranking per household that solves both problems with one pipeline.
        </div>
    </div>
    """)


# ─── PAGE: SEGMENT EXPLORER ───────────────────────────────────────────────────

def render_segments():
    st.subheader("Customer Segment Explorer")

    fuel     = customers_df[customers_df["gas_rewards_ind_6m"] == True]
    premium  = customers_df[customers_df["clv_tier_level_id"] == "4U+"]
    high_pts = customers_df[customers_df["current_point_balance"] >= 1000]
    recent   = customers_df[customers_df["days_since_last_txn"] <= 7]
    high_churn = customers_df[customers_df["churn_segment_cd"] == "High Risk"]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.html(f"""<div class="seg-card">
            <div class="seg-number">{len(fuel)}</div>
            <div class="seg-label">&#9981; Fuel Redeemers</div>
        </div>""")
    with c2:
        st.html(f"""<div class="seg-card">
            <div class="seg-number">{len(premium)}</div>
            <div class="seg-label">&#9733; for U+ Subscribers</div>
        </div>""")
    with c3:
        st.html(f"""<div class="seg-card">
            <div class="seg-number">{len(high_pts)}</div>
            <div class="seg-label">&#11088; High Points (1000+)</div>
        </div>""")
    with c4:
        st.html(f"""<div class="seg-card">
            <div class="seg-number">{len(recent)}</div>
            <div class="seg-label">&#9889; Active This Week</div>
        </div>""")
    with c5:
        st.html(f"""<div class="seg-card">
            <div class="seg-number">{len(high_churn)}</div>
            <div class="seg-label">&#9888; High Churn Risk</div>
        </div>""")

    st.markdown("---")

    segment_choice = st.selectbox(
        "Drill into segment",
        ["Fuel Redeemers", "for U+ Subscribers", "High Points Holders", "Active This Week", "High Churn Risk"]
    )

    seg_map = {
        "Fuel Redeemers":       fuel,
        "for U+ Subscribers":   premium,
        "High Points Holders":  high_pts,
        "Active This Week":     recent,
        "High Churn Risk":      high_churn,
    }
    seg_df = seg_map[segment_choice][[
        "household_id", "full_name", "clv_tier_level_id", "current_point_balance",
        "fav_channel", "days_since_last_txn", "customer_age", "churn_segment_cd"
    ]].rename(columns={
        "household_id":          "Household ID",
        "full_name":             "Name",
        "clv_tier_level_id":     "Tier",
        "current_point_balance": "Points",
        "fav_channel":           "Channel",
        "days_since_last_txn":   "Days Since Txn",
        "customer_age":          "Age Group",
        "churn_segment_cd":      "Churn Risk",
    })

    st.markdown(f"**{len(seg_df)} households** in this segment")
    st.dataframe(seg_df, use_container_width=True, hide_index=True)

    st.markdown("#### Segment Stats")
    s1, s2, s3 = st.columns(3)
    s1.metric("Avg Points Balance", f"{seg_df['Points'].mean():,.0f}")
    s2.metric("Avg Days Since Txn", f"{seg_df['Days Since Txn'].mean():.1f}")
    s3.metric("4U+ Share",          f"{(seg_df['Tier'] == '4U+').mean()*100:.1f}%")

    st.markdown("---")
    st.markdown("#### Sign in as a customer from this segment")
    seg_labels  = (seg_df["Name"] + "  (" + seg_df["Household ID"] + ")").tolist()
    seg_hid_map = dict(zip(seg_labels, seg_df["Household ID"].tolist()))
    pick_label  = st.selectbox("Select customer", seg_labels)
    pick        = seg_hid_map[pick_label]
    if st.button("View their offers", type="primary"):
        st.session_state.household_id = pick
        st.session_state.page = "dashboard"
        st.rerun()


def page_segments():
    with st.sidebar:
        st.html(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
            <img src="data:image/png;base64,{ICON_B64}" height="32"
                 style="filter: brightness(0) invert(1);"/>
            <span style="color:white; font-size:1.2rem; font-weight:700;">SmartOfferEngine</span>
        </div>
        """)
        st.markdown("---")
        if st.button("← Back to Login"):
            st.session_state.page = "login"
            st.rerun()

    st.html(f"""
    <div class="abs-header">
        <img src="data:image/png;base64,{ICON_B64}" height="40" style="filter: brightness(0) invert(1);"/>
        <span style="color:#A8C8F0; font-size:0.9rem;">Segment Explorer</span>
    </div>
    """)

    render_segments()


# ─── FEATURE ENGINEER (Business-Friendly UI) ─────────────────────────────────

def read_feature_cols():
    """Read FEATURE_COLS_STANDARD and FEATURE_COLS_GR from scoring_ml.py.
    Returns dict: {"standard": [...], "gr": [...]}.
    """
    import re
    scoring_file = os.path.join(os.path.dirname(__file__), "engine", "scoring_ml.py")
    with open(scoring_file, 'r', encoding='utf-8') as f:
        content = f.read()

    def _extract(var_name):
        match = re.search(rf'{var_name}\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if not match:
            return []
        features = []
        for line in match.group(1).split('\n'):
            line = line.strip().strip(',')
            if not line or line.startswith('#'):
                continue
            # handle comma-separated on one line e.g. "a", "b",
            for token in line.split(','):
                token = token.strip().strip('"').strip("'")
                if token:
                    features.append(token)
        return features

    return {
        "standard": _extract("FEATURE_COLS_STANDARD"),
        "gr": _extract("FEATURE_COLS_GR"),
    }


def get_feature_categories():
    """Return feature definitions grouped by model applicability.
    Returns (categories_dict, feature_cols_dict) where feature_cols_dict
    has keys 'standard' and 'gr'.
    """
    feature_cols = read_feature_cols()

    # Full catalogue of known features with descriptions and which models they apply to
    ALL_FEATURES = [
        # Standard-only
        ("is_4uplus",                 "Premium tier status (4U+)",                          "standard"),
        ("gas_rewards",               "Fuel rewards participation (6m)",                     "standard"),
        ("doordash",                  "DoorDash adoption signal",                            "standard"),
        ("instacart",                 "Instacart adoption signal",                           "standard"),
        ("uber",                      "Uber Eats adoption signal",                           "standard"),
        ("is_j4u_exclusive",          "J4U exclusive offer flag",                            "standard"),
        ("is_freshpass_offer",        "FreshPass subscription required",                     "standard"),
        ("channel_match",             "Does preferred channel match offer channel?",          "standard"),
        # GR-only
        ("current_point_balance",     "Points balance — primary GR eligibility gate",        "gr"),
        ("points_expiring_next_month","Points expiring next month (urgency signal)",          "gr"),
        ("points_gap",                "Surplus above GR tier threshold",                     "gr"),
        # Shared by both
        ("household_size",            "Number of people in household",                       "both"),
        ("num_children",              "Number of children in household",                     "both"),
        ("churn_risk",                "Predicted churn probability (0–1)",                   "both"),
        ("days_since_last_txn",       "Days since last purchase (recency)",                  "both"),
        ("discount_value",            "Dollar amount or item value of the offer",            "both"),
        ("redemption_rate",           "Historical redemption % for this offer",              "both"),
        ("days_until_expiry",         "Days until offer expires",                            "both"),
        ("category_affinity",         "Customer's historical spend in this offer's category","both"),
    ]

    categories = {
        "Standard Model Only": [(n, d) for n, d, m in ALL_FEATURES if m == "standard"],
        "GR Model Only":       [(n, d) for n, d, m in ALL_FEATURES if m == "gr"],
        "Both Models":         [(n, d) for n, d, m in ALL_FEATURES if m == "both"],
    }

    return categories, feature_cols


def get_feature_importance():
    """Get feature importance from model_metadata.json and model_gr_metadata.json."""
    meta = load_model_metadata()
    importance = {}

    if "propensity_standard" in meta and "top_features" in meta["propensity_standard"]:
        for feat, imp in meta["propensity_standard"]["top_features"]:
            importance[feat] = {"standard": imp, "gr": None}

    if "propensity_gr" in meta and "top_features" in meta["propensity_gr"]:
        for feat, imp in meta["propensity_gr"]["top_features"]:
            if feat in importance:
                importance[feat]["gr"] = imp
            else:
                importance[feat] = {"standard": None, "gr": imp}

    return importance


def write_feature_cols(selected_standard: list, selected_gr: list):
    """Write updated FEATURE_COLS_STANDARD and FEATURE_COLS_GR back to scoring_ml.py."""
    import re

    scoring_file = os.path.join(os.path.dirname(__file__), "engine", "scoring_ml.py")
    with open(scoring_file, 'r', encoding='utf-8') as f:
        content = f.read()

    _STANDARD_CUSTOMER = ["is_4uplus", "gas_rewards", "doordash", "instacart", "uber",
                          "household_size", "num_children", "churn_risk", "days_since_last_txn"]
    _STANDARD_OFFER    = ["discount_value", "is_j4u_exclusive", "is_freshpass_offer",
                          "redemption_rate", "days_until_expiry"]
    _STANDARD_INTER    = ["channel_match", "category_affinity"]

    _GR_CUSTOMER = ["current_point_balance", "points_expiring_next_month", "is_4uplus",
                    "household_size", "num_children", "churn_risk", "days_since_last_txn"]
    _GR_OFFER    = ["discount_value", "redemption_rate", "days_until_expiry"]
    _GR_INTER    = ["category_affinity", "points_gap"]

    def _build_list(var_name, selected, customer_pool, offer_pool, inter_pool, comment_no_pts=""):
        c = [f for f in customer_pool if f in selected]
        o = [f for f in offer_pool    if f in selected]
        i = [f for f in inter_pool    if f in selected]
        lines = [f'{var_name} = [']
        if comment_no_pts:
            lines.append(f'    # Customer — {comment_no_pts}')
        else:
            lines.append('    # Customer')
        lines.append('    ' + ', '.join(f'"{f}"' for f in c) + ',')
        lines.append('    # Offer')
        lines.append('    ' + ', '.join(f'"{f}"' for f in o) + ',')
        lines.append('    # Interaction')
        lines.append('    ' + ', '.join(f'"{f}"' for f in i) + ',')
        lines.append(']')
        return '\n'.join(lines)

    new_std = _build_list("FEATURE_COLS_STANDARD", selected_standard,
                          _STANDARD_CUSTOMER, _STANDARD_OFFER, _STANDARD_INTER,
                          comment_no_pts="no points features; standard offers don't require points to redeem")
    new_gr  = _build_list("FEATURE_COLS_GR", selected_gr,
                          _GR_CUSTOMER, _GR_OFFER, _GR_INTER)

    content = re.sub(r'FEATURE_COLS_STANDARD\s*=\s*\[.*?\]', new_std, content, flags=re.DOTALL)
    content = re.sub(r'FEATURE_COLS_GR\s*=\s*\[.*?\]',      new_gr,  content, flags=re.DOTALL)

    with open(scoring_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def render_feature_engineer():
    """Business-friendly UI for managing propensity model features."""
    st.markdown("# 🔧 Feature Engineer")
    st.markdown("Enable/disable features for each model. Changes trigger a full retrain of both propensity models.")

    categories, feature_cols = get_feature_categories()
    feature_importance = get_feature_importance()
    std_active = set(feature_cols.get("standard", []))
    gr_active  = set(feature_cols.get("gr", []))

    # Current model metrics
    meta = load_model_metadata()
    c1, c2, c3, c4 = st.columns(4)
    auc_std = meta.get("propensity_standard", {}).get("auc_cv", "—")
    auc_gr  = meta.get("propensity_gr", {}).get("auc_cv", "—")
    c1.metric("Standard AUC", f"{auc_std:.4f}" if isinstance(auc_std, float) else auc_std)
    c2.metric("GR AUC",       f"{auc_gr:.4f}"  if isinstance(auc_gr,  float) else auc_gr)
    c3.metric("Standard Features", len(std_active))
    c4.metric("GR Features",        len(gr_active))

    st.markdown("---")
    st.caption("✅ = currently active  |  ☐ = inactive (can add)  |  importance % from last training run")

    selected_std = []
    selected_gr  = []
    changes = {"std_added": [], "std_removed": [], "gr_added": [], "gr_removed": []}

    # Section headers per group
    _GROUP_LABEL = {
        "Standard Model Only": "Standard model only — not applicable to GR offers",
        "GR Model Only":       "GR model only — points/threshold signals not relevant to standard offers",
        "Both Models":         "Shared by both models",
    }

    for group_name, features in categories.items():
        if not features:
            continue
        st.markdown(f"#### {group_name}")
        st.caption(_GROUP_LABEL.get(group_name, ""))

        for feat_name, feat_desc in features:
            imp        = feature_importance.get(feat_name, {"standard": None, "gr": None})
            imp_std    = imp["standard"]
            imp_gr     = imp["gr"]
            in_std     = feat_name in std_active
            in_gr      = feat_name in gr_active

            # Build expander title
            imp_parts = []
            if imp_std is not None:
                imp_parts.append(f"Std {imp_std:.1%}")
            if imp_gr is not None:
                imp_parts.append(f"GR {imp_gr:.1%}")
            imp_str = f" — {', '.join(imp_parts)}" if imp_parts else ""
            active_icon = "✅" if (in_std or in_gr) else "☐"
            with st.expander(f"{active_icon} **{feat_name}**{imp_str}"):
                st.caption(feat_desc)

                ec1, ec2 = st.columns(2)

                # Standard column — only show for standard-applicable features
                if group_name in ("Standard Model Only", "Both Models"):
                    with ec1:
                        use_std = st.checkbox("Standard model", value=in_std, key=f"std_{feat_name}")
                        if use_std:
                            selected_std.append(feat_name)
                            if not in_std:
                                changes["std_added"].append(feat_name)
                        else:
                            if in_std:
                                changes["std_removed"].append(feat_name)
                        if imp_std is not None:
                            st.caption(f"Current importance: {imp_std:.1%}")
                else:
                    with ec1:
                        st.caption("*(Standard model — N/A)*")

                # GR column — only show for GR-applicable features
                if group_name in ("GR Model Only", "Both Models"):
                    with ec2:
                        use_gr = st.checkbox("GR model", value=in_gr, key=f"gr_{feat_name}")
                        if use_gr:
                            selected_gr.append(feat_name)
                            if not in_gr:
                                changes["gr_added"].append(feat_name)
                        else:
                            if in_gr:
                                changes["gr_removed"].append(feat_name)
                        if imp_gr is not None:
                            st.caption(f"Current importance: {imp_gr:.1%}")
                else:
                    with ec2:
                        st.caption("*(GR model — N/A)*")

    st.markdown("---")

    # Change summary
    any_changes = any(changes.values())
    if any_changes:
        if changes["std_added"]:
            st.success(f"Standard — adding: {', '.join(f'`{f}`' for f in changes['std_added'])}")
        if changes["std_removed"]:
            st.warning(f"Standard — removing: {', '.join(f'`{f}`' for f in changes['std_removed'])}")
        if changes["gr_added"]:
            st.success(f"GR — adding: {', '.join(f'`{f}`' for f in changes['gr_added'])}")
        if changes["gr_removed"]:
            st.warning(f"GR — removing: {', '.join(f'`{f}`' for f in changes['gr_removed'])}")
    else:
        st.info("ℹ️ No changes — feature sets match current scoring_ml.py")

    err_std = len(selected_std) < 3
    err_gr  = len(selected_gr)  < 3
    if err_std:
        st.error(f"❌ Standard model needs at least 3 features (currently {len(selected_std)})")
    if err_gr:
        st.error(f"❌ GR model needs at least 3 features (currently {len(selected_gr)})")

    if st.button("🚀 Apply Changes & Retrain Both Models", type="primary",
                 disabled=(err_std or err_gr)):
        with st.spinner("⏳ Updating scoring_ml.py and retraining…"):
            try:
                write_feature_cols(selected_std, selected_gr)
                st.success(f"✅ scoring_ml.py updated — Standard: {len(selected_std)} features, GR: {len(selected_gr)} features")

                import subprocess
                env = os.environ.copy()
                env["DATABASE_URL"] = DB_URL
                env["PYTHONIOENCODING"] = "utf-8"

                result = subprocess.run(
                    [sys.executable, os.path.join(os.path.dirname(__file__), "engine", "scoring_ml.py"), "--retrain"],
                    cwd=os.path.dirname(os.path.dirname(__file__)),
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=600,
                )

                if result.returncode == 0:
                    st.success("✅ Both models retrained successfully!")
                    st.code(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
                    st.cache_data.clear()
                    st.toast("🔄 Caches cleared — rankings updated")
                else:
                    st.error("❌ Retraining failed:")
                    st.code(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

            except subprocess.TimeoutExpired:
                st.error("⏱️ Retraining exceeded 10 minutes. Try reducing the feature count.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.markdown("---")
    st.markdown("### Feature Definitions")
    
    with st.expander("📚 Full Feature Reference"):
        st.markdown("""
        **Customer Features** track customer behavior and attributes:
        - `current_point_balance`: Loyalty points available
        - `points_expiring_next_month`: Urgency signal (points about to expire)
        - `is_4uplus`: Premium tier (0 or 1)
        - `gas_rewards`: Fuel rewards participation in last 6 months
        - `doordash`, `instacart`, `uber`: Delivery app adoption
        - `household_size`: # people in household
        - `num_children`: Presence of kids
        - `churn_risk`: Predicted churn score (0–1)
        - `days_since_last_txn`: Purchase recency
        
        **Offer Features** describe the offer:
        - `discount_value`: $ amount or item value
        - `is_j4u_exclusive`: J4U only (1) or available to all (0)
        - `is_freshpass_offer`: Requires FreshPass (1) or not (0)
        - `redemption_rate`: How often customers redeem %
        - `days_until_expiry`: Days remaining
        
        **Interaction Features** capture customer-offer fit:
        - `channel_match`: Does customer's preferred channel match offer's channel?
        - `category_affinity`: Customer's historical spend score in this category
        - `points_gap`: How far above the Grocery Reward tier threshold?
        """)


# ─── ROUTER ───────────────────────────────────────────────────────────────────

# ─── OMS — OFFER MANAGEMENT SYSTEM ───────────────────────────────────────────

def _oms_load_offers() -> pd.DataFrame:
    """Load all non-deleted offers for the OMS manage tab."""
    with _engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT client_offer_id, offer_dsc, delivery_channel_cd, program_type,
                   discount_type_cd, discount_value, start_dt, end_dt,
                   offer_status_cd, is_appliable_to_j4u_ind, is_freshpass_offer_ind,
                   tier_1_points_threshold, target_level_cd,
                   dw_create_ts
            FROM c360_offer
            WHERE dw_logical_delete_ind = FALSE
            ORDER BY dw_create_ts DESC
        """)).fetchall()
        cols = ["client_offer_id", "offer_dsc", "delivery_channel_cd", "program_type",
                "discount_type_cd", "discount_value", "start_dt", "end_dt",
                "offer_status_cd", "is_appliable_to_j4u_ind", "is_freshpass_offer_ind",
                "tier_1_points_threshold", "target_level_cd", "dw_create_ts"]
        return pd.DataFrame(rows, columns=cols)


def _oms_create_offer(fields: dict) -> str:
    """Insert a new offer row; returns the generated client_offer_id."""
    import uuid as _uuid
    from datetime import datetime as _dt

    client_offer_id = f"OFR-OMS-{str(_uuid.uuid4())[:8].upper()}"
    oms_offer_id    = f"OMS-{str(_uuid.uuid4())[:8].upper()}"
    now = _dt.now()

    with _engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO c360_offer (
                client_offer_id, oms_offer_id, offer_dsc, title_dsc1,
                headline_txt, description_txt, categories_txt,
                start_dt, end_dt, display_start_dt, display_end_dt,
                offer_type, delivery_channel_cd, program_type, program_subtype,
                discount_type_cd, discount_value, min_purch_qty, min_purch_amt,
                target_level_cd, is_appliable_to_j4u_ind, is_freshpass_offer_ind,
                tier_1_points_threshold, is_in_weekly_ad, offer_status_cd,
                dw_create_ts, dw_last_update_ts,
                dw_logical_delete_ind, dw_current_version_ind
            ) VALUES (
                :client_offer_id, :oms_offer_id, :offer_dsc, :title_dsc1,
                :headline_txt, :description_txt, :categories_txt,
                :start_dt, :end_dt, :start_dt, :end_dt,
                :offer_type, :delivery_channel_cd, :program_type, :program_subtype,
                :discount_type_cd, :discount_value, :min_purch_qty, :min_purch_amt,
                :target_level_cd, :is_appliable_to_j4u_ind, :is_freshpass_offer_ind,
                :tier_1_points_threshold, :is_in_weekly_ad, :offer_status_cd,
                :now, :now, FALSE, TRUE
            )
        """), {"client_offer_id": client_offer_id, "oms_offer_id": oms_offer_id, "now": now, **fields})
        conn.commit()
    return client_offer_id


def _oms_update_offer(client_offer_id: str, fields: dict):
    """Update mutable fields on an existing offer."""
    from datetime import datetime as _dt
    fields["dw_last_update_ts"] = _dt.now()
    fields["oid"] = client_offer_id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields if k != "oid")
    with _engine.connect() as conn:
        conn.execute(text(f"UPDATE c360_offer SET {set_clause} WHERE client_offer_id = :oid"), fields)
        conn.commit()


def _oms_deactivate_offer(client_offer_id: str):
    """Soft-delete: mark offer as INACTIVE."""
    from datetime import datetime as _dt
    with _engine.connect() as conn:
        conn.execute(text("""
            UPDATE c360_offer
            SET offer_status_cd = 'INACTIVE', dw_logical_delete_ind = TRUE,
                dw_last_update_ts = :now
            WHERE client_offer_id = :oid
        """), {"oid": client_offer_id, "now": _dt.now()})
        conn.commit()


def render_oms():
    st.subheader("Offer Management System (OMS)")
    st.caption("Create, edit, and deactivate offers in the catalog. Changes take effect after re-scoring.")

    tab_create, tab_manage = st.tabs(["➕ Create Offer", "📋 Manage Offers"])

    # ── CREATE ──────────────────────────────────────────────────────────────
    with tab_create:
        st.markdown("### New Offer")

        col1, col2 = st.columns(2)
        with col1:
            offer_dsc = st.text_input("Offer Description *", placeholder="e.g. $2 Off Cheerios 18 oz")
            program_type = st.selectbox("Program Type *", ["Club Card", "J4U", "Grocery Reward"])
            delivery_channel_cd = st.selectbox("Delivery Channel *", ["J4U", "Weekly Ad", "Auto Clip"])
            discount_type_cd = st.selectbox("Discount Type *", [
                "AMT_OFF", "PCT_OFF", "GROCERY_REWARD", "DEPT_REWARD",
                "FREE_ITEM", "FUEL_CENTS", "POINTS_MULTIPLIER", "FREE_DELIVERY"
            ])
            _gr_types = {"GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM"}
            if discount_type_cd in _gr_types:
                st.info("🎁 This type appears in **My Rewards** (points-based). Set a Points Threshold below.")
            else:
                st.info("🏷️ This type appears in **My Offers** (standard ranked list).")
            discount_value = st.number_input("Discount Value ($)", min_value=0.0, step=0.25, value=1.0)
            target_level_cd = st.selectbox("Target Level", ["ITEM", "CATEGORY", "BASKET"])

        with col2:
            from datetime import date as _date
            start_dt = st.date_input("Start Date *", value=_date.today())
            end_dt   = st.date_input("End Date *",   value=_date.today().replace(day=28))
            program_subtype = st.text_input("Program Subtype", placeholder="e.g. Department, Free Item (GR only)")
            categories_txt  = st.text_input("Category", placeholder="e.g. Dairy Eggs Cheese")
            min_purch_qty   = st.number_input("Min Purchase Qty", min_value=0, step=1, value=1)

        st.markdown("#### Targeting")
        c1, c2, c3 = st.columns(3)
        with c1:
            is_appliable_to_j4u_ind  = st.checkbox("4U+ Exclusive (J4U only)")
        with c2:
            is_freshpass_offer_ind   = st.checkbox("FreshPass Only")
        with c3:
            is_in_weekly_ad          = st.checkbox("In Weekly Ad")

        tier_pts = None
        if program_type == "Grocery Reward":
            tier_pts = st.selectbox("Points Threshold (GR tier)",
                                    [100, 200, 300, 400, 500, 700, 1000, 1200])

        st.markdown("#### Optional Details")
        title_dsc1      = st.text_input("Title", placeholder="e.g. Club Card Price")
        headline_txt    = st.text_input("Headline", placeholder="e.g. $2.00 off when you buy 1")
        description_txt = st.text_area("Description", height=80)

        st.markdown("---")
        if st.button("🚀 Create Offer", type="primary"):
            if not offer_dsc.strip():
                st.error("Offer description is required.")
            elif end_dt <= start_dt:
                st.error("End date must be after start date.")
            else:
                try:
                    cid = _oms_create_offer({
                        "offer_dsc":              offer_dsc.strip(),
                        "title_dsc1":             title_dsc1 or None,
                        "headline_txt":           headline_txt or None,
                        "description_txt":        description_txt or None,
                        "categories_txt":         categories_txt or None,
                        "start_dt":               str(start_dt),
                        "end_dt":                 str(end_dt),
                        "offer_type":             "ITEM_DISCOUNT",
                        "delivery_channel_cd":    delivery_channel_cd,
                        "program_type":           program_type,
                        "program_subtype":        program_subtype or None,
                        "discount_type_cd":       discount_type_cd,
                        "discount_value":         discount_value,
                        "min_purch_qty":          min_purch_qty if min_purch_qty > 0 else None,
                        "min_purch_amt":          None,
                        "target_level_cd":        target_level_cd,
                        "is_appliable_to_j4u_ind": is_appliable_to_j4u_ind,
                        "is_freshpass_offer_ind": is_freshpass_offer_ind,
                        "tier_1_points_threshold": tier_pts,
                        "is_in_weekly_ad":        is_in_weekly_ad,
                        "offer_status_cd":        "ACTIVE",
                    })
                    st.success(f"✅ Offer created: **{cid}**")
                    st.session_state["oms_last_created"] = cid
                except Exception as e:
                    st.error(f"❌ Failed to create offer: {e}")

        if st.session_state.get("oms_last_created"):
            st.markdown("---")
            st.markdown("#### Score Now")
            st.caption("Re-run the scoring engines so this offer appears in customer rankings.")
            col_rb, col_ml = st.columns(2)
            with col_rb:
                if st.button("⚡ Run Rule-Based Scoring", use_container_width=True):
                    import subprocess
                    env = os.environ.copy()
                    env["DATABASE_URL"] = DB_URL
                    env["DYLD_LIBRARY_PATH"] = os.path.expanduser("~/lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
                    scoring_path = os.path.join(os.path.dirname(__file__), "engine", "scoring.py")
                    with st.spinner("Scoring all households…"):
                        result = subprocess.run([sys.executable, scoring_path], capture_output=True, text=True, timeout=60, env=env)
                    if result.returncode == 0:
                        load_scored.clear()
                        st.success("✅ Rule-based scores updated. Switch to My Offers to see rankings.")
                    else:
                        st.error(f"❌ Scoring failed: {result.stderr[-500:]}")
            with col_ml:
                if st.button("🤖 Run Propensity Scoring", use_container_width=True):
                    import subprocess
                    env = os.environ.copy()
                    env["DATABASE_URL"] = DB_URL
                    env["DYLD_LIBRARY_PATH"] = os.path.expanduser("~/lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
                    ml_path = os.path.join(os.path.dirname(__file__), "engine", "scoring_ml.py")
                    with st.spinner("Running propensity models…"):
                        result = subprocess.run([sys.executable, ml_path], capture_output=True, text=True, timeout=120, env=env)
                    if result.returncode == 0:
                        load_scored.clear()
                        st.success("✅ Propensity scores updated. Switch to My Offers to see rankings.")
                    else:
                        st.error(f"❌ Scoring failed: {result.stderr[-500:]}")

    # ── MANAGE ──────────────────────────────────────────────────────────────
    with tab_manage:
        st.markdown("### All Offers")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            status_filter = st.selectbox("Filter by Status", ["All", "ACTIVE", "INACTIVE"])
        with col_f2:
            pt_filter = st.selectbox("Filter by Program Type", ["All", "Club Card", "J4U", "Grocery Reward"])

        df = _oms_load_offers()
        if status_filter != "All":
            df = df[df["offer_status_cd"] == status_filter]
        if pt_filter != "All":
            df = df[df["program_type"] == pt_filter]

        search = st.text_input("Search offers", placeholder="Type to filter by description or ID")
        if search:
            mask = (
                df["offer_dsc"].str.contains(search, case=False, na=False) |
                df["client_offer_id"].str.contains(search, case=False, na=False)
            )
            df = df[mask]

        st.caption(f"{len(df)} offer(s) shown")

        if df.empty:
            st.info("No offers match the current filters.")
        else:
            display_df = df[["client_offer_id", "offer_dsc", "program_type",
                              "discount_type_cd", "discount_value",
                              "start_dt", "end_dt", "offer_status_cd"]].copy()
            display_df.columns = ["ID", "Description", "Program", "Discount Type",
                                   "Value ($)", "Start", "End", "Status"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### Edit or Deactivate an Offer")

            offer_labels = {f"{r['client_offer_id']} — {r['offer_dsc'][:50]}": r['client_offer_id']
                            for _, r in df.iterrows()}
            chosen_label = st.selectbox("Select offer", list(offer_labels.keys()))
            chosen_id    = offer_labels[chosen_label]
            chosen_row   = df[df["client_offer_id"] == chosen_id].iloc[0]

            edit_col, del_col = st.columns([3, 1])

            with edit_col:
                with st.expander("✏️ Edit this offer"):
                    e_dsc      = st.text_input("Description",       value=chosen_row["offer_dsc"],            key="e_dsc")
                    e_channel  = st.selectbox("Delivery Channel",   ["J4U", "Weekly Ad", "Auto Clip"],
                                              index=["J4U", "Weekly Ad", "Auto Clip"].index(chosen_row["delivery_channel_cd"])
                                                    if chosen_row["delivery_channel_cd"] in ["J4U", "Weekly Ad", "Auto Clip"] else 0,
                                              key="e_chan")
                    e_discount = st.number_input("Discount Value ($)", value=float(chosen_row["discount_value"] or 0),
                                                 min_value=0.0, step=0.25, key="e_disc")
                    from datetime import date as _date2
                    e_end      = st.date_input("End Date", value=chosen_row["end_dt"], key="e_end")
                    e_status   = st.selectbox("Status", ["ACTIVE", "INACTIVE"],
                                             index=0 if chosen_row["offer_status_cd"] == "ACTIVE" else 1,
                                             key="e_status")

                    if st.button("💾 Save Changes", key="save_edit"):
                        try:
                            _oms_update_offer(chosen_id, {
                                "offer_dsc":          e_dsc.strip(),
                                "delivery_channel_cd": e_channel,
                                "discount_value":     e_discount,
                                "end_dt":             str(e_end),
                                "offer_status_cd":    e_status,
                            })
                            st.success(f"✅ Offer **{chosen_id}** updated.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ {ex}")

            with del_col:
                st.markdown("&nbsp;")
                if chosen_row["offer_status_cd"] == "ACTIVE":
                    if st.button("🗑 Deactivate", type="secondary", key="deactivate_btn"):
                        st.session_state["confirm_deactivate"] = chosen_id

            if st.session_state.get("confirm_deactivate") == chosen_id:
                st.warning(f"Are you sure you want to deactivate **{chosen_id}**?")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("Yes, deactivate", type="primary"):
                        try:
                            _oms_deactivate_offer(chosen_id)
                            st.success(f"✅ Offer **{chosen_id}** deactivated.")
                            st.session_state.pop("confirm_deactivate", None)
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ {ex}")
                with c_no:
                    if st.button("Cancel"):
                        st.session_state.pop("confirm_deactivate", None)
                        st.rerun()

        st.markdown("---")
        st.markdown("#### Score Now")
        st.caption("Re-run scoring engines after edits so changes appear in customer rankings.")
        col_rb2, col_ml2 = st.columns(2)
        with col_rb2:
            if st.button("⚡ Run Rule-Based Scoring", use_container_width=True, key="manage_score_rb"):
                import subprocess
                env = os.environ.copy()
                env["DATABASE_URL"] = DB_URL
                env["DYLD_LIBRARY_PATH"] = os.path.expanduser("~/lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
                scoring_path = os.path.join(os.path.dirname(__file__), "engine", "scoring.py")
                with st.spinner("Scoring all households…"):
                    result = subprocess.run([sys.executable, scoring_path], capture_output=True, text=True, timeout=60, env=env)
                if result.returncode == 0:
                    load_scored.clear()
                    st.success("✅ Rule-based scores updated.")
                else:
                    st.error(f"❌ {result.stderr[-500:]}")
        with col_ml2:
            if st.button("🤖 Run Propensity Scoring", use_container_width=True, key="manage_score_ml"):
                import subprocess
                env = os.environ.copy()
                env["DATABASE_URL"] = DB_URL
                env["DYLD_LIBRARY_PATH"] = os.path.expanduser("~/lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
                ml_path = os.path.join(os.path.dirname(__file__), "engine", "scoring_ml.py")
                with st.spinner("Running propensity models…"):
                    result = subprocess.run([sys.executable, ml_path], capture_output=True, text=True, timeout=120, env=env)
                if result.returncode == 0:
                    load_scored.clear()
                    st.success("✅ Propensity scores updated.")
                else:
                    st.error(f"❌ {result.stderr[-500:]}")


if st.session_state.page == "login":
    page_login()
elif st.session_state.page == "dashboard":
    page_dashboard()
elif st.session_state.page == "segments":
    page_segments()
