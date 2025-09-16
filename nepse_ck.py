from nepse_scraper import Nepse_scraper
import pandas as pd
from datetime import datetime
import requests
import base64
import os

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
    volume_daily = item.get('totalTradedQuantity', 0)

    filtered_data.append({
        'Symbol': symbol,
        'Date': date,
        'Open': open_price,
        'Close': close_price,
        'Volume': volume_daily
    })

df = pd.DataFrame(filtered_data, columns=columns)

if not df.empty:
    today_day_name = datetime.now().strftime('%A')
    file_name_local = f'nepse_{today_day_name}.csv'
    df.to_csv(file_name_local, index=False)
    print(f"Data saved locally to '{file_name_local}'")
else:
    print("No data available to create DataFrame.")

# -------------------- Upload to GitHub --------------------
# Use environment variable for token (safer)
token = os.getenv('GITHUB_TOKEN')  # Set this in GitHub Actions Secrets
if not token:
    raise ValueError("GitHub token not found. Set GITHUB_TOKEN environment variable.")

repo = 'ChintanKoirala/NepseAnalysis'
branch = 'main'
file_name_github = f'espen_{datetime.today().strftime("%Y-%m-%d")}.csv'
upload_url = f'https://api.github.com/repos/{repo}/contents/{file_name_github}'

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json'
}

# Convert DataFrame to Base64
csv_base64 = base64.b64encode(df.to_csv(index=False).encode()).decode()

# Check if file already exists
response = requests.get(upload_url, headers=headers)
payload = {
    'message': f'Upload {file_name_github}',
    'content': csv_base64,
    'branch': branch
}

if response.status_code == 200:
    # File exists, include SHA to update
    sha = response.json()['sha']
    payload['sha'] = sha

# Upload (or update) file
response = requests.put(upload_url, headers=headers, json=payload)

if response.status_code in [200, 201]:
    print(f'File {file_name_github} uploaded successfully!')
else:
    print(f'Failed to upload {file_name_github}. Status code: {response.status_code}')
    print(response.json())


    
