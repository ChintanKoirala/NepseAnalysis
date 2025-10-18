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
import numpy as np
import requests
import re
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"
MAX_DAYS = 60  # keep only latest 60 unique days

# -------------------- Fetch Latest Combined File --------------------
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
        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))
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
filtered_data = [
    {
        'Symbol': item.get('symbol', ''),
        'Date': item.get('businessDate', ''),
        'Open': item.get('openPrice', 0),
        'Close': item.get('closePrice', 0),
        'Volume': item.get('totalTradedQuantity', 0)
    } for item in content
]

df_today = pd.DataFrame(filtered_data, columns=COLUMNS)

if not df_today.empty:
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_file = f"nepse_{today_date}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Wilder-smoothed RSI --------------------
def calculate_rsi_wilder(prices, period=14):
    prices = pd.Series(prices).astype(float).reset_index(drop=True)
    length = len(prices)
    rsi = pd.Series([np.nan] * length)
    if length < (period + 1):
        return rsi

    deltas = prices.diff()
    gains = deltas.clip(lower=0)
    losses = -deltas.clip(upper=0)

    avg_gain = gains.iloc[1:period+1].mean()
    avg_loss = losses.iloc[1:period+1].mean()

    if avg_gain == 0 and avg_loss == 0:
        rsi.iloc[period] = 50.0
    elif avg_loss == 0:
        rsi.iloc[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi.iloc[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, length):
        gain = gains.iloc[i]
        loss = losses.iloc[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_gain == 0 and avg_loss == 0:
            rsi_val = 50.0
        elif avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100 - (100 / (1 + rs))
        rsi.iloc[i] = round(rsi_val, 2)

    return rsi

# -------------------- Merge with Latest GitHub CSV --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol', 'Date'], inplace=True)

        result_list = []
        N = 14  # RSI period
        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy()
            group['Avg_Vol_9D'] = group['Volume'].rolling(window=9).mean()
            group['MA_3D'] = group['Close'].rolling(window=3).mean()
            group['MA_9D'] = group['Close'].rolling(window=9).mean()

            if len(group) >= (N + 1):
                rsi_series = calculate_rsi_wilder(group['Close'].values, period=N)
                group['RSI_14D'] = np.nan
                last_rsi = rsi_series.iloc[-1]
                if not np.isnan(last_rsi):
                    group.iloc[-1, group.columns.get_loc('RSI_14D')] = last_rsi

                group['Vol_Ratio'] = group['Volume'] / group['Avg_Vol_9D']

                # Buy/Sell Zone
                group['Remarks'] = ''
                row = group.iloc[-1]
                if row['MA_3D'] >= 1.01 * row['MA_9D'] and row['Vol_Ratio'] >= 0.4:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Buy Zone'
                elif row['MA_3D'] <= 0.99 * row['MA_9D'] and row['Vol_Ratio'] < 2.0:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Sell Zone'

                result_list.append(group.iloc[[-1]])

        if result_list:
            df_lastday = pd.concat(result_list, ignore_index=True)
        else:
            df_lastday = pd.DataFrame(columns=[
                'Symbol', 'Date', 'Open', 'Close', 'Volume',
                'Avg_Vol_9D', 'MA_3D', 'MA_9D', 'RSI_14D', 'Remarks'
            ])

        # -------------------- Refine Remarks --------------------
        def update_remarks(row):
            rsi = row['RSI_14D']
            vol_ratio = row['Vol_Ratio']
            vol = row['Volume']
            avg_vol = row['Avg_Vol_9D']
            remark = row['Remarks']

            if remark == 'Buy Zone':
                if rsi <= 60 and vol_ratio >= 1.2: remark = 'Strong Buy'
                if rsi <= 40 and vol_ratio >= 1.6: remark = 'Very Strong Buy'
                if rsi <= 40 and vol_ratio >= 2.0: remark = 'Very Very Strong Buy'
                if rsi > 60: remark = 'Overbought - Ready to Sell'
            elif remark == 'Sell Zone':
                if rsi < 70 and vol <= avg_vol: remark = 'Strong Sell'
                if rsi >= 70: remark = 'Very Very Strong Sell'
                if vol <= 0.9 * avg_vol: remark = 'Much Strong Sell'
                if vol <= 0.8 * avg_vol: remark = 'Very Much Strong Sell'
            return remark

        df_lastday['Remarks'] = df_lastday.apply(update_remarks, axis=1)

        # -------------------- Sort by Signal Strength --------------------
        signal_order = [
            'Very Very Strong Buy', 'Very Strong Buy', 'Strong Buy', 'Overbought - Ready to Sell',
            'Strong Sell', 'Much Strong Sell', 'Very Much Strong Sell', 'Very Very Strong Sell'
        ]
        df_lastday['Remarks'] = pd.Categorical(df_lastday['Remarks'], categories=signal_order, ordered=True)
        df_lastday.sort_values(by=['Remarks', 'Symbol'], inplace=True)

        df_lastday['Date'] = df_lastday['Date'].dt.strftime('%Y-%m-%d')
        df_lastday['Avg_Vol_9D'] = df_lastday['Avg_Vol_9D'].fillna(0).astype(int)
        df_lastday['MA_3D'] = df_lastday['MA_3D'].round(2)
        df_lastday['MA_9D'] = df_lastday['MA_9D'].round(2)

        df_lastday = df_lastday[['Symbol', 'Date', 'Open', 'Close', 'Volume',
                                 'Avg_Vol_9D', 'MA_3D', 'MA_9D', 'RSI_14D', 'Remarks']]

        df_lastday.reset_index(drop=True, inplace=True)
        df_lastday.index += 1
        df_lastday.index.name = 'S.N.'

        df_lastday.to_csv("filtered_nepse_signals.csv", index=True)
        print("✅ File 'filtered_nepse_signals.csv' saved successfully with updated criteria.")

    except Exception as e:
        print(f"⚠️ Failed to process and calculate: {e}")


# EMA cross calculation and signal generation


try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"

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

        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))
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

# -------------------- Helper: Wilder-smoothed RSI --------------------
def calculate_rsi_wilder(prices, period=9):
    """
    Returns a pandas Series of RSI values using Wilder's smoothing.
    RSI values will start appearing at index `period` (0-based).
    If there are fewer than period+1 prices, returns a series of NaNs.
    """
    prices = pd.Series(prices).astype(float).reset_index(drop=True)
    length = len(prices)
    rsi = pd.Series([np.nan] * length)

    if length < (period + 1):
        return rsi

    deltas = prices.diff()
    gains = deltas.clip(lower=0)
    losses = -deltas.clip(upper=0)

    # first average (simple mean of first `period` deltas: indices 1..period)
    avg_gain = gains.iloc[1:period+1].mean()
    avg_loss = losses.iloc[1:period+1].mean()

    # first RSI value at position `period`
    if avg_gain == 0 and avg_loss == 0:
        rsi.iloc[period] = 50.0
    elif avg_loss == 0:
        rsi.iloc[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi.iloc[period] = 100 - (100 / (1 + rs))

    # Wilder smoothing for subsequent values
    for i in range(period + 1, length):
        gain = gains.iloc[i]
        loss = losses.iloc[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_gain == 0 and avg_loss == 0:
            rsi_val = 50.0
        elif avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100 - (100 / (1 + rs))
        rsi.iloc[i] = rsi_val

    return rsi

# -------------------- Merge with Latest GitHub CSV --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Combine new and old
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date and sort
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol', 'Date'], inplace=True)

        # -------------------- Calculate Averages, RSI, and Remarks --------------------
        result_list = []
        N = 9  # RSI period (9)
        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy()
            group['Avg_Vol_9D'] = group['Volume'].rolling(window=9).mean()
            group['MA_3D'] = group['Close'].rolling(window=3).mean()
            group['MA_9D'] = group['Close'].rolling(window=9).mean()

            # Only calculate RSI if at least N+1 closes exist (need N deltas)
            if len(group) >= (N + 1):
                # compute RSI series using Wilder smoothing
                rsi_series = calculate_rsi_wilder(group['Close'].values, period=N)

                # create RSI_9D column and set last value
                group['RSI_9D'] = np.nan
                last_rsi = rsi_series.iloc[-1]
                if not np.isnan(last_rsi):
                    group.iloc[-1, group.columns.get_loc('RSI_9D')] = round(float(last_rsi), 2)

                # Calculate Vol_Ratio
                group['Vol_Ratio'] = group['Volume'] / group['Avg_Vol_9D']

                # Add initial Remarks column based on MA + Volume
                group['Remarks'] = ''
                if group.iloc[-1]['MA_3D'] >= group.iloc[-1]['MA_9D'] * 1.01 and group.iloc[-1]['Vol_Ratio'] >= 1.20:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Buy'
                elif group.iloc[-1]['MA_3D'] <= group.iloc[-1]['MA_9D'] * 0.99 and group.iloc[-1]['Vol_Ratio'] < 1.20:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Sell'

                result_list.append(group.iloc[[-1]])  # Keep only last traded day

        # Combine only symbols with >=N+1 days
        if result_list:
            df_lastday = pd.concat(result_list, ignore_index=True)
        else:
            df_lastday = pd.DataFrame(columns=[
                'Symbol', 'Date', 'Open', 'Close', 'Volume',
                'Avg_Vol_9D', 'MA_3D', 'MA_9D', 'RSI_9D', 'Remarks'
            ])

        # -------------------- Filtering Criteria --------------------
        df_filtered = df_lastday[
            ((df_lastday['MA_3D'] >= df_lastday['MA_9D'] * 1.01) & (df_lastday['Vol_Ratio'] >= 1.20)) |
            ((df_lastday['MA_3D'] <= df_lastday['MA_9D'] * 0.99) & (df_lastday['Vol_Ratio'] < 1.20))
        ].copy()

        # -------------------- Update Remarks Based on RSI and Volume --------------------
        def update_remarks(row):
            # Step 1: RSI-based update
            if row['Remarks'] == 'Buy':
                if row['RSI_9D'] > 60:
                    remark = 'Overbought - Ready to Sell'
                else:
                    remark = 'Strong Buy'
            elif row['Remarks'] == 'Sell':
                if row['RSI_9D'] >= 70:
                    remark = 'Very Very Strong Sell'
                else:
                    remark = 'Strong Sell'
            else:
                remark = row['Remarks']

            # Step 2: Volume-based refinement
            if remark == 'Strong Buy' and row['Volume'] >= 1.6 * row['Avg_Vol_9D']:
                remark = 'Very Strong Buy'
            if remark == 'Strong Sell' and row['Volume'] <= 0.8 * row['Avg_Vol_9D']:
                remark = 'Much Strong Sell'

            # Step 3: Additional refinement
            if remark == 'Very Strong Buy' and row['RSI_9D'] <= 40:
                remark = 'Very Very Strong Buy'
            if remark == 'Much Strong Sell' and row['Volume'] <= 0.6 * row['Avg_Vol_9D']:
                remark = 'Very Much Strong Sell'

            return remark

        df_filtered['Remarks'] = df_filtered.apply(update_remarks, axis=1)

        # -------------------- Sort Stocks by Common Signal (Remarks) --------------------
        signal_order = [
            'Very Very Strong Buy',
            'Very Strong Buy',
            'Strong Buy',
            'Overbought - Ready to Sell',
            'Strong Sell',
            'Much Strong Sell',
            'Very Much Strong Sell',
            'Very Very Strong Sell'
        ]
        df_filtered['Remarks'] = pd.Categorical(df_filtered['Remarks'], categories=signal_order, ordered=True)
        df_filtered.sort_values(by=['Remarks', 'Symbol'], inplace=True)

        # -------------------- Final Formatting --------------------
        df_filtered['Date'] = df_filtered['Date'].dt.strftime('%Y-%m-%d')
        df_filtered['Avg_Vol_9D'] = df_filtered['Avg_Vol_9D'].fillna(0).astype(int)
        df_filtered['MA_3D'] = df_filtered['MA_3D'].round(2)
        df_filtered['MA_9D'] = df_filtered['MA_9D'].round(2)

        df_filtered = df_filtered[['Symbol', 'Date', 'Open', 'Close', 'Volume',
                                   'Avg_Vol_9D', 'MA_3D', 'MA_9D', 'RSI_9D', 'Remarks']]

        df_filtered.reset_index(drop=True, inplace=True)
        df_filtered.index += 1
        df_filtered.index.name = 'S.N.'

        # -------------------- Save Final Output --------------------
        df_filtered.to_csv("filtered_nepse_signals.csv", index=True)
        print("✅ File 'filtered_nepse_signals.csv' saved successfully with signals grouped serially by type.")

    except Exception as e:
        print(f"⚠️ Failed to process and calculate: {e}")











# upload output files in github ripo





import os
import sys
import base64
import requests
import glob
from datetime import datetime

# -------------------- GitHub Config --------------------
repo = "ChintanKoirala/NepseAnalysis"
branch = "main"

# -------------------- Detect filtered signals file --------------------
local_file = None
last_traded_date = None

# 1️⃣ Try to find dated file first (preferred)
signal_files = sorted(glob.glob("filtered_nepse_signals_*.csv"), reverse=True)
if signal_files:
    local_file = signal_files[0]
    last_traded_date = local_file.replace("filtered_nepse_signals_", "").replace(".csv", "")
else:
    # 2️⃣ If not found, fallback to undated file
    if os.path.exists("filtered_nepse_signals.csv"):
        local_file = "filtered_nepse_signals.csv"
        last_traded_date = datetime.now().strftime("%Y-%m-%d")
    else:
        print("❌ No filtered_nepse_signals file found locally. Exiting.")
        sys.exit(1)

repo_file = f"daily_data/filtered_nepse_signals_{last_traded_date}.csv"
upload_url = f"https://api.github.com/repos/{repo}/contents/{repo_file}"

print(f"✅ Found filtered signals file: {local_file}")

# -------------------- GitHub Token --------------------
token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
if not token:
    print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
    sys.exit(1)
else:
    print("✅ Using GitHub token.")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# -------------------- Read & encode file --------------------
try:
    with open(local_file, "rb") as f:
        content = f.read()
    encoded_content = base64.b64encode(content).decode()
    print(f"ℹ️ File '{local_file}' read successfully.")
except Exception as e:
    print(f"❌ Failed to read '{local_file}': {e}")
    sys.exit(1)

# -------------------- Check if file exists in repo --------------------
sha = None
try:
    response = requests.get(upload_url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get("sha")
        print(f"ℹ️ File '{repo_file}' exists. It will be updated.")
    elif response.status_code == 404:
        print(f"ℹ️ File '{repo_file}' does not exist. It will be created.")
    else:
        print(f"⚠️ Unexpected status {response.status_code} when checking repo.")
        print(response.json())
except Exception as e:
    print(f"⚠️ Failed to check file in repo: {e}")

# -------------------- Upload / Update --------------------
payload = {
    "message": f"Upload filtered_nepse_signals file for {last_traded_date}",
    "content": encoded_content,
    "branch": branch
}
if sha:
    payload["sha"] = sha

try:
    response = requests.put(upload_url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        print(f"✅ File '{repo_file}' uploaded successfully!")
    else:
        print(f"❌ Upload failed. Status: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"❌ Exception during upload: {e}")






