/**
 * Auth Helper - Global Authorization & Security checks
 * Prevents unauthorized access to admin endpoints
 */

console.log('[AUTH-HELPER] Loading Auth Helper...');

// ==================== AUTHORIZATION GUARD ====================
// Check if current user is admin before allowing admin API calls
const originalFetch = window.fetch;

window.fetch = function(...args) {
    const url = args[0] || '';
    const isAdminApi = typeof url === 'string' && url.includes('/api/admin');
    
    if (isAdminApi) {
        const isAdmin = localStorage.getItem('is_admin') === 'true';
        if (!isAdmin) {
            console.error('[AUTH-GUARD] BLOCKED: Non-admin user attempted to call admin API:', url);
            return Promise.reject(new Error('Unauthorized: Admin access required'));
        }
    }
    
    return originalFetch.apply(this, args);
};

console.log('[AUTH-HELPER] Authorization guard installed');

// ==================== PAGE PROTECTION ====================
// Prevent non-admin users from seeing admin pages
document.addEventListener('DOMContentLoaded', function() {
    const isAdmin = localStorage.getItem('is_admin') === 'true';
    const currentPath = window.location.pathname;
    
    // If on admin page and not admin, redirect immediately
    if (currentPath.includes('/user/admin/') && !isAdmin) {
        console.error('[AUTH-HELPER] Non-admin user detected on admin page. Redirecting...');
        window.location.replace('/user/dashboard');
    }
});

console.log('[AUTH-HELPER] Page protection installed');
