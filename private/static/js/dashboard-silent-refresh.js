/**
 * Silent Refresh Token Manager
 * Handles: Token refresh without user interruption, refresh token rotation, session continuity
 * 
 * Production Features:
 * - Automatic refresh token rotation
 * - Silent refresh (no logout if refresh succeeds)
 * - Prevents mid-transaction session loss
 * - Graceful degradation if refresh fails
 * - Secure HTTP-only cookie support for refresh tokens
 * - Exponential backoff on refresh failure
 */

class SilentRefreshManager {
    constructor() {
        this.config = {
            REFRESH_BEFORE_EXPIRY_MS: 5 * 60 * 1000, // Refresh 5 minutes before expiry
            CHECK_INTERVAL_MS: 30 * 1000, // Check every 30 seconds
            MAX_REFRESH_ATTEMPTS: 3,
            REFRESH_BACKOFF_MS: 2000,
        };
        
        this.state = {
            isRefreshing: false,
            refreshAttempts: 0,
            lastRefreshTime: null,
            tokenExpiryTime: null,
        };
        
        this.checkIntervalId = null;
    }
    
    /**
     * Initialize silent refresh manager
     */
    init() {
        console.log('[SILENT-REFRESH] Initializing silent refresh manager...');
        
        this.startRefreshCheck();
        console.log('[SILENT-REFRESH] ✓ Silent refresh manager initialized');
    }
    
    /**
     * Start periodic refresh check
     */
    startRefreshCheck() {
        this.checkIntervalId = setInterval(async () => {
            await this.checkAndRefreshIfNeeded();
        }, this.config.CHECK_INTERVAL_MS);
        
        // Also check immediately
        this.checkAndRefreshIfNeeded();
    }
    
    /**
     * Check if token needs refresh and refresh if necessary
     */
    async checkAndRefreshIfNeeded() {
        let token;
        
        try {
            // Get current token from localStorage
            token = localStorage.getItem('auth_token');
            
            if (!token) {
                console.warn('[SILENT-REFRESH] No token found. Skipping refresh check.');
                return;
            }
            
            // Decode JWT to check expiry
            const decoded = this.decodeJWT(token);
            
            if (!decoded) {
                console.warn('[SILENT-REFRESH] Invalid token format. Skipping refresh.');
                return;
            }
            
            const expiryTime = decoded.exp * 1000; // Convert to milliseconds
            const now = Date.now();
            const timeUntilExpiry = expiryTime - now;
            
            this.state.tokenExpiryTime = expiryTime;
            
            // If token expires within the refresh window, refresh it silently
            if (timeUntilExpiry > 0 && timeUntilExpiry < this.config.REFRESH_BEFORE_EXPIRY_MS) {
                console.log(`[SILENT-REFRESH] Token expiring in ${Math.round(timeUntilExpiry / 1000)}s. Attempting silent refresh...`);
                
                await this.performSilentRefresh();
            }
            
        } catch (error) {
            console.error('[SILENT-REFRESH] Check failed:', error.message);
        }
    }
    
    /**
     * Perform silent token refresh
     */
    async performSilentRefresh() {
        if (this.state.isRefreshing) {
            console.log('[SILENT-REFRESH] Refresh already in progress. Skipping.');
            return;
        }
        
        this.state.isRefreshing = true;
        this.state.refreshAttempts = 0;
        
        try {
            for (let attempt = 0; attempt < this.config.MAX_REFRESH_ATTEMPTS; attempt++) {
                try {
                    console.log(`[SILENT-REFRESH] Refresh attempt ${attempt + 1}/${this.config.MAX_REFRESH_ATTEMPTS}...`);
                    
                    const response = await fetch('/api/v1/auth/refresh-token', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        credentials: 'include', // Include cookies for refresh token
                        timeout: 10000,
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        
                        if (data.access_token) {
                            localStorage.setItem('auth_token', data.access_token);
                            this.state.lastRefreshTime = Date.now();
                            this.state.refreshAttempts = 0;
                            
                            console.log('[SILENT-REFRESH] ✓ Token refreshed silently. User session continues.');
                            
                            // Log audit event
                            if (typeof dashboardAudit !== 'undefined' && dashboardAudit) {
                                dashboardAudit.logAction('silent_token_refresh', { success: true });
                            }
                            
                            return true;
                        }
                    }
                    
                    if (response.status === 401 || response.status === 403) {
                        console.warn('[SILENT-REFRESH] Refresh token invalid. User must login again.');
                        this.handleRefreshFailure();
                        return false;
                    }
                    
                    // Retry on other errors
                    if (attempt < this.config.MAX_REFRESH_ATTEMPTS - 1) {
                        const backoffDelay = this.config.REFRESH_BACKOFF_MS * Math.pow(2, attempt);
                        console.warn(`[SILENT-REFRESH] Refresh failed. Retrying in ${backoffDelay}ms...`);
                        await new Promise(resolve => setTimeout(resolve, backoffDelay));
                    }
                    
                } catch (error) {
                    console.error(`[SILENT-REFRESH] Refresh attempt ${attempt + 1} failed:`, error.message);
                    
                    if (attempt < this.config.MAX_REFRESH_ATTEMPTS - 1) {
                        const backoffDelay = this.config.REFRESH_BACKOFF_MS * Math.pow(2, attempt);
                        await new Promise(resolve => setTimeout(resolve, backoffDelay));
                    }
                }
            }
            
            // All retry attempts failed
            console.error('[SILENT-REFRESH] All refresh attempts failed. User session may expire.');
            this.handleRefreshFailure();
            return false;
            
        } finally {
            this.state.isRefreshing = false;
        }
    }
    
    /**
     * Handle refresh failure gracefully
     */
    handleRefreshFailure() {
        console.warn('[SILENT-REFRESH] Silent refresh failed. Notifying user.');
        
        // Log audit event
        if (typeof dashboardAudit !== 'undefined' && dashboardAudit) {
            dashboardAudit.logAction('silent_token_refresh', { success: false, reason: 'refresh_failed' });
        }
        
        // Show warning but don't log out automatically
        // User can continue if current token is still valid
        if (typeof dashboardErrorHandler !== 'undefined' && dashboardErrorHandler) {
            dashboardErrorHandler.showBanner(
                'We couldn\'t refresh your session. Please save your work and login again if needed.'
            );
        }
    }
    
    /**
     * Decode JWT token
     */
    decodeJWT(token) {
        try {
            const parts = token.split('.');
            
            if (parts.length !== 3) {
                throw new Error('Invalid JWT format');
            }
            
            // Base64 decode the payload
            const payload = JSON.parse(atob(parts[1]));
            
            return payload;
            
        } catch (error) {
            console.error('[SILENT-REFRESH] JWT decode error:', error.message);
            return null;
        }
    }
    
    /**
     * Force immediate refresh
     */
    async forceRefresh() {
        console.log('[SILENT-REFRESH] Forcing immediate token refresh...');
        return await this.performSilentRefresh();
    }
    
    /**
     * Get refresh state
     */
    getState() {
        return {
            isRefreshing: this.state.isRefreshing,
            lastRefreshTime: this.state.lastRefreshTime,
            tokenExpiryTime: this.state.tokenExpiryTime,
            canRefresh: !this.state.isRefreshing && this.state.refreshAttempts < this.config.MAX_REFRESH_ATTEMPTS,
        };
    }
    
    /**
     * Stop refresh checks
     */
    stop() {
        if (this.checkIntervalId) {
            clearInterval(this.checkIntervalId);
            console.log('[SILENT-REFRESH] Refresh checks stopped');
        }
    }
    
    /**
     * Destroy manager
     */
    destroy() {
        this.stop();
        console.log('[SILENT-REFRESH] Destroyed');
    }
}

// Global instance
const silentRefreshManager = new SilentRefreshManager();
