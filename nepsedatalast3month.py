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
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
LATEST_URL = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data/espen_2025-09-18.csv"
MAX_DAYS = 60  # keep only latest 60 days

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
try:
    df_latest = pd.read_csv(LATEST_URL)

    # Ensure only required columns exist
    df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

    # Combine new + old
    df_combined = pd.concat([df_latest, df_today], ignore_index=True)

    # Drop duplicates (Symbol + Date unique)
    df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

    # Convert Date to datetime for sorting
    df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')

    # Sort by Date (descending)
    df_combined.sort_values(by='Date', ascending=False, inplace=True)

    # Keep only last MAX_DAYS
    unique_dates = df_combined['Date'].dropna().drop_duplicates().sort_values(ascending=False)
    cutoff_dates = unique_dates[:MAX_DAYS]  # latest 60 unique days
    df_combined = df_combined[df_combined['Date'].isin(cutoff_dates)]

    # Save combined
    df_combined.to_csv("combined_nepse.csv", index=False)
    print(f"✅ Combined CSV updated (last {MAX_DAYS} days kept)")
except Exception as e:
    print(f"⚠️ Failed to merge with GitHub CSV: {e}")

