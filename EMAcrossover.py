# this code abstracts todays necessary data from nepse scraper

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
from datetime import datetime
import os

# -------------------- Create Scraper Object --------------------
request_obj = Nepse_scraper()

# -------------------- Fetch Today's Price Data --------------------
try:
    today_price = request_obj.get_today_price()
    content_data = today_price.get('content', [])
except Exception as e:
    print(f"⚠️ Failed to fetch today's data: {e}")
    content_data = []

# -------------------- Process Data --------------------
filtered_data = []

# Columns (without High, Low, and Percent Change)
columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

for item in content_data:
    symbol = item.get('symbol', '')
    date = item.get('businessDate', '')
    open_price = item.get('openPrice', 0)
    close_price = item.get('closePrice', 0)
    volume_daily = item.get('totalTradedQuantity', 0)  # traded quantity

    filtered_data.append({
        'Symbol': symbol,
        'Date': date,
        'Open': open_price,
        'Close': close_price,
        'Volume': volume_daily
    })

# -------------------- Create DataFrame --------------------
df = pd.DataFrame(filtered_data, columns=columns)

# Optional: sort by Symbol
df = df.sort_values(by='Symbol')

# -------------------- Save to CSV --------------------
if not df.empty:
    print(df.head())  # Show first 5 rows
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f"nepse_{today_date}.csv"
    df.to_csv(file_name, index=False)
    print(f"✅ Data saved to '{file_name}'")
else:
    print("⚠️ No data available to create DataFrame.")




# this code combines last traded day data from nepse and combines it with other latest data for 60 days only

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
import requests
import re
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"
MAX_DAYS = 60  # keep only latest 60 unique days

# -------------------- Find Latest combined_nepse File --------------------
def get_latest_combined_url():
    try:
        resp = requests.get(REPO_URL)
        resp.raise_for_status()
        files = resp.json()
        combined_files = [
            f["name"] for f in files if f["name"].startswith("combined_nepse_") and f["name"].endswith(".csv")
        ]
        if not combined_files:
            raise ValueError("No combined_nepse_*.csv file found in repo")

        # Extract dates and find latest
        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))
        if not dates:
            raise ValueError("No valid dated combined_nepse file found")

        latest_date, latest_file = max(dates, key=lambda x: x[0])
        print(f"📂 Latest GitHub file found: {latest_file}")
        return f"{RAW_BASE}/{latest_file}"
    except Exception as e:
        print(f"⚠️ Failed to fetch latest combined file: {e}")
        return None

LATEST_URL = get_latest_combined_url()

# -------------------- Fetch Today's NEPSE Data --------------------
scraper = Nepse_scraper()
try:
    today_data = scraper.get_today_price()
    content = today_data.get('content', [])
except Exception as e:
    print(f"⚠️ Failed to fetch today's NEPSE data: {e}")
    content = []

# -------------------- Process Today's Data --------------------
filtered_data = []
for item in content:
    filtered_data.append({
        'Symbol': item.get('symbol', ''),
        'Date': item.get('businessDate', ''),
        'Open': item.get('openPrice', 0),
        'Close': item.get('closePrice', 0),
        'Volume': item.get('totalTradedQuantity', 0)
    })

df_today = pd.DataFrame(filtered_data, columns=COLUMNS)

# -------------------- Save Today's File --------------------
if not df_today.empty:
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_file = f"nepse_{today_date}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Merge with Latest GitHub CSV --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)

        # Keep only expected columns
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Combine new + old
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)

        # Drop duplicates (Symbol + Date unique)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date to datetime
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')

        # Sort descending
        df_combined.sort_values(by='Date', ascending=False, inplace=True)

        # Keep only latest MAX_DAYS unique dates
        recent_dates = df_combined['Date'].dropna().unique()[:MAX_DAYS]
        df_combined = df_combined[df_combined['Date'].isin(recent_dates)]

        # Ensure Date formatted back to string
        df_combined['Date'] = df_combined['Date'].dt.strftime('%Y-%m-%d')

        # Save combined
        df_combined.to_csv("combined_nepse.csv", index=False)
        print(f"✅ Combined CSV updated (last {MAX_DAYS} days kept)")
    except Exception as e:
        print(f"⚠️ Failed to merge with GitHub CSV: {e}")




# EMA cross calculation and signal generation
try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
import requests
import re
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"
MAX_DAYS = 60  # keep only latest 60 unique days

# -------------------- Find Latest combined_nepse File --------------------
def get_latest_combined_url():
    try:
        resp = requests.get(REPO_URL)
        resp.raise_for_status()
        files = resp.json()
        combined_files = [
            f["name"] for f in files if f["name"].startswith("combined_nepse_") and f["name"].endswith(".csv")
        ]
        if not combined_files:
            raise ValueError("No combined_nepse_*.csv file found in repo")

        # Extract dates and find latest
        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))
        if not dates:
            raise ValueError("No valid dated combined_nepse file found")

        latest_date, latest_file = max(dates, key=lambda x: x[0])
        print(f"📂 Latest GitHub file found: {latest_file}")
        return f"{RAW_BASE}/{latest_file}"
    except Exception as e:
        print(f"⚠️ Failed to fetch latest combined file: {e}")
        return None

LATEST_URL = get_latest_combined_url()

# -------------------- Fetch Today's NEPSE Data --------------------
scraper = Nepse_scraper()
try:
    today_data = scraper.get_today_price()
    content = today_data.get('content', [])
except Exception as e:
    print(f"⚠️ Failed to fetch today's NEPSE data: {e}")
    content = []

# -------------------- Process Today's Data --------------------
filtered_data = []
for item in content:
    filtered_data.append({
        'Symbol': item.get('symbol', ''),
        'Date': item.get('businessDate', ''),
        'Open': item.get('openPrice', 0),
        'Close': item.get('closePrice', 0),
        'Volume': item.get('totalTradedQuantity', 0)
    })

df_today = pd.DataFrame(filtered_data, columns=COLUMNS)

# -------------------- Save Today's File --------------------
if not df_today.empty:
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_file = f"nepse_{today_date}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Merge with Latest GitHub CSV --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)

        # Keep only expected columns
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Combine new + old
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)

        # Drop duplicates (Symbol + Date unique)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date to datetime
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')

        # Sort descending
        df_combined.sort_values(by='Date', ascending=False, inplace=True)

        # Keep only latest MAX_DAYS unique dates
        recent_dates = df_combined['Date'].dropna().unique()[:MAX_DAYS]
        df_combined = df_combined[df_combined['Date'].isin(recent_dates)]

        # Ensure Date formatted back to string
        df_combined['Date'] = df_combined['Date'].dt.strftime('%Y-%m-%d')

        # -------------------- Indicator Calculation --------------------
        df_combined['Remarks'] = ""

        for symbol, group in df_combined.groupby("Symbol"):
            group_sorted = group.sort_values(by="Date", ascending=False).head(2)  # last 2 days
            if len(group_sorted) < 2:
                continue

            last_close = group_sorted.iloc[0]['Close']
            prev_close = group_sorted.iloc[1]['Close']
            last_vol = group_sorted.iloc[0]['Volume']
            avg_vol = group_sorted['Volume'].mean()

            ma1 = last_close  # 1-day MA
            ma2 = (last_close + prev_close) / 2  # 2-day MA

            if ma1 > ma2:  # bullish crossover
                remark = "Strong Buy" if last_vol > avg_vol else "Buy"
            elif ma2 > ma1:  # bearish crossover
                remark = "Strong Sell" if last_vol < avg_vol else "Sell"
            else:
                remark = ""

            df_combined.loc[
                (df_combined['Symbol'] == symbol) & (df_combined['Date'] == group_sorted.iloc[0]['Date']),
                'Remarks'
            ] = remark

        # Save combined file
        df_combined.to_csv("combined_nepse.csv", index=False)
        print(f"✅ Combined CSV updated with signals (last {MAX_DAYS} days kept)")

        # -------------------- Display Today's Signals --------------------
        df_today_signals = df_combined[(df_combined['Date'] == today_date) & (df_combined['Remarks'] != "")]
        if not df_today_signals.empty:
            df_today_signals = df_today_signals.reset_index(drop=True)
            df_today_signals.index += 1  # make serial numbers start at 1
            print("\n📊 Today's Stocks with Signals:")
            print(df_today_signals[['Symbol', 'Close', 'Volume', 'Remarks']])
        else:
            print("\nℹ️ No signals generated for today.")

    except Exception as e:
        print(f"⚠️ Failed to merge with GitHub CSV: {e}")







