import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found in .env file.")

# Constants
INPUT_CSV = 'input.csv'
OUTPUT_CSV = 'output_with_attachments.csv'
DELAY_BETWEEN_REQUESTS = 0.5
VERIFY_SSL = False  # Set False for GitHub Enterprise self-signed certs

# Headers with GitHub token
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "text/html"  # Make sure we get HTML not JSON
}

# Turn off SSL warnings (internal GHEs often have self-signed certs)
requests.packages.urllib3.disable_warnings()


def extract_orgname(url):
    return urlparse(url).path.strip('/')


def check_for_attachments(wiki_url):
    try:
        response = requests.get(wiki_url, headers=HEADERS, timeout=10, verify=VERIFY_SSL)
        if response.status_code != 200:
            print(f"❌ Failed to fetch {wiki_url} (status {response.status_code})")
            return False, None

        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup.find_all(['a', 'img'], href=True):
            if '/wiki/uploads/' in tag['href']:
                full_link = urljoin(wiki_url, tag['href'])
                return True, full_link

        return False, None
    except Exception as e:
        print(f"⚠️ Error checking {wiki_url}: {e}")
        return False, None


def main():
    df = pd.read_csv(INPUT_CSV)
    results = []

    for url in df.iloc[:, 0]:  # First column = wiki URL
        orgname = extract_orgname(url)
        wiki_page = url.rstrip('/') + '/wiki'

        print(f"🔍 Checking wiki for: {orgname}")
        has_attachments, first_link = check_for_attachments(wiki_page)

        results.append({
            "orgname": orgname,
            "wiki_url": url,
            "has_attachments": has_attachments,
            "first_attachment_url": first_link if has_attachments else ''
        })

        time.sleep(DELAY_BETWEEN_REQUESTS)

    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Done! Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
