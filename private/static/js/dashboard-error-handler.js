/**
 * Dashboard Error Handler & Recovery Module
 * Handles: Error boundaries, maintenance mode, retry logic, error state UI
 * 
 * Production Features:
 * - Error boundary banner for server unavailability
 * - Maintenance mode detection and redirect
 * - Retry mechanism with exponential backoff
 * - Per-component error states
 * - Silent error logging to audit trail
 * - User-friendly error messages
 */

class DashboardErrorHandler {
    constructor() {
        this.config = {
            MAX_RETRIES: 3,
            RETRY_DELAY_MS: 1000,
            EXPONENTIAL_BACKOFF_FACTOR: 2,
            MAINTENANCE_CHECK_INTERVAL_MS: 30000,
            ERROR_DISPLAY_DURATION_MS: 5000,
        };
        
        this.state = {
            errorBannerVisible: false,
            maintenanceModeActive: false,
            failedComponents: {},
            retryAttempts: {},
            lastErrorTime: null,
        };
        
        this.errorComponents = new Map();
    }
    
    /**
     * Initialize error handler
     */
    init() {
        console.log('[ERROR-HANDLER] Initializing error handler...');
        
        this.setupGlobalErrorHandler();
        this.setupMaintenanceModeCheck();
        this.setupBrowserOnlineCheck();
        
        console.log('[ERROR-HANDLER] ✓ Error handler initialized');
    }
    
    /**
     * Setup global error handler for uncaught exceptions
     */
    setupGlobalErrorHandler() {
        window.addEventListener('error', (event) => {
            console.error('[ERROR-HANDLER] Uncaught error:', event.error);
            this.logErrorEvent({
                type: 'js_error',
                message: event.error?.message || 'Unknown error',
                stack: event.error?.stack,
                timestamp: new Date().toISOString(),
            });
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            console.error('[ERROR-HANDLER] Unhandled rejection:', event.reason);
            this.logErrorEvent({
                type: 'unhandled_rejection',
                message: event.reason?.message || JSON.stringify(event.reason),
                timestamp: new Date().toISOString(),
            });
        });
    }
    
    /**
     * Check if system is in maintenance mode
     */
    setupMaintenanceModeCheck() {
        const checkMaintenance = async () => {
            try {
                const response = await fetch('/api/v1/system/status', {
                    method: 'GET',
                    cache: 'no-cache',
                    timeout: 5000,
                });
                
                if (response.status === 503) {
                    this.handleMaintenanceMode();
                } else if (response.ok) {
                    const data = await response.json();
                    if (data.maintenance === true) {
                        this.handleMaintenanceMode();
                    } else {
                        this.clearMaintenanceMode();
                    }
                }
            } catch (error) {
                console.warn('[ERROR-HANDLER] Maintenance check failed:', error.message);
                // Don't show maintenance mode on network error, only on explicit 503
            }
        };
        
        // Check on load and periodically
        checkMaintenance();
        this.maintenanceIntervalId = setInterval(checkMaintenance, this.config.MAINTENANCE_CHECK_INTERVAL_MS);
    }
    
    /**
     * Handle maintenance mode: show overlay and redirect or wait
     */
    handleMaintenanceMode() {
        if (this.state.maintenanceModeActive) return;
        
        this.state.maintenanceModeActive = true;
        console.warn('[ERROR-HANDLER] System in maintenance mode');
        
        const maintenanceDiv = document.getElementById('maintenance-mode-redirect');
        if (maintenanceDiv) {
            maintenanceDiv.style.display = 'flex';
        }
        
        if (dashboardAudit) {
            dashboardAudit.logAction('maintenance_mode_detected');
        }
    }
    
    /**
     * Clear maintenance mode
     */
    clearMaintenanceMode() {
        if (!this.state.maintenanceModeActive) return;
        
        this.state.maintenanceModeActive = false;
        console.log('[ERROR-HANDLER] Maintenance mode cleared');
        
        const maintenanceDiv = document.getElementById('maintenance-mode-redirect');
        if (maintenanceDiv) {
            maintenanceDiv.style.display = 'none';
        }
    }
    
    /**
     * Monitor browser online/offline status
     */
    setupBrowserOnlineCheck() {
        window.addEventListener('online', () => {
            console.log('[ERROR-HANDLER] Browser online. Attempting to recover...');
            this.hideBanner();
            // Auto-retry failed requests
            this.retryFailedComponents();
        });
        
        window.addEventListener('offline', () => {
            console.warn('[ERROR-HANDLER] Browser offline');
            this.showBanner('No internet connection. Some data may be unavailable.');
        });
    }
    
    /**
     * Show error boundary banner
     */
    showBanner(message = 'We\'re having trouble reaching the server. Some data may be outdated.') {
        if (this.state.errorBannerVisible) return;
        
        this.state.errorBannerVisible = true;
        this.state.lastErrorTime = Date.now();
        
        const banner = document.getElementById('error-boundary-banner');
        if (banner) {
            document.getElementById('error-boundary-message').textContent = message;
            banner.style.display = 'block';
        }
        
        console.warn('[ERROR-HANDLER] Error banner shown:', message);
    }
    
    /**
     * Hide error boundary banner
     */
    hideBanner() {
        if (!this.state.errorBannerVisible) return;
        
        this.state.errorBannerVisible = false;
        
        const banner = document.getElementById('error-boundary-banner');
        if (banner) {
            banner.style.display = 'none';
        }
        
        console.log('[ERROR-HANDLER] Error banner hidden');
    }
    
    /**
     * Register component for error state management
     */
    registerComponent(componentId, retryCallback) {
        this.errorComponents.set(componentId, {
            id: componentId,
            retryCallback,
            retryCount: 0,
            lastError: null,
        });
    }
    
    /**
     * Handle component error
     */
    handleComponentError(componentId, error, options = {}) {
        console.error(`[ERROR-HANDLER] Component error [${componentId}]:`, error);
        
        const { showBanner = true, showLocalError = true, message = null } = options;
        
        this.state.failedComponents[componentId] = {
            error: error.message || String(error),
            timestamp: Date.now(),
            retryCount: this.state.retryAttempts[componentId] || 0,
        };
        
        if (showBanner) {
            this.showBanner(message || 'We\'re having trouble loading this data. Please try again.');
        }
        
        if (showLocalError) {
            this.showComponentError(componentId, error);
        }
        
        this.logErrorEvent({
            type: 'component_error',
            componentId,
            message: error.message,
            retryCount: this.state.retryAttempts[componentId] || 0,
            timestamp: new Date().toISOString(),
        });
    }
    
    /**
     * Show error state in component UI
     */
    showComponentError(componentId, error) {
        const container = document.getElementById(componentId + '-container') || 
                         document.getElementById(componentId);
        
        if (!container) return;
        
        const errorHtml = `
            <div class="data-error-state">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Unable to load data</strong>
                <p class="mb-2 small text-muted">${error.message || 'Please check your connection and try again.'}</p>
                <button class="retry-btn" onclick="dashboardErrorHandler.retryComponent('${componentId}')">
                    <i class="fas fa-sync-alt me-1"></i>Retry
                </button>
            </div>
        `;
        
        container.innerHTML = errorHtml;
    }
    
    /**
     * Retry failed component
     */
    async retryComponent(componentId) {
        const component = this.errorComponents.get(componentId);
        
        if (!component) {
            console.warn(`[ERROR-HANDLER] Component ${componentId} not registered`);
            return;
        }
        
        const retryCount = this.state.retryAttempts[componentId] || 0;
        
        if (retryCount >= this.config.MAX_RETRIES) {
            console.error(`[ERROR-HANDLER] Max retries exceeded for ${componentId}`);
            return;
        }
        
        this.state.retryAttempts[componentId] = retryCount + 1;
        
        console.log(`[ERROR-HANDLER] Retrying ${componentId} (attempt ${retryCount + 1}/${this.config.MAX_RETRIES})`);
        
        try {
            await component.retryCallback();
            
            // Clear error state on success
            delete this.state.failedComponents[componentId];
            console.log(`[ERROR-HANDLER] ✓ ${componentId} recovered successfully`);
            
        } catch (error) {
            console.error(`[ERROR-HANDLER] Retry failed for ${componentId}:`, error);
            this.handleComponentError(componentId, error, { showBanner: true });
        }
    }
    
    /**
     * Retry all failed components
     */
    async retryFailedComponents() {
        const failedComponentIds = Object.keys(this.state.failedComponents);
        
        console.log(`[ERROR-HANDLER] Retrying ${failedComponentIds.length} failed components...`);
        
        for (const componentId of failedComponentIds) {
            await this.retryComponent(componentId);
            // Stagger retries to avoid thundering herd
            await new Promise(resolve => setTimeout(resolve, 200));
        }
    }
    
    /**
     * Get exponential backoff delay
     */
    getBackoffDelay(retryCount) {
        const delay = this.config.RETRY_DELAY_MS * 
                     Math.pow(this.config.EXPONENTIAL_BACKOFF_FACTOR, retryCount);
        
        // Add jitter to prevent thundering herd
        const jitter = Math.random() * 0.1 * delay;
        return delay + jitter;
    }
    
    /**
     * Retry API call with exponential backoff
     */
    async retryFetch(url, options = {}, maxRetries = this.config.MAX_RETRIES) {
        let lastError;
        
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                const response = await fetch(url, {
                    ...options,
                    timeout: options.timeout || 30000,
                });
                
                if (response.ok || response.status === 404) {
                    return response;
                }
                
                if (response.status === 429 || response.status === 503) {
                    // Rate limited or service unavailable - retry
                    const delay = this.getBackoffDelay(attempt);
                    console.warn(`[ERROR-HANDLER] Rate limited or unavailable. Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }
                
                // Other errors (4xx, 5xx) - don't retry
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                
            } catch (error) {
                lastError = error;
                
                if (attempt < maxRetries - 1) {
                    const delay = this.getBackoffDelay(attempt);
                    console.warn(`[ERROR-HANDLER] Fetch failed (attempt ${attempt + 1}/${maxRetries}). Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                } else {
                    console.error('[ERROR-HANDLER] Max retries exceeded');
                }
            }
        }
        
        throw lastError || new Error('Max retries exceeded');
    }
    
    /**
     * Log error event to audit trail
     */
    logErrorEvent(event) {
        if (dashboardAudit) {
            dashboardAudit.logAction('error_event', {
                type: event.type,
                message: event.message,
                componentId: event.componentId,
                retryCount: event.retryCount,
                timestamp: event.timestamp,
            });
        }
    }
    
    /**
     * Get error statistics for debugging
     */
    getErrorStats() {
        return {
            errorBannerVisible: this.state.errorBannerVisible,
            maintenanceModeActive: this.state.maintenanceModeActive,
            failedComponents: this.state.failedComponents,
            retryAttempts: this.state.retryAttempts,
            lastErrorTime: this.state.lastErrorTime,
        };
    }
    
    /**
     * Clear all error states
     */
    clearAllErrors() {
        this.hideBanner();
        this.state.failedComponents = {};
        this.state.retryAttempts = {};
        console.log('[ERROR-HANDLER] All error states cleared');
    }
    
    /**
     * Destroy error handler
     */
    destroy() {
        if (this.maintenanceIntervalId) {
            clearInterval(this.maintenanceIntervalId);
        }
        this.errorComponents.clear();
        console.log('[ERROR-HANDLER] Destroyed');
    }
}

// Global instance
const dashboardErrorHandler = new DashboardErrorHandler();
