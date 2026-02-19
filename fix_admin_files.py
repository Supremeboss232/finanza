#!/usr/bin/env python3
"""
Fix admin HTML files:
1. Replace relative CSS/JS paths with absolute /static/ paths
2. Fix navigation links
3. Ensure API endpoints are correct
"""

import os
import re
from pathlib import Path

admin_dir = Path("private/admin")
files_to_fix = list(admin_dir.glob("*.html"))

fixes_made = 0

for html_file in files_to_fix:
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix relative CSS paths: ../../css/ -> /static/css/
    content = re.sub(r'href=["\'](?:\.\.\/)*css/', 'href="/static/css/', content)
    
    # Fix relative JS paths: ../../js/ -> /static/js/ or /admin_static/js/
    content = re.sub(r'src=["\'](?:\.\.\/)*js/', 'src="/static/js/', content)
    
    # Fix relative lib paths: ../../lib/ -> /static/lib/
    content = re.sub(r'(?:href|src)=["\'](?:\.\.\/)*lib/', 'href="/static/lib/', content)
    
    # Fix admin-utils.js path - should be /admin_static/js/admin-utils.js
    content = content.replace('src="/static/js/admin-utils.js"', 'src="/admin_static/js/admin-utils.js"')
    
    # Fix any remaining relative paths in script/link tags
    content = re.sub(r'(src|href)=["\']\.\.\/\.\.\/([^"\']+)', r'\1="/static/\2', content)
    
    if content != original_content:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        fixes_made += 1
        print(f"✅ Fixed: {html_file.name}")
    else:
        print(f"⏭️  Skipped: {html_file.name} (no changes needed)")

print(f"\n📊 Summary: Fixed {fixes_made}/{len(files_to_fix)} files")
