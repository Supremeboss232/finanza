// Lightweight admin fetch helper
// Uses cookie credentials by default and falls back to Authorization header if present in localStorage
window.adminClient = (function(){
    async function adminFetch(path, opts = {}){
        const defaultHeaders = opts.headers || {};
        const token = localStorage.getItem('access_token');
        const headers = Object.assign({}, defaultHeaders);
        if (!('credentials' in opts)) opts.credentials = 'include';
        // If cookie auth not available and token present, send Authorization header
        if (token && !(opts.credentials === 'include')) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        opts.headers = headers;
        return fetch(path, opts);
    }

    async function getJSON(path, opts={}){
        const res = await adminFetch(path, opts);
        if (!res.ok) throw res;
        return res.json();
    }

    async function postJSON(path, body, opts={}){
        opts.method = opts.method || 'POST';
        opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers || {});
        opts.body = JSON.stringify(body);
        return adminFetch(path, opts);
    }

    return { adminFetch, getJSON, postJSON };
})();
