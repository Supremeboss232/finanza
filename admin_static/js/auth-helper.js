/**
 * Authentication helper for admin pages
 * Provides utilities for API calls with proper authentication
 */

// API Configuration
const apiConfig = {
    baseURL: window.location.origin,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
};

/**
 * Fetch wrapper that automatically includes authentication
 * Supports both cookie-based auth (default) and Bearer token auth
 */
async function authenticatedFetch(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        credentials: 'include', // Important: include cookies for auth
        ...options
    };

    try {
        const response = await fetch(url, defaultOptions);
        
        // If unauthorized, attempt to redirect to login
        if (response.status === 401) {
            console.warn('Unauthorized (401). Check authentication cookie.');
            // Don't redirect - let the caller handle it
        }
        
        if (response.status === 403) {
            console.error('Forbidden (403). Admin access required.');
        }
        
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

/**
 * Helper to make JSON API calls with authentication
 */
async function apiCall(endpoint, options = {}) {
    const url = apiConfig.baseURL + endpoint;
    const response = await authenticatedFetch(url, options);
    
    if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`API Error: ${response.status} ${response.statusText}\n${errorData}`);
    }
    
    return await response.json();
}

console.log('Auth helper loaded. apiConfig:', apiConfig);
