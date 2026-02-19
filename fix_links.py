#!/usr/bin/env python3
"""
Convert all absolute admin links to relative links
"""
import os
import re
from pathlib import Path

ADMIN_DIR = Path('private/admin')

def fix_absolute_links(filepath):
    """Convert absolute /admin/ links to relative links"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace /admin/ links with just the filename
    # This regex handles href="/admin/admin_*.html" and similar patterns
    content = re.sub(r'href=["\']?/admin/([a-z_]+\.html)["\']?', r'href="\1"', content)
    content = re.sub(r'href=["\']?/admin/([a-z_]+)["\']?', r'href="\1.html"', content)
    
    # Also handle action="/admin/ patterns for forms
    content = re.sub(r'action=["\']?/admin/([a-z_]+\.html)["\']?', r'action="\1"', content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all admin HTML files"""
    if not ADMIN_DIR.exists():
        print(f"Error: {ADMIN_DIR} does not exist")
        return
    
    admin_files = sorted(ADMIN_DIR.glob('admin_*.html'))
    fixed_count = 0
    
    for filepath in admin_files:
        if fix_absolute_links(str(filepath)):
            print(f"✓ Fixed links in {filepath.name}")
            fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
