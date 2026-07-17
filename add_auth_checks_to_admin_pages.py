#!/usr/bin/env python3
"""
Add authorization checks to all admin pages to prevent non-admin users from accessing them.
"""

import os
import re
from pathlib import Path

ADMIN_DIR = Path("private/admin")
AUTH_CHECK_SCRIPT = '''<script>
// Authorization Check - Prevent non-admin users from accessing admin pages
if (localStorage.getItem('is_admin') !== 'true') {
    window.stop(); // Stop page loading immediately
    document.body.innerHTML = '<div style="padding: 50px; text-align: center;"><h1>Access Denied</h1><p>You do not have permission to access this page.</p><a href="/user/dashboard">Return to Dashboard</a></div>';
    setTimeout(() => window.location.href = '/user/dashboard', 500);
    throw new Error('Unauthorized');
}
</script>
'''

def add_auth_check_to_file(file_path):
    """Add auth check to a single HTML file if it doesn't already have one."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if auth check already exists
    if 'Authorization Check - Prevent non-admin' in content:
        print(f"  ✓ {file_path.name} - already has auth check")
        return False
    
    # Find the insertion point - right after <body> tag
    body_pattern = r'(<body[^>]*>)'
    match = re.search(body_pattern, content)
    
    if not match:
        print(f"  ✗ {file_path.name} - could not find <body> tag")
        return False
    
    # Insert the auth check right after the <body> tag
    insertion_point = match.end()
    new_content = content[:insertion_point] + '\n    ' + AUTH_CHECK_SCRIPT + '\n' + content[insertion_point:]
    
    # Write back the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✓ {file_path.name} - auth check added")
    return True

def main():
    """Process all admin HTML files."""
    if not ADMIN_DIR.exists():
        print(f"Error: {ADMIN_DIR} does not exist")
        return
    
    print(f"Adding authorization checks to admin pages in {ADMIN_DIR}...\n")
    
    admin_files = sorted([
        f for f in ADMIN_DIR.glob("admin_*.html") 
        if not f.name.endswith('.backup')
    ])
    
    if not admin_files:
        print("No admin files found!")
        return
    
    print(f"Found {len(admin_files)} admin files to process:\n")
    
    updated = 0
    for file_path in admin_files:
        if add_auth_check_to_file(file_path):
            updated += 1
    
    print(f"\n✅ Complete! Updated {updated}/{len(admin_files)} files")

if __name__ == "__main__":
    main()
