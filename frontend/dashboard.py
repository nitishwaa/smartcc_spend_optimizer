# frontend/dashboard.py
# Entry point for the SmartCC Advisor Streamlit dashboard.
# Run from project root: streamlit run frontend/dashboard.py

import sys
import os

# Ensure project root is in the import path so `backend.*` resolves correctly.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import subprocess
import json
import yaml
import pandas as pd
import streamlit as st

from frontend.components.styles import CSS_BLOCK, fmt_inr, kpi_card
from frontend.components        import analysis, by_card, savings_advisor, raw_data

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartCC Advisor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS_BLOCK, unsafe_allow_html=True)

# ─── Data Loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    path = os.path.join(_PROJECT_ROOT, "data", "transactions.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["date"]  = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df

@st.cache_data(ttl=300)
def load_config_data():
    path = os.path.join(_PROJECT_ROOT, "config.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💳 SmartCC Advisor")
    st.markdown("---")

    st.markdown('<div class="section-header">Fetch New Data</div>', unsafe_allow_html=True)
    days_fetch = st.slider("Days to fetch", 7, 180, 90, step=7)

    if st.button("🔄 Run Parser", use_container_width=True, type="primary"):
        script = os.path.join(_PROJECT_ROOT, "backend", "email_reader.py")
        with st.spinner("Connecting to Gmail and fetching emails…"):
            try:
                result = subprocess.run(
                    [sys.executable, script, "--days", str(days_fetch)],
                    capture_output=True, text=True, timeout=300,
                    cwd=_PROJECT_ROOT,
                )
                if result.returncode == 0:
                    st.success("✅ Fetch complete!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Parser failed:")
                    st.code(result.stderr[-2000:])
            except subprocess.TimeoutExpired:
                st.error("Timed out after 5 minutes.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    df_raw = load_data()
    if df_raw is None:
        st.warning("No data yet.\n\nClick **Run Parser** to fetch emails.")
        st.stop()

    st.markdown('<div class="section-header">Time Period</div>', unsafe_allow_html=True)
    period_map = {"Last 1 Month": 30, "Last 2 Months": 60, "Last 3 Months": 90, "Last 6 Months": 180}
    selected_period = st.radio("Time period", list(period_map.keys()), index=2,
                               label_visibility="collapsed")
    days   = period_map[selected_period]
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)

    st.markdown('<div class="section-header">Cards</div>', unsafe_allow_html=True)
    all_cards    = sorted(df_raw["card_name"].dropna().unique().tolist())
    card_option  = st.radio("Card filter", ["All Cards", "Select Cards"], index=0,
                            label_visibility="collapsed")
    selected_cards = all_cards
    if card_option == "Select Cards":
        selected_cards = st.multiselect("Select cards", all_cards, default=all_cards[:1],
                                        label_visibility="collapsed") or all_cards

    st.markdown('<div class="section-header">Transaction Type</div>', unsafe_allow_html=True)
    show_types = st.multiselect("Transaction types", ["PURCHASE", "EMI", "CASH_ADVANCE"],
                                default=["PURCHASE"], label_visibility="collapsed")

    st.markdown("---")
    st.caption(
        f"Data: {df_raw['date'].min().strftime('%d %b %Y')} – "
        f"{df_raw['date'].max().strftime('%d %b %Y')}"
    )
    st.caption(f"{len(df_raw)} total transactions")

# ─── Filter ────────────────────────────────────────────────────────────────────
df = df_raw[
    (df_raw["date"] >= cutoff) &
    (df_raw["card_name"].isin(selected_cards)) &
    (df_raw["type"].isin(show_types) if show_types else True)
].copy()

if df.empty:
    st.warning("No transactions match your filters.")
    st.stop()

spend_df = df[df["type"] == "PURCHASE"]

# ─── Page Header + KPIs ────────────────────────────────────────────────────────
card_label = ", ".join(selected_cards) if len(selected_cards) <= 3 else f"{len(selected_cards)} cards"
st.markdown(f"""
<div style="padding:0.25rem 0 1.5rem 0">
    <div style="font-size:1.9rem;font-weight:800;color:#0f172a;letter-spacing:-0.03em;line-height:1.1">
        Spending Analysis&nbsp;
        <span style="background:linear-gradient(90deg,#0d9488,#06b6d4);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                     background-clip:text">{selected_period}</span>
    </div>
    <div style="font-size:0.85rem;color:#94a3b8;margin-top:0.4rem">
        {len(df)} transactions &nbsp;·&nbsp; {card_label}
    </div>
</div>
""", unsafe_allow_html=True)

total_spend = spend_df["amount"].sum()
avg_txn     = spend_df["amount"].mean() if len(spend_df) else 0
top_cat     = spend_df.groupby("category")["amount"].sum().idxmax() if len(spend_df) else "—"
online_pct  = (
    spend_df[spend_df["channel"] == "online"]["amount"].sum() / total_spend * 100
    if total_spend else 0
)

k1, k2, k3, k4 = st.columns(4)
for col, label, value, sub in [
    (k1, "Total Spend",         fmt_inr(total_spend), f"{len(spend_df)} purchases"),
    (k2, "Avg per Transaction", fmt_inr(avg_txn),     f"across {len(spend_df)} txns"),
    (k3, "Top Category",        top_cat,
          fmt_inr(spend_df[spend_df["category"] == top_cat]["amount"].sum()) if top_cat != "—" else "—"),
    (k4, "Online Spend",        f"{online_pct:.0f}%", "of total purchases"),
]:
    with col:
        st.markdown(kpi_card(label, value, sub), unsafe_allow_html=True)

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Analysis",
    "💳  By Card",
    "💰  Savings Advisor",
    "🗒️  Raw Data",
])

with tab1:
    analysis.render(spend_df)

with tab2:
    by_card.render(spend_df, selected_cards)

with tab3:
    cfg = load_config_data()
    savings_advisor.render(spend_df, cfg)

with tab4:
    raw_data.render(df, selected_period)
