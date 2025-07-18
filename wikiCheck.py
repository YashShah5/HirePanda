import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import os
from dotenv import load_dotenv
import urllib3

# Disable warnings for self-signed certs (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load GitHub token from .env
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("GITHUB_TOKEN not found in .env file.")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}"
}

def check_for_attachments(wiki_pages_url):
    try:
        resp = requests.get(wiki_pages_url, headers=HEADERS, verify=False)
        if resp.status_code != 200:
            print(f"[!] Failed to fetch {wiki_pages_url}: HTTP {resp.status_code}")
            return False

        soup = BeautifulSoup(resp.text, 'html.parser')
        page_links = soup.select('a[href*="/wiki/"]')

        for link in page_links:
            href = link.get('href')
            if not href:
                continue

            full_page_url = urljoin(wiki_pages_url, href)
            page_resp = requests.get(full_page_url, headers=HEADERS, verify=False)
            if page_resp.status_code != 200:
                continue

            page_soup = BeautifulSoup(page_resp.text, 'html.parser')
            attachments = page_soup.select(
                'img[src*="/wiki-attachment/"], a[href*="/wiki-attachment/"]'
            )

            if attachments:
                return True

        return False
    except Exception as e:
        print(f"[!] Error checking {wiki_pages_url}: {e}")
        return False

def main(csv_path):
    results = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue

            base_url = row[0].strip()
            wiki_pages_url = base_url.rstrip('/') + "/wiki/_pages"
            print(f"🔍 Checking: {wiki_pages_url}")

            has_attachments = check_for_attachments(wiki_pages_url)

            results.append({
                'wiki_url': base_url,
                'has_attachments': has_attachments
            })

    # Write output to CSV
    with open('wiki_attachment_results.csv', 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=['wiki_url', 'has_attachments'])
        writer.writeheader()
        writer.writerows(results)

    print("✅ Finished. Results saved to 'wiki_attachment_results.csv'.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_wiki_attachments.py <input_csv_file>")
    else:
        main(sys.argv[1])
