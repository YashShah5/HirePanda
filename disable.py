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

def get_org_repos(org_name):
    repos = []
    page = 1

    while True:
        url = f"{BASE_URL}/orgs/{org_name}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching repos: {response.status_code}")
            return repos

        data = response.json()
        if not data:
            break

        for repo in data:
            repos.append({
                "name": repo["name"],
                "disabled": repo.get("disabled", False)
            })

        page += 1

    return repos

def write_to_csv(repos, org_complex):
    filename = f"disabled_repos_report.csv"
    with open(filename, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repository Name", "Disabled"])
        for repo in repos:
            writer.writerow([repo["name"], repo["disabled"]])
        writer.writerow([])
        writer.writerow(["Org Marked Complex", org_complex])

    print(f"\n📁 CSV saved as: {filename}")

def check_for_disabled_repos(repos):
    has_disabled = False
    for repo in repos:
        print(f"Checking repo: {repo['name']} - Disabled: {repo['disabled']}")
        if repo['disabled']:
            has_disabled = True
    return has_disabled

def main():
    print(f"Fetching repos for org: {ORG_NAME}")
    repos = get_org_repos(ORG_NAME)

    if not repos:
        print("No repos found or failed to fetch.")
        return

    print(f"Total repos checked: {len(repos)}")
    has_disabled = check_for_disabled_repos(repos)

    if has_disabled:
        print(f"\n🔴 Org '{ORG_NAME}' is marked COMPLEX due to disabled repositories.")
    else:
        print(f"\n🟢 Org '{ORG_NAME}' has no disabled repos — NOT complex.")

    write_to_csv(repos, "Yes" if has_disabled else "No")

if __name__ == "__main__":
    main()