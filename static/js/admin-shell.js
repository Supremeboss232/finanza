/**
 * Finanza Admin — Unified Purple-Indigo Gradient Top Navbar, Role Privileges Matrix Modal & 29-Module Switcher
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
                { label: "Admin & Roles Control", href: "/user/admin/management_panel", aliases: ["/user/admin/management_panel"], icon: "fa-sliders-h" },
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

    window.openAdminRolesMatrixModal = function () {
        let modal = document.getElementById("finanzaAdminRolesModal");
        const matrix = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRoleMatrix()) || window.DEFAULT_ROLE_MATRIX || {};
        const currentRole = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRole()) || localStorage.getItem("admin_role") || "SUPER_ADMIN";

        if (!modal) {
            modal = document.createElement("div");
            modal.id = "finanzaAdminRolesModal";
            modal.style.cssText = "display:none;position:fixed;inset:0;background:rgba(15,23,42,0.72);z-index:99999;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px);";
            document.body.appendChild(modal);
        }

        const roleCardsHtml = Object.keys(matrix).map(roleKey => {
            const r = matrix[roleKey];
            const isCurrent = roleKey === currentRole;
            const canList = (r.can_do || []).map(item => `<li style="margin-bottom:6px;color:#1e293b;font-size:0.86rem;"><i class="fas fa-check-circle text-success me-2"></i>${item}</li>`).join("");
            const cannotList = (r.cannot_do || []).map(item => `<li style="margin-bottom:6px;color:#64748b;font-size:0.85rem;"><i class="fas fa-times-circle text-danger me-2"></i>${item}</li>`).join("");

            return `
                <div style="border:${isCurrent ? '2px solid #667eea' : '1px solid #e2e8f0'};border-radius:12px;padding:18px;background:${isCurrent ? '#f8faff' : '#ffffff'};box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                        <div>
                            <span style="background:${r.badge_color || '#667eea'};color:#fff;padding:4px 12px;border-radius:20px;font-size:0.78rem;font-weight:700;letter-spacing:0.5px;">${roleKey}</span>
                            <strong style="font-size:1.05rem;color:#0f172a;margin-left:8px;">${r.title || roleKey}</strong>
                        </div>
                        ${isCurrent ? '<span style="background:#667eea;color:#fff;padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;"><i class="fas fa-user-check me-1"></i>Your Active Role</span>' : ''}
                    </div>
                    <p style="font-size:0.88rem;color:#475569;margin-bottom:12px;">${r.summary || ''}</p>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;">
                        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;">
                            <div style="font-weight:700;font-size:0.8rem;color:#166534;text-transform:uppercase;margin-bottom:8px;"><i class="fas fa-shield-alt me-1"></i>What ${roleKey} CAN Do</div>
                            <ul style="list-style:none;padding:0;margin:0;">${canList}</ul>
                        </div>
                        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;">
                            <div style="font-weight:700;font-size:0.8rem;color:#991b1b;text-transform:uppercase;margin-bottom:8px;"><i class="fas fa-ban me-1"></i>What ${roleKey} CANNOT Do</div>
                            <ul style="list-style:none;padding:0;margin:0;">${cannotList}</ul>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        modal.innerHTML = `
            <div style="background:#fff;border-radius:16px;max-width:980px;width:100%;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,0.3);overflow:hidden;">
                <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:20px 26px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h4 style="margin:0;font-weight:700;font-size:1.25rem;"><i class="fas fa-user-shield me-2"></i>Finanza Admin Roles & Privileges Matrix</h4>
                        <small style="opacity:0.9;">Complete breakdown of all 5 Administrator tiers — what each role can and cannot do</small>
                    </div>
                    <button type="button" onclick="document.getElementById('finanzaAdminRolesModal').style.display='none'" style="background:rgba(255,255,255,0.2);border:none;color:#fff;width:36px;height:36px;border-radius:50%;font-size:1.2rem;cursor:pointer;">&times;</button>
                </div>
                <div style="padding:22px 26px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;">
                    ${roleCardsHtml}
                </div>
                <div style="padding:14px 26px;background:#f8fafc;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;">
                    <a href="/user/admin/management_panel" class="btn btn-sm btn-primary" style="background:linear-gradient(135deg,#667eea,#764ba2);border:none;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:600;">
                        <i class="fas fa-sliders-h me-1"></i> Open Admin Management Panel
                    </a>
                    <button type="button" onclick="document.getElementById('finanzaAdminRolesModal').style.display='none'" style="background:#e2e8f0;border:none;color:#1e293b;padding:8px 18px;border-radius:6px;font-weight:600;cursor:pointer;">Close</button>
                </div>
            </div>
        `;
        modal.style.display = "flex";
    };

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
        const initialRole = localStorage.getItem("admin_role") || "SUPER_ADMIN";

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
                    <a href="/user/admin/management_panel" class="adm-link ${isActive(['/user/admin/management_panel'])}">
                        <i class="fas fa-user-shield"></i> Admins & Roles
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
                    <button type="button" class="adm-pill-btn" id="admRoleMatrixBtn" onclick="window.openAdminRolesMatrixModal()" title="View Admin Role Privileges (What Each Admin Can & Cannot Do)" style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.35);color:#fff;cursor:pointer;">
                        <i class="fas fa-shield-alt"></i> <span id="admNavRoleBadge">${initialRole}</span>
                    </button>
                    <a href="/user/dashboard" class="adm-pill-btn" title="Open Client Portal">
                        <i class="fas fa-external-link-alt"></i> Client View
                    </a>
                    <a href="/logout" data-action="admin-logout" class="adm-pill-btn logout" title="Sign Out">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        `;

        document.body.prepend(nav);

        window.addEventListener("finanza:admin-ready", function (e) {
            const roleEl = document.getElementById("admNavRoleBadge");
            if (roleEl && e.detail && e.detail.admin_role) {
                roleEl.textContent = e.detail.admin_role;
            }
        });

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
