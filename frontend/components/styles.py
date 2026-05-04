# frontend/components/styles.py
# Shared CSS, color constants, and formatting helpers for the dashboard.

import plotly.graph_objects as go

TEAL   = "#0d9488"
COLORS = ["#0d9488", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#10b981", "#f97316", "#ec4899"]

CATEGORY_BADGE: dict[str, str] = {
    "Food & Dining":     "badge-food",
    "Online Shopping":   "badge-shopping",
    "Grocery":           "badge-shopping",
    "Transport":         "badge-transport",
    "Fuel":              "badge-fuel",
    "Entertainment":     "badge-entertainment",
    "Utilities & Bills": "badge-utilities",
    "Health":            "badge-health",
    "Travel":            "badge-travel",
    "Cash Advance":      "badge-other",
    "Other":             "badge-other",
}

CSS_BLOCK = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ─── Sidebar ─────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] .section-header {
    color: #94a3b8 !important;
    border-bottom-color: #334155 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #0d9488, #0f766e) !important;
    color: #fff !important; border: none !important;
    font-weight: 600 !important; border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(13,148,136,0.4) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #0f766e, #065f46) !important;
    box-shadow: 0 4px 14px rgba(13,148,136,0.5) !important;
}
[data-testid="stSidebar"] hr { border-color: #334155 !important; }

/* ─── Section Header ──────────────────────────────────────────────────── */
.section-header {
    font-size: 0.68rem; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin: 1.75rem 0 1rem 0;
    display: flex; align-items: center; gap: 0.6rem;
    border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;
}
.section-header::before {
    content: '';
    display: block; width: 3px; height: 13px; flex-shrink: 0;
    background: linear-gradient(180deg, #0d9488, #06b6d4);
    border-radius: 2px;
}

/* ─── KPI Cards ───────────────────────────────────────────────────────── */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.25rem 1.5rem 1.1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
    position: relative; overflow: hidden;
    transition: box-shadow 0.15s;
}
.kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #0d9488, #06b6d4);
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.kpi-label {
    font-size: 0.68rem; font-weight: 700; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem;
}
.kpi-value {
    font-size: 1.8rem; font-weight: 800; color: #0f172a;
    line-height: 1.1; letter-spacing: -0.025em;
}
.kpi-sub { font-size: 0.75rem; color: #94a3b8; margin-top: 0.4rem; }

.kpi-card-green { border-color: #bbf7d0; background: #f0fdf4; }
.kpi-card-amber { border-color: #fde68a; background: #fffbeb; }
.kpi-card-red   { border-color: #fecaca; background: #fef2f2; }

.kpi-card-green::before { background: linear-gradient(90deg, #059669, #34d399); }
.kpi-card-amber::before { background: linear-gradient(90deg, #d97706, #fbbf24); }
.kpi-card-red::before   { background: linear-gradient(90deg, #dc2626, #f87171); }

.kpi-value-green { color: #059669 !important; }
.kpi-value-amber { color: #b45309 !important; }
.kpi-value-red   { color: #dc2626 !important; }

/* ─── Recommendation Cards ────────────────────────────────────────────── */
.rec-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    overflow: hidden;
    height: 100%;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    transition: transform 0.15s, box-shadow 0.15s;
}
.rec-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.rec-card-band   { padding: 1.1rem 1.25rem 0.9rem; }
.rec-card-name   { font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 0.1rem; }
.rec-card-issuer {
    font-size: 0.68rem; color: rgba(255,255,255,0.7);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
}
.rec-card-body   { padding: 1rem 1.25rem 1.1rem; }
.rec-label {
    font-size: 0.66rem; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem;
}
.rec-cashback {
    font-size: 1.75rem; font-weight: 800; color: #0f172a;
    line-height: 1.1; letter-spacing: -0.025em;
}
.rec-fee      { font-size: 0.78rem; color: #64748b; margin: 0.45rem 0 0.5rem; }
.rec-divider  { border: none; border-top: 1px solid #f1f5f9; margin: 0.6rem 0; }
.rec-cat-row  { display: flex; justify-content: space-between; font-size: 0.79rem; padding: 0.2rem 0; color: #334155; }
.rec-note     {
    font-size: 0.72rem; color: #64748b; margin-top: 0.75rem;
    background: #f8fafc; border-radius: 8px; padding: 0.55rem 0.7rem;
    border-left: 3px solid #e2e8f0;
}

/* ─── Missed-savings rows ─────────────────────────────────────────────── */
.miss-row {
    display: flex; align-items: center;
    padding: 0.55rem 0.5rem; border-bottom: 1px solid #f1f5f9;
    font-size: 0.84rem; border-radius: 6px;
    transition: background 0.1s;
}
.miss-row:hover { background: #f8fafc; }
.miss-merchant  { font-weight: 600; color: #0f172a; flex: 2; }
.miss-meta      { color: #64748b; flex: 1; font-size: 0.76rem; }
.miss-amount    { font-weight: 600; color: #334155; text-align: right; flex: 0.8; }
.miss-missed    { font-weight: 700; color: #dc2626; text-align: right; flex: 0.8; }

/* ─── Transaction rows ────────────────────────────────────────────────── */
.txn-row {
    display: flex; align-items: center;
    padding: 0.65rem 0.5rem; border-bottom: 1px solid #f1f5f9;
    font-size: 0.875rem; border-radius: 6px;
    transition: background 0.1s;
}
.txn-row:hover { background: #f8fafc; }
.txn-merchant  { font-weight: 600; color: #0f172a; flex: 2; }
.txn-meta      { color: #64748b; flex: 1; font-size: 0.78rem; }
.txn-amount    { font-weight: 700; color: #0f172a; text-align: right; flex: 1; }

/* ─── Badges ──────────────────────────────────────────────────────────── */
.txn-badge           { font-size: 0.67rem; padding: 2px 9px; border-radius: 999px; font-weight: 600; letter-spacing: 0.01em; }
.badge-food          { background: #fef3c7; color: #92400e; }
.badge-shopping      { background: #dbeafe; color: #1e40af; }
.badge-transport     { background: #dcfce7; color: #166534; }
.badge-fuel          { background: #fee2e2; color: #991b1b; }
.badge-entertainment { background: #ede9fe; color: #5b21b6; }
.badge-utilities     { background: #f1f5f9; color: #475569; }
.badge-health        { background: #fce7f3; color: #9d174d; }
.badge-travel        { background: #cffafe; color: #155e75; }
.badge-other         { background: #f1f5f9; color: #64748b; }

/* ─── Tabs ────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; border-bottom: 2px solid #e2e8f0;
    padding-bottom: 0; background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.84rem; font-weight: 500; color: #64748b;
    background: transparent; border: none;
    padding: 0.55rem 1.1rem; border-radius: 8px 8px 0 0;
    transition: color 0.15s, background 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #0d9488; background: #f0fdfa;
}
.stTabs [aria-selected="true"] {
    color: #0d9488 !important;
    font-weight: 700 !important;
    background: transparent !important;
    border-bottom: 2px solid #0d9488 !important;
}

/* ─── DataFrame ───────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ─── Expander ────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    overflow: hidden;
}

/* ─── Hide Streamlit chrome ───────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
</style>
"""


def fmt_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"


def apply_theme(fig) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#334155", size=12),
        margin=dict(t=50, b=40, l=40, r=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.05,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
    )
    fig.update_xaxes(
        showgrid=False, tickfont=dict(size=11, color="#94a3b8"),
        linecolor="#e2e8f0", tickcolor="#e2e8f0",
    )
    fig.update_yaxes(
        gridcolor="#f1f5f9", tickfont=dict(size=11, color="#94a3b8"),
        linecolor="rgba(0,0,0,0)",
    )
    return fig


def kpi_card(label: str, value: str, sub: str, extra_cls: str = "", value_cls: str = "") -> str:
    return (
        f'<div class="kpi-card {extra_cls}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value {value_cls}">{value}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>'
    )


def section_header(text: str) -> str:
    return f'<div class="section-header">{text}</div>'
