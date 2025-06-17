import csv
import os
import shutil
import subprocess
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
INPUT_CSV = "url.csv"
OUTPUT_CSV = "binary_over_100mb_report.csv"
SIZE_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100MB

def parse_org_repo(url):
    try:
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    except Exception as e:
        print(f"Error parsing URL: {url} → {e}")
    return None, None

def clone_repo(repo_url, repo_name):
    # Inject token if available
    if GITHUB_TOKEN:
        repo_url = repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
    try:
        subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_name],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"[!] Failed to clone: {repo_url}")
        return False

def has_large_file(path):
    for root, _, files in os.walk(path):
        for name in files:
            try:
                size = os.path.getsize(os.path.join(root, name))
                if size > SIZE_THRESHOLD_BYTES:
                    return True
            except:
                continue
    return False

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"[ERROR] Missing input file: {INPUT_CSV}")
        return

    results = []

    with open(INPUT_CSV, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0].strip():
                continue

            url = row[0].strip()
            org, repo = parse_org_repo(url)
            if not org or not repo:
                continue

            repo_dir = f"temp_repo_{repo}"
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)

            cloned = clone_repo(url, repo_dir)
            if not cloned:
                results.append({"org": org, "repo_name": repo, "has_binary_over_100mb": "clone_failed"})
                continue

            flag = has_large_file(repo_dir)
            results.append({"org": org, "repo_name": repo, "has_binary_over_100mb": flag})
            shutil.rmtree(repo_dir)

    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["org", "repo_name", "has_binary_over_100mb"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"✅ Done. Output saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
