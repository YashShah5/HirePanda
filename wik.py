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
    raise ValueError("❌ GITHUB_TOKEN not found. Please set it in your .env file.")

# === Configuration ===
GITHUB_BASE_URL = "https://github.qualcomm.com/api/v3"
INPUT_CSV = "input.csv"
OUTPUT_CSV = "orgs_with_wiki_attachments.csv"
TMP_CLONE_DIR = "./tmp_wikis"

# === GitHub client ===
g = Github(base_url=GITHUB_BASE_URL, login_or_token=GITHUB_TOKEN)
os.makedirs(TMP_CLONE_DIR, exist_ok=True)
orgs_with_attachments = set()

# === Step 1: Extract org names from CSV ===
def extract_orgs_from_csv(csv_path):
    orgs = set()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("link") or row.get("Link") or row.get("URL")
            if url:
                parsed = urlparse(url)
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 1:
                    orgs.add(parts[0])
    return list(orgs)

# === Step 2: Check each repo for wiki attachments ===
def check_org_for_attachments(org_name):
    try:
        org = g.get_organization(org_name)
        print(f"\n🔍 Scanning org: {org_name}")
        repos = org.get_repos()

        for repo in repos:
            print(f"➡️  Repo: {repo.full_name} | has_wiki={repo.has_wiki}")
            if not repo.has_wiki:
                continue

            wiki_url = f"https://{GITHUB_TOKEN}@github.qualcomm.com/{org_name}/{repo.name}.wiki.git"
            clone_path = os.path.join(TMP_CLONE_DIR, f"{org_name}__{repo.name}.wiki")

            result = subprocess.run(
                ["git", "clone", "--depth=1", wiki_url, clone_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                print(f"   ❌ Could not clone wiki: {result.stderr.decode().strip()}")
                continue

            print(f"   ✅ Wiki cloned successfully.")
            attachments_path = os.path.join(clone_path, "attachments")

            if os.path.isdir(attachments_path):
                attachment_files = os.listdir(attachments_path)
                if attachment_files:
                    print(f"   📎 Attachments found: {attachment_files}")
                    orgs_with_attachments.add(org_name)
                    break  # One match per org is enough
                else:
                    print(f"   🚫 attachments/ folder exists but is empty.")
            else:
                print(f"   🚫 attachments/ folder not found.")

            shutil.rmtree(clone_path, ignore_errors=True)

    except Exception as e:
        print(f"⚠️ Error processing org {org_name}: {e}")

# === Main ===
orgs = extract_orgs_from_csv(INPUT_CSV)
print(f"\n📦 Found {len(orgs)} org(s): {orgs}\n")

for org_name in orgs:
    check_org_for_attachments(org_name)

# === Output Results ===
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["org_name"])
    for org in sorted(orgs_with_attachments):
        writer.writerow([org])

print(f"\n✅ Done. Found {len(orgs_with_attachments)} org(s) with wiki attachments.")
print(f"📄 Output written to: {OUTPUT_CSV}")
