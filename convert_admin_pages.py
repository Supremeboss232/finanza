#!/usr/bin/env python3
"""
Convert all admin HTML pages to extend base.html with relative links
"""
import os
import re
from pathlib import Path

ADMIN_DIR = Path('private/admin')

# Mapping of files to their nav_active values
NAV_ACTIVE_MAP = {
    'admin_reports.html': 'Reports',
    'admin_content.html': 'Content',
    'admin_profile.html': 'Profile',
    'admin_security_center.html': 'Security',
    'admin_logs.html': 'Security',
    'admin_activity_monitor.html': 'Security',
    'admin_notifications.html': 'Security',
    'admin_roles.html': 'Roles',
    'admin_manage_admins.html': 'Roles',
    'admin_system_settings.html': 'Settings',
    'admin_email_settings.html': 'Settings',
    'admin_payment_settings.html': 'Settings',
    'admin_maintenance_mode.html': 'Settings',
    'admin_kyc_list.html': 'KYC',
    'admin_kyc_review.html': 'KYC',
    'admin_kyc_details.html': 'KYC',
    'admin_kyc_settings.html': 'KYC',
    'admin_pending_deposits.html': 'Transactions',
    'admin_pending_withdrawals.html': 'Transactions',
    'admin_submissions.html': 'Transactions',
    'admin_fund_user.html': 'Transactions',
    'admin_adjust_balance.html': 'Transactions',
    'admin_transaction_details.html': 'Transactions',
    'admin_user_details.html': 'Users',
    'admin_user_accounts.html': 'Users',
    'admin_user_assets.html': 'Users',
    'admin_user_investments.html': 'Users',
    'admin_user_loans.html': 'Users',
    'admin_user_cards.html': 'Users',
    'admin_user_wallets.html': 'Users',
}

def extract_page_title(filename):
    """Extract a nice page title from filename"""
    name = filename.replace('admin_', '').replace('.html', '')
    # Convert underscores to spaces and title case
    title = name.replace('_', ' ').title()
    return title

def convert_admin_page(filepath):
    """Convert a single admin page to extend base.html"""
    filename = os.path.basename(filepath)
    
    if filename in ('base.html', 'sidebar_nav.html'):
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if already converted
    if '{% extends "base.html" %}' in content:
        print(f"✓ {filename} - already converted")
        return False
    
    # Get nav_active value
    nav_active = NAV_ACTIVE_MAP.get(filename, 'Dashboard')
    page_title = extract_page_title(filename)
    
    # Pattern to match HTML doctype through navbar end
    pattern = r'<!DOCTYPE html>.*?<!-- Navbar End -->\s*'
    
    # Find where to split - after navbar, before page header
    navbar_end = content.find('<!-- Navbar End -->')
    if navbar_end == -1:
        print(f"✗ {filename} - could not find navbar end marker")
        return False
    
    # Find the start
    doctype_start = content.find('<!DOCTYPE html>')
    if doctype_start == -1:
        print(f"✗ {filename} - could not find doctype start")
        return False
    
    # Extract content after navbar
    content_start = navbar_end + len('<!-- Navbar End -->')
    remaining_content = content[content_start:].strip()
    
    # Build new content
    new_content = f'''{{%% extends "base.html" %%}}

{{%% block title %%}}{page_title}{{%% endblock %%}}

{{%% set nav_active = '{nav_active}' %%}}

{{%% block content %%}}
{remaining_content}
{{%% endblock %%}}'''
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ {filename} - converted (nav_active: {nav_active})")
    return True

def main():
    """Convert all admin HTML files"""
    if not ADMIN_DIR.exists():
        print(f"Error: {ADMIN_DIR} does not exist")
        return
    
    admin_files = sorted(ADMIN_DIR.glob('admin_*.html'))
    converted_count = 0
    
    for filepath in admin_files:
        if convert_admin_page(str(filepath)):
            converted_count += 1
    
    print(f"\n✓ Converted {converted_count} files")

if __name__ == '__main__':
    main()
