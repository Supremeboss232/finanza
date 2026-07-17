/**
 * Dashboard Global Guard Script
 * Prevents Flash of Unauthenticated Content (FOUC)
 * Runs BEFORE any HTML or CSS is rendered
 * 
 * CRITICAL: This script must be loaded in <head> BEFORE all other resources
 * Place this tag at the very top of <head>:
 * <script src="/static/js/dashboard-guard.js"></script>
 */

(function() {
    'use strict';
    
    const TIMEOUT = 3000; // 3 second timeout for token check
    const TOKEN_KEY = 'token';
    const NULL_TOKEN = 'NO_TOKEN_FOUND';
    
    // Immediately hide body to prevent FOUC
    document.documentElement.style.opacity = '0';
    document.documentElement.style.visibility = 'hidden';
    
    // Add timeout to show body anyway (fail-safe)
    let renderTimeout = setTimeout(() => {
        console.warn('[GUARD] Timeout: Showing dashboard anyway');
        revealPage();
    }, TIMEOUT);
    
    /**
     * Check token in cookie and localStorage
     * Prioritizes HTTP-only cookie (more secure)
     */
    function getValidToken() {
        // Check localStorage as backup
        const token = localStorage.getItem(TOKEN_KEY);
        if (!token) {
            return null;
        }
        
        // Validate token format (basic JWT check)
        if (!isValidJWTFormat(token)) {
            return null;
        }
        
        return token;
    }
    
    /**
     * Basic JWT format validation
     * JWT format: header.payload.signature
     */
    function isValidJWTFormat(token) {
        if (typeof token !== 'string') return false;
        const parts = token.split('.');
        return parts.length === 3 && parts.every(part => part.length > 0);
    }
    
    /**
     * Decode JWT payload (without verification)
     * Used to check expiry
     */
    function decodeJWT(token) {
        try {
            const payload = token.split('.')[1];
            const decoded = JSON.parse(atob(payload));
            return decoded;
        } catch (e) {
            console.warn('[GUARD] Invalid JWT:', e);
            return null;
        }
    }
    
    /**
     * Check if token is expired
     */
    function isTokenExpired(token) {
        const decoded = decodeJWT(token);
        if (!decoded || !decoded.exp) {
            return false; // Can't determine expiry, allow
        }
        
        const now = Math.floor(Date.now() / 1000);
        return decoded.exp < now;
    }
    
    /**
     * Verify token is still valid on backend
     * This also validates the token hasn't been revoked/logged out
     */
    async function verifyTokenOnBackend(token) {
        try {
            const response = await fetch('/api/v1/auth/verify-token', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            return response.ok;
        } catch (e) {
            console.error('[GUARD] Token verification failed:', e);
            return false;
        }
    }
    
    /**
     * Show unauthorized page (quick redirect)
     */
    function redirectToSignin() {
        clearTimeout(renderTimeout);
        localStorage.clear();
        sessionStorage.clear();
        
        // Set flag so signin page knows why they're there
        sessionStorage.setItem('redirect_reason', 'session_expired');
        
        // Use replace to prevent back button access
        window.location.replace('/signin');
    }
    
    /**
     * Reveal and initialize dashboard
     */
    function revealPage() {
        clearTimeout(renderTimeout);
        document.documentElement.style.opacity = '1';
        document.documentElement.style.visibility = 'visible';
        
        // Signal that guard check passed
        window.DASHBOARD_GUARD_PASSED = true;
        
        // Trigger custom event for other scripts to initialize
        window.dispatchEvent(new CustomEvent('dashboardGuardPassed'));
        
        console.log('[GUARD] ✓ Dashboard guard cleared. Rendering page.');
    }
    
    /**
     * Main guard check orchestration
     */
    async function performGuardCheck() {
        try {
            // Step 1: Check localStorage for token
            const token = getValidToken();
            if (!token) {
                console.warn('[GUARD] ✗ No valid token found. Redirecting to signin.');
                redirectToSignin();
                return;
            }
            
            // Step 2: Check token expiry (client-side)
            if (isTokenExpired(token)) {
                console.warn('[GUARD] ✗ Token expired. Redirecting to signin.');
                redirectToSignin();
                return;
            }
            
            // Step 3: Verify token with backend (ensures session is valid, not revoked)
            const isValid = await verifyTokenOnBackend(token);
            if (!isValid) {
                console.warn('[GUARD] ✗ Token verification failed on backend. Redirecting to signin.');
                redirectToSignin();
                return;
            }
            
            // All checks passed - reveal dashboard
            revealPage();
            
        } catch (e) {
            console.error('[GUARD] Critical error during guard check:', e);
            // On critical error, allow page to show but will fail when loading data
            revealPage();
        }
    }
    
    // Execute guard check immediately
    performGuardCheck();
    
})();
