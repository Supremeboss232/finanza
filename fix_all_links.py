#!/usr/bin/env python3
"""
Comprehensive fix for broken links in all HTML files:
1. Fix relative CSS/JS/lib paths
2. Update navigation links to correct routes
3. Fix static file references
"""

import os
import re
from pathlib import Path

def fix_html_file(file_path):
    """Fix a single HTML file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. Fix CSS paths
    content = re.sub(r'href=["\'](?:\.\.\/)*css/', 'href="/static/css/', content)
    
    # 2. Fix JS paths
    content = re.sub(r'src=["\'](?:\.\.\/)*js/', 'src="/static/js/', content)
    
    # 3. Fix lib paths
    content = re.sub(r'(?:href|src)=["\'](?:\.\.\/)*lib/', 'href="/static/lib/', content)
    
    # 4. Fix admin-utils and auth-helper to use /admin_static/
    content = content.replace('src="/static/js/admin-utils.js"', 'src="/admin_static/js/admin-utils.js"')
    content = content.replace('src="/static/js/auth-helper.js"', 'src="/admin_static/js/auth-helper.js"')
    
    # 5. Fix remaining relative paths
    content = re.sub(r'(src|href)=["\']\.\.\/\.\.\/([^"\']+)', r'\1="/static/\2', content)
    
    # 6. Fix img paths
    content = re.sub(r'src=["\'](?:\.\.\/)*img/', 'src="/static/img/', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Fix all HTML files in private folder
private_dir = Path("private")
fixed_count = 0
total_count = 0

for html_file in private_dir.rglob("*.html"):
    total_count += 1
    if fix_html_file(html_file):
        fixed_count += 1
        print(f"Fixed: {html_file.relative_to('.')}")
    else:
        print(f"Skipped: {html_file.relative_to('.')}")

print(f"\nSummary: Fixed {fixed_count}/{total_count} files")
