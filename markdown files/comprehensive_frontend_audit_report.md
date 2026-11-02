# Comprehensive Frontend-to-Backend Audit Report

This automated audit scans all user and admin templates for broken CDNs, mismatched backend API paths, syntax/image errors, and XSS risks.

## ⚠️ Broken CDN Path Summary (nested /static/)
These links fail to load on user machines, breaking icons and Javascript interactions:

_None found._

## ❌ API Endpoint Mismatches (404/Silent Failures)
These client-side `fetch()` requests target routes that do not exist on the FastAPI backend:

_None found._

## 🖼️ Broken Image Assets / Empty Placeholders
Image files referencing blank, missing, or temporary source paths:

_None found._

## ⚡ Script Syntax Errors
HTML-inlined JavaScript compiler or runtime errors:

_None found._

## 🔒 XSS Vulnerability Gaps (Raw innerHTML injection)
These lines assign unescaped/unsanitized dynamic values directly to `.innerHTML`, allowing XSS:

### 📄 [account.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\account.html)
- Expression: `accountsData.map(account => `
                    <tr>
                        <td>
                            <strong class="text-primary">${maskAccountNumber(account.account_number)}</strong>
                            <br>
                            <small class="text-muted">ID: ${account.id}</small>
                        </td>
                        <td>
                            <span class="badge bg-info">${account.account_type ? account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1) : 'Checking'}</span>
                        </td>
                        <td class="text-success fw-bold text-end">${formatCurrency(account.balance)}</td>
                        <td>${account.currency || 'USD'}</td>
                        <td>${formatDate(account.created_at)}</td>
                        <td>${getStatusBadge(account.status)}</td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = accountsData.map(account => `
                    <tr>
                        <td>
                            <strong class="text-primary">${maskAccountNumber(account.account_number)}</strong>
                            <br>
                            <small class="text-muted">ID: ${account.id}</small>
                        </td>
                        <td>
                            <span class="badge bg-info">${account.account_type ? account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1) : 'Checking'}</span>
                        </td>
                        <td class="text-success fw-bold text-end">${formatCurrency(account.balance)}</td>
                        <td>${account.currency || 'USD'}</td>
                        <td>${formatDate(account.created_at)}</td>
                        <td>${getStatusBadge(account.status)}</td>
                    </tr>
                `).join('');`
- Expression: ``
                    <tr><td colspan="6" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Failed to load accounts: ${error.message}
                    </td></tr>
                ``
  Line: `.innerHTML = `
                    <tr><td colspan="6" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Failed to load accounts: ${error.message}
                    </td></tr>
                `;`
- Expression: ``
                    <tr><td colspan="5" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Failed to load transactions
                    </td></tr>
                ``
  Line: `.innerHTML = `
                    <tr><td colspan="5" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Failed to load transactions
                    </td></tr>
                `;`
### 📄 [alerts.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\alerts.html)
- Expression: `alerts.map(alert => `
            <tr>
                <td>${new Date(alert.created_at).toLocaleString()}</td>
                <td><span class="badge bg-light text-dark">${alert.alert_type}</span></td>
                <td>${alert.message}</td>
                <td>${alert.sent_channels.join(', ')}</td>
                <td><span class="badge ${alert.is_read ? 'bg-secondary' : 'bg-primary'}">
                    ${alert.is_read ? 'Read' : 'New'}
                </span></td>
                <td>
                    ${!alert.is_read ? `<button class="btn btn-sm btn-outline-primary" onclick="markAlertRead('${alert.id}')">Mark Read</button>` : ''}
                </td>
            </tr>
        `).join('')`
  Line: `.innerHTML = alerts.map(alert => `
            <tr>
                <td>${new Date(alert.created_at).toLocaleString()}</td>
                <td><span class="badge bg-light text-dark">${alert.alert_type}</span></td>
                <td>${alert.message}</td>
                <td>${alert.sent_channels.join(', ')}</td>
                <td><span class="badge ${alert.is_read ? 'bg-secondary' : 'bg-primary'}">
                    ${alert.is_read ? 'Read' : 'New'}
                </span></td>
                <td>
                    ${!alert.is_read ? `<button class="btn btn-sm btn-outline-primary" onclick="markAlertRead('${alert.id}')">Mark Read</button>` : ''}
                </td>
            </tr>
        `).join('');`
### 📄 [business_analysis.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\business_analysis.html)
- Expression: ``
                            <td>${report.month}</td>
                            <td>Monthly Transaction Report</td>
                            <td>
                                <span class="badge bg-success">Completed</span>
                                <br>
                                <small class="text-muted">${report.count} transactions, Total: ${formatCurrency(report.totalAmount)}</small>
                            </td>
                        ``
  Line: `.innerHTML = `
                            <td>${report.month}</td>
                            <td>Monthly Transaction Report</td>
                            <td>
                                <span class="badge bg-success">Completed</span>
                                <br>
                                <small class="text-muted">${report.count} transactions, Total: ${formatCurrency(report.totalAmount)}</small>
                            </td>
                        `;`
- Expression: ``<tr><td colspan="3" class="text-center text-danger py-4">
                    Error loading analysis data: ${error.message}
                </td></tr>``
  Line: `.innerHTML = `<tr><td colspan="3" class="text-center text-danger py-4">
                    Error loading analysis data: ${error.message}
                </td></tr>`;`
### 📄 [cards.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\cards.html)
- Expression: ``<tr><td colspan="8" class="text-center text-danger py-4"><i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4"><i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}</td></tr>`;`
- Expression: ``
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s`
  Line: `.innerHTML = `
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s;`
- Expression: ``
                <td class="fw-bold">•••• •••• •••• ${lastFour}</td>
                <td>${formatCardType(card.card_type)}</td>
                <td class="text-success fw-bold">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>$${creditLimit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>
                    <div class="progress" style="height: 20px`
  Line: `.innerHTML = `
                <td class="fw-bold">•••• •••• •••• ${lastFour}</td>
                <td>${formatCardType(card.card_type)}</td>
                <td class="text-success fw-bold">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>$${creditLimit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>
                    <div class="progress" style="height: 20px;`
- Expression: ``
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatCardType(card.card_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Card Status:</strong> <span class="badge bg-info">${(card.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Card Number</h6>
                        <h5 class="text-primary">•••• •••• •••• ${lastFour}</h5>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Card Balance</h6>
                        <h5 class="text-success">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Credit Limit</h6>
                        <h5 class="text-warning">$${creditLimit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Available Credit</h6>
                        <h5 class="text-info">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Credit Limit Usage</h6>
                    <div class="progress" style="height: 25px`
  Line: `.innerHTML = `
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatCardType(card.card_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Card Status:</strong> <span class="badge bg-info">${(card.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Card Number</h6>
                        <h5 class="text-primary">•••• •••• •••• ${lastFour}</h5>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Card Balance</h6>
                        <h5 class="text-success">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Credit Limit</h6>
                        <h5 class="text-warning">$${creditLimit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Available Credit</h6>
                        <h5 class="text-info">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h5>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Credit Limit Usage</h6>
                    <div class="progress" style="height: 25px;`
- Expression: ``
                        <strong>${info.title}</strong>
                        <ul class="mb-0 mt-2">
                            ${info.features.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    ``
  Line: `.innerHTML = `
                        <strong>${info.title}</strong>
                        <ul class="mb-0 mt-2">
                            ${info.features.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    `;`
### 📄 [contact.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\contact.html)
- Expression: ``<div class="text-center text-muted py-5"><i class="bi bi-inbox" style="font-size: 3rem`
  Line: `.innerHTML = `<div class="text-center text-muted py-5"><i class="bi bi-inbox" style="font-size: 3rem;`
- Expression: ``
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Ticket ID</th>
                                    <th>Subject</th>
                                    <th>Status</th>
                                    <th>Priority</th>
                                    <th>Created</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tickets.map(t => `
                                    <tr>
                                        <td><code>#${t.ticket_number || t.id}</code></td>
                                        <td><strong>${t.subject || 'Support Request'}</strong></td>
                                        <td><span class="badge ${getStatusColor(t.status || 'open')}">${t.status || 'open'}</span></td>
                                        <td><span class="badge ${getPriorityBadge(t.priority || 'normal')}">${t.priority || 'normal'}</span></td>
                                        <td><small>${new Date(t.created_at).toLocaleDateString()}</small></td>
                                        <td><a href="#" class="btn btn-sm btn-outline-primary">View</a></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ``
  Line: `.innerHTML = `
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Ticket ID</th>
                                    <th>Subject</th>
                                    <th>Status</th>
                                    <th>Priority</th>
                                    <th>Created</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tickets.map(t => `
                                    <tr>
                                        <td><code>#${t.ticket_number || t.id}</code></td>
                                        <td><strong>${t.subject || 'Support Request'}</strong></td>
                                        <td><span class="badge ${getStatusColor(t.status || 'open')}">${t.status || 'open'}</span></td>
                                        <td><span class="badge ${getPriorityBadge(t.priority || 'normal')}">${t.priority || 'normal'}</span></td>
                                        <td><small>${new Date(t.created_at).toLocaleDateString()}</small></td>
                                        <td><a href="#" class="btn btn-sm btn-outline-primary">View</a></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;`
- Expression: ``<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>Ticket submitted successfully! Ticket #: <strong>${data.ticket_number || data.id}</strong></div>``
  Line: `.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>Ticket submitted successfully! Ticket #: <strong>${data.ticket_number || data.id}</strong></div>`;`
- Expression: ``<div class="alert alert-danger">Failed: ${error.detail || 'Unknown error'}</div>``
  Line: `.innerHTML = `<div class="alert alert-danger">Failed: ${error.detail || 'Unknown error'}</div>`;`
### 📄 [dashboard.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\dashboard.html)
- Expression: ``
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <small class="text-muted">
                        Showing 1–${Math.min(transactionPageSize, totalTransactions)} of ${totalTransactions} transactions
                    </small>
                    <div>
                        <button class="btn btn-outline-success btn-sm load-more-btn me-2" onclick="loadMoreTransactions()">
                            <i class="fas fa-chevron-down me-2"></i>Load More
                        </button>
                        <a href="/user/transactions" class="btn btn-outline-primary btn-sm load-more-btn">
                            <i class="fas fa-list me-2"></i>View All
                        </a>
                    </div>
                </div>
            ``
  Line: `.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <small class="text-muted">
                        Showing 1–${Math.min(transactionPageSize, totalTransactions)} of ${totalTransactions} transactions
                    </small>
                    <div>
                        <button class="btn btn-outline-success btn-sm load-more-btn me-2" onclick="loadMoreTransactions()">
                            <i class="fas fa-chevron-down me-2"></i>Load More
                        </button>
                        <a href="/user/transactions" class="btn btn-outline-primary btn-sm load-more-btn">
                            <i class="fas fa-list me-2"></i>View All
                        </a>
                    </div>
                </div>
            `;`
- Expression: ``
                <i class="fas fa-${piiMasking ? 'eye-slash' : 'eye'} me-1 pii-toggle"></i><span id="pii-toggle-text">${piiMasking ? 'Hide' : 'Show'}</span> Numbers
            ``
  Line: `.innerHTML = `
                <i class="fas fa-${piiMasking ? 'eye-slash' : 'eye'} me-1 pii-toggle"></i><span id="pii-toggle-text">${piiMasking ? 'Hide' : 'Show'}</span> Numbers
            `;`
- Expression: ``
                    <div class="suspension-banner">
                        <strong><i class="fas fa-lock me-2"></i>Account Suspended</strong>
                        <p class="mb-0 mt-2">${status.suspension_reason || 'Your account has been suspended.'}</p>
                    </div>
                ``
  Line: `.innerHTML = `
                    <div class="suspension-banner">
                        <strong><i class="fas fa-lock me-2"></i>Account Suspended</strong>
                        <p class="mb-0 mt-2">${status.suspension_reason || 'Your account has been suspended.'}</p>
                    </div>
                `;`
### 📄 [deposits.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\deposits.html)
- Expression: ``
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s`
  Line: `.innerHTML = `
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s;`
- Expression: ``
                <td class="fw-bold">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-success fw-bold">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>${dep.interest_rate || 0}%</td>
                <td>$${interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>
                    <div class="progress" style="height: 20px`
  Line: `.innerHTML = `
                <td class="fw-bold">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-success fw-bold">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>${dep.interest_rate || 0}%</td>
                <td>$${interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>
                    <div class="progress" style="height: 20px;`
- Expression: ``
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatDepositType(dep.deposit_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Deposit Status:</strong> <span class="badge bg-info">${(dep.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Principal Amount</h6>
                        <h4 class="text-primary">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Current Balance</h6>
                        <h4 class="text-success">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Interest Earned</h6>
                        <h4 class="text-info">$${interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Interest Rate</h6>
                        <h4 class="text-warning">${dep.interest_rate || 0}% p.a.</h4>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Interest Accumulation Progress</h6>
                    <div class="progress" style="height: 25px`
  Line: `.innerHTML = `
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatDepositType(dep.deposit_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Deposit Status:</strong> <span class="badge bg-info">${(dep.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Principal Amount</h6>
                        <h4 class="text-primary">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Current Balance</h6>
                        <h4 class="text-success">$${balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Interest Earned</h6>
                        <h4 class="text-info">$${interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Interest Rate</h6>
                        <h4 class="text-warning">${dep.interest_rate || 0}% p.a.</h4>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Interest Accumulation Progress</h6>
                    <div class="progress" style="height: 25px;`
### 📄 [financial_planning.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\financial_planning.html)
- Expression: ``
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong class="d-block">${goal.title}</strong>
                                    <span class="text-muted small">Target: $${Number(goal.target_amount).toLocaleString()}</span>
                                </div>
                                <span class="fw-bold text-primary">$${Number(goal.current_amount).toLocaleString()}</span>
                            </div>
                            <div class="progress mt-2" style="height: 10px`
  Line: `.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong class="d-block">${goal.title}</strong>
                                    <span class="text-muted small">Target: $${Number(goal.target_amount).toLocaleString()}</span>
                                </div>
                                <span class="fw-bold text-primary">$${Number(goal.current_amount).toLocaleString()}</span>
                            </div>
                            <div class="progress mt-2" style="height: 10px;`
### 📄 [insurance.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\insurance.html)
- Expression: ``
                        <td>${p.policy_number || ('POL-' + p.id)}</td>
                        <td>${p.type}</td>
                        <td>$${Number(p.premium).toLocaleString()}</td>
                        <td>$${Number(p.coverage_amount).toLocaleString()}</td>
                        <td>${p.renewal_date || ''}</td>
                        <td><span class="badge ${p.status === 'active' ? 'bg-success' : 'bg-warning'}">${p.status}</span></td>
                    ``
  Line: `.innerHTML = `
                        <td>${p.policy_number || ('POL-' + p.id)}</td>
                        <td>${p.type}</td>
                        <td>$${Number(p.premium).toLocaleString()}</td>
                        <td>$${Number(p.coverage_amount).toLocaleString()}</td>
                        <td>${p.renewal_date || ''}</td>
                        <td><span class="badge ${p.status === 'active' ? 'bg-success' : 'bg-warning'}">${p.status}</span></td>
                    `;`
### 📄 [investments.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\investments.html)
- Expression: ``
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s`
  Line: `.innerHTML = `
                <div class="card h-100 shadow-sm border-0 cursor-pointer" style="transition: transform 0.2s;`
- Expression: ``
                <td class="fw-bold">${formatInvestmentType(inv.investment_type)}</td>
                <td>$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-success fw-bold">$${value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>$${returns.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>${inv.annual_return_rate || 0}%</td>
                <td>
                    <div class="progress" style="height: 20px`
  Line: `.innerHTML = `
                <td class="fw-bold">${formatInvestmentType(inv.investment_type)}</td>
                <td>$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="text-success fw-bold">$${value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>$${returns.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>${inv.annual_return_rate || 0}%</td>
                <td>
                    <div class="progress" style="height: 20px;`
- Expression: ``
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatInvestmentType(inv.investment_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Investment Status:</strong> <span class="badge bg-info">${(inv.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Amount Invested</h6>
                        <h4 class="text-primary">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Current Value</h6>
                        <h4 class="text-success">$${value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Returns Earned</h6>
                        <h4 class="text-info">$${returns.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Annual Return Rate</h6>
                        <h4 class="text-warning">${inv.annual_return_rate || 0}%</h4>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Return Progress</h6>
                    <div class="progress" style="height: 25px`
  Line: `.innerHTML = `
                <div class="row mb-4">
                    <div class="col-12">
                        <h5 class="mb-3">${formatInvestmentType(inv.investment_type)}</h5>
                        <div class="alert alert-info">
                            <strong>Investment Status:</strong> <span class="badge bg-info">${(inv.status || 'active').toUpperCase()}</span>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Amount Invested</h6>
                        <h4 class="text-primary">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Current Value</h6>
                        <h4 class="text-success">$${value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Returns Earned</h6>
                        <h4 class="text-info">$${returns.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</h4>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted text-uppercase mb-2">Annual Return Rate</h6>
                        <h4 class="text-warning">${inv.annual_return_rate || 0}%</h4>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Return Progress</h6>
                    <div class="progress" style="height: 25px;`
### 📄 [kyc.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\kyc.html)
- Expression: ``
                <div class="mb-3">
                    <strong>Risk Assessment:</strong>
                    <span class="badge ${getRiskBadgeClass(requirements.risk)}">${requirements.risk}</span>
                </div>
                <div class="mb-3">
                    <strong>Required Documents:</strong>
                    <ul class="mb-0 mt-2">
                        ${requirements.documents.map(doc => `<li>${formatDocumentName(doc)}</li>`).join('')}
                    </ul>
                </div>
                <div class="mb-3">
                    <strong>Accepted ID Types:</strong> ${requirements.idTypes}
                </div>
                <div>
                    <strong>Proof of Address:</strong> ${requirements.addressTypes}
                </div>
            ``
  Line: `.innerHTML = `
                <div class="mb-3">
                    <strong>Risk Assessment:</strong>
                    <span class="badge ${getRiskBadgeClass(requirements.risk)}">${requirements.risk}</span>
                </div>
                <div class="mb-3">
                    <strong>Required Documents:</strong>
                    <ul class="mb-0 mt-2">
                        ${requirements.documents.map(doc => `<li>${formatDocumentName(doc)}</li>`).join('')}
                    </ul>
                </div>
                <div class="mb-3">
                    <strong>Accepted ID Types:</strong> ${requirements.idTypes}
                </div>
                <div>
                    <strong>Proof of Address:</strong> ${requirements.addressTypes}
                </div>
            `;`
- Expression: ``<strong>Accepted IDs (${region}):</strong> ${requirements.idTypes}``
  Line: `.innerHTML = `<strong>Accepted IDs (${region}):</strong> ${requirements.idTypes}`;`
- Expression: ``<strong>Accepted Documents (${region}):</strong> ${requirements.addressTypes}``
  Line: `.innerHTML = `<strong>Accepted Documents (${region}):</strong> ${requirements.addressTypes}`;`
- Expression: ``<span class="badge ${getRiskBadgeClass(requirements.risk)}">${requirements.risk} Risk</span>``
  Line: `.innerHTML = `<span class="badge ${getRiskBadgeClass(requirements.risk)}">${requirements.risk} Risk</span>`;`
- Expression: ``<div class="alert alert-danger">✗ Upload failed: ${error.detail || 'Unknown error'}</div>``
  Line: `.innerHTML = `<div class="alert alert-danger">✗ Upload failed: ${error.detail || 'Unknown error'}</div>`;`
- Expression: ``<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>``
  Line: `.innerHTML = `<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>`;`
- Expression: ``<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>``
  Line: `.innerHTML = `<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>`;`
- Expression: ``<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>``
  Line: `.innerHTML = `<div class="alert alert-danger mb-0">✗ ${error.detail || 'Upload failed'}</div>`;`
### 📄 [kyc_pending.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\kyc_pending.html)
- Expression: ``
                        <ul class="list-group">
                            <li class="list-group-item">
                                <strong>Document Type:</strong> ID Document<br>
                                <strong>Submitted:</strong> Today<br>
                                <strong>Status:</strong> <span class="badge bg-warning">Under Review</span>
                            </li>
                        </ul>
                    ``
  Line: `.innerHTML = `
                        <ul class="list-group">
                            <li class="list-group-item">
                                <strong>Document Type:</strong> ID Document<br>
                                <strong>Submitted:</strong> Today<br>
                                <strong>Status:</strong> <span class="badge bg-warning">Under Review</span>
                            </li>
                        </ul>
                    `;`
### 📄 [loans.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\loans.html)
- Expression: ``
                    <div class="col-12 text-center text-danger py-5">
                        <i class="fas fa-exclamation-circle me-2"></i>Failed to load loans
                    </div>
                ``
  Line: `.innerHTML = `
                    <div class="col-12 text-center text-danger py-5">
                        <i class="fas fa-exclamation-circle me-2"></i>Failed to load loans
                    </div>
                `;`
- Expression: ``
                    <div class="col-12 text-center text-muted py-5">
                        <i class="fas fa-inbox me-2"></i>No loans found
                    </div>
                ``
  Line: `.innerHTML = `
                    <div class="col-12 text-center text-muted py-5">
                        <i class="fas fa-inbox me-2"></i>No loans found
                    </div>
                `;`
- Expression: ``
                    <tr>
                        <td colspan="8" class="text-center py-4">No loans found</td>
                    </tr>
                ``
  Line: `.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-4">No loans found</td>
                    </tr>
                `;`
- Expression: ``
                <div class="mb-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <h6 class="text-muted mb-2">${formatLoanType(loan.loan_type)}</h6>
                            <h3 class="text-primary mb-3">$${loan.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</h3>
                            <div class="d-flex justify-content-center gap-4">
                                <div>
                                    <small class="text-muted d-block">Outstanding</small>
                                    <h6 class="text-danger">$${outstanding.toLocaleString('en-US', {minimumFractionDigits: 2})}</h6>
                                </div>
                                <div>
                                    <small class="text-muted d-block">Status</small>
                                    <span class="loan-status status-${loan.status}">${loan.status.charAt(0).toUpperCase() + loan.status.slice(1)}</span>
                                </div>
                                <div>
                                    <small class="text-muted d-block">Progress</small>
                                    <h6 class="text-success">${progress.toFixed(1)}%</h6>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="mb-3">Repayment Progress</h6>
                    <div class="progress mb-2" style="height: 12px`
  Line: `.innerHTML = `
                <div class="mb-4">
                    <div class="card bg-light border-0">
                        <div class="card-body text-center">
                            <h6 class="text-muted mb-2">${formatLoanType(loan.loan_type)}</h6>
                            <h3 class="text-primary mb-3">$${loan.amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</h3>
                            <div class="d-flex justify-content-center gap-4">
                                <div>
                                    <small class="text-muted d-block">Outstanding</small>
                                    <h6 class="text-danger">$${outstanding.toLocaleString('en-US', {minimumFractionDigits: 2})}</h6>
                                </div>
                                <div>
                                    <small class="text-muted d-block">Status</small>
                                    <span class="loan-status status-${loan.status}">${loan.status.charAt(0).toUpperCase() + loan.status.slice(1)}</span>
                                </div>
                                <div>
                                    <small class="text-muted d-block">Progress</small>
                                    <h6 class="text-success">${progress.toFixed(1)}%</h6>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="mb-3">Repayment Progress</h6>
                    <div class="progress mb-2" style="height: 12px;`
### 📄 [notifications.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\notifications.html)
- Expression: ``<div class="list-group-item text-center text-muted py-5"><i class="bi bi-inbox" style="font-size: 3rem`
  Line: `.innerHTML = `<div class="list-group-item text-center text-muted py-5"><i class="bi bi-inbox" style="font-size: 3rem;`
### 📄 [project.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\project.html)
- Expression: ``
                        <td>${p.name}</td>
                        <td>${p.description || ''}</td>
                        <td>${p.deadline || ''}</td>
                        <td><span class="badge ${p.status === 'completed' ? 'bg-success' : p.status === 'in_progress' ? 'bg-info' : 'bg-secondary'}">${p.status.replace('_', ' ')}</span></td>
                        <td><button class="btn btn-sm btn-outline-primary">Edit</button></td>
                    ``
  Line: `.innerHTML = `
                        <td>${p.name}</td>
                        <td>${p.description || ''}</td>
                        <td>${p.deadline || ''}</td>
                        <td><span class="badge ${p.status === 'completed' ? 'bg-success' : p.status === 'in_progress' ? 'bg-info' : 'bg-secondary'}">${p.status.replace('_', ' ')}</span></td>
                        <td><button class="btn btn-sm btn-outline-primary">Edit</button></td>
                    `;`
### 📄 [security.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\security.html)
- Expression: `history.map(log => `
            <tr>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${log.device_name || 'Unknown'}</td>
                <td>${log.location || 'Unknown'}</td>
                <td><code>${log.ip_address}</code></td>
                <td><span class="badge bg-${log.success ? 'success' : 'danger'}">${log.success ? 'Success' : 'Failed'}</span></td>
                <td>
                    ${!log.current ? `<button class="btn btn-sm btn-outline-danger" onclick="reportSuspicious('${log.id}')">Report</button>` : '<span class="text-muted">Current</span>'}
                </td>
            </tr>
        `).join('')`
  Line: `.innerHTML = history.map(log => `
            <tr>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${log.device_name || 'Unknown'}</td>
                <td>${log.location || 'Unknown'}</td>
                <td><code>${log.ip_address}</code></td>
                <td><span class="badge bg-${log.success ? 'success' : 'danger'}">${log.success ? 'Success' : 'Failed'}</span></td>
                <td>
                    ${!log.current ? `<button class="btn btn-sm btn-outline-danger" onclick="reportSuspicious('${log.id}')">Report</button>` : '<span class="text-muted">Current</span>'}
                </td>
            </tr>
        `).join('');`
- Expression: `devices.map(device => `
            <div class="device-item ${device.current_device ? 'current' : ''}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">
                            <i class="fas fa-${device.device_type === 'mobile' ? 'mobile-alt' : 'laptop'} me-2"></i>
                            ${device.device_name}
                            ${device.current_device ? '<span class="badge bg-success ms-2">Current Device</span>' : ''}
                        </h6>
                        <p class="small text-muted mb-1">
                            <i class="fas fa-map-marker-alt me-1"></i>${device.location}
                        </p>
                        <p class="small text-muted mb-1">
                            <i class="fas fa-globe me-1"></i>${device.ip_address}
                        </p>
                        <p class="small text-muted mb-0">
                            <i class="fas fa-clock me-1"></i>Last used: ${new Date(device.last_activity).toLocaleString()}
                        </p>
                    </div>
                    <div>
                        ${!device.current_device ? `<button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${device.id}')">Remove</button>` : ''}
                    </div>
                </div>
            </div>
        `).join('')`
  Line: `.innerHTML = devices.map(device => `
            <div class="device-item ${device.current_device ? 'current' : ''}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">
                            <i class="fas fa-${device.device_type === 'mobile' ? 'mobile-alt' : 'laptop'} me-2"></i>
                            ${device.device_name}
                            ${device.current_device ? '<span class="badge bg-success ms-2">Current Device</span>' : ''}
                        </h6>
                        <p class="small text-muted mb-1">
                            <i class="fas fa-map-marker-alt me-1"></i>${device.location}
                        </p>
                        <p class="small text-muted mb-1">
                            <i class="fas fa-globe me-1"></i>${device.ip_address}
                        </p>
                        <p class="small text-muted mb-0">
                            <i class="fas fa-clock me-1"></i>Last used: ${new Date(device.last_activity).toLocaleString()}
                        </p>
                    </div>
                    <div>
                        ${!device.current_device ? `<button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${device.id}')">Remove</button>` : ''}
                    </div>
                </div>
            </div>
        `).join('');`
### 📄 [settings.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\settings.html)
- Expression: `data.logins.slice(0, 5).map(login => `
                            <tr>
                                <td><small>${new Date(login.timestamp).toLocaleString()}</small></td>
                                <td><small>${login.device || 'Unknown'}</small></td>
                                <td><small>${maskIp(login.ip_address)}</small></td>
                                <td><span class="badge bg-success">Success</span></td>
                            </tr>
                        `).join('')`
  Line: `.innerHTML = data.logins.slice(0, 5).map(login => `
                            <tr>
                                <td><small>${new Date(login.timestamp).toLocaleString()}</small></td>
                                <td><small>${login.device || 'Unknown'}</small></td>
                                <td><small>${maskIp(login.ip_address)}</small></td>
                                <td><span class="badge bg-success">Success</span></td>
                            </tr>
                        `).join('');`
- Expression: `data.devices.map(device => `
                            <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                                <div>
                                    <p class="mb-0"><small><strong>${device.device_name}</strong></small></p>
                                    <p class="mb-0"><small class="text-muted">Last used: ${new Date(device.last_used).toLocaleDateString()}</small></p>
                                </div>
                                <button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${device.id}')">Remove</button>
                            </div>
                        `).join('')`
  Line: `.innerHTML = data.devices.map(device => `
                            <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                                <div>
                                    <p class="mb-0"><small><strong>${device.device_name}</strong></small></p>
                                    <p class="mb-0"><small class="text-muted">Last used: ${new Date(device.last_used).toLocaleDateString()}</small></p>
                                </div>
                                <button class="btn btn-sm btn-outline-danger" onclick="removeDevice('${device.id}')">Remove</button>
                            </div>
                        `).join('');`
### 📄 [settlement_status.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\settlement_status.html)
- Expression: ``
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Settlement ID</h6>
                                <p>${settlement.id}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Status</h6>
                                <p><span class="status-badge status-${settlement.status}">${settlement.status}</span></p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Type</h6>
                                <p>${settlement.type.toUpperCase()}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Amount</h6>
                                <p><strong>$${settlement.amount.toLocaleString('en-US', {maximumFractionDigits: 2})}</strong></p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>From Account</h6>
                                <p>${settlement.from_account}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>To Account</h6>
                                <p>${settlement.to_account}</p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Submitted</h6>
                                <p>${new Date(settlement.submitted).toLocaleString()}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Reference Number</h6>
                                <p>${settlement.reference || 'N/A'}</p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-12">
                                <h6>Timeline</h6>
                                <div class="timeline-item">
                                    <strong>Submitted</strong>
                                    <p class="text-muted">${new Date(settlement.submitted).toLocaleString()}</p>
                                </div>
                                ${settlement.status !== 'pending' ? `
                                    <div class="timeline-item">
                                        <strong>Processing Started</strong>
                                        <p class="text-muted">Processing</p>
                                    </div>
                                ` : ''}
                                ${settlement.status === 'confirmed' ? `
                                    <div class="timeline-item">
                                        <strong>Confirmed</strong>
                                        <p class="text-muted">${new Date(settlement.settled_date).toLocaleString()}</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ``
  Line: `.innerHTML = `
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Settlement ID</h6>
                                <p>${settlement.id}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Status</h6>
                                <p><span class="status-badge status-${settlement.status}">${settlement.status}</span></p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Type</h6>
                                <p>${settlement.type.toUpperCase()}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Amount</h6>
                                <p><strong>$${settlement.amount.toLocaleString('en-US', {maximumFractionDigits: 2})}</strong></p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>From Account</h6>
                                <p>${settlement.from_account}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>To Account</h6>
                                <p>${settlement.to_account}</p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h6>Submitted</h6>
                                <p>${new Date(settlement.submitted).toLocaleString()}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Reference Number</h6>
                                <p>${settlement.reference || 'N/A'}</p>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-12">
                                <h6>Timeline</h6>
                                <div class="timeline-item">
                                    <strong>Submitted</strong>
                                    <p class="text-muted">${new Date(settlement.submitted).toLocaleString()}</p>
                                </div>
                                ${settlement.status !== 'pending' ? `
                                    <div class="timeline-item">
                                        <strong>Processing Started</strong>
                                        <p class="text-muted">Processing</p>
                                    </div>
                                ` : ''}
                                ${settlement.status === 'confirmed' ? `
                                    <div class="timeline-item">
                                        <strong>Confirmed</strong>
                                        <p class="text-muted">${new Date(settlement.settled_date).toLocaleString()}</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;`
### 📄 [transactions.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\transactions.html)
- Expression: ``
            <tr><td colspan="7" class="text-center text-danger py-4">
                <i class="fas fa-exclamation-circle me-2"></i>Failed to load transactions
            </td></tr>
        ``
  Line: `.innerHTML = `
            <tr><td colspan="7" class="text-center text-danger py-4">
                <i class="fas fa-exclamation-circle me-2"></i>Failed to load transactions
            </td></tr>
        `;`
- Expression: ``
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-inbox me-2"></i>No transactions found
                </td>
            </tr>
        ``
  Line: `.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-inbox me-2"></i>No transactions found
                </td>
            </tr>
        `;`
- Expression: `transactions.map(t => `
        <tr class="cursor-pointer" onclick="viewTransactionDetail(${t.id})">
            <td class="fw-500">${formatDate(t.created_at || t.date)}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <i class="fas ${getTransactionIcon(t.transaction_type)} text-primary"></i>
                    <span>${truncateText(t.description || t.purpose, 30)}</span>
                </div>
            </td>
            <td>
                <span class="badge bg-light text-dark text-uppercase text-sm">${t.transaction_type || t.type || 'Other'}</span>
            </td>
            <td class="fw-600 ${t.amount >= 0 ? 'text-success' : 'text-danger'}">
                ${t.amount >= 0 ? '+' : ''}$${Math.abs(t.amount || 0).toFixed(2)}
            </td>
            <td>
                <span class="text-muted small">${getCategory(t.transaction_type)}</span>
            </td>
            <td>
                <span class="badge ${getStatusBadgeClass(t.status)}">
                    ${(t.status || 'completed').charAt(0).toUpperCase() + (t.status || 'completed').slice(1)}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-primary btn-xs" onclick="event.stopPropagation()`
  Line: `.innerHTML = transactions.map(t => `
        <tr class="cursor-pointer" onclick="viewTransactionDetail(${t.id})">
            <td class="fw-500">${formatDate(t.created_at || t.date)}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <i class="fas ${getTransactionIcon(t.transaction_type)} text-primary"></i>
                    <span>${truncateText(t.description || t.purpose, 30)}</span>
                </div>
            </td>
            <td>
                <span class="badge bg-light text-dark text-uppercase text-sm">${t.transaction_type || t.type || 'Other'}</span>
            </td>
            <td class="fw-600 ${t.amount >= 0 ? 'text-success' : 'text-danger'}">
                ${t.amount >= 0 ? '+' : ''}$${Math.abs(t.amount || 0).toFixed(2)}
            </td>
            <td>
                <span class="text-muted small">${getCategory(t.transaction_type)}</span>
            </td>
            <td>
                <span class="badge ${getStatusBadgeClass(t.status)}">
                    ${(t.status || 'completed').charAt(0).toUpperCase() + (t.status || 'completed').slice(1)}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-primary btn-xs" onclick="event.stopPropagation();`
- Expression: ``<span class="page-link">Page ${page}</span>``
  Line: `.innerHTML = `<span class="page-link">Page ${page}</span>`;`
- Expression: ``
        <div class="row mb-3">
            <div class="col-12">
                <div class="card bg-light border-0">
                    <div class="card-body text-center">
                        <i class="fas ${getTransactionIcon(transaction.transaction_type)} fa-2x text-primary mb-2"></i>
                        <h6 class="text-muted mb-2">${transaction.description || 'Transaction'}</h6>
                        <h3 class="${amountClass} mb-0">
                            ${transaction.amount >= 0 ? '+' : ''}$${Math.abs(transaction.amount || 0).toFixed(2)}
                        </h3>
                    </div>
                </div>
            </div>
        </div>
        <dl class="row g-0">
            <dt class="col-sm-4 fw-600">Date & Time:</dt>
            <dd class="col-sm-8">${formatDateTime(transaction.created_at || transaction.date)}</dd>
            
            <dt class="col-sm-4 fw-600">Type:</dt>
            <dd class="col-sm-8">
                <span class="badge bg-light text-dark text-uppercase">${transaction.transaction_type || 'Other'}</span>
            </dd>
            
            <dt class="col-sm-4 fw-600">Category:</dt>
            <dd class="col-sm-8">${getCategory(transaction.transaction_type)}</dd>
            
            <dt class="col-sm-4 fw-600">Status:</dt>
            <dd class="col-sm-8">
                <span class="badge ${statusClass}">
                    ${(transaction.status || 'completed').charAt(0).toUpperCase() + (transaction.status || 'completed').slice(1)}
                </span>
            </dd>
            
            ${transaction.reference_id ? `
                <dt class="col-sm-4 fw-600">Reference:</dt>
                <dd class="col-sm-8"><code class="bg-light px-2 py-1 rounded">${transaction.reference_id}</code></dd>
            ` : ''}
            
            ${transaction.merchant ? `
                <dt class="col-sm-4 fw-600">Merchant:</dt>
                <dd class="col-sm-8">${transaction.merchant}</dd>
            ` : ''}
            
            ${transaction.from_account ? `
                <dt class="col-sm-4 fw-600">From:</dt>
                <dd class="col-sm-8">${maskAccountNumber(transaction.from_account)}</dd>
            ` : ''}
            
            ${transaction.to_account ? `
                <dt class="col-sm-4 fw-600">To:</dt>
                <dd class="col-sm-8">${maskAccountNumber(transaction.to_account)}</dd>
            ` : ''}
            
            ${transaction.notes ? `
                <dt class="col-sm-4 fw-600">Notes:</dt>
                <dd class="col-sm-8 text-muted">${transaction.notes}</dd>
            ` : ''}
        </dl>
    ``
  Line: `.innerHTML = `
        <div class="row mb-3">
            <div class="col-12">
                <div class="card bg-light border-0">
                    <div class="card-body text-center">
                        <i class="fas ${getTransactionIcon(transaction.transaction_type)} fa-2x text-primary mb-2"></i>
                        <h6 class="text-muted mb-2">${transaction.description || 'Transaction'}</h6>
                        <h3 class="${amountClass} mb-0">
                            ${transaction.amount >= 0 ? '+' : ''}$${Math.abs(transaction.amount || 0).toFixed(2)}
                        </h3>
                    </div>
                </div>
            </div>
        </div>
        <dl class="row g-0">
            <dt class="col-sm-4 fw-600">Date & Time:</dt>
            <dd class="col-sm-8">${formatDateTime(transaction.created_at || transaction.date)}</dd>
            
            <dt class="col-sm-4 fw-600">Type:</dt>
            <dd class="col-sm-8">
                <span class="badge bg-light text-dark text-uppercase">${transaction.transaction_type || 'Other'}</span>
            </dd>
            
            <dt class="col-sm-4 fw-600">Category:</dt>
            <dd class="col-sm-8">${getCategory(transaction.transaction_type)}</dd>
            
            <dt class="col-sm-4 fw-600">Status:</dt>
            <dd class="col-sm-8">
                <span class="badge ${statusClass}">
                    ${(transaction.status || 'completed').charAt(0).toUpperCase() + (transaction.status || 'completed').slice(1)}
                </span>
            </dd>
            
            ${transaction.reference_id ? `
                <dt class="col-sm-4 fw-600">Reference:</dt>
                <dd class="col-sm-8"><code class="bg-light px-2 py-1 rounded">${transaction.reference_id}</code></dd>
            ` : ''}
            
            ${transaction.merchant ? `
                <dt class="col-sm-4 fw-600">Merchant:</dt>
                <dd class="col-sm-8">${transaction.merchant}</dd>
            ` : ''}
            
            ${transaction.from_account ? `
                <dt class="col-sm-4 fw-600">From:</dt>
                <dd class="col-sm-8">${maskAccountNumber(transaction.from_account)}</dd>
            ` : ''}
            
            ${transaction.to_account ? `
                <dt class="col-sm-4 fw-600">To:</dt>
                <dd class="col-sm-8">${maskAccountNumber(transaction.to_account)}</dd>
            ` : ''}
            
            ${transaction.notes ? `
                <dt class="col-sm-4 fw-600">Notes:</dt>
                <dd class="col-sm-8 text-muted">${transaction.notes}</dd>
            ` : ''}
        </dl>
    `;`
### 📄 [transfers.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\transfers.html)
- Expression: `accounts.map(a => 
                `<option value="${a.id}">${a.name} - $${a.balance.toFixed(2)}</option>`
            ).join('')`
  Line: `.innerHTML = accounts.map(a => 
                `<option value="${a.id}">${a.name} - $${a.balance.toFixed(2)}</option>`
            ).join('');`
- Expression: `recipients.map(r => 
            `<option value="${r.id}">${r.name} (${r.account_type})</option>`
        ).join('')`
  Line: `.innerHTML = recipients.map(r => 
            `<option value="${r.id}">${r.name} (${r.account_type})</option>`
        ).join('');`
- Expression: `transfers.map(t => `
            <tr>
                <td>${new Date(t.created_at).toLocaleDateString()}</td>
                <td><span class="badge bg-light text-dark">${t.type}</span></td>
                <td>${t.recipient_name}</td>
                <td>$${t.amount.toFixed(2)}</td>
                <td><span class="badge badge-${t.status}">${t.status}</span></td>
                <td><button class="btn btn-sm btn-outline-primary">Details</button></td>
            </tr>
        `).join('')`
  Line: `.innerHTML = transfers.map(t => `
            <tr>
                <td>${new Date(t.created_at).toLocaleDateString()}</td>
                <td><span class="badge bg-light text-dark">${t.type}</span></td>
                <td>${t.recipient_name}</td>
                <td>$${t.amount.toFixed(2)}</td>
                <td><span class="badge badge-${t.status}">${t.status}</span></td>
                <td><button class="btn btn-sm btn-outline-primary">Details</button></td>
            </tr>
        `).join('');`
### 📄 [treasury_portfolio.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\user\treasury_portfolio.html)
- Expression: ``
                            <div class="alert alert-warning mb-3">
                                Your portfolio allocation is off by <strong>${data.rebalance_deviation.toFixed(1)}%</strong>. 
                                Consider rebalancing to maintain your target allocation.
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Current vs Target</h6>
                                    <ul class="list-unstyled">
                                        <li>Equities: ${classes.equities.percent.toFixed(1)}% (Target: 40%)</li>
                                        <li>Fixed Income: ${classes.fixed.percent.toFixed(1)}% (Target: 30%)</li>
                                        <li>Real Estate: ${classes.real_estate.percent.toFixed(1)}% (Target: 20%)</li>
                                        <li>Alternative: ${classes.alternative.percent.toFixed(1)}% (Target: 10%)</li>
                                    </ul>
                                </div>
                            </div>
                        ``
  Line: `.innerHTML = `
                            <div class="alert alert-warning mb-3">
                                Your portfolio allocation is off by <strong>${data.rebalance_deviation.toFixed(1)}%</strong>. 
                                Consider rebalancing to maintain your target allocation.
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Current vs Target</h6>
                                    <ul class="list-unstyled">
                                        <li>Equities: ${classes.equities.percent.toFixed(1)}% (Target: 40%)</li>
                                        <li>Fixed Income: ${classes.fixed.percent.toFixed(1)}% (Target: 30%)</li>
                                        <li>Real Estate: ${classes.real_estate.percent.toFixed(1)}% (Target: 20%)</li>
                                        <li>Alternative: ${classes.alternative.percent.toFixed(1)}% (Target: 10%)</li>
                                    </ul>
                                </div>
                            </div>
                        `;`
### 📄 [admin_ach_management.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_ach_management.html)
- Expression: ``
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            ``
  Line: `.innerHTML = `
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;`
- Expression: `data.data.map(file => `
                    <tr>
                        <td><strong>${escapeHtml(file.id)}</strong></td>
                        <td>${escapeHtml(file.filename || 'N/A')}</td>
                        <td>${new Date(file.upload_date).toLocaleDateString()}</td>
                        <td>${file.entry_count || 0}</td>
                        <td>$${(file.total_volume || 0).toLocaleString()}</td>
                        <td><span class="status-badge status-${file.status}">${escapeHtml(file.status)}</span></td>
                        <td>${Math.round(file.processing_pct || 0)}%</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewFileDetails('${file.id}')" title="View details">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = data.data.map(file => `
                    <tr>
                        <td><strong>${escapeHtml(file.id)}</strong></td>
                        <td>${escapeHtml(file.filename || 'N/A')}</td>
                        <td>${new Date(file.upload_date).toLocaleDateString()}</td>
                        <td>${file.entry_count || 0}</td>
                        <td>$${(file.total_volume || 0).toLocaleString()}</td>
                        <td><span class="status-badge status-${file.status}">${escapeHtml(file.status)}</span></td>
                        <td>${Math.round(file.processing_pct || 0)}%</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewFileDetails('${file.id}')" title="View details">
                                <i class="fas fa-eye"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');`
- Expression: `data.data.map(ret => {
                    const accountDisplay = CONFIG.features.enablePiiMasking ? 
                        SecurityManager.maskPII(ret.account_number, 'account') : 
                        escapeHtml(ret.account_number)`
  Line: `.innerHTML = data.data.map(ret => {
                    const accountDisplay = CONFIG.features.enablePiiMasking ? 
                        SecurityManager.maskPII(ret.account_number, 'account') : 
                        escapeHtml(ret.account_number);`
### 📄 [admin_activity_dashboard.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_activity_dashboard.html)
- Expression: ``
                    <td class="font-monospace text-muted">${new Date(log.created_at).toLocaleString()}</td>
                    <td><span class="fw-bold text-dark">${log.admin_email || 'System'}</span></td>
                    <td><span class="badge-action ${badgeClass}">${log.action || 'Unknown'}</span></td>
                    <td>${log.affected_user_id || '<span class="text-muted">—</span>'}</td>
                    <td>${log.details || 'No additional details.'}</td>
                ``
  Line: `.innerHTML = `
                    <td class="font-monospace text-muted">${new Date(log.created_at).toLocaleString()}</td>
                    <td><span class="fw-bold text-dark">${log.admin_email || 'System'}</span></td>
                    <td><span class="badge-action ${badgeClass}">${log.action || 'Unknown'}</span></td>
                    <td>${log.affected_user_id || '<span class="text-muted">—</span>'}</td>
                    <td>${log.details || 'No additional details.'}</td>
                `;`
- Expression: ``
                    <td><span class="fw-bold">${admin}</span></td>
                    <td><span class="badge bg-secondary">${stats.total}</span></td>
                    <td>${stats.suspensions}</td>
                    <td>${stats.balance}</td>
                    <td class="text-muted small">${stats.last ? stats.last.toLocaleString() : '—'}</td>
                ``
  Line: `.innerHTML = `
                    <td><span class="fw-bold">${admin}</span></td>
                    <td><span class="badge bg-secondary">${stats.total}</span></td>
                    <td>${stats.suspensions}</td>
                    <td>${stats.balance}</td>
                    <td class="text-muted small">${stats.last ? stats.last.toLocaleString() : '—'}</td>
                `;`
- Expression: ``
                    <td><strong>${r.type}</strong></td>
                    <td>${sevBadge}</td>
                    <td>${r.details}</td>
                    <td>${r.count}</td>
                    <td><button class="btn btn-xs btn-outline-dark" onclick="inspectRisk('${r.type}')">Inspect</button></td>
                ``
  Line: `.innerHTML = `
                    <td><strong>${r.type}</strong></td>
                    <td>${sevBadge}</td>
                    <td>${r.details}</td>
                    <td>${r.count}</td>
                    <td><button class="btn btn-xs btn-outline-dark" onclick="inspectRisk('${r.type}')">Inspect</button></td>
                `;`
### 📄 [admin_advanced_search.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_advanced_search.html)
- Expression: ``<tr><td colspan="9" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Searching database...</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Searching database...</td></tr>`;`
- Expression: ``<tr><td colspan="9" class="text-center py-4 text-danger"><i class="fas fa-exclamation-circle me-1"></i> Failed to run query. Check console logs.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-danger"><i class="fas fa-exclamation-circle me-1"></i> Failed to run query. Check console logs.</td></tr>`;`
- Expression: ``<tr><td colspan="9" class="text-center py-4 text-muted">No matching user profiles found.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-muted">No matching user profiles found.</td></tr>`;`
- Expression: ``
                    <td>
                        <div class="fw-bold text-dark">${u.full_name || 'N/A'}</div>
                        <div class="text-muted small font-monospace">${u.email}</div>
                    </td>
                    <td class="font-monospace">${u.account_number || '—'}</td>
                    <td>${kycBadge}</td>
                    <td>${statusBadge}</td>
                    <td class="text-uppercase">${u.region || '—'}</td>
                    <td class="fw-bold">$${parseFloat(u.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td>${mfaIndicator}</td>
                    <td>${new Date(u.created_at).toLocaleDateString()}</td>
                    <td class="text-end">
                        <a href="/user/admin/users?user_id=${u.id}" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-user-cog"></i> View Profile
                        </a>
                    </td>
                ``
  Line: `.innerHTML = `
                    <td>
                        <div class="fw-bold text-dark">${u.full_name || 'N/A'}</div>
                        <div class="text-muted small font-monospace">${u.email}</div>
                    </td>
                    <td class="font-monospace">${u.account_number || '—'}</td>
                    <td>${kycBadge}</td>
                    <td>${statusBadge}</td>
                    <td class="text-uppercase">${u.region || '—'}</td>
                    <td class="fw-bold">$${parseFloat(u.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td>${mfaIndicator}</td>
                    <td>${new Date(u.created_at).toLocaleDateString()}</td>
                    <td class="text-end">
                        <a href="/user/admin/users?user_id=${u.id}" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-user-cog"></i> View Profile
                        </a>
                    </td>
                `;`
- Expression: ``<button class="page-link" onclick="changePage(${currentPage - 1})">Prev</button>``
  Line: `.innerHTML = `<button class="page-link" onclick="changePage(${currentPage - 1})">Prev</button>`;`
- Expression: ``<button class="page-link" onclick="changePage(${i})">${i}</button>``
  Line: `.innerHTML = `<button class="page-link" onclick="changePage(${i})">${i}</button>`;`
- Expression: ``<button class="page-link" onclick="changePage(${currentPage + 1})">Next</button>``
  Line: `.innerHTML = `<button class="page-link" onclick="changePage(${currentPage + 1})">Next</button>`;`
- Expression: ``${key}: ${val}``
  Line: `.innerHTML = `${key}: ${val}`;`
### 📄 [admin_bank_connect.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_bank_connect.html)
- Expression: ``<i class="${icons[type]}" style="color:${colors[type]}"></i><span>${msg}</span>``
  Line: `.innerHTML = `<i class="${icons[type]}" style="color:${colors[type]}"></i><span>${msg}</span>`;`
- Expression: ``<span class="spinner"></span>${text || 'Saving…'}``
  Line: `.innerHTML = `<span class="spinner"></span>${text || 'Saving…'}`;`
- Expression: ``
            <div class="ping-idle" style="color:#9ca3af`
  Line: `.innerHTML = `
            <div class="ping-idle" style="color:#9ca3af;`
- Expression: ``
                <div class="ping-result">
                    <div class="ping-ms ${data.reachable ? q : 'error'}">${data.reachable ? data.latency_ms + '<small style="font-size:1.2rem`
  Line: `.innerHTML = `
                <div class="ping-result">
                    <div class="ping-ms ${data.reachable ? q : 'error'}">${data.reachable ? data.latency_ms + '<small style="font-size:1.2rem;`
- Expression: ``<div class="ping-result"><div class="ping-ms error">✗</div><div class="ping-label" style="color:#9ca3af`
  Line: `.innerHTML = `<div class="ping-result"><div class="ping-ms error">✗</div><div class="ping-label" style="color:#9ca3af;`
- Expression: `pingHistory.map(p => `
            <span style="background:${p.ok ? '#f0fdf4' : '#fef2f2'}`
  Line: `.innerHTML = pingHistory.map(p => `
            <span style="background:${p.ok ? '#f0fdf4' : '#fef2f2'};`
- Expression: ``<i class="fas fa-fingerprint me-1"></i> SHA-256 Fingerprint: ${btoa(data.public_key_pem || '').slice(0, 47)}…``
  Line: `.innerHTML =
                `<i class="fas fa-fingerprint me-1"></i> SHA-256 Fingerprint: ${btoa(data.public_key_pem || '').slice(0, 47)}…`;`
### 📄 [admin_bill_pay.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_bill_pay.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            `;`
- Expression: `bills.map(b => `
                <tr>
                    <td><strong>#${securityManager.escapeHtml(b.id || '')}</strong></td>
                    <td>${securityManager.escapeHtml(b.user_email || '')}</td>
                    <td>${securityManager.escapeHtml(b.payee_name || '')}</td>
                    <td>$${(b.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td><span class="badge bg-info">${securityManager.escapeHtml(b.frequency || '')}</span></td>
                    <td>${new Date(b.due_date).toLocaleDateString()}</td>
                    <td><span class="status-badge status-${b.status || 'scheduled'}">${securityManager.escapeHtml(b.status || '')}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary me-1" onclick="editBill('${b.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="cancelBill('${b.id}', '${securityManager.escapeHtml(b.payee_name || '')}', ${b.amount}, '${b.due_date}')">Cancel</button>
                    </td>
                </tr>
            `).join('')`
  Line: `.innerHTML = bills.map(b => `
                <tr>
                    <td><strong>#${securityManager.escapeHtml(b.id || '')}</strong></td>
                    <td>${securityManager.escapeHtml(b.user_email || '')}</td>
                    <td>${securityManager.escapeHtml(b.payee_name || '')}</td>
                    <td>$${(b.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td><span class="badge bg-info">${securityManager.escapeHtml(b.frequency || '')}</span></td>
                    <td>${new Date(b.due_date).toLocaleDateString()}</td>
                    <td><span class="status-badge status-${b.status || 'scheduled'}">${securityManager.escapeHtml(b.status || '')}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary me-1" onclick="editBill('${b.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="cancelBill('${b.id}', '${securityManager.escapeHtml(b.payee_name || '')}', ${b.amount}, '${b.due_date}')">Cancel</button>
                    </td>
                </tr>
            `).join('');`
- Expression: `(data.data || []).map(p => `
                        <tr>
                            <td>${securityManager.escapeHtml(p.id || '')}</td>
                            <td>${securityManager.escapeHtml(p.payee_name || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(p.account_number || '', false)}</span></td>
                            <td><span class="masked-text">${securityManager.maskPII(p.routing_number || '', false)}</span></td>
                            <td>${securityManager.escapeHtml(p.category || '')}</td>
                            <td>${p.active_users || 0}</td>
                            <td><span class="badge ${p.status === 'active' ? 'bg-success' : p.status === 'inactive' ? 'bg-danger' : 'bg-secondary'}">${securityManager.escapeHtml(p.status ? p.status.toUpperCase() : 'PENDING')}</span></td>
                            <td><button class="btn btn-sm btn-warning" onclick="editPayee('${p.id}')">Edit</button></td>
                        </tr>
                    `).join('') || '<tr><td colspan="8" class="text-center text-muted">No payees found</td></tr>'`
  Line: `.innerHTML = (data.data || []).map(p => `
                        <tr>
                            <td>${securityManager.escapeHtml(p.id || '')}</td>
                            <td>${securityManager.escapeHtml(p.payee_name || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(p.account_number || '', false)}</span></td>
                            <td><span class="masked-text">${securityManager.maskPII(p.routing_number || '', false)}</span></td>
                            <td>${securityManager.escapeHtml(p.category || '')}</td>
                            <td>${p.active_users || 0}</td>
                            <td><span class="badge ${p.status === 'active' ? 'bg-success' : p.status === 'inactive' ? 'bg-danger' : 'bg-secondary'}">${securityManager.escapeHtml(p.status ? p.status.toUpperCase() : 'PENDING')}</span></td>
                            <td><button class="btn btn-sm btn-warning" onclick="editPayee('${p.id}')">Edit</button></td>
                        </tr>
                    `).join('') || '<tr><td colspan="8" class="text-center text-muted">No payees found</td></tr>';`
- Expression: `paginatedPayments.map(p => `
                <tr>
                    <td>#${securityManager.escapeHtml(p.id || '')}</td>
                    <td>${securityManager.escapeHtml(p.user_email || '')}</td>
                    <td>${securityManager.escapeHtml(p.payee_name || '')}</td>
                    <td>$${(p.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td>${new Date(p.sent_date).toLocaleDateString()}</td>
                    <td>${p.delivered_date ? new Date(p.delivered_date).toLocaleDateString() : '-'}</td>
                    <td><span class="status-badge status-${p.status || 'scheduled'}">${securityManager.escapeHtml(p.status || '')}</span></td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPayment('${p.id}')">View</button></td>
                </tr>
            `).join('')`
  Line: `.innerHTML = paginatedPayments.map(p => `
                <tr>
                    <td>#${securityManager.escapeHtml(p.id || '')}</td>
                    <td>${securityManager.escapeHtml(p.user_email || '')}</td>
                    <td>${securityManager.escapeHtml(p.payee_name || '')}</td>
                    <td>$${(p.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td>${new Date(p.sent_date).toLocaleDateString()}</td>
                    <td>${p.delivered_date ? new Date(p.delivered_date).toLocaleDateString() : '-'}</td>
                    <td><span class="status-badge status-${p.status || 'scheduled'}">${securityManager.escapeHtml(p.status || '')}</span></td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPayment('${p.id}')">View</button></td>
                </tr>
            `).join('');`
- Expression: ``Are you sure you want to cancel the scheduled payment of <strong>$${formattedAmount}</strong> to <strong>${securityManager.escapeHtml(payeeName)}</strong> due on <strong>${formattedDate}</strong>?``
  Line: `.innerHTML = `Are you sure you want to cancel the scheduled payment of <strong>$${formattedAmount}</strong> to <strong>${securityManager.escapeHtml(payeeName)}</strong> due on <strong>${formattedDate}</strong>?`;`
- Expression: `'<option value="">Select user...</option>' + 
                        users.map(u => `<option value="${u.id}">${securityManager.escapeHtml(u.email)} (${securityManager.escapeHtml(u.first_name || '')} ${securityManager.escapeHtml(u.last_name || '')})</option>`).join('')`
  Line: `.innerHTML = '<option value="">Select user...</option>' + 
                        users.map(u => `<option value="${u.id}">${securityManager.escapeHtml(u.email)} (${securityManager.escapeHtml(u.first_name || '')} ${securityManager.escapeHtml(u.last_name || '')})</option>`).join('');`
- Expression: `'<option value="">Select payee...</option>' + 
                        payees.map(p => `<option value="${p.id}">${securityManager.escapeHtml(p.payee_name)}</option>`).join('')`
  Line: `.innerHTML = '<option value="">Select payee...</option>' + 
                        payees.map(p => `<option value="${p.id}">${securityManager.escapeHtml(p.payee_name)}</option>`).join('');`
### 📄 [admin_blockchain.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_blockchain.html)
- Expression: ``
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            ``
  Line: `.innerHTML = `
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;`
- Expression: `data.data.map(settlement => {
                    const threshold = CONFIG.confirmationThresholds[settlement.chain] || 12`
  Line: `.innerHTML = data.data.map(settlement => {
                    const threshold = CONFIG.confirmationThresholds[settlement.chain] || 12;`
### 📄 [admin_bulk_operations.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_bulk_operations.html)
- Expression: ``<i class="fas fa-info-circle me-2"></i>${message}``
  Line: `.innerHTML = `<i class="fas fa-info-circle me-2"></i>${message}`;`
### 📄 [admin_currency_exchange.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_currency_exchange.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            `;`
- Expression: `transactions.map(tx => {
                const userDisplay = securityManager.maskPII(tx.user_name || 'Unknown', false)`
  Line: `.innerHTML = transactions.map(tx => {
                const userDisplay = securityManager.maskPII(tx.user_name || 'Unknown', false);`
### 📄 [admin_dashboard_hub.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_dashboard_hub.html)
- Expression: ``
                            <span class="text-white">${adminUserInfo.email}</span>
                            <small class="text-muted ms-2">(${adminUserInfo.admin_role})</small>
                        ``
  Line: `.innerHTML = `
                            <span class="text-white">${adminUserInfo.email}</span>
                            <small class="text-muted ms-2">(${adminUserInfo.admin_role})</small>
                        `;`
- Expression: ``<div class="text-muted"><small>No recent activity logged</small></div>``
  Line: `.innerHTML = `<div class="text-muted"><small>No recent activity logged</small></div>`;`
- Expression: `logs.map(entry => `
                    <div class="d-flex align-items-start mb-2 pb-2 border-bottom">
                        <span class="badge bg-secondary me-2 text-nowrap">${new Date(entry.timestamp || entry.created_at).toLocaleTimeString()}</span>
                        <div>
                            <strong class="small">${entry.action || entry.action_type || 'Action'}</strong>
                            <span class="text-muted small ms-1">${entry.details || ''}</span>
                            ${entry.user || entry.admin_email ? `<br><small class="text-muted">${entry.user || entry.admin_email}</small>` : ''}
                        </div>
                    </div>
                `).join('')`
  Line: `.innerHTML = logs.map(entry => `
                    <div class="d-flex align-items-start mb-2 pb-2 border-bottom">
                        <span class="badge bg-secondary me-2 text-nowrap">${new Date(entry.timestamp || entry.created_at).toLocaleTimeString()}</span>
                        <div>
                            <strong class="small">${entry.action || entry.action_type || 'Action'}</strong>
                            <span class="text-muted small ms-1">${entry.details || ''}</span>
                            ${entry.user || entry.admin_email ? `<br><small class="text-muted">${entry.user || entry.admin_email}</small>` : ''}
                        </div>
                    </div>
                `).join('');`
- Expression: ``<div class="text-muted"><small>No recent activity logged</small></div>``
  Line: `.innerHTML = `<div class="text-muted"><small>No recent activity logged</small></div>`;`
### 📄 [admin_fraud_detection.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_fraud_detection.html)
- Expression: ``
                <span style="color: ${config.color}`
  Line: `.innerHTML = `
                <span style="color: ${config.color};`
- Expression: `result.transactions.map(txn => `
                    <tr data-txn-id="${txn.id}" style="cursor: pointer`
  Line: `.innerHTML = result.transactions.map(txn => `
                    <tr data-txn-id="${txn.id}" style="cursor: pointer;`
- Expression: `result.devices.map(dev => `
                    <tr>
                        <td><strong>${dev.device_id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(dev.user_email)}</td>
                        <td>${dev.browser}</td>
                        <td>${dev.ip_address}</td>
                        <td>${dev.location}</td>
                        <td><span class="badge ${dev.risk_level === 'high' ? 'bg-danger' : dev.risk_level === 'medium' ? 'bg-warning' : 'bg-success'}">${dev.risk_level}</span></td>
                        <td>${new Date(dev.last_active).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-warning" onclick="flagDevice('${dev.device_id}')">Flag</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = result.devices.map(dev => `
                    <tr>
                        <td><strong>${dev.device_id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(dev.user_email)}</td>
                        <td>${dev.browser}</td>
                        <td>${dev.ip_address}</td>
                        <td>${dev.location}</td>
                        <td><span class="badge ${dev.risk_level === 'high' ? 'bg-danger' : dev.risk_level === 'medium' ? 'bg-warning' : 'bg-success'}">${dev.risk_level}</span></td>
                        <td>${new Date(dev.last_active).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-warning" onclick="flagDevice('${dev.device_id}')">Flag</button></td>
                    </tr>
                `).join('');`
- Expression: `result.rules.map(rule => `
                    <tr>
                        <td><strong>#${rule.id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(rule.rule_name)}</td>
                        <td>${rule.trigger_condition}</td>
                        <td><span class="badge bg-info">${rule.action}</span></td>
                        <td><strong>${rule.matches_24h}</strong></td>
                        <td><span class="badge ${rule.is_active ? 'bg-success' : 'bg-secondary'}">${rule.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td>${new Date(rule.last_modified).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="editRule('${rule.id}')">Edit</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = result.rules.map(rule => `
                    <tr>
                        <td><strong>#${rule.id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(rule.rule_name)}</td>
                        <td>${rule.trigger_condition}</td>
                        <td><span class="badge bg-info">${rule.action}</span></td>
                        <td><strong>${rule.matches_24h}</strong></td>
                        <td><span class="badge ${rule.is_active ? 'bg-success' : 'bg-secondary'}">${rule.is_active ? 'Active' : 'Inactive'}</span></td>
                        <td>${new Date(rule.last_modified).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="editRule('${rule.id}')">Edit</button></td>
                    </tr>
                `).join('');`
- Expression: `result.matches.map(match => `
                    <tr>
                        <td><strong>#${match.id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(match.user_name)}</td>
                        <td><span class="badge bg-warning">${match.sanction_list}</span></td>
                        <td>${match.match_score}%</td>
                        <td><strong>${match.confidence}%</strong></td>
                        <td>${new Date(match.detection_date).toLocaleDateString()}</td>
                        <td><span class="badge badge-flagged">Under Review</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewSanctions('${match.id}')">Review</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = result.matches.map(match => `
                    <tr>
                        <td><strong>#${match.id.substring(0, 12)}</strong></td>
                        <td>${securityManager.escapeHtml(match.user_name)}</td>
                        <td><span class="badge bg-warning">${match.sanction_list}</span></td>
                        <td>${match.match_score}%</td>
                        <td><strong>${match.confidence}%</strong></td>
                        <td>${new Date(match.detection_date).toLocaleDateString()}</td>
                        <td><span class="badge badge-flagged">Under Review</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewSanctions('${match.id}')">Review</button></td>
                    </tr>
                `).join('');`
### 📄 [admin_fund.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_fund.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${escapeHtml(message)}</span>
            `;`
- Expression: `users.map(u => `
                        <div class="autocomplete-item" onclick="selectUser('${type}', ${u.id}, '${escapeHtml(u.email)}', ${u.balance || 0}, '${escapeHtml(u.full_name)}')">
                            <div><strong>${escapeHtml(u.full_name)}</strong></div>
                            <small class="text-muted">${escapeHtml(u.email)} • Balance: $${(u.balance || 0).toFixed(2)}</small>
                        </div>
                    `).join('')`
  Line: `.innerHTML = users.map(u => `
                        <div class="autocomplete-item" onclick="selectUser('${type}', ${u.id}, '${escapeHtml(u.email)}', ${u.balance || 0}, '${escapeHtml(u.full_name)}')">
                            <div><strong>${escapeHtml(u.full_name)}</strong></div>
                            <small class="text-muted">${escapeHtml(u.email)} • Balance: $${(u.balance || 0).toFixed(2)}</small>
                        </div>
                    `).join('');`
- Expression: `state.pendingApprovals.map(approval => `
                        <div class="card mb-3">
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-8">
                                        <h6>${approval.operation_type === 'fund' ? 'Fund' : 'Adjust'} - <span class="text-muted">${escapeHtml(approval.user_email)}</span></h6>
                                        <p class="mb-1"><strong>Amount:</strong> $${approval.amount.toFixed(2)}</p>
                                        <p class="mb-1"><small>${approval.reason}</small></p>
                                        <small class="text-muted">Requested by: ${escapeHtml(approval.requested_by)} • ${new Date(approval.created_at).toLocaleString()}</small>
                                    </div>
                                    <div class="col-md-4 text-end">
                                        <button class="btn btn-sm btn-success me-2" onclick="approveOperation('${approval.id}')">
                                            <i class="fas fa-check"></i> Approve
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="rejectOperation('${approval.id}')">
                                            <i class="fas fa-times"></i> Reject
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')`
  Line: `.innerHTML = state.pendingApprovals.map(approval => `
                        <div class="card mb-3">
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-8">
                                        <h6>${approval.operation_type === 'fund' ? 'Fund' : 'Adjust'} - <span class="text-muted">${escapeHtml(approval.user_email)}</span></h6>
                                        <p class="mb-1"><strong>Amount:</strong> $${approval.amount.toFixed(2)}</p>
                                        <p class="mb-1"><small>${approval.reason}</small></p>
                                        <small class="text-muted">Requested by: ${escapeHtml(approval.requested_by)} • ${new Date(approval.created_at).toLocaleString()}</small>
                                    </div>
                                    <div class="col-md-4 text-end">
                                        <button class="btn btn-sm btn-success me-2" onclick="approveOperation('${approval.id}')">
                                            <i class="fas fa-check"></i> Approve
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="rejectOperation('${approval.id}')">
                                            <i class="fas fa-times"></i> Reject
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('');`
- Expression: `state.recentOperations.map(op => `
                    <div class="history-item">
                        <div class="row">
                            <div class="col-md-8">
                                <p class="mb-1"><strong>${escapeHtml(op.user_email)}</strong></p>
                                <p class="mb-1"><small>${escapeHtml(op.reason || op.notes || 'No description')}</small></p>
                                <small class="text-muted">
                                    <span class="ref-badge">${op.transaction_ref}</span>
                                    ${op.ticket_reference ? `• Ticket: ${escapeHtml(op.ticket_reference)}` : ''}
                                </small>
                            </div>
                            <div class="col-md-4 text-end">
                                <p class="mb-1">
                                    <span class="badge ${op.operation_type === 'fund' ? 'badge-credit' : (op.operation_type === 'credit' ? 'badge-credit' : 'badge-debit')}">
                                        ${(op.operation_type || 'OPERATION').toUpperCase()}
                                    </span>
                                    ${op.approval_required ? '<span class="badge badge-pending ms-1">PENDING</span>' : ''}
                                    ${op.status === 'approved' ? '<span class="badge badge-approved ms-1">APPROVED</span>' : ''}
                                </p>
                                <p class="mb-0">
                                    <span class="${op.operation_type === 'fund' || op.operation_type === 'credit' ? 'amount-positive' : 'amount-negative'}">
                                        ${op.operation_type === 'fund' || op.operation_type === 'credit' ? '+' : '-'}$${op.amount.toFixed(2)}
                                    </span>
                                </p>
                                <small class="text-muted">${new Date(op.created_at).toLocaleString()}</small>
                            </div>
                        </div>
                    </div>
                `).join('')`
  Line: `.innerHTML = state.recentOperations.map(op => `
                    <div class="history-item">
                        <div class="row">
                            <div class="col-md-8">
                                <p class="mb-1"><strong>${escapeHtml(op.user_email)}</strong></p>
                                <p class="mb-1"><small>${escapeHtml(op.reason || op.notes || 'No description')}</small></p>
                                <small class="text-muted">
                                    <span class="ref-badge">${op.transaction_ref}</span>
                                    ${op.ticket_reference ? `• Ticket: ${escapeHtml(op.ticket_reference)}` : ''}
                                </small>
                            </div>
                            <div class="col-md-4 text-end">
                                <p class="mb-1">
                                    <span class="badge ${op.operation_type === 'fund' ? 'badge-credit' : (op.operation_type === 'credit' ? 'badge-credit' : 'badge-debit')}">
                                        ${(op.operation_type || 'OPERATION').toUpperCase()}
                                    </span>
                                    ${op.approval_required ? '<span class="badge badge-pending ms-1">PENDING</span>' : ''}
                                    ${op.status === 'approved' ? '<span class="badge badge-approved ms-1">APPROVED</span>' : ''}
                                </p>
                                <p class="mb-0">
                                    <span class="${op.operation_type === 'fund' || op.operation_type === 'credit' ? 'amount-positive' : 'amount-negative'}">
                                        ${op.operation_type === 'fund' || op.operation_type === 'credit' ? '+' : '-'}$${op.amount.toFixed(2)}
                                    </span>
                                </p>
                                <small class="text-muted">${new Date(op.created_at).toLocaleString()}</small>
                            </div>
                        </div>
                    </div>
                `).join('');`
### 📄 [admin_hmda.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_hmda.html)
- Expression: `apps.data?.map(app => `
                    <tr>
                        <td><strong>${app.id}</strong></td>
                        <td>${app.applicant_name}</td>
                        <td>$${app.loan_amount?.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td>${app.property_type}</td>
                        <td>${app.action_type}</td>
                        <td><span class="status-badge status-${app.decision}">${app.decision}</span></td>
                        <td>${new Date(app.application_date).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-info">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No applications found</td></tr>'`
  Line: `.innerHTML = apps.data?.map(app => `
                    <tr>
                        <td><strong>${app.id}</strong></td>
                        <td>${app.applicant_name}</td>
                        <td>$${app.loan_amount?.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td>${app.property_type}</td>
                        <td>${app.action_type}</td>
                        <td><span class="status-badge status-${app.decision}">${app.decision}</span></td>
                        <td>${new Date(app.application_date).toLocaleDateString()}</td>
                        <td><button class="btn btn-sm btn-info">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No applications found</td></tr>';`
- Expression: `applicants.data?.map(app => `
                    <tr>
                        <td>${app.id}</td>
                        <td>${app.name}</td>
                        <td>${app.ethnicity || 'N/A'}</td>
                        <td>${app.gender || 'N/A'}</td>
                        <td>$${app.income?.toLocaleString('en-US', {minimumFractionDigits: 0})}</td>
                        <td>${app.credit_score || 'N/A'}</td>
                        <td>${app.application_count || 0}</td>
                        <td><button class="btn btn-sm btn-primary">Details</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No applicants found</td></tr>'`
  Line: `.innerHTML = applicants.data?.map(app => `
                    <tr>
                        <td>${app.id}</td>
                        <td>${app.name}</td>
                        <td>${app.ethnicity || 'N/A'}</td>
                        <td>${app.gender || 'N/A'}</td>
                        <td>$${app.income?.toLocaleString('en-US', {minimumFractionDigits: 0})}</td>
                        <td>${app.credit_score || 'N/A'}</td>
                        <td>${app.application_count || 0}</td>
                        <td><button class="btn btn-sm btn-primary">Details</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No applicants found</td></tr>';`
- Expression: `submissions.data?.map(sub => `
                    <tr>
                        <td>${sub.id}</td>
                        <td>${sub.year}</td>
                        <td>Q${sub.quarter}</td>
                        <td>${sub.record_count}</td>
                        <td><span class="status-badge status-${sub.status}">${sub.status}</span></td>
                        <td>${new Date(sub.submitted_date).toLocaleDateString()}</td>
                        <td><span class="badge bg-${sub.validation_status === 'passed' ? 'success' : 'warning'}">${sub.validation_status}</span></td>
                        <td><button class="btn btn-sm btn-primary">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No submissions found</td></tr>'`
  Line: `.innerHTML = submissions.data?.map(sub => `
                    <tr>
                        <td>${sub.id}</td>
                        <td>${sub.year}</td>
                        <td>Q${sub.quarter}</td>
                        <td>${sub.record_count}</td>
                        <td><span class="status-badge status-${sub.status}">${sub.status}</span></td>
                        <td>${new Date(sub.submitted_date).toLocaleDateString()}</td>
                        <td><span class="badge bg-${sub.validation_status === 'passed' ? 'success' : 'warning'}">${sub.validation_status}</span></td>
                        <td><button class="btn btn-sm btn-primary">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No submissions found</td></tr>';`
### 📄 [admin_international_compliance.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_international_compliance.html)
- Expression: ``
                <div style="display: flex`
  Line: `.innerHTML = `
                <div style="display: flex;`
- Expression: ``
                        <div class="sanctions-unavailable">
                            <h6><i class="fas fa-exclamation-triangle"></i> Screening Unavailable</h6>
                            <p class="mb-2">The sanctions screening service is currently unavailable. This may be due to:</p>
                            <ul class="mb-0">
                                <li>Scheduled maintenance on external API</li>
                                <li>Network connectivity issue</li>
                                <li>Service timeout</li>
                            </ul>
                            <p class="mt-3 mb-0"><small>Impact: Transactions cannot be cleared until screening is available.</small></p>
                        </div>
                    ``
  Line: `.innerHTML = `
                        <div class="sanctions-unavailable">
                            <h6><i class="fas fa-exclamation-triangle"></i> Screening Unavailable</h6>
                            <p class="mb-2">The sanctions screening service is currently unavailable. This may be due to:</p>
                            <ul class="mb-0">
                                <li>Scheduled maintenance on external API</li>
                                <li>Network connectivity issue</li>
                                <li>Service timeout</li>
                            </ul>
                            <p class="mt-3 mb-0"><small>Impact: Transactions cannot be cleared until screening is available.</small></p>
                        </div>
                    `;`
- Expression: ``
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i> <strong>No sanctions matches found</strong>
                                <br><small>${name} passed screening for ${database.toUpperCase()} database</small>
                            </div>
                        ``
  Line: `.innerHTML = `
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle"></i> <strong>No sanctions matches found</strong>
                                <br><small>${name} passed screening for ${database.toUpperCase()} database</small>
                            </div>
                        `;`
- Expression: ``
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i> Screening encountered an error. Retrying...
                    </div>
                ``
  Line: `.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i> Screening encountered an error. Retrying...
                    </div>
                `;`
- Expression: `data.documents.map(doc => `
                        <a href="#" class="list-group-item list-group-item-action">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <i class="fas fa-file"></i> ${securityManager.escapeHtml(doc.filename)}
                                    <br><small class="text-muted">${doc.type} • ${new Date(doc.uploaded_at).toLocaleDateString()}</small>
                                </div>
                                <button class="btn btn-sm btn-outline-primary" onclick="downloadDocument('${doc.id}')">
                                    <i class="fas fa-download"></i>
                                </button>
                            </div>
                        </a>
                    `).join('')`
  Line: `.innerHTML = data.documents.map(doc => `
                        <a href="#" class="list-group-item list-group-item-action">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <i class="fas fa-file"></i> ${securityManager.escapeHtml(doc.filename)}
                                    <br><small class="text-muted">${doc.type} • ${new Date(doc.uploaded_at).toLocaleDateString()}</small>
                                </div>
                                <button class="btn btn-sm btn-outline-primary" onclick="downloadDocument('${doc.id}')">
                                    <i class="fas fa-download"></i>
                                </button>
                            </div>
                        </a>
                    `).join('');`
### 📄 [admin_kyc.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_kyc.html)
- Expression: ``<tr><td colspan="10" class="text-center py-4 text-muted">No submissions matched active filters.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">No submissions matched active filters.</td></tr>`;`
- Expression: ``
                    <td><input type="checkbox" class="row-checkbox" data-id="${k.id}" onclick="updateSelected()"></td>
                    <td>
                        <div class="fw-bold">${k.user?.full_name || 'N/A'}</div>
                        <div class="text-muted small">${k.user?.email || 'N/A'}</div>
                    </td>
                    <td>
                        <span class="text-uppercase small font-bold">${k.document_type}</span>
                        <div class="text-muted small">${k.document_number || 'N/A'}</div>
                    </td>
                    <td>${new Date(k.submitted_at).toLocaleDateString()}</td>
                    <td>${pendingStr}</td>
                    <td>${slaBadge}</td>
                    <td>${riskBadge}</td>
                    <td>${assignee}</td>
                    <td><span class="badge-status badge-${k.status}">${k.status}</span></td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-primary" onclick="openReviewModal(${k.id})">
                            <i class="fas fa-eye me-1"></i> Review
                        </button>
                    </td>
                ``
  Line: `.innerHTML = `
                    <td><input type="checkbox" class="row-checkbox" data-id="${k.id}" onclick="updateSelected()"></td>
                    <td>
                        <div class="fw-bold">${k.user?.full_name || 'N/A'}</div>
                        <div class="text-muted small">${k.user?.email || 'N/A'}</div>
                    </td>
                    <td>
                        <span class="text-uppercase small font-bold">${k.document_type}</span>
                        <div class="text-muted small">${k.document_number || 'N/A'}</div>
                    </td>
                    <td>${new Date(k.submitted_at).toLocaleDateString()}</td>
                    <td>${pendingStr}</td>
                    <td>${slaBadge}</td>
                    <td>${riskBadge}</td>
                    <td>${assignee}</td>
                    <td><span class="badge-status badge-${k.status}">${k.status}</span></td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-primary" onclick="openReviewModal(${k.id})">
                            <i class="fas fa-eye me-1"></i> Review
                        </button>
                    </td>
                `;`
- Expression: ``
                <p>Are you sure you want to approve the <strong>${selectedIds.size}</strong> selected submissions?</p>
                <div class="alert alert-warning small">This bypassing dual manual checklist verification for all items. Proceed with caution.</div>
            ``
  Line: `.innerHTML = `
                <p>Are you sure you want to approve the <strong>${selectedIds.size}</strong> selected submissions?</p>
                <div class="alert alert-warning small">This bypassing dual manual checklist verification for all items. Proceed with caution.</div>
            `;`
- Expression: ``
                <p>Are you sure you want to reject the <strong>${selectedIds.size}</strong> selected submissions?</p>
                <label class="form-label font-bold small">Please select a standard bulk rejection reason</label>
                <select id="bulkRejectionReason" class="form-select mb-3">
                    <option value="POOR_IMAGE_QUALITY">POOR_IMAGE_QUALITY - Blurry document</option>
                    <option value="NAME_MISMATCH">NAME_MISMATCH - Profile name doesn't match ID</option>
                    <option value="EXPIRED_DOCUMENT">EXPIRED_DOCUMENT - ID is expired</option>
                </select>
            ``
  Line: `.innerHTML = `
                <p>Are you sure you want to reject the <strong>${selectedIds.size}</strong> selected submissions?</p>
                <label class="form-label font-bold small">Please select a standard bulk rejection reason</label>
                <select id="bulkRejectionReason" class="form-select mb-3">
                    <option value="POOR_IMAGE_QUALITY">POOR_IMAGE_QUALITY - Blurry document</option>
                    <option value="NAME_MISMATCH">NAME_MISMATCH - Profile name doesn't match ID</option>
                    <option value="EXPIRED_DOCUMENT">EXPIRED_DOCUMENT - ID is expired</option>
                </select>
            `;`
### 📄 [admin_lending.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_lending.html)
- Expression: ``<tr><td colspan="8" class="text-center py-3 text-muted">No pending loan applications.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="8" class="text-center py-3 text-muted">No pending loan applications.</td></tr>`;`
- Expression: ``
                    <td><strong>${a.id}</strong></td>
                    <td class="font-monospace">${a.owner_id || a.user_id}</td>
                    <td>$${(a.amount || 0).toLocaleString()}</td>
                    <td>${a.term_months} Months</td>
                    <td>${a.purpose || 'Personal Loan'}</td>
                    <td>${a.created_at ? new Date(a.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td><span class="status-badge status-pending">${a.status}</span></td>
                    <td class="text-end">
                        <button class="btn btn-xs btn-success me-1" onclick="openApproveModal(${a.id})"><i class="fas fa-check"></i> Approve</button>
                        <button class="btn btn-xs btn-danger me-1" onclick="openRejectModal(${a.id})"><i class="fas fa-times"></i> Reject</button>
                    </td>
                ``
  Line: `.innerHTML = `
                    <td><strong>${a.id}</strong></td>
                    <td class="font-monospace">${a.owner_id || a.user_id}</td>
                    <td>$${(a.amount || 0).toLocaleString()}</td>
                    <td>${a.term_months} Months</td>
                    <td>${a.purpose || 'Personal Loan'}</td>
                    <td>${a.created_at ? new Date(a.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td><span class="status-badge status-pending">${a.status}</span></td>
                    <td class="text-end">
                        <button class="btn btn-xs btn-success me-1" onclick="openApproveModal(${a.id})"><i class="fas fa-check"></i> Approve</button>
                        <button class="btn btn-xs btn-danger me-1" onclick="openRejectModal(${a.id})"><i class="fas fa-times"></i> Reject</button>
                    </td>
                `;`
- Expression: ``<tr><td colspan="9" class="text-center py-3 text-muted">No loans matches filters.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="9" class="text-center py-3 text-muted">No loans matches filters.</td></tr>`;`
- Expression: ``
                    <td><strong>${l.id}</strong></td>
                    <td class="font-monospace">${l.owner_id || '—'}</td>
                    <td>$${parseFloat(l.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td>${parseFloat(l.interest_rate || 0).toFixed(2)}%</td>
                    <td>${l.term_months} months</td>
                    <td class="fw-bold">$${parseFloat(l.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td><span class="status-badge ${statusClass}">${l.status}</span></td>
                    <td>${l.next_payment_date || 'N/A'}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-info" onclick="viewLoanModifications(${l.id})">
                            <i class="fas fa-history"></i> History
                        </button>
                        ${l.status === 'approved' ? `
                            <button class="btn btn-sm btn-success" onclick="activateLoan(${l.id})">
                                <i class="fas fa-coins"></i> Disburse
                            </button>
                        ` : ''}
                    </td>
                ``
  Line: `.innerHTML = `
                    <td><strong>${l.id}</strong></td>
                    <td class="font-monospace">${l.owner_id || '—'}</td>
                    <td>$${parseFloat(l.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td>${parseFloat(l.interest_rate || 0).toFixed(2)}%</td>
                    <td>${l.term_months} months</td>
                    <td class="fw-bold">$${parseFloat(l.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td><span class="status-badge ${statusClass}">${l.status}</span></td>
                    <td>${l.next_payment_date || 'N/A'}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-info" onclick="viewLoanModifications(${l.id})">
                            <i class="fas fa-history"></i> History
                        </button>
                        ${l.status === 'approved' ? `
                            <button class="btn btn-sm btn-success" onclick="activateLoan(${l.id})">
                                <i class="fas fa-coins"></i> Disburse
                            </button>
                        ` : ''}
                    </td>
                `;`
- Expression: ``<tr><td colspan="6" class="text-center py-3 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading...</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-muted"><span class="spinner-border spinner-border-sm me-2"></span> Loading...</td></tr>`;`
- Expression: ``<tr><td colspan="6" class="text-center py-3 text-muted">No modification logs for this loan.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-muted">No modification logs for this loan.</td></tr>`;`
- Expression: `items.map(item => `
                    <tr>
                        <td>${item.id}</td>
                        <td><span class="badge bg-secondary">${item.modification_type}</span></td>
                        <td>${item.requested_by || 'Admin'}</td>
                        <td>${item.effective_date ? new Date(item.effective_date).toLocaleDateString() : 'N/A'}</td>
                        <td>${item.reason || 'N/A'}</td>
                        <td><span class="badge bg-success">Approved</span></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = items.map(item => `
                    <tr>
                        <td>${item.id}</td>
                        <td><span class="badge bg-secondary">${item.modification_type}</span></td>
                        <td>${item.requested_by || 'Admin'}</td>
                        <td>${item.effective_date ? new Date(item.effective_date).toLocaleDateString() : 'N/A'}</td>
                        <td>${item.reason || 'N/A'}</td>
                        <td><span class="badge bg-success">Approved</span></td>
                    </tr>
                `).join('');`
- Expression: ``<tr><td colspan="6" class="text-center py-3 text-danger">Failed to load modifications.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-danger">Failed to load modifications.</td></tr>`;`
### 📄 [admin_lending_compliance.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_lending_compliance.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            `;`
- Expression: `(data.data || []).map(c => `
                        <tr>
                            <td>${securityManager.escapeHtml(c.id || '')}</td>
                            <td>${securityManager.escapeHtml(c.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(c.borrower_name || 'N/A', false)}</span></td>
                            <td>${new Date(c.contact_date).toLocaleDateString()}</td>
                            <td>${securityManager.escapeHtml(c.contact_type || '')}</td>
                            <td>${securityManager.escapeHtml(c.outcome || '')}</td>
                            <td>${c.next_followup || 'None'}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No collections activity</td></tr>'`
  Line: `.innerHTML = (data.data || []).map(c => `
                        <tr>
                            <td>${securityManager.escapeHtml(c.id || '')}</td>
                            <td>${securityManager.escapeHtml(c.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(c.borrower_name || 'N/A', false)}</span></td>
                            <td>${new Date(c.contact_date).toLocaleDateString()}</td>
                            <td>${securityManager.escapeHtml(c.contact_type || '')}</td>
                            <td>${securityManager.escapeHtml(c.outcome || '')}</td>
                            <td>${c.next_followup || 'None'}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No collections activity</td></tr>';`
- Expression: `(data.data || []).map(h => `
                        <tr>
                            <td>${securityManager.escapeHtml(h.id || '')}</td>
                            <td>${securityManager.escapeHtml(h.account_id || '')}</td>
                            <td>${securityManager.escapeHtml(h.hold_type || '')}</td>
                            <td>${securityManager.escapeHtml(h.reason || '')}</td>
                            <td>$${(h.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>${new Date(h.created_date).toLocaleDateString()}</td>
                            <td><span class="badge bg-warning">${securityManager.escapeHtml(h.status || '')}</span></td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No account holds</td></tr>'`
  Line: `.innerHTML = (data.data || []).map(h => `
                        <tr>
                            <td>${securityManager.escapeHtml(h.id || '')}</td>
                            <td>${securityManager.escapeHtml(h.account_id || '')}</td>
                            <td>${securityManager.escapeHtml(h.hold_type || '')}</td>
                            <td>${securityManager.escapeHtml(h.reason || '')}</td>
                            <td>$${(h.amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>${new Date(h.created_date).toLocaleDateString()}</td>
                            <td><span class="badge bg-warning">${securityManager.escapeHtml(h.status || '')}</span></td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No account holds</td></tr>';`
- Expression: `(data.data || []).map(f => `
                        <tr>
                            <td>${securityManager.escapeHtml(f.id || '')}</td>
                            <td>${securityManager.escapeHtml(f.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(f.borrower_name || 'N/A', false)}</span></td>
                            <td>${securityManager.escapeHtml(f.plan_type || '')}</td>
                            <td>${f.duration_months || 0} mo</td>
                            <td>${new Date(f.start_date).toLocaleDateString()}</td>
                            <td>${new Date(f.end_date).toLocaleDateString()}</td>
                            <td><span class="badge bg-info">${securityManager.escapeHtml(f.status || '')}</span></td>
                        </tr>
                    `).join('') || '<tr><td colspan="8" class="text-center text-muted">No forbearance plans</td></tr>'`
  Line: `.innerHTML = (data.data || []).map(f => `
                        <tr>
                            <td>${securityManager.escapeHtml(f.id || '')}</td>
                            <td>${securityManager.escapeHtml(f.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(f.borrower_name || 'N/A', false)}</span></td>
                            <td>${securityManager.escapeHtml(f.plan_type || '')}</td>
                            <td>${f.duration_months || 0} mo</td>
                            <td>${new Date(f.start_date).toLocaleDateString()}</td>
                            <td>${new Date(f.end_date).toLocaleDateString()}</td>
                            <td><span class="badge bg-info">${securityManager.escapeHtml(f.status || '')}</span></td>
                        </tr>
                    `).join('') || '<tr><td colspan="8" class="text-center text-muted">No forbearance plans</td></tr>';`
- Expression: `(data.data || []).map(c => `
                        <tr>
                            <td>${securityManager.escapeHtml(c.id || '')}</td>
                            <td>${securityManager.escapeHtml(c.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(c.borrower_name || 'N/A', false)}</span></td>
                            <td>$${(c.principal || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>${new Date(c.chargeoff_date).toLocaleDateString()}</td>
                            <td>${securityManager.escapeHtml(c.reason || '')}</td>
                            <td>${securityManager.escapeHtml(c.recovery_status || 'Pending')}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No charge-offs</td></tr>'`
  Line: `.innerHTML = (data.data || []).map(c => `
                        <tr>
                            <td>${securityManager.escapeHtml(c.id || '')}</td>
                            <td>${securityManager.escapeHtml(c.loan_id || '')}</td>
                            <td><span class="masked-text">${securityManager.maskPII(c.borrower_name || 'N/A', false)}</span></td>
                            <td>$${(c.principal || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>${new Date(c.chargeoff_date).toLocaleDateString()}</td>
                            <td>${securityManager.escapeHtml(c.reason || '')}</td>
                            <td>${securityManager.escapeHtml(c.recovery_status || 'Pending')}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="7" class="text-center text-muted">No charge-offs</td></tr>';`
### 📄 [admin_management_panel.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_management_panel.html)
- Expression: `data.admins.map(admin => `
                        <div class="admin-item">
                            <div class="admin-info">
                                <div class="admin-email">${admin.email}</div>
                                <div class="admin-role">
                                    <span class="role-badge role-${(admin.admin_role || 'standard').toLowerCase()}">
                                        ${(admin.admin_role || 'STANDARD').toUpperCase()}
                                    </span>
                                    <small>Created: ${new Date(admin.created_at).toLocaleDateString()}</small>
                                </div>
                            </div>
                            <div class="admin-actions">
                                <button class="btn btn-primary btn-sm" onclick="openResetPassword('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-key"></i> Reset PWD
                                </button>
                                <button class="btn btn-warning btn-sm" onclick="openChangeRole('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-user-cog"></i> Role
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="openRevoke('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-ban"></i> Revoke
                                </button>
                            </div>
                        </div>
                    `).join('')`
  Line: `.innerHTML = data.admins.map(admin => `
                        <div class="admin-item">
                            <div class="admin-info">
                                <div class="admin-email">${admin.email}</div>
                                <div class="admin-role">
                                    <span class="role-badge role-${(admin.admin_role || 'standard').toLowerCase()}">
                                        ${(admin.admin_role || 'STANDARD').toUpperCase()}
                                    </span>
                                    <small>Created: ${new Date(admin.created_at).toLocaleDateString()}</small>
                                </div>
                            </div>
                            <div class="admin-actions">
                                <button class="btn btn-primary btn-sm" onclick="openResetPassword('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-key"></i> Reset PWD
                                </button>
                                <button class="btn btn-warning btn-sm" onclick="openChangeRole('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-user-cog"></i> Role
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="openRevoke('${admin.id}', '${admin.email}')">
                                    <i class="fas fa-ban"></i> Revoke
                                </button>
                            </div>
                        </div>
                    `).join('');`
- Expression: ``<p class="empty-state" style="color:red`
  Line: `.innerHTML = `<p class="empty-state" style="color:red;`
- Expression: `'<option value="">Choose an admin...</option>' +
                    data.admins.map(admin => 
                        `<option value="${admin.id}">${admin.email} (${admin.admin_role || 'STANDARD'})</option>`
                    ).join('')`
  Line: `.innerHTML = '<option value="">Choose an admin...</option>' +
                    data.admins.map(admin => 
                        `<option value="${admin.id}">${admin.email} (${admin.admin_role || 'STANDARD'})</option>`
                    ).join('');`
### 📄 [admin_mfa_setup.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_mfa_setup.html)
- Expression: `data.backup_codes
                            .map(code => `<div class="backup-code">${code}</div>`)
                            .join('')`
  Line: `.innerHTML = data.backup_codes
                            .map(code => `<div class="backup-code">${code}</div>`)
                            .join('');`
### 📄 [admin_mobile_deposit.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_mobile_deposit.html)
- Expression: ``
                    <span class="toast-icon">${icons[type]}</span>
                    <span class="toast-message">${securityManager.escapeHtml(message)}</span>
                    <span class="toast-close" onclick="this.parentElement.remove()">✕</span>
                ``
  Line: `.innerHTML = `
                    <span class="toast-icon">${icons[type]}</span>
                    <span class="toast-message">${securityManager.escapeHtml(message)}</span>
                    <span class="toast-close" onclick="this.parentElement.remove()">✕</span>
                `;`
- Expression: `data.data.map(deposit => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(deposit.id)}</strong></td>
                        <td>${securityManager.escapeHtml(deposit.user_email)}</td>
                        <td>${formatCurrency(deposit.amount)}</td>
                        <td>${securityManager.escapeHtml(deposit.check_number)}</td>
                        <td>
                            <span class="badge ${getIQABadgeClass(deposit.iqa_score)}">
                                ${deposit.iqa_score || 0}%
                            </span>
                        </td>
                        <td>
                            ${deposit.is_duplicate ? '<span class="badge-duplicate">⚠ DUPLICATE</span>' : '<span class="badge badge-passed">✓ Unique</span>'}
                        </td>
                        <td>
                            ${deposit.endorsement_verified ? 
                                '<span class="endorsement-verified">✓ Present</span>' : 
                                '<span class="endorsement-missing">⚠ Missing</span>'}
                        </td>
                        <td><span class="badge badge-${getStatusClass(deposit.status)}">${deposit.status}</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewDeposit('${deposit.id}', '${deposit.amount}', '${deposit.check_number}')">Review</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = data.data.map(deposit => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(deposit.id)}</strong></td>
                        <td>${securityManager.escapeHtml(deposit.user_email)}</td>
                        <td>${formatCurrency(deposit.amount)}</td>
                        <td>${securityManager.escapeHtml(deposit.check_number)}</td>
                        <td>
                            <span class="badge ${getIQABadgeClass(deposit.iqa_score)}">
                                ${deposit.iqa_score || 0}%
                            </span>
                        </td>
                        <td>
                            ${deposit.is_duplicate ? '<span class="badge-duplicate">⚠ DUPLICATE</span>' : '<span class="badge badge-passed">✓ Unique</span>'}
                        </td>
                        <td>
                            ${deposit.endorsement_verified ? 
                                '<span class="endorsement-verified">✓ Present</span>' : 
                                '<span class="endorsement-missing">⚠ Missing</span>'}
                        </td>
                        <td><span class="badge badge-${getStatusClass(deposit.status)}">${deposit.status}</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewDeposit('${deposit.id}', '${deposit.amount}', '${deposit.check_number}')">Review</button></td>
                    </tr>
                `).join('');`
- Expression: `data.data.map(img => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(img.id)}</strong></td>
                        <td>#${securityManager.escapeHtml(img.deposit_id)}</td>
                        <td><span class="badge bg-info">${img.side}</span></td>
                        <td><span class="badge ${getIQAStatusBadgeClass(img.iqa_status)}">${img.iqa_status}</span></td>
                        <td><strong>${img.quality_score || 0}%</strong></td>
                        <td>
                            ${img.micr_match ? 
                                '<span class="badge bg-success">✓ Match</span>' : 
                                '<span class="badge bg-danger">✕ Mismatch</span>'}
                        </td>
                        <td>${formatDate(img.uploaded_date)}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewImage('${img.id}')">View</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = data.data.map(img => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(img.id)}</strong></td>
                        <td>#${securityManager.escapeHtml(img.deposit_id)}</td>
                        <td><span class="badge bg-info">${img.side}</span></td>
                        <td><span class="badge ${getIQAStatusBadgeClass(img.iqa_status)}">${img.iqa_status}</span></td>
                        <td><strong>${img.quality_score || 0}%</strong></td>
                        <td>
                            ${img.micr_match ? 
                                '<span class="badge bg-success">✓ Match</span>' : 
                                '<span class="badge bg-danger">✕ Mismatch</span>'}
                        </td>
                        <td>${formatDate(img.uploaded_date)}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewImage('${img.id}')">View</button></td>
                    </tr>
                `).join('');`
- Expression: `data.data.map(ocr => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(ocr.id)}</strong></td>
                        <td>#${securityManager.escapeHtml(ocr.deposit_id)}</td>
                        <td>${formatCurrency(ocr.check_amount)}</td>
                        <td>${securityManager.escapeHtml(ocr.routing_number)}</td>
                        <td>${securityManager.maskPII(ocr.account_number)}</td>
                        <td>
                            ${ocr.routing_match && ocr.account_match ? 
                                '<span class="badge bg-success">✓ Match</span>' : 
                                '<span class="badge bg-danger">✕ Mismatch</span>'}
                        </td>
                        <td><strong>${ocr.confidence || 0}%</strong></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewOCRResult('${ocr.id}', '${ocr.deposit_id}')">Review</button></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = data.data.map(ocr => `
                    <tr>
                        <td><strong>#${securityManager.escapeHtml(ocr.id)}</strong></td>
                        <td>#${securityManager.escapeHtml(ocr.deposit_id)}</td>
                        <td>${formatCurrency(ocr.check_amount)}</td>
                        <td>${securityManager.escapeHtml(ocr.routing_number)}</td>
                        <td>${securityManager.maskPII(ocr.account_number)}</td>
                        <td>
                            ${ocr.routing_match && ocr.account_match ? 
                                '<span class="badge bg-success">✓ Match</span>' : 
                                '<span class="badge bg-danger">✕ Mismatch</span>'}
                        </td>
                        <td><strong>${ocr.confidence || 0}%</strong></td>
                        <td><button class="btn btn-sm btn-primary" onclick="reviewOCRResult('${ocr.id}', '${ocr.deposit_id}')">Review</button></td>
                    </tr>
                `).join('');`
### 📄 [admin_monitoring.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_monitoring.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            `;`
- Expression: ``
                <div class="metric-card mb-2">
                    <small class="text-muted d-block">CPU Load</small>
                    <div class="progress" style="height: 20px`
  Line: `.innerHTML = `
                <div class="metric-card mb-2">
                    <small class="text-muted d-block">CPU Load</small>
                    <div class="progress" style="height: 20px;`
- Expression: `data.alerts.map(alert => {
                const severityColor = alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'`
  Line: `.innerHTML = data.alerts.map(alert => {
                const severityColor = alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info';`
- Expression: `Object.entries(grouped).map(([cluster, items]) => {
                return `
                    <div class="cluster-group">
                        <div class="cluster-header">
                            <span><i class="fas fa-server"></i> ${securityManager.escapeHtml(cluster)}</span>
                            <span class="badge bg-info">${items.length} services</span>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Service Name</th>
                                        <th>Status</th>
                                        <th>CPU</th>
                                        <th>Memory</th>
                                        <th>Disk</th>
                                        <th>Network</th>
                                        <th>Last Updated</th>
                                        <th>Quick Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${items.map(service => {
                                        const statusColor = service.status === 'healthy' ? 'success' : service.status === 'warning' ? 'warning' : 'danger'`
  Line: `.innerHTML = Object.entries(grouped).map(([cluster, items]) => {
                return `
                    <div class="cluster-group">
                        <div class="cluster-header">
                            <span><i class="fas fa-server"></i> ${securityManager.escapeHtml(cluster)}</span>
                            <span class="badge bg-info">${items.length} services</span>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Service Name</th>
                                        <th>Status</th>
                                        <th>CPU</th>
                                        <th>Memory</th>
                                        <th>Disk</th>
                                        <th>Network</th>
                                        <th>Last Updated</th>
                                        <th>Quick Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${items.map(service => {
                                        const statusColor = service.status === 'healthy' ? 'success' : service.status === 'warning' ? 'warning' : 'danger';`
### 📄 [admin_reporting.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_reporting.html)
- Expression: ``
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            ``
  Line: `.innerHTML = `
                <i class="fas ${icons[type]}"></i>
                <span>${securityManager.escapeHtml(message)}</span>
            `;`
- Expression: ``
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Transaction ID</th>
                                <th>Amount</th>
                                <th>Type</th>
                                <th>Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.transactions.map(tx => `
                                <tr>
                                    <td><code>${securityManager.escapeHtml(String(tx.id || 'N/A'))}</code></td>
                                    <td>$${(tx.amount || 0).toFixed(2)}</td>
                                    <td>${securityManager.escapeHtml(String(tx.type || 'unknown'))}</td>
                                    <td>${new Date(tx.timestamp).toLocaleTimeString()}</td>
                                    <td><span class="badge bg-success">${securityManager.escapeHtml(String(tx.status || 'unknown'))}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ``
  Line: `.innerHTML = `
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Transaction ID</th>
                                <th>Amount</th>
                                <th>Type</th>
                                <th>Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.transactions.map(tx => `
                                <tr>
                                    <td><code>${securityManager.escapeHtml(String(tx.id || 'N/A'))}</code></td>
                                    <td>$${(tx.amount || 0).toFixed(2)}</td>
                                    <td>${securityManager.escapeHtml(String(tx.type || 'unknown'))}</td>
                                    <td>${new Date(tx.timestamp).toLocaleTimeString()}</td>
                                    <td><span class="badge bg-success">${securityManager.escapeHtml(String(tx.status || 'unknown'))}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;`
- Expression: `data.tasks.map(task => {
                    // Validate required fields
                    if (!task.task_id || !task.report_type) {
                        console.warn('Invalid task data:', task)`
  Line: `.innerHTML = data.tasks.map(task => {
                    // Validate required fields
                    if (!task.task_id || !task.report_type) {
                        console.warn('Invalid task data:', task);`
- Expression: `data.schedules.map(schedule => {
                    // Validate data before processing
                    if (!schedule.schedule_id || !schedule.report_type) {
                        console.warn('Invalid schedule data:', schedule)`
  Line: `.innerHTML = data.schedules.map(schedule => {
                    // Validate data before processing
                    if (!schedule.schedule_id || !schedule.report_type) {
                        console.warn('Invalid schedule data:', schedule);`
### 📄 [admin_reports.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_reports.html)
- Expression: `sorted.map((user, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${user.full_name || 'N/A'}</td>
                    <td>${user.email}</td>
                    <td><strong>$${(user.balance || 0).toFixed(2)}</strong></td>
                    <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
            `).join('') || '<tr><td colspan="5" class="text-center text-muted">No data</td></tr>'`
  Line: `.innerHTML = sorted.map((user, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${user.full_name || 'N/A'}</td>
                    <td>${user.email}</td>
                    <td><strong>$${(user.balance || 0).toFixed(2)}</strong></td>
                    <td><span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
            `).join('') || '<tr><td colspan="5" class="text-center text-muted">No data</td></tr>';`
- Expression: `recent.map((t, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${t.user?.email || 'N/A'}</td>
                    <td><span class="badge bg-info">${t.transaction_type}</span></td>
                    <td>$${parseFloat(t.amount).toFixed(2)}</td>
                    <td><span class="badge ${t.status === 'completed' ? 'bg-success' : t.status === 'pending' ? 'bg-warning' : 'bg-danger'}">${t.status}</span></td>
                    <td>${new Date(t.created_at).toLocaleDateString()}</td>
                </tr>
            `).join('') || '<tr><td colspan="6" class="text-center text-muted">No data</td></tr>'`
  Line: `.innerHTML = recent.map((t, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${t.user?.email || 'N/A'}</td>
                    <td><span class="badge bg-info">${t.transaction_type}</span></td>
                    <td>$${parseFloat(t.amount).toFixed(2)}</td>
                    <td><span class="badge ${t.status === 'completed' ? 'bg-success' : t.status === 'pending' ? 'bg-warning' : 'bg-danger'}">${t.status}</span></td>
                    <td>${new Date(t.created_at).toLocaleDateString()}</td>
                </tr>
            `).join('') || '<tr><td colspan="6" class="text-center text-muted">No data</td></tr>';`
### 📄 [admin_settings.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_settings.html)
- Expression: `logs.map(log => `
                    <tr>
                        <td>${new Date(log.timestamp).toLocaleString()}</td>
                        <td>${log.admin_name || log.admin_id}</td>
                        <td>${log.action}</td>
                        <td><code>${log.setting_name}</code></td>
                        <td><code class="text-muted">${log.old_value || '-'}</code></td>
                        <td><code class="text-success">${log.new_value || '-'}</code></td>
                        <td><small>${log.ip_address}</small></td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = logs.map(log => `
                    <tr>
                        <td>${new Date(log.timestamp).toLocaleString()}</td>
                        <td>${log.admin_name || log.admin_id}</td>
                        <td>${log.action}</td>
                        <td><code>${log.setting_name}</code></td>
                        <td><code class="text-muted">${log.old_value || '-'}</code></td>
                        <td><code class="text-success">${log.new_value || '-'}</code></td>
                        <td><small>${log.ip_address}</small></td>
                    </tr>
                `).join('');`
- Expression: ``
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}
                <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
            ``
  Line: `.innerHTML = `
                <strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}
                <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
            `;`
### 📄 [admin_settlement.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_settlement.html)
- Expression: ``
                <div style="padding: 12px 16px`
  Line: `.innerHTML = `
                <div style="padding: 12px 16px;`
- Expression: `state.pending.data.map(s => `
                <div class="settlement-mobile-card">
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">ID:</span><span class="settlement-mobile-value">${escapeHtml(s.id)}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Amount:</span><span class="settlement-mobile-value">$${s.amount.toLocaleString()}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Type:</span><span class="settlement-mobile-value">${escapeHtml(s.type)}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Status:</span><span class="settlement-mobile-value"><span class="status-badge">${s.status}</span></span></div>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-success w-100 mb-2" onclick="processSettlement('${s.id}')">Process</button>
                        <button class="btn btn-sm btn-danger w-100" onclick="rejectSettlement('${s.id}')">Reject</button>
                    </div>
                </div>
            `).join('')`
  Line: `.innerHTML = state.pending.data.map(s => `
                <div class="settlement-mobile-card">
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">ID:</span><span class="settlement-mobile-value">${escapeHtml(s.id)}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Amount:</span><span class="settlement-mobile-value">$${s.amount.toLocaleString()}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Type:</span><span class="settlement-mobile-value">${escapeHtml(s.type)}</span></div>
                    <div class="settlement-mobile-row"><span class="settlement-mobile-label">Status:</span><span class="settlement-mobile-value"><span class="status-badge">${s.status}</span></span></div>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-success w-100 mb-2" onclick="processSettlement('${s.id}')">Process</button>
                        <button class="btn btn-sm btn-danger w-100" onclick="rejectSettlement('${s.id}')">Reject</button>
                    </div>
                </div>
            `).join('');`
### 📄 [admin_superadmin_dashboard.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_superadmin_dashboard.html)
- Expression: ``
                <div class="text-muted">
                    <small>No recent activity logged</small>
                </div>
            ``
  Line: `.innerHTML = `
                <div class="text-muted">
                    <small>No recent activity logged</small>
                </div>
            `;`
### 📄 [admin_transactions.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_transactions.html)
- Expression: `response.data.map(t => `
                    <tr>
                        <td><input type="checkbox" class="txn-checkbox" value="${t.id}" onchange="updateBatchActions()"></td>
                        <td>${t.id}</td>
                        <td><a href="#" onclick="openUserControlCenter(${t.user_id}, '${t.user_email}')`
  Line: `.innerHTML = response.data.map(t => `
                    <tr>
                        <td><input type="checkbox" class="txn-checkbox" value="${t.id}" onchange="updateBatchActions()"></td>
                        <td>${t.id}</td>
                        <td><a href="#" onclick="openUserControlCenter(${t.user_id}, '${t.user_email}');`
- Expression: `response.data.map(d => `
                    <tr>
                        <td>${d.id}</td>
                        <td>${d.transaction_id}</td>
                        <td>${d.user_email}</td>
                        <td>${d.reason}</td>
                        <td>${formatCurrency(d.amount)}</td>
                        <td><span class="status-badge status-${d.status}">${d.status.toUpperCase()}</span></td>
                        <td>${formatDate(d.filed_date)}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewDispute(${d.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No disputes</td></tr>'`
  Line: `.innerHTML = response.data.map(d => `
                    <tr>
                        <td>${d.id}</td>
                        <td>${d.transaction_id}</td>
                        <td>${d.user_email}</td>
                        <td>${d.reason}</td>
                        <td>${formatCurrency(d.amount)}</td>
                        <td><span class="status-badge status-${d.status}">${d.status.toUpperCase()}</span></td>
                        <td>${formatDate(d.filed_date)}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewDispute(${d.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No disputes</td></tr>';`
- Expression: `response.data.map(r => `
                    <tr>
                        <td>${r.id}</td>
                        <td>${r.original_transaction_id}</td>
                        <td>${formatCurrency(r.amount)}</td>
                        <td>${r.reason}</td>
                        <td><span class="status-badge status-${r.status}">${r.status.toUpperCase()}</span></td>
                        <td>${formatDate(r.initiated_date)}</td>
                        <td>${r.completion_date ? formatDate(r.completion_date) : 'Pending'}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewReturn(${r.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No returns</td></tr>'`
  Line: `.innerHTML = response.data.map(r => `
                    <tr>
                        <td>${r.id}</td>
                        <td>${r.original_transaction_id}</td>
                        <td>${formatCurrency(r.amount)}</td>
                        <td>${r.reason}</td>
                        <td><span class="status-badge status-${r.status}">${r.status.toUpperCase()}</span></td>
                        <td>${formatDate(r.initiated_date)}</td>
                        <td>${r.completion_date ? formatDate(r.completion_date) : 'Pending'}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewReturn(${r.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No returns</td></tr>';`
- Expression: `response.data.map(r => `
                    <tr>
                        <td>${r.id}</td>
                        <td>${r.ach_entry_id}</td>
                        <td><code>${r.return_code}</code></td>
                        <td>${r.reason}</td>
                        <td>${formatCurrency(r.amount)}</td>
                        <td>${formatDate(r.return_date)}</td>
                        <td><span class="status-badge status-${r.status}">${r.status.toUpperCase()}</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewAchReturn(${r.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No ACH returns</td></tr>'`
  Line: `.innerHTML = response.data.map(r => `
                    <tr>
                        <td>${r.id}</td>
                        <td>${r.ach_entry_id}</td>
                        <td><code>${r.return_code}</code></td>
                        <td>${r.reason}</td>
                        <td>${formatCurrency(r.amount)}</td>
                        <td>${formatDate(r.return_date)}</td>
                        <td><span class="status-badge status-${r.status}">${r.status.toUpperCase()}</span></td>
                        <td><button class="btn btn-sm btn-primary" onclick="viewAchReturn(${r.id})">View</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="8" class="text-center text-muted">No ACH returns</td></tr>';`
- Expression: `'<option value="">Select User</option>' + response.data.map(u => 
                    `<option value="${u.id}" data-balance="${u.balance || 0}">${u.email}</option>`
                ).join('')`
  Line: `.innerHTML = '<option value="">Select User</option>' + response.data.map(u => 
                    `<option value="${u.id}" data-balance="${u.balance || 0}">${u.email}</option>`
                ).join('');`
### 📄 [admin_treasury.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_treasury.html)
- Expression: ``
                <div style="padding: 12px 16px`
  Line: `.innerHTML = `
                <div style="padding: 12px 16px;`
- Expression: `state.portfolios.data.map(p => `
                <div class="portfolio-mobile-card">
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Name:</span><span class="portfolio-mobile-value">${escapeHtml(p.name)}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Investor:</span><span class="portfolio-mobile-value">${escapeHtml(p.investor)}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Value:</span><span class="portfolio-mobile-value">$${p.value.toLocaleString()}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Return:</span><span class="portfolio-mobile-value">${p.return >= 0 ? '+' : ''}${p.return.toFixed(2)}%</span></div>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-primary w-100" onclick="triggerManagePortfolio('${p.id}')">
                            <i class="fas fa-cog"></i> Manage
                        </button>
                    </div>
                </div>
            `).join('')`
  Line: `.innerHTML = state.portfolios.data.map(p => `
                <div class="portfolio-mobile-card">
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Name:</span><span class="portfolio-mobile-value">${escapeHtml(p.name)}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Investor:</span><span class="portfolio-mobile-value">${escapeHtml(p.investor)}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Value:</span><span class="portfolio-mobile-value">$${p.value.toLocaleString()}</span></div>
                    <div class="portfolio-mobile-row"><span class="portfolio-mobile-label">Return:</span><span class="portfolio-mobile-value">${p.return >= 0 ? '+' : ''}${p.return.toFixed(2)}%</span></div>
                    <div class="mt-2">
                        <button class="btn btn-sm btn-primary w-100" onclick="triggerManagePortfolio('${p.id}')">
                            <i class="fas fa-cog"></i> Manage
                        </button>
                    </div>
                </div>
            `).join('');`
- Expression: ``<span class="${portfolio.return >= 0 ? 'text-success' : 'text-danger'}">${portfolio.return >= 0 ? '+' : ''}${portfolio.return.toFixed(2)}%</span>``
  Line: `.innerHTML = `<span class="${portfolio.return >= 0 ? 'text-success' : 'text-danger'}">${portfolio.return >= 0 ? '+' : ''}${portfolio.return.toFixed(2)}%</span>`;`
### 📄 [admin_users.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_users.html)
- Expression: ``
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                ``
  Line: `.innerHTML = `
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;`
- Expression: ``
                    <nav aria-label="Page navigation" class="mt-3">
                        <ul class="pagination justify-content-center">
                            <li class="page-item ${prevDisabled ? 'disabled' : ''}">
                                <button class="page-link" onclick="Pagination.goToPage(${this.currentPage - 1}, '${onPageChange}')">
                                    <i class="fas fa-chevron-left"></i> Previous
                                </button>
                            </li>
                            <li class="page-item active">
                                <span class="page-link">Page ${this.currentPage} of ${this.totalPages}</span>
                            </li>
                            <li class="page-item ${nextDisabled ? 'disabled' : ''}">
                                <button class="page-link" onclick="Pagination.goToPage(${this.currentPage + 1}, '${onPageChange}')">
                                    Next <i class="fas fa-chevron-right"></i>
                                </button>
                            </li>
                        </ul>
                    </nav>
                ``
  Line: `.innerHTML = `
                    <nav aria-label="Page navigation" class="mt-3">
                        <ul class="pagination justify-content-center">
                            <li class="page-item ${prevDisabled ? 'disabled' : ''}">
                                <button class="page-link" onclick="Pagination.goToPage(${this.currentPage - 1}, '${onPageChange}')">
                                    <i class="fas fa-chevron-left"></i> Previous
                                </button>
                            </li>
                            <li class="page-item active">
                                <span class="page-link">Page ${this.currentPage} of ${this.totalPages}</span>
                            </li>
                            <li class="page-item ${nextDisabled ? 'disabled' : ''}">
                                <button class="page-link" onclick="Pagination.goToPage(${this.currentPage + 1}, '${onPageChange}')">
                                    Next <i class="fas fa-chevron-right"></i>
                                </button>
                            </li>
                        </ul>
                    </nav>
                `;`
- Expression: `d.data.map(u => {
                    const phoneDisplay = VisibilityRules.phoneNumber() 
                        ? (u.phone_number || '-') 
                        : '••••••••'`
  Line: `.innerHTML = d.data.map(u => {
                    const phoneDisplay = VisibilityRules.phoneNumber() 
                        ? (u.phone_number || '-') 
                        : '••••••••';`
- Expression: `d.data.map(h => `
                    <tr>
                        <td>${h.id}</td>
                        <td>${h.user_email || h.email || '-'}</td>
                        <td><span class="badge bg-danger">${h.hold_type || 'UNKNOWN'}</span></td>
                        <td>${h.reason || '-'}</td>
                        <td>${h.created_at ? new Date(h.created_at).toLocaleDateString() : '-'}</td>
                        <td>${h.released_at ? new Date(h.released_at).toLocaleDateString() : 'TBD'}</td>
                        <td>
                            <button class="btn btn-xs btn-success" onclick="openReleaseModal(${h.id}, '${h.reason}')"><i class="fas fa-unlock"></i></button>
                        </td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = d.data.map(h => `
                    <tr>
                        <td>${h.id}</td>
                        <td>${h.user_email || h.email || '-'}</td>
                        <td><span class="badge bg-danger">${h.hold_type || 'UNKNOWN'}</span></td>
                        <td>${h.reason || '-'}</td>
                        <td>${h.created_at ? new Date(h.created_at).toLocaleDateString() : '-'}</td>
                        <td>${h.released_at ? new Date(h.released_at).toLocaleDateString() : 'TBD'}</td>
                        <td>
                            <button class="btn btn-xs btn-success" onclick="openReleaseModal(${h.id}, '${h.reason}')"><i class="fas fa-unlock"></i></button>
                        </td>
                    </tr>
                `).join('');`
- Expression: `d.data.map(dev => `
                    <tr>
                        <td>${dev.email || dev.user_email || '-'}</td>
                        <td>${dev.device_type || '-'}</td>
                        <td><code>${dev.ip_address || '-'}</code></td>
                        <td>${dev.browser || dev.browser_info || '-'}</td>
                        <td>${dev.last_active ? new Date(dev.last_active).toLocaleDateString() : '-'}</td>
                        <td>
                            <button class="btn btn-xs btn-danger" onclick="openRevokeModal(${dev.device_id || dev.id}, '${dev.ip_address}')">
                                <i class="fas fa-power-off"></i>
                            </button>
                        </td>
                    </tr>
                `).join('')`
  Line: `.innerHTML = d.data.map(dev => `
                    <tr>
                        <td>${dev.email || dev.user_email || '-'}</td>
                        <td>${dev.device_type || '-'}</td>
                        <td><code>${dev.ip_address || '-'}</code></td>
                        <td>${dev.browser || dev.browser_info || '-'}</td>
                        <td>${dev.last_active ? new Date(dev.last_active).toLocaleDateString() : '-'}</td>
                        <td>
                            <button class="btn btn-xs btn-danger" onclick="openRevokeModal(${dev.device_id || dev.id}, '${dev.ip_address}')">
                                <i class="fas fa-power-off"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');`
- Expression: `d.feed_items.map(item => `
                    <div class="feed-item">
                        <span class="feed-badge" style="background: ${item.type === 'transaction' ? '#e7f3ff' : '#fff3cd'}`
  Line: `.innerHTML = d.feed_items.map(item => `
                    <div class="feed-item">
                        <span class="feed-badge" style="background: ${item.type === 'transaction' ? '#e7f3ff' : '#fff3cd'};`
- Expression: ``
                    <p><strong>Email:</strong> ${user.email}</p>
                    <p><strong>Name:</strong> ${user.full_name || '-'}</p>
                    <p><strong>Status:</strong> ${user.is_active ? 'Active' : 'Inactive'}</p>
                    <p><strong>KYC Status:</strong> ${user.kyc_status || 'PENDING'}</p>
                    <p><strong>Last Login:</strong> ${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</p>
                ``
  Line: `.innerHTML = `
                    <p><strong>Email:</strong> ${user.email}</p>
                    <p><strong>Name:</strong> ${user.full_name || '-'}</p>
                    <p><strong>Status:</strong> ${user.is_active ? 'Active' : 'Inactive'}</p>
                    <p><strong>KYC Status:</strong> ${user.kyc_status || 'PENDING'}</p>
                    <p><strong>Last Login:</strong> ${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</p>
                `;`
- Expression: ``
                    <h6>Audit History</h6>
                    <div class="activity-feed" style="max-height: 300px`
  Line: `.innerHTML = `
                    <h6>Audit History</h6>
                    <div class="activity-feed" style="max-height: 300px;`
- Expression: ``
                        <div class="row">
                            <div class="col-md-6">
                                <h6>ID Document</h6>
                                ${idFrontUrl ? `
                                    <img src="${idFrontUrl}" style="max-width: 100%`
  Line: `.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6>ID Document</h6>
                                ${idFrontUrl ? `
                                    <img src="${idFrontUrl}" style="max-width: 100%;`
- Expression: ``
                        <p><strong>Status:</strong> <span class="kyc-badge kyc-${(d.status||'pending').toLowerCase()}">${(d.status||'PENDING').toUpperCase()}</span></p>
                        <p><strong>Document Type:</strong> ${d.user_info?.document_type || '-'}</p>
                        <p><strong>Submitted:</strong> ${d.user_info?.submitted_at ? new Date(d.user_info.submitted_at).toLocaleDateString() : '-'}</p>
                    ``
  Line: `.innerHTML = `
                        <p><strong>Status:</strong> <span class="kyc-badge kyc-${(d.status||'pending').toLowerCase()}">${(d.status||'PENDING').toUpperCase()}</span></p>
                        <p><strong>Document Type:</strong> ${d.user_info?.document_type || '-'}</p>
                        <p><strong>Submitted:</strong> ${d.user_info?.submitted_at ? new Date(d.user_info.submitted_at).toLocaleDateString() : '-'}</p>
                    `;`
- Expression: ``
                    <h6><strong>Users (${d.results.users?.length || 0})</strong></h6>
                    ${(d.results.users || []).map(u => 
                        `<div class="search-result-item" onclick="openUserDetailModal(${u.id})" style="cursor: pointer`
  Line: `.innerHTML = `
                    <h6><strong>Users (${d.results.users?.length || 0})</strong></h6>
                    ${(d.results.users || []).map(u => 
                        `<div class="search-result-item" onclick="openUserDetailModal(${u.id})" style="cursor: pointer;`
### 📄 [admin_vendor_hub.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_vendor_hub.html)
- Expression: ``<i class="fas fa-user-circle me-1"></i>${u.email||'Admin'}``
  Line: `.innerHTML=`<i class="fas fa-user-circle me-1"></i>${u.email||'Admin'}`;`
- Expression: ``<i class="fas fa-check-circle me-1"></i>Live \u2014 ${data.frontend_url} (${data.latency_ms}ms)``
  Line: `.innerHTML=`<i class="fas fa-check-circle me-1"></i>Live \u2014 ${data.frontend_url} (${data.latency_ms}ms)`;`
- Expression: ``<span class="text-danger"><i class="fas fa-times-circle me-1"></i>${data.error||'Cannot reach app URL'}</span>``
  Line: `.innerHTML=`<span class="text-danger"><i class="fas fa-times-circle me-1"></i>${data.error||'Cannot reach app URL'}</span>`;`
- Expression: ``<i class="fas fa-check me-1"></i>OK (${data.latency_ms}ms)``
  Line: `.innerHTML=`<i class="fas fa-check me-1"></i>OK (${data.latency_ms}ms)`;`
### 📄 [admin_webhooks.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\admin_webhooks.html)
- Expression: ``<tr><td colspan="6" class="text-center py-3 text-muted">No webhook configuration registered.</td></tr>``
  Line: `.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-muted">No webhook configuration registered.</td></tr>`;`
- Expression: ``
                    <td><strong>${w.id}</strong></td>
                    <td class="font-monospace">${w.url}</td>
                    <td><span class="badge bg-secondary">Production</span></td>
                    <td>${events}</td>
                    <td>${statusBadge}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-dark me-1" onclick="openDetailsModal(${w.id}, '${w.secret_key || ''}')" title="Security & Test Console">
                            <i class="fas fa-lock"></i> Controls
                        </button>
                        <button class="btn btn-sm btn-outline-warning me-1" onclick="openEditModal(${w.id})" title="Edit Webhook">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteWebhook(${w.id})" title="Delete Webhook">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                ``
  Line: `.innerHTML = `
                    <td><strong>${w.id}</strong></td>
                    <td class="font-monospace">${w.url}</td>
                    <td><span class="badge bg-secondary">Production</span></td>
                    <td>${events}</td>
                    <td>${statusBadge}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-dark me-1" onclick="openDetailsModal(${w.id}, '${w.secret_key || ''}')" title="Security & Test Console">
                            <i class="fas fa-lock"></i> Controls
                        </button>
                        <button class="btn btn-sm btn-outline-warning me-1" onclick="openEditModal(${w.id})" title="Edit Webhook">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteWebhook(${w.id})" title="Delete Webhook">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                `;`
### 📄 [mfa_setup.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/private\admin\mfa_setup.html)
- Expression: `codes.map(code => 
                `<div class="backup-code" onclick="copyToClipboard('${code}')" title="Click to copy">
                    ${code}
                </div>`
            ).join('')`
  Line: `.innerHTML = codes.map(code => 
                `<div class="backup-code" onclick="copyToClipboard('${code}')" title="Click to copy">
                    ${code}
                </div>`
            ).join('');`
- Expression: `data.admins.map(admin => `
                        <div class="mfa-item">
                            <div class="mfa-info">
                                <div class="mfa-email">${admin.email}</div>
                                <div class="mfa-status">
                                    <span class="status-badge ${admin.mfa_enabled ? 'status-enabled' : 'status-disabled'}">
                                        ${admin.mfa_enabled ? '✓ MFA Enabled' : '✗ MFA Disabled'}
                                    </span>
                                    ${admin.mfa_enabled ? `<small>Setup: ${new Date(admin.mfa_setup_date).toLocaleDateString()}</small>` : ''}
                                </div>
                            </div>
                            <div class="mfa-actions">
                                ${!admin.mfa_enabled ? 
                                    `<button class="btn btn-primary btn-sm" onclick="enableMFAForAdmin('${admin.id}', '${admin.email}')">
                                        <i class="fas fa-shield-alt"></i> Enable MFA
                                    </button>` :
                                    `<button class="btn btn-warning btn-sm" onclick="resetMFAForAdmin('${admin.id}', '${admin.email}')">
                                        <i class="fas fa-sync-alt"></i> Reset MFA
                                    </button>`
                                }
                            </div>
                        </div>
                    `).join('')`
  Line: `.innerHTML = data.admins.map(admin => `
                        <div class="mfa-item">
                            <div class="mfa-info">
                                <div class="mfa-email">${admin.email}</div>
                                <div class="mfa-status">
                                    <span class="status-badge ${admin.mfa_enabled ? 'status-enabled' : 'status-disabled'}">
                                        ${admin.mfa_enabled ? '✓ MFA Enabled' : '✗ MFA Disabled'}
                                    </span>
                                    ${admin.mfa_enabled ? `<small>Setup: ${new Date(admin.mfa_setup_date).toLocaleDateString()}</small>` : ''}
                                </div>
                            </div>
                            <div class="mfa-actions">
                                ${!admin.mfa_enabled ? 
                                    `<button class="btn btn-primary btn-sm" onclick="enableMFAForAdmin('${admin.id}', '${admin.email}')">
                                        <i class="fas fa-shield-alt"></i> Enable MFA
                                    </button>` :
                                    `<button class="btn btn-warning btn-sm" onclick="resetMFAForAdmin('${admin.id}', '${admin.email}')">
                                        <i class="fas fa-sync-alt"></i> Reset MFA
                                    </button>`
                                }
                            </div>
                        </div>
                    `).join('');`
- Expression: ``<p class="empty-state" style="color:red`
  Line: `.innerHTML = `<p class="empty-state" style="color:red;`
- Expression: `'<option value="">Choose an admin...</option>' +
                    data.admins.map(admin => 
                        `<option value="${admin.id}">${admin.email}</option>`
                    ).join('')`
  Line: `.innerHTML = '<option value="">Choose an admin...</option>' +
                    data.admins.map(admin => 
                        `<option value="${admin.id}">${admin.email}</option>`
                    ).join('');`
- Expression: `data.mfa_enabled ? 
                    '<span class="status-badge status-enabled">✓ Enabled</span>' :
                    '<span class="status-badge status-disabled">✗ Disabled</span>'`
  Line: `.innerHTML = data.mfa_enabled ? 
                    '<span class="status-badge status-enabled">✓ Enabled</span>' :
                    '<span class="status-badge status-disabled">✗ Disabled</span>';`
- Expression: `data.backup_codes.map(code => 
                        `<div class="backup-code ${code.used ? 'used' : ''}">
                            ${code.code}
                            <small style="display:block`
  Line: `.innerHTML = data.backup_codes.map(code => 
                        `<div class="backup-code ${code.used ? 'used' : ''}">
                            ${code.code}
                            <small style="display:block;`
### 📄 [forgot_password.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/static\forgot_password.html)
- Expression: `[
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert">`,
                `   <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>`,
                `   <div>${message}</div>`,
                '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
                '</div>'
            ].join('')`
  Line: `.innerHTML = [
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert">`,
                `   <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>`,
                `   <div>${message}</div>`,
                '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
                '</div>'
            ].join('');`
### 📄 [reset_password.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/static\reset_password.html)
- Expression: `[
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert" style="animation: slideDown 0.3s ease-out`
  Line: `.innerHTML = [
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert" style="animation: slideDown 0.3s ease-out;`
### 📄 [signup.html](file:///c:/Users/Aweh/Downloads/supreme/financial-services-website-template/static\signup.html)
- Expression: `[
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert" style="animation: slideDown 0.3s ease-out`
  Line: `.innerHTML = [
                `<div class="alert alert-${type} alert-dismissible fade show" role="alert" style="animation: slideDown 0.3s ease-out;`
