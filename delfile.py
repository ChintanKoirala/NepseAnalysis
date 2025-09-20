# delete particular file in github
# import os
# import sys
# import requests

# # -------------------- GitHub token --------------------
# # Use GitHub Actions token or local Personal Access Token
# token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
# if not token:
#     print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
#     sys.exit(1)

# repo = "ChintanKoirala/NepseAnalysis"
# branch = "main"   # ✅ branch is just 'main'
# folder = "daily_data"   # ✅ folder path inside repo
# file_name = "combined_nepse_2025-09-20.csv"

# # Full GitHub API URL for file
# file_url = f"https://api.github.com/repos/{repo}/contents/{folder}/{file_name}"

# headers = {
#     "Authorization": f"Bearer {token}",
#     "Accept": "application/vnd.github.v3+json"
# }

# # -------------------- Get SHA of the file --------------------
# response = requests.get(file_url, headers=headers, params={"ref": branch})
# if response.status_code == 200:
#     sha = response.json().get("sha")
#     if not sha:
#         print(f"❌ Could not find SHA for {file_name}")
#         sys.exit(1)
# else:
#     print(f"❌ File not found on GitHub: {folder}/{file_name}")
#     print(response.json())
#     sys.exit(1)

# # -------------------- Delete the file --------------------
# payload = {
#     "message": f"Delete NEPSE file {file_name}",
#     "sha": sha,
#     "branch": branch
# }

# delete_response = requests.delete(file_url, headers=headers, json=payload)



# del all uploaded files except last six files
import os
import requests
from datetime import datetime

# -------------------- Get GitHub token from environment --------------------
token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
if not token:
    print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
    exit(1)

# -------------------- Repo & folder settings --------------------
repo = "ChintanKoirala/NepseAnalysis"
branch = "main"
folder = "daily_data"

# GitHub API URL for the folder
folder_url = f"https://api.github.com/repos/{repo}/contents/{folder}"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# -------------------- Get list of files in folder --------------------
response = requests.get(folder_url, headers=headers, params={"ref": branch})

if response.status_code == 401:
    print("❌ Unauthorized. Bad credentials or token missing required scopes.")
    exit(1)
elif response.status_code != 200:
    print(f"❌ Failed to fetch folder contents. Status code: {response.status_code}")
    print(response.json())
    exit(1)

files = response.json()

# Ensure files is a list
if not isinstance(files, list):
    print("❌ Unexpected response from GitHub API:", files)
    exit(1)

# -------------------- Extract CSV files with dates --------------------
dated_files = []
for f in files:
    name = f.get("name", "")
    sha = f.get("sha", "")
    if name.endswith(".csv") and "_" in name:
        try:
            # Assuming format: prefix_YYYY-MM-DD.csv
            date_str = name.split("_")[-1].replace(".csv", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            dated_files.append((file_date, name, sha))
        except ValueError:
            continue

# -------------------- Sort by date descending --------------------
dated_files.sort(reverse=True, key=lambda x: x[0])

# -------------------- Keep last 6 files only --------------------
to_delete = dated_files[6:]   # everything except the latest 6 files

if not to_delete:
    print("✅ No old files to delete. Only 6 or fewer files exist.")
    exit(0)

print("🗑️ Files scheduled for deletion:")
for _, name, _ in to_delete:
    print(f"   - {name}")

# -------------------- Delete old files --------------------
for file_date, name, sha in to_delete:
    file_url = f"https://api.github.com/repos/{repo}/contents/{folder}/{name}"
    payload = {
        "message": f"Delete old NEPSE file {name}",
        "sha": sha,
        "branch": branch
    }

    delete_response = requests.delete(file_url, headers=headers, json=payload)

    if delete_response.status_code in (200, 204):
        print(f"✅ Deleted {name}")
    else:
        print(f"❌ Failed to delete {name}. Status code: {delete_response.status_code}")
        print(delete_response.json())
