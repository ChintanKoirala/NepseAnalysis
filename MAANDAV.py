


# this code calculates 9 days average vol  and 9 day moving average 

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

import pandas as pd
import requests
import re
from datetime import datetime

pd.options.mode.chained_assignment = None  # disable pandas warnings

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

df_today = pd.DataFrame([{
        'Symbol': item.get('symbol', ''),
        'Date': item.get('businessDate', ''),
        'Open': item.get('openPrice', 0),
        'Close': item.get('closePrice', 0),
        'Volume': item.get('totalTradedQuantity', 0)
    } for item in content], columns=COLUMNS)

if not df_today.empty:
    today_file = f"nepse_{datetime.now().strftime('%Y-%m-%d')}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Merge and Process --------------------
if not df_today.empty and LATEST_URL:
    try:
        # Read latest GitHub CSV safely
        df_latest = pd.read_csv(LATEST_URL, dtype=str)
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Force numeric columns
        for col in ['Open', 'Close', 'Volume']:
            df_latest[col] = pd.to_numeric(df_latest[col], errors='coerce')
            df_today[col] = pd.to_numeric(df_today[col], errors='coerce')

        # Merge
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date and sort
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol', 'Date'], inplace=True)

        # Drop invalid Close
        df_combined.dropna(subset=['Close'], inplace=True)

        # -------------------- Calculate Averages and RSI(13 Wilder) --------------------
        N = 13
        result_list = []

        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy()
            group.sort_values(by='Date', inplace=True)
            group.reset_index(drop=True, inplace=True)

            group['Avg_Vol_13D'] = group['Volume'].rolling(window=N, min_periods=1).mean()
            group['MA_3D'] = group['Close'].rolling(window=3, min_periods=1).mean()
            group['MA_13D'] = group['Close'].rolling(window=N, min_periods=1).mean()

            if len(group) < N + 1:
                continue  # skip if not enough data

            closes = group['Close']
            deltas = closes.diff()
            gains = deltas.clip(lower=0)
            losses = -deltas.clip(upper=0)

            # First average gain/loss
            avg_gain = gains.iloc[1:N+1].mean()
            avg_loss = losses.iloc[1:N+1].mean()

            rsi_values = [None] * len(closes)

            # Wilder smoothing
            for i in range(N + 1, len(closes)):
                current_gain = gains.iloc[i]
                current_loss = losses.iloc[i]

                avg_gain = ((avg_gain * (N - 1)) + current_gain) / N
                avg_loss = ((avg_loss * (N - 1)) + current_loss) / N

                if avg_loss == 0 and avg_gain == 0:
                    rsi = 50.0
                elif avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                rsi_values[i] = rsi

            group['RSI_13D'] = pd.Series(rsi_values, index=group.index)

            result_list.append(group.iloc[[-1]])  # keep last day

        if result_list:
            df_lastday = pd.concat(result_list, ignore_index=True)
        else:
            df_lastday = pd.DataFrame(columns=['Symbol', 'Date', 'Open', 'Close', 'Volume',
                                               'Avg_Vol_13D', 'MA_3D', 'MA_13D', 'RSI_13D'])

        # -------------------- Final Formatting --------------------
        df_lastday['Date'] = pd.to_datetime(df_lastday['Date']).dt.strftime('%Y-%m-%d')
        df_lastday['Avg_Vol_13D'] = df_lastday['Avg_Vol_13D'].fillna(0).astype(int)
        df_lastday['MA_3D'] = df_lastday['MA_3D'].round(2)
        df_lastday['MA_13D'] = df_lastday['MA_13D'].round(2)
        df_lastday['RSI_13D'] = df_lastday['RSI_13D'].round(2)

        df_final = df_lastday[['Symbol', 'Date', 'Open', 'Close', 'Volume',
                               'Avg_Vol_13D', 'MA_3D', 'MA_13D', 'RSI_13D']]

        df_final.sort_values(by='Symbol', inplace=True)
        df_final.reset_index(drop=True, inplace=True)
        df_final.index += 1
        df_final.index.name = 'S.N.'

        df_final.to_csv("completedata.csv", index=True)
        print("✅ File 'completedata.csv' saved successfully with RSI(13) using Wilder’s smoothing.")

    except Exception as e:
        print(f"⚠️ Failed to process and calculate: {e}")


# upload in github



import os
import sys
import base64
import requests
from datetime import datetime
import shutil

# -------------------- GitHub Config --------------------
REPO = "ChintanKoirala/NepseAnalysis"
BRANCH = "main"
UPLOAD_FOLDER = "daily_data"
LOCAL_FILE = "completedata.csv"  # Updated output file

# -------------------- Verify Local File --------------------
if not os.path.exists(LOCAL_FILE):
    print(f"❌ Output file '{LOCAL_FILE}' not found. Please run the NEPSE data script first.")
    sys.exit(1)

# Get today's date
today_date = datetime.now().strftime("%Y-%m-%d")
dated_filename = f"completedata_{today_date}.csv"

# Create a dated copy to preserve original
shutil.copy(LOCAL_FILE, dated_filename)
print(f"✅ Copied local file to '{dated_filename}' for upload.")

# -------------------- GitHub Token --------------------
token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
if not token:
    print("❌ GitHub token not found. Please set GITHUB_TOKEN or GH_PAT.")
    sys.exit(1)
else:
    print("✅ GitHub token loaded successfully.")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# -------------------- Prepare File for Upload --------------------
repo_path = f"{UPLOAD_FOLDER}/{dated_filename}"
upload_url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"

try:
    with open(dated_filename, "rb") as f:
        content = f.read()
    encoded_content = base64.b64encode(content).decode()
    print(f"ℹ️ File '{dated_filename}' read and encoded successfully.")
except Exception as e:
    print(f"❌ Failed to read '{dated_filename}': {e}")
    sys.exit(1)

# -------------------- Check if File Already Exists --------------------
sha = None
try:
    check_resp = requests.get(upload_url, headers=headers)
    if check_resp.status_code == 200:
        sha = check_resp.json().get("sha")
        print(f"ℹ️ File '{repo_path}' already exists in repo. It will be updated.")
    elif check_resp.status_code == 404:
        print(f"ℹ️ File '{repo_path}' does not exist. A new file will be created.")
    else:
        print(f"⚠️ Unexpected response ({check_resp.status_code}) while checking file.")
        print(check_resp.text)
except Exception as e:
    print(f"⚠️ Could not check file existence: {e}")

# -------------------- Upload to GitHub --------------------
payload = {
    "message": f"Upload completedata file for {today_date}",
    "content": encoded_content,
    "branch": BRANCH
}
if sha:
    payload["sha"] = sha

try:
    upload_resp = requests.put(upload_url, headers=headers, json=payload)
    if upload_resp.status_code in [200, 201]:
        print(f"✅ Successfully uploaded '{repo_path}' to GitHub repository.")
    else:
        print(f"❌ Upload failed! Status: {upload_resp.status_code}")
        print(upload_resp.text)
except Exception as e:
    print(f"❌ Exception during upload: {e}")


