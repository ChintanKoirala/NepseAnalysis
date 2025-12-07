# this code abstracts todays necessary data from nepse scraper

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
RSI_PERIOD = 14

# -------------------- Fetch Latest GitHub CSV --------------------
def get_latest_combined_url():
    try:
        resp = requests.get(REPO_URL)
        resp.raise_for_status()
        files = resp.json()
        combined_files = [f["name"] for f in files if f["name"].startswith("combined_nepse_") and f["name"].endswith(".csv")]
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
# Fix SSL verification error by disabling SSL check
scraper = Nepse_scraper(verify_ssl=False)

try:
    today_data = scraper.get_today_price()
    if isinstance(today_data, dict):
        content = today_data.get('content', [])
    elif isinstance(today_data, list):
        content = today_data
    else:
        content = []
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
    today_file = f"nepse_{datetime.now().strftime('%Y-%m-%d')}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Standard RSI Calculation --------------------
def calculate_rsi_standard(prices, period=14):
    prices = pd.Series(prices).astype(float).reset_index(drop=True)
    rsi = pd.Series([np.nan] * len(prices))
    if len(prices) < period + 1:
        return rsi
    for i in range(period, len(prices)):
        window = prices[i - period:i + 1]
        deltas = window.diff().dropna()
        gains = deltas[deltas > 0].sum()
        losses = -deltas[deltas < 0].sum()
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            rsi_val = 100.0
        elif avg_gain == 0:
            rsi_val = 0.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100 - (100 / (1 + rs))
        rsi.iloc[i] = round(rsi_val, 1)
    return rsi

# -------------------- Merge and Process --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Combine old + today
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol','Date'], inplace=True)

        result_list = []
        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy()
            group['Avg_Vol_9D'] = group['Volume'].rolling(9).mean()
            group['MA_3D'] = group['Close'].rolling(3).mean()
            group['MA_9D'] = group['Close'].rolling(9).mean()
            group['Vol_Ratio'] = group['Volume'] / group['Avg_Vol_9D']

            if len(group) >= RSI_PERIOD + 3:
                rsi_series = calculate_rsi_standard(group['Close'].values, period=RSI_PERIOD)
                group['RSI_14D_Last'] = np.nan
                group['RSI_14D_1DayBefore'] = np.nan
                group['RSI_14D_2DaysBefore'] = np.nan

                group.iloc[-1, group.columns.get_loc('RSI_14D_Last')] = rsi_series.iloc[-1]
                group.iloc[-1, group.columns.get_loc('RSI_14D_1DayBefore')] = rsi_series.iloc[-2]
                group.iloc[-1, group.columns.get_loc('RSI_14D_2DaysBefore')] = rsi_series.iloc[-3]

                # Remarks logic
                def update_remarks(row):
                    rsi_last = row['RSI_14D_Last']
                    rsi_prev1 = row['RSI_14D_1DayBefore']
                    rsi_prev2 = row['RSI_14D_2DaysBefore']
                    ma3, ma9 = row['MA_3D'], row['MA_9D']
                    vol_ratio = row['Vol_Ratio']
                    vol, avg_vol = row['Volume'], row['Avg_Vol_9D']
                    remark = ''

                    # Buy Zone
                    if ma3 >= ma9 and vol_ratio >= 0.4:
                        if (rsi_last < 60) and (rsi_last > rsi_prev1 > rsi_prev2) and (vol_ratio >= 1.5):
                            remark = 'Very Strong Buy'
                        elif (rsi_last < 60) and (rsi_last > rsi_prev1 > rsi_prev2) and (vol_ratio >= 1.0):
                            remark = 'Strong Buy'
                        elif rsi_last >= 60:
                            remark = 'Overbought – Ready to Sell'
                        else:
                            remark = 'Buy Zone'
                    # Sell Zone
                    elif ma3 <= ma9 and vol_ratio < 3.0:
                        if (rsi_last < 70) and (rsi_last < rsi_prev1 < rsi_prev2) and (vol <= 0.7 * avg_vol):
                            remark = 'Very Strong Sell'
                        elif (rsi_last < 70) and (rsi_last < rsi_prev1 < rsi_prev2) and (vol <= avg_vol):
                            remark = 'Strong Sell'
                        else:
                            remark = 'Sell Zone'
                    else:
                        remark = 'Hold'
                    return remark

                group['Remarks'] = group.apply(update_remarks, axis=1)
                result_list.append(group.iloc[[-1]])

        df_lastday = pd.concat(result_list, ignore_index=True) if result_list else pd.DataFrame(columns=[
            'Symbol','Date','Open','Close','Volume','Avg_Vol_9D','MA_3D','MA_9D',
            'RSI_14D_Last','RSI_14D_1DayBefore','RSI_14D_2DaysBefore','Remarks'
        ])

        # Sort and format
        signal_order = [
            'Very Strong Buy', 'Strong Buy', 'Overbought – Ready to Sell',
            'Very Strong Sell', 'Strong Sell',
            'Buy Zone', 'Sell Zone', 'Hold'
        ]
        df_lastday['Remarks'] = pd.Categorical(df_lastday['Remarks'], categories=signal_order, ordered=True)
        df_lastday.sort_values(by=['Remarks','Symbol'], inplace=True)

        df_lastday['Date'] = pd.to_datetime(df_lastday['Date']).dt.strftime('%Y-%m-%d')
        df_lastday['Avg_Vol_9D'] = df_lastday['Avg_Vol_9D'].fillna(0).astype(int)
        df_lastday['MA_3D'] = df_lastday['MA_3D'].round(2)
        df_lastday['MA_9D'] = df_lastday['MA_9D'].round(2)
        df_lastday['RSI_14D_Last'] = df_lastday['RSI_14D_Last'].round(1)
        df_lastday['RSI_14D_1DayBefore'] = df_lastday['RSI_14D_1DayBefore'].round(1)
        df_lastday['RSI_14D_2DaysBefore'] = df_lastday['RSI_14D_2DaysBefore'].round(1)

        df_lastday = df_lastday[['Symbol','Date','Open','Close','Volume','Avg_Vol_9D','MA_3D','MA_9D',
                                 'RSI_14D_Last','RSI_14D_1DayBefore','RSI_14D_2DaysBefore','Remarks']]
        df_lastday.reset_index(drop=True, inplace=True)
        df_lastday.index += 1
        df_lastday.index.name = 'S.N.'

        df_lastday.to_csv("filtered_nepse_signals.csv", index=True)
        print("✅ File 'filtered_nepse_signals.csv' saved successfully with SSL fix.")

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






