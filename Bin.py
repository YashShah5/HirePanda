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
SIZE_THRESHOLD_BYTES = 1 * 1024 * 1024  # 1MB for debug
OUTPUT_CSV = "binary_over_1mb_report.csv"

# TEMP: Treat all files as binary to verify detection
def is_binary_file(filename):
    return True

def get_all_orgs():
    orgs = []
    page = 1
    while True:
        res = requests.get(f"{BASE_URL}/user/orgs?per_page=100&page={page}", headers=HEADERS)
        if res.status_code != 200:
            print("Failed to fetch orgs:", res.text)
            break
        data = res.json()
        if not data:
            break
        orgs.extend([org["login"] for org in data])
        page += 1
    print(f"Found {len(orgs)} orgs: {orgs}")
    return orgs

def get_all_repos(org_name):
    repos = []
    page = 1
    while True:
        res = requests.get(f"{BASE_URL}/orgs/{org_name}/repos?per_page=100&page={page}", headers=HEADERS)
        if res.status_code != 200:
            print(f"Failed to fetch repos for {org_name}: {res.text}")
            break
        data = res.json()
        if not data:
            break
        urls = [repo["clone_url"] for repo in data if not repo.get("archived", False)]
        print(f"{org_name}: Found {len(urls)} repos")
        repos.extend(urls)
        page += 1
    return repos

def check_binary_files_over_threshold(repo_path):
    try:
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if is_binary_file(file_path):
                    size = os.path.getsize(file_path)
                    if size > SIZE_THRESHOLD_BYTES:
                        print(f"Binary > threshold: {file_path} ({size / 1024 / 1024:.2f} MB)")
                        return True
    except Exception as e:
        print(f"Error scanning {repo_path}: {e}")
    return False

def clone_and_check(repo_url):
    repo_name = repo_url.split('/')[-1].replace(".git", "")
    if os.path.exists(repo_name):
        shutil.rmtree(repo_name)
    try:
        print(f"Cloning {repo_url}")
        subprocess.run(["git", "clone", "--depth", "1", repo_url], check=True)
        has_large_binary = check_binary_files_over_threshold(repo_name)
        shutil.rmtree(repo_name)
        return has_large_binary
    except subprocess.CalledProcessError as e:
        print(f"Clone failed for {repo_url}: {e}")
    except Exception as e:
        print(f"Unexpected error for {repo_url}: {e}")
    return False

def main():
    orgs = get_all_orgs()
    results = []

    for org in orgs:
        repos = get_all_repos(org)
        for repo_url in repos:
            print(f"Checking repo: {repo_url}")
            has_large_binary = clone_and_check(repo_url)
            results.append({
                "org": org,
                "repo_url": repo_url,
                "has_binary_over_1mb": has_large_binary
            })

    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["org", "repo_url", "has_binary_over_1mb"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"\nCSV written to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
