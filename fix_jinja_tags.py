#!/usr/bin/env python3
"""
Fix the double-escaped Jinja2 template tags
"""
import os
from pathlib import Path

ADMIN_DIR = Path('private/admin')

def fix_jinja_escaping(filepath):
    """Fix double-escaped Jinja2 tags"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the double escaping
    fixed = content.replace('{%%', '{%').replace('%%}', '%}')
    
    if fixed != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
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
        if fix_jinja_escaping(str(filepath)):
            print(f"✓ Fixed {filepath.name}")
            fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
