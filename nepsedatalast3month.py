import sys
import subprocess
import os
import base64
from datetime import datetime, timedelta

# -------------------- Install dependencies if missing --------------------
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", package])

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    install("nepse-scraper")
    from nepse_scraper import Nepse_scraper

try:
    import pandas as pd
except ModuleNotFoundError:
    install("pandas")
    import pandas as pd

try:
    import requests
except ModuleNotFoundError:
    install("requests")
    import requests

# -------------------- Scrape NEPSE Data (last 3 months, skip closed days) --------------------
request_obj = Nepse_scraper()

end_date = datetime.today()
start_date = end_date - timedelta(days=90)  # last 3 months

filtered_data = []
columns = ["Symbol", "Date", "Open", "Close", "Volume"]

# Loop through each day
date_cursor = start_date
while date_cursor <= end_date:
    try:
        # get_today_price also accepts a date string
        daily_data = request_obj.get_today_price(date_cursor.strftime("%Y-%m-%d"))
        content_data = daily_data.get("content", [])

        if not content_data:  # NEPSE closed
            print(f"⏩ Skipped {date_cursor.strftime('%Y-%m-%d')} (market closed)")
        else:
            for item in content_data:
                symbol = item.get("symbol", "")
                date = item.get("businessDate", "")
                open_price = item.get("openPrice", "")
                close_price = item.get("closePrice", "")
                volume_daily = int(item.get("totalTradedQuantity") or 0)

                filtered_data.append({
                    "Symbol": symbol,
                    "Date": date,
                    "Open": open_price,
                    "Close": close_price,
                    "Volume": volume_daily
                })

            print(f"✅ Collected data for {date_cursor.strftime('%Y-%m-%d')}")

    except Exception as e:
        print(f"⚠️ Failed to fetch {date_cursor.strftime('%Y-%m-%d')}: {e}")

    date_cursor += timedelta(days=1)

df = pd.DataFrame(filtered_data, columns=columns)

# Convert Date column to datetime and sort
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"])
    df.sort_values(by="Date", ascending=False, inplace=True)

# -------------------- Save CSV locally --------------------
if not df.empty:
    file_name_local = f'nepse_last_3_months.csv'
    df.to_csv(file_name_local, index=False)
    print(f"✅ Data saved locally to '{file_name_local}'")
else:
    print("⚠️ No trading data available in the last 3 months.")
    sys.exit(0)

# -------------------- Upload CSV to GitHub --------------------
token = os.getenv("GITHUB_TOKEN")

if not token:
    token = os.getenv("GH_PAT")
    if not token:
        print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
        sys.exit(1)
    else:
        print("✅ Using personal access token from GH_PAT")

repo = "ChintanKoirala/NepseAnalysis"
branch = "main"
file_name_github = f"daily_data/nepse_last_3_months.csv"
upload_url = f"https://api.github.com/repos/{repo}/contents/{file_name_github}"

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

csv_base64 = base64.b64encode(df.to_csv(index=False).encode()).decode()

response = requests.get(upload_url, headers=headers)
sha = None
if response.status_code == 200:
    sha = response.json().get("sha")

payload = {
    "message": f"Upload NEPSE last 3 months data {datetime.today().strftime('%Y-%m-%d')}",
    "content": csv_base64,
    "branch": branch
}
if sha:
    payload["sha"] = sha

response = requests.put(upload_url, headers=headers, json=payload)

if response.status_code in [200, 201]:
    print(f"✅ File {file_name_github} uploaded successfully to GitHub!")
else:
    print(f"❌ Failed to upload {file_name_github}.")
    print(f"Status: {response.status_code} - {response.reason}")
    print(response.text)
