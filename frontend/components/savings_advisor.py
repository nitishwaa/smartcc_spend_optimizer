# frontend/components/savings_advisor.py
# Tab 3 — Savings Advisor: missed savings within portfolio + card recommendations.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from .styles import apply_theme, TEAL, fmt_inr, kpi_card, section_header

# backend imports — sys.path set up by frontend/dashboard.py
from backend.card_advisor  import (
    get_card_name_map, get_owned_catalog_ids,
    compute_missed_savings, recommend_cards,
)
from backend.card_catalog import CARD_CATALOG

ISSUER_GRADIENTS: dict[str, str] = {
    "HDFC":       "linear-gradient(135deg, #004C8F, #0070CC)",
    "ICICI":      "linear-gradient(135deg, #9B1C1C, #DC2626)",
    "Axis":       "linear-gradient(135deg, #6D0F37, #97144D)",
    "SBI":        "linear-gradient(135deg, #1E3A8A, #3B82F6)",
    "IDFC First": "linear-gradient(135deg, #B91C1C, #EF4444)",
    "Amex":       "linear-gradient(135deg, #0369A1, #0EA5E9)",
}


def render(spend_df: pd.DataFrame, config: dict) -> None:
    card_name_map = get_card_name_map(config)
    owned_ids     = get_owned_catalog_ids(config)

    # ── Section 1: Portfolio Optimizer ────────────────────────────────────────
    st.markdown(
        section_header("Portfolio Optimizer — Are you using the right card?"),
        unsafe_allow_html=True,
    )

    if not card_name_map:
        st.info(
            "Add a `catalog_id` to each card in **config.yaml** to unlock missed-savings analysis.\n\n"
            "```yaml\ncards:\n  - bank: hdfc\n    last_four: \"9930\"\n"
            "    name: \"HDFC Millennia\"\n    catalog_id: hdfc_millennia\n```\n\n"
            "Available IDs: " + ", ".join(f"`{k}`" for k in CARD_CATALOG)
        )
    else:
        missed_df = compute_missed_savings(spend_df, card_name_map)

        if missed_df.empty:
            st.info("No data — make sure cards in config.yaml have `catalog_id` set.")
        else:
            total_earned = float(missed_df["cashback_earned"].sum())
            total_missed = float(missed_df["cashback_missed"].sum())
            miss_pct = (
                total_missed / (total_earned + total_missed) * 100
                if (total_earned + total_missed) > 0 else 0
            )
            best_miss_cat = (
                missed_df.groupby("category")["cashback_missed"].sum().idxmax()
                if not missed_df.empty else "—"
            )

            m1, m2, m3, m4 = st.columns(4)
            for col, label, value, sub, extra, vcls in [
                (m1, "Estimated Earned",  fmt_inr(total_earned), "cashback this period",  "kpi-card-green", "kpi-value-green"),
                (m2, "Missed Savings",    fmt_inr(total_missed), "left on the table",     "kpi-card-red",   "kpi-value-red"),
                (m3, "Missed Rate",       f"{miss_pct:.1f}%",    "of potential cashback", "kpi-card-amber", "kpi-value-amber"),
                (m4, "Costliest Miss",    best_miss_cat,          "highest missed category","",              ""),
            ]:
                with col:
                    st.markdown(kpi_card(label, value, sub, extra, vcls), unsafe_allow_html=True)

            st.markdown("")
            ma, mb = st.columns([3, 2])

            with ma:
                st.markdown(section_header("Missed Savings by Category"), unsafe_allow_html=True)
                cat_miss = (
                    missed_df.groupby("category")[["cashback_earned", "cashback_missed"]]
                    .sum()
                    .reset_index()
                    .sort_values("cashback_missed", ascending=True)
                )
                cat_miss = cat_miss[cat_miss["cashback_missed"] > 0]
                if not cat_miss.empty:
                    fig = go.Figure()
                    fig.add_bar(x=cat_miss["cashback_earned"], y=cat_miss["category"],
                                orientation="h", name="Earned", marker_color=TEAL)
                    fig.add_bar(x=cat_miss["cashback_missed"], y=cat_miss["category"],
                                orientation="h", name="Missed", marker_color="#dc2626")
                    fig.update_layout(barmode="stack", bargap=0.3,
                                      height=max(240, len(cat_miss) * 40))
                    fig.update_xaxes(title_text="Cashback (₹)", tickformat=",.0f", showgrid=False)
                    fig.update_yaxes(title_text="")
                    st.plotly_chart(apply_theme(fig), use_container_width=True)

            with mb:
                st.markdown(section_header("Optimization Tips"), unsafe_allow_html=True)
                tips = (
                    missed_df[missed_df["cashback_missed"] > 0]
                    .groupby(["category", "optimal_card", "optimal_rate"])["cashback_missed"]
                    .sum()
                    .reset_index()
                    .sort_values("cashback_missed", ascending=False)
                    .drop_duplicates("category")
                    .head(5)
                )
                if tips.empty:
                    st.success("✅ You're already using the optimal card for every category!")
                else:
                    for _, tip in tips.iterrows():
                        st.markdown(
                            f"**{tip['category']}** — use _{tip['optimal_card']}_ "
                            f"({tip['optimal_rate']:.1f}%) · save {fmt_inr(tip['cashback_missed'])} more"
                        )

            n_miss = len(missed_df[missed_df["cashback_missed"] > 0])
            with st.expander(f"📋 Top missed transactions ({n_miss} rows)"):
                top_miss = (
                    missed_df[missed_df["cashback_missed"] > 0]
                    .sort_values("cashback_missed", ascending=False)
                    .head(50)
                )
                st.markdown(
                    '<div class="miss-row" style="font-weight:600;border-bottom:2px solid #dcd9d5">'
                    '<div class="miss-merchant">Merchant</div>'
                    '<div class="miss-meta">Category</div>'
                    '<div class="miss-meta">Card Used</div>'
                    '<div class="miss-meta">Use Instead</div>'
                    '<div class="miss-amount">Spend</div>'
                    '<div class="miss-missed">Missed ₹</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                for _, row in top_miss.iterrows():
                    st.markdown(f'''
                    <div class="miss-row">
                        <div class="miss-merchant">{row["merchant"]}</div>
                        <div class="miss-meta">{row["category"]}</div>
                        <div class="miss-meta">{row["card_used"]}</div>
                        <div class="miss-meta" style="color:#01696f">{row["optimal_card"]}</div>
                        <div class="miss-amount">{fmt_inr(row["amount"])}</div>
                        <div class="miss-missed">−{fmt_inr(row["cashback_missed"])}</div>
                    </div>''', unsafe_allow_html=True)

    # ── Section 2: Card Recommendations ───────────────────────────────────────
    st.markdown("")
    st.markdown(
        section_header("Card Recommendations — What to add next"),
        unsafe_allow_html=True,
    )

    if spend_df.empty:
        st.info("No purchase data available for recommendations.")
        return

    date_min = spend_df["date"].min()
    date_max = spend_df["date"].max()
    months   = max(1, (date_max - date_min).days / 30)

    st.caption(
        f"Based on {fmt_inr(spend_df['amount'].sum())} spend over {months:.0f} months "
        f"({date_min.strftime('%d %b %y')} – {date_max.strftime('%d %b %y')}), "
        "annualised to estimate yearly benefit."
    )

    recs = recommend_cards(spend_df, owned_ids, top_n=3)

    if not recs:
        st.success("🎉 You already own all cards in our catalog!")
    else:
        rec_cols = st.columns(len(recs))
        for col, rec in zip(rec_cols, recs):
            top_cats_html = "".join(
                f'<div class="rec-cat-row">'
                f'<span>{c}</span>'
                f'<span style="font-weight:600">{fmt_inr(v)}/yr</span>'
                f'</div>'
                for c, v in rec["top_categories"]
            )
            fee_waiver = CARD_CATALOG[rec["card_id"]].get("fee_waiver_spend", 0)
            fee_note = (
                f"₹{rec['annual_fee']:,}/yr fee · waived at ₹{fee_waiver:,} spend"
                if rec["annual_fee"] > 0 else "No annual fee"
            )
            net_color = "#059669" if rec["net_benefit"] > 0 else "#dc2626"
            gradient  = ISSUER_GRADIENTS.get(
                rec["issuer"], "linear-gradient(135deg, #374151, #6B7280)"
            )
            with col:
                st.markdown(f'''
                <div class="rec-card">
                    <div class="rec-card-band" style="background:{gradient}">
                        <div class="rec-card-name">{rec["display_name"]}</div>
                        <div class="rec-card-issuer">{rec["issuer"]}</div>
                    </div>
                    <div class="rec-card-body">
                        <div class="rec-label">Est. Annual Cashback</div>
                        <div class="rec-cashback">{fmt_inr(rec["annual_cashback"])}</div>
                        <div class="rec-fee">{fee_note}</div>
                        <div style="font-size:0.82rem;color:{net_color};font-weight:700;margin-bottom:0.5rem">
                            Net benefit: {fmt_inr(rec["net_benefit"])}/yr
                        </div>
                        <hr class="rec-divider"/>
                        <div class="rec-label" style="margin-bottom:0.4rem">Best earning categories</div>
                        {top_cats_html}
                        <div class="rec-note">{rec["notes"]}</div>
                    </div>
                </div>''', unsafe_allow_html=True)

    with st.expander("📊 Full comparison — all cards"):
        all_recs = recommend_cards(spend_df, owned_ids, top_n=len(CARD_CATALOG))
        if all_recs:
            comp_df = pd.DataFrame([{
                "Card":                    r["display_name"],
                "Issuer":                  r["issuer"],
                "Annual Fee (₹)":          r["annual_fee"],
                "Est. Cashback/yr (₹)":    r["annual_cashback"],
                "Net Benefit/yr (₹)":      r["net_benefit"],
            } for r in all_recs]).sort_values("Net Benefit/yr (₹)", ascending=False)
            st.dataframe(
                comp_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Est. Cashback/yr (₹)": st.column_config.NumberColumn(format="₹%.0f"),
                    "Net Benefit/yr (₹)":   st.column_config.NumberColumn(format="₹%.0f"),
                    "Annual Fee (₹)":        st.column_config.NumberColumn(format="₹%.0f"),
                },
            )
