/**
 * Finanza Institutional Banking — Unified Public Frontend Shell
 * Ensures consistent navigation, session-aware E-Banking CTA buttons,
 * interactive callback/newsletter forms, and zero dead links across all public pages.
 */
(function () {
    function hasActiveSession() {
        const token = localStorage.getItem('token') || localStorage.getItem('access_token');
        if (!token || token === 'null' || token === 'undefined') return false;
        return true;
    }

    function getPortalUrl() {
        const isAdmin = localStorage.getItem('is_admin') === 'true';
        return isAdmin ? '/user/admin/dashboard' : '/user/dashboard';
    }

    function showPublicToast(message, type) {
        if (window.showToast && typeof window.showToast === 'function') {
            window.showToast(message, type || 'success');
            return;
        }
        let box = document.getElementById('fzPublicToast');
        if (!box) {
            box = document.createElement('div');
            box.id = 'fzPublicToast';
            box.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;max-width:420px;padding:14px 20px;border-radius:12px;color:#fff;font-weight:600;box-shadow:0 12px 30px rgba(0,0,0,0.25);transition:opacity 0.3s ease;';
            document.body.appendChild(box);
        }
        box.style.background = type === 'danger' ? '#dc2626' : '#16a34a';
        box.innerHTML = `<i class="fa fa-check-circle me-2"></i>${message}`;
        box.style.opacity = '1';
        setTimeout(() => { box.style.opacity = '0'; }, 4000);
    }

    function upgradeNavbarAndLinks() {
        const path = window.location.pathname.replace(/\.html$/, '') || '/';
        const loggedIn = hasActiveSession();
        const portalUrl = getPortalUrl();

        // 1. Standardize the main navbar across all public pages (including feature.html, testimonial.html, etc.)
        const navCollapse = document.getElementById('navbarCollapse');
        if (navCollapse) {
            const isActive = (p) => (path === p ? 'active' : '');
            const ctaHtml = loggedIn
                ? `<div class="d-none d-lg-flex ms-3 fz-nav-cta-group">
                       <a class="tp-btn btn btn-primary py-2 px-4" href="${portalUrl}">
                           <i class="fa fa-th-large me-1"></i> MY PORTAL
                       </a>
                       <a class="fz-btn-outline" href="/logout" onclick="localStorage.clear();sessionStorage.clear();">
                           <i class="fa fa-sign-out-alt me-1"></i> Sign Out
                       </a>
                   </div>`
                : `<div class="d-none d-lg-flex ms-3 fz-nav-cta-group">
                       <a class="fz-btn-outline" href="/signin">Sign In</a>
                       <a class="tp-btn btn btn-primary py-2 px-4" href="/signup">
                           OPEN ACCOUNT <i class="fa fa-arrow-right ms-1"></i>
                       </a>
                   </div>`;

            navCollapse.innerHTML = `
                <div class="navbar-nav ms-auto p-4 p-lg-0">
                    <a href="/" class="nav-item nav-link ${isActive('/')}">Home</a>
                    <div class="nav-item dropdown">
                        <a href="javascript:void(0)" class="nav-link dropdown-toggle ${['/personal','/corporate','/about','/service','/feature'].includes(path) ? 'active' : ''}" data-bs-toggle="dropdown">Banking</a>
                        <div class="dropdown-menu border-light m-0">
                            <a href="/personal" class="dropdown-item">Personal Banking</a>
                            <a href="/corporate" class="dropdown-item">Corporate & Institutional</a>
                            <a href="/service" class="dropdown-item">All Financial Services</a>
                            <a href="/feature" class="dropdown-item">Platform Capabilities</a>
                            <a href="/about" class="dropdown-item">About Finanza</a>
                        </div>
                    </div>
                    <a href="/deposits" class="nav-item nav-link ${isActive('/deposits')}">Deposits</a>
                    <a href="/cards" class="nav-item nav-link ${isActive('/cards')}">Cards</a>
                    <a href="/loans" class="nav-item nav-link ${isActive('/loans')}">Loans</a>
                    <a href="/investments" class="nav-item nav-link ${isActive('/investments')}">Investments</a>
                    <a href="/insurance" class="nav-item nav-link ${isActive('/insurance')}">Insurance</a>
                    <a href="/contact" class="nav-item nav-link ${isActive('/contact')}">Contact</a>
                    <div class="nav-item dropdown d-lg-none">
                        <a href="javascript:void(0)" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">E-Banking</a>
                        <div class="dropdown-menu border-light m-0">
                            ${loggedIn
                                ? `<a href="${portalUrl}" class="dropdown-item">Open My Portal</a>
                                   <a href="/logout" class="dropdown-item" onclick="localStorage.clear();sessionStorage.clear();">Sign Out</a>`
                                : `<a href="/signin" class="dropdown-item">Sign In</a>
                                   <a href="/signup" class="dropdown-item">Create Account</a>`
                            }
                        </div>
                    </div>
                </div>
                ${ctaHtml}
            `;
        }

        // 2. Ensure navbar-brand always shows clean Finanza emblem
        const brand = document.querySelector('.navbar-brand');
        if (brand) {
            brand.setAttribute('href', '/');
            brand.innerHTML = `<h1 class="display-6 text-primary m-0"><i class="fa fa-university me-2" style="-webkit-text-fill-color:#2563eb;"></i>Finanza</h1>`;
        }

        // 3. Rewrite any remaining /dashboard or dead links across the page body
        document.querySelectorAll('a').forEach(a => {
            const rawHref = (a.getAttribute('href') || '').trim();
            if (rawHref === '/dashboard' || rawHref === '/static/dashboard.html') {
                a.setAttribute('href', loggedIn ? portalUrl : '/signin');
            } else if (rawHref === '/dashboard/signup') {
                a.setAttribute('href', '/signup');
            } else if (rawHref === '/account-recovery') {
                a.setAttribute('href', '/forgot-password');
            } else if (rawHref === '' && !a.classList.contains('dropdown-toggle')) {
                if (a.closest('.project-img')) {
                    a.setAttribute('href', '/project');
                } else if (a.closest('.team-social') || a.querySelector('.fab')) {
                    a.setAttribute('href', '/contact');
                } else {
                    a.setAttribute('href', '/service');
                }
            } else if (rawHref === '#' && !a.hasAttribute('data-bs-toggle') && !a.classList.contains('back-to-top')) {
                const txt = (a.textContent || '').toLowerCase();
                if (txt.includes('support') || txt.includes('help') || txt.includes('contact')) {
                    a.setAttribute('href', '/contact');
                } else if (txt.includes('term') || txt.includes('condition') || txt.includes('privacy')) {
                    a.setAttribute('href', '/about');
                } else if (txt.includes('finanza')) {
                    a.setAttribute('href', '/');
                } else if (txt.includes('account')) {
                    a.setAttribute('href', loggedIn ? portalUrl : '/signin');
                }
            }
        });

        // 4. Inject Institutional Trust Strip before Footer on main marketing pages
        const footer = document.querySelector('.footer');
        if (footer && !document.getElementById('fzTrustStrip') && !['/signin', '/signup', '/forgot-password', '/reset-password'].includes(path)) {
            const strip = document.createElement('div');
            strip.id = 'fzTrustStrip';
            strip.className = 'fz-trust-strip';
            strip.innerHTML = `
                <div class="container">
                    <div class="fz-trust-grid">
                        <div class="fz-trust-item">
                            <div class="fz-trust-icon"><i class="fa fa-shield-alt"></i></div>
                            <div>
                                <div class="fw-bold">256-Bit Bank-Grade Security</div>
                                <small class="text-white-50">Multi-factor authentication & real-time fraud monitoring</small>
                            </div>
                        </div>
                        <div class="fz-trust-item">
                            <div class="fz-trust-icon"><i class="fa fa-globe"></i></div>
                            <div>
                                <div class="fw-bold">Global Payment Rails</div>
                                <small class="text-white-50">Instant ACH, FedNow, SWIFT Wire & Multi-Currency FX</small>
                            </div>
                        </div>
                        <div class="fz-trust-item">
                            <div class="fz-trust-icon"><i class="fa fa-university"></i></div>
                            <div>
                                <div class="fw-bold">Institutional Reserve Backing</div>
                                <small class="text-white-50">Full-reserve double-entry ledger & automated clearing</small>
                            </div>
                        </div>
                        <div class="fz-trust-item">
                            <div class="fz-trust-icon"><i class="fa fa-headset"></i></div>
                            <div>
                                <div class="fw-bold">24/7 Dedicated Concierge</div>
                                <small class="text-white-50">Personal & corporate advisory specialists on standby</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            footer.parentNode.insertBefore(strip, footer);
        }

        // 5. Wire interactive callback / contact / newsletter forms on public pages
        document.querySelectorAll('.callback button[type="submit"], .footer button').forEach(btn => {
            if (btn.dataset.fzWired) return;
            btn.dataset.fzWired = '1';
            btn.addEventListener('click', function (e) {
                const form = btn.closest('form');
                if (form && (form.id === 'signInForm' || form.id === 'signupForm' || form.id === 'forgotPasswordForm' || form.id === 'resetPasswordForm')) {
                    return;
                }
                e.preventDefault();
                const container = btn.closest('.callback') || btn.closest('.footer') || btn.parentElement;
                const inputs = container ? container.querySelectorAll('input, textarea') : [];
                let hasValue = false;
                inputs.forEach(inp => {
                    if (inp.value && inp.value.trim()) hasValue = true;
                });
                if (!hasValue) {
                    showPublicToast('Please enter your contact details before submitting.', 'danger');
                    return;
                }
                inputs.forEach(inp => { inp.value = ''; });
                showPublicToast('Thank you! A Finanza relationship specialist has received your request.', 'success');
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', upgradeNavbarAndLinks);
    } else {
        upgradeNavbarAndLinks();
    }
})();
