# import sys
# import subprocess
# import os
# import base64
# from datetime import datetime

# # -------------------- Install dependencies if missing --------------------
# def install(package):
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", package])

# try:
#     from nepse_scraper import Nepse_scraper
# except ModuleNotFoundError:
#     install("nepse-scraper")
#     from nepse_scraper import Nepse_scraper

# try:
#     import pandas as pd
# except ModuleNotFoundError:
#     install("pandas")
#     import pandas as pd

# try:
#     import requests
# except ModuleNotFoundError:
#     install("requests")
#     import requests

# # -------------------- Scrape NEPSE Data --------------------
# request_obj = Nepse_scraper()
# today_price = request_obj.get_today_price()
# content_data = today_price.get('content', [])

# filtered_data = []
# columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

# for item in content_data:
#     symbol = item.get('symbol', '')
#     date = item.get('businessDate', '')
#     open_price = item.get('openPrice', '')
#     close_price = item.get('closePrice', '')
#     volume_daily = int(item.get('totalTradedQuantity') or 0)

#     filtered_data.append({
#         'Symbol': symbol,
#         'Date': date,
#         'Open': open_price,
#         'Close': close_price,
#         'Volume': volume_daily
#     })

# df = pd.DataFrame(filtered_data, columns=columns)

# # -------------------- Save CSV locally --------------------
# if not df.empty:
#     today_day_name = datetime.now().strftime('%A')
#     file_name_local = f'nepse_{today_day_name}.csv'
#     df.to_csv(file_name_local, index=False)
#     print(f"✅ Data saved locally to '{file_name_local}'")
# else:
#     print("⚠️ No data available to create DataFrame.")

# # -------------------- Upload CSV to GitHub --------------------
# # Try GitHub Actions token first
# token = os.getenv("GITHUB_TOKEN")

# # Fallback to personal access token (PAT) if running locally
# if not token:
#     token = os.getenv("GH_PAT")  # Create a secret for local runs
#     if not token:
#         print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
#         sys.exit(1)
#     else:
#         print("✅ Using personal access token from GH_PAT")

# repo = "ChintanKoirala/NepseAnalysis"
# branch = "main"
# file_name_github = f"daily_data/nepse_{datetime.today().strftime('%Y-%m-%d')}.csv"
# upload_url = f"https://api.github.com/repos/{repo}/contents/{file_name_github}"

# headers = {
#     "Authorization": f"Bearer {token}",
#     "Accept": "application/vnd.github.v3+json"
# }

# # Convert DataFrame to base64
# csv_base64 = base64.b64encode(df.to_csv(index=False).encode()).decode()

# # Check if file exists
# response = requests.get(upload_url, headers=headers)
# sha = None
# if response.status_code == 200:
#     sha = response.json().get("sha")

# payload = {
#     "message": f"Upload NEPSE data {datetime.today().strftime('%Y-%m-%d')}",
#     "content": csv_base64,
#     "branch": branch
# }
# if sha:
#     payload["sha"] = sha  # update if file exists

# # Upload
# response = requests.put(upload_url, headers=headers, json=payload)

# if response.status_code in [200, 201]:
#     print(f"✅ File {file_name_github} uploaded successfully to GitHub!")
# else:
#     print(f"❌ Failed to upload {file_name_github}. Status code: {response.status_code}")
#     print(response.json())
import sys
import subprocess
import os
import base64
from datetime import datetime

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

# -------------------- Scrape NEPSE Data --------------------
request_obj = Nepse_scraper()
today_price = request_obj.get_today_price()
content_data = today_price.get('content', [])

filtered_data = []
columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

for item in content_data:
    symbol = item.get('symbol', '')
    date = item.get('businessDate', '')
    open_price = item.get('openPrice', '')
    close_price = item.get('closePrice', '')
    volume_daily = int(item.get('totalTradedQuantity') or 0)

    filtered_data.append({
        'Symbol': symbol,
        'Date': date,
        'Open': open_price,
        'Close': close_price,
        'Volume': volume_daily
    })

df = pd.DataFrame(filtered_data, columns=columns)

# -------------------- Save CSV locally --------------------
if not df.empty:
    today_day_name = datetime.now().strftime('%A')
    file_name_local = f'nepse_{today_day_name}.csv'
    df.to_csv(file_name_local, index=False)
    print(f"✅ Data saved locally to '{file_name_local}'")
else:
    print("⚠️ No data available to create DataFrame.")

# -------------------- Upload CSV to GitHub --------------------
# Try GitHub Actions token first
token = os.getenv("GITHUB_TOKEN")

# Fallback to personal access token (PAT) if running locally
if not token:
    token = os.getenv("GH_PAT")  # Create a secret for local runs
    if not token:
        print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
        sys.exit(1)
    else:
        print("✅ Using personal access token from GH_PAT")

repo = "ChintanKoirala/NepseAnalysis"
branch = "main"
file_name_github = f"daily_data/nepse_{datetime.today().strftime('%Y-%m-%d')}.csv"
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
    "message": f"Upload NEPSE data {datetime.today().strftime('%Y-%m-%d')}",
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
