#!/usr/bin/env python3
"""Generate all admin templates with consistent Finanza design."""

import os

TEMPLATE_MAP = {
    'admin_profile.html': ('Admin Profile', 'admin/profile', 'My Profile'),
    'admin_settings.html': ('Admin Settings', 'admin/settings', 'System Settings'),
    'admin_system_settings.html': ('System Settings', 'admin/system-settings', 'System Settings'),
    'admin_email_settings.html': ('Email Settings', 'admin/email-settings', 'Email Configuration'),
    'admin_payment_settings.html': ('Payment Settings', 'admin/payment-settings', 'Payment Configuration'),
    'admin_maintenance_mode.html': ('Maintenance Mode', 'admin/maintenance', 'Maintenance Mode'),
    'admin_users.html': ('User Management', 'admin/users', 'Manage Users'),
    'admin_user_details.html': ('User Details', 'admin/user-details', 'User Information'),
    'admin_user_accounts.html': ('User Accounts', 'admin/user-accounts', 'Linked Accounts'),
    'admin_user_assets.html': ('User Assets', 'admin/user-assets', 'User Assets'),
    'admin_user_investments.html': ('User Investments', 'admin/user-investments', 'Investment Portfolio'),
    'admin_user_loans.html': ('User Loans', 'admin/user-loans', 'User Loans'),
    'admin_user_cards.html': ('User Cards', 'admin/user-cards', 'Card Management'),
    'admin_user_wallets.html': ('User Wallets', 'admin/user-wallets', 'Wallet Management'),
    'admin_kyc.html': ('KYC Management', 'admin/kyc', 'KYC Submissions'),
    'admin_kyc_list.html': ('KYC List', 'admin/kyc-list', 'All KYC Records'),
    'admin_kyc_review.html': ('KYC Review', 'admin/kyc-review', 'Review Submissions'),
    'admin_kyc_details.html': ('KYC Details', 'admin/kyc-details', 'KYC Information'),
    'admin_kyc_settings.html': ('KYC Settings', 'admin/kyc-settings', 'KYC Configuration'),
    'admin_transactions.html': ('Transactions', 'admin/transactions', 'Transaction Management'),
    'admin_transaction_details.html': ('Transaction Details', 'admin/transaction-details', 'Transaction Info'),
    'admin_pending_deposits.html': ('Pending Deposits', 'admin/pending-deposits', 'Deposit Requests'),
    'admin_pending_withdrawals.html': ('Pending Withdrawals', 'admin/pending-withdrawals', 'Withdrawal Requests'),
    'admin_submissions.html': ('Submissions', 'admin/submissions', 'User Submissions'),
    'admin_fund_user.html': ('Fund User', 'admin/fund-user', 'Credit User Account'),
    'admin_adjust_balance.html': ('Adjust Balance', 'admin/adjust-balance', 'Balance Adjustment'),
    'admin_reports.html': ('Reports', 'admin/reports', 'System Reports'),
    'admin_content.html': ('Content Management', 'admin/content', 'Manage Content'),
    'admin_logs.html': ('System Logs', 'admin/logs', 'Activity Logs'),
    'admin_activity_monitor.html': ('Activity Monitor', 'admin/activity', 'Real-time Activity'),
    'admin_security_center.html': ('Security Center', 'admin/security', 'Security Settings'),
    'admin_notifications.html': ('Notifications', 'admin/notifications', 'Send Notifications'),
    'admin_roles.html': ('Manage Roles', 'admin/roles', 'Role Management'),
    'admin_manage_admins.html': ('Manage Admins', 'admin/manage-admins', 'Admin Accounts'),
}

def get_active_link(path):
    """Map path to nav link for active state."""
    paths = {
        'admin/profile': 'Profile',
        'admin/settings': 'Settings',
        'admin/system-settings': 'Settings',
        'admin/email-settings': 'Settings',
        'admin/payment-settings': 'Settings',
        'admin/maintenance': 'Settings',
        'admin/users': 'Users',
        'admin/user-details': 'Users',
        'admin/user-accounts': 'Users',
        'admin/user-assets': 'Users',
        'admin/user-investments': 'Users',
        'admin/user-loans': 'Users',
        'admin/user-cards': 'Users',
        'admin/user-wallets': 'Users',
        'admin/kyc': 'KYC',
        'admin/kyc-list': 'KYC',
        'admin/kyc-review': 'KYC',
        'admin/kyc-details': 'KYC',
        'admin/kyc-settings': 'KYC',
        'admin/transactions': 'Transactions',
        'admin/transaction-details': 'Transactions',
        'admin/pending-deposits': 'Transactions',
        'admin/pending-withdrawals': 'Transactions',
        'admin/submissions': 'Submissions',
        'admin/fund-user': 'Transactions',
        'admin/adjust-balance': 'Transactions',
        'admin/reports': 'Reports',
        'admin/content': 'Content',
        'admin/logs': 'Settings',
        'admin/activity': 'Settings',
        'admin/security': 'Settings',
        'admin/notifications': 'Settings',
        'admin/roles': 'Settings',
        'admin/manage-admins': 'Settings',
    }
    return paths.get(path)

def generate_template(title, page_title, subtitle):
    """Generate a single admin page template."""
    return f'''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <title>Finanza - {title}</title>
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <meta content="" name="keywords">
    <meta content="" name="description">

    <!-- Google Web Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Jost:wght@500;600;700&family=Open+Sans:wght@400;500&display=swap" rel="stylesheet">  

    <!-- Icon Font Stylesheet -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.10.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css" rel="stylesheet">

    <!-- Libraries Stylesheet -->
    <link href="/lib/animate/animate.min.css" rel="stylesheet">
    <link href="/lib/owlcarousel/assets/owl.carousel.min.css" rel="stylesheet">

    <!-- Customized Bootstrap Stylesheet -->
    <link href="/css/bootstrap.min.css" rel="stylesheet">

    <!-- Template Stylesheet -->
    <link href="/css/style.css" rel="stylesheet">
</head>

<body>
    <!-- Spinner Start -->
    <div id="spinner" class="show bg-white position-fixed translate-middle w-100 vh-100 top-50 start-50 d-flex align-items-center justify-content-center">
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div>
    </div>
    <!-- Spinner End -->


    <!-- Navbar Start -->
    <div class="container-fluid px-0 wow fadeIn" data-wow-delay="0.1s">
        <nav class="navbar navbar-expand-lg navbar-light py-lg-0 px-lg-5">
            <a href="/admin/dashboard" class="navbar-brand ms-4 ms-lg-0">
                <h1 class="m-0 text-primary">Finanza Admin</h1>
            </a>
            <button type="button" class="navbar-toggler me-4" data-bs-toggle="collapse" data-bs-target="#navbarCollapse">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarCollapse"> 
                <div class="navbar-nav ms-auto p-4 p-lg-0">
                    <a href="/admin/dashboard" class="nav-item nav-link">Dashboard</a>
                    <a href="/admin/users" class="nav-item nav-link">Users</a>
                    <a href="/admin/kyc" class="nav-item nav-link">KYC</a>
                    <a href="/admin/transactions" class="nav-item nav-link">Transactions</a>
                    <a href="/admin/submissions" class="nav-item nav-link">Submissions</a>
                    <a href="/admin/content" class="nav-item nav-link">Content</a>
                    <a href="/admin/reports" class="nav-item nav-link">Reports</a>
                    <a href="/admin/settings" class="nav-item nav-link">Settings</a>
                    <a href="/admin/profile" class="nav-item nav-link">Profile</a>
                </div>
                <div class="d-none d-lg-flex ms-2">
                    <button class="btn btn-danger py-2 px-4 animated slideInLeft" data-bs-toggle="modal" data-bs-target="#logoutModal">
                        LOGOUT <i class="fa fa-sign-out-alt"></i>
                    </button>
                </div>
            </div>
        </nav>
    </div>
    <!-- Navbar End -->


    <!-- Page Header Start -->
    <div class="container-fluid page-header mb-5">
        <div class="container">
            <h1 class="display-4 pb-3 mb-0 animated slideInDown">{page_title}</h1>
        </div>
    </div>
    <!-- Page Header End -->


    <!-- Admin Content Start -->
    <div class="container-xxl py-5">
        <div class="container">
            <div class="row g-4 mb-5">
                <div class="col-12 text-center wow fadeInUp" data-wow-delay="0.1s">
                    <p class="d-inline-block border rounded text-primary fw-semi-bold py-1 px-3">{subtitle}</p>
                    <h1 class="display-5 mb-5">{title}</h1>
                </div>
            </div>
        </div>
    </div>
    <!-- Admin Content End -->


    <!-- Logout Modal -->
    <div class="modal fade" id="logoutModal" tabindex="-1" aria-labelledby="logoutModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="logoutModalLabel">Confirm Logout</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    Are you sure you want to log out?
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <a href="/logout" class="btn btn-danger">Logout</a>
                </div>
            </div>
        </div>
    </div>


    <!-- Footer Start -->
    <div class="container-fluid bg-dark text-light footer mt-5 py-3 wow fadeIn" data-wow-delay="0.1s">
        <div class="container">
            <div class="row">
                <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
                    &copy; <a class="border-bottom" href="#">Finanza</a>, All Right Reserved.
                </div>
                <div class="col-md-6 text-center text-md-end">
                    Designed By <a class="border-bottom" href="https://htmlcodex.com">HTML Codex</a>
                </div>
            </div>
        </div>
    </div>
    <!-- Footer End -->


    <!-- Back to Top -->
    <a href="#" class="btn btn-lg btn-primary btn-lg-square rounded-circle back-to-top"><i class="bi bi-arrow-up"></i></a>


    <!-- JavaScript Libraries -->
    <script src="https://code.jquery.com/jquery-3.4.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/lib/wow/wow.min.js"></script>
    <script src="/lib/easing/easing.min.js"></script>
    <script src="/lib/waypoints/waypoints.min.js"></script>
    <script src="/lib/owlcarousel/owl.carousel.min.js"></script>
    <script src="/lib/counterup/counterup.min.js"></script>

    <!-- Template Javascript -->
    <script src="/js/main.js"></script>
</body>

</html>
'''

def main():
    """Generate all admin templates."""
    base_dir = 'private/admin'
    os.makedirs(base_dir, exist_ok=True)
    
    for filename, (title, path, subtitle) in TEMPLATE_MAP.items():
        filepath = os.path.join(base_dir, filename)
        content = generate_template(title, title, subtitle)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Generated {filepath}")

if __name__ == '__main__':
    main()
