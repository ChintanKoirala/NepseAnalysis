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

try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
import requests
import re
from datetime import datetime

# -------------------- Config --------------------
COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"
MAX_DAYS = 60  # keep only latest 60 unique days

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

        # Extract dates and find latest
        dates = []
        for fname in combined_files:
            match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
            if match:
                dates.append((match.group(1), fname))
        if not dates:
            raise ValueError("No valid dated combined_nepse file found")

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

        # Combine new + old
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)

        # Drop duplicates (Symbol + Date unique)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date to datetime
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')

        # Sort descending
        df_combined.sort_values(by='Date', ascending=False, inplace=True)

        # Keep only latest MAX_DAYS unique dates
        recent_dates = df_combined['Date'].dropna().unique()[:MAX_DAYS]
        df_combined = df_combined[df_combined['Date'].isin(recent_dates)]

        # Ensure Date formatted back to string
        df_combined['Date'] = df_combined['Date'].dt.strftime('%Y-%m-%d')

        # Save combined
        df_combined.to_csv("combined_nepse.csv", index=False)
        print(f"✅ Combined CSV updated (last {MAX_DAYS} days kept)")
    except Exception as e:
        print(f"⚠️ Failed to merge with GitHub CSV: {e}")


# EMA cross calculation and signal generation
# # -------------------- Install nepse_scraper if missing --------------------
# try:
#     from nepse_scraper import Nepse_scraper
# except ModuleNotFoundError:
#     import sys, subprocess
#     subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
#     from nepse_scraper import Nepse_scraper

# # -------------------- Imports --------------------
# import pandas as pd
# import requests
# import re
# from datetime import datetime

# # -------------------- Config --------------------
# COLUMNS = ['Symbol', 'Date', 'Open', 'Close', 'Volume']
# REPO_URL = "https://api.github.com/repos/ChintanKoirala/NepseAnalysis/contents/daily_data"
# RAW_BASE = "https://raw.githubusercontent.com/ChintanKoirala/NepseAnalysis/main/daily_data"
# MAX_DAYS = 60  # keep only latest 60 unique days

# # -------------------- Find Latest combined_nepse File --------------------
# def get_latest_combined_url():
#     try:
#         resp = requests.get(REPO_URL)
#         resp.raise_for_status()
#         files = resp.json()
#         combined_files = [
#             f["name"] for f in files
#             if f["name"].startswith("combined_nepse_") and f["name"].endswith(".csv")
#         ]
#         if not combined_files:
#             raise ValueError("No combined_nepse_*.csv file found in repo")

#         dates = []
#         for fname in combined_files:
#             match = re.search(r"combined_nepse_(\d{4}-\d{2}-\d{2})\.csv", fname)
#             if match:
#                 dates.append((match.group(1), fname))

#         if not dates:
#             raise ValueError("No valid dated combined_nepse file found")

#         latest_date, latest_file = max(dates, key=lambda x: x[0])
#         print(f"📂 Latest GitHub file found: {latest_file}")
#         return f"{RAW_BASE}/{latest_file}"

#     except Exception as e:
#         print(f"⚠️ Failed to fetch latest combined file: {e}")
#         return None

# LATEST_URL = get_latest_combined_url()

# # -------------------- Fetch Today's NEPSE Data --------------------
# scraper = Nepse_scraper()
# try:
#     today_data = scraper.get_today_price()
#     content = today_data.get('content', [])
# except Exception as e:
#     print(f"⚠️ Failed to fetch today's NEPSE data: {e}")
#     content = []

# # -------------------- Process Today's Data --------------------
# filtered_data = []
# for item in content:
#     filtered_data.append({
#         'Symbol': item.get('symbol', ''),
#         'Date': item.get('businessDate', ''),
#         'Open': item.get('openPrice', 0),
#         'Close': item.get('closePrice', 0),
#         'Volume': item.get('totalTradedQuantity', 0)
#     })

# df_today = pd.DataFrame(filtered_data, columns=COLUMNS)

# # -------------------- Save Today's File --------------------
# if not df_today.empty:
#     today_date = df_today['Date'].iloc[0]
#     today_file = f"nepse_{today_date}.csv"
#     df_today.to_csv(today_file, index=False)
#     print(f"✅ Today's data saved as '{today_file}'")
# else:
#     print("⚠️ No data available for today.")

# # -------------------- Merge with Latest GitHub CSV --------------------
# if not df_today.empty and LATEST_URL:
#     try:
#         df_latest = pd.read_csv(LATEST_URL)
#         df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]
#         df_combined = pd.concat([df_latest, df_today], ignore_index=True)
#         df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)
#         df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
#         df_combined.sort_values(by='Date', ascending=False, inplace=True)
#         recent_dates = sorted(df_combined['Date'].dropna().unique(), reverse=True)[:MAX_DAYS]
#         df_combined = df_combined[df_combined['Date'].isin(recent_dates)]
#         df_combined['Date'] = df_combined['Date'].dt.strftime('%Y-%m-%d')

#         # -------------------- Indicator Calculation --------------------
#         df_combined['Remarks'] = ""
#         df_combined['RSI_5'] = 0.0
#         df_combined['Avg_Vol_5D'] = 0

#         def calculate_rsi(prices, period=5):
#             if len(prices) < period:
#                 return None
#             deltas = prices.diff()
#             gain = deltas.where(deltas > 0, 0)
#             loss = -deltas.where(deltas < 0, 0)
#             avg_gain = gain.rolling(window=period).mean().iloc[-1]
#             avg_loss = loss.rolling(window=period).mean().iloc[-1]
#             if avg_loss == 0:
#                 return 100
#             rs = avg_gain / avg_loss
#             rsi = 100 - (100 / (1 + rs))
#             return round(rsi, 2)

#         signal_order = [
#             "Very Very Strong Buy", "Very Strong Buy", "Strong Buy", "Buy",
#             "Very Very Strong Sell", "Very Strong Sell", "Strong Sell", "Sell"
#         ]

#         for symbol, group in df_combined.groupby("Symbol"):
#             group_sorted = group.sort_values(by="Date", ascending=False).head(5)
#             if len(group_sorted) < 5:
#                 continue

#             ma1 = group_sorted['Close'].head(2).mean()   # 2-day MA
#             ma2 = group_sorted['Close'].head(5).mean()   # 5-day MA
#             last_vol = group_sorted.iloc[0]['Volume']
#             avg_vol_5days = int(group_sorted['Volume'].head(5).mean())  # integer part only
#             rsi_5 = calculate_rsi(group_sorted['Close'])

#             df_combined.loc[df_combined['Symbol'] == symbol, 'RSI_5'] = rsi_5
#             df_combined.loc[df_combined['Symbol'] == symbol, 'Avg_Vol_5D'] = avg_vol_5days

#             # --- Signal Logic ---
#             if ma1 > ma2 and last_vol > avg_vol_5days:
#                 remark = "Strong Buy"
#                 if rsi_5 is not None and 50 <= rsi_5 <= 75:
#                     remark = "Very Strong Buy"
#             elif ma1 > ma2 and last_vol < avg_vol_5days:
#                 remark = "Buy"
#             elif ma2 > ma1 and last_vol > avg_vol_5days:
#                 remark = "Strong Sell"
#                 if rsi_5 is not None and 30 <= rsi_5 <= 49:
#                     remark = "Very Strong Sell"
#             elif ma2 > ma1 and last_vol < avg_vol_5days:
#                 remark = "Sell"
#             else:
#                 remark = ""

#             df_combined.loc[
#                 (df_combined['Symbol'] == symbol) & 
#                 (df_combined['Date'] == group_sorted.iloc[0]['Date']),
#                 'Remarks'
#             ] = remark

#         # Save combined CSV
#         df_combined.to_csv("combined_nepse.csv", index=False)
#         df_combined.to_csv(f"combined_nepse_{today_date}.csv", index=False)
#         print(f"✅ Combined CSV updated with signals (last {MAX_DAYS} days kept)")

#         # -------------------- Save LAST TRADING DAY CROSSOVER SIGNALS --------------------
#         last_signals = df_combined[
#             (df_combined['Date'] == today_date) &
#             (df_combined['Remarks'].isin(signal_order))
#         ].copy()

#         def is_crossover(row, df):
#             symbol = row['Symbol']
#             group = df[df['Symbol'] == symbol].sort_values(by='Date', ascending=False).head(2)
#             if len(group) < 2:
#                 return False
#             ma1_prev = group['Close'].iloc[1]
#             ma2_prev = group['Close'].head(5).mean()
#             ma1_today = row['Close']
#             ma2_today = group['Close'].head(5).mean()
#             return (ma1_prev <= ma2_prev and ma1_today > ma2_today) or (ma1_prev >= ma2_prev and ma1_today < ma2_today)

#         crossover_signals = last_signals[last_signals.apply(lambda row: is_crossover(row, df_combined), axis=1)]

#         if not crossover_signals.empty:
#             # Update remarks based on very high volume condition
#             for idx, row in crossover_signals.iterrows():
#                 if row['Remarks'] == "Very Strong Buy" and row['Volume'] > 1.30 * row['Avg_Vol_5D']:
#                     crossover_signals.at[idx, 'Remarks'] = "Very Very Strong Buy"
#                 elif row['Remarks'] == "Very Strong Sell" and row['Volume'] > 1.30 * row['Avg_Vol_5D']:
#                     crossover_signals.at[idx, 'Remarks'] = "Very Very Strong Sell"

#             # --- Custom Sorting by Buy/Sell priority ---
#             crossover_signals['Signal_Order'] = crossover_signals['Remarks'].apply(
#                 lambda x: signal_order.index(x) if x in signal_order else 999
#             )
#             crossover_signals.sort_values(by='Signal_Order', ascending=True, inplace=True)
#             crossover_signals.drop(columns=['Signal_Order'], inplace=True)

#             # Do NOT add S.N. column
#             signals_file = f"signals_{today_date}.csv"
#             crossover_signals.to_csv(signals_file, index=False)
#             print(f"📊 MA crossover signals saved with custom buy/sell order in '{signals_file}'")
#         else:
#             print("\nℹ️ No MA crossover signals for last traded day.")

#     except Exception as e:
#         print(f"⚠️ Failed to merge with GitHub CSV: {e}")



# -------------------- Install nepse_scraper if missing --------------------
try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nepse-scraper"])
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
import requests
import re
from datetime import datetime

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
        df_latest = df_latest[[col for col in COLUMNS if col in df_latest.columns]]

        # Combine new and old
        df_combined = pd.concat([df_latest, df_today], ignore_index=True)
        df_combined.drop_duplicates(subset=['Symbol', 'Date'], keep='last', inplace=True)

        # Convert Date and sort
        df_combined['Date'] = pd.to_datetime(df_combined['Date'], errors='coerce')
        df_combined.sort_values(by=['Symbol', 'Date'], inplace=True)

        # -------------------- Calculate Averages, RSI, and Remarks --------------------
        result_list = []
        for symbol, group in df_combined.groupby('Symbol'):
            group = group.copy()
            group['Avg_Vol_9D'] = group['Volume'].rolling(window=9).mean()
            group['MA_3D'] = group['Close'].rolling(window=3).mean()
            group['MA_9D'] = group['Close'].rolling(window=9).mean()

            # Only calculate RSI if at least 9 days exist
            if len(group) >= 9:
                last_9 = group['Close'].iloc[-9:]
                delta = last_9.diff().dropna()
                gain = delta.clip(lower=0).mean()
                loss = -delta.clip(upper=0).mean()
                if loss == 0:
                    rsi = 100
                else:
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                group['RSI_9D'] = None
                group.iloc[-1, group.columns.get_loc('RSI_9D')] = round(rsi, 2)

                # Calculate Vol_Ratio
                group['Vol_Ratio'] = group['Volume'] / group['Avg_Vol_9D']

                # Add initial Remarks column based on MA + Volume
                group['Remarks'] = ''
                if group.iloc[-1]['MA_3D'] >= group.iloc[-1]['MA_9D'] * 1.01 and group.iloc[-1]['Vol_Ratio'] >= 1.20:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Buy'
                elif group.iloc[-1]['MA_3D'] <= group.iloc[-1]['MA_9D'] * 0.99 and group.iloc[-1]['Vol_Ratio'] < 1.20:
                    group.iloc[-1, group.columns.get_loc('Remarks')] = 'Sell'

                result_list.append(group.iloc[[-1]])  # Keep only last traded day

        # Combine only symbols with >=9 days
        df_lastday = pd.concat(result_list, ignore_index=True)

        # -------------------- Filtering Criteria --------------------
        df_filtered = df_lastday[
            ((df_lastday['MA_3D'] >= df_lastday['MA_9D'] * 1.01) & (df_lastday['Vol_Ratio'] >= 1.20)) |
            ((df_lastday['MA_3D'] <= df_lastday['MA_9D'] * 0.99) & (df_lastday['Vol_Ratio'] < 1.20))
        ].copy()

        # -------------------- Update Remarks Based on RSI and Volume --------------------
        def update_remarks(row):
            # Step 1: RSI-based update
            if row['Remarks'] == 'Buy':
                if row['RSI_9D'] > 60:
                    remark = 'Overbought - Ready to Sell'
                else:
                    remark = 'Strong Buy'
            elif row['Remarks'] == 'Sell':
                if row['RSI_9D'] >= 70:
                    remark = 'Very Very Strong Sell'
                else:
                    remark = 'Strong Sell'
            else:
                remark = row['Remarks']

            # Step 2: Volume-based refinement
            if remark == 'Strong Buy' and row['Volume'] >= 1.6 * row['Avg_Vol_9D']:
                remark = 'Very Strong Buy'
            if remark == 'Strong Sell' and row['Volume'] <= 0.8 * row['Avg_Vol_9D']:
                remark = 'Much Strong Sell'

            # Step 3: Additional refinement
            if remark == 'Very Strong Buy' and row['RSI_9D'] <= 40:
                remark = 'Very Very Strong Buy'
            if remark == 'Much Strong Sell' and row['Volume'] <= 0.6 * row['Avg_Vol_9D']:
                remark = 'Very Much Strong Sell'

            return remark

        df_filtered['Remarks'] = df_filtered.apply(update_remarks, axis=1)

        # -------------------- Sort Stocks by Common Signal (Remarks) --------------------
        signal_order = [
            'Very Very Strong Buy',
            'Very Strong Buy',
            'Strong Buy',
            'Overbought - Ready to Sell',
            'Strong Sell',
            'Much Strong Sell',
            'Very Much Strong Sell',
            'Very Very Strong Sell'
        ]
        df_filtered['Remarks'] = pd.Categorical(df_filtered['Remarks'], categories=signal_order, ordered=True)
        df_filtered.sort_values(by=['Remarks', 'Symbol'], inplace=True)

        # -------------------- Final Formatting --------------------
        df_filtered['Date'] = df_filtered['Date'].dt.strftime('%Y-%m-%d')
        df_filtered['Avg_Vol_9D'] = df_filtered['Avg_Vol_9D'].fillna(0).astype(int)
        df_filtered['MA_3D'] = df_filtered['MA_3D'].round(2)
        df_filtered['MA_9D'] = df_filtered['MA_9D'].round(2)

        df_filtered = df_filtered[['Symbol', 'Date', 'Open', 'Close', 'Volume',
                                   'Avg_Vol_9D', 'MA_3D', 'MA_9D', 'RSI_9D', 'Remarks']]

        df_filtered.reset_index(drop=True, inplace=True)
        df_filtered.index += 1
        df_filtered.index.name = 'S.N.'

        # -------------------- Save Final Output --------------------
        df_filtered.to_csv("filtered_nepse_signals.csv", index=True)
        print("✅ File 'filtered_nepse_signals.csv' saved successfully with signals grouped serially by type.")

    except Exception as e:
        print(f"⚠️ Failed to process and calculate: {e}")











# upload output files in github ripo
# import os
# import sys
# import base64
# import requests
# import glob

# # -------------------- GitHub Config --------------------
# repo = "ChintanKoirala/NepseAnalysis"
# branch = "main"

# # -------------------- Detect latest signals file --------------------
# signal_files = sorted(glob.glob("signals_*.csv"), reverse=True)
# if not signal_files:
#     print("❌ No signals_*.csv file found locally. Exiting.")
#     sys.exit(1)

# local_file = signal_files[0]  # pick the latest file
# last_traded_date = local_file.replace("signals_", "").replace(".csv", "")
# repo_file = f"daily_data/signals_{last_traded_date}.csv"
# upload_url = f"https://api.github.com/repos/{repo}/contents/{repo_file}"

# print(f"✅ Found latest signals file: {local_file}")

# # -------------------- GitHub Token --------------------
# token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
# if not token:
#     print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
#     sys.exit(1)
# else:
#     print("✅ Using GitHub token.")

# headers = {
#     "Authorization": f"Bearer {token}",
#     "Accept": "application/vnd.github.v3+json"
# }

# # -------------------- Read & encode file --------------------
# try:
#     with open(local_file, "rb") as f:
#         content = f.read()
#     encoded_content = base64.b64encode(content).decode()
#     print(f"ℹ️ File '{local_file}' read successfully.")
# except Exception as e:
#     print(f"❌ Failed to read '{local_file}': {e}")
#     sys.exit(1)

# # -------------------- Check if file exists in repo --------------------
# sha = None
# try:
#     response = requests.get(upload_url, headers=headers)
#     if response.status_code == 200:
#         sha = response.json().get("sha")
#         print(f"ℹ️ File '{repo_file}' exists. It will be updated.")
#     elif response.status_code == 404:
#         print(f"ℹ️ File '{repo_file}' does not exist. It will be created.")
#     else:
#         print(f"⚠️ Unexpected status {response.status_code} when checking repo.")
#         print(response.json())
# except Exception as e:
#     print(f"⚠️ Failed to check file in repo: {e}")

# # -------------------- Upload / Update --------------------
# payload = {
#     "message": f"Upload signals file for {last_traded_date}",
#     "content": encoded_content,
#     "branch": branch
# }
# if sha:
#     payload["sha"] = sha

# try:
#     response = requests.put(upload_url, headers=headers, json=payload)
#     if response.status_code in [200, 201]:
#         print(f"✅ File '{repo_file}' uploaded successfully!")
#     else:
#         print(f"❌ Upload failed. Status: {response.status_code}")
#         print(response.json())
# except Exception as e:
#     print(f"❌ Exception during upload: {e}")




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






