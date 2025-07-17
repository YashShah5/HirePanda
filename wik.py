import os
import csv
import subprocess
import shutil
from urllib.parse import urlparse
from github import Github
from dotenv import load_dotenv

# === Load .env ===
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found in .env file")

# === Configuration ===
GITHUB_BASE_URL = "https://github.qualcomm.com/api/v3"
INPUT_CSV = "input.csv"
OUTPUT_CSV = "orgs_with_wiki_attachments.csv"
TMP_CLONE_DIR = "./tmp_wikis"

# === GitHub setup ===
g = Github(base_url=GITHUB_BASE_URL, login_or_token=GITHUB_TOKEN)
os.makedirs(TMP_CLONE_DIR, exist_ok=True)
orgs_with_attachments = set()

# === Extract orgs from input.csv ===
def extract_orgs_from_csv(csv_path):
    orgs = set()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("link") or row.get("Link") or row.get("URL")
            if url:
                parsed = urlparse(url)
                parts = parsed.path.strip("/").split("/")
                if parts:
                    orgs.add(parts[0])
    return list(orgs)

# === Check each repo in org for attachments ===
def check_org_for_attachments(org_name):
    print(f"\n🔍 Checking org: {org_name}")
    try:
        org = g.get_organization(org_name)
        repos = org.get_repos()

        for repo in repos:
            print(f"➡️  Repo: {repo.full_name} | has_wiki={repo.has_wiki}")

            if not repo.has_wiki:
                print(f"   ⛔ Skipping (wiki disabled)")
                continue

            wiki_url = f"https://{GITHUB_TOKEN}@github.qualcomm.com/{org_name}/{repo.name}.wiki.git"
            clone_path = os.path.join(TMP_CLONE_DIR, f"{org_name}__{repo.name}.wiki")

            result = subprocess.run(
                ["git", "clone", "--depth=1", wiki_url, clone_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if result.returncode != 0:
                print(f"   ❌ Wiki clone failed: {result.stderr.decode().strip()}")
                continue
            print(f"   ✅ Wiki cloned successfully.")

            attachments_path = os.path.join(clone_path, "attachments")
            if os.path.isdir(attachments_path):
                files = os.listdir(attachments_path)
                if files:
                    print(f"   📎 Attachments found in {repo.full_name}: {files}")
                    orgs_with_attachments.add(org_name)
                    shutil.rmtree(clone_path, ignore_errors=True)
                    return  # One match per org is enough
                else:
                    print(f"   🚫 attachments/ folder is empty.")
            else:
                print(f"   🚫 No attachments/ folder found.")

            shutil.rmtree(clone_path, ignore_errors=True)

    except Exception as e:
        print(f"⚠️ Error scanning org {org_name}: {e}")

# === Run ===
orgs = extract_orgs_from_csv(INPUT_CSV)
print(f"\n🔎 Found {len(orgs)} orgs in CSV: {orgs}")

for org_name in orgs:
    check_org_for_attachments(org_name)

# === Output CSV ===
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["org_name"])
    for org in sorted(orgs_with_attachments):
        writer.writerow([org])

print(f"\n✅ Done. Found {len(orgs_with_attachments)} org(s) with wiki attachments.")
print(f"📄 Results saved to {OUTPUT_CSV}")
