#!/usr/bin/env python3
"""
Generate all user-facing HTML pages with consistent navbar
"""

NAVBAR = '''    <!-- Navbar Start -->
    <div class="container-fluid fixed-top px-0 wow fadeIn" data-wow-delay="0.1s">
        <div class="top-bar row gx-0 align-items-center d-none d-lg-flex">
            <div class="col-lg-6 px-5 text-start">
                <small><i class="fa fa-map-marker-alt text-primary me-2"></i>123 Street, New York, USA</small>
                <small class="ms-4"><i class="fa fa-clock text-primary me-2"></i>9.00 am - 9.00 pm</small>
            </div>
            <div class="col-lg-6 px-5 text-end">
                <small><i class="fa fa-envelope text-primary me-2"></i>info@example.com</small>
                <small class="ms-4"><i class="fa fa-phone-alt text-primary me-2"></i>+012 345 6789</small>
            </div>
        </div>

        <nav class="navbar navbar-expand-lg navbar-light py-lg-0 px-lg-5 wow fadeIn" data-wow-delay="0.1s">
            <a href="/user/dashboard" class="navbar-brand ms-4 ms-lg-0">
                <h5 class="m-0 text-primary"><i class="fa fa-university me-2"></i>Finanza</h5>
            </a>
            <button type="button" class="navbar-toggler me-4" data-bs-toggle="collapse" data-bs-target="#navbarCollapse">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarCollapse">
                <div class="navbar-nav ms-auto p-4 p-lg-0">
                    <!-- MAIN -->
                    <a href="/user/dashboard" class="nav-item nav-link">Dashboard</a>
                    <a href="/user/account" class="nav-item nav-link">Account</a>
                    <a href="/user/kyc" class="nav-item nav-link">KYC</a>
                    
                    <!-- FINANCIAL PRODUCTS -->
                    <div class="nav-item dropdown">
                        <a href="javascript:void(0)" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">Products</a>
                        <div class="dropdown-menu border-light m-0">
                            <a href="/user/cards" class="dropdown-item">Cards</a>
                            <a href="/user/deposits" class="dropdown-item">Deposits</a>
                            <a href="/user/loans" class="dropdown-item">Loans</a>
                            <a href="/user/investments" class="dropdown-item">Investments</a>
                        </div>
                    </div>

                    <!-- TOOLS & ANALYTICS -->
                    <div class="nav-item dropdown">
                        <a href="javascript:void(0)" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">Services</a>
                        <div class="dropdown-menu border-light m-0">
                            <a href="/user/business_analysis" class="dropdown-item">Business Analysis</a>
                            <a href="/user/financial_planning" class="dropdown-item">Financial Planning</a>
                            <a href="/user/insurance" class="dropdown-item">Insurance</a>
                            <a href="/user/project" class="dropdown-item">Projects</a>
                        </div>
                    </div>

                    <!-- USER UTILITIES -->
                    <div class="nav-item dropdown">
                        <a href="javascript:void(0)" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">More</a>
                        <div class="dropdown-menu border-light m-0">
                            <a href="/user/profile" class="dropdown-item">Profile</a>
                            <a href="/user/settings" class="dropdown-item">Settings</a>
                            <a href="/user/notifications" class="dropdown-item">Notifications</a>
                            <a href="/user/contact" class="dropdown-item">Contact/Support</a>
                            <hr class="m-2">
                            <a href="/logout" class="dropdown-item text-danger">Logout</a>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    </div>
    <!-- Navbar End -->'''

FOOTER = '''    <!-- Footer Start -->
    <div class="container-fluid bg-dark text-light footer mt-5 py-5 wow fadeIn" data-wow-delay="0.1s">
        <div class="container py-5">
            <div class="row g-5">
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Address</h5>
                    <p class="mb-2"><i class="fa fa-map-marker-alt me-3"></i>123 Street, New York, USA</p>
                    <p class="mb-2"><i class="fa fa-phone-alt me-3"></i>+012 345 6789</p>
                    <p class="mb-0"><i class="fa fa-envelope me-3"></i>info@example.com</p>
                </div>
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Quick Links</h5>
                    <a class="btn btn-link text-white-50" href="/user/dashboard">Dashboard</a>
                    <a class="btn btn-link text-white-50" href="/user/kyc">KYC</a>
                    <a class="btn btn-link text-white-50" href="/user/contact">Support</a>
                </div>
            </div>
        </div>
        <div class="container">
            <div class="copyright">
                <div class="row">
                    <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
                        &copy; <a class="border-bottom" href="#">Finanza Bank</a>, All Right Reserved.
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- Footer End -->

    <!-- Back to Top -->
    <a href="#" class="btn btn-lg btn-primary btn-lg-square back-to-top"><i class="bi bi-arrow-up"></i></a>

    <!-- JavaScript Libraries -->
    <script src="https://code.jquery.com/jquery-3.4.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/lib/wow/wow.min.js"></script>
    <script src="/lib/easing/easing.min.js"></script>
    <script src="/lib/waypoints/waypoints.min.js"></script>
    <script src="/lib/counterup/counterup.min.js"></script>
    <script src="/lib/owlcarousel/owl.carousel.min.js"></script>
    <script src="/js/main.js"></script>
    <script src="/js/user-guard.js"></script>
</body>

</html>'''

def generate_page(title, page_name, content):
    """Generate a complete HTML page"""
    return f'''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <title>{title} - Finanza Bank</title>
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <meta content="" name="keywords">
    <meta content="" name="description">

    <!-- Favicon -->
    <link href="/img/favicon.ico" rel="icon">

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
        <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status">
            <span class="sr-only">Loading...</span>
        </div>
    </div>
    <!-- Spinner End -->

{NAVBAR}

    <!-- Page Header Start -->
    <div class="container-fluid page-header mb-5 wow fadeIn" data-wow-delay="0.1s">
        <div class="container">
            <h1 class="display-4 pb-3 animated slideInDown">{title}</h1>
            <nav aria-label="breadcrumb animated slideInDown">
                <ol class="breadcrumb mb-0">
                    <li class="breadcrumb-item"><a class="text-white" href="/user/dashboard">Home</a></li>
                    <li class="breadcrumb-item text-primary active" aria-current="page">{title}</li>
                </ol>
            </nav>
        </div>
    </div>
    <!-- Page Header End -->

    <!-- Content Start -->
    <div class="container-xxl py-5">
        <div class="container">
            <div class="row g-5">
                <div class="col-lg-12 wow fadeInUp" data-wow-delay="0.1s">
{content}
                </div>
            </div>
        </div>
    </div>
    <!-- Content End -->

{FOOTER}'''

# Define pages
pages = {
    'kyc.html': ('KYC Verification', 'kyc', '''                    <h2 class="mb-4">Know Your Customer (KYC) Verification</h2>
                    <p class="mb-4">Complete your KYC verification to unlock all features and services.</p>
                    
                    <div class="row g-4">
                        <div class="col-md-6">
                            <div class="card p-4 bg-light">
                                <h5 class="card-title">Verification Status</h5>
                                <p class="mb-3">
                                    {% if user and user.is_verified %}
                                    <span class="badge bg-success">Verified</span>
                                    {% else %}
                                    <span class="badge bg-warning">Not Verified</span>
                                    {% endif %}
                                </p>
                                <p class="text-muted">Your account verification status and details.</p>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card p-4 bg-light">
                                <h5 class="card-title">Next Steps</h5>
                                {% if user and not user.is_verified %}
                                <a href="/user/kyc_form" class="btn btn-primary">Start KYC Verification</a>
                                {% else %}
                                <p class="text-success">Your account is fully verified!</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>

                    <div class="mt-5">
                        <h5>What is KYC?</h5>
                        <p>Know Your Customer (KYC) is a standard identification and verification process required by financial institutions to prevent fraud and money laundering.</p>
                    </div>'''),
    
    'kyc_form.html': ('KYC Verification Form', 'kyc_form', '''                    <h2 class="mb-4">Complete Your KYC Verification</h2>
                    <p class="mb-4">Please provide the required information for identity verification.</p>
                    
                    <form method="POST" action="/api/v1/kyc/submit" enctype="multipart/form-data" class="needs-validation">
                        <div class="card mb-4">
                            <div class="card-header"><h5>Personal Information</h5></div>
                            <div class="card-body">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">Full Name *</label>
                                        <input type="text" class="form-control" name="full_name" required>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Date of Birth *</label>
                                        <input type="date" class="form-control" name="dob" required>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">Nationality *</label>
                                        <input type="text" class="form-control" name="nationality" required>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Gender *</label>
                                        <select class="form-select" name="gender" required>
                                            <option value="">Select...</option>
                                            <option value="male">Male</option>
                                            <option value="female">Female</option>
                                            <option value="other">Other</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Address *</label>
                                    <textarea class="form-control" name="address" rows="3" required></textarea>
                                </div>
                            </div>
                        </div>

                        <div class="card mb-4">
                            <div class="card-header"><h5>Identity Document</h5></div>
                            <div class="card-body">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label">Document Type *</label>
                                        <select class="form-select" name="document_type" required>
                                            <option value="">Select...</option>
                                            <option value="passport">Passport</option>
                                            <option value="national_id">National ID</option>
                                            <option value="driver_license">Driver's License</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Document Number *</label>
                                        <input type="text" class="form-control" name="document_number" required>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Upload Document (Front) *</label>
                                    <input type="file" class="form-control" name="document_front" accept="image/*" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Upload Selfie *</label>
                                    <input type="file" class="form-control" name="selfie" accept="image/*" required>
                                </div>
                            </div>
                        </div>

                        <button type="submit" class="btn btn-primary btn-lg">Submit KYC Verification</button>
                    </form>'''),
    
    'kyc_pending.html': ('KYC Verification Pending', 'kyc_pending', '''                    <div class="alert alert-warning" role="alert">
                        <h4 class="alert-heading">Verification Pending</h4>
                        <p>Your KYC verification is currently under review. We will process your documents and notify you shortly.</p>
                    </div>

                    <div class="card mt-4">
                        <div class="card-body">
                            <h5 class="card-title">What to Expect</h5>
                            <ul>
                                <li>Document verification typically takes 1-3 business days</li>
                                <li>You'll receive an email notification once verification is complete</li>
                                <li>Some features may be limited until verification is approved</li>
                            </ul>
                        </div>
                    </div>'''),
    
    'kyc_success.html': ('KYC Verification Approved', 'kyc_success', '''                    <div class="alert alert-success" role="alert">
                        <h4 class="alert-heading">Verification Successful!</h4>
                        <p>Congratulations! Your KYC verification has been approved. You now have full access to all features and services.</p>
                    </div>

                    <div class="card mt-4">
                        <div class="card-body">
                            <h5 class="card-title">You're All Set</h5>
                            <p>Your account is now fully verified. You can now:</p>
                            <ul>
                                <li>Access all financial products</li>
                                <li>Make unlimited transactions</li>
                                <li>Apply for loans and investments</li>
                                <li>Use all platform features</li>
                            </ul>
                            <a href="/user/dashboard" class="btn btn-primary mt-3">Go to Dashboard</a>
                        </div>
                    </div>'''),
    
    'kyc_rejected.html': ('KYC Verification Rejected', 'kyc_rejected', '''                    <div class="alert alert-danger" role="alert">
                        <h4 class="alert-heading">Verification Not Approved</h4>
                        <p>Unfortunately, your KYC verification could not be approved at this time.</p>
                    </div>

                    <div class="card mt-4">
                        <div class="card-body">
                            <h5 class="card-title">Next Steps</h5>
                            <p>Possible reasons for rejection:</p>
                            <ul>
                                <li>Document image quality too low</li>
                                <li>Information doesn't match document</li>
                                <li>Expired identification document</li>
                            </ul>
                            <p class="mt-3">Please contact support for more information.</p>
                            <a href="/user/kyc_form" class="btn btn-primary mt-3">Try Again</a>
                            <a href="/user/contact" class="btn btn-secondary mt-3">Contact Support</a>
                        </div>
                    </div>'''),
}

# Generate and save pages
import os
base_path = 'c:\\Users\\Aweh\\Downloads\\supreme\\financial-services-website-template\\private\\user\\'

for filename, (title, page_type, content) in pages.items():
    filepath = os.path.join(base_path, filename)
    html = generate_page(title, page_type, content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✓ Created: {filename}")

print("\nAll KYC pages generated successfully!")
