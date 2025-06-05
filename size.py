#!/usr/bin/env python3

import os
import csv
import logging
from github import Github, Auth, BadCredentialsException

# Constants for environment variables
GHES_BASE_URL = os.getenv('GHES_BASE_URL')
GHES_DEFAULT_ORG = os.getenv('GHES_ORG')
GHES_TOKEN = os.getenv('GHES_TOKEN')

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_ghes_auth():
    """
    Validates GHES authentication and returns the authenticated GitHub instance.
    """
    try:
        auth = Auth.Token(GHES_TOKEN)
        g = Github(base_url=GHES_BASE_URL, auth=auth)
        org = g.get_organization(GHES_DEFAULT_ORG)  # Check if organization exists
        logging.info(f"Authenticated with GHES. Organization: {org.login}")
        return g
    except BadCredentialsException:
        raise ValueError("Invalid GHES credentials. Please check your token and organization name.")
    except Exception as e:
        raise ValueError(f"Error authenticating with GHES: {e}")


def check_repo_size(repo):
    """
    Checks the repository size and classifies it.
    Returns repo size (MB), classification, and preflight check result.
    """
    try:
        # GitHub API gives size in KB
        size_kb = repo.size
        size_mb = size_kb / 1024  # Convert to MB
        size_gb = size_mb / 1024  # Convert to GB

        # Classification logic
        if size_gb < 10:
            classification = 'Simple'
        elif 10 <= size_gb <= 20:
            classification = 'Medium'
        else:
            classification = 'Complex'

        logging.info(f"Repo: {repo.name}, Size: {size_gb:.2f} GB, Classification: {classification}")

        return round(size_mb, 2), classification, 'Pass'
    except Exception as e:
        logging.error(f"Error checking size for repository {repo.name}: {e}")
        return 0, 'Unknown', 'Fail'


def main():
    try:
        # Authenticate and get repos
        ghes = validate_ghes_auth()
        org = ghes.get_organization(GHES_DEFAULT_ORG)
        repos = org.get_repos()

        # Prepare CSV report
        csv_report_filename = f"repo_size_report_{GHES_DEFAULT_ORG}.csv"
        with open(csv_report_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Repository", "Size (MB)", "Classification", "Preflight Check Result"])

            for repo in repos:
                size_mb, classification, check_result = check_repo_size(repo)
                writer.writerow([repo.name, size_mb, classification, check_result])

        logging.info(f"Repo size check completed. Report generated: {csv_report_filename}")
        return True

    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return False
    except Exception as e:
        logging.error(f"Overall process encountered an error: {e}")
        return False


if __name__ == "__main__":
    main()
