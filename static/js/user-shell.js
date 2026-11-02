/**
 * FINANZA DIGITAL BANKING — UNIFIED APP SHELL ENGINE (user-shell.js)
 * Powers navigation, live header balances, global "+ Add Money" flow,
 * receipt printing, toast notifications, and authenticated API calls.
 */
(function () {
    'use strict';

    const NAV_SECTIONS = [
        {
            title: 'Overview',
            items: [
                { href: '/user/dashboard', icon: 'fa-chart-pie', label: 'Dashboard', match: ['/user/dashboard'] },
                { href: '/user/account', icon: 'fa-building-columns', label: 'Accounts & Statements', match: ['/user/account'] },
                { href: '/user/transactions', icon: 'fa-list-check', label: 'Ledger Activity', match: ['/user/transactions', '/user/settlement_status'] }
            ]
        },
        {
            title: 'Move Money',
            items: [
                { href: '/user/transfers', icon: 'fa-paper-plane', label: 'Send & Wire Money', match: ['/user/transfers', '/user/international_transfers', '/user/scheduled_transfers'] },
                { href: '/user/bill_pay', icon: 'fa-file-invoice-dollar', label: 'Pay Bills', match: ['/user/bill_pay'] },
                { href: '/user/currency_exchange', icon: 'fa-coins', label: 'FX Exchange', match: ['/user/currency_exchange'] }
            ]
        },
        {
            title: 'Cards & Wealth',
            items: [
                { href: '/user/cards', icon: 'fa-credit-card', label: 'Cards Studio', match: ['/user/cards'] },
                { href: '/user/deposits', icon: 'fa-vault', label: 'Savings & CDs', match: ['/user/deposits'] },
                { href: '/user/loans', icon: 'fa-hand-holding-dollar', label: 'Loans & Credit', match: ['/user/loans', '/user/loans_enhanced'] },
                { href: '/user/investments', icon: 'fa-arrow-trend-up', label: 'Investments', match: ['/user/investments', '/user/project', '/user/treasury_portfolio'] },
                { href: '/user/blockchain', icon: 'fa-cubes', label: 'Crypto & Web3', match: ['/user/blockchain'] },
                { href: '/user/insurance', icon: 'fa-shield-halved', label: 'Insurance', match: ['/user/insurance'] },
                { href: '/user/analytics', icon: 'fa-chart-line', label: 'Cash Flow Analytics', match: ['/user/analytics', '/user/business_analysis', '/user/financial_planning'] }
            ]
        },
        {
            title: 'Profile & Security',
            items: [
                { href: '/user/kyc', icon: 'fa-id-card-clip', label: 'Identity (KYC)', match: ['/user/kyc', '/user/kyc_form', '/user/kyc/verify', '/user/kyc_pending', '/user/kyc_rejected', '/user/kyc_success'] },
                { href: '/user/profile', icon: 'fa-user-tie', label: 'My Profile', match: ['/user/profile'] },
                { href: '/user/settings', icon: 'fa-lock', label: 'Security & Settings', match: ['/user/settings', '/user/security', '/user/fraud_detection', '/user/webhooks_config'] },
                { href: '/user/notifications', icon: 'fa-bell', label: 'Notifications', match: ['/user/notifications', '/user/alerts'] },
                { href: '/user/contact', icon: 'fa-headset', label: '24/7 Concierge', match: ['/user/contact', '/user/support'] }
            ]
        }
    ];

    const state = {
        user: null,
        accounts: [],
        primaryAccount: null,
        totalBalance: 0,
        masked: localStorage.getItem('fb_balance_masked') === '1',
        ready: false
    };

    function getAuthHeaders(extra = {}) {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        const headers = Object.assign({ 'Accept': 'application/json' }, extra);
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }

    async function api(url, options = {}) {
        const opts = Object.assign({ credentials: 'include' }, options);
        opts.headers = getAuthHeaders(options.headers || {});
        if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(opts.body);
        }
        const response = await fetch(url, opts);
        let data = null;
        const ctype = response.headers.get('content-type') || '';
        if (ctype.includes('application/json')) {
            try { data = await response.json(); } catch (_) { data = null; }
        }
        if (response.status === 401) {
            window.location.href = '/signin';
            throw new Error('Session expired. Redirecting to sign in...');
        }
        if (!response.ok) {
            const msg = (data && (data.detail || data.message || data.error)) || `Request failed (HTTP ${response.status})`;
            throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        }
        return data;
    }

    function fmt(amount, currency = 'USD', ignoreMask = false) {
        if (state.masked && !ignoreMask) return '••••••';
        const num = Number(amount || 0);
        try {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency || 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(num);
        } catch (_) {
            return `$${num.toFixed(2)}`;
        }
    }

    function fmtDate(isoStr, includeTime = false) {
        if (!isoStr) return '—';
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return String(isoStr);
        const opts = { year: 'numeric', month: 'short', day: 'numeric' };
        if (includeTime) {
            opts.hour = '2-digit';
            opts.minute = '2-digit';
        }
        return d.toLocaleDateString('en-US', opts);
    }

    function toast(message, type = 'success') {
        let container = document.getElementById('fb-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'fb-toast-container';
            document.body.appendChild(container);
        }
        const icons = {
            success: 'fa-circle-check text-success',
            error: 'fa-circle-exclamation text-danger',
            warning: 'fa-triangle-exclamation text-warning',
            info: 'fa-circle-info text-info'
        };
        const el = document.createElement('div');
        el.className = `fb-toast toast-${type}`;
        el.innerHTML = `
            <i class="fas ${icons[type] || icons.info} mt-1"></i>
            <div style="flex:1;font-size:0.84rem;line-height:1.4;">${message}</div>
            <button type="button" style="background:none;border:none;color:#94a3b8;cursor:pointer;padding:0;" onclick="this.parentElement.remove()">
                <i class="fas fa-xmark"></i>
            </button>
        `;
        container.appendChild(el);
        setTimeout(() => { if (el && el.parentNode) el.remove(); }, 4500);
    }

    function copyText(text, label = 'Value') {
        if (!text) return;
        navigator.clipboard.writeText(String(text)).then(() => {
            toast(`${label} copied to clipboard`, 'info');
        }).catch(() => {
            toast(`Copied: ${text}`, 'info');
        });
    }

    function buildShellDOM() {
        const pageContent = document.getElementById('bank-page-content');
        if (!pageContent || document.querySelector('.fb-app-shell')) return;

        const pageTitle = document.body.dataset.pageTitle || document.title.replace(' - Finanza Bank', '') || 'Online Banking';
        const pageSubtitle = document.body.dataset.pageSubtitle || 'Finanza Private & Commercial Digital Banking';
        const currentPath = window.location.pathname.replace(/\.html$/, '');

        const navHtml = NAV_SECTIONS.map(sec => `
            <div class="fb-nav-section">
                <div class="fb-nav-section-title">${sec.title}</div>
                ${sec.items.map(item => {
                    const isActive = item.match.some(m => currentPath === m || currentPath.startsWith(m + '/'));
                    return `
                        <a href="${item.href}" class="fb-nav-link ${isActive ? 'active' : ''}">
                            <i class="fas ${item.icon}"></i>
                            <span>${item.label}</span>
                        </a>
                    `;
                }).join('')}
            </div>
        `).join('');

        const shell = document.createElement('div');
        shell.className = 'fb-app-shell';
        shell.innerHTML = `
            <div class="fb-sidebar-backdrop" id="fbSidebarBackdrop"></div>
            <aside class="fb-sidebar" id="fbSidebar" aria-label="Banking Navigation">
                <div class="fb-sidebar-brand">
                    <a href="/user/dashboard" class="fb-brand-logo">
                        <span class="fb-brand-icon"><i class="fas fa-landmark"></i></span>
                        <span>Finanza</span>
                    </a>
                    <span class="fb-brand-tag">Private Bank</span>
                </div>
                <nav class="fb-sidebar-nav">
                    ${navHtml}
                </nav>
                <div class="fb-sidebar-footer">
                    <div class="fb-sidebar-user">
                        <div class="fb-user-avatar" id="fbSidebarAvatar">FB</div>
                        <div class="fb-user-meta">
                            <div class="fb-user-name" id="fbSidebarName">Loading...</div>
                            <div class="fb-user-email" id="fbSidebarEmail">—</div>
                        </div>
                        <a href="/user/logout" title="Sign Out" class="text-secondary ms-1" style="text-decoration:none;">
                            <i class="fas fa-right-from-bracket"></i>
                        </a>
                    </div>
                </div>
            </aside>

            <div class="fb-main">
                <header class="fb-topbar">
                    <div class="fb-topbar-left">
                        <button type="button" class="fb-mobile-toggle" id="fbMobileMenuBtn" aria-label="Toggle Menu">
                            <i class="fas fa-bars"></i>
                        </button>
                        <h1 class="fb-page-title">${pageTitle}</h1>
                        <span class="fb-page-subtitle">${pageSubtitle}</span>
                    </div>

                    <div class="fb-topbar-right">
                        <!-- Primary Account Number Pill -->
                        <div class="fb-header-pill hide-mobile" id="fbHeaderAccountPill" title="Primary Account Number">
                            <span class="pill-label">Acct</span>
                            <span class="font-mono" id="fbHeaderAcctNum">••••••••••</span>
                            <button type="button" class="pill-action" id="fbCopyAcctBtn" title="Copy Account Number">
                                <i class="far fa-copy"></i>
                            </button>
                        </div>

                        <!-- Total Balance Pill -->
                        <div class="fb-header-pill" title="Total Available Balance">
                            <span class="pill-label hide-mobile">Balance</span>
                            <span class="tabular-nums fw-bold text-primary" id="fbHeaderBalance">$0.00</span>
                            <button type="button" class="pill-action" id="fbToggleMaskBtn" title="Show/Hide Balances">
                                <i class="far ${state.masked ? 'fa-eye-slash' : 'fa-eye'}" id="fbMaskIcon"></i>
                            </button>
                        </div>

                        <!-- Global + Add Money Button -->
                        <button type="button" class="btn btn-emerald btn-sm d-inline-flex align-items-center gap-2" onclick="FinanzaShell.openAddMoneyModal()">
                            <i class="fas fa-plus-circle"></i>
                            <span class="hide-mobile">Add Money</span>
                        </button>

                        <!-- KYC Status Badge -->
                        <a href="/user/kyc" class="fb-badge fb-badge-neutral text-decoration-none hide-mobile" id="fbHeaderKycBadge">
                            <i class="fas fa-shield-halved"></i>
                            <span>KYC</span>
                        </a>

                        <!-- Notifications Bell -->
                        <a href="/user/notifications" class="fb-icon-btn" title="Notifications & Alerts">
                            <i class="far fa-bell"></i>
                            <span class="fb-notif-dot" id="fbHeaderNotifCount" style="display:none;">0</span>
                        </a>

                        <!-- Profile Link -->
                        <a href="/user/profile" class="fb-icon-btn hide-mobile" title="Profile & Settings">
                            <i class="far fa-user"></i>
                        </a>
                    </div>
                </header>

                <main class="fb-workspace" id="fbWorkspaceMount"></main>
            </div>

            <!-- Mobile Bottom Navigation -->
            <nav class="fb-mobile-bottom-bar" aria-label="Mobile Navigation">
                <a href="/user/dashboard" class="fb-mobile-nav-item ${currentPath === '/user/dashboard' ? 'active' : ''}">
                    <i class="fas fa-chart-pie"></i><span>Home</span>
                </a>
                <a href="/user/transfers" class="fb-mobile-nav-item ${currentPath.includes('transfer') ? 'active' : ''}">
                    <i class="fas fa-paper-plane"></i><span>Transfer</span>
                </a>
                <a href="#" onclick="FinanzaShell.openAddMoneyModal();return false;" class="fb-mobile-nav-item" style="color:var(--fb-emerald);">
                    <i class="fas fa-circle-plus"></i><span>Add Money</span>
                </a>
                <a href="/user/cards" class="fb-mobile-nav-item ${currentPath.includes('cards') ? 'active' : ''}">
                    <i class="fas fa-credit-card"></i><span>Cards</span>
                </a>
                <a href="/user/transactions" class="fb-mobile-nav-item ${currentPath.includes('transactions') ? 'active' : ''}">
                    <i class="fas fa-list-check"></i><span>Activity</span>
                </a>
            </nav>
        `;

        document.body.prepend(shell);
        const mount = document.getElementById('fbWorkspaceMount');
        mount.appendChild(pageContent);
        pageContent.style.display = 'block';

        // Inject Global Modals (Add Money Modal + Printable Receipt Modal)
        injectGlobalModals();

        // Bind events
        const mobileBtn = document.getElementById('fbMobileMenuBtn');
        const sidebar = document.getElementById('fbSidebar');
        const backdrop = document.getElementById('fbSidebarBackdrop');
        if (mobileBtn) {
            mobileBtn.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                backdrop.classList.toggle('open');
            });
        }
        if (backdrop) {
            backdrop.addEventListener('click', () => {
                sidebar.classList.remove('open');
                backdrop.classList.remove('open');
            });
        }

        const maskBtn = document.getElementById('fbToggleMaskBtn');
        if (maskBtn) {
            maskBtn.addEventListener('click', () => {
                state.masked = !state.masked;
                localStorage.setItem('fb_balance_masked', state.masked ? '1' : '0');
                const icon = document.getElementById('fbMaskIcon');
                if (icon) icon.className = `far ${state.masked ? 'fa-eye-slash' : 'fa-eye'}`;
                updateHeaderUI();
                window.dispatchEvent(new CustomEvent('finanza:mask-changed', { detail: { masked: state.masked } }));
            });
        }

        const copyAcctBtn = document.getElementById('fbCopyAcctBtn');
        if (copyAcctBtn) {
            copyAcctBtn.addEventListener('click', () => {
                const acct = state.primaryAccount ? state.primaryAccount.account_number : (state.user && state.user.account_number);
                if (acct) copyText(acct, 'Account Number');
            });
        }
    }

    function injectGlobalModals() {
        const modalWrap = document.createElement('div');
        modalWrap.innerHTML = `
            <!-- GLOBAL ADD / DEPOSIT MONEY MODAL -->
            <div class="modal fade" id="fbAddMoneyModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg" style="border-radius:16px;">
                        <div class="modal-header border-bottom px-4 py-3">
                            <div>
                                <h5 class="modal-title fw-bold mb-0"><i class="fas fa-circle-plus text-success me-2"></i>Add / Deposit Money</h5>
                                <small class="text-muted">Fund your Finanza account via Payment Gateway, Mobile Check, or Direct Wire/ACH</small>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-4">
                            <div class="fb-tabs mb-4 w-100 justify-content-start">
                                <button type="button" class="fb-tab-btn active" onclick="FinanzaShell.switchAddMoneyTab('gateway', this)">
                                    <i class="fas fa-bolt"></i> Payment Gateway
                                </button>
                                <button type="button" class="fb-tab-btn" onclick="FinanzaShell.switchAddMoneyTab('check', this)">
                                    <i class="fas fa-money-check-dollar"></i> Mobile Check Deposit
                                </button>
                                <button type="button" class="fb-tab-btn" onclick="FinanzaShell.switchAddMoneyTab('wire', this)">
                                    <i class="fas fa-building-columns"></i> Wire / Direct Deposit Info
                                </button>
                            </div>

                            <!-- Tab 1: Payment Gateway Deposit -->
                            <div id="fbAddTab-gateway">
                                <form id="fbGatewayFundForm">
                                    <div class="row g-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Amount (USD)</label>
                                            <div class="input-group">
                                                <span class="input-group-text">$</span>
                                                <input type="number" class="form-control" id="fbFundAmount" min="10" step="0.01" placeholder="500.00" required>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Payment Gateway Rail</label>
                                            <select class="form-select" id="fbFundGatewayProvider">
                                                <option value="stripe">Stripe (Card / Apple Pay / ACH)</option>
                                                <option value="paystack">Paystack (Card / Instant Bank Transfer)</option>
                                                <option value="flutterwave">Flutterwave</option>
                                                <option value="adyen">Adyen</option>
                                            </select>
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label">Reference Note (Optional)</label>
                                            <input type="text" class="form-control" id="fbFundNotes" placeholder="e.g., Personal Checking Top-Up">
                                        </div>
                                    </div>
                                    <div class="alert alert-light border mt-3 mb-0 small text-secondary">
                                        <i class="fas fa-shield-halved text-primary me-1"></i>
                                        <strong>Settlement Protection:</strong> External gateway deposits initiate a verified payment session. Your ledger balance updates automatically as soon as the payment gateway confirms settlement via signed webhook.
                                    </div>
                                    <div class="d-flex justify-content-end gap-2 mt-4">
                                        <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
                                        <button type="submit" class="btn btn-emerald" id="fbGatewayFundBtn">
                                            <i class="fas fa-lock me-1"></i> Proceed to Deposit
                                        </button>
                                    </div>
                                </form>
                            </div>

                            <!-- Tab 2: Mobile Check Deposit -->
                            <div id="fbAddTab-check" style="display:none;">
                                <form id="fbCheckDepositForm">
                                    <div class="row g-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Check Amount (USD)</label>
                                            <div class="input-group">
                                                <span class="input-group-text">$</span>
                                                <input type="number" class="form-control" id="fbCheckAmount" min="1" step="0.01" placeholder="1250.00" required>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Check Number</label>
                                            <input type="text" class="form-control font-mono" id="fbCheckNumber" placeholder="1042" required>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Front of Check (Photo/Scan)</label>
                                            <input type="file" class="form-control" accept="image/*,.pdf">
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Back of Check (Endorsed)</label>
                                            <input type="file" class="form-control" accept="image/*,.pdf">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label">Memo / Payor Name</label>
                                            <input type="text" class="form-control" id="fbCheckMemo" placeholder="e.g., Payroll Check — Acme Corp">
                                        </div>
                                    </div>
                                    <div class="d-flex justify-content-end gap-2 mt-4">
                                        <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
                                        <button type="submit" class="btn btn-primary" id="fbCheckSubmitBtn">
                                            <i class="fas fa-upload me-1"></i> Submit Check for Clearing
                                        </button>
                                    </div>
                                </form>
                            </div>

                            <!-- Tab 3: Direct Deposit / ACH & Wire Instructions -->
                            <div id="fbAddTab-wire" style="display:none;">
                                <div class="p-3 rounded-3 bg-light border mb-3">
                                    <div class="row g-3">
                                        <div class="col-md-6">
                                            <small class="text-muted d-block">Beneficiary Bank</small>
                                            <div class="fw-bold">Finanza Bank, N.A.</div>
                                        </div>
                                        <div class="col-md-6">
                                            <small class="text-muted d-block">Account Holder Name</small>
                                            <div class="fw-bold" id="fbWireHolderName">—</div>
                                        </div>
                                        <div class="col-md-4">
                                            <small class="text-muted d-block">Account Number</small>
                                            <div class="d-flex align-items-center gap-2">
                                                <code class="bank-code fw-bold text-primary fs-6" id="fbWireAcctNum">—</code>
                                                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="FinanzaShell.copyText(document.getElementById('fbWireAcctNum').textContent, 'Account Number')">
                                                    <i class="far fa-copy"></i>
                                                </button>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <small class="text-muted d-block">ACH / ABA Routing Number</small>
                                            <div class="d-flex align-items-center gap-2">
                                                <code class="bank-code fw-bold fs-6" id="fbWireRouting">021000021</code>
                                                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="FinanzaShell.copyText('021000021', 'Routing Number')">
                                                    <i class="far fa-copy"></i>
                                                </button>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <small class="text-muted d-block">International SWIFT / BIC</small>
                                            <div class="d-flex align-items-center gap-2">
                                                <code class="bank-code fw-bold fs-6">FNZAUS33XXX</code>
                                                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="FinanzaShell.copyText('FNZAUS33XXX', 'SWIFT Code')">
                                                    <i class="far fa-copy"></i>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="small text-muted">
                                    Use these coordinates to receive payroll direct deposits, domestic ACH/Fedwire transfers, or international SWIFT wires directly into your Finanza Checking account.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- GLOBAL PRINTABLE TRANSACTION RECEIPT MODAL -->
            <div class="modal fade" id="fbReceiptModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg" style="border-radius:16px;">
                        <div class="modal-header border-bottom px-4 py-3">
                            <h5 class="modal-title fw-bold mb-0"><i class="fas fa-receipt text-primary me-2"></i>Official Transaction Receipt</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-4" id="fbReceiptBody"></div>
                        <div class="modal-footer border-top px-4 py-3">
                            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="window.print()">
                                <i class="fas fa-print me-1"></i> Print / Save PDF
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalWrap);

        // Bind Gateway Fund Form
        const gwForm = document.getElementById('fbGatewayFundForm');
        if (gwForm) {
            gwForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('fbGatewayFundBtn');
                const orig = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Initializing...';
                try {
                    const amount = parseFloat(document.getElementById('fbFundAmount').value);
                    const provider = document.getElementById('fbFundGatewayProvider').value;
                    const notes = document.getElementById('fbFundNotes').value;
                    const res = await api('/api/user/accounts/fund', {
                        method: 'POST',
                        body: { amount, method: 'payment_gateway', provider, notes }
                    });
                    toast(res.message || 'Deposit session created.', 'success');
                    const modalEl = document.getElementById('fbAddMoneyModal');
                    if (window.bootstrap && bootstrap.Modal.getInstance(modalEl)) {
                        bootstrap.Modal.getInstance(modalEl).hide();
                    }
                    gwForm.reset();
                    await refreshUserContext();
                } catch (err) {
                    toast(err.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = orig;
                }
            });
        }

        // Bind Mobile Check Form
        const chkForm = document.getElementById('fbCheckDepositForm');
        if (chkForm) {
            chkForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('fbCheckSubmitBtn');
                const orig = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';
                try {
                    const amount = parseFloat(document.getElementById('fbCheckAmount').value);
                    const check_number = document.getElementById('fbCheckNumber').value;
                    const notes = document.getElementById('fbCheckMemo').value;
                    const res = await api('/api/user/accounts/fund', {
                        method: 'POST',
                        body: { amount, method: 'mobile_check', check_number, notes }
                    });
                    toast(res.message || 'Check submitted for clearing.', 'success');
                    const modalEl = document.getElementById('fbAddMoneyModal');
                    if (window.bootstrap && bootstrap.Modal.getInstance(modalEl)) {
                        bootstrap.Modal.getInstance(modalEl).hide();
                    }
                    chkForm.reset();
                    await refreshUserContext();
                } catch (err) {
                    toast(err.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = orig;
                }
            });
        }
    }

    function updateHeaderUI() {
        const u = state.user || {};
        const primary = state.primaryAccount || {};
        const acctNum = primary.account_number || u.account_number || '—';

        const nameEl = document.getElementById('fbSidebarName');
        const emailEl = document.getElementById('fbSidebarEmail');
        const avatarEl = document.getElementById('fbSidebarAvatar');
        if (nameEl) nameEl.textContent = u.full_name || u.username || 'Client';
        if (emailEl) emailEl.textContent = u.email || '';
        if (avatarEl) {
            if (u.profile_picture_url || u.avatar_url) {
                avatarEl.innerHTML = `<img src="${u.profile_picture_url || u.avatar_url}" alt="Avatar" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            } else {
                const initials = (u.full_name || u.email || 'FB').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
                avatarEl.textContent = initials;
            }
        }

        const acctNumEl = document.getElementById('fbHeaderAcctNum');
        if (acctNumEl) {
            acctNumEl.textContent = state.masked && acctNum.length > 4
                ? `••••${acctNum.slice(-4)}`
                : acctNum;
        }

        const balEl = document.getElementById('fbHeaderBalance');
        if (balEl) {
            balEl.textContent = fmt(state.totalBalance, 'USD');
        }

        const kycEl = document.getElementById('fbHeaderKycBadge');
        if (kycEl) {
            const kstatus = (u.kyc_status || (u.is_verified ? 'approved' : 'unverified')).toLowerCase();
            if (kstatus === 'approved' || kstatus === 'verified' || u.is_verified) {
                kycEl.className = 'fb-badge fb-badge-success text-decoration-none hide-mobile';
                kycEl.innerHTML = '<i class="fas fa-circle-check"></i><span>KYC Verified</span>';
            } else if (kstatus === 'pending' || kstatus === 'submitted') {
                kycEl.className = 'fb-badge fb-badge-warning text-decoration-none hide-mobile';
                kycEl.innerHTML = '<i class="fas fa-clock"></i><span>KYC Pending</span>';
            } else {
                kycEl.className = 'fb-badge fb-badge-danger text-decoration-none hide-mobile';
                kycEl.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>Verify ID</span>';
            }
        }

        const wireHolder = document.getElementById('fbWireHolderName');
        const wireAcct = document.getElementById('fbWireAcctNum');
        if (wireHolder) wireHolder.textContent = u.full_name || u.email || 'Account Holder';
        if (wireAcct) wireAcct.textContent = acctNum;
    }

    async function refreshUserContext() {
        try {
            const [profileRes, accountsRes, notifsRes] = await Promise.allSettled([
                api('/api/user/profile'),
                api('/api/user/accounts'),
                api('/api/user/notifications')
            ]);

            if (profileRes.status === 'fulfilled' && profileRes.value) {
                state.user = profileRes.value;
            }
            if (accountsRes.status === 'fulfilled' && accountsRes.value) {
                const list = Array.isArray(accountsRes.value)
                    ? accountsRes.value
                    : (accountsRes.value.accounts || []);
                state.accounts = list;
                state.primaryAccount = list[0] || null;
                state.totalBalance = list.reduce((sum, a) => sum + Number(a.balance || 0), 0);
            } else if (state.user && state.user.account_balance !== undefined) {
                state.totalBalance = Number(state.user.account_balance || 0);
            }

            if (notifsRes.status === 'fulfilled' && Array.isArray(notifsRes.value)) {
                const unread = notifsRes.value.filter(n => !n.is_read).length;
                const dot = document.getElementById('fbHeaderNotifCount');
                if (dot) {
                    if (unread > 0) {
                        dot.textContent = unread > 99 ? '99+' : String(unread);
                        dot.style.display = 'inline-flex';
                    } else {
                        dot.style.display = 'none';
                    }
                }
            }

            state.ready = true;
            updateHeaderUI();
            window.dispatchEvent(new CustomEvent('finanza:context-ready', { detail: state }));
            return state;
        } catch (err) {
            console.warn('[FinanzaShell] Failed to refresh user context:', err);
            return state;
        }
    }

    function openAddMoneyModal(defaultTab = 'gateway') {
        const modalEl = document.getElementById('fbAddMoneyModal');
        if (!modalEl) return;
        const buttons = modalEl.querySelectorAll('.fb-tab-btn');
        if (defaultTab === 'check' && buttons[1]) switchAddMoneyTab('check', buttons[1]);
        else if (defaultTab === 'wire' && buttons[2]) switchAddMoneyTab('wire', buttons[2]);
        else if (buttons[0]) switchAddMoneyTab('gateway', buttons[0]);

        if (window.bootstrap) {
            new bootstrap.Modal(modalEl).show();
        }
    }

    function switchAddMoneyTab(tab, btnEl) {
        ['gateway', 'check', 'wire'].forEach(t => {
            const pane = document.getElementById(`fbAddTab-${t}`);
            if (pane) pane.style.display = t === tab ? 'block' : 'none';
        });
        if (btnEl && btnEl.parentElement) {
            btnEl.parentElement.querySelectorAll('.fb-tab-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
        }
    }

    function showReceipt(txn) {
        const body = document.getElementById('fbReceiptBody');
        const modalEl = document.getElementById('fbReceiptModal');
        if (!body || !modalEl || !txn) return;

        const isCredit = (txn.direction || '').toLowerCase() === 'credit' ||
                         ['deposit', 'credit', 'transfer_received', 'loan_disbursement', 'investment_liquidation'].includes((txn.type || txn.transaction_type || '').toLowerCase());
        const status = (txn.status || 'completed').toLowerCase();
        const badgeCls = status === 'completed' ? 'fb-badge-success' : (status === 'pending' ? 'fb-badge-warning' : 'fb-badge-danger');

        body.innerHTML = `
            <div class="text-center pb-3 mb-3 border-bottom">
                <div class="d-inline-flex align-items-center justify-content-center rounded-circle mb-2" style="width:48px;height:48px;background:var(--fb-primary-soft);color:var(--fb-primary);">
                    <i class="fas fa-landmark fs-5"></i>
                </div>
                <div class="fw-bold">FINANZA BANK, N.A.</div>
                <div class="small text-muted">Official Electronic Ledger Receipt</div>
                <div class="fs-3 fw-extrabold mt-2 tabular-nums ${isCredit ? 'text-success' : 'text-dark'}">
                    ${isCredit ? '+' : '-'}${fmt(txn.amount, 'USD', true)}
                </div>
                <span class="fb-badge ${badgeCls} mt-1">${status.toUpperCase()}</span>
            </div>
            <div class="small">
                <div class="d-flex justify-content-between py-2 border-bottom">
                    <span class="text-muted">Reference Number</span>
                    <code class="bank-code fw-bold">${txn.reference_number || ('TXN-' + txn.id)}</code>
                </div>
                <div class="d-flex justify-content-between py-2 border-bottom">
                    <span class="text-muted">Date & Time</span>
                    <span class="fw-semibold">${fmtDate(txn.created_at || txn.date, true)}</span>
                </div>
                <div class="d-flex justify-content-between py-2 border-bottom">
                    <span class="text-muted">Transaction Type</span>
                    <span class="fw-semibold text-capitalize">${String(txn.transaction_type || txn.type || 'Transfer').replace(/_/g, ' ')}</span>
                </div>
                <div class="d-flex justify-content-between py-2 border-bottom">
                    <span class="text-muted">Entry Direction</span>
                    <span class="fw-semibold text-uppercase">${isCredit ? 'CREDIT (+)' : 'DEBIT (-)'}</span>
                </div>
                <div class="py-2">
                    <span class="text-muted d-block mb-1">Description / Counterparty</span>
                    <div class="fw-semibold p-2 rounded bg-light border">${txn.description || txn.recipient_name || 'Standard Ledger Entry'}</div>
                </div>
            </div>
        `;
        if (window.bootstrap) {
            new bootstrap.Modal(modalEl).show();
        }
    }

    // Initialize Shell as soon as DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        buildShellDOM();
        refreshUserContext();
    });

    window.FinanzaShell = {
        state,
        api,
        fmt,
        fmtDate,
        toast,
        copyText,
        refreshUserContext,
        openAddMoneyModal,
        switchAddMoneyTab,
        showReceipt
    };
})();
