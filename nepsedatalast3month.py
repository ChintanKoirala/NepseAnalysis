# nepsedatalast3month.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from joblib import Parallel, delayed
from nepse_scraper import Nepse_scraper   # ✅ correct class name

# -------------------- Settings --------------------
today = datetime.today().date()
start_date = today - timedelta(days=90)

# Initialize scraper
scraper = Nepse_scraper()

# -------------------- Fetch company list --------------------
companies = scraper.get_listed_companies()
symbols = [c['symbol'] for c in companies]

# -------------------- Fetch price history --------------------
def fetch_data(symbol):
    try:
        df = scraper.get_price_history(symbol, start_date, today)
        if df is not None and not df.empty:
            df["Symbol"] = symbol
            return df
    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")
    return pd.DataFrame()

results = Parallel(n_jobs=8)(delayed(fetch_data)(s) for s in symbols)
all_data = pd.concat(results, ignore_index=True)

# -------------------- Save raw data --------------------
raw_file = f"nepse_{today.strftime('%A')}.csv"
all_data.to_csv(raw_file, index=False)
print(f"✅ Raw daily data saved: {raw_file}")

# -------------------- Data cleaning --------------------
# Ensure numeric values
for col in ["Close", "52W_High", "52W_Low", "Open", "High", "Low", "Volume"]:
    if col in all_data.columns:
        all_data[col] = pd.to_numeric(all_data[col], errors="coerce")

# Drop rows missing critical values
all_data = all_data.dropna(subset=["Close", "52W_High", "52W_Low"])

# -------------------- Calculations --------------------
all_data["Pct_from_52W_High"] = (
    100 * all_data["Close"] / all_data["52W_High"]
)
all_data["Pct_from_52W_Low"] = (
    100 * all_data["Close"] / all_data["52W_Low"]
)

def pct_sign(x, high=True):
    if pd.isna(x):
        return ""
    if high:
        return f"-{100 - x:.2f}%" if x < 100 else f"+{x - 100:.2f}%"
    else:
        return f"+{x - 100:.2f}%" if x >= 100 else f"-{100 - x:.2f}%"

all_data["Pct_from_52W_High_Sign"] = all_data["Pct_from_52W_High"].apply(lambda x: pct_sign(x, high=True))
all_data["Pct_from_52W_Low_Sign"]  = all_data["Pct_from_52W_Low"].apply(lambda x: pct_sign(x, high=False))

# -------------------- Save cleaned file --------------------
clean_file = "nepse_cleaned.csv"
all_data.to_csv(clean_file, index=False)
print(f"✅ Cleaned data saved: {clean_file}")
print(all_data.head())
