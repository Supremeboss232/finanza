/**
 * toast-utils.js — Global Toast Notification & Confirm Dialog Utility
 * Finanza Banking Application
 *
 * Exposes:
 *   window.showToast(message, type='success', duration=4000)
 *   window.showConfirm(message) → Promise<boolean>
 */

(function () {
  'use strict';

  /* ─────────────────────────────────────────────
     STYLES
  ───────────────────────────────────────────── */
  var STYLES = [
    '#toastContainer {',
    '  position: fixed;',
    '  top: 20px;',
    '  right: 20px;',
    '  z-index: 9999;',
    '  display: flex;',
    '  flex-direction: column;',
    '  gap: 10px;',
    '  max-width: 360px;',
    '  width: calc(100% - 40px);',
    '  pointer-events: none;',
    '}',
    '',
    '.finanza-toast {',
    '  display: flex;',
    '  align-items: center;',
    '  gap: 12px;',
    '  padding: 14px 16px;',
    '  border-radius: 8px;',
    '  box-shadow: 0 4px 18px rgba(0,0,0,0.18);',
    '  font-family: inherit;',
    '  font-size: 14px;',
    '  line-height: 1.4;',
    '  pointer-events: all;',
    '  cursor: default;',
    '  opacity: 0;',
    '  transform: translateX(110%);',
    '  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.22,1,0.36,1);',
    '  will-change: opacity, transform;',
    '  min-width: 240px;',
    '  position: relative;',
    '  overflow: hidden;',
    '}',
    '',
    '.finanza-toast.toast-show {',
    '  opacity: 1;',
    '  transform: translateX(0);',
    '}',
    '',
    '.finanza-toast.toast-hide {',
    '  opacity: 0;',
    '  transform: translateX(110%);',
    '  transition: opacity 0.3s ease, transform 0.3s ease;',
    '}',
    '',
    '.finanza-toast.toast-success { background: #28a745; color: #fff; }',
    '.finanza-toast.toast-error   { background: #dc3545; color: #fff; }',
    '.finanza-toast.toast-warning { background: #ffc107; color: #212529; }',
    '.finanza-toast.toast-info    { background: #17a2b8; color: #fff; }',
    '',
    '.finanza-toast .toast-icon { font-size: 18px; flex-shrink: 0; line-height: 1; }',
    '.finanza-toast .toast-message { flex: 1; word-break: break-word; }',
    '',
    '.finanza-toast .toast-close {',
    '  background: none; border: none; cursor: pointer;',
    '  font-size: 16px; line-height: 1; padding: 0 0 0 8px;',
    '  opacity: 0.75; flex-shrink: 0; color: inherit; transition: opacity 0.2s;',
    '}',
    '.finanza-toast .toast-close:hover { opacity: 1; }',
    '',
    '.finanza-toast .toast-progress {',
    '  position: absolute; bottom: 0; left: 0;',
    '  height: 3px; width: 100%; border-radius: 0 0 8px 8px;',
    '  background: rgba(255,255,255,0.45);',
    '  transform-origin: left;',
    '  animation-name: toastProgress;',
    '  animation-timing-function: linear;',
    '  animation-fill-mode: forwards;',
    '}',
    '',
    '@keyframes toastProgress {',
    '  from { transform: scaleX(1); }',
    '  to   { transform: scaleX(0); }',
    '}',
    '',
    '/* ── Confirm Modal ── */',
    '.finanza-confirm-overlay {',
    '  position: fixed; inset: 0; z-index: 10500;',
    '  background: rgba(0,0,0,0.5);',
    '  display: flex; align-items: center; justify-content: center;',
    '  animation: fcOverlayIn 0.2s ease;',
    '}',
    '@keyframes fcOverlayIn { from { opacity: 0; } to { opacity: 1; } }',
    '',
    '.finanza-confirm-dialog {',
    '  background: #fff; border-radius: 12px; padding: 32px 28px 24px;',
    '  max-width: 420px; width: calc(100% - 40px);',
    '  box-shadow: 0 8px 40px rgba(0,0,0,0.22);',
    '  font-family: inherit; text-align: center;',
    '  animation: fcDialogIn 0.25s cubic-bezier(0.22,1,0.36,1);',
    '}',
    '@keyframes fcDialogIn {',
    '  from { transform: scale(0.88); opacity: 0; }',
    '  to   { transform: scale(1);    opacity: 1; }',
    '}',
    '.finanza-confirm-dialog .fc-icon { font-size: 36px; color: #ffc107; margin-bottom: 14px; }',
    '.finanza-confirm-dialog .fc-title { font-size: 18px; font-weight: 600; color: #212529; margin-bottom: 10px; }',
    '.finanza-confirm-dialog .fc-message { font-size: 14px; color: #555; margin-bottom: 24px; line-height: 1.5; }',
    '.finanza-confirm-dialog .fc-actions { display: flex; gap: 12px; justify-content: center; }',
    '.finanza-confirm-dialog .fc-btn {',
    '  padding: 9px 24px; border-radius: 6px; border: none;',
    '  font-size: 14px; font-weight: 500; cursor: pointer;',
    '  transition: filter 0.15s; min-width: 90px;',
    '}',
    '.finanza-confirm-dialog .fc-btn:hover { filter: brightness(0.92); }',
    '.finanza-confirm-dialog .fc-btn-cancel  { background: #f1f3f5; color: #495057; }',
    '.finanza-confirm-dialog .fc-btn-confirm { background: #dc3545; color: #fff; }'
  ].join('\n');

  /* ─────────────────────────────────────────────
     INJECT STYLES (once)
  ───────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('finanza-toast-styles')) return;
    var styleEl = document.createElement('style');
    styleEl.id = 'finanza-toast-styles';
    styleEl.textContent = STYLES;
    (document.head || document.documentElement).appendChild(styleEl);
  }

  /* ─────────────────────────────────────────────
     CONTAINER
  ───────────────────────────────────────────── */
  function getContainer() {
    var container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      document.body.appendChild(container);
    }
    return container;
  }

  /* ─────────────────────────────────────────────
     TYPE CONFIG
  ───────────────────────────────────────────── */
  var TYPE_CONFIG = {
    success: { icon: 'fas fa-check-circle',        className: 'toast-success' },
    error:   { icon: 'fas fa-times-circle',         className: 'toast-error'   },
    warning: { icon: 'fas fa-exclamation-triangle', className: 'toast-warning' },
    info:    { icon: 'fas fa-info-circle',          className: 'toast-info'    }
  };

  /* ─────────────────────────────────────────────
     DISMISS HELPER
  ───────────────────────────────────────────── */
  function dismissToast(toast) {
    toast.classList.add('toast-hide');
    toast.classList.remove('toast-show');
    setTimeout(function () {
      if (toast.parentNode) { toast.parentNode.removeChild(toast); }
    }, 350);
  }

  /* ─────────────────────────────────────────────
     showToast
  ───────────────────────────────────────────── */
  /**
   * Display a toast notification.
   * @param {string} message   - Text to display
   * @param {string} type      - 'success' | 'error' | 'warning' | 'info'
   * @param {number} duration  - Auto-dismiss delay in ms (0 = no auto-dismiss)
   */
  function showToast(message, type, duration) {
    type     = TYPE_CONFIG[type] ? type : 'success';
    duration = (typeof duration === 'number') ? duration : 4000;

    injectStyles();
    var container = getContainer();
    var config    = TYPE_CONFIG[type];

    /* Build toast element */
    var toast = document.createElement('div');
    toast.className = 'finanza-toast ' + config.className;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');

    /* Icon */
    var iconEl = document.createElement('i');
    iconEl.className = 'toast-icon ' + config.icon;

    /* Message */
    var msgEl = document.createElement('span');
    msgEl.className = 'toast-message';
    msgEl.textContent = message;

    /* Close button */
    var closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', function () { dismissToast(toast); });

    toast.appendChild(iconEl);
    toast.appendChild(msgEl);
    toast.appendChild(closeBtn);

    /* Progress bar */
    if (duration > 0) {
      var progress = document.createElement('div');
      progress.className = 'toast-progress';
      progress.style.animationDuration = duration + 'ms';
      toast.appendChild(progress);
    }

    container.appendChild(toast);

    /* Trigger slide-in on next frame */
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        toast.classList.add('toast-show');
      });
    });

    /* Auto-dismiss */
    var autoTimer = null;
    if (duration > 0) {
      autoTimer = setTimeout(function () { dismissToast(toast); }, duration);
    }

    /* Pause on hover */
    toast.addEventListener('mouseenter', function () {
      if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
      var prog = toast.querySelector('.toast-progress');
      if (prog) { prog.style.animationPlayState = 'paused'; }
    });
    toast.addEventListener('mouseleave', function () {
      if (duration > 0) {
        var prog = toast.querySelector('.toast-progress');
        if (prog) { prog.style.animationPlayState = 'running'; }
        autoTimer = setTimeout(function () { dismissToast(toast); }, 1500);
      }
    });
  }

  /* ─────────────────────────────────────────────
     showConfirm
  ───────────────────────────────────────────── */
  /**
   * Show a styled confirmation dialog.
   * Uses Bootstrap modal if available, otherwise a custom overlay.
   * @param {string} message
   * @returns {Promise<boolean>}
   */
  function showConfirm(message) {
    return new Promise(function (resolve) {
      injectStyles();

      if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        _showBootstrapConfirm(message, resolve);
      } else if (typeof $ !== 'undefined' && $.fn && $.fn.modal) {
        _showBootstrapConfirm(message, resolve);
      } else {
        _showCustomConfirm(message, resolve);
      }
    });
  }

  /* Bootstrap-based confirm */
  function _showBootstrapConfirm(message, resolve) {
    var modalId = 'finanzaConfirmModal_' + Date.now();
    var modalHtml =
      '<div class="modal fade" id="' + modalId + '" tabindex="-1" role="dialog" aria-modal="true">' +
      '  <div class="modal-dialog modal-dialog-centered" role="document">' +
      '    <div class="modal-content" style="border-radius:12px;overflow:hidden;">' +
      '      <div class="modal-body text-center py-4 px-4">' +
      '        <div style="font-size:36px;color:#ffc107;margin-bottom:14px;"><i class="fas fa-exclamation-triangle"></i></div>' +
      '        <h5 class="modal-title" style="font-weight:600;margin-bottom:10px;">Are you sure?</h5>' +
      '        <p style="color:#555;font-size:14px;margin-bottom:24px;">' + _escapeHtml(message) + '</p>' +
      '        <div class="d-flex gap-3 justify-content-center">' +
      '          <button class="btn btn-secondary fc-cancel-btn" style="min-width:90px;">Cancel</button>' +
      '          <button class="btn btn-danger fc-confirm-btn" style="min-width:90px;">Confirm</button>' +
      '        </div>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '</div>';

    var wrapper = document.createElement('div');
    wrapper.innerHTML = modalHtml;
    var modalEl = wrapper.firstElementChild;
    document.body.appendChild(modalEl);

    var resolved = false;
    function finish(result) {
      if (resolved) return;
      resolved = true;
      if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        var instance = bootstrap.Modal.getInstance(modalEl);
        if (instance) instance.hide();
      } else if (typeof $ !== 'undefined') {
        $(modalEl).modal('hide');
      }
      setTimeout(function () {
        if (modalEl.parentNode) modalEl.parentNode.removeChild(modalEl);
      }, 400);
      resolve(result);
    }

    modalEl.querySelector('.fc-confirm-btn').addEventListener('click', function () { finish(true); });
    modalEl.querySelector('.fc-cancel-btn').addEventListener('click',  function () { finish(false); });
    modalEl.addEventListener('hidden.bs.modal', function () { finish(false); });

    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
      var bsModal = new bootstrap.Modal(modalEl);
      bsModal.show();
    } else if (typeof $ !== 'undefined') {
      $(modalEl).modal('show');
    }
  }

  /* Custom (no-Bootstrap) confirm */
  function _showCustomConfirm(message, resolve) {
    var overlay = document.createElement('div');
    overlay.className = 'finanza-confirm-overlay';
    overlay.innerHTML =
      '<div class="finanza-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="fcTitle">' +
      '  <div class="fc-icon"><i class="fas fa-exclamation-triangle"></i></div>' +
      '  <div class="fc-title" id="fcTitle">Are you sure?</div>' +
      '  <div class="fc-message">' + _escapeHtml(message) + '</div>' +
      '  <div class="fc-actions">' +
      '    <button class="fc-btn fc-btn-cancel">Cancel</button>' +
      '    <button class="fc-btn fc-btn-confirm">Confirm</button>' +
      '  </div>' +
      '</div>';

    document.body.appendChild(overlay);

    var resolved = false;
    function finish(result) {
      if (resolved) return;
      resolved = true;
      overlay.style.animation = 'fcOverlayIn 0.2s ease reverse';
      setTimeout(function () {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }, 220);
      resolve(result);
    }

    overlay.querySelector('.fc-btn-confirm').addEventListener('click', function () { finish(true); });
    overlay.querySelector('.fc-btn-cancel').addEventListener('click',  function () { finish(false); });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) finish(false);
    });
    function onKey(e) {
      if (e.key === 'Escape') { document.removeEventListener('keydown', onKey); finish(false); }
    }
    document.addEventListener('keydown', onKey);
  }

  /* Simple HTML escape */
  function _escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /* ─────────────────────────────────────────────
     EXPOSE GLOBALS
  ───────────────────────────────────────────── */
  window.showToast   = showToast;
  window.showConfirm = showConfirm;

  /* Global Alert Override */
  window.alert = function (message) {
    if (message === undefined || message === null) return;
    var msgStr = String(message);
    var lower = msgStr.toLowerCase();
    var type = 'success';
    
    if (lower.indexOf('error') !== -1 || 
        lower.indexOf('fail') !== -1 || 
        lower.indexOf('invalid') !== -1 || 
        lower.indexOf('unable') !== -1 || 
        lower.indexOf('cannot') !== -1 || 
        lower.indexOf('unauthorized') !== -1 || 
        lower.indexOf('wrong') !== -1) {
      type = 'error';
    } else if (lower.indexOf('warning') !== -1 || 
               lower.indexOf('attention') !== -1 || 
               lower.indexOf('caution') !== -1 || 
               lower.indexOf('confirm') !== -1) {
      type = 'warning';
    } else if (lower.indexOf('info') !== -1 || 
               lower.indexOf('note') !== -1) {
      type = 'info';
    }
    
    showToast(msgStr, type);
  };

})();
