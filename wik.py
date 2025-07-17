import os
import csv
import subprocess
import shutil
from urllib.parse import urlparse
from github import Github, GithubEnterprise

# === CONFIG ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Export this before running
GITHUB_BASE_URL = "https://github.qualcomm.com/api/v3"  # Adjust if your GHE has a different API URL
INPUT_CSV = "input.csv"
OUTPUT_CSV = "orgs_with_wiki_attachments.csv"
TMP_CLONE_DIR = "./tmp_wikis"

# === SETUP ===
g = GithubEnterprise(GITHUB_BASE_URL, login_or_token=GITHUB_TOKEN)
os.makedirs(TMP_CLONE_DIR, exist_ok=True)
orgs_with_attachments = set()

# === STEP 1: READ ORG NAMES FROM CSV ===
def extract_orgs_from_csv(csv_path):
    orgs = set()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("link") or row.get("Link")  # allow for lowercase or uppercase column
            if url:
                parsed = urlparse(url)
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 1:
                    orgs.add(parts[0])
    return list(orgs)

# === STEP 2: PROCESS EACH ORG ===
def check_org_for_attachments(org_name):
    try:
        org = g.get_organization(org_name)
        print(f"🔍 Scanning org: {org_name}")
        repos = org.get_repos()

        for repo in repos:
            if not repo.has_wiki:
                continue

            wiki_url = f"https://{GITHUB_TOKEN}@github.qualcomm.com/{org_name}/{repo.name}.wiki.git"
            clone_path = os.path.join(TMP_CLONE_DIR, f"{org_name}__{repo.name}.wiki")

            try:
                subprocess.run(["git", "clone", "--depth=1", wiki_url, clone_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                attachments_dir = os.path.join(clone_path, "attachments")

                if os.path.isdir(attachments_dir) and os.listdir(attachments_dir):
                    print(f"✅ Found attachments in: {org_name}/{repo.name}")
                    orgs_with_attachments.add(org_name)
                    break  # One match per org is enough

            except subprocess.CalledProcessError:
                # Likely the wiki hasn't been initialized
                continue
            finally:
                shutil.rmtree(clone_path, ignore_errors=True)

    except Exception as e:
        print(f"⚠️ Error with org {org_name}: {e}")

# === MAIN ===
orgs = extract_orgs_from_csv(INPUT_CSV)
for org_name in orgs:
    check_org_for_attachments(org_name)

# === OUTPUT RESULT ===
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["org_name"])
    for org in sorted(orgs_with_attachments):
        writer.writerow([org])

print(f"\n🎉 Done! Found {len(orgs_with_attachments)} orgs with wikis that have attachments.")
print(f"📄 Output saved to {OUTPUT_CSV}")
