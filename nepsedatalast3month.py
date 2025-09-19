# -------------------- Install & Import Nepse Scraper --------------------
try:
    from nepse_scraper import Nepse_scraper
except ModuleNotFoundError:
    import sys
    !{sys.executable} -m pip install nepse-scraper
    from nepse_scraper import Nepse_scraper

# -------------------- Imports --------------------
import pandas as pd
from datetime import datetime
import glob

# -------------------- Create Scraper Object --------------------
scraper = Nepse_scraper()

# -------------------- Fetch Today's Price Data --------------------
try:
    today_price = scraper.get_today_price()
    content_data = today_price.get('content', [])
except Exception as e:
    print(f"⚠️ Failed to fetch today's data: {e}")
    content_data = []

# -------------------- Process Data --------------------
columns = ['Symbol', 'Date', 'Open', 'Close', 'Percent Change', 'Volume']
filtered_data = []

for item in content_data:
    symbol = item.get('symbol', '')
    date = item.get('businessDate', '')
    
    # Safely get open and close prices
    open_price = float(item.get('openPrice', 0) or 0)
    close_price = float(item.get('closePrice', 0) or 0)
    
    # Calculate percent change
    percent_change = round(((close_price - open_price) / open_price * 100) if open_price else 0, 2)
    
    # Correctly calculate total traded volume
    volume = 0
    if 'tradedShares' in item:
        # If volume is nested in 'tradedShares'
        try:
            volume = sum(int(str(x).replace(',', '')) for x in item.get('tradedShares', []))
        except:
            volume = 0
    else:
        # Use totalTradedQuantity if available
        try:
            volume = int(str(item.get('totalTradedQuantity', 0)).replace(',', ''))
        except:
            volume = 0

    filtered_data.append({
        'Symbol': symbol,
        'Date': date,
        'Open': open_price,
        'Close': close_price,
        'Percent Change': percent_change,
        'Volume': volume
    })

# -------------------- Save Today's CSV --------------------
df_today = pd.DataFrame(filtered_data, columns=columns)
if not df_today.empty:
    today_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f"nepse_{today_date}.csv"
    df_today.to_csv(file_name, index=False)
    print(f"✅ Today's data saved to '{file_name}'")
else:
    print("⚠️ No data available for today.")

# -------------------- Combine Last 15 Days --------------------
csv_files = sorted(glob.glob("nepse_*.csv"), reverse=True)[:15]  # Last 15 files
df_list = [pd.read_csv(f) for f in csv_files]

if df_list:
    df_last15 = pd.concat(df_list, ignore_index=True)
    df_last15['Date'] = pd.to_datetime(df_last15['Date'])
    df_last15 = df_last15.sort_values(by=['Date', 'Symbol'], ascending=[False, True])

    file_name_15 = f"nepse_last15days_{today_date}.csv"
    df_last15.to_csv(file_name_15, index=False)
    print(f"✅ Last 15 days data saved to '{file_name_15}'")
    print(df_last15.head())
else:
    print("⚠️ No previous CSVs found for last 15 days.")
