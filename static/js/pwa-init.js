/**
 * Finanza PWA Initializer & Mobile App Installer
 * Injects Web App Manifest, iOS/Android standalone meta tags, registers /sw.js,
 * and provides one-tap "Install Finanza App" support on Android & iOS.
 */
(function () {
    if (window.__FINANZA_PWA_INITIALIZED__) return;
    window.__FINANZA_PWA_INITIALIZED__ = true;

    let deferredPrompt = null;

    function injectPwaHeadTags() {
        const head = document.head || document.getElementsByTagName('head')[0];
        if (!head) return;

        const ensureLink = (rel, href) => {
            if (!head.querySelector(`link[rel="${rel}"]`)) {
                const l = document.createElement('link');
                l.rel = rel;
                l.href = href;
                head.appendChild(l);
            }
        };

        const ensureMeta = (name, content) => {
            if (!head.querySelector(`meta[name="${name}"]`)) {
                const m = document.createElement('meta');
                m.name = name;
                m.content = content;
                head.appendChild(m);
            }
        };

        ensureLink('manifest', '/manifest.json');
        ensureLink('apple-touch-icon', '/static/img/apple-touch-icon.png');
        ensureMeta('theme-color', '#667eea');
        ensureMeta('mobile-web-app-capable', 'yes');
        ensureMeta('apple-mobile-web-app-capable', 'yes');
        ensureMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
        ensureMeta('apple-mobile-web-app-title', 'Finanza');
    }

    function isStandaloneApp() {
        return (
            window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true
        );
    }

    function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function () {
                navigator.serviceWorker
                    .register('/sw.js', { scope: '/' })
                    .catch(function (err) {
                        console.debug('SW registration info:', err);
                    });
            });
        }
    }

    function showInstallGuideModal() {
        let modal = document.getElementById('finanzaPwaGuideModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'finanzaPwaGuideModal';
            modal.style.cssText =
                'display:flex;position:fixed;inset:0;background:rgba(15,23,42,0.75);z-index:100000;align-items:center;justify-content:center;padding:16px;backdrop-filter:blur(4px);';
            document.body.appendChild(modal);
        }

        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        const stepsHtml = isIOS
            ? `
                <ol style="text-align:left;padding-left:20px;margin:12px 0;line-height:1.7;color:#1e293b;font-size:0.9rem;">
                    <li>Tap the <strong>Share</strong> button <span style="background:#e2e8f0;padding:2px 6px;border-radius:4px;">&#x2191;</span> at the bottom of Safari.</li>
                    <li>Scroll down and tap <strong>Add to Home Screen</strong>.</li>
                    <li>Tap <strong>Add</strong> in the top-right corner to launch Finanza full-screen.</li>
                </ol>
              `
            : `
                <ol style="text-align:left;padding-left:20px;margin:12px 0;line-height:1.7;color:#1e293b;font-size:0.9rem;">
                    <li>Tap the browser menu <strong>&#8942;</strong> (top-right corner of Chrome).</li>
                    <li>Select <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
                    <li>Confirm <strong>Install</strong> to add the Finanza app to your phone's app drawer.</li>
                </ol>
              `;

        modal.innerHTML = `
            <div style="background:#fff;border-radius:16px;max-width:400px;width:100%;padding:24px;box-shadow:0 20px 50px rgba(0,0,0,0.3);text-align:center;">
                <img src="/static/img/icon-192.png" alt="Finanza" style="width:64px;height:64px;border-radius:14px;margin-bottom:12px;box-shadow:0 4px 12px rgba(102,126,234,0.35);">
                <h4 style="margin:0 0 6px;color:#0f172a;font-weight:700;font-size:1.15rem;">Install Finanza Mobile App</h4>
                <p style="margin:0 0 12px;color:#64748b;font-size:0.85rem;">Launch Finanza full-screen from your home screen with zero browser bars.</p>
                ${stepsHtml}
                <button type="button" onclick="document.getElementById('finanzaPwaGuideModal').style.display='none'" style="margin-top:10px;width:100%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;padding:11px;border-radius:10px;font-weight:700;cursor:pointer;">Got It</button>
            </div>
        `;
        modal.style.display = 'flex';
    }

    window.installFinanzaApp = async function () {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            try {
                const choice = await deferredPrompt.userChoice;
                if (choice && choice.outcome === 'accepted') {
                    deferredPrompt = null;
                    hideInstallBanners();
                }
            } catch (_) {}
            return;
        }
        showInstallGuideModal();
    };

    function hideInstallBanners() {
        const banner = document.getElementById('finanzaPwaInstallBanner');
        if (banner) banner.style.display = 'none';
        document.querySelectorAll('.finanza-pwa-install-btn').forEach(el => {
            el.style.display = 'none';
        });
    }

    function injectFloatingInstallBanner() {
        if (isStandaloneApp()) return;
        if (sessionStorage.getItem('finanza_pwa_banner_dismissed') === '1') return;
        if (document.getElementById('finanzaPwaInstallBanner')) return;

        const banner = document.createElement('div');
        banner.id = 'finanzaPwaInstallBanner';
        banner.style.cssText =
            'position:fixed;bottom:74px;left:12px;right:12px;max-width:440px;margin:0 auto;background:linear-gradient(135deg,#1e1b4b 0%,#312e81 100%);color:#fff;border-radius:14px;padding:12px 14px;box-shadow:0 12px 30px rgba(0,0,0,0.35);z-index:9990;display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid rgba(255,255,255,0.18);';
        banner.innerHTML = `
            <div style="display:flex;align-items:center;gap:10px;min-width:0;">
                <img src="/static/img/icon-192.png" alt="Finanza" style="width:40px;height:40px;border-radius:10px;flex-shrink:0;">
                <div style="min-width:0;">
                    <div style="font-weight:700;font-size:0.86rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Finanza Mobile App</div>
                    <div style="font-size:0.74rem;color:#cbd5e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Install for full-screen banking access</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                <button type="button" onclick="window.installFinanzaApp()" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;padding:7px 13px;border-radius:8px;font-weight:700;font-size:0.78rem;cursor:pointer;">Install</button>
                <button type="button" aria-label="Dismiss" onclick="sessionStorage.setItem('finanza_pwa_banner_dismissed','1');document.getElementById('finanzaPwaInstallBanner').style.display='none';" style="background:transparent;border:none;color:#cbd5e1;font-size:1.1rem;padding:2px 6px;cursor:pointer;">&times;</button>
            </div>
        `;
        document.body.appendChild(banner);
    }

    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        deferredPrompt = e;
        injectFloatingInstallBanner();
    });

    window.addEventListener('appinstalled', function () {
        deferredPrompt = null;
        hideInstallBanners();
    });

    injectPwaHeadTags();
    registerServiceWorker();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            if (!isStandaloneApp() && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                setTimeout(injectFloatingInstallBanner, 1500);
            }
        });
    } else if (!isStandaloneApp() && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
        setTimeout(injectFloatingInstallBanner, 1500);
    }
})();
