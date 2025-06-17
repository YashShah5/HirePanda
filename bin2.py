import csv
import requests
from urllib.parse import urlparse
from collections import defaultdict
import os
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = os.getenv("GITHUB_BASE_URL", "https://github-test.qualcomm.com")
INPUT_CSV = "url.csv"
OUTPUT_CSV = "binary_over_100mb_report.csv"
SIZE_THRESHOLD_BYTES = 100 * 1024 * 1024

def parse_org_and_repo_from_url(url):
    """
    Extracts org and repo name from URLs like:
    https://github-test.qualcomm.com/org/repo
    """
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def get_file_size_bytes(url):
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        } if GITHUB_TOKEN else {}

        res = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        if res.status_code == 200:
            return int(res.headers.get("Content-Length", 0))
        else:
            print(f"HEAD failed for {url} → {res.status_code}")
    except Exception as e:
        print(f"Error getting size for {url}: {e}")
    return 0

def main():
    repo_data = defaultdict(lambda: {"total": 0, "over_100mb": 0})

    if not os.path.exists(INPUT_CSV):
        print(f"[ERROR] Cannot find input file: {INPUT_CSV}")
        return

    with open(INPUT_CSV, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0].startswith(BASE_URL):
                continue

            url = row[0].strip()
            org, repo = parse_org_and_repo_from_url(url)
            if not org or not repo:
                continue

            key = (org, repo)
            repo_data[key]["total"] += 1

            size = get_file_size_bytes(url)
            if size > SIZE_THRESHOLD_BYTES:
                repo_data[key]["over_100mb"] += 1
                print(f">100MB: {url} ({size / 1024 / 1024:.2f} MB)")

    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "org", "repo_name", "has_binary_over_100mb", "binary_file_count_over_100mb", "total_url_count"
        ])
        writer.writeheader()
        for (org, repo), stats in repo_data.items():
            writer.writerow({
                "org": org,
                "repo_name": repo,
                "has_binary_over_100mb": stats["over_100mb"] > 0,
                "binary_file_count_over_100mb": stats["over_100mb"],
                "total_url_count": stats["total"]
            })

    print(f"✅ Output written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
