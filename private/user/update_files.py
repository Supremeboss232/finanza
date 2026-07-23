import re
import os

files = [
    'dashboard.html', 'transactions.html', 'transfers.html', 'cards.html', 
    'account.html', 'loans.html', 'deposits.html'
]

mobile_css = '    <link href="/static/css/mobile.css" rel="stylesheet">'
mobile_nav = '''    <!-- Mobile Bottom Navigation Bar -->
    <div id="mobile-bottom-nav" role="navigation" aria-label="Mobile navigation">
        <a href="/user/dashboard" class="mobile-nav-item" id="mbnav-home">
            <i class="fas fa-home"></i>
            Home
        </a>
        <a href="/user/transfers" class="mobile-nav-item" id="mbnav-transfer">
            <i class="fas fa-exchange-alt"></i>
            Transfer
        </a>
        <a href="/user/cards" class="mobile-nav-item" id="mbnav-cards">
            <i class="fas fa-credit-card"></i>
            Cards
        </a>
        <a href="/user/transactions" class="mobile-nav-item" id="mbnav-txn">
            <i class="fas fa-list-alt"></i>
            Activity
        </a>
        <div class="mobile-nav-item" id="mbnav-more" onclick="toggleMobileMoreMenu()">
            <i class="fas fa-th"></i>
            More
        </div>
    </div>

    <!-- Mobile More Menu -->
    <div id="mobile-more-overlay" onclick="closeMobileMoreMenu()"></div>
    <div id="mobile-more-menu">
        <a href="/user/account" class="mobile-more-item"><i class="fas fa-university"></i>Account</a>
        <a href="/user/loans" class="mobile-more-item"><i class="fas fa-hand-holding-usd"></i>Loans</a>
        <a href="/user/deposits" class="mobile-more-item"><i class="fas fa-piggy-bank"></i>Deposits</a>
        <a href="/user/investments" class="mobile-more-item"><i class="fas fa-chart-line"></i>Invest</a>
        <a href="/user/kyc_form" class="mobile-more-item"><i class="fas fa-id-card"></i>KYC</a>
        <a href="/user/notifications" class="mobile-more-item"><i class="fas fa-bell"></i>Alerts</a>
        <a href="/user/settings" class="mobile-more-item"><i class="fas fa-cog"></i>Settings</a>
        <a href="/user/security" class="mobile-more-item"><i class="fas fa-shield-alt"></i>Security</a>
        <a href="/user/profile" class="mobile-more-item"><i class="fas fa-user"></i>Profile</a>
        <a href="/user/bill_pay" class="mobile-more-item"><i class="fas fa-file-invoice-dollar"></i>Bill Pay</a>
        <a href="/user/international_transfers" class="mobile-more-item"><i class="fas fa-globe"></i>Intl Transfer</a>
        <a href="#" onclick="handleLogout ? handleLogout(event) : (window.location='/auth/logout')" class="mobile-more-item" style="color:#dc3545;"><i class="fas fa-sign-out-alt" style="color:#dc3545;"></i>Logout</a>
    </div>

    <script>
    // Mobile more menu toggle
    function toggleMobileMoreMenu() {
        var menu = document.getElementById('mobile-more-menu');
        var overlay = document.getElementById('mobile-more-overlay');
        var isOpen = menu.classList.contains('open');
        if (isOpen) {
            menu.classList.remove('open');
            overlay.classList.remove('open');
        } else {
            menu.classList.add('open');
            overlay.classList.add('open');
        }
    }
    function closeMobileMoreMenu() {
        document.getElementById('mobile-more-menu').classList.remove('open');
        document.getElementById('mobile-more-overlay').classList.remove('open');
    }
    // Highlight the active mobile nav tab based on current URL
    (function() {
        var path = window.location.pathname;
        var map = {
            '/user/dashboard': 'mbnav-home',
            '/user/transfers': 'mbnav-transfer',
            '/user/bill_pay': 'mbnav-transfer',
            '/user/cards': 'mbnav-cards',
            '/user/transactions': 'mbnav-txn',
        };
        var activeId = null;
        for (var key in map) {
            if (path.indexOf(key) !== -1) { activeId = map[key]; break; }
        }
        if (activeId) {
            var el = document.getElementById(activeId);
            if (el) el.classList.add('active');
        }
    })();
    </script>'''

for f in files:
    path = f
    if not os.path.exists(path):
        print(f"File {f} not found.")
        continue
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Task 1: Add mobile.css
    if 'mobile.css' not in content:
        content = re.sub(r'(</head>)', r'' + mobile_css + '\n\\1', content, flags=re.IGNORECASE)
        
    # Task 2: dashboard.html stat cards
    if f == 'dashboard.html':
        content = content.replace('col-lg-3 col-md-6 mb-3', 'col-lg-3 col-6 mb-3 stat-card-col')
        
    # Task 3: Mobile bottom nav
    if 'id="mobile-bottom-nav"' not in content:
        content = re.sub(r'(</body>)', r'' + mobile_nav + '\n\\1', content, flags=re.IGNORECASE)
        
    # Task 4: table-responsive wrapper
    matches = list(re.finditer(r'<table\s+class="[^"]*?table[^"]*?".*?</table>', content, re.DOTALL))
    offset = 0
    new_content = content
    for match in matches:
        start = match.start() + offset
        end = match.end() + offset
        before = new_content[:start]
        # check if it is wrapped in table-responsive
        if not re.search(r'<div class="[^"]*?table-responsive[^"]*?">\s*$', before):
            table_html = new_content[start:end]
            wrapped = '<div class="table-responsive">\n' + table_html + '\n</div>'
            new_content = new_content[:start] + wrapped + new_content[end:]
            offset += len(wrapped) - len(table_html)
            
    with open(path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    print(f'Processed {f}')
