/**
 * Finanza Admin — Unified Purple-Indigo Gradient Top Navbar, Role Privileges Matrix Modal,
 * 29-Module Switcher, and Android/Mobile Slide-Over Drawer + Bottom Navigation Bar.
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

    const MODULE_LABELS = {
        "/user/admin/dashboard": "Dashboard Hub",
        "/user/admin/monitoring": "System Monitoring",
        "/user/admin/activity_dashboard": "Admin Activity & Risk",
        "/user/admin/management_panel": "Admin & Roles Control",
        "/user/admin/reporting": "Enterprise Reporting",
        "/user/admin/users": "User Management",
        "/user/admin/advanced_search": "Advanced Search",
        "/user/admin/bulk_operations": "Bulk Operations",
        "/user/admin/kyc": "KYC Verification",
        "/user/admin/fund": "Fund & Adjust Balance",
        "/user/admin/transactions": "Transactions Ledger",
        "/user/admin/treasury": "Treasury & Portfolio",
        "/user/admin/currency_exchange": "Currency Exchange (FX)",
        "/user/admin/settlement": "Settlement & Clearing",
        "/user/admin/ach_management": "ACH Management",
        "/user/admin/bill_pay": "Bill Pay Operations",
        "/user/admin/mobile_deposit": "Mobile Check Deposit",
        "/user/admin/blockchain": "Blockchain & Crypto",
        "/user/admin/lending": "Loan Origination",
        "/user/admin/lending_compliance": "Lending Compliance",
        "/user/admin/hmda": "HMDA Regulatory LAR",
        "/user/admin/fraud_detection": "Fraud Detection",
        "/user/admin/international_compliance": "International & OFAC",
        "/user/admin/bank_connect": "Bank & Gateways",
        "/user/admin/vendor_hub": "Vendor Integration Hub",
        "/user/admin/webhooks": "Webhooks Manager",
        "/user/admin/mfa_setup": "Admin MFA Security",
        "/user/admin/profile": "Admin Profile",
        "/user/admin/settings": "System Settings"
    };

    const DEFAULT_ROLE_ACCOUNTS = {
        SUPER_ADMIN: "admin@admin.com",
        ADMIN: "admin@finanza.com",
        TREASURY: "treasury@finanza.com",
        COMPLIANCE: "compliance@finanza.com",
        SUPPORT: "support@finanza.com"
    };

    function normalizePath(p) {
        if (!p) return "";
        return p.replace(/\/+$/, "").replace(/-/g, "_") || "/user/admin/dashboard";
    }

    function formatPagePills(pages, isRestricted) {
        if (!pages || !pages.length) {
            return isRestricted
                ? '<span style="font-size:0.78rem;color:#16a34a;font-weight:600;"><i class="fas fa-unlock me-1"></i>None — Unrestricted Access to All 29 Modules</span>'
                : '';
        }
        if (pages.includes("*")) {
            return '<span style="background:#dcfce7;color:#166534;padding:3px 9px;border-radius:12px;font-size:0.76rem;font-weight:600;">All 29 Admin Modules (*)</span>';
        }
        return pages.map(p => {
            const norm = normalizePath(p);
            const label = MODULE_LABELS[norm] || norm.replace("/user/admin/", "");
            const bg = isRestricted ? "#fee2e2" : "#e0e7ff";
            const fg = isRestricted ? "#991b1b" : "#1e40af";
            const icon = isRestricted ? "fa-lock" : "fa-external-link-alt";
            return `<a href="${p}" style="display:inline-block;background:${bg};color:${fg};padding:2px 8px;border-radius:10px;font-size:0.74rem;font-weight:600;margin:2px;text-decoration:none;"><i class="fas ${icon} me-1" style="font-size:0.68rem;"></i>${label}</a>`;
        }).join("");
    }

    window.previewAdminRole = function (roleKey) {
        if (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.setPreviewRole) {
            window.FinanzaAdminRBAC.setPreviewRole(roleKey);
            const roleEl = document.getElementById("admNavRoleBadge");
            const drawerRoleEl = document.getElementById("admDrawerRoleBadge");
            const active = window.FinanzaAdminRBAC.getRole();
            if (roleEl) roleEl.textContent = active;
            if (drawerRoleEl) drawerRoleEl.textContent = active;
            updateMegaMenuForRole();
            window.openAdminRolesMatrixModal();
        }
    };

    window.openAdminRolesMatrixModal = function () {
        let modal = document.getElementById("finanzaAdminRolesModal");
        const matrix = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRoleMatrix()) || window.DEFAULT_ROLE_MATRIX || {};
        const currentRole = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRole()) || localStorage.getItem("admin_role") || "SUPER_ADMIN";
        const actualRole = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getActualRole()) || currentRole;
        const isPreview = Boolean(window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getPreviewRole());

        if (!modal) {
            modal = document.createElement("div");
            modal.id = "finanzaAdminRolesModal";
            modal.style.cssText = "display:none;position:fixed;inset:0;background:rgba(15,23,42,0.72);z-index:99999;align-items:center;justify-content:center;padding:10px;backdrop-filter:blur(4px);";
            document.body.appendChild(modal);
        }

        const roleCardsHtml = Object.keys(matrix).map(roleKey => {
            const r = matrix[roleKey];
            const isCurrent = roleKey === currentRole;
            const defaultEmail = r.default_account || DEFAULT_ROLE_ACCOUNTS[roleKey] || "";
            const canList = (r.can_do || []).map(item => `<li style="margin-bottom:6px;color:#1e293b;font-size:0.84rem;"><i class="fas fa-check-circle text-success me-2"></i>${item}</li>`).join("");
            const cannotList = (r.cannot_do || []).map(item => `<li style="margin-bottom:6px;color:#64748b;font-size:0.83rem;"><i class="fas fa-times-circle text-danger me-2"></i>${item}</li>`).join("");
            const allowedPills = formatPagePills(r.allowed_pages || [], false);
            const restrictedPills = formatPagePills(r.restricted_pages || [], true);

            const actionBtns = [];
            if (actualRole === "SUPER_ADMIN") {
                if (!isCurrent) {
                    actionBtns.push(`<button type="button" onclick="window.previewAdminRole('${roleKey}')" style="background:#f1f5f9;border:1px solid #cbd5e1;color:#0f172a;padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;cursor:pointer;"><i class="fas fa-eye me-1"></i>Preview as ${roleKey}</button>`);
                } else if (isPreview) {
                    actionBtns.push(`<button type="button" onclick="window.previewAdminRole(null)" style="background:#fee2e2;border:1px solid #fca5a5;color:#991b1b;padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;cursor:pointer;"><i class="fas fa-undo me-1"></i>Restore SUPER_ADMIN</button>`);
                }
                actionBtns.push(`<a href="/user/admin/management_panel?role=${roleKey}" style="background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;text-decoration:none;"><i class="fas fa-user-cog me-1"></i>Assign / Manage</a>`);
            }

            return `
                <div style="border:${isCurrent ? '2px solid #667eea' : '1px solid #e2e8f0'};border-radius:12px;padding:14px;background:${isCurrent ? '#f8faff' : '#ffffff'};box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;">
                            <span style="background:${r.badge_color || '#667eea'};color:#fff;padding:4px 12px;border-radius:20px;font-size:0.76rem;font-weight:700;letter-spacing:0.5px;">${roleKey}</span>
                            <strong style="font-size:1rem;color:#0f172a;">${r.title || roleKey}</strong>
                            ${defaultEmail ? `<span style="background:#f1f5f9;color:#475569;padding:2px 8px;border-radius:6px;font-size:0.73rem;font-family:monospace;"><i class="fas fa-envelope me-1"></i>${defaultEmail}</span>` : ''}
                        </div>
                        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                            ${isCurrent ? `<span style="background:#667eea;color:#fff;padding:3px 10px;border-radius:6px;font-size:0.74rem;font-weight:600;"><i class="fas fa-user-check me-1"></i>${isPreview ? 'Previewing Role' : 'Your Active Role'}</span>` : ''}
                            ${actionBtns.join('')}
                        </div>
                    </div>
                    <p style="font-size:0.85rem;color:#475569;margin-bottom:12px;">${r.summary || ''}</p>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;">
                        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;">
                            <div style="font-weight:700;font-size:0.78rem;color:#166534;text-transform:uppercase;margin-bottom:8px;"><i class="fas fa-shield-alt me-1"></i>What ${roleKey} CAN Do</div>
                            <ul style="list-style:none;padding:0;margin:0;">${canList}</ul>
                        </div>
                        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;">
                            <div style="font-weight:700;font-size:0.78rem;color:#991b1b;text-transform:uppercase;margin-bottom:8px;"><i class="fas fa-ban me-1"></i>What ${roleKey} CANNOT Do</div>
                            <ul style="list-style:none;padding:0;margin:0;">${cannotList}</ul>
                        </div>
                    </div>
                    <div style="margin-top:12px;padding-top:10px;border-top:1px dashed #e2e8f0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;">
                        <div>
                            <div style="font-size:0.73rem;font-weight:700;color:#1e40af;text-transform:uppercase;margin-bottom:4px;"><i class="fas fa-check me-1"></i>Allowed Modules</div>
                            <div>${allowedPills}</div>
                        </div>
                        <div>
                            <div style="font-size:0.73rem;font-weight:700;color:#991b1b;text-transform:uppercase;margin-bottom:4px;"><i class="fas fa-lock me-1"></i>Restricted Modules</div>
                            <div>${restrictedPills}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        modal.innerHTML = `
            <div style="background:#fff;border-radius:16px;max-width:1020px;width:100%;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,0.3);overflow:hidden;">
                <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;gap:10px;">
                    <div>
                        <h4 style="margin:0;font-weight:700;font-size:1.1rem;"><i class="fas fa-user-shield me-2"></i>Finanza Admin Roles & Privileges Matrix</h4>
                        <small style="opacity:0.9;font-size:0.78rem;">Complete breakdown of all 5 Administrator tiers — what each role can and cannot do</small>
                    </div>
                    <button type="button" onclick="document.getElementById('finanzaAdminRolesModal').style.display='none'" style="background:rgba(255,255,255,0.2);border:none;color:#fff;width:34px;height:34px;border-radius:50%;font-size:1.2rem;cursor:pointer;flex-shrink:0;">&times;</button>
                </div>
                <div style="padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:14px;-webkit-overflow-scrolling:touch;">
                    ${roleCardsHtml}
                </div>
                <div style="padding:12px 16px;background:#f8fafc;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                        <a href="/user/admin/management_panel" class="btn btn-sm btn-primary" style="background:linear-gradient(135deg,#667eea,#764ba2);border:none;color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;">
                            <i class="fas fa-sliders-h me-1"></i> Admin Management Panel
                        </a>
                        ${isPreview ? `<button type="button" onclick="window.previewAdminRole(null)" style="background:#ef4444;border:none;color:#fff;padding:7px 12px;border-radius:6px;font-weight:600;font-size:0.82rem;cursor:pointer;"><i class="fas fa-undo me-1"></i>Exit Role Preview</button>` : ''}
                    </div>
                    <button type="button" onclick="document.getElementById('finanzaAdminRolesModal').style.display='none'" style="background:#e2e8f0;border:none;color:#1e293b;padding:7px 16px;border-radius:6px;font-weight:600;font-size:0.82rem;cursor:pointer;">Close</button>
                </div>
            </div>
        `;
        modal.style.display = "flex";
    };

    function updateMegaMenuForRole() {
        const rbac = window.FinanzaAdminRBAC;
        if (!rbac || !rbac.canAccessPage) return;
        const role = rbac.getRole();
        document.querySelectorAll(".adm-mega-item").forEach(el => {
            const href = el.getAttribute("href");
            const allowed = rbac.canAccessPage(href, role);
            const lockBadge = el.querySelector(".adm-lock-icon");
            if (!allowed) {
                el.style.opacity = "0.55";
                el.title = `Restricted for ${role}`;
                if (!lockBadge) {
                    const i = document.createElement("i");
                    i.className = "fas fa-lock adm-lock-icon ms-auto text-danger";
                    i.style.fontSize = "0.72rem";
                    el.appendChild(i);
                }
            } else {
                el.style.opacity = "";
                el.title = "";
                if (lockBadge) lockBadge.remove();
            }
        });
    }

    window.toggleAdminMobileDrawer = function (forceState) {
        const drawer = document.getElementById("admMobileDrawer");
        const backdrop = document.getElementById("admMobileBackdrop");
        if (!drawer || !backdrop) return;
        const shouldOpen = typeof forceState === "boolean" ? forceState : !drawer.classList.contains("open");
        if (shouldOpen) {
            drawer.classList.add("open");
            backdrop.classList.add("open");
        } else {
            drawer.classList.remove("open");
            backdrop.classList.remove("open");
        }
    };

    function wrapAdminTablesForMobile() {
        document.querySelectorAll("table").forEach(tbl => {
            if (tbl.closest(".table-responsive") || tbl.closest(".adm-touch-table")) return;
            const wrapper = document.createElement("div");
            wrapper.className = "table-responsive adm-touch-table";
            if (tbl.parentNode) {
                tbl.parentNode.insertBefore(wrapper, tbl);
                wrapper.appendChild(tbl);
            }
        });
    }

    function mountAdminNavbar() {
        if (document.getElementById("finanzaUnifiedAdminNav")) return;
        document.body.classList.add("finanza-admin-shell-ready");

        const currentPath = normalizePath(window.location.pathname);

        let megaColsHtml = "";
        let drawerDivisionsHtml = "";
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
            drawerDivisionsHtml += `
                <div class="adm-drawer-div mb-3">
                    <div class="adm-mega-col-title">${div.title}</div>
                    ${itemsHtml}
                </div>
            `;
        });

        const isActive = (paths) => paths.some(p => normalizePath(p) === currentPath) ? "active" : "";
        const initialRole = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRole()) || localStorage.getItem("admin_role") || "SUPER_ADMIN";

        const nav = document.createElement("nav");
        nav.id = "finanzaUnifiedAdminNav";
        nav.className = "navbar navbar-expand-lg navbar-dark";
        nav.innerHTML = `
            <div class="adm-nav-container">
                <div class="adm-brand-group">
                    <button type="button" class="adm-mobile-hamburger" id="admMobileMenuBtn" onclick="window.toggleAdminMobileDrawer()" aria-label="Open Admin Menu">
                        <i class="fas fa-bars"></i>
                    </button>
                    <a class="adm-brand" href="/user/admin/dashboard">
                        <span class="adm-brand-icon"><i class="fas fa-university"></i></span>
                        <span>Finanza Admin</span>
                    </a>
                </div>

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
                    <a href="/user/dashboard" class="adm-pill-btn adm-hide-mobile" title="Open Client Portal">
                        <i class="fas fa-external-link-alt"></i> <span>Client View</span>
                    </a>
                    <a href="/logout" data-action="admin-logout" class="adm-pill-btn logout" title="Sign Out">
                        <i class="fas fa-sign-out-alt"></i> <span class="adm-hide-mobile">Logout</span>
                    </a>
                </div>
            </div>
        `;

        const mobileShell = document.createElement("div");
        mobileShell.innerHTML = `
            <div id="admMobileBackdrop" onclick="window.toggleAdminMobileDrawer(false)"></div>
            <aside id="admMobileDrawer" aria-label="Admin Mobile Navigation">
                <div class="adm-drawer-header">
                    <div class="d-flex align-items-center gap-2">
                        <span class="adm-brand-icon" style="width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.2);display:inline-flex;align-items:center;justify-content:center;"><i class="fas fa-university"></i></span>
                        <div>
                            <div class="fw-bold" style="font-size:0.96rem;line-height:1.1;">Finanza Admin</div>
                            <small style="font-size:0.72rem;opacity:0.88;">Role: <strong id="admDrawerRoleBadge">${initialRole}</strong></small>
                        </div>
                    </div>
                    <button type="button" onclick="window.toggleAdminMobileDrawer(false)" style="background:rgba(255,255,255,0.18);border:none;color:#fff;width:32px;height:32px;border-radius:8px;font-size:1.05rem;">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="p-2 border-bottom bg-light">
                    <div class="adm-mega-search">
                        <i class="fas fa-search"></i>
                        <input type="text" id="admDrawerSearchInput" placeholder="Search 29 admin modules..." autocomplete="off">
                    </div>
                </div>
                <div class="adm-drawer-body" id="admDrawerList">
                    ${drawerDivisionsHtml}
                </div>
                <div class="adm-drawer-footer">
                    <button type="button" onclick="window.toggleAdminMobileDrawer(false);window.openAdminRolesMatrixModal();" class="btn btn-sm btn-outline-primary flex-fill fw-semibold" style="font-size:0.76rem;">
                        <i class="fas fa-shield-alt me-1"></i>Role Matrix
                    </button>
                    <a href="/user/dashboard" class="btn btn-sm btn-outline-secondary flex-fill fw-semibold" style="font-size:0.76rem;">
                        <i class="fas fa-external-link-alt me-1"></i>Client View
                    </a>
                </div>
            </aside>

            <nav id="admMobileBottomNav" aria-label="Admin Quick Bottom Bar">
                <a href="/user/admin/dashboard" class="adm-bnav-item ${isActive(['/user/admin', '/user/admin/dashboard'])}">
                    <i class="fas fa-th-large"></i>
                    <span>Hub</span>
                </a>
                <a href="/user/admin/users" class="adm-bnav-item ${isActive(['/user/admin/users'])}">
                    <i class="fas fa-users"></i>
                    <span>Users</span>
                </a>
                <a href="/user/admin/kyc" class="adm-bnav-item ${isActive(['/user/admin/kyc'])}">
                    <i class="fas fa-id-card"></i>
                    <span>KYC</span>
                    <span class="adm-bnav-badge" id="admBottomKycBadge" style="display:none;">0</span>
                </a>
                <a href="/user/admin/lending" class="adm-bnav-item ${isActive(['/user/admin/lending', '/user/admin/lending_compliance', '/user/admin/hmda'])}">
                    <i class="fas fa-hand-holding-usd"></i>
                    <span>Lending</span>
                </a>
                <button type="button" class="adm-bnav-item" onclick="window.toggleAdminMobileDrawer()">
                    <i class="fas fa-bars"></i>
                    <span>All 29</span>
                </button>
            </nav>
        `;

        document.body.prepend(nav);
        document.body.appendChild(mobileShell);
        updateMegaMenuForRole();
        wrapAdminTablesForMobile();

        const obs = new MutationObserver(() => wrapAdminTablesForMobile());
        obs.observe(document.body, { childList: true, subtree: true });

        window.addEventListener("finanza:admin-ready", function (e) {
            const roleEl = document.getElementById("admNavRoleBadge");
            const drawerRoleEl = document.getElementById("admDrawerRoleBadge");
            const activeRole = (window.FinanzaAdminRBAC && window.FinanzaAdminRBAC.getRole()) || (e.detail && e.detail.admin_role);
            if (roleEl && activeRole) roleEl.textContent = activeRole;
            if (drawerRoleEl && activeRole) drawerRoleEl.textContent = activeRole;
            updateMegaMenuForRole();
        });

        window.addEventListener("finanza:role-changed", function (e) {
            const roleEl = document.getElementById("admNavRoleBadge");
            const drawerRoleEl = document.getElementById("admDrawerRoleBadge");
            if (e.detail && e.detail.role) {
                if (roleEl) roleEl.textContent = e.detail.role;
                if (drawerRoleEl) drawerRoleEl.textContent = e.detail.role;
            }
            updateMegaMenuForRole();
        });

        const wrap = document.getElementById("admMegaWrap");
        const btn = document.getElementById("admMegaToggleBtn");
        const searchInput = document.getElementById("admMegaSearchInput");
        const drawerSearchInput = document.getElementById("admDrawerSearchInput");

        if (btn && wrap) {
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
        }

        if (searchInput && wrap) {
            searchInput.addEventListener("input", function () {
                const q = this.value.trim().toLowerCase();
                wrap.querySelectorAll(".adm-mega-item").forEach(el => {
                    const hay = el.getAttribute("data-search") || "";
                    el.style.display = (!q || hay.includes(q)) ? "flex" : "none";
                });
            });
        }

        if (drawerSearchInput) {
            drawerSearchInput.addEventListener("input", function () {
                const q = this.value.trim().toLowerCase();
                document.querySelectorAll("#admDrawerList .adm-mega-item").forEach(el => {
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
                const bottomBadge = document.getElementById("admBottomKycBadge");
                if (badge && pendingKyc > 0) {
                    badge.textContent = pendingKyc;
                    badge.style.display = "inline-block";
                }
                if (bottomBadge && pendingKyc > 0) {
                    bottomBadge.textContent = pendingKyc;
                    bottomBadge.style.display = "inline-flex";
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
