#!/usr/bin/env python3
"""Generate all user templates with consistent Finanza design."""

import os

USER_TEMPLATES = {
    # MAIN
    'dashboard.html': ('Dashboard', 'Overview of your account', 'Dashboard'),
    'account.html': ('Account & Profile', 'Manage your profile and account settings', 'My Account'),
    'kyc.html': ('KYC Verification', 'Know Your Customer verification', 'KYC'),
    
    # FINANCIAL PRODUCTS
    'cards.html': ('My Cards', 'Manage your payment cards', 'Cards'),
    'deposits.html': ('Deposits', 'Make deposits and manage your funds', 'Deposits'),
    'loans.html': ('Loans', 'View and manage your loans', 'Loans'),
    'investments.html': ('Investments', 'Manage your investment portfolio', 'Investments'),
    
    # TOOLS & ANALYTICS
    'business_analysis.html': ('Business Analysis', 'Analyze your business metrics', 'Business Analysis'),
    'financial_planning.html': ('Financial Planning', 'Plan your financial future', 'Financial Planning'),
    'insurance.html': ('Insurance', 'Insurance products and coverage', 'Insurance'),
    'project.html': ('Projects', 'Manage your projects', 'Projects'),
    
    # USER UTILITIES
    'settings.html': ('Settings', 'Account settings and preferences', 'Settings'),
    'notifications.html': ('Notifications', 'Your notifications and alerts', 'Notifications'),
    'contact.html': ('Contact Support', 'Get help and support', 'Support'),
}

def generate_user_template(title, description, subtitle):
    """Generate a single user page template."""
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
            <a href="/user/dashboard" class="navbar-brand ms-4 ms-lg-0">
                <h1 class="m-0 text-primary">Finanza</h1>
            </a>
            <button type="button" class="navbar-toggler me-4" data-bs-toggle="collapse" data-bs-target="#navbarCollapse">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarCollapse"> 
                <div class="navbar-nav ms-auto p-4 p-lg-0">
                    <!-- Main Section -->
                    <a href="/user/dashboard" class="nav-item nav-link">Dashboard</a>
                    <a href="/user/account" class="nav-item nav-link">Account</a>
                    <a href="/user/kyc" class="nav-item nav-link">KYC</a>
                    
                    <!-- Financial Products -->
                    <a href="/user/cards" class="nav-item nav-link">Cards</a>
                    <a href="/user/deposits" class="nav-item nav-link">Deposits</a>
                    <a href="/user/loans" class="nav-item nav-link">Loans</a>
                    <a href="/user/investments" class="nav-item nav-link">Investments</a>
                    
                    <!-- Tools & Analytics -->
                    <a href="/user/business_analysis" class="nav-item nav-link">Analysis</a>
                    <a href="/user/financial_planning" class="nav-item nav-link">Planning</a>
                    <a href="/user/insurance" class="nav-item nav-link">Insurance</a>
                    
                    <!-- Settings -->
                    <a href="/user/settings" class="nav-item nav-link">Settings</a>
                </div>
                <div class="d-none d-lg-flex ms-2">
                    <a href="/logout" class="btn btn-danger py-2 px-4 animated slideInLeft">
                        LOGOUT <i class="fa fa-sign-out-alt"></i>
                    </a>
                </div>
            </div>
        </nav>
    </div>
    <!-- Navbar End -->


    <!-- Page Header Start -->
    <div class="container-fluid page-header mb-5">
        <div class="container">
            <h1 class="display-4 pb-3 mb-0 animated slideInDown">{title}</h1>
        </div>
    </div>
    <!-- Page Header End -->


    <!-- User Content Start -->
    <div class="container-xxl py-5">
        <div class="container">
            <div class="row g-4 mb-5">
                <div class="col-12 text-center wow fadeInUp" data-wow-delay="0.1s">
                    <p class="d-inline-block border rounded text-primary fw-semi-bold py-1 px-3">{subtitle}</p>
                    <h1 class="display-5 mb-5">{title}</h1>
                    <p class="lead">{description}</p>
                </div>
            </div>
        </div>
    </div>
    <!-- User Content End -->


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
    """Generate all user templates."""
    base_dir = 'templates/user'
    os.makedirs(base_dir, exist_ok=True)
    
    for filename, (title, description, subtitle) in USER_TEMPLATES.items():
        filepath = os.path.join(base_dir, filename)
        content = generate_user_template(title, description, subtitle)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✓ Generated {filepath}")
    
    print(f"\n✅ Created {len(USER_TEMPLATES)} user templates in {base_dir}/")

if __name__ == '__main__':
    main()
