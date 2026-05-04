# frontend/components/by_card.py
# Tab 2 — Per-card spend breakdown: category bar chart + online/offline donut.

import streamlit as st
import pandas as pd
import plotly.express as px
from .styles import apply_theme, TEAL, fmt_inr, section_header


def render(spend_df: pd.DataFrame, selected_cards: list[str]) -> None:
    if spend_df.empty:
        st.info("No purchase data for the selected cards and period.")
        return

    for card in selected_cards:
        card_df = spend_df[spend_df["card_name"] == card]
        if card_df.empty:
            continue

        card_total = card_df["amount"].sum()
        card_txns  = len(card_df)
        card_avg   = card_df["amount"].mean()

        st.markdown(f'''
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;
                    padding:1rem 1.5rem;margin:1rem 0 0.5rem 0;
                    box-shadow:0 1px 6px rgba(0,0,0,0.06);position:relative;overflow:hidden">
            <div style="position:absolute;top:0;left:0;right:0;height:3px;
                        background:linear-gradient(90deg,#0d9488,#06b6d4)"></div>
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-size:1rem;font-weight:700;color:#0f172a">💳 {card}</div>
                    <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.15rem">
                        {card_txns} transactions &nbsp;·&nbsp; avg {fmt_inr(card_avg)}
                    </div>
                </div>
                <div style="font-size:1.5rem;font-weight:800;color:#0d9488;letter-spacing:-0.025em">
                    {fmt_inr(card_total)}
                </div>
            </div>
        </div>''', unsafe_allow_html=True)

        ca, cb = st.columns(2)

        with ca:
            cat_b = card_df.groupby("category")["amount"].sum().reset_index()
            fig = px.bar(
                cat_b.sort_values("amount"), x="amount", y="category",
                orientation="h", color_discrete_sequence=[TEAL],
            )
            fig.update_traces(marker_cornerradius=4)
            fig.update_layout(
                showlegend=False, height=280,
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#28251d"),
            )
            fig.update_xaxes(title_text="Spend (₹)", tickformat=",.0f", showgrid=False)
            fig.update_yaxes(title_text="", gridcolor="#f3f0ec")
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            ch_b = card_df.groupby("channel")["amount"].sum().reset_index()
            fig = px.pie(
                ch_b, values="amount", names="channel",
                color_discrete_map={"online": TEAL, "offline": "#da7101"},
                hole=0.5,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                showlegend=False, height=280,
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#28251d"),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
