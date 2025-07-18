import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

# Load token from .env
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found in .env file.")

# Constants
INPUT_CSV = 'input.csv'
OUTPUT_CSV = 'output_with_attachments.csv'
DELAY_BETWEEN_REQUESTS = 0.5
VERIFY_SSL = False

# Auth headers
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "text/html"
}

# Turn off SSL warnings (for GitHub Enterprise self-signed certs)
requests.packages.urllib3.disable_warnings()


def extract_org_repo(url):
    parts = urlparse(url).path.strip('/').split('/')
    return parts[0], parts[1] if len(parts) > 1 else None


def get_all_wiki_pages(wiki_home_url):
    """
    Gets all wiki subpage links from the /wiki/_pages index.
    """
    try:
        pages_url = urljoin(wiki_home_url, '_pages')  # ensures proper trailing slash
        response = requests.get(pages_url, headers=HEADERS, timeout=10, verify=VERIFY_SSL)
        if response.status_code != 200:
            print(f"❌ Failed to fetch {pages_url} (status {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        page_urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/wiki/' in href and not href.endswith('/_pages'):
                full_url = urljoin(pages_url, href)
                page_urls.append(full_url)

        return list(set(page_urls))  # deduplicated list

    except Exception as e:
        print(f"⚠️ Error fetching wiki pages from {wiki_home_url}: {e}")
        return []


def get_attachments_from_page(page_url):
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10, verify=VERIFY_SSL)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        attachments = []

        for tag in soup.find_all(['a', 'img'], href=True):
            if '/wiki/uploads/' in tag['href']:
                attachments.append(urljoin(page_url, tag['href']))

        return attachments

    except Exception as e:
        print(f"⚠️ Error checking {page_url}: {e}")
        return []


def main():
    df = pd.read_csv(INPUT_CSV)
    results = []

    for url in df.iloc[:, 0]:  # Assumes wiki repo URL in first column
        orgname, reponame = extract_org_repo(url)
        if not reponame:
            print(f"⚠️ Skipping invalid repo URL: {url}")
            continue

        wiki_home = url.rstrip('/') + '/wiki/'
        print(f"\n🔍 Scanning: {orgname}/{reponame}")

        all_pages = get_all_wiki_pages(wiki_home)

        # Always include the homepage too
        if wiki_home not in all_pages:
            all_pages.insert(0, wiki_home)

        all_attachments = []
        for page in all_pages:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            attachments = get_attachments_from_page(page)
            all_attachments.extend(attachments)

        unique_attachments = list(set(all_attachments))

        results.append({
            "orgname": orgname,
            "wiki_url": url,
            "has_attachments": bool(unique_attachments),
            "attachment_urls": ", ".join(unique_attachments)
        })

        time.sleep(DELAY_BETWEEN_REQUESTS)

    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Done! Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
