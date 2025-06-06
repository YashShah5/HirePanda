#!/usr/bin/env python3

import os
import csv
import logging
from github import Github, Auth, BadCredentialsException
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get environment variables
GHES_BASE_URL = os.getenv('GHES_BASE_URL', '')
GHES_ORG = os.getenv('GHES_ORG', '')
GHES_TOKEN = os.getenv('GHES_TOKEN', '')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        # Authenticate with GHES
        auth = Auth.Token(GHES_TOKEN)
        g = Github(base_url=GHES_BASE_URL, auth=auth)

        # Check if the org exists
        org = g.get_organization(GHES_ORG)
        repos = org.get_repos()

        # Create a CSV file
        with open('test_repo_sizes.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Repository", "Size (KB)"])

            # Loop through all repos and write to CSV
            for repo in repos:
                writer.writerow([repo.name, repo.size])

        logging.info("Test CSV file created: test_repo_sizes.csv")
    
    except BadCredentialsException:
        logging.error("Invalid credentials. Check your .env file.")
    except Exception as e:
        logging.error(f"Something went wrong: {e}")

if __name__ == "__main__":
    main()
