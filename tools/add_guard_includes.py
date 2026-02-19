"""Add include of guard scripts into private/user and private/admin HTML files.
Inserts the appropriate <script src="/js/...-guard.js"></script> before closing </body>
Backs up each file to filename.bak before modifying.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / 'private' / 'user'
ADMIN_DIR = ROOT / 'private' / 'admin'

USER_SNIPPET = '<script src="/js/user-guard.js"></script>'
ADMIN_SNIPPET = '<script src="/js/admin-guard.js"></script>'

def process_dir(directory: Path, snippet: str):
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return
    for p in directory.glob('**/*.html'):
        try:
            text = p.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Failed reading {p}: {e}")
            continue
        if snippet in text:
            print(f"Already has snippet: {p}")
            continue
        # find closing </body>
        idx = text.rfind('</body>')
        if idx == -1:
            print(f"No </body> tag found in {p}, skipping")
            continue
        backup = p.with_suffix(p.suffix + '.bak')
        backup.write_text(text, encoding='utf-8')
        new_text = text[:idx] + snippet + '\n' + text[idx:]
        p.write_text(new_text, encoding='utf-8')
        print(f"Inserted snippet into {p}")

if __name__ == '__main__':
    process_dir(USER_DIR, USER_SNIPPET)
    process_dir(ADMIN_DIR, ADMIN_SNIPPET)
    print('Done.')
