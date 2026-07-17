/**
 * CSRF Token Manager
 * Handles CSRF token generation, validation, and injection into requests
 * 
 * Strategy:
 * - Double-submit cookie pattern (cookie + header)
 * - Automatic token refresh on expiry
 * - Transparent injection into fetch requests
 */

class CSRFTokenManager {
    constructor() {
        this.token = null;
        this.expiryTime = null;
        this.TOKEN_COOKIE_NAME = 'csrf_token';
        this.TOKEN_HEADER_NAME = 'X-CSRF-Token';
        this.TOKEN_STORAGE_KEY = 'csrf_token_local';
        this.EXPIRY_DURATION_MS = 60 * 60 * 1000; // 1 hour
        
        // Auto-refresh config
        this.refreshInterval = null;
        this.shouldAutoRefresh = true;
    }
    
    /**
     * Initialize CSRF protection
     */
    async init() {
        console.log('[CSRF] Initializing CSRF token manager...');
        
        // Try to get token from storage first
        this.token = this.getStoredToken();
        
        // If no token or expired, fetch a new one
        if (!this.token || this.isExpired()) {
            await this.refreshToken();
        }
        
        // Start auto-refresh interval (1 hour - 5 minutes before expiry)
        this.startAutoRefresh();
        
        // Intercept fetch to inject CSRF token
        this.interceptFetch();
        
        console.log('[CSRF] ✓ CSRF token manager ready');
    }
    
    /**
     * Fetch new CSRF token from backend
     */
    async refreshToken() {
        try {
            const response = await fetch('/api/v1/auth/csrf-token', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error(`Failed to get CSRF token: ${response.status}`);
            }
            
            const data = await response.json();
            this.saveToken(data.csrf_token);
            
            console.log('[CSRF] ✓ CSRF token refreshed');
            return true;
        } catch (e) {
            console.error('[CSRF] Failed to refresh token:', e);
            return false;
        }
    }
    
    /**
     * Save token to storage
     */
    saveToken(token) {
        this.token = token;
        this.expiryTime = Date.now() + this.EXPIRY_DURATION_MS;
        
        // Store in localStorage as backup
        localStorage.setItem(this.TOKEN_STORAGE_KEY, JSON.stringify({
            token: this.token,
            expiry: this.expiryTime
        }));
        
        // Notify state manager
        if (window.dashboardState) {
            window.dashboardState.state.security.csrf_token = token;
        }
    }
    
    /**
     * Get stored token from localStorage
     */
    getStoredToken() {
        try {
            const stored = localStorage.getItem(this.TOKEN_STORAGE_KEY);
            if (!stored) return null;
            
            const { token, expiry } = JSON.parse(stored);
            
            // Check if stored token is expired
            if (expiry && expiry < Date.now()) {
                localStorage.removeItem(this.TOKEN_STORAGE_KEY);
                return null;
            }
            
            return token;
        } catch (e) {
            return null;
        }
    }
    
    /**
     * Check if current token is expired
     */
    isExpired() {
        if (!this.expiryTime) return true;
        return Date.now() > this.expiryTime;
    }
    
    /**
     * Get current token
     */
    getToken() {
        if (this.isExpired()) {
            console.warn('[CSRF] Token expired');
            return null;
        }
        return this.token;
    }
    
    /**
     * Start auto-refresh interval
     * Refreshes token 5 minutes before expiry
     */
    startAutoRefresh() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (!this.shouldAutoRefresh) {
            console.log('[CSRF] Auto-refresh disabled');
            return;
        }
        
        // Refresh every 55 minutes (token lasts 60)
        this.refreshInterval = setInterval(async () => {
            if (this.isExpired()) {
                console.log('[CSRF] Token expired, refreshing...');
                await this.refreshToken();
            }
        }, 55 * 60 * 1000);
        
        console.log('[CSRF] Auto-refresh started');
    }
    
    /**
     * Stop auto-refresh interval
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    /**
     * Determine if request needs CSRF protection
     * Only state-changing requests (POST, PUT, PATCH, DELETE) need CSRF token
     */
    doesRequestNeedCSRF(method) {
        const statefulMethods = ['POST', 'PUT', 'PATCH', 'DELETE'];
        return statefulMethods.includes((method || 'GET').toUpperCase());
    }
    
    /**
     * Inject CSRF token into fetch request
     */
    injectCSRFToken(options) {
        const method = options.method || 'GET';
        
        // Only inject for state-changing requests
        if (!this.doesRequestNeedCSRF(method)) {
            return options;
        }
        
        const token = this.getToken();
        if (!token) {
            console.warn('[CSRF] CSRF token not available for request');
            return options;
        }
        
        // Initialize headers if not present
        if (!options.headers) {
            options.headers = {};
        }
        
        // Add CSRF token to headers
        options.headers[this.TOKEN_HEADER_NAME] = token;
        
        return options;
    }
    
    /**
     * Intercept global fetch to inject CSRF tokens
     * Wraps window.fetch with CSRF handling
     */
    interceptFetch() {
        const originalFetch = window.fetch;
        
        window.fetch = async (resource, options = {}) => {
            // Only intercept for same-origin requests
            const url = typeof resource === 'string' ? resource : resource.url;
            if (!this.isSameOrigin(url)) {
                return originalFetch.apply(window, arguments);
            }
            
            // Inject CSRF token
            const modifiedOptions = this.injectCSRFToken({ ...options });
            
            try {
                const response = await originalFetch(resource, modifiedOptions);
                
                // Handle CSRF token validation failures
                if (response.status === 403 && response.headers.get('X-CSRF-Token-Invalid')) {
                    console.warn('[CSRF] Token validation failed, refreshing...');
                    await this.refreshToken();
                    // Retry request with new token
                    const retryOptions = this.injectCSRFToken({ ...options });
                    return originalFetch(resource, retryOptions);
                }
                
                return response;
            } catch (e) {
                console.error('[CSRF] Fetch error:', e);
                throw e;
            }
        };
    }
    
    /**
     * Check if URL is same origin (security)
     */
    isSameOrigin(url) {
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.origin === window.location.origin;
        } catch (e) {
            // Relative URL is same origin
            return true;
        }
    }
    
    /**
     * Cleanup
     */
    destroy() {
        this.stopAutoRefresh();
        console.log('[CSRF] CSRF manager destroyed');
    }
}

// Initialize as singleton
const csrfManager = new CSRFTokenManager();
console.log('[CSRF] CSRF manager created');
