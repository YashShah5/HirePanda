# tag-validation-org-level.py
"""
Compares tags for all repositories in a GitHub organization (source vs. destination).
Outputs any missing tags to a CSV file.
"""

import os
import csv
import logging
import traceback
from typing import Dict, Optional
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

DESTINATION_TOKEN: Optional[str] = os.getenv("DESTINATION_TOKEN")
DESTINATION_ORG: Optional[str] = os.getenv("DESTINATION_ORG")

OUTPUT_CSV: str = os.getenv("OUTPUT_CSV", "missing_tags_report.csv")


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


# --- Fetch tags from repo ---
def fetch_tags(repo: Repository.Repository) -> Dict[str, str]:
    logging.info(f"Fetching tags from repo: {repo.full_name}")
    return {tag.name: tag.commit.sha for tag in repo.get_tags()}


# --- Compare tags ---
def compare_tags(
    source_tags: Dict[str, str],
    destination_tags: Dict[str, str]
) -> Dict[str, str]:
    missing_tags: Dict[str, str] = {}
    for name, sha in source_tags.items():
        if name not in destination_tags:
            missing_tags[name] = sha
    return missing_tags


# --- Write missing tags to CSV ---
def write_csv(missing_tag_data: list[dict]) -> None:
    logging.info(f"Writing missing tags report to CSV: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Repository Name", "Missing Tag Name", "Commit SHA"])
        for row in missing_tag_data:
            writer.writerow([row["repo"], row["tag"], row["sha"]])
    logging.info("CSV write complete.")


# --- Main Logic: Verify tags for all repos in the org ---
def verify_org_tags() -> None:
    try:
        logging.info("Starting org-level tag verification...")

        # Authenticate to GitHub for source and destination
        source_gh: Github = validate_auth(
            SOURCE_TOKEN, SOURCE_ORG, SOURCE_BASE_URL, label="source"
        )
        destination_gh: Github = validate_auth(
            DESTINATION_TOKEN, DESTINATION_ORG, label="destination"
        )

        # Get org objects
        source_org = source_gh.get_organization(SOURCE_ORG)
        destination_org = destination_gh.get_organization(DESTINATION_ORG)

        # Get list of repos
        source_repos = {repo.name: repo for repo in source_org.get_repos()}
        destination_repos = {repo.name: repo for repo in destination_org.get_repos()}
        logging.info(f"Found {len(source_repos)} repos in source org.")
        logging.info(f"Found {len(destination_repos)} repos in destination org.")

        # Compare tags for each repo present in both orgs
        missing_tag_data: list[dict] = []

        for repo_name, source_repo in source_repos.items():
            if repo_name not in destination_repos:
                logging.warning(f"Repo '{repo_name}' not found in destination. Skipping.")
                continue

            destination_repo = destination_repos[repo_name]
            source_tags = fetch_tags(source_repo)
            destination_tags = fetch_tags(destination_repo)

            missing_tags = compare_tags(source_tags, destination_tags)
            if missing_tags:
                for name, sha in missing_tags.items():
                    missing_tag_data.append({
                        "repo": repo_name,
                        "tag": name,
                        "sha": sha
                    })
                logging.warning(f"{len(missing_tags)} tag(s) missing in '{repo_name}'.")
            else:
                logging.info(f"All tags present in '{repo_name}'.")

        # Write the final report to CSV
        write_csv(missing_tag_data)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"GitHub API error: {e}")
    except ValueError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        traceback.print_exc()


# --- Entry Point ---
if __name__ == "__main__":
    verify_org_tags()
