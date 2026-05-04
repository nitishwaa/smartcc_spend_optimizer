# backend/card_advisor.py
# Missed savings analysis and card recommendation engine.

from __future__ import annotations
import yaml
import pandas as pd
from .card_catalog import CARD_CATALOG


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_card_name_map(config: dict) -> dict[str, str]:
    """Returns {card_name: catalog_id} built from config.yaml cards list."""
    mapping = {}
    for card in config.get("cards", []):
        name = card.get("name", "").strip()
        cid = card.get("catalog_id", "").strip()
        if name and cid:
            mapping[name] = cid
    return mapping


def get_owned_catalog_ids(config: dict) -> list[str]:
    """Returns de-duplicated list of catalog_ids for cards the user owns."""
    seen = set()
    ids = []
    for card in config.get("cards", []):
        cid = card.get("catalog_id", "").strip()
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids


def _get_rate(card_data: dict, category: str, channel: str) -> float:
    """Returns effective cashback % for given category + channel."""
    if channel == "offline":
        offline = card_data.get("offline_cashback")
        if offline is not None:
            return offline.get(category, offline.get("_default", 0.0))
    return card_data["cashback"].get(category, 0.0)


def compute_missed_savings(
    df: pd.DataFrame,
    card_name_map: dict[str, str],
    catalog: dict | None = None,
) -> pd.DataFrame:
    """
    Per-transaction analysis. For each PURCHASE row:
      - actual_rate  : cashback % from the card that was used
      - optimal_rate : best cashback % available among owned cards
      - optimal_card : which owned card gives that rate
      - cashback_earned  : amount × actual_rate / 100
      - cashback_missed  : amount × (optimal_rate - actual_rate) / 100

    Returns an empty DataFrame if df is empty or no owned cards are mapped.
    """
    if catalog is None:
        catalog = CARD_CATALOG

    owned_ids = list(dict.fromkeys(card_name_map.values()))
    spend = df[df["type"] == "PURCHASE"].copy() if "type" in df.columns else df.copy()

    if spend.empty or not owned_ids:
        return pd.DataFrame()

    records = []
    for _, row in spend.iterrows():
        category  = row.get("category", "Other")
        channel   = row.get("channel", "online")
        amount    = float(row.get("amount", 0))
        card_name = row.get("card_name", "")

        actual_cid  = card_name_map.get(card_name)
        actual_rate = _get_rate(catalog[actual_cid], category, channel) if actual_cid and actual_cid in catalog else 0.0

        best_rate, best_card_name = 0.0, "—"
        for cid in owned_ids:
            if cid not in catalog:
                continue
            rate = _get_rate(catalog[cid], category, channel)
            if rate > best_rate:
                best_rate = rate
                best_card_name = catalog[cid]["display_name"]

        records.append({
            "txn_id":          row.get("txn_id", ""),
            "date":            row.get("date"),
            "merchant":        row.get("merchant", ""),
            "amount":          amount,
            "category":        category,
            "channel":         channel,
            "card_used":       card_name,
            "actual_rate":     actual_rate,
            "optimal_card":    best_card_name,
            "optimal_rate":    best_rate,
            "cashback_earned": round(amount * actual_rate / 100, 2),
            "cashback_missed": round(amount * max(0, best_rate - actual_rate) / 100, 2),
        })

    return pd.DataFrame(records) if records else pd.DataFrame()


def recommend_cards(
    df: pd.DataFrame,
    owned_ids: list[str],
    catalog: dict | None = None,
    top_n: int = 3,
) -> list[dict]:
    """
    For each card NOT in owned_ids, estimate annual cashback on current spend.
    Returns top_n recommendations sorted by net annual benefit (cashback - annual fee).
    """
    if catalog is None:
        catalog = CARD_CATALOG

    spend = df[df["type"] == "PURCHASE"].copy() if "type" in df.columns else df.copy()
    if spend.empty:
        return []

    date_range_days = max(1, (pd.to_datetime(spend["date"]).max() - pd.to_datetime(spend["date"]).min()).days)
    annual_factor = 365.0 / date_range_days

    if "channel" not in spend.columns:
        spend["channel"] = "online"
    spend_by = spend.groupby(["category", "channel"])["amount"].sum().reset_index()

    recs = []
    for card_id, card in catalog.items():
        if card_id in owned_ids:
            continue

        annual_cb = 0.0
        cat_earnings: dict[str, float] = {}

        for _, row in spend_by.iterrows():
            rate   = _get_rate(card, row["category"], row["channel"])
            earned = row["amount"] * rate / 100 * annual_factor
            cat_earnings[row["category"]] = cat_earnings.get(row["category"], 0.0) + earned
            annual_cb += earned

        cap = card.get("monthly_cashback_cap")
        if cap:
            annual_cb = min(annual_cb, cap * 12)

        net = annual_cb - card["annual_fee"]
        top_cats = sorted(cat_earnings.items(), key=lambda x: x[1], reverse=True)[:3]

        recs.append({
            "card_id":         card_id,
            "display_name":    card["display_name"],
            "issuer":          card["issuer"],
            "annual_fee":      card["annual_fee"],
            "annual_cashback": round(annual_cb),
            "net_benefit":     round(net),
            "top_categories":  [(c, round(v)) for c, v in top_cats],
            "notes":           card["notes"],
            "best_for":        card.get("best_for", []),
            "color":           card.get("color", "#666666"),
        })

    return sorted(recs, key=lambda x: x["net_benefit"], reverse=True)[:top_n]


def spending_summary(df: pd.DataFrame) -> dict:
    """Quick summary stats for dashboard callouts."""
    spend = df[df["type"] == "PURCHASE"] if "type" in df.columns else df
    total = float(spend["amount"].sum()) if not spend.empty else 0.0
    by_cat = spend.groupby("category")["amount"].sum().to_dict() if not spend.empty else {}
    return {"total": total, "by_category": by_cat}
