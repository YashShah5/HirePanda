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
SOURCE_BASE_URL = os.getenv("SOURCE_BASE_URL")
SOURCE_TOKEN = os.getenv("SOURCE_TOKEN")
SOURCE_ORG = os.getenv("SOURCE_ORG")
SOURCE_REPO = os.getenv("SOURCE_REPO")

DESTINATION_TOKEN = os.getenv("DESTINATION_TOKEN")
DESTINATION_ORG = os.getenv("DESTINATION_ORG")
DESTINATION_REPO = os.getenv("DESTINATION_REPO")

OUTPUT_CSV = os.getenv("OUTPUT_CSV", "missing_tags.csv")

# --- GitHub Authentication ---
def authenticate_github(token, base_url=None):
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(token)

def validate_auth(token, org_name, base_url=None, label=""):
    if not token or len(token.strip()) < 10:
        raise ValueError(f"GitHub token is missing or malformed for {label}")

    logging.info(f"Authenticating with {label} GitHub for org: {org_name}")
    try:
        gh = authenticate_github(token.strip(), base_url)
        org = gh.get_organization(org_name)
        logging.info(f"Successfully authenticated with {label} GitHub.")
        return gh, org
    except BadCredentialsException:
        raise ValueError(f"Invalid GitHub credentials for {label}")
    except Exception as e:
        raise ValueError(f"Error authenticating with {label}: {e}")

# --- Tag Fetch & Comparison ---
def fetch_tags(repo):
    logging.info(f"Fetching tags from repo: {repo.full_name}")
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}

def compare_tags(source_tags, destination_tags):
    return [(name, sha) for name, sha in source_tags.items() if name not in destination_tags]

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

        source_gh, _ = validate_auth(SOURCE_TOKEN, SOURCE_ORG, SOURCE_BASE_URL, label="source")
        destination_gh, _ = validate_auth(DESTINATION_TOKEN, DESTINATION_ORG, label="destination")

        logging.info("Loading repositories...")
        source_repo = source_gh.get_repo(f"{SOURCE_ORG}/{SOURCE_REPO}")
        destination_repo = destination_gh.get_repo(f"{DESTINATION_ORG}/{DESTINATION_REPO}")
        logging.info("Repositories loaded successfully.")

        source_tags = fetch_tags(source_repo)
        destination_tags = fetch_tags(destination_repo)

        missing_tags = compare_tags(source_tags, destination_tags)

        if missing_tags:
            logging.warning(f"{len(missing_tags)} tag(s) are missing in the destination.")
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
