# part1_email_reader.py

import imaplib
import email
import re
import csv
import json
import yaml
import os
import hashlib
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv

load_dotenv()


# ─── Load Config ───────────────────────────────────────────
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)


# ─── Bank Email Patterns ────────────────────────────────────
BANK_PATTERNS = {
    'hdfc': {
        'sender': 'alerts@hdfcbank.bank.in',
        'amount': r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
        'merchant': r'at\s+([A-Za-z0-9\s\-\_\.\&]+?)(?:\s+on\s|\s+Info|\.|$)',
        'card': r'(?:Card|card)\s*(?:no\.?)?\s*(?:XX|xx)(\d{4})',
        'type': 'DEBIT',
        'credit_signals': ['credited', 'refund', 'payment received', 'cashback credited']
    },
    'idfc': {
        'sender': ['noreply@idfcfirstbank.com', 'alerts@idfcfirstbank.com'],
        'amount': r'INR\s*([\d,]+(?:\.\d{2})?)',
        'merchant': r'at\s+([A-Za-z0-9\s\-\_\.\&]+?)(?:\s+on\s|\.|$)',
        'card': r'(?:XX|xx)(\d{4})',
        'type': 'DEBIT',
        'credit_signals': ['credited', 'refund', 'payment received']
    },
    'sbi': {
        'sender': 'onlinesbicard@sbicard.com',
        'amount': r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
        'merchant': r'at\s+([A-Za-z0-9\s\-\_\.\&]+?)(?:\s+on\s|\.|$)',
        'card': r'(?:XX|xx)(\d{4})',
        'type': 'DEBIT',
        'credit_signals': ['credited', 'refund', 'payment received']
    },
    'axis': {
        'sender': 'alerts@axisbank.com',
        'amount': r'INR\s*([\d,]+(?:\.\d{2})?)',
        'merchant': r'(?:at|At)\s+([A-Za-z0-9\s\-\_\.\&]+?)(?:\s+on\s|\.|$)',
        'card': r'(?:XX|xx)(\d{4})',
        'type': 'DEBIT',
        'credit_signals': ['credited', 'refund', 'payment received']
    }
}

ONLINE_MERCHANTS = [
    'amazon', 'flipkart', 'myntra', 'ajio', 'meesho', 'nykaa',
    'swiggy', 'zomato', 'blinkit', 'zepto', 'bigbasket', 'dunzo',
    'netflix', 'hotstar', 'spotify', 'youtube', 'primevideo',
    'irctc', 'makemytrip', 'goibibo', 'cleartrip', 'bookmyshow',
    'phonepe', 'paytm', 'gpay', 'razorpay', 'cashfree'
]

OFFLINE_SIGNALS = [
    'pos', 'swipe', 'tap', 'nfc', 'contactless', 'retail', 'store',
    'mart', 'supermarket', 'petrol', 'bpcl', 'hpcl', 'iocl'
]

CATEGORIES = {
    'Food & Dining': ['swiggy', 'zomato', 'dominos', 'mcdonalds', 'kfc',
                      'restaurant', 'cafe', 'food', 'eat', 'pizza', 'burger', 'barbeque'],
    'Online Shopping': ['amazon', 'flipkart', 'myntra', 'ajio', 'meesho',
                         'nykaa', 'tatacliq', 'snapdeal'],
    'Grocery': ['bigbasket', 'blinkit', 'zepto', 'grofers', 'dmart',
                'supermarket', 'grocery', 'nature basket'],
    'Fuel': ['petrol', 'bpcl', 'hpcl', 'iocl', 'fuel', 'shell', 'essar'],
    'Transport': ['uber', 'ola', 'rapido', 'irctc', 'railway', 'metro',
                  'redbus', 'makemytrip', 'goibibo'],
    'Entertainment': ['netflix', 'hotstar', 'spotify', 'youtube', 'primevideo',
                       'cinema', 'pvr', 'inox', 'bookmyshow', 'zee5'],
    'Utilities & Bills': ['electricity', 'water', 'gas', 'broadband',
                           'airtel', 'jio', 'bsnl', 'recharge', 'tataplay'],
    'Health': ['pharmacy', 'hospital', 'clinic', 'medical',
               'apollo', 'practo', 'netmeds', '1mg', 'medplus'],
    'Travel': ['hotel', 'marriott', 'oyo', 'airbnb', 'flight', 'indigo',
               'air india', 'vistara', 'spicejet'],
    'Cash Advance': ['atm', 'cash advance', 'cash withdrawal']
}


def detect_channel(merchant: str, body: str) -> str:
    merchant_lower = merchant.lower()
    body_lower = body.lower()
    if any(m in merchant_lower for m in ONLINE_MERCHANTS):
        return 'online'
    if any(s in body_lower for s in OFFLINE_SIGNALS):
        return 'offline'
    if 'pos' in body_lower or 'point of sale' in body_lower:
        return 'offline'
    return 'online'


def categorise(merchant: str) -> str:
    merchant_lower = merchant.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in merchant_lower for k in keywords):
            return category
    return 'Other'


def clean_merchant(raw: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9\s\-\&\.]', '', raw)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:60]


def is_emi(body: str) -> bool:
    return any(s in body.lower() for s in ['emi', 'equated monthly', 'installment', 'no cost emi'])


def make_txn_id(date: str, merchant: str, amount: float, card: str) -> str:
    raw = f"{date}|{merchant.lower()}|{amount}|{card}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class EmailReader:

    def __init__(self):
        self.config = load_config()
        self.email_addr = os.getenv('GMAIL_ADDRESS')
        self.app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.transactions = []
        self.seen_ids = set()

    def connect(self):
        print("Connecting to Gmail...")
        self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
        self.mail.login(self.email_addr, self.app_password)
        self.mail.select('inbox')
        print("✅ Connected successfully")

    def fetch_transactions(self, days_back: int = None):
        days_back = days_back or self.config.get('fetch', {}).get('days_back', 90)
        max_per_bank = self.config.get('fetch', {}).get('max_emails_per_bank', 500)
        print(f"\nFetching bank emails from last {days_back} days...")
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')

        for bank_name, pattern in BANK_PATTERNS.items():
            print(f"  Checking {bank_name.upper()} emails...")
            senders = pattern['sender'] if isinstance(pattern['sender'], list) else [pattern['sender']]
            all_msgs = []
            for sender in senders:
                _, msgs = self.mail.search(None, f'FROM "{sender}" SINCE {cutoff}')
                if msgs[0]:
                    all_msgs.extend(msgs[0].split())
            if not all_msgs:
                print(f"  No emails from {bank_name.upper()}")
                continue
            count = 0
            for num in all_msgs[-max_per_bank:]:
                try:
                    _, data = self.mail.fetch(num, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    body = self._get_body(msg)
                    date_str = msg.get('Date', '')
                    if self._is_credit_email(body, pattern):
                        continue
                    txn = self._parse_transaction(body, date_str, bank_name, pattern)
                    if txn and txn['txn_id'] not in self.seen_ids:
                        self.seen_ids.add(txn['txn_id'])
                        self.transactions.append(txn)
                        count += 1
                except Exception:
                    continue
            print(f"  ✅ {count} transactions from {bank_name.upper()}")

    def _get_body(self, msg) -> str:
        if msg.is_multipart():
            plain, html = None, None
            for part in msg.walk():
                ctype = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if ctype == 'text/plain' and plain is None:
                        plain = payload.decode('utf-8', errors='replace')
                    elif ctype == 'text/html' and html is None:
                        html = payload.decode('utf-8', errors='replace')
                except Exception:
                    continue
            if plain:
                return plain
            if html:
                return BeautifulSoup(html, 'html.parser').get_text(separator=' ')
        try:
            return msg.get_payload(decode=True).decode('utf-8', errors='replace')
        except Exception:
            return ''

    def _is_credit_email(self, body: str, pattern: dict) -> bool:
        body_lower = body.lower()
        return any(s in body_lower for s in pattern.get('credit_signals', []))

    def _parse_transaction(self, body, date_str, bank, pattern) -> dict:
        try:
            amount_match  = re.search(pattern['amount'],   body, re.IGNORECASE)
            merchant_match = re.search(pattern['merchant'], body, re.IGNORECASE)
            card_match    = re.search(pattern['card'],     body, re.IGNORECASE)
            if not amount_match:
                return None
            amount = float(amount_match.group(1).replace(',', ''))
            if amount <= 0:
                return None
            merchant   = clean_merchant(merchant_match.group(1) if merchant_match else 'Unknown')
            card_last4 = card_match.group(1) if card_match else 'XXXX'
            try:
                txn_date = parsedate_to_datetime(date_str).strftime('%Y-%m-%d')
            except Exception:
                txn_date = datetime.now().strftime('%Y-%m-%d')
            card_name = self._resolve_card_name(bank, card_last4)
            channel   = detect_channel(merchant, body)
            emi       = is_emi(body)
            if 'atm' in body.lower() or 'cash advance' in body.lower():
                txn_type = 'CASH_ADVANCE'
            elif emi:
                txn_type = 'EMI'
            else:
                txn_type = 'PURCHASE'
            return {
                'txn_id':        make_txn_id(txn_date, merchant, amount, card_last4),
                'date':          txn_date,
                'merchant':      merchant,
                'amount':        amount,
                'category':      categorise(merchant),
                'channel':       channel,
                'bank':          bank.upper(),
                'card_last_four': card_last4,
                'card_name':     card_name,
                'type':          txn_type,
                'is_emi':        emi
            }
        except Exception:
            return None

    def _resolve_card_name(self, bank: str, last4: str) -> str:
        for card in self.config.get('cards', []):
            if card.get('bank', '').lower() == bank.lower() and str(card.get('last_four', '')) == str(last4):
                return card.get('name', f'{bank.upper()} Card')
        return f'{bank.upper()} XX{last4}'

    def save(self):
        if not self.transactions:
            print("\n⚠️  No transactions found")
            return
        os.makedirs('data', exist_ok=True)
        fieldnames = ['txn_id', 'date', 'merchant', 'amount', 'category',
                      'channel', 'bank', 'card_last_four', 'card_name', 'type', 'is_emi']
        with open('data/transactions.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.transactions)
        with open('data/transactions.json', 'w') as f:
            json.dump(self.transactions, f, indent=2)
        print(f"\n✅ Saved {len(self.transactions)} transactions")
        print(f"   CSV  → data/transactions.csv")
        print(f"   JSON → data/transactions.json")
        self._print_summary()

    def _print_summary(self):
        df = pd.DataFrame(self.transactions)
        spend_df = df[df['type'] == 'PURCHASE']
        print("\n── Summary ─────────────────────────────")
        print(f"Total transactions : {len(df)}")
        print(f"  └─ Purchases     : {len(spend_df)}")
        print(f"  └─ EMI           : {len(df[df['type']=='EMI'])}")
        print(f"  └─ Cash Advance  : {len(df[df['type']=='CASH_ADVANCE'])}")
        print(f"Total spend        : ₹{spend_df['amount'].sum():,.2f}")
        print(f"Date range         : {df['date'].min()} → {df['date'].max()}")
        print(f"\nBy category:")
        for cat, amt in spend_df.groupby('category')['amount'].sum().sort_values(ascending=False).items():
            print(f"  {cat:<25} ₹{amt:>10,.2f}")
        print(f"\nBy channel:")
        for ch, amt in spend_df.groupby('channel')['amount'].sum().items():
            print(f"  {ch:<25} ₹{amt:>10,.2f}")
        print(f"\nBy card:")
        for card, amt in spend_df.groupby('card_name')['amount'].sum().sort_values(ascending=False).items():
            print(f"  {card:<25} ₹{amt:>10,.2f}")
        print("─────────────────────────────────────────")


if __name__ == '__main__':
    reader = EmailReader()
    reader.connect()
    reader.fetch_transactions()
    reader.save()
