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
MAX_DAYS = 60  # keep only latest 60 unique days

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
            raise ValueError("No combined_nepse file found")

        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))

        if not dates:
            raise ValueError("No valid dated files found")

        latest_date, latest_file = max(dates, key=lambda x: x[0])
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

    # ✅ FIX: Works for both list and dict responses
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

        # Combine old + new
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)

        # Remove duplicates
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert date
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')

        # Sort descending
        df_combined.sort_values(by='Date', ascending=False, inplace=True)

        # Keep only last MAX_DAYS unique dates
        recent_dates = df_combined['Date'].dropna().unique()[:MAX_DAYS]
        df_combined = df_combined[df_combined['Date'].isin(recent_dates)]

        # Format back to string
        df_combined['Date'] = df_combined['Date'].dt.strftime('%Y-%m-%d')

        # Save combined file
        df_combined.to_csv("combined_nepse.csv", index=False)
        print(f"✅ Combined CSV updated (last {MAX_DAYS} days kept)")

    except Exception as e:
        print(f"⚠️ Failed to merge with GitHub CSV: {e}")






# upload output files in github ripo
import os
import sys
import base64
import requests
from datetime import datetime

# -------------------- GitHub Config --------------------
repo = "ChintanKoirala/NepseAnalysis"
branch = "main"
local_file = "combined_nepse.csv"
repo_file = f"daily_data/combined_nepse_{datetime.today().strftime('%Y-%m-%d')}.csv"
upload_url = f"https://api.github.com/repos/{repo}/contents/{repo_file}"

# -------------------- Get GitHub Token --------------------
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

# -------------------- Check local file --------------------
if not os.path.exists(local_file):
    print(f"⚠️ Local file '{local_file}' does not exist. Exiting.")
    sys.exit(1)

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
        print(f"ℹ️ File '{repo_file}' exists in repo. It will be updated.")
    elif response.status_code == 404:
        print(f"ℹ️ File '{repo_file}' does not exist in repo. It will be created.")
    else:
        print(f"⚠️ Unexpected status {response.status_code} when checking repo.")
        print(response.json())
except Exception as e:
    print(f"⚠️ Failed to check file in repo: {e}")

# -------------------- Upload / Update --------------------
payload = {
    "message": f"Upload {repo_file} {datetime.today().strftime('%Y-%m-%d')}",
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
        print(f"❌ Failed to upload '{repo_file}'. Status code: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"❌ Exception during upload: {e}")
