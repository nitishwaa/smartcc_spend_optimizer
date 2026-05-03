# dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import subprocess
import json
import os
import sys
from datetime import datetime

# ─── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="CC Advisor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background: #1c1b19; border-right: 1px solid #262523; }
    [data-testid="stSidebar"] * { color: #cdccca !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stRadio label {
        color: #7a7974 !important; font-size: 0.75rem !important;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    .kpi-card {
        background: #f9f8f5; border: 1px solid #dcd9d5;
        border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 0.5rem;
    }
    .kpi-label { font-size: 0.75rem; color: #7a7974; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
    .kpi-value { font-size: 1.75rem; font-weight: 700; color: #28251d; line-height: 1.2; }
    .kpi-sub   { font-size: 0.8rem; color: #7a7974; margin-top: 0.25rem; }
    .section-header {
        font-size: 0.7rem; font-weight: 600; color: #7a7974;
        text-transform: uppercase; letter-spacing: 0.08em;
        margin: 1.5rem 0 0.75rem 0;
        border-bottom: 1px solid #dcd9d5; padding-bottom: 0.5rem;
    }
    .txn-row {
        display: flex; align-items: center;
        padding: 0.6rem 0; border-bottom: 1px solid #f3f0ec; font-size: 0.875rem;
    }
    .txn-merchant { font-weight: 500; color: #28251d; flex: 2; }
    .txn-meta     { color: #7a7974; flex: 1; font-size: 0.8rem; }
    .txn-amount   { font-weight: 600; color: #28251d; text-align: right; flex: 1; }
    .txn-badge    { font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; font-weight: 500; }
    .badge-food         { background: #fef3c7; color: #92400e; }
    .badge-shopping     { background: #dbeafe; color: #1e40af; }
    .badge-transport    { background: #d1fae5; color: #065f46; }
    .badge-fuel         { background: #fee2e2; color: #991b1b; }
    .badge-entertainment{ background: #ede9fe; color: #5b21b6; }
    .badge-utilities    { background: #f3f4f6; color: #374151; }
    .badge-health       { background: #fce7f3; color: #9d174d; }
    .badge-travel       { background: #cffafe; color: #155e75; }
    .badge-other        { background: #f3f0ec; color: #7a7974; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #dcd9d5; }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.8rem; font-weight: 500; color: #7a7974;
        background: transparent; border: none; padding: 0.5rem 1rem;
    }
    .stTabs [aria-selected="true"] { color: #01696f !important; border-bottom: 2px solid #01696f !important; }
    [data-testid="stDataFrame"] { border: 1px solid #dcd9d5; border-radius: 12px; overflow: hidden; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ─────────────────────────────────────────────
TEAL   = '#01696f'
COLORS = ['#01696f','#437a22','#006494','#7a39bb','#da7101','#a12c7b','#d19900','#a13544']
CATEGORY_BADGE = {
    'Food & Dining': 'badge-food', 'Online Shopping': 'badge-shopping',
    'Grocery': 'badge-shopping', 'Transport': 'badge-transport',
    'Fuel': 'badge-fuel', 'Entertainment': 'badge-entertainment',
    'Utilities & Bills': 'badge-utilities', 'Health': 'badge-health',
    'Travel': 'badge-travel', 'Cash Advance': 'badge-other', 'Other': 'badge-other',
}

def fmt_inr(amount): return f"₹{amount:,.0f}"

def apply_theme(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#28251d'),
        margin=dict(t=60, b=40, l=40, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor='#f3f0ec', tickfont=dict(size=11))
    return fig

# ─── Data Loader ───────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    path = 'data/transactions.json'
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['date']  = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    return df

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💳 CC Advisor")
    st.markdown("---")

    # ── Fetch Button ──────────────────────────────────────
    st.markdown('<div class="section-header">Fetch New Data</div>', unsafe_allow_html=True)
    days_fetch = st.slider("Days to fetch", 7, 180, 90, step=7)

    if st.button("🔄 Run Parser", use_container_width=True, type="primary"):
        with st.spinner("Connecting to Gmail and fetching emails..."):
            try:
                result = subprocess.run(
                    [sys.executable, 'part1_email_reader.py'],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    st.success("✅ Fetch complete!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Parser failed:")
                    st.code(result.stderr[-1000:])
            except subprocess.TimeoutExpired:
                st.error("Timed out after 5 minutes.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    df_raw = load_data()
    if df_raw is None:
        st.warning("No data yet.\n\nClick **Run Parser** above to fetch emails.")
        st.stop()

    # ── Filters ───────────────────────────────────────────
    st.markdown('<div class="section-header">Time Period</div>', unsafe_allow_html=True)
    period_map = {"Last 1 Month": 30, "Last 2 Months": 60, "Last 3 Months": 90, "Last 6 Months": 180}
    selected_period = st.radio("", list(period_map.keys()), index=2)
    days = period_map[selected_period]
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)

    st.markdown('<div class="section-header">Cards</div>', unsafe_allow_html=True)
    all_cards = sorted(df_raw['card_name'].dropna().unique().tolist())
    card_option = st.radio("", ["All Cards", "Select Cards"], index=0)
    selected_cards = all_cards
    if card_option == "Select Cards":
        selected_cards = st.multiselect("", all_cards, default=all_cards[:1]) or all_cards

    st.markdown('<div class="section-header">Transaction Type</div>', unsafe_allow_html=True)
    show_types = st.multiselect("", ['PURCHASE', 'EMI', 'CASH_ADVANCE'], default=['PURCHASE'])

    st.markdown("---")
    st.caption(f"Data: {df_raw['date'].min().strftime('%d %b %Y')} – {df_raw['date'].max().strftime('%d %b %Y')}")
    st.caption(f"{len(df_raw)} total transactions")

# ─── Filter ────────────────────────────────────────────────
df = df_raw[
    (df_raw['date'] >= cutoff) &
    (df_raw['card_name'].isin(selected_cards)) &
    (df_raw['type'].isin(show_types) if show_types else True)
].copy()

if df.empty:
    st.warning("No transactions match your filters.")
    st.stop()

spend_df = df[df['type'] == 'PURCHASE']

# ─── Header ────────────────────────────────────────────────
st.markdown(f"### Spending Analysis &nbsp;·&nbsp; {selected_period}", unsafe_allow_html=True)
card_label = ', '.join(selected_cards) if len(selected_cards) <= 3 else f'{len(selected_cards)} cards'
st.caption(f"{len(df)} transactions · {card_label}")

# ─── KPIs ──────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
total_spend = spend_df['amount'].sum()
avg_txn     = spend_df['amount'].mean() if len(spend_df) else 0
top_cat     = spend_df.groupby('category')['amount'].sum().idxmax() if len(spend_df) else "—"
online_pct  = (spend_df[spend_df['channel']=='online']['amount'].sum() / total_spend * 100) if total_spend else 0

for col, label, value, sub in [
    (k1, "Total Spend", fmt_inr(total_spend), f"{len(spend_df)} purchases"),
    (k2, "Avg per Transaction", fmt_inr(avg_txn), f"across {len(spend_df)} txns"),
    (k3, "Top Category", top_cat, fmt_inr(spend_df[spend_df['category']==top_cat]['amount'].sum()) if top_cat != "—" else "—"),
    (k4, "Online Spend", f"{online_pct:.0f}%", "of total purchases"),
]:
    with col:
        st.markdown(f'''<div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>''', unsafe_allow_html=True)

# ─── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊  Analysis", "💳  By Card", "🗒️  Raw Data"])

# ── Tab 1: Analysis ────────────────────────────────────────
with tab1:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown('<div class="section-header">Monthly Spend Trend</div>', unsafe_allow_html=True)
        monthly = spend_df.groupby('month')['amount'].sum().reset_index()
        monthly.columns = ['Month', 'Amount']
        fig = px.bar(monthly, x='Month', y='Amount', color_discrete_sequence=[TEAL])
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(showlegend=False, bargap=0.35)
        fig.update_yaxes(title_text="Spend (₹)", tickformat=",.0f")
        fig.update_xaxes(title_text="Month")
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Spend by Category</div>', unsafe_allow_html=True)
        cat_data = spend_df.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)
        top7 = cat_data.head(7)
        if len(cat_data) > 7:
            import pandas as _pd
            other = _pd.DataFrame([{'category': 'Other', 'amount': cat_data.iloc[7:]['amount'].sum()}])
            top7  = _pd.concat([top7, other], ignore_index=True)
        fig = px.pie(top7, values='amount', names='category', color_discrete_sequence=COLORS, hole=0.45)
        fig.update_traces(textposition='inside', textinfo='percent', textfont_size=12)
        fig.update_layout(showlegend=True, legend=dict(orientation='v', x=1.02, y=0.5))
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<div class="section-header">Online vs Offline by Month</div>', unsafe_allow_html=True)
        ch_data = spend_df.groupby(['month', 'channel'])['amount'].sum().reset_index()
        fig = px.bar(ch_data, x='month', y='amount', color='channel',
                     color_discrete_map={'online': TEAL, 'offline': '#da7101'}, barmode='stack')
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(bargap=0.35)
        fig.update_yaxes(title_text="Spend (₹)", tickformat=",.0f")
        fig.update_xaxes(title_text="Month")
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    with c4:
        st.markdown('<div class="section-header">Top 10 Merchants</div>', unsafe_allow_html=True)
        top_m = spend_df.groupby('merchant')['amount'].sum().nlargest(10).reset_index()
        top_m.columns = ['Merchant', 'Amount']
        fig = px.bar(top_m.sort_values('Amount'), x='Amount', y='Merchant',
                     orientation='h', color_discrete_sequence=[TEAL])
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title_text="Total (₹)", tickformat=",.0f")
        fig.update_yaxes(title_text="")
        st.plotly_chart(apply_theme(fig), use_container_width=True)

# ── Tab 2: By Card ─────────────────────────────────────────
with tab2:
    for card in selected_cards:
        card_df = spend_df[spend_df['card_name'] == card]
        if card_df.empty:
            continue
        card_total = card_df['amount'].sum()
        card_txns  = len(card_df)
        card_avg   = card_df['amount'].mean()
        st.markdown(f'''
        <div style="background:#f9f8f5;border:1px solid #dcd9d5;border-radius:12px;
                    padding:1rem 1.25rem;margin:0.75rem 0 0.5rem 0;">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-size:1rem;font-weight:700;color:#28251d">💳 {card}</div>
                    <div style="font-size:0.8rem;color:#7a7974">{card_txns} transactions · avg {fmt_inr(card_avg)}</div>
                </div>
                <div style="font-size:1.4rem;font-weight:700;color:#01696f">{fmt_inr(card_total)}</div>
            </div>
        </div>''', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            cat_b = card_df.groupby('category')['amount'].sum().reset_index()
            fig = px.bar(cat_b.sort_values('amount'), x='amount', y='category',
                         orientation='h', color_discrete_sequence=[TEAL])
            fig.update_traces(marker_cornerradius=4)
            fig.update_layout(showlegend=False, height=280, margin=dict(t=20,b=20,l=10,r=10),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(family='Inter', color='#28251d'))
            fig.update_xaxes(title_text="Spend (₹)", tickformat=",.0f", showgrid=False)
            fig.update_yaxes(title_text="", gridcolor='#f3f0ec')
            st.plotly_chart(fig, use_container_width=True)
        with cb:
            ch_b = card_df.groupby('channel')['amount'].sum().reset_index()
            fig = px.pie(ch_b, values='amount', names='channel',
                         color_discrete_map={'online': TEAL, 'offline': '#da7101'}, hole=0.5)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, height=280, margin=dict(t=20,b=20,l=10,r=10),
                              paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Inter', color='#28251d'))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")

# ── Tab 3: Raw Data ────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Transactions</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([3, 2, 1])
    with sc1:
        search = st.text_input("🔍 Search merchant", placeholder="e.g. Swiggy, Amazon...")
    with sc2:
        sort_by = st.selectbox("Sort by", ['date', 'amount', 'merchant', 'category'])
    with sc3:
        asc = st.selectbox("Order", ['↓ Desc', '↑ Asc']) == '↑ Asc'

    disp = df.copy()
    if search:
        disp = disp[disp['merchant'].str.contains(search, case=False, na=False)]
    disp = disp.sort_values(sort_by, ascending=asc)

    st.markdown(f"Showing **{len(disp)}** transactions")
    for _, row in disp.head(200).iterrows():
        badge = CATEGORY_BADGE.get(row.get('category', 'Other'), 'badge-other')
        ch_icon   = "🌐" if row.get('channel') == 'online' else "🏪"
        type_icon = "💳" if row.get('type') == 'PURCHASE' else ("📦" if row.get('type') == 'EMI' else "🏧")
        st.markdown(f'''
        <div class="txn-row">
            <div class="txn-merchant">{type_icon} {row["merchant"]}
                <span style="margin-left:8px" class="txn-badge {badge}">{row.get("category","Other")}</span>
            </div>
            <div class="txn-meta">{pd.to_datetime(row["date"]).strftime("%d %b %Y")}</div>
            <div class="txn-meta">{row.get("card_name","—")}</div>
            <div class="txn-meta">{ch_icon} {row.get("channel","—")}</div>
            <div class="txn-amount">{fmt_inr(row["amount"])}</div>
        </div>''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    export = disp.drop(columns=['month'], errors='ignore')
    st.dataframe(export, use_container_width=True, hide_index=True, column_config={
        "amount":  st.column_config.NumberColumn("Amount (₹)", format="₹%.0f"),
        "date":    st.column_config.DateColumn("Date"),
        "is_emi":  st.column_config.CheckboxColumn("EMI?"),
    })
    st.download_button(
        "⬇️  Download CSV",
        data=export.to_csv(index=False),
        file_name=f"transactions_{selected_period.replace(' ','_').lower()}.csv",
        mime="text/csv"
    )
