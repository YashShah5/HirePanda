import requests
import pandas as pd
import os

# Set your GitHub token here
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"

# Input and output files
INPUT_FILE = "repo_links.csv"
OUTPUT_FILE = "repo_links_with_status.csv"

# Dynamic and static clues
DYNAMIC_CLUES = ['package.json', 'next.config.js', 'gatsby-config.js', 'webpack.config.js', 'nuxt.config.js']
STATIC_CLUES = ['_config.yml', 'index.html']

# Helper to extract API URL from the repo URL
def get_api_url(repo_url):
    parts = repo_url.strip().split('/')
    owner = parts[-2]
    repo = parts[-1]
    return f"https://github-test.qualcomm.com/api/v3/repos/{owner}/{repo}/contents"

# Recursive function to get **all** files in the repo
def get_all_files(api_url, headers, all_files=[]):
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        contents = response.json()
        for item in contents:
            if item['type'] == 'file':
                all_files.append(item['name'])
            elif item['type'] == 'dir':
                get_all_files(item['url'], headers, all_files)
    else:
        print(f"Error fetching {api_url}: {response.status_code} - {response.text}")
    return all_files

# Analyze repo based on files found
def analyze_repo_files(files):
    dynamic_found = any(clue in files for clue in DYNAMIC_CLUES)
    static_found = any(clue in files for clue in STATIC_CLUES)

    if dynamic_found:
        return "Dynamic"
    elif static_found:
        return "Static"
    else:
        return "Unknown"

def main():
    df = pd.read_csv(INPUT_FILE)
    statuses = []

    for index, row in df.iterrows():
        repo_url = row['url']
        api_url = get_api_url(repo_url)

        print(f"\nAnalyzing repo: {repo_url}")
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        # Recursively gather all files
        all_files = get_all_files(api_url, headers, [])

        # Analyze and record status
        status = analyze_repo_files(all_files)
        print(f"Status: {status}")

        statuses.append(status)

    # Save results to a new CSV
    df['status'] = statuses
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Analysis complete. Results saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
