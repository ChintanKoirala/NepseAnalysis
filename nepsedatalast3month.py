import pandas as pd
import numpy as np
from nepse_scraper import NepseScraper
from joblib import Parallel, delayed
import datetime

# Initialize scraper
scraper = NepseScraper()

# Get today's date
today = datetime.date.today()
start_date = today - datetime.timedelta(days=90)

# Fetch historical data for all companies
companies = scraper.get_listed_companies()
symbols = [c['symbol'] for c in companies]

def fetch_data(symbol):
    try:
        df = scraper.get_price_history(symbol, start_date, today)
        if df is not None and not df.empty:
            df['Symbol'] = symbol
            return df
    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")
    return pd.DataFrame()

results = Parallel(n_jobs=8)(delayed(fetch_data)(s) for s in symbols)
all_data = pd.concat(results, ignore_index=True)

# Save daily data
all_data.to_csv(f"nepse_{today.strftime('%A')}.csv", index=False)
print(f"✅ Daily data saved to 'nepse_{today.strftime('%A')}.csv'")
print(all_data.head())

# --- Data Cleaning ---
numeric_cols = ["Close", "52W_High", "52W_Low"]
for col in numeric_cols:
    if col in all_data.columns:
        all_data[col] = pd.to_numeric(all_data[col], errors="coerce")

# Drop rows where critical data is missing
all_data = all_data.dropna(subset=["Close", "52W_High", "52W_Low"])

# --- Calculations ---
all_data['Pct_from_52W_High'] = (
    100 * all_data['Close'] / all_data['52W_High']
)
all_data['Pct_from_52W_Low'] = (
    100 * all_data['Close'] / all_data['52W_Low']
)

# Add % difference signs
all_data['Pct_from_52W_High_Sign'] = (
    (all_data['Pct_from_52W_High'] - 100).round(2).astype(str) + "%"
)
all_data['Pct_from_52W_Low_Sign'] = (
    (all_data['Pct_from_52W_Low'] - 100).round(2).astype(str) + "%"
)

# Save cleaned file
all_data.to_csv("nepse_cleaned.csv", index=False)
print("✅ Cleaned data saved to 'nepse_cleaned.csv'")
print(all_data.head())
