/**
 * Finanza Admin — Unified Purple-Indigo Gradient Top Navbar & 29-Module Switcher
 * Preserves the signature #667eea -> #764ba2 Finanza Admin design across all 29 pages.
 */

window.navigateTo = window.navigateTo || function (url) {
    if (url) window.location.href = url;
};

(function () {
    const ADMIN_DIVISIONS = [
        {
            title: "Executive & Command",
            items: [
                { label: "Dashboard Hub", href: "/user/admin/dashboard", aliases: ["/user/admin", "/user/admin/", "/user/admin/dashboard", "/user/admin/admin_dashboard_hub"], icon: "fa-th-large" },
                { label: "System Monitoring", href: "/user/admin/monitoring", aliases: ["/user/admin/monitoring", "/user/admin/overview"], icon: "fa-heartbeat" },
                { label: "Admin Activity & Risk", href: "/user/admin/activity_dashboard", aliases: ["/user/admin/activity_dashboard"], icon: "fa-user-shield" },
                { label: "Super-Admin Control", href: "/user/admin/management_panel", aliases: ["/user/admin/management_panel"], icon: "fa-sliders-h" },
                { label: "Enterprise Reporting", href: "/user/admin/reporting", aliases: ["/user/admin/reporting", "/user/admin/reports"], icon: "fa-chart-bar" }
            ]
        },
        {
            title: "Customers & KYC",
            items: [
                { label: "User Management", href: "/user/admin/users", aliases: ["/user/admin/users", "/user/admin/admin_users.html"], icon: "fa-users" },
                { label: "Advanced Search", href: "/user/admin/advanced_search", aliases: ["/user/admin/advanced_search"], icon: "fa-search-plus" },
                { label: "Bulk Operations", href: "/user/admin/bulk_operations", aliases: ["/user/admin/bulk_operations"], icon: "fa-layer-group" },
                { label: "KYC Verification", href: "/user/admin/kyc", aliases: ["/user/admin/kyc", "/user/admin/submissions"], icon: "fa-id-card" }
            ]
        },
        {
            title: "Treasury, Fund & FX",
            items: [
                { label: "Fund & Adjust Balance", href: "/user/admin/fund", aliases: ["/user/admin/fund"], icon: "fa-coins" },
                { label: "Transactions Ledger", href: "/user/admin/transactions", aliases: ["/user/admin/transactions"], icon: "fa-exchange-alt" },
                { label: "Treasury & Portfolio", href: "/user/admin/treasury", aliases: ["/user/admin/treasury"], icon: "fa-landmark" },
                { label: "Currency Exchange (FX)", href: "/user/admin/currency_exchange", aliases: ["/user/admin/currency_exchange"], icon: "fa-globe" },
                { label: "Settlement & Clearing", href: "/user/admin/settlement", aliases: ["/user/admin/settlement"], icon: "fa-network-wired" }
            ]
        },
        {
            title: "Payment Rails",
            items: [
                { label: "ACH Management", href: "/user/admin/ach_management", aliases: ["/user/admin/ach_management"], icon: "fa-university" },
                { label: "Bill Pay Operations", href: "/user/admin/bill_pay", aliases: ["/user/admin/bill_pay"], icon: "fa-file-invoice-dollar" },
                { label: "Mobile Check Deposit", href: "/user/admin/mobile_deposit", aliases: ["/user/admin/mobile_deposit"], icon: "fa-camera" },
                { label: "Blockchain & Crypto", href: "/user/admin/blockchain", aliases: ["/user/admin/blockchain"], icon: "fa-link" }
            ]
        },
        {
            title: "Lending & Compliance",
            items: [
                { label: "Loan Origination", href: "/user/admin/lending", aliases: ["/user/admin/lending"], icon: "fa-hand-holding-usd" },
                { label: "Lending Compliance", href: "/user/admin/lending_compliance", aliases: ["/user/admin/lending_compliance"], icon: "fa-balance-scale" },
                { label: "HMDA Regulatory LAR", href: "/user/admin/hmda", aliases: ["/user/admin/hmda"], icon: "fa-home" },
                { label: "Fraud Detection", href: "/user/admin/fraud_detection", aliases: ["/user/admin/fraud_detection"], icon: "fa-crosshairs" },
                { label: "International & OFAC", href: "/user/admin/international_compliance", aliases: ["/user/admin/international_compliance", "/user/admin/compliance"], icon: "fa-passport" }
            ]
        },
        {
            title: "Gateways & System",
            items: [
                { label: "Bank & Gateways", href: "/user/admin/bank_connect", aliases: ["/user/admin/bank_connect", "/user/admin/bank-connect"], icon: "fa-plug" },
                { label: "Vendor Integration Hub", href: "/user/admin/vendor_hub", aliases: ["/user/admin/vendor_hub", "/user/admin/vendor-hub"], icon: "fa-cubes" },
                { label: "Webhooks Manager", href: "/user/admin/webhooks", aliases: ["/user/admin/webhooks"], icon: "fa-broadcast-tower" },
                { label: "Admin MFA Security", href: "/user/admin/mfa_setup", aliases: ["/user/admin/mfa_setup", "/user/admin/admin_mfa_setup"], icon: "fa-key" },
                { label: "Admin Profile", href: "/user/admin/profile", aliases: ["/user/admin/profile"], icon: "fa-user-tie" },
                { label: "System Settings", href: "/user/admin/settings", aliases: ["/user/admin/settings"], icon: "fa-cogs" }
            ]
        }
    ];

    function normalizePath(p) {
        if (!p) return "";
        return p.replace(/\/+$/, "").replace(/-/g, "_") || "/user/admin/dashboard";
    }

    function mountAdminNavbar() {
        if (document.getElementById("finanzaUnifiedAdminNav")) return;
        document.body.classList.add("finanza-admin-shell-ready");

        const currentPath = normalizePath(window.location.pathname);

        let megaColsHtml = "";
        ADMIN_DIVISIONS.forEach(div => {
            let itemsHtml = "";
            div.items.forEach(item => {
                const isMatch = item.aliases.some(a => normalizePath(a) === currentPath);
                itemsHtml += `
                    <a href="${item.href}" class="adm-mega-item ${isMatch ? "active" : ""}" data-search="${item.label.toLowerCase()} ${div.title.toLowerCase()}">
                        <i class="fas ${item.icon}"></i>
                        <span>${item.label}</span>
                    </a>
                `;
            });
            megaColsHtml += `
                <div class="adm-mega-col">
                    <div class="adm-mega-col-title">${div.title}</div>
                    ${itemsHtml}
                </div>
            `;
        });

        const isActive = (paths) => paths.some(p => normalizePath(p) === currentPath) ? "active" : "";

        const nav = document.createElement("nav");
        nav.id = "finanzaUnifiedAdminNav";
        nav.className = "navbar navbar-expand-lg navbar-dark";
        nav.innerHTML = `
            <div class="adm-nav-container">
                <a class="adm-brand" href="/user/admin/dashboard">
                    <span class="adm-brand-icon"><i class="fas fa-university"></i></span>
                    <span>Finanza Admin</span>
                </a>

                <div class="adm-links">
                    <a href="/user/admin/dashboard" class="adm-link ${isActive(['/user/admin', '/user/admin/dashboard'])}">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a href="/user/admin/users" class="adm-link ${isActive(['/user/admin/users'])}">
                        <i class="fas fa-users"></i> Users
                    </a>
                    <a href="/user/admin/kyc" class="adm-link ${isActive(['/user/admin/kyc'])}">
                        <i class="fas fa-id-card"></i> KYC
                        <span class="adm-kyc-pill" id="admNavKycBadge" style="display:none;">0</span>
                    </a>
                    <a href="/user/admin/fund" class="adm-link ${isActive(['/user/admin/fund'])}">
                        <i class="fas fa-coins"></i> Fund / Adjust
                    </a>
                    <a href="/user/admin/transactions" class="adm-link ${isActive(['/user/admin/transactions'])}">
                        <i class="fas fa-exchange-alt"></i> Transactions
                    </a>
                    <a href="/user/admin/bank_connect" class="adm-link ${isActive(['/user/admin/bank_connect'])}">
                        <i class="fas fa-plug"></i> Gateways
                    </a>
                    <a href="/user/admin/vendor_hub" class="adm-link ${isActive(['/user/admin/vendor_hub'])}">
                        <i class="fas fa-cubes"></i> Vendor Hub
                    </a>

                    <div class="adm-mega-wrap" id="admMegaWrap">
                        <button type="button" class="adm-link" id="admMegaToggleBtn">
                            <i class="fas fa-th"></i> All 29 Modules <i class="fas fa-chevron-down" style="font-size:0.75rem;"></i>
                        </button>
                        <div class="adm-mega-menu" id="admMegaMenu">
                            <div class="adm-mega-header">
                                <div class="adm-mega-search">
                                    <i class="fas fa-search"></i>
                                    <input type="text" id="admMegaSearchInput" placeholder="Filter all 29 admin modules (e.g. ACH, Lending, HMDA, MFA, FX)..." autocomplete="off">
                                </div>
                                <span class="badge bg-primary" style="background:linear-gradient(135deg,#667eea,#764ba2)!important;padding:7px 11px;">29 Modules</span>
                            </div>
                            <div class="adm-mega-grid" id="admMegaGrid">
                                ${megaColsHtml}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="adm-right-controls">
                    <a href="/user/dashboard" class="adm-pill-btn" title="Open Client Portal">
                        <i class="fas fa-external-link-alt"></i> Client View
                    </a>
                    <a href="/logout" class="adm-pill-btn logout" title="Sign Out">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        `;

        document.body.prepend(nav);

        // Toggle All 29 Modules dropdown
        const wrap = document.getElementById("admMegaWrap");
        const btn = document.getElementById("admMegaToggleBtn");
        const searchInput = document.getElementById("admMegaSearchInput");

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            wrap.classList.toggle("open");
            if (wrap.classList.contains("open") && searchInput) {
                setTimeout(() => searchInput.focus(), 50);
            }
        });

        document.addEventListener("click", function (e) {
            if (!wrap.contains(e.target)) {
                wrap.classList.remove("open");
            }
        });

        if (searchInput) {
            searchInput.addEventListener("input", function () {
                const q = this.value.trim().toLowerCase();
                const items = wrap.querySelectorAll(".adm-mega-item");
                items.forEach(el => {
                    const hay = el.getAttribute("data-search") || "";
                    el.style.display = (!q || hay.includes(q)) ? "flex" : "none";
                });
            });
        }

        // Populate live KYC pending count
        fetch("/api/admin/metrics", { credentials: "include" })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                const pendingKyc = data.pending_kyc || (data.data && data.data.pending_kyc) || 0;
                const badge = document.getElementById("admNavKycBadge");
                if (badge && pendingKyc > 0) {
                    badge.textContent = pendingKyc;
                    badge.style.display = "inline-block";
                }
            })
            .catch(() => {});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mountAdminNavbar);
    } else {
        mountAdminNavbar();
    }
})();
