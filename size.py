#!/usr/bin/env python3

import os
import csv
import logging
from github import Github, Auth, BadCredentialsException

# Load environment variables
GHES_BASE_URL = os.getenv('GHES_BASE_URL', '')
GHES_ORG = os.getenv('GHES_ORG', '')
GHES_TOKEN = os.getenv('GHES_TOKEN', '')

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_ghes_auth():
    """
    Validate GitHub authentication and return the Github instance.
    """
    try:
        auth = Auth.Token(GHES_TOKEN)
        g = Github(base_url=GHES_BASE_URL, auth=auth)
        org = g.get_organization(GHES_ORG)
        logging.info(f"Connected to GHES. Organization: {org.login}")
        return g
    except BadCredentialsException:
        raise ValueError("Bad GitHub token or org. Check your .env file.")
    except Exception as e:
        raise ValueError(f"Problem connecting to GHES: {e}")


def check_repo_size(repo):
    """
    Get the size of a repository and classify it.
    """
    try:
        size_kb = repo.size
        size_mb = size_kb / 1024
        size_gb = size_mb / 1024

        # Classify the repo
        if size_gb < 10:
            classification = 'Simple'
        elif 10 <= size_gb <= 20:
            classification = 'Medium'
        else:
            classification = 'Complex'

        logging.info(f"{repo.name} - {size_gb:.2f} GB - {classification}")
        return round(size_mb, 2), classification, 'Pass'
    except Exception as e:
        logging.error(f"Could not check size for {repo.name}: {e}")
        return 0.0, 'Unknown', 'Fail'


def main():
    """
    Main function that runs the whole process.
    """
    try:
        # Authenticate and get repos
        ghes = validate_ghes_auth()
        org = ghes.get_organization(GHES_ORG)
        repos = org.get_repos()

        # Create CSV report
        csv_filename = f"repo_size_report_{GHES_ORG}.csv"
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Repository", "Size (MB)", "Classification", "Preflight Check Result"])

            for repo in repos:
                size_mb, classification, result = check_repo_size(repo)
                writer.writerow([repo.name, size_mb, classification, result])

        logging.info(f"Done. Report is in {csv_filename}")

    except Exception as e:
        logging.error(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
