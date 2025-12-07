


# this code calculates 9 days average vol  and 9 day moving average 
# -------------------- Auto install --------------------
try:
    from nepse_scraper import NepseScraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import NepseScraper

# -------------------- Imports --------------------
import pandas as pd
import requests
import re
from datetime import datetime
import urllib3

# -------------------- Disable SSL warnings --------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"

# -------------------- Find Latest combined_nepse File --------------------
def get_latest_combined_url():
    try:
        resp = requests.get(REPO_URL, verify=False)
        resp.raise_for_status()
        files = resp.json()

        combined_files = [
            f["name"] for f in files 
            if f["name"].startswith("combined_nepse_") and f["name"].endswith(".csv")
        ]

        if not combined_files:
            raise ValueError("No combined_nepse_* file found")

        dated_files = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dated_files.append((match.group(1), fname))

        latest_date, latest_file = max(dated_files, key=lambda x: x[0])
        print(f"📂 Latest GitHub file found: {latest_file}")
        return f"{RAW_BASE}/{latest_file}"

    except Exception as e:
        print(f"⚠️ Failed to fetch latest combined file: {e}")
        return None

LATEST_URL = get_latest_combined_url()

# -------------------- Fetch Today's NEPSE Data --------------------
scraper = NepseScraper(verify_ssl=False)

try:
    today_data = scraper.get_today_price()
    content = today_data.get('content', [])
except Exception as e:
    print(f"⚠️ Failed to fetch today's NEPSE data: {e}")
    content = []

# -------------------- Process Today's Data --------------------
rows = []
for item in content:
    rows.append({
        'Symbol': item.get('symbol', ''),
        'Date': item.get('businessDate', ''),
        'Open': item.get('openPrice', 0),
        'Close': item.get('closePrice', 0),
        'Volume': item.get('totalTradedQuantity', 0)
    })

df_today = pd.DataFrame(rows, columns=COLUMNS)

# -------------------- Save Today's File --------------------
if not df_today.empty:
    today_date = datetime.now().strftime('%Y-%m-%d')
    today_file = f"nepse_{today_date}.csv"
    df_today.to_csv(today_file, index=False)
    print(f"✅ Today's data saved as '{today_file}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Merge + Calculate RSI --------------------
if not df_today.empty and LATEST_URL:
    try:
        df_latest = pd.read_csv(LATEST_URL)
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol', 'Date'], inplace=True)

        N = 14
        output_rows = []

        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy().sort_values(by='Date')

            closes = pd.to_numeric(group['Close'], errors='coerce').dropna()
            if len(closes) < N + 3:
                continue

            delta = closes.diff()
            gains = delta.clip(lower=0)
            losses = -delta.clip(upper=0)

            rsi_values = []

            for offset in [0, 1, 2]:
                if len(closes) < N + 1 + offset:
                    rsi_values.append(None)
                    continue

                gp = gains.iloc[-(N + offset):-offset if offset != 0 else None]
                lp = losses.iloc[-(N + offset):-offset if offset != 0 else None]

                avg_gain = gp.mean()
                avg_loss = lp.mean()

                if avg_loss == 0 and avg_gain == 0:
                    rsi = 50.0
                elif avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                rsi_values.append(round(rsi, 2))

            last_row = group.iloc[[-1]].copy()
            last_row['Avg_Vol_9D'] = group['Volume'].rolling(9).mean().iloc[-1]
            last_row['MA_3D'] = group['Close'].rolling(3).mean().iloc[-1]
            last_row['MA_9D'] = group['Close'].rolling(9).mean().iloc[-1]

            last_row['Rsi_14D_Last'] = rsi_values[0]
            last_row['Rsi_14D_1D_Before'] = rsi_values[1]
            last_row['Rsi_14D_2D_Before'] = rsi_values[2]

            output_rows.append(last_row)

        if output_rows:
            df_final = pd.concat(output_rows, ignore_index=True)
        else:
            df_final = pd.DataFrame()

        if not df_final.empty:
            df_final['Date'] = pd.to_datetime(df_final['Date']).dt.strftime('%Y-%m-%d')
            df_final['Avg_Vol_9D'] = df_final['Avg_Vol_9D'].fillna(0).astype(int)
            df_final['MA_3D'] = df_final['MA_3D'].round(2)
            df_final['MA_9D'] = df_final['MA_9D'].round(2)

            df_final = df_final[['Symbol', 'Date', 'Open', 'Close', 'Volume',
                                 'Avg_Vol_9D', 'MA_3D', 'MA_9D',
                                 'Rsi_14D_Last', 'Rsi_14D_1D_Before', 'Rsi_14D_2D_Before']]

            df_final.sort_values(by='Symbol', inplace=True)
            df_final.reset_index(drop=True, inplace=True)
            df_final.index += 1
            df_final.index.name = 'S.N.'

            df_final.to_csv("completedata.csv", index=True)
            print("✅ File 'completedata.csv' saved successfully")

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


