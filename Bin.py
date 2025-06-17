import os
import csv
import subprocess
import shutil
import requests
from dotenv import load_dotenv

# Load GitHub token from .env
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
BASE_URL = "https://api.github.com"

# Constants
SIZE_THRESHOLD_BYTES = 100 * 1024 * 1024
BINARY_EXTENSIONS = {
    '.zip', '.tar', '.gz', '.7z', '.rar', '.mp4', '.mp3', '.mov',
    '.exe', '.bin', '.iso', '.dll', '.so', '.pdf', '.jpg', '.png'
}
OUTPUT_CSV = "binary_over_100mb_report.csv"

def get_all_orgs():
    orgs = []
    page = 1
    while True:
        res = requests.get(f"{BASE_URL}/user/orgs?per_page=100&page={page}", headers=HEADERS)
        if res.status_code != 200:
            break
        data = res.json()
        if not data:
            break
        orgs.extend([org["login"] for org in data])
        page += 1
    return orgs

def get_all_repos(org_name):
    repos = []
    page = 1
    while True:
        res = requests.get(f"{BASE_URL}/orgs/{org_name}/repos?per_page=100&page={page}", headers=HEADERS)
        if res.status_code != 200:
            break
        data = res.json()
        if not data:
            break
        repos.extend([repo["clone_url"] for repo in data if not repo.get("archived", False)])
        page += 1
    return repos

def is_binary_file(filename):
    return os.path.splitext(filename)[1].lower() in BINARY_EXTENSIONS

def check_binary_files_over_100mb(repo_path):
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if is_binary_file(file_path):
                    if os.path.getsize(file_path) > SIZE_THRESHOLD_BYTES:
                        return True
            except Exception:
                continue
    return False

def clone_and_check(repo_url):
    repo_name = repo_url.split('/')[-1].replace(".git", "")
    if os.path.exists(repo_name):
        shutil.rmtree(repo_name)
    try:
        subprocess.run(["git", "clone", "--depth", "1", repo_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_large_binary = check_binary_files_over_100mb(repo_name)
        shutil.rmtree(repo_name)
        return has_large_binary
    except Exception:
        return False

def main():
    orgs = get_all_orgs()
    results = []

    for org in orgs:
        repos = get_all_repos(org)
        for repo_url in repos:
            has_large_binary = clone_and_check(repo_url)
            results.append({
                "org": org,
                "repo_url": repo_url,
                "has_binary_over_100mb": has_large_binary
            })

    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["org", "repo_url", "has_binary_over_100mb"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

if __name__ == "__main__":
    main()
