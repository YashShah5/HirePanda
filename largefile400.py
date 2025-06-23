import csv
import os
import subprocess
import tempfile
import shutil
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

INPUT_CSV = 'urlTestGreater.csv'
OUTPUT_CSV = 'repo_large_file_report.csv'
SIZE_THRESHOLD_BYTES = 400 * 1024 * 1024  # 400MB


def format_url_with_token(repo_url):
    """Insert the token into the URL for authentication."""
    if GITHUB_TOKEN and "@" not in repo_url:
        if repo_url.startswith("https://"):
            parts = repo_url.split("https://")
            return f"https://{GITHUB_TOKEN}@{parts[1]}"
    return repo_url


def clone_repo(repo_url, destination):
    """Clone the repo to a temp folder using the token if needed."""
    try:
        secure_url = format_url_with_token(repo_url)
        subprocess.run(['git', 'clone', '--depth=1', secure_url, destination], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Cloning failed: {repo_url} — {e}")
        return False


def has_file_over_threshold(path):
    """Walk the repo and check if any file is over 400MB."""
    for root, _, files in os.walk(path):
        for f in files:
            try:
                size = os.path.getsize(os.path.join(root, f))
                if size > SIZE_THRESHOLD_BYTES:
                    return True
            except Exception:
                continue
    return False


def main():
    with open(INPUT_CSV, newline='') as csvfile:
        reader = csv.reader(csvfile)
        urls = [row[0].strip() for row in reader if row]

    with open(OUTPUT_CSV, mode='w', newline='') as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(['repo_url', 'has_large_file'])

        for url in urls:
            with tempfile.TemporaryDirectory() as tmpdir:
                print(f"[INFO] Checking {url}")
                if clone_repo(url, tmpdir):
                    large_file_found = has_file_over_threshold(tmpdir)
                    writer.writerow([url, large_file_found])
                else:
                    writer.writerow([url, 'CLONE_FAILED'])


if __name__ == "__main__":
    main()
