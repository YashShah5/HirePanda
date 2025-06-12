import os
import requests
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = os.getenv("GITHUB_ORG")

BASE_URL = "https://api.github.com"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def check_repo_disabled(org, repo_name):
    url = f"{BASE_URL}/repos/{org}/{repo_name}"
    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        print(f"Repo: {repo_name} - Status: 404 (Assumed Disabled)")
        return True
    elif response.status_code == 200:
        data = response.json()
        disabled = data.get("disabled", False)
        print(f"Repo: {repo_name} - Disabled: {disabled}")
        return disabled
    else:
        print(f"Repo: {repo_name} - Unexpected Status: {response.status_code} (Assumed Enabled)")
        return False

def read_repo_list(csv_path):
    repo_names = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            repo_names.append(row["repo_name"])
    return repo_names

def write_csv_output(repo_results, org_complex):
    output_file = "disabled_repos_report.csv"
    with open(output_file, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repository Name", "Disabled"])
        for repo_name, disabled in repo_results.items():
            writer.writerow([repo_name, disabled])
        writer.writerow([])
        writer.writerow(["Org Marked Complex", "Yes" if org_complex else "No"])
    print(f"\n CSV saved as: {output_file}")

def main():
    print(f"Starting check for org: {ORG_NAME}")

    repo_names = read_repo_list("repos.csv")
    repo_results = {}
    has_disabled = False

    for repo in repo_names:
        disabled = check_repo_disabled(ORG_NAME, repo)
        repo_results[repo] = disabled
        if disabled:
            has_disabled = True

    if has_disabled:
        print(f"\n Org '{ORG_NAME}' is marked COMPLEX due to disabled repos.")
    else:
        print(f"\n Org '{ORG_NAME}' has no disabled repos — NOT complex.")

    write_csv_output(repo_results, has_disabled)

if __name__ == "__main__":
    main()