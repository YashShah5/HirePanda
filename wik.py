import os
import csv
import subprocess
import shutil
from urllib.parse import urlparse
from github import Github
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found. Set it in a .env file.")

# === Configuration ===
GITHUB_BASE_URL = "https://github.qualcomm.com/api/v3"
INPUT_CSV = "input.csv"  # your input CSV file
OUTPUT_CSV = "orgs_with_wiki_attachments.csv"
TMP_CLONE_DIR = "./tmp_wikis"

# === GitHub client ===
g = Github(base_url=GITHUB_BASE_URL, login_or_token=GITHUB_TOKEN)
os.makedirs(TMP_CLONE_DIR, exist_ok=True)
orgs_with_attachments = set()

# === Step 1: Extract org names from input CSV ===
def extract_orgs_from_csv(csv_path):
    orgs = set()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("link") or row.get("Link")
            if url:
                parsed = urlparse(url)
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 1:
                    orgs.add(parts[0])
    return list(orgs)

# === Step 2: Scan each org for wiki attachments ===
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
                subprocess.run(
                    ["git", "clone", "--depth=1", wiki_url, clone_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                attachments_dir = os.path.join(clone_path, "attachments")

                if os.path.isdir(attachments_dir) and os.listdir(attachments_dir):
                    print(f"✅ Found attachments in: {org_name}/{repo.name}")
                    orgs_with_attachments.add(org_name)
                    break  # We only need 1 match per org

            except subprocess.CalledProcessError:
                # Wiki might not exist or is private/uninitialized
                continue
            finally:
                shutil.rmtree(clone_path, ignore_errors=True)

    except Exception as e:
        print(f"⚠️ Error with org {org_name}: {e}")

# === Run the script ===
orgs = extract_orgs_from_csv(INPUT_CSV)
for org_name in orgs:
    check_org_for_attachments(org_name)

# === Save results to output CSV ===
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["org_name"])
    for org in sorted(orgs_with_attachments):
        writer.writerow([org])

print(f"\n🎉 Done! {len(orgs_with_attachments)} org(s) have wiki attachments.")
print(f"📄 Output saved to: {OUTPUT_CSV}")
