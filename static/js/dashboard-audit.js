/**
 * Dashboard Audit Trail Logger
 * Logs all dashboard visits and actions for security audit trails
 * 
 * Data Logged:
 * - Timestamp
 * - IP address (server-side)
 * - Device info
 * - User agent
 * - Actions performed
 * - Session duration
 */

class DashboardAuditLogger {
    constructor() {
        this.sessionStartTime = Date.now();
        this.actions = [];
        this.maxActionsBuffer = 50;
        this.flushInterval = null;
        this.flushIntervalMs = 5 * 60 * 1000; // Flush every 5 minutes
    }
    
    /**
     * Initialize audit logger
     */
    init() {
        console.log('[AUDIT] Initializing audit logger...');
        
        // Log dashboard access
        this.logAction('dashboard_access', {
            device: this.getDeviceInfo(),
            userAgent: navigator.userAgent
        });
        
        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.logAction('dashboard_hidden');
            } else {
                this.logAction('dashboard_visible');
            }
        });
        
        // Listen for page unload to flush audit data
        window.addEventListener('beforeunload', () => {
            this.logAction('dashboard_exit', {
                sessionDuration: Date.now() - this.sessionStartTime
            });
            this.flushAuditData(true); // Synchronous flush on beforeunload
        });
        
        // Start periodic flush
        this.startPeriodicFlush();
        
        console.log('[AUDIT] ✓ Audit logger initialized');
    }
    
    /**
     * Log a dashboard action
     */
    logAction(actionType, metadata = {}) {
        const action = {
            type: actionType,
            timestamp: new Date().toISOString(),
            metadata
        };
        
        this.actions.push(action);
        console.log(`[AUDIT] Action: ${actionType}`, metadata);
        
        // Auto-flush if buffer is full
        if (this.actions.length >= this.maxActionsBuffer) {
            this.flushAuditData();
        }
    }
    
    /**
     * Get device information
     */
    getDeviceInfo() {
        return {
            screenWidth: window.innerWidth,
            screenHeight: window.innerHeight,
            platform: navigator.platform,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            isMobile: /iPhone|iPad|Android/i.test(navigator.userAgent)
        };
    }
    
    /**
     * Flush audit data to backend
     */
    async flushAuditData(sync = false) {
        if (this.actions.length === 0) {
            return;
        }
        
        const actionsToSend = [...this.actions];
        this.actions = [];
        
        try {
            const payload = {
                actions: actionsToSend,
                sessionStartTime: this.sessionStartTime,
                sessionDuration: Date.now() - this.sessionStartTime
            };
            
            if (sync) {
                // Use sendBeacon for synchronous sending (beforeunload)
                const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                navigator.sendBeacon('/api/v1/audit/dashboard-session', blob);
                console.log('[AUDIT] ✓ Session audit flushed (beacon)');
            } else {
                // Use fetch for asynchronous sending
                const response = await fetch('/api/v1/audit/dashboard-session', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    console.log('[AUDIT] ✓ Audit data flushed');
                } else {
                    console.warn('[AUDIT] Failed to flush audit data');
                    // Re-add actions to buffer if flush failed
                    this.actions.unshift(...actionsToSend);
                }
            }
        } catch (e) {
            console.error('[AUDIT] Error flushing audit data:', e);
            // Re-add actions to buffer if flush failed
            this.actions.unshift(...actionsToSend);
        }
    }
    
    /**
     * Start periodic flush
     */
    startPeriodicFlush() {
        this.flushInterval = setInterval(() => {
            this.flushAuditData();
        }, this.flushIntervalMs);
    }
    
    /**
     * Stop periodic flush
     */
    stopPeriodicFlush() {
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
            this.flushInterval = null;
        }
    }
    
    /**
     * Log button click action
     */
    logButtonClick(buttonId, buttonText) {
        this.logAction('button_click', {
            buttonId,
            buttonText: buttonText || 'Unknown'
        });
    }
    
    /**
     * Log navigation
     */
    logNavigation(destination) {
        this.logAction('navigation', {
            destination
        });
    }
    
    /**
     * Log API call
     */
    logAPICall(endpoint, method, status) {
        this.logAction('api_call', {
            endpoint,
            method,
            status
        });
    }
    
    /**
     * Log account action (transfer, payment, etc)
     */
    logAccountAction(action, details) {
        this.logAction(`account_${action}`, details);
    }
    
    /**
     * Cleanup
     */
    destroy() {
        this.stopPeriodicFlush();
        this.flushAuditData();
        console.log('[AUDIT] Audit logger destroyed');
    }
}

// Initialize audit logger
const dashboardAudit = new DashboardAuditLogger();
console.log('[AUDIT] Audit logger created');
