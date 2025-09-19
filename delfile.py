import os
import sys
import requests

# -------------------- GitHub token --------------------
# Use GitHub Actions token or local Personal Access Token
token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_PAT")
if not token:
    print("❌ GitHub token not found. Set GITHUB_TOKEN (Actions) or GH_PAT (local).")
    sys.exit(1)

repo = "ChintanKoirala/NepseAnalysis"
branch = "main"   # ✅ branch is just 'main'
folder = "daily_data"   # ✅ folder path inside repo
file_name = "espen_2025-09-18.csv"

# Full GitHub API URL for file
file_url = f"https://api.github.com/repos/{repo}/contents/{folder}/{file_name}"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# -------------------- Get SHA of the file --------------------
response = requests.get(file_url, headers=headers, params={"ref": branch})
if response.status_code == 200:
    sha = response.json().get("sha")
    if not sha:
        print(f"❌ Could not find SHA for {file_name}")
        sys.exit(1)
else:
    print(f"❌ File not found on GitHub: {folder}/{file_name}")
    print(response.json())
    sys.exit(1)

# -------------------- Delete the file --------------------
payload = {
    "message": f"Delete NEPSE file {file_name}",
    "sha": sha,
    "branch": branch
}

delete_response = requests.delete(file_url, headers=headers, json=payload)

if delete_response.status_code in (200, 204):
    print(f"✅ File {file_name} deleted successfully from GitHub!")
else:
    print(f"❌ Failed to delete {file_name}. Status code: {delete_response.status_code}")
    print(delete_response.json())
