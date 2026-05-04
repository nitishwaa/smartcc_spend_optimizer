# frontend/components/raw_data.py
# Tab 4 — Transaction table: filterable, sortable, with CSV export.

import streamlit as st
import pandas as pd
from .styles import CATEGORY_BADGE, fmt_inr, section_header


def render(df: pd.DataFrame, selected_period: str) -> None:
    st.markdown(section_header("Transactions"), unsafe_allow_html=True)

    sc1, sc2, sc3 = st.columns([3, 2, 1])
    with sc1:
        search = st.text_input("🔍 Search merchant", placeholder="e.g. Swiggy, Amazon…")
    with sc2:
        sort_by = st.selectbox("Sort by", ["date", "amount", "merchant", "category"])
    with sc3:
        asc = st.selectbox("Order", ["↓ Desc", "↑ Asc"]) == "↑ Asc"

    disp = df.copy()
    if search:
        disp = disp[disp["merchant"].str.contains(search, case=False, na=False)]
    disp = disp.sort_values(sort_by, ascending=asc)

    st.markdown(f"Showing **{len(disp)}** transactions")
    for _, row in disp.head(200).iterrows():
        badge     = CATEGORY_BADGE.get(row.get("category", "Other"), "badge-other")
        ch_icon   = "🌐" if row.get("channel") == "online" else "🏪"
        type_icon = "💳" if row.get("type") == "PURCHASE" else ("📦" if row.get("type") == "EMI" else "🏧")
        st.markdown(f'''
        <div class="txn-row">
            <div class="txn-merchant">{type_icon} {row["merchant"]}
                <span style="margin-left:8px" class="txn-badge {badge}">
                    {row.get("category", "Other")}
                </span>
            </div>
            <div class="txn-meta">{pd.to_datetime(row["date"]).strftime("%d %b %Y")}</div>
            <div class="txn-meta">{row.get("card_name", "—")}</div>
            <div class="txn-meta">{ch_icon} {row.get("channel", "—")}</div>
            <div class="txn-amount">{fmt_inr(row["amount"])}</div>
        </div>''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(section_header("Export"), unsafe_allow_html=True)

    export = disp.drop(columns=["month"], errors="ignore")
    st.dataframe(
        export,
        use_container_width=True,
        hide_index=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.0f"),
            "date":   st.column_config.DateColumn("Date"),
            "is_emi": st.column_config.CheckboxColumn("EMI?"),
        },
    )
    st.download_button(
        "⬇️  Download CSV",
        data=export.to_csv(index=False),
        file_name=f"transactions_{selected_period.replace(' ', '_').lower()}.csv",
        mime="text/csv",
    )
