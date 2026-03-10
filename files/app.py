"""
SmartRewards — Albertsons Loyalty Demo
Streamlit UI: Customer Login → Profile → Personalised Offers → Segment Explorer
Run: streamlit run files/app.py
"""

import base64
import json
import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ─── CONFIG ──────────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
_engine = create_engine(DB_URL, pool_pre_ping=True)

def _logo_b64() -> str:
    with open(os.path.join(STATIC_DIR, "logo.svg"), "rb") as f:
        return base64.b64encode(f.read()).decode()

LOGO_B64 = _logo_b64()

st.set_page_config(
    page_title="SmartRewards | Albertsons",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── BRANDING ─────────────────────────────────────────────────────────────────

BLUE  = "#00529B"
RED   = "#E31837"
LIGHT = "#F0F4FA"

st.markdown(f"""
<style>
    /* Global */
    html, body, [class*="css"] {{ font-family: 'Segoe UI', sans-serif; }}
    .main {{ background-color: #FFFFFF; }}

    /* Header bar */
    .abs-header {{
        background: {BLUE};
        padding: 18px 32px;
        border-radius: 10px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
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

    /* Channel pills */
    .pill-j4u       {{ background:#D6EAF8; color:#1A5276; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-weeklyadd {{ background:#D1F2EB; color:#1A7A5E; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-autoclip  {{ background:#EDE7F6; color:#4A235A; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
    .pill-other     {{ background:#FFF3CD; color:#856404; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}

    /* Score bar */
    .score-bar-bg {{ background:#EEF2F7; border-radius:6px; height:10px; margin-top:6px; }}
    .score-bar-fill {{ height:10px; border-radius:6px; background: linear-gradient(90deg, {BLUE}, {RED}); }}

    /* Segment cards */
    .seg-card {{
        background: {LIGHT};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }}
    .seg-number {{ font-size: 2.2rem; font-weight: 800; color: {BLUE}; }}
    .seg-label  {{ color: #555; font-size: 0.9rem; }}

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
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    section[data-testid="stSidebar"] .stRadio label {{ color: white !important; }}

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
            cp.churn_segment_cd, cp.gas_rewards_ind_6m, cp.dairy_purchase_ind_6m,
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
            (o.end_dt - CURRENT_DATE)::int              AS days_left
        FROM c360_scored_offers so
        JOIN c360_offer o ON o.client_offer_id = so.client_offer_id
        ORDER BY so.household_id, so.rank
    """, _engine)


def load_model_metadata() -> dict:
    meta_path = os.path.join(os.path.dirname(__file__), "engine", "model_metadata.json")
    try:
        with open(meta_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


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


# ─── SESSION STATE ────────────────────────────────────────────────────────────

if "household_id" not in st.session_state:
    st.session_state.household_id = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "clipped_offers" not in st.session_state:
    # { household_id: [client_offer_id, ...] }
    st.session_state.clipped_offers = {}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def channel_pill(channel: str) -> str:
    mapping = {
        "J4U":        ("pill-j4u",       "for U App"),
        "Weekly Ad":  ("pill-weeklyadd", "Weekly Ad"),
        "Auto Clip":  ("pill-autoclip",  "Auto Clip"),
    }
    css, label = mapping.get(channel, ("pill-other", channel))
    return f'<span class="{css}">{label}</span>'


def tier_badge(tier: str) -> str:
    if tier == "4U+":
        return '<span class="badge-4u">★ for U+</span>'
    return '<span class="badge-standard">Standard</span>'


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
    st.html(f"""
    <div class="login-box">
        <img src="data:image/svg+xml;base64,{LOGO_B64}" width="180" style="margin-bottom:16px;"/>
        <p style="color:#888; margin-bottom:28px; font-size:0.95rem;">Personalised Loyalty Offer Engine</p>
    </div>
    """)

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("### Sign in to your account")
        st.caption("Select a household to continue — no password required for demo")

        display = customers_df.apply(
            lambda r: (
                f"{r['household_id']}  |  {r['clv_tier_level_id']}  |  "
                f"{r['fav_channel']}  |  {r['current_point_balance']:,} pts"
            ),
            axis=1
        )
        options = ["— Select a customer —"] + display.tolist()
        choice = st.selectbox("Customer", options, label_visibility="collapsed")

        if st.button("Sign In", width="stretch", type="primary"):
            if choice == "— Select a customer —":
                st.warning("Please select a customer to continue.")
            else:
                hid = choice.split("|")[0].strip()
                st.session_state.household_id = hid
                st.session_state.page = "dashboard"
                st.rerun()

        st.markdown("---")
        if st.button("Explore Customer Segments", width="stretch"):
            st.session_state.page = "segments"
            st.rerun()


# ─── PAGE: DASHBOARD ──────────────────────────────────────────────────────────

def page_dashboard():
    hid      = st.session_state.household_id
    customer = customers_df[customers_df["household_id"] == hid].iloc[0].to_dict()

    with st.sidebar:
        st.markdown(f"## 🛒 SmartRewards")

        # Customer switcher
        all_options = customers_df.apply(
            lambda r: (
                r["household_id"],
                f"{r['household_id']}  |  {r['clv_tier_level_id']}  |  {r['full_name']}"
            ), axis=1
        ).tolist()
        hid_to_label = {h: l for h, l in all_options}
        current_idx = next((i for i, (h, _) in enumerate(all_options) if h == hid), 0)
        selected_label = st.selectbox(
            "Switch Customer",
            options=[l for _, l in all_options],
            index=current_idx,
            label_visibility="collapsed"
        )
        selected_hid = next(h for h, l in all_options if l == selected_label)
        if selected_hid != hid:
            st.session_state.household_id = selected_hid
            st.rerun()

        st.caption(f"Tier: **{customer['clv_tier_level_id']}**")
        clipped_count = len(get_clipped(hid))
        if clipped_count:
            st.markdown(f"✂️ **{clipped_count} offer{'s' if clipped_count > 1 else ''} clipped**")
        st.markdown("---")
        nav = st.radio(
            "Navigate",
            ["My Offers", "My Rewards", "My Clipped Offers", "My Profile", "Segment Explorer",
             "Compare Customers", "Compare Models", "How Offers Are Scored", "Demo Script"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        if st.button("Sign Out"):
            logout()
            st.rerun()

    st.html(f"""
    <div class="abs-header">
        <img src="data:image/svg+xml;base64,{LOGO_B64}" height="40"/>
        <span style="color:#A8C8F0; font-size:0.9rem;">Personalised Offers Engine &nbsp;|&nbsp; <i>for U</i> Loyalty Program</span>
    </div>
    """)

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
    elif nav == "How Offers Are Scored":
        render_allocation_criteria()
    elif nav == "Demo Script":
        render_demo_script()
    else:
        render_segments()


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
    st.subheader("My Personalised Offers")

    # Model toggle
    model_choice = st.radio(
        "Scoring model",
        ["📋 Rule-Based", "🤖 Propensity (XGBoost)"],
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_model = "rule_based" if "Rule-Based" in model_choice else "propensity"

    if selected_model == "propensity":
        meta = load_model_metadata()
        if meta:
            st.html(f"""
            <div style="background:#EEF2FF; border:1px solid #C7D2FE; border-radius:8px;
                        padding:10px 16px; margin-bottom:12px; font-size:0.85rem;">
                🤖 <b>XGBoost Propensity Model</b> &nbsp;|&nbsp;
                Trained on <b>{meta.get('n_train', '—')}</b> clip events
                ({meta.get('n_pos', '—')} redeemed / {meta.get('n_neg', '—')} not redeemed)
                &nbsp;|&nbsp; CV AUC: <b>{meta.get('auc_cv', '—')}</b>
                &nbsp;|&nbsp; Top signals:
                <b>{', '.join(f[0].replace('_', ' ') for f in meta.get('top_features', [])[:3])}</b>
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
        top_n = st.slider("Number of Offers", min_value=1, max_value=10, value=5)
    with col3:
        show_scores = st.toggle("Show Score Breakdown", value=False,
                                disabled=(selected_model == "propensity"))

    cust_offers = scored_df[
        (scored_df["household_id"] == hid) &
        (scored_df["model_type"] == selected_model) &
        (scored_df["program_type"] != "Grocery Reward")
    ].copy()
    if channel_filter != "All Channels":
        cust_offers = cust_offers[cust_offers["delivery_channel_cd"] == channel_filter]
    cust_offers = cust_offers.sort_values("score", ascending=False).head(top_n)

    if cust_offers.empty:
        st.info("No offers found for the selected filters.")
        return

    st.markdown(f"Showing **{len(cust_offers)}** personalised offers for **{hid}**")
    st.markdown("")

    for i, (_, row) in enumerate(cust_offers.iterrows(), start=1):
        offer_id   = row["client_offer_id"]
        gr         = is_grocery_reward(row)
        clipped    = is_clipped(hid, offer_id)
        n_clipped  = clip_count(hid, offer_id)

        boosts = []
        if row["recency_boost_applied"]:
            boosts.append("⚡ Recency Boost")
        if row["tier_multiplier_applied"]:
            boosts.append("★ for U+ Boost")
        boost_html = "  &nbsp;".join(
            [f'<span style="color:{RED}; font-size:0.8rem; font-weight:600;">{b}</span>' for b in boosts]
        )

        days_left = int(row["days_left"]) if row["days_left"] is not None else None
        if days_left is not None and days_left <= 3:
            expiry_html = f'<span style="background:#FEE2E2; color:#991B1B; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:10px;">⏰ Expires in {days_left}d</span>'
        elif days_left is not None and days_left <= 7:
            expiry_html = f'<span style="background:#FEF3C7; color:#92400E; font-size:0.75rem; font-weight:600; padding:2px 8px; border-radius:10px;">Expires in {days_left}d</span>'
        else:
            expiry_html = ""

        clipped_html = (
            f'<span style="color:#1A7A5E; font-size:0.8rem; font-weight:700;">✂️ Clipped'
            + (f' ×{n_clipped}' if n_clipped > 1 else '')
            + ' — Active at checkout</span>'
        ) if clipped else ""

        card_col, btn_col = st.columns([5, 1])
        with card_col:
            st.html(f"""
            <div class="offer-card" style="{'border-color:#1A7A5E; background:#F0FBF6;' if clipped else ''}">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <span class="offer-rank">#{i}</span>&nbsp;&nbsp;
                        <span class="offer-name">{row['offer_dsc']}</span>
                        &nbsp;&nbsp;{channel_pill(row['delivery_channel_cd'])}
                        &nbsp;&nbsp;{boost_html}
                    </div>
                    <div style="text-align:right;">
                        <span class="offer-discount">{format_discount(row['discount_value'], row['discount_type_cd'])}</span><br>
                        <span style="color:#888; font-size:0.8rem;">Score: <b>{row['score']}</b> / 100</span>
                    </div>
                </div>
                <div style="color:#888; font-size:0.82rem; margin-top:6px;">
                    Channel: <b>{row['delivery_channel_cd']}</b>
                    {'&nbsp;&nbsp;<span style="color:#856404; font-size:0.78rem;">&#9733; Multiple clips allowed</span>' if gr else ''}
                    {'&nbsp;&nbsp;' + expiry_html if expiry_html else ''}
                </div>
                {score_bar(row['score'])}
                <div style="margin-top:8px;">{clipped_html}</div>
            </div>
            """)

        with btn_col:
            st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
            if clipped:
                if st.button("Unclip", key=f"unclip_{hid}_{offer_id}_{i}", width="stretch"):
                    unclip_offer_local(hid, offer_id)
                    st.rerun()
            if gr or not clipped:
                btn_label = "Clip ✂️" if not clipped else "Clip again ✂️"
                if st.button(btn_label, key=f"clip_{hid}_{offer_id}_{i}", width="stretch", type="primary"):
                    clip_offer_local(hid, offer_id, gr)
                    st.rerun()

        if show_scores:
            with st.expander(f"Score breakdown — {row['offer_dsc']}"):
                labels = {
                    "transaction_affinity": ("Transaction Affinity", "30%", "Historical spend in this category"),
                    "redemption_match":     ("Redemption Match",     "25%", "Channel alignment with your preference"),
                    "points_eligibility":   ("Points Eligibility",   "20%", "You have enough points to benefit"),
                    "cart_affinity":        ("Cart / Browse Affinity","15%", "Based on your online shopping activity"),
                    "demographic_match":    ("Demographic Match",    "10%", "Profile fit for this offer type"),
                }
                for key, (label, weight, desc) in labels.items():
                    val = float(row[key])
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{label}** — *{desc}*")
                    c2.markdown(f"Weight: `{weight}`")
                    c3.progress(val, text=f"{val:.2f}")

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

    gr_df = load_gr_offers(balance)
    if gr_df.empty:
        st.info("You don't have enough points for any Grocery Rewards yet. Keep shopping to earn points!")
        return

    ALL_TIERS = [100, 200, 300, 400, 500, 700, 1000, 1200]
    eligible_tiers = sorted(gr_df["pts_threshold"].unique().tolist())

    # Tier tab labels
    tab_labels = [f"{t} pts" for t in eligible_tiers]
    tabs = st.tabs(tab_labels)

    for tab, tier in zip(tabs, eligible_tiers):
        with tab:
            tier_offers = gr_df[gr_df["pts_threshold"] == tier]
            basket  = tier_offers[tier_offers["discount_type_cd"] == "GROCERY_REWARD"]
            dept    = tier_offers[tier_offers["discount_type_cd"] == "DEPT_REWARD"]
            free    = tier_offers[tier_offers["discount_type_cd"] == "FREE_ITEM"]

            # ── Basket & Dept discounts ───────────────────────────────────────
            disc_rows = pd.concat([basket, dept])
            if not disc_rows.empty:
                cols = st.columns(min(len(disc_rows), 3))
                for col, (_, row) in zip(cols, disc_rows.iterrows()):
                    disc_type = row["discount_type_cd"]
                    badge_color = "#DC2626" if disc_type == "GROCERY_REWARD" else "#1D4ED8"
                    badge_label = f"${row['discount_value']:.0f} OFF"
                    dept_note = f"Any {row['category']} Purchase" if disc_type == "DEPT_REWARD" else "Your Next Purchase"
                    days_left = int(row["days_left"]) if row["days_left"] is not None else None
                    expiry = f'<span style="font-size:0.72rem; color:#6B7280;">Expires in {days_left}d</span>' if days_left and days_left <= 14 else ""
                    with col:
                        st.html(f"""
                        <div style="border:1.5px solid #E5E7EB; border-radius:12px; padding:16px;
                                    background:#fff; min-height:160px;">
                            <div style="color:{badge_color}; font-size:1rem; font-weight:800;
                                        margin-bottom:6px;">{badge_label}</div>
                            <div style="font-size:0.88rem; font-weight:600; color:#111827;">{dept_note}</div>
                            <div style="font-size:0.78rem; color:#6B7280; margin-top:4px;">
                                of ${row['discount_value']:.0f} or more.*
                            </div>
                            {expiry}
                        </div>
                        """)
                        st.button(f"Use {tier} pts", key=f"gr_disc_{hid}_{tier}_{row['client_offer_id']}",
                                  use_container_width=True, type="primary",
                                  on_click=clip_offer_local, args=(hid, row["client_offer_id"], True, tier))

            # ── Free items ────────────────────────────────────────────────────
            if not free.empty:
                if not disc_rows.empty:
                    st.markdown("##### Free Items")
                free_cols = st.columns(3)
                for idx, (_, row) in enumerate(free.iterrows()):
                    days_left = int(row["days_left"]) if row["days_left"] is not None else None
                    expiry = f'<span style="font-size:0.72rem; color:#6B7280;">Expires in {days_left}d</span>' if days_left and days_left <= 14 else ""
                    col = free_cols[idx % 3]
                    with col:
                        st.html(f"""
                        <div style="border:1.5px solid #E5E7EB; border-radius:12px; padding:16px;
                                    background:#fff; min-height:160px;">
                            <div style="color:#DC2626; font-size:1rem; font-weight:800;
                                        margin-bottom:6px;">FREE</div>
                            <div style="font-size:0.85rem; font-weight:600; color:#111827; line-height:1.3;">
                                {row['offer_dsc'].replace(f' — {tier} pts', '').replace(f'FREE ', '')}
                            </div>
                            <div style="font-size:0.75rem; color:#6B7280; margin-top:4px;">Limit 1.</div>
                            {expiry}
                        </div>
                        """)
                        st.button(f"Use {tier} pts", key=f"gr_free_{hid}_{tier}_{row['client_offer_id']}",
                                  use_container_width=True, type="primary",
                                  on_click=clip_offer_local, args=(hid, row["client_offer_id"], True, tier))


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

    col_rb, col_ml = st.columns(2)

    with col_rb:
        st.html("""<div style="background:#F0F9FF; border:1px solid #BAE6FD;
                    border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <b>📋 Rule-Based Engine</b><br>
                    <span style="font-size:0.82rem; color:#555;">
                    5 manually-weighted rules. No learning from data.
                    Same weights for every customer.</span></div>""")

        rb_offers = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "rule_based")
        ].sort_values("rank")

        for _, row in rb_offers.iterrows():
            st.html(f"""
            <div style="padding:8px 12px; margin-bottom:6px; border-radius:6px;
                        background:#F8FAFC; border:1px solid #E2E8F0;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#64748B; font-size:0.78rem; font-weight:700;">
                        #{int(row['rank'])}</span>
                    &nbsp;<span style="font-size:0.88rem;">{row['offer_dsc']}</span>
                    &nbsp;{channel_pill(row['delivery_channel_cd'])}
                </div>
                <span style="font-weight:700; color:{BLUE}; font-size:0.9rem;">
                    {row['score']:.1f}</span>
            </div>""")

    with col_ml:
        auc_txt = f"CV AUC: {meta['auc_cv']}" if meta else ""
        st.html(f"""<div style="background:#F5F3FF; border:1px solid #DDD6FE;
                    border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <b>🤖 Propensity Model (XGBoost)</b><br>
                    <span style="font-size:0.82rem; color:#555;">
                    Trained on {meta.get('n_train','—')} clip events. {auc_txt}.
                    Learns patterns the rules can't capture.</span></div>""")

        ml_offers = scored_df[
            (scored_df["household_id"] == hid) &
            (scored_df["model_type"] == "propensity")
        ].sort_values("rank")

        # Build rank lookup from rule-based for delta display
        rb_rank = {row["client_offer_id"]: int(row["rank"])
                   for _, row in rb_offers.iterrows()}

        for _, row in ml_offers.iterrows():
            oid = row["client_offer_id"]
            ml_rank = int(row["rank"])
            rb_r = rb_rank.get(oid)
            if rb_r is not None:
                delta = rb_r - ml_rank
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
                        background:#FAF5FF; border:1px solid #E9D5FF;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#7C3AED; font-size:0.78rem; font-weight:700;">
                        #{ml_rank}</span>
                    &nbsp;<span style="font-size:0.88rem;">{row['offer_dsc']}</span>
                    &nbsp;{channel_pill(row['delivery_channel_cd'])}
                    &nbsp;{delta_html}
                </div>
                <span style="font-weight:700; color:#7C3AED; font-size:0.9rem;">
                    {row['score']:.1f}</span>
            </div>""")

    if meta and meta.get("top_features"):
        st.markdown("---")
        st.markdown("#### 🔍 What XGBoost learned — top feature importances")
        cols = st.columns(len(meta["top_features"][:6]))
        for col, (feat, imp) in zip(cols, meta["top_features"][:6]):
            col.metric(feat.replace("_", " ").title(), f"{imp:.3f}")

    st.markdown("---")
    st.caption(
        "▲ green = ranked higher by propensity model vs rule-based &nbsp;|&nbsp;"
        "▼ red = ranked lower &nbsp;|&nbsp; — = same rank"
    )


def render_comparison(current_hid: str):
    st.subheader("Compare Customers")
    st.caption("Select two households to compare their profiles and personalised offers side by side.")

    all_hids = customers_df["household_id"].tolist()
    col1, col2 = st.columns(2)
    with col1:
        hid_a = st.selectbox("Customer A", all_hids,
                             index=all_hids.index(current_hid), key="compare_a")
    with col2:
        default_b = all_hids[1] if all_hids[0] == hid_a else all_hids[0]
        hid_b = st.selectbox("Customer B", all_hids,
                             index=all_hids.index(default_b), key="compare_b")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.html(f'<div class="compare-header">{hid_a}</div>')
        st.html(_customer_summary_html(hid_a))
    with col_b:
        st.html(f'<div class="compare-header">{hid_b}</div>')
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
        "tag": "Overview",
        "title": "SmartRewards — What It Does",
        "narration": (
            "SmartRewards is an AI-powered personalised offer engine built on top of Albertsons' "
            "for U loyalty program. It scores every customer-offer pair using 5 weighted rules — "
            "transaction history, channel alignment, points eligibility, browsing behaviour, and "
            "demographic fit — and returns a ranked list of the most relevant offers per household."
        ),
        "customer": None,
        "highlight": "stats",
    },
    {
        "tag": "Scoring Engine",
        "title": "How Offers Are Scored",
        "narration": (
            "Before we look at individual customers, here's the engine underneath. "
            "Every customer-offer pair is scored using 5 weighted rules — transaction history, "
            "channel alignment, points eligibility, browsing behaviour, and demographic fit. "
            "Multipliers then boost the score for recent shoppers and premium tier members. "
            "Business rules apply on top to handle edge cases like the eCommerce nudge and FreshPass targeting."
        ),
        "customer": None,
        "highlight": "criteria",
    },
    {
        "tag": "Story 1 of 2",
        "title": "Meet a Fuel Redeemer",
        "narration": (
            "This household primarily redeems at Fuel stations — a typical offline loyalist. "
            "They have a solid points balance but have never shopped online. "
            "SmartRewards' goal: nudge them toward eCommerce without abandoning their Fuel habit."
        ),
        "customer": "fuel",
        "highlight": "profile",
    },
    {
        "tag": "Story 1 of 2",
        "title": "The eCommerce Nudge in Action",
        "narration": (
            "Notice that J4U digital offers appear in the top recommendations despite this being a Fuel customer. "
            "That's intentional — the engine gives a partial score to digital offers for Fuel redeemers, "
            "enough to surface them without completely overriding their natural preferences. "
            "This is the migration strategy: show relevant online offers, let the customer discover them."
        ),
        "customer": "fuel",
        "highlight": "offers",
    },
    {
        "tag": "Story 2 of 2",
        "title": "Meet a for U+ Subscriber",
        "narration": (
            "This is a premium for U+ member — Albertsons' highest loyalty tier. "
            "They get access to exclusive offers unavailable to Standard members, "
            "and a 1.5× tier multiplier that boosts their scores significantly. "
            "These customers are the highest-value segment and the primary target for SmartRewards."
        ),
        "customer": "premium",
        "highlight": "profile",
    },
    {
        "tag": "Story 2 of 2",
        "title": "The Tier Multiplier Effect",
        "narration": (
            "Watch how scores for exclusive offers jump significantly for for U+ members. "
            "The 1.5× tier multiplier rewards loyalty and creates a clear incentive to upgrade. "
            "Offers marked with ★ for U+ Boost are exclusive to this tier — "
            "a tangible benefit that Standard members can see but not access."
        ),
        "customer": "premium",
        "highlight": "offers",
    },
    {
        "tag": "Head-to-Head",
        "title": "Side-by-Side Comparison",
        "narration": (
            "Here's the clearest way to see SmartRewards at work: the same offer catalog, "
            "two very different customers, two completely different ranked results. "
            "The engine personalises at the household level — not the segment level. "
            "Every household gets a unique ranked list based on their own behaviour."
        ),
        "customer": "both",
        "highlight": "compare",
    },
]

if "demo_step" not in st.session_state:
    st.session_state.demo_step = 0


def render_demo_script():
    step_idx = st.session_state.demo_step
    step     = DEMO_STEPS[step_idx]
    total    = len(DEMO_STEPS)

    st.html(f"""
    <div class="demo-step">
        <div class="step-tag">Step {step_idx + 1} of {total} &nbsp;·&nbsp; {step['tag']}</div>
        <h3>{step['title']}</h3>
        <p>{step['narration']}</p>
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

    # Pick demo personas
    fuel_rows = customers_df[customers_df["gas_rewards_ind_6m"] == True]
    premium_rows = customers_df[customers_df["clv_tier_level_id"] == "4U+"]
    fuel_cust    = fuel_rows.iloc[0].to_dict() if not fuel_rows.empty else customers_df.iloc[0].to_dict()
    premium_cust = premium_rows.iloc[0].to_dict() if not premium_rows.empty else customers_df.iloc[1].to_dict()

    highlight = step["highlight"]
    customer  = step["customer"]

    if highlight == "criteria":
        render_allocation_criteria()

    elif highlight == "stats":
        fuel_count    = int(customers_df["gas_rewards_ind_6m"].sum())
        premium_count = len(customers_df[customers_df["clv_tier_level_id"] == "4U+"])
        high_pts      = len(customers_df[customers_df["current_point_balance"] >= 1000])
        avg_score     = scored_df["score"].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Households",    f"{len(customers_df):,}")
        c2.metric("Fuel Redeemers",      f"{fuel_count}")
        c3.metric("for U+ Subscribers",  f"{premium_count}")
        c4.metric("Avg Offer Score",      f"{avg_score:.1f}")
        st.markdown("")
        c5, c6 = st.columns(2)
        c5.metric("Offers in Catalog",   f"{len(offers_df)}")
        c6.metric("High Points (1000+)", f"{high_pts}")

    elif highlight == "profile":
        cust = fuel_cust if customer == "fuel" else premium_cust
        render_profile(cust)

    elif highlight == "offers":
        cust = fuel_cust if customer == "fuel" else premium_cust
        render_offers(cust, cust["household_id"])

    elif highlight == "compare":
        hid_a = fuel_cust["household_id"]
        hid_b = premium_cust["household_id"]

        col_a, col_b = st.columns(2)
        with col_a:
            st.html(f'<div class="compare-header">⛽ {hid_a} — Fuel Redeemer</div>')
            st.html(_customer_summary_html(hid_a))
        with col_b:
            st.html(f'<div class="compare-header">★ {hid_b} — for U+ Subscriber</div>')
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
        "household_id", "clv_tier_level_id", "current_point_balance",
        "fav_channel", "days_since_last_txn", "customer_age", "churn_segment_cd"
    ]].rename(columns={
        "household_id":          "Household ID",
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
    pick = st.selectbox("Select household", seg_df["Household ID"].tolist())
    if st.button("View their offers", type="primary"):
        st.session_state.household_id = pick
        st.session_state.page = "dashboard"
        st.rerun()


def page_segments():
    with st.sidebar:
        st.markdown("## 🛒 SmartRewards")
        st.markdown("---")
        if st.button("← Back to Login"):
            st.session_state.page = "login"
            st.rerun()

    st.html(f"""
    <div class="abs-header">
        <img src="data:image/svg+xml;base64,{LOGO_B64}" height="40"/>
        <span style="color:#A8C8F0; font-size:0.9rem;">Segment Explorer</span>
    </div>
    """)

    render_segments()


# ─── ROUTER ───────────────────────────────────────────────────────────────────

if st.session_state.page == "login":
    page_login()
elif st.session_state.page == "dashboard":
    page_dashboard()
elif st.session_state.page == "segments":
    page_segments()
