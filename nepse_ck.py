# # this code abstracts todays necessary data from nepse scraper

# try:
#     from nepse_scraper import Nepse_scraper
# except ModuleNotFoundError:
#     import sys
#     import subprocess
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
#     from nepse_scraper import Nepse_scraper

# # -------------------- Imports --------------------
# import pandas as pd
# from datetime import datetime
# import os

# # -------------------- Create Scraper Object --------------------
# request_obj = Nepse_scraper()

# # -------------------- Fetch Today's Price Data --------------------
# try:
#     today_price = request_obj.get_today_price()
#     content_data = today_price.get('content', [])
# except Exception as e:
#     print(f"⚠️ Failed to fetch today's data: {e}")
#     content_data = []

# # -------------------- Process Data --------------------
# filtered_data = []

# # Columns (without High, Low, and Percent Change)
# columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

# for item in content_data:
#     symbol = item.get('symbol', '')
#     date = item.get('businessDate', '')
#     open_price = item.get('openPrice', 0)
#     close_price = item.get('closePrice', 0)
#     volume_daily = item.get('totalTradedQuantity', 0)  # traded quantity

#     filtered_data.append({
#         'Symbol': symbol,
#         'Date': date,
#         'Open': open_price,
#         'Close': close_price,
#         'Volume': volume_daily
#     })

# # -------------------- Create DataFrame --------------------
# df = pd.DataFrame(filtered_data, columns=columns)

# # Optional: sort by Symbol
# df = df.sort_values(by='Symbol')

# # -------------------- Save to CSV --------------------
# if not df.empty:
#     print(df.head())  # Show first 5 rows
#     today_date = datetime.now().strftime('%Y-%m-%d')
#     file_name = f"nepse_{today_date}.csv"
#     df.to_csv(file_name, index=False)
#     print(f"✅ Data saved to '{file_name}'")
# else:
#     print("⚠️ No data available to create DataFrame.")



# # upload todays data in github ripo
# import os
# import sys
# import base64
# import requests
# from datetime import datetime
# import pandas as pd

# # -------------------- Example DataFrame --------------------
# # Replace this with your actual NEPSE data DataFrame
# df = pd.DataFrame({
#     "Symbol": ["NABIL", "NICA"],
#     "Price": [750, 820],
#     "Volume": [1200, 900]
# })

# # -------------------- GitHub Token Handling --------------------
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
# else:
#     print("✅ Using GitHub Actions token")

# # -------------------- GitHub Repo Config --------------------
# repo = "ChintanKoirala/NepseAnalysis"
# branch = "main"
# file_name_github = f"daily_data/nepse_{datetime.today().strftime('%Y-%m-%d')}.csv"
# upload_url = f"https://api.github.com/repos/{repo}/contents/{file_name_github}"

# headers = {
#     "Authorization": f"Bearer {token}",
#     "Accept": "application/vnd.github.v3+json"
# }

# # -------------------- Convert DataFrame to Base64 --------------------
# csv_base64 = base64.b64encode(df.to_csv(index=False).encode()).decode()

# # -------------------- Check if File Already Exists --------------------
# response = requests.get(upload_url, headers=headers)
# sha = None
# if response.status_code == 200:
#     sha = response.json().get("sha")

# # -------------------- Prepare Payload --------------------
# payload = {
#     "message": f"Upload NEPSE data {datetime.today().strftime('%Y-%m-%d')}",
#     "content": csv_base64,
#     "branch": branch
# }
# if sha:
#     payload["sha"] = sha  # update if file exists

# # -------------------- Upload File --------------------
# response = requests.put(upload_url, headers=headers, json=payload)

# if response.status_code in [200, 201]:
#     print(f"✅ File {file_name_github} uploaded successfully to GitHub!")
# else:
#     print(f"❌ Failed to upload {file_name_github}. Status code: {response.status_code}")
#     print(response.json())
