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


def get_all_wiki_pages(base_wiki_url):
    """
    Returns a list of full URLs to all subpages in the wiki.
    """
    try:
        response = requests.get(base_wiki_url, headers=HEADERS, timeout=10, verify=VERIFY_SSL)
        if response.status_code != 200:
            print(f"❌ Failed to fetch {base_wiki_url} (status {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.select('div#wiki-rightbar a[href^="/"]')
        page_urls = [urljoin(base_wiki_url, link['href']) for link in links if link['href']]
        return list(set(page_urls))  # de-duplicate

    except Exception as e:
        print(f"⚠️ Error fetching subpages for {base_wiki_url}: {e}")
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

    for url in df.iloc[:, 0]:  # First column = wiki repo URL
        orgname, reponame = extract_org_repo(url)
        if not reponame:
            print(f"⚠️ Skipping invalid repo URL: {url}")
            continue

        wiki_home = url.rstrip('/') + '/wiki'
        print(f"\n🔍 Scanning: {orgname}/{reponame}")

        all_pages = get_all_wiki_pages(wiki_home)
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
