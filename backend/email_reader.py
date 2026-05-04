# backend/email_reader.py
# Fetches credit-card transaction alerts from Gmail and writes data/transactions.{csv,json}
# Usage (from project root): python backend/email_reader.py [--days N]

import imaplib
import email
import re
import csv
import json
import yaml
import os
import hashlib
import argparse
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ─── Bank Patterns ─────────────────────────────────────────────────────────────
# Each 'amount', 'merchant', 'card' key may be a single pattern or a list.
# Patterns are tried in order; first match wins.

BANK_PATTERNS = {
    "hdfc": {
        "sender": [
            "alerts@hdfcbank.net",
            "alerts@hdfcbank.bank.in",
            "noreply@hdfcbank.com",
            "hdfcbank@alerts.hdfcbank.net",
        ],
        "amount": [
            r"(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
            r"(?:of|for|amount)\s+(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
            r"([\d,]+(?:\.\d{2})?)\s*(?:Rs\.?|INR)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\s+Info\b|\.\s|\s{2,}|$)",
            r"spent\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"used\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"merchant[:\s]+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"purchase\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
        ],
        "card": [
            r"(?:Credit|Debit)\s+Card\s+(?:ending\s+(?:in\s+)?(?:XX|xx)?)?(\d{4})",
            r"(?:XX|xx)(\d{4})",
            r"Card\s*(?:no\.?)?\s*(?:XX|xx)(\d{4})",
        ],
        "credit_signals": ["credited", "refund", "payment received", "cashback credited", "payment due"],
    },
    "idfc": {
        "sender": ["noreply@idfcfirstbank.com", "alerts@idfcfirstbank.com"],
        "amount": [
            r"INR\s*([\d,]+(?:\.\d{1,2})?)",
            r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"spent\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
        ],
        "card": [r"(?:XX|xx)(\d{4})"],
        "credit_signals": ["credited", "refund", "payment received"],
    },
    "sbi": {
        "sender": ["onlinesbicard@sbicard.com", "alerts@sbicard.com"],
        "amount": [
            r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
            r"INR\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"spent\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
        ],
        "card": [r"(?:XX|xx)(\d{4})"],
        "credit_signals": ["credited", "refund", "payment received"],
    },
    "axis": {
        "sender": ["alerts@axisbank.com", "noreply@axisbank.com"],
        "amount": [
            r"INR\s*([\d,]+(?:\.\d{1,2})?)",
            r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"(?:at|At)\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
        ],
        "card": [r"(?:XX|xx)(\d{4})"],
        "credit_signals": ["credited", "refund", "payment received"],
    },
    "icici": {
        "sender": ["alerts@icicibank.com", "creditcards@icicibank.com"],
        "amount": [
            r"INR\s*([\d,]+(?:\.\d{1,2})?)",
            r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
            r"for\s+(?:INR|Rs\.?)\s+[\d,]+\s+at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.|$)",
        ],
        "card": [r"(?:XX|xx)(\d{4})", r"ending\s+(\d{4})"],
        "credit_signals": ["credited", "refund", "payment received"],
    },
    "kotak": {
        "sender": ["alerts@kotak.com", "noreply@kotak.com"],
        "amount": [
            r"INR\s*([\d,]+(?:\.\d{1,2})?)",
            r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        "merchant": [
            r"at\s+([A-Za-z0-9][A-Za-z0-9 \-_.\&\/]{2,50}?)(?=\s+on\b|\.\s|$)",
        ],
        "card": [r"(?:XX|xx)(\d{4})", r"ending\s+(\d{4})"],
        "credit_signals": ["credited", "refund", "payment received"],
    },
}

# ─── Classification Helpers ────────────────────────────────────────────────────

ONLINE_MERCHANTS = {
    "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa",
    "swiggy", "zomato", "blinkit", "zepto", "bigbasket", "dunzo",
    "netflix", "hotstar", "spotify", "youtube", "primevideo",
    "irctc", "makemytrip", "goibibo", "cleartrip", "bookmyshow",
    "phonepe", "paytm", "gpay", "razorpay", "cashfree", "tatacliq",
    "snapdeal", "1mg", "netmeds", "practo",
}

OFFLINE_SIGNALS = {
    "pos", "swipe", "tap", "nfc", "contactless",
    "petrol pump", "bpcl", "hpcl", "iocl",
}

CATEGORIES = {
    "Food & Dining":     ["swiggy", "zomato", "dominos", "mcdonalds", "kfc",
                          "restaurant", "cafe", "food", "eat", "pizza", "burger", "barbeque",
                          "subway", "starbucks", "chaayos", "wow momo"],
    "Online Shopping":   ["amazon", "flipkart", "myntra", "ajio", "meesho",
                          "nykaa", "tatacliq", "snapdeal", "lenskart", "clovia"],
    "Grocery":           ["bigbasket", "blinkit", "zepto", "grofers", "dmart",
                          "supermarket", "grocery", "nature basket", "instamart"],
    "Fuel":              ["petrol", "bpcl", "hpcl", "iocl", "fuel", "shell", "essar", "nayara"],
    "Transport":         ["uber", "ola", "rapido", "irctc", "railway", "metro",
                          "redbus", "makemytrip", "goibibo", "mmt", "yatra"],
    "Entertainment":     ["netflix", "hotstar", "spotify", "youtube", "primevideo",
                          "cinema", "pvr", "inox", "bookmyshow", "zee5", "sony liv"],
    "Utilities & Bills": ["electricity", "water", "gas", "broadband",
                          "airtel", "jio", "bsnl", "recharge", "tataplay", "tata sky",
                          "vodafone", "vi ", "bescom", "msedcl"],
    "Health":            ["pharmacy", "hospital", "clinic", "medical",
                          "apollo", "practo", "netmeds", "1mg", "medplus", "healthkart"],
    "Travel":            ["hotel", "marriott", "oyo", "airbnb", "flight", "indigo",
                          "air india", "vistara", "spicejet", "goair", "akasa",
                          "agoda", "booking.com", "mmt"],
    "Cash Advance":      ["atm", "cash advance", "cash withdrawal"],
}


def detect_channel(merchant: str, body: str) -> str:
    m = merchant.lower()
    b = body.lower()
    if any(k in m for k in ONLINE_MERCHANTS):
        return "online"
    if any(s in b for s in OFFLINE_SIGNALS):
        return "offline"
    if "pos" in b or "point of sale" in b:
        return "offline"
    return "online"


def categorise(merchant: str) -> str:
    m = merchant.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in m for k in keywords):
            return category
    return "Other"


def clean_merchant(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 \-\&\.]", "", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().title()
    return cleaned[:60]


def is_emi(body: str) -> bool:
    return any(s in body.lower() for s in ["emi", "equated monthly", "installment", "no cost emi"])


def make_txn_id(date: str, merchant: str, amount: float, card: str) -> str:
    raw = f"{date}|{merchant.lower()}|{amount}|{card}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _try_patterns(patterns, text: str, flags: int = re.IGNORECASE):
    """Try each pattern in the list and return the first match (or None)."""
    plist = patterns if isinstance(patterns, list) else [patterns]
    for p in plist:
        m = re.search(p, text, flags)
        if m:
            return m
    return None


# ─── EmailReader ───────────────────────────────────────────────────────────────

class EmailReader:

    def __init__(self):
        self.config       = load_config()
        self.email_addr   = os.getenv("GMAIL_ADDRESS")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD")
        self.transactions: list[dict] = []
        self.seen_ids:     set[str]   = set()

    def connect(self):
        print("Connecting to Gmail...")
        self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
        self.mail.login(self.email_addr, self.app_password)
        self.mail.select("inbox")
        print("✅ Connected")

    def fetch_transactions(self, days_back: int | None = None):
        fetch_cfg    = self.config.get("fetch", {})
        days_back    = days_back or fetch_cfg.get("days_back", 90)
        max_per_bank = fetch_cfg.get("max_emails_per_bank", 500)
        cutoff       = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        print(f"\nFetching bank emails from last {days_back} days (since {cutoff})...")

        for bank_name, pattern in BANK_PATTERNS.items():
            print(f"  → {bank_name.upper()}", end=" ", flush=True)
            senders = pattern["sender"] if isinstance(pattern["sender"], list) else [pattern["sender"]]
            nums    = []
            for sender in senders:
                _, msgs = self.mail.search(None, f'FROM "{sender}" SINCE {cutoff}')
                if msgs[0]:
                    nums.extend(msgs[0].split())
            if not nums:
                print("— no emails")
                continue

            count = 0
            for num in nums[-max_per_bank:]:
                try:
                    _, data = self.mail.fetch(num, "(RFC822)")
                    msg  = email.message_from_bytes(data[0][1])
                    body = self._get_body(msg)
                    if self._is_credit_email(body, pattern):
                        continue
                    txn = self._parse_transaction(body, msg.get("Date", ""), bank_name, pattern)
                    if txn and txn["txn_id"] not in self.seen_ids:
                        self.seen_ids.add(txn["txn_id"])
                        self.transactions.append(txn)
                        count += 1
                except Exception:
                    continue
            print(f"— {count} transactions")

    def _get_body(self, msg) -> str:
        plain, html = None, None
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    text = payload.decode("utf-8", errors="replace")
                    if ctype == "text/plain" and plain is None:
                        plain = text
                    elif ctype == "text/html" and html is None:
                        html = text
                except Exception:
                    continue
        else:
            try:
                raw = msg.get_payload(decode=True)
                if raw:
                    text = raw.decode("utf-8", errors="replace")
                    if msg.get_content_type() == "text/html":
                        html = text
                    else:
                        plain = text
            except Exception:
                pass

        if plain:
            return plain
        if html:
            try:
                return BeautifulSoup(html, "lxml").get_text(separator=" ")
            except Exception:
                return BeautifulSoup(html, "html.parser").get_text(separator=" ")
        return ""

    def _is_credit_email(self, body: str, pattern: dict) -> bool:
        b = body.lower()
        return any(s in b for s in pattern.get("credit_signals", []))

    def _parse_transaction(self, body: str, date_str: str, bank: str, pattern: dict) -> dict | None:
        try:
            amount_m   = _try_patterns(pattern["amount"],   body)
            merchant_m = _try_patterns(pattern["merchant"], body)
            card_m     = _try_patterns(pattern["card"],     body)

            if not amount_m:
                return None
            amount = float(amount_m.group(1).replace(",", ""))
            if amount <= 0:
                return None

            merchant   = clean_merchant(merchant_m.group(1)) if merchant_m else "Unknown"
            card_last4 = card_m.group(1) if card_m else "XXXX"

            try:
                txn_date = parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
            except Exception:
                txn_date = datetime.now().strftime("%Y-%m-%d")

            card_name = self._resolve_card_name(bank, card_last4)
            channel   = detect_channel(merchant, body)
            emi_flag  = is_emi(body)

            if "atm" in body.lower() or "cash advance" in body.lower():
                txn_type = "CASH_ADVANCE"
            elif emi_flag:
                txn_type = "EMI"
            else:
                txn_type = "PURCHASE"

            return {
                "txn_id":         make_txn_id(txn_date, merchant, amount, card_last4),
                "date":           txn_date,
                "merchant":       merchant,
                "amount":         amount,
                "category":       categorise(merchant),
                "channel":        channel,
                "bank":           bank.upper(),
                "card_last_four": card_last4,
                "card_name":      card_name,
                "type":           txn_type,
                "is_emi":         emi_flag,
            }
        except Exception:
            return None

    def _resolve_card_name(self, bank: str, last4: str) -> str:
        for card in self.config.get("cards", []):
            if (card.get("bank", "").lower() == bank.lower()
                    and str(card.get("last_four", "")) == str(last4)):
                return card.get("name", f"{bank.upper()} Card")
        return f"{bank.upper()} XX{last4}"

    def save(self):
        if not self.transactions:
            print("\n⚠️  No transactions found.")
            return
        os.makedirs("data", exist_ok=True)
        fields = ["txn_id", "date", "merchant", "amount", "category",
                  "channel", "bank", "card_last_four", "card_name", "type", "is_emi"]
        with open("data/transactions.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.transactions)
        with open("data/transactions.json", "w", encoding="utf-8") as f:
            json.dump(self.transactions, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Saved {len(self.transactions)} transactions")
        print(f"   CSV  → data/transactions.csv")
        print(f"   JSON → data/transactions.json")
        self._print_summary()

    def _print_summary(self):
        df = pd.DataFrame(self.transactions)
        spend = df[df["type"] == "PURCHASE"]
        print("\n── Summary ──────────────────────────────────────")
        print(f"Total transactions : {len(df)}")
        print(f"  └─ Purchases     : {len(spend)}")
        print(f"  └─ EMI           : {len(df[df['type']=='EMI'])}")
        print(f"  └─ Cash Advance  : {len(df[df['type']=='CASH_ADVANCE'])}")
        print(f"Total spend        : ₹{spend['amount'].sum():,.2f}")
        print(f"Date range         : {df['date'].min()} → {df['date'].max()}")
        print("\nBy category:")
        for cat, amt in spend.groupby("category")["amount"].sum().sort_values(ascending=False).items():
            print(f"  {cat:<25} ₹{amt:>10,.2f}")
        print("\nBy card:")
        for card, amt in spend.groupby("card_name")["amount"].sum().sort_values(ascending=False).items():
            print(f"  {card:<30} ₹{amt:>10,.2f}")
        print("─────────────────────────────────────────────────")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CC transactions from Gmail")
    parser.add_argument("--days", type=int, default=None,
                        help="Number of days to look back (overrides config.yaml)")
    args = parser.parse_args()

    reader = EmailReader()
    reader.connect()
    reader.fetch_transactions(days_back=args.days)
    reader.save()
