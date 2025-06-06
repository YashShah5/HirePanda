#!/usr/bin/env python3

import os
import csv
import logging
from typing import Tuple
from github import Github, Auth, BadCredentialsException, Organization, Repository

# Load environment variables (replace with your actual values in the .env file)
GHES_BASE_URL: str = os.getenv('GHES_BASE_URL', '')
GHES_DEFAULT_ORG: str = os.getenv('GHES_ORG', '')
GHES_TOKEN: str = os.getenv('GHES_TOKEN', '')

# Set up basic logging so we can see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_ghes_auth() -> Github:
    """
    Validates GHES authentication and returns the authenticated GitHub instance.
    If something goes wrong, it raises a ValueError.
    """
    try:
        # Create the GitHub API client with the token we got from the .env file
        auth: Auth.Token = Auth.Token(GHES_TOKEN)
        g: Github = Github(base_url=GHES_BASE_URL, auth=auth)

        # Check if we can access the organization to confirm the credentials work
        org: Organization.Organization = g.get_organization(GHES_DEFAULT_ORG)
        logging.info(f"Authenticated with GHES. Organization: {org.login}")

        # Return the authenticated GitHub object so we can reuse it later
        return g
    except BadCredentialsException:
        # If the token is bad, let the user know
        raise ValueError("Invalid GHES credentials. Please check your token and organization name.")
    except Exception as e:
        # Any other error during auth
        raise ValueError(f"Error authenticating with GHES: {e}")


def check_repo_size(repo: Repository.Repository) -> Tuple[float, str, str]:
    """
    For a given repository, calculate its size and classify it.
    Returns: (size in MB, classification label, pass/fail result)
    """
    try:
        # GitHub API gives repo size in KB, so convert to MB and GB
        size_kb: int = repo.size
        size_mb: float = size_kb / 1024
        size_gb: float = size_mb / 1024

        # Determine classification based on size
        if size_gb < 10:
            classification: str = 'Simple'
        elif 10 <= size_gb <= 20:
            classification = 'Medium'
        else:
            classification = 'Complex'

        # Log what we found
        logging.info(f"Repo: {repo.name}, Size: {size_gb:.2f} GB, Classification: {classification}")

        # Return the final results
        return round(size_mb, 2), classification, 'Pass'
    except Exception as e:
        # If something goes wrong, log it and mark the check as failed
        logging.error(f"Error checking size for repository {repo.name}: {e}")
        return 0.0, 'Unknown', 'Fail'


def main() -> bool:
    """
    Main function that authenticates, loops through repos, and writes the report.
    Returns True if everything worked, False otherwise.
    """
    try:
        # Authenticate with GHES and get our organization
        ghes: Github = validate_ghes_auth()
        org: Organization.Organization = ghes.get_organization(GHES_DEFAULT_ORG)
        repos = org.get_repos()  # Get all repositories in the organization

        # Open (or create) a CSV file to save the report
        csv_report_filename: str = f"repo_size_report_{GHES_DEFAULT_ORG}.csv"
        with open(csv_report_filename, 'w', newline='') as csvfile:
            writer: csv.writer = csv.writer(csvfile)
            # Write the CSV header
            writer.writerow(["Repository", "Size (MB)", "Classification", "Preflight Check Result"])

            # Loop through each repo and get its size/classification
            for repo in repos:
                size_mb, classification, check_result = check_repo_size(repo)
                # Write the results to the CSV file
                writer.writerow([repo.name, size_mb, classification, check_result])

        # Let the user know we’re done!
        logging.info(f"Repo size check completed. Report generated: {csv_report_filename}")
        return True

    except ValueError as e:
        # If we failed during authentication or some other validation
        logging.error(f"Validation error: {e}")
        return False
    except Exception as e:
        # Catch any other unexpected error
        logging.error(f"Overall process encountered an error: {e}")
        return False


if __name__ == "__main__":
    # Run the main function if this script is executed directly
    main()
