// page-sync.js
// Generic page synchronizer: detects which user page is open and loads data
(function(){
    const path = location.pathname.replace(/\/$/, '');
    const container = document.querySelector('.container-xxl .container .row .col-lg-12');

    async function fetchAndRender(url, renderFn){
        try{
            const res = await fetch(url, {credentials: 'include'});
            if(!res.ok){ console.debug('Fetch failed', url, res.status); return; }
            const data = await res.json();
            renderFn(data);
        }catch(e){ console.debug('Fetch error', e); }
    }

    function renderList(title, items, fields){
        if(!container) return;
        const card = document.createElement('div');
        card.className = 'card';
        const body = document.createElement('div'); body.className='card-body';
        const h = document.createElement('h5'); h.className='card-title'; h.textContent = title;
        body.appendChild(h);
        const ul = document.createElement('ul'); ul.className='list-group list-group-flush';
        items.forEach(it =>{
            const li = document.createElement('li'); li.className='list-group-item';
            const parts = fields.map(f=> it[f] ?? '').join(' • ');
            li.textContent = parts;
            ul.appendChild(li);
        });
        body.appendChild(ul);
        card.appendChild(body);
        container.prepend(card);
    }

    // Map routes to API endpoints and renderers
    if(path.endsWith('/cards')){
        fetchAndRender('/api/v1/cards/', data => renderList('Your Cards', data, ['card_type','card_number','status']));
    } else if(path.endsWith('/deposits')){
        fetchAndRender('/api/v1/deposits/', data => renderList('Your Deposits', data, ['amount','currency','status']));
    } else if(path.endsWith('/loans')){
        fetchAndRender('/api/v1/loans/', data => renderList('Your Loans', data, ['amount','interest_rate','status']));
    } else if(path.endsWith('/investments')){
        fetchAndRender('/api/v1/investments/', data => renderList('Your Investments', data, ['investment_type','amount','status']));
    } else if(path.endsWith('/kyc') || path.endsWith('/kyc/verify') || path.endsWith('/kyc_form.html')){
        // KYC form and status pages are handled server-side but we can show recent submissions
        fetchAndRender('/api/v1/kyc/submissions', data => renderList('KYC Submissions', data, ['document_type','status']));
    } else if(path.endsWith('/account') || path.endsWith('/profile')){
        // Show core user info (already provided server-side) — optionally refresh via API
        fetchAndRender('/api/v1/users/me/', data => {
            if(!container) return;
            const card = document.createElement('div'); card.className='card';
            const body = document.createElement('div'); body.className='card-body';
            body.innerHTML = `<h5 class="card-title">Account</h5><p><strong>Name:</strong> ${data.full_name ?? ''}</p><p><strong>Email:</strong> ${data.email}</p>`;
            card.appendChild(body); container.prepend(card);
        });
    }

    // React to realtime events by reloading the page-specific data
    window.onRealtimeMessage = function(text){
        try{ const payload = JSON.parse(text); if(payload.event && payload.event.startsWith('user:')) location.reload(); }catch(e){}
    }

})();
