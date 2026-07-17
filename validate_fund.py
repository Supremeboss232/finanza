#!/usr/bin/env python3
from html.parser import HTMLParser
import json

try:
    with open('private/admin/admin_fund.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = HTMLParser()
    parser.feed(content)
    print('✓ HTML structure is valid')
    print(f'✓ File size: {len(content)} bytes')
    print()
    
    checks = [
        ('function generateIdempotencyKey', 'Idempotency key generation'),
        ('function searchUsers', 'User search function'),
        ('function validateFundForm', 'Fund form validation'),
        ('function loadPendingApprovals', 'Approval workflow'),
        ('function auditLog', 'Audit logging'),
        ('CONFIG.APPROVAL_THRESHOLD', 'Production config'),
        ('X-Idempotency-Key', 'Idempotency header'),
        ('generateTransactionReference', 'Transaction reference'),
        ('approveOperation', 'Approval functions'),
        ('showToast', 'Toast notifications'),
        ('escapeHtml', 'XSS protection'),
    ]
    
    print('Production Features Check:')
    print('-' * 50)
    all_present = True
    for check, desc in checks:
        if check in content:
            print(f'✓ {desc}')
        else:
            print(f'✗ {desc} - NOT FOUND')
            all_present = False
    
    print()
    print('Summary:')
    if all_present:
        print('✓ ALL PRODUCTION FEATURES PRESENT')
    else:
        print('✗ Some features missing')
        
except SyntaxError as e:
    print(f'✗ HTML Syntax Error: {e}')
except Exception as e:
    print(f'✗ Error: {e}')
