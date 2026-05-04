# frontend/components/analysis.py
# Tab 1 — Spend Analysis: monthly trend, category breakdown, channel mix, top merchants.

import streamlit as st
import pandas as pd
import plotly.express as px
from .styles import apply_theme, TEAL, COLORS, section_header


def render(spend_df: pd.DataFrame) -> None:
    if spend_df.empty:
        st.info("No purchase data for the selected period.")
        return

    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown(section_header("Monthly Spend Trend"), unsafe_allow_html=True)
        monthly = spend_df.groupby("month")["amount"].sum().reset_index()
        monthly.columns = ["Month", "Amount"]
        fig = px.bar(monthly, x="Month", y="Amount", color_discrete_sequence=[TEAL])
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(showlegend=False, bargap=0.35)
        fig.update_yaxes(title_text="Spend (₹)", tickformat=",.0f")
        fig.update_xaxes(title_text="")
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    with c2:
        st.markdown(section_header("Spend by Category"), unsafe_allow_html=True)
        cat_data = (
            spend_df.groupby("category")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )
        top7 = cat_data.head(7).copy()
        if len(cat_data) > 7:
            other_row = pd.DataFrame([{"category": "Other",
                                        "amount": cat_data.iloc[7:]["amount"].sum()}])
            top7 = pd.concat([top7, other_row], ignore_index=True)
        fig = px.pie(top7, values="amount", names="category",
                     color_discrete_sequence=COLORS, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent", textfont_size=12)
        fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.02, y=0.5))
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown(section_header("Online vs Offline by Month"), unsafe_allow_html=True)
        ch_data = spend_df.groupby(["month", "channel"])["amount"].sum().reset_index()
        fig = px.bar(
            ch_data, x="month", y="amount", color="channel",
            color_discrete_map={"online": TEAL, "offline": "#da7101"},
            barmode="stack",
        )
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(bargap=0.35)
        fig.update_yaxes(title_text="Spend (₹)", tickformat=",.0f")
        fig.update_xaxes(title_text="")
        st.plotly_chart(apply_theme(fig), use_container_width=True)

    with c4:
        st.markdown(section_header("Top 10 Merchants"), unsafe_allow_html=True)
        top_m = spend_df.groupby("merchant")["amount"].sum().nlargest(10).reset_index()
        top_m.columns = ["Merchant", "Amount"]
        fig = px.bar(
            top_m.sort_values("Amount"), x="Amount", y="Merchant",
            orientation="h", color_discrete_sequence=[TEAL],
        )
        fig.update_traces(marker_cornerradius=4)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title_text="Total (₹)", tickformat=",.0f")
        fig.update_yaxes(title_text="")
        st.plotly_chart(apply_theme(fig), use_container_width=True)
