import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

GITHUB_TOKEN = 'your_token_here'
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}'
}

def check_for_attachments(wiki_base_url):
    try:
        # Fetch the _pages listing
        response = requests.get(wiki_base_url, headers=HEADERS, verify=False)
        if response.status_code != 200:
            print(f"[!] Failed to fetch {wiki_base_url}: {response.status_code}")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        page_links = soup.select('a[href*="/wiki/"]')

        for link in page_links:
            href = link.get('href')
            if not href:
                continue
            full_page_url = urljoin(wiki_base_url, href)
            page_resp = requests.get(full_page_url, headers=HEADERS, verify=False)

            if page_resp.status_code != 200:
                continue

            page_soup = BeautifulSoup(page_resp.text, 'html.parser')
            # Look for images or files from wiki-attachment path
            attachments = page_soup.select('img[src*="/wiki-attachment/"], a[href*="/wiki-attachment/"]')

            if attachments:
                return True
        return False
    except Exception as e:
        print(f"Error checking {wiki_base_url}: {e}")
        return False

def main(csv_path):
    results = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue
            wiki_url = row[0].strip()
            print(f"Checking {wiki_url} ...")
            has_attachments = check_for_attachments(wiki_url)
            results.append({
                'wiki_url': wiki_url,
                'has_attachments': has_attachments
            })

    # Output to a results file
    with open('wiki_attachment_results.csv', 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=['wiki_url', 'has_attachments'])
        writer.writeheader()
        writer.writerows(results)

    print("✅ Done. Results saved to 'wiki_attachment_results.csv'.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_wiki_attachments.py <input_csv_file>")
    else:
        main(sys.argv[1])
