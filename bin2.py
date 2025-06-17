import csv
import requests
from urllib.parse import urlparse
from collections import defaultdict
import os
from dotenv import load_dotenv

# Load token and base URL
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = os.getenv("GITHUB_BASE_URL", "https://github.com")  # fallback to public GitHub

INPUT_CSV = "binary_file_urls.csv"
OUTPUT_CSV = "binary_repo_size_summary.csv"
SIZE_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB

def extract_repo_url(file_url):
    parts = file_url.split("/")
    if len(parts) >= 5:
        return "/".join(parts[:5])  # e.g., https://github.qualcomm.com/org/repo
    return None

def get_file_size_bytes(url):
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        } if GITHUB_TOKEN else {}

        res = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        if res.status_code == 200:
            return int(res.headers.get("Content-Length", 0))
        else:
            print(f"HEAD request failed: {url} → {res.status_code}")
    except Exception as e:
        print(f"Error on {url}: {e}")
    return 0

def main():
    repo_stats = defaultdict(lambda: {"total": 0, "over_100mb": 0})

    with open(INPUT_CSV, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            file_url = row[0].strip()
            if not file_url.startswith(BASE_URL):
                continue  # Skip URLs outside your org

            repo_url = extract_repo_url(file_url)
            if not repo_url:
                continue

            repo_stats[repo_url]["total"] += 1
            size_bytes = get_file_size_bytes(file_url)
            if size_bytes > SIZE_THRESHOLD_BYTES:
                repo_stats[repo_url]["over_100mb"] += 1
                print(f">100MB: {file_url} ({size_bytes / 1024 / 1024:.2f} MB)")

    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "repo_url", "has_binary_over_100mb", "binary_file_count_over_100mb", "total_binary_file_count"
        ])
        writer.writeheader()
        for repo_url, stats in repo_stats.items():
            writer.writerow({
                "repo_url": repo_url,
                "has_binary_over_100mb": stats["over_100mb"] > 0,
                "binary_file_count_over_100mb": stats["over_100mb"],
                "total_binary_file_count": stats["total"]
            })

    print(f"Done. Wrote output to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
