// user-client.js
// Fetches user stats and updates the dashboard; listens to realtime events and refreshes data.
(function(){
    async function fetchStats(){
        try{
            // Note: API path depends on router prefixes; try common paths
            const candidates = [
                '/api/v1/users/users/me/stats',
                '/api/v1/users/me/stats',
                '/api/v1/users/me/stats',
                '/api/v1/users/me/stats'
            ];
            let res, data;
            for(const url of candidates){
                try{
                    res = await fetch(url, {credentials: 'include'});
                    if(res.ok){ data = await res.json(); break; }
                }catch(e){ continue; }
            }
            if(!data) return;
            document.getElementById('user-balance')?.textContent = (data.balance ? data.balance.toLocaleString() : '0.00');
            document.getElementById('user-investments')?.textContent = (data.investments ? data.investments.toLocaleString() : '0.00');
            document.getElementById('user-loans')?.textContent = (data.loans ? data.loans.toLocaleString() : '0.00');

            // Recent transactions
            const tbody = document.querySelector('table.table tbody');
            if(tbody && data.recent_transactions){
                // remove old rows except template
                Array.from(tbody.querySelectorAll('tr')).forEach(r => { if(r.id !== 'txn-row-template') r.remove() });
                const tmpl = document.getElementById('txn-row-template');
                data.recent_transactions.forEach(txn =>{
                    const tr = tmpl.cloneNode(true);
                    tr.style.display = '';
                    tr.id = '';
                    tr.querySelector('.txn-date').textContent = txn.created_at?.split('T')[0] ?? txn.created_at ?? '';
                    tr.querySelector('.txn-desc').textContent = txn.transaction_type ?? txn.description ?? '';
                    let amt = txn.amount ?? 0;
                    tr.querySelector('.txn-amount').textContent = (amt >= 0 ? '+ ' : '- ') + Math.abs(amt).toFixed(2);
                    const amtClass = amt >= 0 ? 'text-success' : 'text-danger';
                    tr.querySelector('.txn-amount').className = 'txn-amount ' + amtClass;
                    tbody.appendChild(tr);
                })
            }
        }catch(e){ console.debug('Failed to fetch stats', e); }
    }

    // expose handler used by realtime.js
    window.onRealtimeMessage = function(text){
        try{
            const payload = JSON.parse(text);
            if(payload.event && payload.event.startsWith('user:')){
                // For user-specific pages, refresh stats when user-related events occur
                fetchStats();
            }
        }catch(e){ /* ignore non-json messages */ }
    }

    // initial load
    fetchStats();
    // refresh periodically as fallback
    setInterval(fetchStats, 60000);

})();
