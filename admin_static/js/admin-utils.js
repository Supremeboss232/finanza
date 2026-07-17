/**
 * Shared Admin Utilities
 * Common functions for all admin pages
 */

// API Configuration
const API_BASE = '/api/admin/data';
const API_V1 = '/api/v1';
const AUTH_HEADER = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
});

/**
 * Fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: AUTH_HEADER(),
            credentials: 'include',
            ...options
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                // Redirect to login if unauthorized
                window.location.href = '/auth/login';
                return null;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showAlert('Error: ' + error.message, 'danger');
        return null;
    }
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount || 0);
}

/**
 * Format date
 */
function formatDate(date, format = 'short') {
    const d = new Date(date);
    if (isNaN(d)) return 'Invalid date';
    
    switch (format) {
        case 'short':
            return d.toLocaleDateString('en-US');
        case 'long':
            return d.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        case 'time':
            return d.toLocaleTimeString('en-US');
        case 'datetime':
            return d.toLocaleString('en-US');
        default:
            return d.toLocaleDateString('en-US');
    }
}

/**
 * Format percentage
 */
function formatPercent(value, decimals = 2) {
    return (parseFloat(value) || 0).toFixed(decimals) + '%';
}

/**
 * Create status badge HTML
 */
function createStatusBadge(status, statusMap = {}) {
    const colorMap = {
        'pending': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'active': 'success',
        'inactive': 'secondary',
        'approved': 'success',
        'rejected': 'danger',
        'denied': 'danger',
        'delinquent': 'danger',
        'current': 'success',
        'processing': 'info',
        'default': 'secondary'
    };
    
    const color = colorMap[status?.toLowerCase()] || 'secondary';
    return `<span class="badge bg-${color}">${status}</span>`;
}

/**
 * Populate select dropdown
 */
async function populateSelect(selectId, endpoint, displayField, valueField = 'id', filter = null) {
    try {
        const data = await fetchAPI(endpoint);
        if (!data || !data.data) return;
        
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Keep placeholder
        const placeholder = select.querySelector('option:first-child');
        select.innerHTML = placeholder?.outerHTML || '';
        
        data.data.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField];
            option.textContent = item[displayField];
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error populating select:', error);
    }
}

/**
 * Show alert/toast notification
 */
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        console.warn('Alert container not found');
        alert(message);
        return;
    }
    
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const alertDiv = document.createElement('div');
    alertDiv.innerHTML = alertHTML;
    alertContainer.appendChild(alertDiv.firstElementChild);
    
    if (duration > 0) {
        setTimeout(() => {
            alertDiv.firstElementChild.remove();
        }, duration);
    }
}

/**
 * Open modal helper
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        new bootstrap.Modal(modal).show();
    }
}

/**
 * Close modal helper
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        bootstrap.Modal.getInstance(modal)?.hide();
    }
}

/**
 * Confirm dialog
 */
function confirmAction(message, onConfirm, onCancel = null) {
    if (confirm(message)) {
        onConfirm();
    } else if (onCancel) {
        onCancel();
    }
}

/**
 * Table search/filter
 */
function filterTable(tableId, searchTerm) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.getElementsByTagName('tr');
    const searchLower = searchTerm.toLowerCase();
    
    Array.from(rows).forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchLower) ? '' : 'none';
    });
}

/**
 * Download CSV
 */
function downloadCSV(data, filename = 'export.csv') {
    if (!Array.isArray(data) || data.length === 0) {
        console.error('No data to download');
        return;
    }
    
    // Get headers from first object
    const headers = Object.keys(data[0]);
    
    // Create CSV content
    let csv = headers.join(',') + '\n';
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header];
            // Escape quotes and wrap in quotes if contains comma
            return typeof value === 'string' && value.includes(',') 
                ? `"${value.replace(/"/g, '""')}"` 
                : value;
        });
        csv += values.join(',') + '\n';
    });
    
    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

/**
 * Parse URL parameters
 */
function getURLParams() {
    const params = {};
    const searchParams = new URLSearchParams(window.location.search);
    for (let [key, value] of searchParams) {
        params[key] = value;
    }
    return params;
}

/**
 * Navigate with history
 */
function navigateTo(url, newWindow = false) {
    if (newWindow) {
        window.open(url, '_blank');
    } else {
        window.location.href = url;
    }
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate form
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const inputs = form.querySelectorAll('[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

/**
 * Reset form
 */
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
    }
}

/**
 * Check admin authorization
 */
async function checkAdminAccess() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/auth/login';
        return false;
    }
    return true;
}

/**
 * Load user metrics
 */
async function loadUserMetrics() {
    return await fetchAPI(API_BASE + '/users');
}

/**
 * Load transaction metrics
 */
async function loadTransactionMetrics() {
    return await fetchAPI(API_BASE + '/transactions');
}

/**
 * Load KYC metrics
 */
async function loadKYCMetrics() {
    return await fetchAPI(API_BASE + '/kyc');
}

/**
 * Load system metrics
 */
async function loadSystemMetrics() {
    return await fetchAPI(API_BASE + '/metrics');
}

/**
 * Create pagination HTML
 */
function createPagination(currentPage, totalPages, onPageChange) {
    let html = '<nav><ul class="pagination">';
    
    // Previous button
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="event.preventDefault(); ${onPageChange}(${currentPage - 1})">Previous</a>
    </li>`;
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="event.preventDefault(); ${onPageChange}(${i})">${i}</a>
            </li>`;
        }
    }
    
    // Next button
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="event.preventDefault(); ${onPageChange}(${currentPage + 1})">Next</a>
    </li></ul></nav>`;
    
    return html;
}

/**
 * Export data to Excel (requires xlsx library)
 */
function exportToExcel(data, filename = 'export.xlsx') {
    if (typeof XLSX === 'undefined') {
        console.error('XLSX library not loaded');
        showAlert('Excel export requires XLSX library', 'warning');
        return;
    }
    
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, filename);
}

/**
 * Initialize admin page
 */
async function initAdminPage() {
    // Check authorization
    if (!(await checkAdminAccess())) {
        return;
    }
    
    // Create alert container if doesn't exist
    if (!document.getElementById('alertContainer')) {
        const container = document.createElement('div');
        container.id = 'alertContainer';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.minWidth = '300px';
        document.body.appendChild(container);
    }
    
    console.log('Admin page initialized');
}

// Auto-initialize on DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminPage);
} else {
    initAdminPage();
}
