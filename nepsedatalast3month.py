# -*- coding: utf-8 -*-
"""
Corrected nepse automation script.
Notes:
- Install requirements separately, e.g.:
  !pip install nepse-scraper xlsxwriter gitpython pandas matplotlib joblib requests bs4
- Set GH_TOKEN environment variable if you want GitHub upload/delete features.
"""

import os
import sys
import re
import base64
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from joblib import Parallel, delayed

# Optional imports that might not be present in every environment
try:
    from nepse_scraper import Nepse_scraper
except Exception as e:
    Nepse_scraper = None
    print("Warning: nepse_scraper import failed:", e)

# ---------- Config ----------
GITHUB_OWNER = "iamsrijit"
GITHUB_REPO = "Nepse"
GITHUB_BRANCH = "main"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents"
GH_TOKEN = os.getenv("GH_TOKEN")  # must be set in environment to enable upload/delete

# Patterns for files we create
ESPEN_PREFIX = "espen_"
EMA_PREFIX = "EMA_Cross_for_"
ESPEN_PATTERN = re.compile(rf'^{ESPEN_PREFIX}\d{{4}}-\d{{2}}-\d{{2}}\.csv$')
EMA_PATTERN = re.compile(rf'^{EMA_PREFIX}\d{{4}}-\d{{2}}-\d{{2}}\.csv$')

# ---------- Helper utilities ----------
def bearer_headers():
    if not GH_TOKEN:
        return {}
    return {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def safe_filename(filename: str) -> str:
    return re.sub(r'[^A-Za-z0-9_\-\.]', '_', filename)

# ---------- Fetch today's NEPSE data ----------
def fetch_today_nepse():
    if Nepse_scraper is None:
        raise RuntimeError("nepse_scraper is not available. Install nepse-scraper package.")
    req = Nepse_scraper()
    # Some versions have get_today_price() or get_price_today() or similar; try a few names
    method_candidates = ["get_today_price", "get_price_today", "get_today_prices", "get_price"]
    response = None
    for m in method_candidates:
        func = getattr(req, m, None)
        if callable(func):
            try:
                response = func()
                break
            except Exception as e:
                # continue trying other methods
                print(f"Attempt to call {m} raised: {e}")
                response = None
    if response is None:
        # As a last resort, if the object itself is callable or has 'get' behavior
        if hasattr(req, "get") and callable(getattr(req, "get")):
            try:
                response = req.get("today_price")
            except Exception:
                response = None

    if not response:
        raise RuntimeError("Unable to fetch NEPSE data from nepse_scraper. Check package version and API changes.")

    # Expected shape: dict with key 'content' being list of items
    content = response.get("content") if isinstance(response, dict) else None
    if content is None:
        # Try if response itself is a list / dataframe-like
        if isinstance(response, list):
            content = response
        else:
            raise RuntimeError("Unexpected NEPSE response format. Expected dict with 'content' list.")
    return content

def build_daily_dataframe(content):
    rows = []
    for item in content:
        symbol = item.get('symbol') or item.get('Symbol') or ""
        date = item.get('businessDate') or item.get('date') or item.get('Date') or ""
        # numeric fields might be strings with commas
        def asnum(key):
            v = item.get(key, 0)
            if isinstance(v, str):
                try:
                    v = v.replace(',', '')
                except Exception:
                    pass
            try:
                return float(v)
            except Exception:
                return np.nan
        open_price = asnum('openPrice') or asnum('Open')
        high_price = asnum('highPrice') or asnum('High')
        low_price = asnum('lowPrice') or asnum('Low')
        close_price = asnum('closePrice') or asnum('Close')
        volume_daily = asnum('totalTradedQuantity') or asnum('Volume') or 0
        high_52w = asnum('fiftyTwoWeekHigh') or np.nan
        low_52w = asnum('fiftyTwoWeekLow') or np.nan

        # normalize date
        if date:
            try:
                parsed_date = pd.to_datetime(date, errors='coerce')
            except Exception:
                parsed_date = pd.NaT
        else:
            parsed_date = pd.NaT

        percent_change = (close_price - open_price) / open_price * 100 if open_price and not np.isnan(open_price) else 0
        rows.append({
            'Symbol': symbol.strip(),
            'Date': parsed_date,
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Percent Change': round(percent_change, 2),
            'Volume': volume_daily,
            '52W_High': high_52w,
            '52W_Low': low_52w
        })
    df = pd.DataFrame(rows)
    return df

# ---------- GitHub helpers (list, read, upload, delete) ----------
def list_repo_contents(path=""):
    url = f"{GITHUB_API_BASE}/{path}" if path else GITHUB_API_BASE
    headers = bearer_headers()
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"GitHub list failed: {r.status_code} {r.text}")
    return r.json()  # list of file objects

def find_latest_csv_in_repo():
    """
    Looks for CSV files in repo root with a date in filename and returns (filename, download_raw_url).
    """
    try:
        contents = list_repo_contents("")
    except Exception as e:
        print("GitHub list error:", e)
        return None, None

    candidates = []
    for item in contents:
        if item.get("type") != "file":
            continue
        name = item.get("name", "")
        if not name.lower().endswith(".csv"):
            continue
        # find ISO date substring
        m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
        if m:
            date_str = m.group(1)
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                candidates.append((d, name, item.get("download_url")))
            except Exception:
                continue

    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0], reverse=True)
    latest = candidates[0]
    return latest[1], latest[2]

def download_csv_from_raw_url(raw_url):
    if not raw_url:
        return pd.DataFrame()
    r = requests.get(raw_url)
    if r.status_code != 200:
        print("Failed to download raw CSV:", r.status_code)
        return pd.DataFrame()
    try:
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        return df
    except Exception as e:
        print("Error reading CSV:", e)
        return pd.DataFrame()

def github_put_file(path_in_repo, df, message="upload file"):
    """Create or update a file in the repo root."""
    if not GH_TOKEN:
        print("GH_TOKEN not set: skipping upload to GitHub.")
        return None
    url = f"{GITHUB_API_BASE}/{path_in_repo}"
    headers = bearer_headers()

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    content_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    # Check if file exists to include sha
    r_get = requests.get(url, headers=headers)
    payload = {"message": message, "content": content_b64, "branch": GITHUB_BRANCH}
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code not in (200, 201):
        print("GitHub upload failed:", r.status_code, r.text)
        return None
    print(f"Uploaded {path_in_repo}: {r.status_code}")
    return r.json()

def github_delete_file(path_in_repo, message="remove file"):
    if not GH_TOKEN:
        print("GH_TOKEN not set: skipping delete on GitHub.")
        return None
    url = f"{GITHUB_API_BASE}/{path_in_repo}"
    headers = bearer_headers()
    r_get = requests.get(url, headers=headers)
    if r_get.status_code != 200:
        print(f"File {path_in_repo} not found on GitHub; nothing to delete.")
        return None
    sha = r_get.json().get("sha")
    payload = {"message": message, "sha": sha, "branch": GITHUB_BRANCH}
    r = requests.delete(url, headers=headers, json=payload)
    if r.status_code not in (200, 204):
        print("GitHub delete failed:", r.status_code, r.text)
        return None
    print(f"Deleted {path_in_repo} from repo.")
    return r.json()

# ---------- Merge with latest GitHub CSV ----------
def merge_with_repo_csv(local_df):
    # Try to find latest CSV in repo and read it
    filename, raw_url = find_latest_csv_in_repo()
    if not filename or not raw_url:
        print("No previous CSV found in repo.")
        return local_df.copy()

    try:
        remote_df = download_csv_from_raw_url(raw_url)
        if remote_df.empty:
            print("Remote CSV empty or unreadable.")
            return local_df.copy()
        # Normalize column names if required
        expected_cols = ['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Percent Change', 'Volume', '52W_High', '52W_Low']
        # If remote has different casing, try to rename
        remote_df_cols = {c: c.strip() for c in remote_df.columns}
        remote_df = remote_df.rename(columns=remote_df_cols)
        # Ensure all expected columns exist (if not, try to infer)
        for c in expected_cols:
            if c not in remote_df.columns:
                # attempt lower-case mapping
                cl = c.lower()
                found = next((rc for rc in remote_df.columns if rc.lower() == cl), None)
                if found:
                    remote_df = remote_df.rename(columns={found: c})
        # Parse dates properly
        if 'Date' in remote_df.columns:
            remote_df['Date'] = pd.to_datetime(remote_df['Date'], errors='coerce')
        # Ensure numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume', '52W_High', '52W_Low']:
            if col in remote_df.columns:
                remote_df[col] = (remote_df[col].astype(str).str.replace(',', '').replace('-', np.nan))
                remote_df[col] = pd.to_numeric(remote_df[col], errors='coerce')

        # Concatenate
        combined = pd.concat([local_df, remote_df], ignore_index=True, sort=False)
        # drop rows without Symbol or Date
        combined = combined.dropna(subset=['Symbol', 'Date'])
        combined['Symbol'] = combined['Symbol'].astype(str).str.strip()
        # sort and deduplicate by Symbol+Date, keeping latest (by Date)
        combined = combined.sort_values(['Symbol', 'Date'], ascending=[True, False])
        combined = combined.drop_duplicates(subset=['Symbol', 'Date'], keep='first')
        combined = combined.sort_values(['Symbol', 'Date']).reset_index(drop=True)
        return combined
    except Exception as e:
        print("Error merging with repo CSV:", e)
        return local_df.copy()

# ---------- Technical indicators ----------
def calculate_rsi(series_close, period=14):
    delta = series_close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    # Use Wilder smoothing for subsequent values
    # Fill initial with simple average
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(method='bfill').fillna(50)
    return rsi

def process_symbol(group):
    # expects group sorted by Date ascending
    group = group.sort_values("Date").reset_index(drop=True)
    group['EMA_20'] = group['Close'].ewm(span=20, adjust=False).mean()
    group['EMA_50'] = group['Close'].ewm(span=50, adjust=False).mean()
    group['RSI'] = calculate_rsi(group['Close'])
    group['30D_Avg_Volume'] = group['Volume'].rolling(30, min_periods=1).mean()
    # slope: difference over 5 bars
    group['Slope_20'] = group['EMA_20'].diff(5) / 5
    group['Slope_50'] = group['EMA_50'].diff(5) / 5
    # crossover detection: EMA20 crosses above EMA50 today but not yesterday
    group['Crossover'] = (group['EMA_20'] > group['EMA_50']) & (group['EMA_20'].shift(1) <= group['EMA_50'].shift(1))
    # Additional filters
    valid = group[
        (group['Crossover']) &
        (group['Slope_20'] > group['Slope_50']) &
        (group['RSI'].between(30, 70, inclusive='both')) &
        (group['Volume'] >= 0.3 * group['30D_Avg_Volume'])
    ].copy()

    # Condition for recent high breakout: close > 95% of previous 60-day max (excluding current day)
    if 'Close' in group.columns:
        prev_60_max = group['Close'].rolling(60, min_periods=1).max().shift(1)
        cond = group['Close'] > (prev_60_max * 0.95)
        # intersect with valid
        valid = valid[cond.loc[valid.index].fillna(False)]

    return valid

# ---------- Main flow ----------
def main():
    print("Starting NEPSE automation:", datetime.now())
    # 1) fetch today's NEPSE content
    try:
        content = fetch_today_nepse()
    except Exception as e:
        print("Error fetching NEPSE:", e)
        return

    today_df = build_daily_dataframe(content)
    if today_df.empty:
        print("No data fetched for today. Exiting.")
        return

    # Save today's CSV locally (optional)
    today_str = datetime.now().strftime("%Y-%m-%d")
    local_daily_filename = f"nepse_{today_str}.csv"
    # Keep date column as datetime until final export
    today_df.to_csv(local_daily_filename, index=False, date_format="%Y-%m-%d")
    print("Saved local daily file:", local_daily_filename)

    # 2) merge with repo CSV (if available)
    full_df = merge_with_repo_csv(today_df)

    # Filter out mutual funds (list from your original script)
    exclude_symbols = set([
        'SAEF', 'SEF', 'CMF1', 'NICGF', 'NBF2', 'CMF2', 'NMB50', 'SIGS2', 'NICBF',
        'SFMF', 'LUK', 'SLCF', 'KEF', 'SBCF', 'PSF', 'NIBSF2', 'NICSF', 'RMF1',
        'NBF3', 'MMF1', 'KDBY', 'NICFC', 'GIBF1', 'NSIF2', 'SAGF', 'NIBLGF',
        'SFEF', 'PRSF', 'C30MF', 'SIGS3', 'RMF2', 'LVF2', 'H8020', 'NICGF2',
        'NIBLSTF', 'KSY', 'NBLD87', 'PBD88', 'OTHERS','HIDCLP','NIMBPO','MUTUAL',
        'CIT','ILI','LEMF','NIBLPF','INVESTMENT','SENFLOAT','HEIP','SBID83','NICAD8283'
    ])
    full_df = full_df[~full_df['Symbol'].isin(exclude_symbols)].copy()

    # Normalize columns, ensure Date and numeric cols are proper dtype
    full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce')
    for col in ['Open', 'High', 'Low', 'Close', 'Volume', '52W_High', '52W_Low']:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce')

    # Save combined_data.csv locally
    combined_file = "combined_data.csv"
    # Format Date when saving
    out_df = full_df.copy()
    out_df['Date'] = out_df['Date'].dt.strftime("%m/%d/%Y")
    out_df.to_csv(combined_file, index=False)
    print("Saved combined data locally:", combined_file)

    # 3) compute EMA/RSI/crossovers across symbols
    # Use groupby and joblib for concurrency
    # We need groups sorted by Date ascending
    groups = [g for _, g in full_df.groupby("Symbol")]
    print(f"Processing {len(groups)} symbols for indicators...")

    results = Parallel(n_jobs=-1)(
        delayed(process_symbol)(g) for g in groups
    )
    if results:
        all_valid_crossovers = pd.concat(results, ignore_index=True)
    else:
        all_valid_crossovers = pd.DataFrame()

    if all_valid_crossovers.empty:
        print("No valid crossovers found.")
    else:
        # Add 52-week percent columns safely
        all_valid_crossovers['Pct_from_52W_High'] = 100 * all_valid_crossovers['Close'] / all_valid_crossovers['52W_High']
        all_valid_crossovers['Pct_from_52W_Low'] = 100 * all_valid_crossovers['Close'] / all_valid_crossovers['52W_Low']
        def sign_pct(x):
            try:
                if np.isnan(x):
                    return ""
                if x >= 100:
                    return f"+{x-100:.2f}%"
                else:
                    return f"-{100-x:.2f}%"
            except Exception:
                return ""
        all_valid_crossovers['Pct_from_52W_High_Sign'] = all_valid_crossovers['Pct_from_52W_High'].apply(sign_pct)
        all_valid_crossovers['Pct_from_52W_Low_Sign'] = all_valid_crossovers['Pct_from_52W_Low'].apply(sign_pct)

        # Save all valid crossovers and latest per symbol
        all_valid_crossovers.to_csv("valid_ema_crossovers.csv", index=False)
        latest_crossovers = all_valid_crossovers.sort_values("Date", ascending=False).drop_duplicates("Symbol")
        latest_crossovers.to_csv("latest_valid_ema_crossovers.csv", index=False)
        print("Saved EMA crossover files. Latest examples:")
        print(latest_crossovers[['Symbol', 'Date', 'Close']].head(10))

    # 4) Upload to GitHub (if token present)
    today_stamp = datetime.today().strftime("%Y-%m-%d")
    espen_filename = f"{ESPEN_PREFIX}{today_stamp}.csv"
    ema_filename = f"{EMA_PREFIX}{today_stamp}.csv"

    if GH_TOKEN:
        # Upload combined data (espen) and latest crossovers (if exist)
        try:
            print("Uploading combined data to GitHub:", espen_filename)
            github_put_file(safe_filename(espen_filename), full_df.assign(Date=full_df['Date'].dt.strftime("%Y-%m-%d")), message=f"Upload {espen_filename}")
        except Exception as e:
            print("Upload error for espen:", e)

        if not all_valid_crossovers.empty:
            try:
                print("Uploading EMA crossovers to GitHub:", ema_filename)
                github_put_file(safe_filename(ema_filename), latest_crossovers.assign(Date=latest_crossovers['Date'].astype(str)), message=f"Upload {ema_filename}")
            except Exception as e:
                print("Upload error for EMA:", e)
    else:
        print("GH_TOKEN not set. Skipping upload to GitHub.")

    # 5) Remove older files in GitHub repo matching patterns (keep only latest of each type)
    if GH_TOKEN:
        try:
            contents = list_repo_contents("")
            # find all espen and ema files and keep the newest for each prefix
            espen_files = [(item['name'], item['download_url']) for item in contents if item.get("type")=="file" and ESPEN_PATTERN.match(item['name'])]
            ema_files = [(item['name'], item['download_url']) for item in contents if item.get("type")=="file" and EMA_PATTERN.match(item['name'])]
            def purge_older(files_list, keep=1, prefix=""):
                if not files_list:
                    return
                # sort by date embedded in filename
                parsed = []
                for name, dl in files_list:
                    m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
                    if not m:
                        continue
                    try:
                        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                        parsed.append((d, name))
                    except:
                        continue
                parsed.sort(key=lambda x: x[0], reverse=True)
                to_keep = set([name for _, name in parsed[:keep]])
                to_delete = [name for _, name in parsed[keep:]]
                for fname in to_delete:
                    print("Deleting old file from GitHub:", fname)
                    github_delete_file(fname, message=f"Remove old {prefix} file {fname}")
            purge_older(espen_files, keep=1, prefix="espen")
            purge_older(ema_files, keep=1, prefix="EMA")
        except Exception as e:
            print("Error while pruning old files on GitHub:", e)

    print("Done:", datetime.now())


if __name__ == "__main__":
    main()
