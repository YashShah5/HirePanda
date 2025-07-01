"""
Compares GitHub issues across all repositories in a source vs. destination org.
Reports any issues that are missing on either side.
"""

import os
import csv
import logging
import traceback
from typing import Dict, Set, Optional, List
from github import (
    Github,
    Auth,
    Repository,
    BadCredentialsException,
    RateLimitExceededException,
    UnknownObjectException
)
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Load .env
load_dotenv()

# --- Logging Config ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Config ---
SOURCE_BASE_URL: Optional[str] = os.getenv("SOURCE_BASE_URL")
SOURCE_TOKEN: Optional[str] = os.getenv("SOURCE_TOKEN")
SOURCE_ORG: Optional[str] = os.getenv("SOURCE_ORG")

DESTINATION_TOKEN: Optional[str] = os.getenv("DESTINATION_TOKEN")
DESTINATION_ORG: Optional[str] = os.getenv("DESTINATION_ORG")

OUTPUT_CSV: str = os.getenv("OUTPUT_CSV", "missing_issues_report.csv")


# --- GitHub Auth ---
def authenticate_github(token: str, base_url: Optional[str] = None) -> Github:
    if base_url:
        return Github(base_url=base_url, auth=Auth.Token(token))
    return Github(auth=Auth.Token(token))


def validate_auth(token: str, org_name: str, base_url: Optional[str] = None, label: str = "") -> Github:
    if not token or len(token.strip()) < 10:
        raise ValueError(f"GitHub token is missing or malformed for {label}")

    logging.info(f"Authenticating with {label} GitHub for org: {org_name}")
    try:
        gh: Github = authenticate_github(token.strip(), base_url)
        gh.get_organization(org_name)
        logging.info(f"Successfully authenticated with {label} GitHub.")
        return gh
    except BadCredentialsException:
        raise ValueError(f"Invalid GitHub credentials for {label}")
    except Exception as e:
        raise ValueError(f"Error authenticating with {label}: {e}")


# --- Fetch Issues ---
def fetch_issue_numbers(repo: Repository.Repository) -> Set[int]:
    issue_nums: Set[int] = set()
    try:
        issues = repo.get_issues(state='all')
        for issue in issues:
            if not hasattr(issue, 'pull_request'):  # skip PRs
                issue_nums.add(issue.number)
        logging.info(f"{repo.full_name}: {len(issue_nums)} issue(s) found")
    except Exception as e:
        logging.warning(f"Failed to fetch issues for {repo.full_name}: {e}")
    return issue_nums


# --- Compare ---
def compare_issues(src: Set[int], dst: Set[int]) -> Dict[str, List[int]]:
    return {
        "missing_in_dest": sorted(list(src - dst)),
        "missing_in_source": sorted(list(dst - src))
    }


# --- CSV Writer ---
def write_csv(missing_data: List[Dict[str, str]]) -> None:
    logging.info(f"Writing report to: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Repository", "Direction", "Missing Issue Number"])
        for row in missing_data:
            writer.writerow([row["repo"], row["direction"], row["issue"]])
    logging.info("CSV write complete.")


# --- Main Logic ---
def verify_org_issues() -> None:
    try:
        logging.info("Starting issue comparison across orgs...")

        # Auth
        source_gh = validate_auth(SOURCE_TOKEN, SOURCE_ORG, SOURCE_BASE_URL, label="source")
        dest_gh = validate_auth(DESTINATION_TOKEN, DESTINATION_ORG, label="destination")

        source_org = source_gh.get_organization(SOURCE_ORG)
        dest_org = dest_gh.get_organization(DESTINATION_ORG)

        source_repos = {repo.name: repo for repo in source_org.get_repos()}
        dest_repos = {repo.name: repo for repo in dest_org.get_repos()}

        logging.info(f"Source repos: {len(source_repos)} | Destination repos: {len(dest_repos)}")

        report_data: List[Dict[str, str]] = []

        for repo_name, src_repo in source_repos.items():
            if repo_name not in dest_repos:
                logging.warning(f"Repo '{repo_name}' missing in destination org. Skipping.")
                continue

            dst_repo = dest_repos[repo_name]

            src_issues = fetch_issue_numbers(src_repo)
            dst_issues = fetch_issue_numbers(dst_repo)

            diffs = compare_issues(src_issues, dst_issues)

            for issue_num in diffs["missing_in_dest"]:
                report_data.append({
                    "repo": repo_name,
                    "direction": "missing_in_destination",
                    "issue": issue_num
                })

            for issue_num in diffs["missing_in_source"]:
                report_data.append({
                    "repo": repo_name,
                    "direction": "missing_in_source",
                    "issue": issue_num
                })

            if diffs["missing_in_dest"] or diffs["missing_in_source"]:
                logging.warning(f"Issue mismatch in '{repo_name}': "
                                f"{len(diffs['missing_in_dest'])} missing in destination, "
                                f"{len(diffs['missing_in_source'])} missing in source.")
            else:
                logging.info(f"Issues match for '{repo_name}'.")

        write_csv(report_data)

    except (RateLimitExceededException, RequestException) as e:
        logging.error(f"GitHub API error: {e}")
    except ValueError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        traceback.print_exc()


# --- Entry Point ---
if __name__ == "__main__":
    verify_org_issues()
