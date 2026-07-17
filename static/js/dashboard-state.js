/**
 * Dashboard State Management System
 * Implements reactive pattern for financial data
 * 
 * Architecture:
 * - Centralized state object
 * - Observer pattern for state changes
 * - Automatic UI updates on state mutation
 * - Built-in loading and error states
 */

class DashboardStateManager {
    constructor() {
        this.state = {
            user: {
                full_name: null,
                email: null,
                kyc_status: null,
                is_verified: false,
                loading: true,
                error: null
            },
            balance: {
                total: 0,
                currency: 'USD',
                loading: true,
                error: null,
                lastUpdated: null
            },
            accounts: {
                list: [],
                total_count: 0,
                loading: true,
                error: null,
                lastUpdated: null
            },
            deposits: {
                list: [],
                total_amount: 0,
                count: 0,
                loading: true,
                error: null,
                lastUpdated: null
            },
            loans: {
                list: [],
                total_amount: 0,
                count: 0,
                loading: true,
                error: null,
                lastUpdated: null
            },
            investments: {
                total_amount: 0,
                count: 0,
                loading: true,
                error: null,
                lastUpdated: null
            },
            transactions: {
                list: [],
                total_count: 0,
                page: 1,
                limit: 20,
                loading: true,
                error: null,
                hasMore: false,
                lastUpdated: null
            },
            accountStatus: {
                is_suspended: false,
                suspension_reason: null,
                freeze_reason: null,
                is_frozen: false
            },
            security: {
                csrf_token: null,
                session_heartbeat: null,
                token_expiry: null,
                last_activity: Date.now()
            }
        };
        
        // Observer subscribers
        this.observers = new Map();
        
        // Session heartbeat interval
        this.heartbeatInterval = null;
        
        // Config
        this.config = {
            AUTO_LOGOUT_AFTER_INACTIVITY_MS: 30 * 60 * 1000, // 30 minutes
            HEARTBEAT_INTERVAL_MS: 5 * 60 * 1000, // 5 minutes
            REFRESH_INTERVAL_MS: 60 * 1000, // 1 minute for non-critical data
            TRANSACTION_LIMIT_DEFAULT: 20,
            LOCALE: navigator.language || 'en-US'
        };
    }
    
    /**
     * Subscribe to state changes
     * Returns unsubscribe function
     */
    subscribe(key, callback) {
        if (!this.observers.has(key)) {
            this.observers.set(key, []);
        }
        this.observers.get(key).push(callback);
        
        // Return unsubscribe function
        return () => {
            const callbacks = this.observers.get(key);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        };
    }
    
    /**
     * Emit state change to all subscribers
     */
    emit(key, newValue) {
        if (this.observers.has(key)) {
            this.observers.get(key).forEach(callback => {
                try {
                    callback(newValue, this.state[key]);
                } catch (e) {
                    console.error(`[STATE] Observer error for ${key}:`, e);
                }
            });
        }
    }
    
    /**
     * Update state and notify observers
     */
    updateState(key, updates) {
        if (!(key in this.state)) {
            console.warn(`[STATE] State key not found: ${key}`);
            return;
        }
        
        const oldState = { ...this.state[key] };
        this.state[key] = { ...this.state[key], ...updates };
        
        console.log(`[STATE] Updated ${key}:`, { from: oldState, to: this.state[key] });
        this.emit(key, this.state[key]);
        
        return this.state[key];
    }
    
    /**
     * Get current state snapshot
     */
    getState(key) {
        return key ? this.state[key] : this.state;
    }
    
    /**
     * Record user activity (for auto-logout)
     */
    recordActivity() {
        this.state.security.last_activity = Date.now();
    }
    
    /**
     * Initialize session heartbeat
     * Periodically validates session is still active
     */
    startSessionHeartbeat() {
        this.heartbeatInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/v1/auth/heartbeat', {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    console.warn('[STATE] Heartbeat failed. Session may have expired.');
                    this.handleSessionExpiry();
                    return;
                }
                
                const data = await response.json();
                if (data.token_expiry) {
                    this.state.security.token_expiry = data.token_expiry;
                }
                
                console.log('[STATE] ✓ Heartbeat OK');
            } catch (e) {
                console.error('[STATE] Heartbeat error:', e);
            }
        }, this.config.HEARTBEAT_INTERVAL_MS);
    }
    
    /**
     * Stop session heartbeat
     */
    stopSessionHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    /**
     * Handle session expiry
     */
    handleSessionExpiry() {
        this.stopSessionHeartbeat();
        localStorage.clear();
        sessionStorage.clear();
        
        // Show alert and redirect
        alert('Your session has expired. Please sign in again.');
        window.location.replace('/signin');
    }
    
    /**
     * Check if token will expire soon (within 5 minutes)
     */
    isTokenExpiringSoon() {
        const expiry = this.state.security.token_expiry;
        if (!expiry) return false;
        
        const now = Date.now();
        const timeUntilExpiry = expiry - now;
        const FIVE_MINUTES = 5 * 60 * 1000;
        
        return timeUntilExpiry < FIVE_MINUTES && timeUntilExpiry > 0;
    }
    
    /**
     * Get currency formatter based on locale and state currency
     */
    getCurrencyFormatter() {
        return new Intl.NumberFormat(this.config.LOCALE, {
            style: 'currency',
            currency: this.state.balance.currency || 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
    
    /**
     * Format currency value
     */
    formatCurrency(amount) {
        try {
            return this.getCurrencyFormatter().format(amount || 0);
        } catch (e) {
            // Fallback if currency not supported
            return `${this.state.balance.currency} ${parseFloat(amount || 0).toFixed(2)}`;
        }
    }
    
    /**
     * Format date based on locale
     */
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return new Intl.DateTimeFormat(this.config.LOCALE, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date);
        } catch (e) {
            return dateString;
        }
    }
    
    /**
     * Mask account number for display
     * Only shows last 4 digits
     */
    maskAccountNumber(accountNumber, reveal = false) {
        if (!accountNumber) return '••••••••';
        if (reveal) return accountNumber;
        const lastFour = accountNumber.substring(accountNumber.length - 4);
        return '••••' + lastFour;
    }
    
    /**
     * Destroy state manager (cleanup)
     */
    destroy() {
        this.stopSessionHeartbeat();
        this.observers.clear();
    }
}

// Export as singleton
const dashboardState = new DashboardStateManager();
console.log('[STATE] State manager initialized');
