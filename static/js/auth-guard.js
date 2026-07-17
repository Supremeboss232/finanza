// ==================== SHARED AUTH GUARD ====================
// This file should be included in all protected portal pages (admin_users.html, admin_dashboard.html, etc.)
// 
// Usage: Add this to your HTML before other scripts:
// <script src="/static/js/auth-guard.js"></script>

/**
 * Shared Authentication Guard
 * 
 * This module provides session validation, token refresh, and automatic logout
 * for all protected portal pages. It implements the "Locked-Gate Authentication"
 * pattern across the entire application.
 * 
 * FEATURES:
 * - Validates user session on page load
 * - Automatically refreshes expired tokens
 * - Redirects to signin page if session invalid
 * - Supports ?next= redirect parameter for post-login navigation
 * - Logs audit trail for all protected page access
 * - Handles role-based access control (RBAC)
 */

(function() {
    'use strict';
    
    // ==================== CONFIGURATION ====================
    
    const AUTH_CONFIG = {
        API_BASE_URL: window.location.origin,
        ENDPOINTS: {
            ME: '/api/v1/users/me',
            REFRESH: '/api/v1/auth/refresh',
            LOGOUT: '/api/v1/auth/logout',
            ACCESS_LOG: '/api/v1/audit/page-access'
        },
        TIMEOUTS: {
            TOKEN_CHECK: 30000,        // Check token expiry every 30 seconds
            REFRESH_BUFFER: 5 * 60 * 1000  // Refresh 5 minutes before expiry
        }
    };
    
    // ==================== UTILITY FUNCTIONS ====================
    
    /**
     * Get token from localStorage
     */
    function getToken() {
        return localStorage.getItem('token');
    }
    
    /**
     * Check if token is expired
     */
    function isTokenExpired(token) {
        try {
            if (!token) return true;
            
            const parts = token.split('.');
            if (parts.length !== 3) return true;
            
            const payload = JSON.parse(atob(parts[1]));
            const expiryTime = payload.exp * 1000;
            const bufferTime = AUTH_CONFIG.TIMEOUTS.REFRESH_BUFFER;
            
            return Date.now() > (expiryTime - bufferTime);
        } catch (error) {
            console.error('[AUTH-GUARD] Token expiry check failed:', error);
            return true;
        }
    }
    
    /**
     * Redirect to signin with next parameter for return navigation
     */
    function redirectToSignin() {
        const currentPath = window.location.pathname + window.location.search;
        const signinUrl = `/signin.html?session_expired=true&next=${encodeURIComponent(currentPath)}`;
        window.location.href = signinUrl;
    }
    
    /**
     * Sanitize sensitive data
     */
    function sanitizeData(data) {
        if (typeof data !== 'string') return data;
        return data.replace(/[<>'"]/g, c => ({
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[c]));
    }
    
    /**
     * Log page access for audit trail
     */
    async function logPageAccess(pageInfo) {
        try {
            const token = getToken();
            if (!token) return;
            
            await fetch(`${AUTH_CONFIG.API_BASE_URL}${AUTH_CONFIG.ENDPOINTS.ACCESS_LOG}`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    page: pageInfo.page || window.location.pathname,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent,
                    referrer: document.referrer
                })
            });
        } catch (error) {
            console.error('[AUTH-GUARD] Page access logging failed:', error);
            // Fail silently - don't block page load for audit failures
        }
    }
    
    /**
     * Fetch with timeout
     */
    async function fetchWithTimeout(url, options = {}, timeout = 5000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
    
    /**
     * Validate session with backend
     */
    async function validateSession() {
        try {
            const token = getToken();
            
            if (!token) {
                console.warn('[AUTH-GUARD] No token found - session invalid');
                return false;
            }
            
            // Check token expiry first (fast check)
            if (isTokenExpired(token)) {
                console.warn('[AUTH-GUARD] Token expired');
                
                // Try to refresh token
                const refreshed = await refreshToken();
                if (!refreshed) {
                    return false;
                }
            }
            
            // Validate token with backend
            const response = await fetchWithTimeout(
                `${AUTH_CONFIG.API_BASE_URL}${AUTH_CONFIG.ENDPOINTS.ME}`,
                {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Authorization': `Bearer ${getToken()}`
                    }
                },
                5000
            );
            
            if (response.status === 401) {
                console.warn('[AUTH-GUARD] Backend rejected token (401)');
                return false;
            }
            
            if (!response.ok) {
                console.error('[AUTH-GUARD] Backend validation failed:', response.status);
                return false;
            }
            
            // Update user data from response
            const userData = await response.json();
            updateUserData(userData);
            
            return true;
            
        } catch (error) {
            console.error('[AUTH-GUARD] Session validation error:', error);
            return false;
        }
    }
    
    /**
     * Refresh authentication token
     */
    async function refreshToken() {
        try {
            console.log('[AUTH-GUARD] Attempting token refresh...');
            
            const response = await fetchWithTimeout(
                `${AUTH_CONFIG.API_BASE_URL}${AUTH_CONFIG.ENDPOINTS.REFRESH}`,
                {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                },
                5000
            );
            
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('token_refresh_time', Date.now());
                console.log('[AUTH-GUARD] Token refreshed successfully');
                return true;
            } else if (response.status === 401) {
                console.warn('[AUTH-GUARD] Token refresh failed (401) - session expired');
                clearSession();
                return false;
            }
            
            return false;
        } catch (error) {
            console.error('[AUTH-GUARD] Token refresh error:', error);
            return false;
        }
    }
    
    /**
     * Update user data from backend response
     */
    function updateUserData(userData) {
        localStorage.setItem('user_email', sanitizeData(userData.email));
        localStorage.setItem('user_id', sanitizeData(String(userData.user_id)));
        localStorage.setItem('full_name', sanitizeData(userData.full_name || ''));
        localStorage.setItem('admin_role', sanitizeData(userData.admin_role || 'USER'));
        localStorage.setItem('is_admin', userData.is_admin === true ? 'true' : 'false');
        
        if (userData.permissions) {
            localStorage.setItem('permissions', JSON.stringify(userData.permissions));
        }
    }
    
    /**
     * Clear session data
     */
    function clearSession() {
        localStorage.removeItem('token');
        localStorage.removeItem('token_type');
        localStorage.removeItem('user_email');
        localStorage.removeItem('user_id');
        localStorage.removeItem('full_name');
        localStorage.removeItem('admin_role');
        localStorage.removeItem('is_admin');
        localStorage.removeItem('permissions');
        localStorage.removeItem('token_refresh_time');
        localStorage.removeItem('remember_me');
        
        console.log('[AUTH-GUARD] Session cleared');
    }
    
    /**
     * Check role-based access control
     */
    function checkRoleAccess(requiredRoles) {
        if (!requiredRoles || requiredRoles.length === 0) {
            // No role requirement
            return true;
        }
        
        const userRole = localStorage.getItem('admin_role') || 'USER';
        const isAdmin = localStorage.getItem('is_admin') === 'true';
        
        // Array of user's roles
        const userRoles = [userRole];
        if (isAdmin) userRoles.push('ADMIN');
        
        // Check if user has any required role
        const hasAccess = requiredRoles.some(role => userRoles.includes(role));
        
        if (!hasAccess) {
            console.warn('[AUTH-GUARD] User does not have required role:', {
                required: requiredRoles,
                userRoles: userRoles
            });
        }
        
        return hasAccess;
    }
    
    /**
     * Setup periodic token refresh
     */
    function setupTokenRefresh() {
        setInterval(async () => {
            const token = getToken();
            if (token && isTokenExpired(token)) {
                console.log('[AUTH-GUARD] Periodic check: Token expired, refreshing...');
                const refreshed = await refreshToken();
                if (!refreshed) {
                    console.warn('[AUTH-GUARD] Periodic refresh failed - redirecting to signin');
                    redirectToSignin();
                }
            }
        }, AUTH_CONFIG.TIMEOUTS.TOKEN_CHECK);
    }
    
    // ==================== PUBLIC API ====================
    
    window.AuthGuard = {
        /**
         * Initialize auth guard on page load
         * Call this at the beginning of your protected page <script>
         * 
         * @param {Object} options - Configuration options
         * @param {Array<string>} options.requiredRoles - Roles required to access page
         * @param {string} options.pageInfo - Info about current page for audit log
         * @param {boolean} options.autoLogout - Auto logout on validation failure (default: true)
         * 
         * @example
         * // In your protected page header:
         * <script>
         *     AuthGuard.init({
         *         requiredRoles: ['ADMIN', 'SUPERADMIN'],
         *         pageInfo: { page: '/admin/users' },
         *         autoLogout: true
         *     });
         * </script>
         */
        init: async function(options = {}) {
            console.log('[AUTH-GUARD] Initializing auth guard...');
            
            const {
                requiredRoles = [],
                pageInfo = {},
                autoLogout = true
            } = options;
            
            // Validate session immediately
            const isValid = await validateSession();
            
            if (!isValid) {
                console.error('[AUTH-GUARD] Session validation failed');
                if (autoLogout) {
                    clearSession();
                    redirectToSignin();
                }
                return false;
            }
            
            // Check role-based access control
            if (requiredRoles.length > 0) {
                const hasAccess = checkRoleAccess(requiredRoles);
                if (!hasAccess) {
                    console.error('[AUTH-GUARD] User does not have required role for this page');
                    // Redirect to unauthorized page
                    window.location.href = '/unauthorized.html';
                    return false;
                }
            }
            
            // Log page access for audit trail
            await logPageAccess(pageInfo);
            
            // Setup periodic token refresh
            setupTokenRefresh();
            
            console.log('[AUTH-GUARD] Init complete - session valid');
            return true;
        },
        
        /**
         * Get current user data
         */
        getUser: function() {
            return {
                email: localStorage.getItem('user_email'),
                id: localStorage.getItem('user_id'),
                fullName: localStorage.getItem('full_name'),
                role: localStorage.getItem('admin_role'),
                isAdmin: localStorage.getItem('is_admin') === 'true',
                permissions: JSON.parse(localStorage.getItem('permissions') || '{}')
            };
        },
        
        /**
         * Check if user has required role
         */
        hasRole: function(roles) {
            if (typeof roles === 'string') {
                roles = [roles];
            }
            return checkRoleAccess(roles);
        },
        
        /**
         * Logout user
         */
        logout: async function() {
            try {
                const token = getToken();
                if (token) {
                    // Call logout endpoint
                    await fetchWithTimeout(
                        `${AUTH_CONFIG.API_BASE_URL}${AUTH_CONFIG.ENDPOINTS.LOGOUT}`,
                        {
                            method: 'POST',
                            credentials: 'include',
                            headers: {
                                'Authorization': `Bearer ${token}`
                            }
                        },
                        5000
                    );
                }
            } catch (error) {
                console.error('[AUTH-GUARD] Logout request failed:', error);
            } finally {
                clearSession();
                window.location.href = '/signin.html';
            }
        },
        
        /**
         * Manually refresh token
         */
        refreshToken: refreshToken,
        
        /**
         * Get token
         */
        getToken: getToken,
        
        /**
         * Check if authenticated
         */
        isAuthenticated: function() {
            const token = getToken();
            return !!token && !isTokenExpired(token);
        },
        
        /**
         * Show logout confirmation and logout
         */
        confirmLogout: function() {
            if (confirm('Are you sure you want to sign out?')) {
                this.logout();
            }
        }
    };
    
    // ==================== AUTO-INITIALIZATION ====================
    
    // Optionally, check for auto-initialization flag
    // Add data-auth-guard="true" to <body> to auto-init auth guard
    if (document.body && document.body.getAttribute('data-auth-guard') === 'true') {
        document.addEventListener('DOMContentLoaded', function() {
            const requiredRoles = document.body.getAttribute('data-required-roles');
            const roles = requiredRoles ? requiredRoles.split(',') : [];
            const pageName = document.body.getAttribute('data-page-name') || window.location.pathname;
            
            window.AuthGuard.init({
                requiredRoles: roles,
                pageInfo: { page: pageName }
            });
        });
    }
    
})();
