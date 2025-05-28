import os
import csv
import logging
import traceback
from github import Github, Auth, BadCredentialsException, RateLimitExceededException, UnknownObjectException
from requests.exceptions import RequestException
from dotenv import load_dotenv

# --- Load environment variables from .env ---
load_dotenv()

# --- Logging Config ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Config values from .env ---
ON_PREM_BASE_URL = os.getenv("ON_PREM_BASE_URL")
ON_PREM_TOKEN = os.getenv("ON_PREM_TOKEN")
ON_PREM_ORG = os.getenv("ON_PREM_ORG")
ON_PREM_REPO = os.getenv("ON_PREM_REPO")

SAAS_TOKEN = os.getenv("SAAS_TOKEN")
SAAS_ORG = os.getenv("SAAS_ORG")
SAAS_REPO = os.getenv("SAAS_REPO")

OUTPUT_CSV = os.getenv("OUTPUT_CSV", "missing_tags.csv")

# --- GitHub Authentication ---
def authenticate_github(token, base_url=None):
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(token)

def validate_auth(token, org_name, base_url=None):
    if not token or len(token.strip()) < 10:
        raise ValueError(f"GitHub token is missing or malformed for {'SaaS' if not base_url else 'On-Prem'}")

    logging.info(f"Authenticating with {'SaaS' if not base_url else 'On-Prem'} GitHub for org: {org_name}")
    try:
        gh = authenticate_github(token.strip(), base_url)
        org = gh.get_organization(org_name)
        logging.info(f"Successfully authenticated with {'SaaS' if not base_url else 'On-Prem'} GitHub.")
        return gh, org
    except BadCredentialsException:
        raise ValueError(f"Invalid GitHub credentials for {'SaaS' if not base_url else 'On-Prem'}")
    except Exception as e:
        raise ValueError(f"Error authenticating with {'SaaS' if not base_url else 'On-Prem'}: {e}")

# --- Tag Fetch & Comparison ---
def fetch_tags(repo):
    logging.info(f"Fetching tags from repo: {repo.full_name}")
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}

def compare_tags(source_tags, target_tags):
    return [(name, sha) for name, sha in source_tags.items() if name not in target_tags]

def write_csv(missing_tags):
    logging.info(f"Writing missing tags to CSV: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Missing Tag Name", "Commit SHA"])
        for name, sha in missing_tags:
            writer.writerow([name, sha])
    logging.info("CSV write complete.")

# --- Main Logic ---
def verify_tags():
    try:
        logging.info("Starting tag verification...")

        on_prem_g, _ = validate_auth(ON_PREM_TOKEN, ON_PREM_ORG, ON_PREM_BASE_URL)
        saas_g, _ = validate_auth(SAAS_TOKEN, SAAS_ORG)

        logging.info("Loading repositories...")
        on_prem_repo = on_prem_g.get_repo(f"{ON_PREM_ORG}/{ON_PREM_REPO}")
        saas_repo = saas_g.get_repo(f"{SAAS_ORG}/{SAAS_REPO}")
        logging.info("Repositories loaded successfully.")

        on_prem_tags = fetch_tags(on_prem_repo)
        saas_tags = fetch_tags(saas_repo)

        missing_tags = compare_tags(on_prem_tags, saas_tags)

        if missing_tags:
            logging.warning(f"{len(missing_tags)} tag(s) are missing in SaaS.")
        else:
            logging.info("All tags are present in both repositories.")

        write_csv(missing_tags)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"GitHub API error: {e}")
    except ValueError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        traceback.print_exc()

# --- Entry Point ---
if __name__ == "__main__":
    verify_tags()
