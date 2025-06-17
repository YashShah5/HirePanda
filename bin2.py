import csv
import os
from urllib.parse import urlparse
from collections import defaultdict
from dotenv import load_dotenv

# Load .env if needed
load_dotenv()

INPUT_CSV = "url.csv"
OUTPUT_CSV = "binary_over_100mb_report.csv"
BASE_URL = os.getenv("GITHUB_BASE_URL", "https://github-test.qualcomm.com")

def parse_org_and_repo_from_url(url):
    try:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    except Exception as e:
        print(f"URL parse error: {url} → {e}")
    return None, None

def main():
    repo_summary = defaultdict(lambda: {"count": 0})

    if not os.path.exists(INPUT_CSV):
        print(f"[ERROR] File not found: {INPUT_CSV}")
        return

    with open(INPUT_CSV, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            url = row[0].strip()
            if not url or not isinstance(url, str) or not url.startswith(BASE_URL):
                continue

            org, repo = parse_org_and_repo_from_url(url)
            if not org or not repo:
                continue

            key = (org, repo)
            repo_summary[key]["count"] += 1

    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "org", "repo_name", "has_binary_over_100mb", "total_url_count"
        ])
        writer.writeheader()
        for (org, repo), stats in repo_summary.items():
            writer.writerow({
                "org": org,
                "repo_name": repo,
                "has_binary_over_100mb": True,  # You already filtered these as binary
                "total_url_count": stats["count"]
            })

    print(f"✅ Output written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
