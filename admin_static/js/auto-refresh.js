/**
 * Auto-Refresh Utility for Admin Pages
 * Automatically refreshes admin page data at regular intervals
 */

class AdminAutoRefresh {
    constructor(refreshFunctionName = 'loadData', intervalMs = 30000) {
        this.refreshFunctionName = refreshFunctionName;
        this.intervalMs = intervalMs;
        this.intervalId = null;
        this.lastRefreshTime = null;
    }

    /**
     * Start auto-refresh
     */
    start() {
        if (this.intervalId) this.stop();
        
        this.intervalId = setInterval(() => {
            this.refresh();
        }, this.intervalMs);
        
        console.log(`[Auto-Refresh] Started with ${this.intervalMs}ms interval`);
    }

    /**
     * Stop auto-refresh
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('[Auto-Refresh] Stopped');
        }
    }

    /**
     * Perform refresh
     */
    async refresh() {
        const now = new Date().toLocaleTimeString();
        console.log(`[Auto-Refresh] Refreshing data at ${now}`);
        
        if (window[this.refreshFunctionName] && typeof window[this.refreshFunctionName] === 'function') {
            try {
                await window[this.refreshFunctionName]();
                this.lastRefreshTime = new Date();
                this.updateRefreshStatus();
            } catch (error) {
                console.error('[Auto-Refresh] Error during refresh:', error);
            }
        } else {
            console.warn(`[Auto-Refresh] Function "${this.refreshFunctionName}" not found`);
        }
    }

    /**
     * Update refresh status indicator if available
     */
    updateRefreshStatus() {
        const statusElement = document.getElementById('refreshStatus');
        if (statusElement && this.lastRefreshTime) {
            statusElement.textContent = `Last refreshed: ${this.lastRefreshTime.toLocaleTimeString()}`;
        }
    }

    /**
     * Get information about current auto-refresh state
     */
    getStatus() {
        return {
            isRunning: this.intervalId !== null,
            lastRefresh: this.lastRefreshTime,
            intervalMs: this.intervalMs,
            functionName: this.refreshFunctionName
        };
    }
}

// Export for use in pages
if (typeof window !== 'undefined') {
    window.AdminAutoRefresh = AdminAutoRefresh;
}
