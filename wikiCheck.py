import os
import subprocess
import shutil
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
USERNAME = os.getenv("GIT_USERNAME")
TOKEN = os.getenv("GIT_TOKEN")

# Config
INPUT_CSV = 'input.csv'
OUTPUT_CSV = 'wiki_git_attachment_results.csv'
TMP_DIR = 'tmp_wiki_clones'

# File types that count as attachments
ATTACHMENT_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.zip', '.pdf', '.pptx', '.docx'}

def has_attachments(path):
    for root, _, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ATTACHMENT_EXTS:
                return True
            # Check markdown/text files for embedded attachments
            if ext in ['.md', '.markdown', '.txt']:
                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    if 'wiki-attachment/' in content:
                        return True
    return False

def clone_and_check(base_url):
    try:
        # Format clone URL with credentials
        if not base_url.endswith('.wiki.git'):
            base_url += '.wiki.git'
        if USERNAME and TOKEN:
            base_url = base_url.replace("https://", f"https://{USERNAME}:{TOKEN}@")

        repo_name = base_url.strip().split('/')[-1].replace('.wiki.git', '')
        clone_path = os.path.join(TMP_DIR, repo_name)

        subprocess.run(['git', 'clone', '--quiet', base_url, clone_path], check=True)
        return has_attachments(clone_path)
    except subprocess.CalledProcessError:
        print(f"[!] Failed to clone: {base_url}")
        return None
    finally:
        if os.path.exists(clone_path):
            shutil.rmtree(clone_path)

def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    results = []

    with open(INPUT_CSV, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue
            base_url = row[0].strip()
            print(f"🔍 Checking: {base_url}")
            result = clone_and_check(base_url)
            results.append({
                'repo_url': base_url,
                'has_attachments': result if result is not None else 'clone_failed'
            })

    with open(OUTPUT_CSV, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=['repo_url', 'has_attachments'])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Done! Results saved to '{OUTPUT_CSV}'")

if __name__ == '__main__':
    main()
