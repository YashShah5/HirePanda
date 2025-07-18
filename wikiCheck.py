import os
import subprocess
import shutil
import csv

# CONFIG
INPUT_CSV = 'input.csv'  # list of GitHub repo URLs (one per line)
OUTPUT_CSV = 'wiki_git_attachment_results.csv'
TMP_DIR = 'tmp_wiki_clones'

# File extensions considered "attachments"
ATTACHMENT_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.zip', '.pdf', '.pptx', '.docx'}

def has_attachments(path):
    for root, _, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ATTACHMENT_EXTS:
                return True
            # Also check if markdown links to /wiki-attachment/
            if ext in ['.md', '.markdown', '.txt']:
                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    if 'wiki-attachment/' in content:
                        return True
    return False

def clone_and_check(url):
    try:
        if not url.endswith('.wiki.git'):
            url += '.wiki.git'

        repo_name = url.strip().split('/')[-1].replace('.wiki.git', '')
        clone_path = os.path.join(TMP_DIR, repo_name)

        subprocess.run(['git', 'clone', '--quiet', url, clone_path], check=True)
        return has_attachments(clone_path)
    except subprocess.CalledProcessError:
        print(f"[!] Failed to clone: {url}")
        return None
    finally:
        # Clean up after each repo
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
            print(f"🔍 Cloning: {base_url}")
            result = clone_and_check(base_url)
            results.append({
                'repo_url': base_url,
                'has_attachments': result if result is not None else 'clone_failed'
            })

    with open(OUTPUT_CSV, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=['repo_url', 'has_attachments'])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Done! Results saved to: {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
