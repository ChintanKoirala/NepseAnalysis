import requests
import pandas as pd
from datetime import datetime
import glob

# -------------------- Nepse Scraper --------------------
class Nepse_scraper:
    BASE_URL = "https://www.nepalstock.com/api/nots/"

    def get_last_n_days(self, symbol, n=10):
        """
        Fetch last n days of data for a given symbol
        Returns a DataFrame with columns: Date, Open, Close, Volume
        """
        url = f"{self.BASE_URL}securityDailyPrices?symbol={symbol}"
        r = requests.get(url)
        if r.status_code != 200:
            raise Exception(f"Failed to fetch data for {symbol}")
        
        data = r.json().get('data', [])
        if not data:
            return pd.DataFrame()  # Return empty DataFrame if no data
        
        # Take last n days
        data = data[-n:]
        df = pd.DataFrame(data)
        df = df[['businessDate', 'openPrice', 'closePrice', 'totalTradedQuantity']]
        df.rename(columns={
            'businessDate': 'Date',
            'openPrice': 'Open',
            'closePrice': 'Close',
            'totalTradedQuantity': 'Volume'
        }, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df.sort_values('Date', ascending=False, inplace=True)
        return df

# -------------------- Create Scraper --------------------
scraper = Nepse_scraper()

# -------------------- Define Symbols --------------------
symbols = ['NABIL', 'NIBL', 'HBL', 'NEPSE_INDEX']  # Replace with all symbols if needed

# -------------------- Fetch Today's Data --------------------
today_records = []

for sym in symbols:
    try:
        df_sym = scraper.get_last_n_days(sym, n=1)
        if not df_sym.empty:
            record = df_sym.iloc[0].to_dict()
            record['Symbol'] = sym
            # Calculate percent change
            record['Percent Change'] = round(
                ((record['Close'] - record['Open']) / record['Open'] * 100) if record['Open'] else 0, 2
            )
            today_records.append(record)
    except Exception as e:
        print(f"⚠️ Failed to fetch data for {sym}: {e}")

df_today = pd.DataFrame(today_records)
today_date = datetime.now().strftime('%Y-%m-%d')
file_today = f"nepse_{today_date}.csv"

if not df_today.empty:
    df_today.to_csv(file_today, index=False)
    print(f"✅ Today's data saved: {file_today}")
else:
    print("⚠️ No data fetched for today.")

# -------------------- Combine Last 15 Days --------------------
csv_files = sorted(glob.glob("nepse_*.csv"), reverse=True)[:15]  # Last 15 files
df_list = [pd.read_csv(f) for f in csv_files]

if df_list:
    df_last15 = pd.concat(df_list, ignore_index=True)
    df_last15['Date'] = pd.to_datetime(df_last15['Date'])
    df_last15.sort_values(by=['Date', 'Symbol'], ascending=[False, True], inplace=True)
    file_last15 = f"nepse_last15days_{today_date}.csv"
    df_last15.to_csv(file_last15, index=False)
    print(f"✅ Last 15 days data saved: {file_last15}")
    print(df_last15.head())
else:
    print("⚠️ No previous CSVs found for last 15 days.")
