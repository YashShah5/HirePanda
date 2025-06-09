#!/usr/bin/env python3

import os
import csv
import logging
from typing import Tuple
from github import Github, Auth, BadCredentialsException, Organization, Repository
from dotenv import load_dotenv  # Add this import

# Load the .env file to set environment variables
load_dotenv()  # Add this line

# Environment variables (loaded from .env file)
GHES_BASE_URL: str = os.getenv('GHES_BASE_URL', '')
GHES_DEFAULT_ORG: str = os.getenv('GHES_ORG', '')
GHES_TOKEN: str = os.getenv('GHES_TOKEN', '')

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_ghes_auth() -> Github:
    """
    Validates GHES authentication and returns the authenticated GitHub instance.
    """
    try:
        auth: Auth.Token = Auth.Token(GHES_TOKEN)
        g: Github = Github(base_url=GHES_BASE_URL, auth=auth)
        org: Organization.Organization = g.get_organization(GHES_DEFAULT_ORG)
        logging.info(f"Authenticated with GHES. Organization: {org.login}")
        return g
    except BadCredentialsException:
        raise ValueError("Invalid GHES credentials. Please check your token and organization name.")
    except Exception as e:
        raise ValueError(f"Error authenticating with GHES: {e}")


def check_repo_size(repo: Repository.Repository) -> Tuple[float, str, str]:
    """
    Checks the repository size and classifies it.
    Returns repo size (MB), classification, and preflight check result.
    """
    try:
        size_kb: int = repo.size
        size_mb: float = size_kb / 1024
        size_gb: float = size_mb / 1024

        if size_gb < 10:
            classification: str = 'Simple'
        elif 10 <= size_gb <= 20:
            classification = 'Medium'
        else:
            classification = 'Complex'

        logging.info(f"Repo: {repo.name}, Size: {size_gb:.2f} GB, Classification: {classification}")

        return round(size_mb, 2), classification, 'Pass'
    except Exception as e:
        logging.error(f"Error checking size for repository {repo.name}: {e}")
        return 0.0, 'Unknown', 'Fail'


def main() -> bool:
    try:
        ghes: Github = validate_ghes_auth()
        org: Organization.Organization = ghes.get_organization(GHES_DEFAULT_ORG)
        repos = org.get_repos()

        csv_report_filename: str = f"repo_size_report_{GHES_DEFAULT_ORG}.csv"
        with open(csv_report_filename, 'w', newline='') as csvfile:
            writer: csv.writer = csv.writer(csvfile)
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
