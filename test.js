import os
import logging
import csv
from github import Github, Auth, BadCredentialsException, RateLimitExceededException, UnknownObjectException
from requests.exceptions import RequestException

# --- Logging Config ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Load Environment Variables ---
ON_PREM_BASE_URL = os.getenv("ON_PREM_BASE_URL")
ON_PREM_TOKEN = os.getenv("ON_PREM_TOKEN")
ON_PREM_ORG = os.getenv("ON_PREM_ORG")

SAAS_TOKEN = os.getenv("SAAS_TOKEN")
SAAS_ORG = os.getenv("SAAS_ORG")

OUTPUT_CSV = "missing_tags.csv"

# --- Helper Functions ---
def authenticate_github(token, base_url=None):
    """Authenticate to GitHub instance using token (and optional base_url)."""
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(token)

def validate_auth(token, org_name, base_url=None):
    """Validates GitHub authentication and returns the GitHub org instance."""
    try:
        gh = authenticate_github(token, base_url)
        org = gh.get_organization(org_name)
        return gh, org
    except BadCredentialsException:
        raise ValueError(f"Invalid credentials for {base_url or 'SAAS'}. Please check your token and organization name.")
    except Exception as e:
        raise ValueError(f"Error authenticating with {base_url or 'SAAS'}: {e}")

def fetch_tags(repo):
    """Returns a dictionary of tag name to commit SHA for a given repository."""
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}

def compare_tags(on_prem_tags, saas_tags):
    """Compares tags from on-prem with SaaS and returns list of missing tags."""
    return [(name, sha) for name, sha in on_prem_tags.items() if name not in saas_tags]

def write_csv(missing_tags):
    """Outputs missing tags to a CSV file."""
    with open(OUTPUT_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Missing Tag Name", "Commit SHA"])
        for name, sha in missing_tags:
            writer.writerow([name, sha])
    logging.info(f"CSV report written: {OUTPUT_CSV}")

# --- Main Verification Logic ---
def verify_tags():
    try:
        logging.info("Authenticating with GitHub instances...")

        on_prem_g, _ = validate_auth(ON_PREM_TOKEN, ON_PREM_ORG, ON_PREM_BASE_URL)
        saas_g, _ = validate_auth(SAAS_TOKEN, SAAS_ORG)

        on_prem_repo = on_prem_g.get_repo(f"{ON_PREM_ORG}/has-pages")
        saas_repo = saas_g.get_repo(f"{SAAS_ORG}/has_pages")

        logging.info("Fetching tags from both repositories...")
        on_prem_tags = fetch_tags(on_prem_repo)
        saas_tags = fetch_tags(saas_repo)

        missing_tags = compare_tags(on_prem_tags, saas_tags)

        if missing_tags:
            logging.warning(f"{len(missing_tags)} tags are missing in SAAS.")
        else:
            logging.info("All tags are present in both repositories.")

        write_csv(missing_tags)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"Error accessing GitHub API: {e}")
    except ValueError as e:
        logging.error(str(e))
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    verify_tags()
