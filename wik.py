import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

# Load token
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("❌ GITHUB_TOKEN not found in .env")

# Config
INPUT_CSV = 'input.csv'
OUTPUT_CSV = 'output_with_api_and_attachments.csv'
DELAY_BETWEEN_REQUESTS = 0.5
VERIFY_SSL = False  # For self-signed GHE certs

API_BASE = "https://github-test.qualcomm.com/api/v3"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

requests.packages.urllib3.disable_warnings()


def extract_org_repo(url):
    parts = urlparse(url).path.strip('/').split('/')
    return parts[0], parts[1] if len(parts) > 1 else None


def get_has_wiki(org, repo):
    api_url = f"{API_BASE}/repos/{org}/{repo}"
    response = requests.get(api_url, headers=HEADERS, verify=VERIFY_SSL)
    if response.status_code != 200:
        print(f"❌ API error: {org}/{repo} (status {response.status_code})")
        return False
    return response.json().get('has_wiki', False)


def get_all_wiki_pages(wiki_home_url):
    try:
        pages_url = urljoin(wiki_home_url, '_pages')
        response = requests.get(pages_url, headers=HEADERS, timeout=10, verify=VERIFY_SSL)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        page_urls = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/wiki/' in href and not href.endswith('/_pages'):
                page_urls.append(urljoin(pages_url, href))
        return list(set(page_urls))
    except Exception as e:
        print(f"⚠️ Failed to fetch wiki pages from {wiki_home_url}: {e}")
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
        print(f"⚠️ Failed to check attachments in {page_url}: {e}")
        return []


def main():
    df = pd.read_csv(INPUT_CSV)
    results = []

    for url in df.iloc[:, 0]:
        org, repo = extract_org_repo(url)
        if not repo:
            print(f"⚠️ Invalid repo URL: {url}")
            continue

        print(f"\n🔍 Checking {org}/{repo}")
        has_wiki = get_has_wiki(org, repo)
        has_attachments = False
        attachment_urls = []

        if has_wiki:
            wiki_home = f"https://github-test.qualcomm.com/{org}/{repo}/wiki/"
            all_pages = get_all_wiki_pages(wiki_home)
            if wiki_home not in all_pages:
                all_pages.insert(0, wiki_home)

            for page in all_pages:
                time.sleep(DELAY_BETWEEN_REQUESTS)
                attachments = get_attachments_from_page(page)
                if attachments:
                    has_attachments = True
                    attachment_urls.extend(attachments)

        results.append({
            "orgname": org,
            "reponame": repo,
            "wiki_url": url,
            "has_wiki": has_wiki,
            "has_attachments": has_attachments,
            "attachment_urls": ", ".join(list(set(attachment_urls)))
        })

        time.sleep(DELAY_BETWEEN_REQUESTS)

    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Done! Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
