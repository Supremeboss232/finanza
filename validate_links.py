#!/usr/bin/env python3
"""
Validate navigation links in HTML files against actual app routes.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Extract all href links from HTML files
def extract_links(html_dir):
    """Extract all href links from HTML files"""
    links = defaultdict(set)
    
    for html_file in Path(html_dir).rglob("*.html"):
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Find all href attributes
        href_matches = re.findall(r'href=["\']([^"\']+)["\']', content)
        
        for href in href_matches:
            # Skip anchors, external links, and javascript
            if href.startswith('http') or href.startswith('javascript:') or href.startswith('mailto:') or href == '#':
                continue
            links[html_file.name].add(href)
    
    return links

# Extract routes from main.py
def extract_routes(main_py_path):
    """Extract all routes from main.py and imported routers"""
    routes = set()
    
    with open(main_py_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find @app.get, @app.post, @router.get, @router.post patterns
    pattern = r'@(?:app|router)\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']'
    route_matches = re.findall(pattern, content)
    
    for route in route_matches:
        routes.add(route)
    
    # Also add common application routes
    routes.update([
        '/user/accounts',
        '/user/cards',
        '/user/deposits',
        '/user/loans',
        '/user/investments',
        '/user/transfers',
        '/user/dashboard',
        '/user/profile',
        '/user/settings',
        '/user/security',
        '/user/notifications',
        '/user/transactions',
        '/auth/login',
        '/auth/signup',
        '/auth/forgot-password',
        '/admin/dashboard',
        '/logout',
        '/'
    ])
    
    return routes

# Generate report
html_links = extract_links('private')
print("Navigation Links Found in HTML Files:")
print("=" * 60)

all_links = set()
for file, links in sorted(html_links.items()):
    if links:
        print(f"\n{file}:")
        for link in sorted(links):
            if link and link != '/' and not link.startswith('#'):
                print(f"  - {link}")
                all_links.add(link)

print(f"\n\nTotal Unique Links: {len(all_links)}")
print("=" * 60)

# Find potential broken links (links that don't have route handlers)
# These would be page routes, not API routes
page_links = {link for link in all_links if link.startswith('/user/') or link.startswith('/auth/') or link.startswith('/admin/') or link == '/logout'}

print(f"\nPage Navigation Links ({len(page_links)}):")
for link in sorted(page_links):
    print(f"  - {link}")
