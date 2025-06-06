# tag-validation.py
"""
Compares GitHub tags between a source and destination repository.
Outputs any missing tags in a CSV file.

TODO
- Create README
- make "def compare_tags" more readable --> less intricate more top down/expand the lines
- add type safety
- arrow functions --> function annotations
"""

import os
import csv
import logging
import traceback
from typing import Optional, Dict
from github import (
    Github,
    Auth,
    BadCredentialsException,
    RateLimitExceededException,
    UnknownObjectException,
    Repository
)
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Logging Config ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Config values from .env ---
SOURCE_BASE_URL: Optional[str] = os.getenv("SOURCE_BASE_URL")
SOURCE_TOKEN: Optional[str] = os.getenv("SOURCE_TOKEN")
SOURCE_ORG: Optional[str] = os.getenv("SOURCE_ORG")
SOURCE_REPO: Optional[str] = os.getenv("SOURCE_REPO")

DESTINATION_TOKEN: Optional[str] = os.getenv("DESTINATION_TOKEN")
DESTINATION_ORG: Optional[str] = os.getenv("DESTINATION_ORG")
DESTINATION_REPO: Optional[str] = os.getenv("DESTINATION_REPO")

OUTPUT_CSV: str = os.getenv("OUTPUT_CSV", "missing_tags.csv")


# --- GitHub Authentication ---
def authenticate_github(token: str, base_url: Optional[str] = None) -> Github:
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(auth=Auth.Token(token))


def validate_auth(
    token: str,
    org_name: str,
    base_url: Optional[str] = None,
    label: str = ""
) -> Github:
    if not token or len(token.strip()) < 10:
        raise ValueError(f"GitHub token is missing or malformed for {label}")

    logging.info(f"Authenticating with {label} GitHub for org: {org_name}")
    try:
        gh: Github = authenticate_github(token.strip(), base_url)
        org = gh.get_organization(org_name)
        logging.info(f"Successfully authenticated with {label} GitHub.")
        return gh
    except BadCredentialsException:
        raise ValueError(f"Invalid GitHub credentials for {label}")
    except Exception as e:
        raise ValueError(f"Error authenticating with {label}: {e}")


# --- Tag Fetch & Comparison ---
def fetch_tags(repo: Repository.Repository) -> Dict[str, str]:
    logging.info(f"Fetching tags from repo: {repo.full_name}")
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}


def compare_tags(
    source_tags: Dict[str, str],
    destination_tags: Dict[str, str]
) -> Dict[str, str]:
    """
    Compares tags between source and destination repos.
    Returns a dictionary of tags present in source but missing in destination.
    """
    missing_tags: Dict[str, str] = {}

    # Iterate through each tag in the source
    for name, sha in source_tags.items():
        # Check if this tag is not in the destination
        if name not in destination_tags:
            # Add to the missing tags dictionary
            missing_tags[name] = sha

    return missing_tags


def write_csv(missing_tags: Dict[str, str]) -> None:
    logging.info(f"Writing missing tags to CSV: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Missing Tag Name", "Commit SHA"])
        for name, sha in missing_tags.items():
            writer.writerow([name, sha])
    logging.info("CSV write complete.")


# --- Main Logic ---
def verify_tags() -> None:
    try:
        logging.info("Starting tag verification...")

        source_gh: Github = validate_auth(
            SOURCE_TOKEN, SOURCE_ORG, SOURCE_BASE_URL, label="source"
        )
        destination_gh: Github = validate_auth(
            DESTINATION_TOKEN, DESTINATION_ORG, label="destination"
        )

        logging.info("Loading repositories...")
        source_repo: Repository.Repository = source_gh.get_repo(f"{SOURCE_ORG}/{SOURCE_REPO}")
        destination_repo: Repository.Repository = destination_gh.get_repo(f"{DESTINATION_ORG}/{DESTINATION_REPO}")
        logging.info("Repositories loaded successfully.")

        source_tags: Dict[str, str] = fetch_tags(source_repo)
        destination_tags: Dict[str, str] = fetch_tags(destination_repo)

        missing_tags: Dict[str, str] = compare_tags(source_tags, destination_tags)

        if missing_tags:
            logging.warning(
                f"{len(missing_tags)} tag(s) are missing in the destination."
            )
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
