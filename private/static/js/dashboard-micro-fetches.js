/**
 * Dashboard Micro-Fetch Service
 * Implements reactive pattern with independent fetches for each data type
 * 
 * Benefits:
 * - Slow API calls don't block fast ones
 * - Partial UI updates as data arrives
 * - Automatic retry on failures
 * - Request deduplication
 */

class DashboardMicroFetes {
    constructor(stateManager) {
        this.state = stateManager;
        this.requestCache = new Map();
        this.activeRequests = new Map();
        this.retryConfig = {
            maxRetries: 3,
            baseDelayMs: 1000,
            backoffMultiplier: 2
        };
    }
    
    /**
     * Generic fetch with error handling and retry logic
     */
    async fetchWithRetry(url, options = {}, retryCount = 0) {
        const cacheKey = `${options.method || 'GET'}:${url}`;
        
        try {
            // Return cached response if within cache duration
            if (this.requestCache.has(cacheKey)) {
                const cached = this.requestCache.get(cacheKey);
                if (Date.now() - cached.timestamp < (options.cacheDuration || 60000)) {
                    console.log(`[MICRO-FETCH] Cache hit: ${url}`);
                    return cached.data;
                }
            }
            
            // Deduplicate active requests
            if (this.activeRequests.has(cacheKey)) {
                console.log(`[MICRO-FETCH] Request deduplication: ${url}`);
                return this.activeRequests.get(cacheKey);
            }
            
            // Fetch with timeout
            const fetchPromise = this.fetchWithTimeout(url, {
                ...options,
                credentials: 'include'
            }, 30000); // 30 second timeout
            
            this.activeRequests.set(cacheKey, fetchPromise);
            const response = await fetchPromise;
            this.activeRequests.delete(cacheKey);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[MICRO-FETCH] ❌ ${url} returned ${response.status}: ${errorText}`);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const data = await response.json();
            
            // Cache successful response
            this.requestCache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            return data;
            
        } catch (e) {
            this.activeRequests.delete(cacheKey);
            
            console.error(`[MICRO-FETCH] ❌ ${url} failed: ${e.message}`);
            
            // Retry logic with exponential backoff
            if (retryCount < this.retryConfig.maxRetries) {
                const delay = this.retryConfig.baseDelayMs * 
                             Math.pow(this.retryConfig.backoffMultiplier, retryCount);
                
                console.warn(`[MICRO-FETCH] Retry ${retryCount + 1}/${this.retryConfig.maxRetries} for ${url} after ${delay}ms`);
                
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.fetchWithRetry(url, options, retryCount + 1);
            }
            
            throw e;
        }
    }
    
    /**
     * Fetch with timeout
     */
    fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
        return Promise.race([
            fetch(url, options),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
            )
        ]);
    }
    
    /**
     * Fetch user profile (identity & KYC status)
     */
    async fetchUserProfile() {
        console.log('[MICRO-FETCH] Fetching user profile...');
        this.state.updateState('user', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/profile', {
                cacheDuration: 5 * 60 * 1000 // 5 min cache
            });
            
            console.log('[MICRO-FETCH] ✓ User profile response:', data);
            
            this.state.updateState('user', {
                full_name: data.full_name,
                email: data.email,
                kyc_status: data.kyc_status,
                is_verified: data.kyc_status === 'approved',
                loading: false,
                error: null
            });
            
            console.log('[MICRO-FETCH] ✓ User profile loaded');
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ User profile error:', e.message);
            this.state.updateState('user', { 
                loading: false, 
                error: e.message 
            });
            // Still resolve promise even on error (don't rethrow)
            return null;
        }
    }
    
    /**
     * Fetch balance (critical data - frequent updates)
     */
    async fetchBalance() {
        console.log('[MICRO-FETCH] Fetching balance...');
        this.state.updateState('balance', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/balance', {
                cacheDuration: 30000 // 30 sec cache for balance
            });
            
            console.log('[MICRO-FETCH] ✓ Balance response:', data);
            
            this.state.updateState('balance', {
                total: data.total_balance,
                currency: data.currency || 'USD',
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Balance loaded:', data.total_balance);
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Balance error:', e.message);
            this.state.updateState('balance', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch accounts list (with PII masking ready)
     */
    async fetchAccounts() {
        console.log('[MICRO-FETCH] Fetching accounts...');
        this.state.updateState('accounts', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/accounts', {
                cacheDuration: 5 * 60 * 1000 // 5 min cache
            });
            
            console.log('[MICRO-FETCH] ✓ Accounts response:', data);
            
            this.state.updateState('accounts', {
                list: data.accounts || [],
                total_count: data.total || 0,
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Accounts loaded:', data.accounts?.length);
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Accounts error:', e.message);
            this.state.updateState('accounts', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch transactions with pagination
     */
    async fetchTransactions(page = 1, limit = 20) {
        console.log(`[MICRO-FETCH] Fetching transactions page ${page}...`);
        
        // Only show loading on first page
        if (page === 1) {
            this.state.updateState('transactions', { loading: true, error: null });
        }
        
        try {
            const data = await this.fetchWithRetry(
                `/api/user/transactions?page=${page}&limit=${limit}`,
                { cacheDuration: 60000 } // 1 min cache
            );
            
            console.log('[MICRO-FETCH] ✓ Transactions response:', data);
            
            this.state.updateState('transactions', {
                list: page === 1 ? data.transactions : [...this.state.getState('transactions').list, ...data.transactions],
                total_count: data.total,
                page,
                limit,
                hasMore: data.has_more || false,
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Transactions loaded:', data.transactions?.length);
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Transactions error:', e.message);
            this.state.updateState('transactions', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch deposits
     */
    async fetchDeposits() {
        console.log('[MICRO-FETCH] Fetching deposits...');
        this.state.updateState('deposits', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/deposits', {
                cacheDuration: 5 * 60 * 1000
            });
            
            console.log('[MICRO-FETCH] ✓ Deposits response:', data);
            
            this.state.updateState('deposits', {
                list: data.deposits || [],
                total_amount: data.total_amount || 0,
                count: data.count || 0,
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Deposits loaded');
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Deposits error:', e.message);
            this.state.updateState('deposits', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch loans
     */
    async fetchLoans() {
        console.log('[MICRO-FETCH] Fetching loans...');
        this.state.updateState('loans', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/loans', {
                cacheDuration: 5 * 60 * 1000
            });
            
            console.log('[MICRO-FETCH] ✓ Loans response:', data);
            
            this.state.updateState('loans', {
                list: data.loans || [],
                total_amount: data.total_amount || 0,
                count: data.count || 0,
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Loans loaded');
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Loans error:', e.message);
            this.state.updateState('loans', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch investments
     */
    async fetchInvestments() {
        console.log('[MICRO-FETCH] Fetching investments...');
        this.state.updateState('investments', { loading: true, error: null });
        
        try {
            const data = await this.fetchWithRetry('/api/user/investments', {
                cacheDuration: 5 * 60 * 1000
            });
            
            console.log('[MICRO-FETCH] ✓ Investments response:', data);
            
            this.state.updateState('investments', {
                total_amount: data.total_amount || 0,
                count: data.count || 0,
                loading: false,
                error: null,
                lastUpdated: new Date().toISOString()
            });
            
            console.log('[MICRO-FETCH] ✓ Investments loaded');
            return data;
        } catch (e) {
            console.error('[MICRO-FETCH] ❌ Investments error:', e.message);
            this.state.updateState('investments', { 
                loading: false, 
                error: e.message 
            });
            return null;
        }
    }
    
    /**
     * Fetch account status (suspension, freezes)
     */
    async fetchAccountStatus() {
        console.log('[MICRO-FETCH] Fetching account status...');
        
        try {
            const data = await this.fetchWithRetry('/api/user/account-status', {
                cacheDuration: 30000 // 30 sec cache
            });
            
            console.log('[MICRO-FETCH] ✓ Account status response:', data);
            
            this.state.updateState('accountStatus', {
                is_suspended: data.is_suspended || false,
                suspension_reason: data.suspension_reason,
                is_frozen: data.is_frozen || false,
                freeze_reason: data.freeze_reason
            });
            
            if (data.is_suspended || data.is_frozen) {
                console.warn('[MICRO-FETCH] ⚠ Account is suspended or frozen');
            }
            
            return data;
        } catch (e) {
            console.warn('[MICRO-FETCH] ❌ Account status error:', e.message);
            return null;
        }
    }
    
    /**
     * Load all dashboard data in parallel (non-blocking)
     * Returns a promise that resolves when all data is loaded
     */
    loadAllDashboardData() {
        console.log('[MICRO-FETCH] Loading all dashboard data...');
        
        // Return promise so caller can track completion
        return Promise.all([
            this.fetchUserProfile(),
            this.fetchBalance(),
            this.fetchAccounts(),
            this.fetchTransactions(1, 20), // Load first page
            this.fetchDeposits(),
            this.fetchLoans(),
            this.fetchInvestments(),
            this.fetchAccountStatus()
        ]).then(() => {
            console.log('[MICRO-FETCH] ✓ All dashboard data loaded');
        }).catch(e => {
            console.error('[MICRO-FETCH] Error loading dashboard data:', e);
        });
    }
    
    /**
     * Cleanup
     */
    destroy() {
        this.requestCache.clear();
        this.activeRequests.clear();
    }
}

// Create micro-fetches service
let microFetches;
// Don't initialize here - will be initialized in dashboard init
window.DashboardMicroFetes = DashboardMicroFetes;  // Expose class globally
console.log('[MICRO-FETCH] DashboardMicroFetes class exposed to window');
console.log('[MICRO-FETCH] window.DashboardMicroFetes available?', !!window.DashboardMicroFetes);
