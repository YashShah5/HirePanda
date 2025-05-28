import os
import csv
import logging
from pathlib import Path
from github import Github, Auth, BadCredentialsException, RateLimitExceededException, UnknownObjectException
from requests.exceptions import RequestException
from dotenv import load_dotenv

# --- Load .env ---
dotenv_path = Path('.') / '.env'
load_dotenv(dotenv_path=dotenv_path)

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Load and validate env vars ---
def get_env_var(name, required=True):
    value = os.getenv(name)
    if required and (value is None or not value.strip()):
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value.strip() if value else value

# --- Config Vars ---
ON_PREM_BASE_URL = get_env_var("ON_PREM_BASE_URL")
ON_PREM_TOKEN = get_env_var("ON_PREM_TOKEN")
ON_PREM_ORG = get_env_var("ON_PREM_ORG")
ON_PREM_REPO = get_env_var("ON_PREM_REPO")

SAAS_TOKEN = get_env_var("SAAS_TOKEN")
SAAS_ORG = get_env_var("SAAS_ORG")
SAAS_REPO = get_env_var("SAAS_REPO")

OUTPUT_CSV = get_env_var("OUTPUT_CSV", required=False) or "missing_tags.csv"

# --- Debug Dump ---
print("\n🔍 DEBUG: Loaded Config")
print(f"ON_PREM_ORG: {ON_PREM_ORG} | REPO: {ON_PREM_REPO} | BASE_URL: {ON_PREM_BASE_URL}")
print(f"SAAS_ORG: {SAAS_ORG} | REPO: {SAAS_REPO}")
print(f"SAAS_TOKEN: {'Set' if SAAS_TOKEN else 'MISSING'}")
print(f"ON_PREM_TOKEN: {'Set' if ON_PREM_TOKEN else 'MISSING'}")
print(f"Output CSV: {OUTPUT_CSV}\n")

# --- GitHub Auth ---
def authenticate_github(token, base_url=None):
    if not token or len(token.strip()) < 10:
        raise ValueError("GitHub token is missing or too short.")
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token.strip()))
    return Github(token.strip())

def validate_auth(token, org_name, base_url=None, label="Unknown"):
    logging.info(f"🔐 Authenticating with {label} GitHub...")
    print(f"  ➤ TOKEN preview ({label}): {token[:6]}...")
    print(f"  ➤ ORG: {org_name}")
    print(f"  ➤ BASE_URL: {base_url or 'https://api.github.com'}")

    try:
        gh = authenticate_github(token, base_url)
        org = gh.get_organization(org_name)
        logging.info(f"✅ Authenticated to {label} GitHub.")
        return gh, org
    except BadCredentialsException:
        raise ValueError(f"❌ Invalid credentials for {label} GitHub.")
    except Exception as e:
        raise ValueError(f"❌ Error authenticating with {label} GitHub: {e}")

# --- Tag Utilities ---
def fetch_tags(repo, label):
    logging.info(f"🔄 Fetching tags from {label} repo: {repo.full_name}")
    tags = {tag.name: tag.commit.sha for tag in repo.get_tags()}
    logging.info(f"📦 {len(tags)} tags found in {label}.")
    return tags

def compare_tags(source_tags, target_tags):
    return [(name, sha) for name, sha in source_tags.items() if name not in target_tags]

def write_csv(missing_tags):
    logging.info(f"📝 Writing output to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Missing Tag Name", "Commit SHA"])
        for name, sha in missing_tags:
            writer.writerow([name, sha])
    logging.info(f"✅ CSV report saved.")

# --- Main Logic ---
def verify_tags():
    try:
        logging.info("🚀 Starting tag verification...")

        # Authenticate
        on_prem_g, _ = validate_auth(ON_PREM_TOKEN, ON_PREM_ORG, ON_PREM_BASE_URL, label="ON-PREM")
        saas_g, _ = validate_auth(SAAS_TOKEN, SAAS_ORG, None, label="SAAS")

        # Fetch repos
        logging.info("📁 Accessing repositories...")
        on_prem_repo = on_prem_g.get_repo(f"{ON_PREM_ORG}/{ON_PREM_REPO}")
        saas_repo = saas_g.get_repo(f"{SAAS_ORG}/{SAAS_REPO}")
        logging.info("✅ Repositories loaded.")

        # Fetch and compare tags
        on_prem_tags = fetch_tags(on_prem_repo, "ON-PREM")
        saas_tags = fetch_tags(saas_repo, "SAAS")

        missing_tags = compare_tags(on_prem_tags, saas_tags)

        if missing_tags:
            logging.warning(f"⚠️ {len(missing_tags)} tag(s) missing in SaaS.")
        else:
            logging.info("🎉 All tags match between ON-PREM and SAAS.")

        write_csv(missing_tags)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"🌐 GitHub API/network error: {e}")
    except ValueError as ve:
        logging.error(str(ve))
    except Exception as e:
        logging.error(f"💥 Unexpected error: {e}")

# --- Run ---
if __name__ == "__main__":
    verify_tags()
