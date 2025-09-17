import sys
import subprocess
import os
import base64
from datetime import datetime, timedelta
import pandas as pd
import requests

# -------------------- Install dependencies if missing --------------------
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", package])

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    install("nepse-scraper")
    from nepse_scraper import Nepse_scraper

# -------------------- Scrape NEPSE Data (last 3 months) --------------------
request_obj = Nepse_scraper()

end_date = datetime.today()
start_date = end_date - timedelta(days=90)

filtered_data = []
columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

# Iterate through last 90 days
for i in range(90):
    day = end_date - timedelta(days=i)
    day_str = day.strftime("%Y-%m-%d")

    try:
        # Try fetching daily data
        daily_data = request_obj.get_today_price(date=day_str)  # nepse-scraper supports date param
        content_data = daily_data.get('content', [])

        if not content_data:
            print(f"⚠️ Market closed on {day_str}, skipping...")
            continue

        for item in content_data:
            symbol = item.get('symbol', '')
            open_price = item.get('openPrice', '')
            close_price = item.get('closePrice', '')
            volume_daily = int(item.get('totalTradedQuantity') or 0)

            filtered_data.append({
                'Symbol': symbol,
                'Date': day_str,
                'Open': open_price,
                'Close': close_price,
                'Volume': volume_daily
            })

    except Exception as e:
        print(f"❌ Failed to fetch {day_str}: {e}")
        continue

# Convert to DataFrame
df = pd.DataFrame(filtered_data, columns=columns)

if df.empty:
    print("⚠️ No data collected for last 3 months.")
    sys.exit(0)

# Sort by Date descending
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(by="Date", ascending=False)

# -------------------- Save CSV locally --------------------
today_day_name = datetime.now().strftime('%A')
file_name_local = f'nepse_last3months_{today_day_name}.csv'
df.to_csv(file_name_local, index=False)
print(f"✅ Data saved locally to '{file_name_local}'")

# -------------------- Upload CSV to GitHub --------------------
# Try GitHub Actions token first
token = os.getenv("GITHUB_TOKEN")

# Fallback to PAT for local runs
if not token:
    token = os.getenv("GH_PAT")
    if not token:
        print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
        sys.exit(1)
    else:
        print("✅ Using personal access token (GH_PAT)")

repo = "ChintanKoirala/NepseAnalysis"
branch = "main"
file_name_github = f"daily_data/nepse_last3months_{datetime.today().strftime('%Y-%m-%d')}.csv"
upload_url = f"https://api.github.com/repos/{repo}/contents/{file_name_github}"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# Convert DataFrame to base64
csv_base64 = base64.b64encode(df.to_csv(index=False).encode()).decode()

# Check if file exists
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
    payload["sha"] = sha  # update if file exists

# Upload
response = requests.put(upload_url, headers=headers, json=payload)

if response.status_code in [200, 201]:
    print(f"✅ File {file_name_github} uploaded successfully to GitHub!")
else:
    print(f"❌ Failed to upload {file_name_github}. Status code: {response.status_code}")
    print(response.json())
