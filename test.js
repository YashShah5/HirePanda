import os
import logging
import csv
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

# --- Helper Functions ---
def authenticate_github(token, base_url=None):
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(token)

def validate_auth(token, org_name, base_url=None):
    try:
        gh = authenticate_github(token, base_url)
        org = gh.get_organization(org_name)
        return gh, org
    except BadCredentialsException:
        raise ValueError(f"Invalid credentials for {base_url or 'SaaS'} GitHub.")
    except Exception as e:
        raise ValueError(f"Error authenticating with {base_url or 'SaaS'}: {e}")

def fetch_tags(repo):
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}

def compare_tags(source_tags, target_tags):
    return [(name, sha) for name, sha in source_tags.items() if name not in target_tags]

def write_csv(missing_tags):
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Missing Tag Name", "Commit SHA"])
        for name, sha in missing_tags:
            writer.writerow([name, sha])
    logging.info(f"CSV report written to {OUTPUT_CSV}")

# --- Main Execution ---
def verify_tags():
    try:
        logging.info("Authenticating with GitHub instances...")

        on_prem_g, _ = validate_auth(ON_PREM_TOKEN, ON_PREM_ORG, ON_PREM_BASE_URL)
        saas_g, _ = validate_auth(SAAS_TOKEN, SAAS_ORG)

        logging.info("Fetching repositories...")
        on_prem_repo = on_prem_g.get_repo(f"{ON_PREM_ORG}/{ON_PREM_REPO}")
        saas_repo = saas_g.get_repo(f"{SAAS_ORG}/{SAAS_REPO}")

        logging.info("Fetching tags...")
        on_prem_tags = fetch_tags(on_prem_repo)
        saas_tags = fetch_tags(saas_repo)

        missing_tags = compare_tags(on_prem_tags, saas_tags)

        if missing_tags:
            logging.warning(f"{len(missing_tags)} tags are missing in SaaS.")
        else:
            logging.info("All tags are present in both repositories.")

        write_csv(missing_tags)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"GitHub API error: {e}")
    except ValueError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    verify_tags()
