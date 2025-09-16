!pip install nepse-scraper
!pip install xlsxwriter
!pip install gitpython
!pip install gitpython pandas
from nepse_scraper import Nepse_scraper
import pandas as pd
from datetime import datetime

# Create an object from the Nepse_scraper class
request_obj = Nepse_scraper()

# Get today's price from NEPSE
today_price = request_obj.get_today_price()

# Extract the 'content' section
content_data = today_price.get('content', [])

# Initialize an empty list to store filtered data
filtered_data = []

# Define the column names
columns = ['Symbol', 'Date', 'Open', 'Close', 'Volume']

# Iterate over each item in the 'content' section
for item in content_data:
    symbol = item.get('symbol', '')
    date = item.get('businessDate', '')
    open_price = item.get('openPrice', '')
    close_price = item.get('closePrice', '')
    volume_daily = item.get('totalTradedQuantity', 0)   # ✅ exact traded shares

    # Append filtered values
    filtered_data.append({
        'Symbol': symbol,
        'Date': date,
        'Open': open_price,
        'Close': close_price,
        'Volume': volume_daily
    })

# Create DataFrame
df = pd.DataFrame(filtered_data, columns=columns)

if not df.empty:
    # Show DataFrame
    print(df)

    # Save with today's weekday in filename
    today_day_name = datetime.now().strftime('%A')
    file_name = f'nepse_{today_day_name}.csv'
    df.to_csv(file_name, index=False)

    print(f"Data saved to '{file_name}'")
else:
    print("No data available to create DataFrame.")
import requests
from datetime import datetime
import base64

# Assuming you have finall_df DataFrame containing your data
# Assuming finall_df is defined elsewhere in your code

try:
    # Convert finall_df to CSV format
    csv_data = df.to_csv(index=False)

    # Encode the CSV data to Base64
    csv_data_base64 = base64.b64encode(csv_data.encode()).decode()

    # Define the GitHub repository URL
    repo_url = 'https://github.com/ChintanKoirala/NepseAnalysis'

    # Define the file name with today's date
    file_name = f'espen_{datetime.today().strftime("%Y-%m-%d")}.csv'

    # Define your personal access token
    token = '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'

    # Define the file path in the repository
    file_path = f'/{file_name}'

    # Define the API URL for uploading files to GitHub
    upload_url = f'https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents{file_path}'

    # Prepare the headers with the authorization token
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Prepare the payload with file content
    payload = {
        'message': f'Upload {file_name}',
        'content': csv_data_base64,
        'branch': 'main'  # Specify the branch you want to upload to
    }

    # Send a PUT request to upload the file
    response = requests.put(upload_url, headers=headers, json=payload)

    # Check the response status
    if response.status_code == 200:
        print(f'File {file_name} uploaded successfully!')
    elif response.status_code == 422:
        print(f'Failed to upload {file_name}. Status code: 422 Unprocessable Entity')
        print('Error Message:', response.json()['message'])
    else:
        print(f'Failed to upload {file_name}. Status code: {response.status_code}')
        # print('Response Content:', response.text)

except Exception as e:
    print('An error occurred:', e)
