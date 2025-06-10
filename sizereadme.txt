# Repo Size Check Script

This script checks the size of all repositories in a specified GitHub Enterprise organization and classifies them as Simple, Medium, or Complex based on their size. It then outputs a CSV report with the details.

## What it does
- Connects to a GitHub Enterprise Server (GHES) instance using the GitHub API.
- Lists all repositories in the organization.
- For each repository:
  - Gets the size from the GitHub API.
  - Converts the size to MB and GB.
  - Classifies it as:
    - Simple: <10GB
    - Medium: 10–20GB
    - Complex: >20GB
- Writes the results to a CSV report with these columns:
  - Repository
  - Size (MB)
  - Classification
  - Preflight Check Result

## Setup

1. Clone this repository (or copy the script file):
    ```bash
    git clone <your-repo-url>
    cd <your-repo-dir>
    ```

2. Install required packages (if not already):
    ```bash
    pip install PyGithub python-dotenv
    ```

3. Create a `.env` file in the same directory as the script:
    ```
    GHES_BASE_URL=https://github-test.qualcomm.com/api/v3
    GHES_ORG=customcpu
    GHES_TOKEN=ghp_XXXXXXXXXXXXXXXXXXXXX
    ```

    Make sure there are no extra spaces after the equal signs.

## Running the script

```bash
python repo_size.py
