/* ============================================
   LONAB - Components JS v2
   ============================================ */

// ============================================
// MODAL MANAGEMENT
// Fermeture UNIQUEMENT via .modal-close ou bouton Annuler
// Le clic sur l'overlay NE ferme PAS le modal
// ============================================
function openModal(modalId) {
    var modal = document.getElementById(modalId);
    if (!modal) { console.warn('Modal not found:', modalId); return; }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    var modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('active');
    document.body.style.overflow = '';
    var form = modal.querySelector('form');
    if (form) {
        form.reset();
        form.querySelectorAll('input[type="hidden"]').forEach(function(el) {
            if (el.id && el.id.endsWith('_id')) el.value = '';
        });
        var titleEl = modal.querySelector('[id$="ModalTitle"]');
        if (titleEl && titleEl.dataset.defaultTitle) {
            titleEl.textContent = titleEl.dataset.defaultTitle;
        }
        form.querySelectorAll('.error-message').forEach(function(e) { e.remove(); });
        form.querySelectorAll('.form-control.error').forEach(function(e) { e.classList.remove('error'); });
    }
}

// Bloquer la fermeture au clic sur l'overlay — monter en bulle stoppée par .modal
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        // Clic sur l'overlay lui-même : ne rien faire
        overlay.addEventListener('click', function (e) {
            // On ne ferme PAS
        });
        // Empêcher le clic sur le .modal de remonter à l'overlay
        const modalBox = overlay.querySelector('.modal');
        if (modalBox) {
            modalBox.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        }
    });

    // Touche Échap : ferme le modal actif (comportement optionnel, peut être retiré)
    // Décommenté ici mais vous pouvez supprimer si vous ne voulez PAS fermer à l'échap
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal-overlay.active');
            if (activeModal) closeModal(activeModal.id);
        }
    });
});

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type, duration) {
    type     = type     || 'success';
    duration = duration || 3800;
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;top:18px;right:18px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
        document.body.appendChild(container);
    }
    var cfg = {
        success: { bg: '#28a745', icon: 'fa-check-circle' },
        error:   { bg: '#dc3545', icon: 'fa-times-circle' },
        warning: { bg: '#f0a500', icon: 'fa-exclamation-triangle' },
        info:    { bg: '#17a2b8', icon: 'fa-info-circle' },
    };
    var c = cfg[type] || cfg.success;
    if (!document.getElementById('toast-keyframes')) {
        var s = document.createElement('style');
        s.id  = 'toast-keyframes';
        s.textContent = '@keyframes toastIn{from{transform:translateX(110%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes toastOut{from{opacity:1}to{opacity:0;transform:translateX(110%)}}';
        document.head.appendChild(s);
    }
    var toast = document.createElement('div');
    toast.style.cssText = 'background:'+c.bg+';color:white;padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;display:flex;align-items:center;gap:9px;box-shadow:0 4px 16px rgba(0,0,0,.22);max-width:340px;min-width:200px;pointer-events:auto;animation:toastIn .25s ease;cursor:pointer;';
    toast.innerHTML = '<i class="fas '+c.icon+'" style="flex-shrink:0;font-size:15px;"></i><span style="flex:1;">'+message+'</span>';
    toast.onclick = function() { toast.remove(); };
    container.appendChild(toast);
    setTimeout(function() {
        toast.style.animation = 'toastOut .25s ease forwards';
        setTimeout(function() { if (toast.parentNode) toast.remove(); }, 260);
    }, duration);
}

function showSuccess(msg) { showToast(msg, 'success'); }
function showError(msg)   { showToast(msg, 'error');   }
function showWarning(msg) { showToast(msg, 'warning'); }
function showInfo(msg)    { showToast(msg, 'info');    }

// ============================================
// CSRF COOKIE
// ============================================
function getCsrfToken() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    if (el) return el.value;
    var match = document.cookie.split(';').map(function(c) { return c.trim(); })
                    .find(function(c) { return c.startsWith('csrftoken='); });
    return match ? match.split('=')[1] : '';
}

// ============================================
// LOADING OVERLAY
// ============================================
function showLoading(message = 'Chargement...') {
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loader">
                <div class="spinner"></div>
                <p id="loadingMessage"></p>
            </div>`;
        document.body.appendChild(overlay);
    }
    document.getElementById('loadingMessage').textContent = message;
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('active');
}

// ── Confirm ────────────────────────────────────────────────────
function showConfirm(title, message, onConfirm, btnLabel) {
    var existing = document.getElementById('globalConfirmModal');
    if (existing) existing.remove();
    btnLabel = btnLabel || 'Supprimer';
    var modal = document.createElement('div');
    modal.id = 'globalConfirmModal';
    modal.className = 'modal-overlay active';
    modal.innerHTML =
        '<div class="modal" style="max-width:420px;width:100%;">'+
          '<div class="modal-header" style="padding:18px 20px;">'+
            '<h3 style="margin:0;font-size:16px;font-weight:700;color:var(--text-primary);">'+title+'</h3>'+
          '</div>'+
          (message ? '<div style="padding:16px 20px;color:var(--text-secondary);font-size:14px;">'+message+'</div>' : '')+
          '<div class="modal-footer" style="padding:14px 20px;border-top:1px solid var(--border-color);display:flex;gap:10px;justify-content:flex-end;">'+
            '<button id="confirmCancel" class="btn btn-secondary">Annuler</button>'+
            '<button id="confirmOk" class="btn" style="background:#dc3545;color:white;">'+
              '<i class="fas fa-exclamation-triangle"></i> '+btnLabel+
            '</button>'+
          '</div>'+
        '</div>';
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    document.getElementById('confirmCancel').onclick = function() {
        modal.remove(); document.body.style.overflow = '';
    };
    document.getElementById('confirmOk').onclick = function() {
        modal.remove(); document.body.style.overflow = '';
        if (typeof onConfirm === 'function') onConfirm();
    };
}

// ── Dropdown ───────────────────────────────────────────────────
function toggleDropdown(id) {
    var el = document.getElementById(id);
    if (!el) return;
    var isOpen = el.classList.contains('open');
    document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
    if (!isOpen) el.classList.add('open');
}
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
    }
});

// ============================================
// DELETE CONFIRMATION
// ============================================
function confirmDelete(itemId, itemName, deleteUrl) {
    // Supprimer l'éventuel modal précédent
    const existing = document.getElementById('_deleteConfirmModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = '_deleteConfirmModal';
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
        <div class="modal modal-small" style="margin-top:90px;" onclick="event.stopPropagation()">
            <div class="modal-header" style="background:linear-gradient(135deg,#dc3545,#c82333);">
                <div class="modal-title">
                    <i class="fas fa-trash-alt"></i>
                    Confirmer la suppression
                </div>
                <button class="modal-close" type="button"
                    onclick="document.getElementById('_deleteConfirmModal').remove(); document.body.style.overflow='';">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body" style="text-align:center;padding:24px 20px;">
                <i class="fas fa-exclamation-triangle"
                   style="font-size:34px;color:#ffc107;display:block;margin-bottom:12px;"></i>
                <p style="font-size:14px;color:#2d3748;margin:0 0 6px;">
                    Supprimer <strong style="color:#dc3545;">${escapeHtml(itemName)}</strong> ?
                </p>
                <p style="font-size:12px;color:#6c757d;margin:0;">Cette action est irréversible.</p>
            </div>
            <div class="modal-footer" style="justify-content:center;gap:10px;">
                <button class="btn btn-outline" type="button"
                    onclick="document.getElementById('_deleteConfirmModal').remove(); document.body.style.overflow='';">
                    <i class="fas fa-times"></i> Annuler
                </button>
                <button class="btn btn-danger" type="button" id="_deleteConfirmBtn">
                    <i class="fas fa-trash-alt"></i> Supprimer
                </button>
            </div>
        </div>`;

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    document.getElementById('_deleteConfirmBtn').addEventListener('click', function () {
        const btn = this;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Suppression...';

        fetch(deleteUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ _method: 'DELETE' }),
        })
        .then(r => r.json())
        .then(data => {
            document.getElementById('_deleteConfirmModal').remove();
            document.body.style.overflow = '';
            if (data.success) {
                showToast(data.message || 'Supprimé avec succès', 'success');
                setTimeout(() => window.location.reload(), 800);
            } else {
                showToast(data.error || 'Erreur lors de la suppression', 'error');
            }
        })
        .catch(() => {
            document.getElementById('_deleteConfirmModal').remove();
            document.body.style.overflow = '';
            showToast('Erreur réseau', 'error');
        });
    });
}

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// ============================================
// PERFORM DELETE (legacy alias)
// ============================================

async function performDelete(url) {
    showLoading('Suppression en cours...');
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ _method: 'DELETE' }),
        });
        hideLoading();
        const data = await response.json();
        if (data.success) {
            showSuccess(data.message || 'Suppression réussie');
            const m = document.getElementById('deleteModal');
            if (m) closeModal('deleteModal');
            setTimeout(() => window.location.reload(), 800);
        } else {
            showError(data.error || 'Erreur lors de la suppression');
        }
    } catch (e) {
        hideLoading();
        showError('Erreur réseau');
    }
}

// ============================================
// FORM SUBMIT — générique AJAX
// ============================================

function submitForm(formId, callback) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        showLoading('Enregistrement...');

        const formData = new FormData(form);
        const url = form.action || window.location.href;

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
            });
            const data = await response.json();
            hideLoading();

            if (data.success) {
                showSuccess(data.message || 'Opération réussie');
                const modal = form.closest('.modal-overlay');
                if (modal) closeModal(modal.id);
                if (typeof callback === 'function') {
                    callback(data);
                } else {
                    setTimeout(() => window.location.reload(), 700);
                }
            } else {
                showError(data.error || 'Une erreur est survenue');
                displayFormErrors(form, data.errors);
            }
        } catch (err) {
            hideLoading();
            showError('Erreur réseau');
        }
    });
}

function displayFormErrors(form, errors) {
    // Nettoyer
    form.querySelectorAll('.error-message').forEach(e => e.remove());
    form.querySelectorAll('.form-control.error').forEach(e => e.classList.remove('error'));
    if (!errors) return;

    for (const [field, messages] of Object.entries(errors)) {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('error');
            const errDiv = document.createElement('div');
            errDiv.className = 'error-message';
            errDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
            input.parentElement.appendChild(errDiv);
        }
    }
}

// ============================================
// DATA TABLE — recherche locale + tri
// ============================================

function initDataTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    // Recherche par saisie
    const searchInput = document.getElementById('tableSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function () {
            filterTable(table, this.value);
        }, 250));
    }

    // Tri par clic sur th
    table.querySelectorAll('th[data-sortable]').forEach(th => {
        th.style.cursor = 'pointer';
        th.style.userSelect = 'none';
        let asc = true;
        th.addEventListener('click', function () {
            const idx = this.cellIndex;
            sortTable(table, idx, asc);
            // Indicateurs visuels
            table.querySelectorAll('th[data-sortable]').forEach(h => {
                h.style.color = '';
                delete h.dataset.sortActive;
            });
            this.style.color = '#28a745';
            this.dataset.sortActive = asc ? 'asc' : 'desc';
            asc = !asc;
        });
    });
}

function filterTable(table, query) {
    const q = query.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = (!q || row.textContent.toLowerCase().includes(q)) ? '' : 'none';
    });
}

function sortTable(table, colIndex, ascending) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
        const aText = (a.cells[colIndex]?.textContent || '').trim();
        const bText = (b.cells[colIndex]?.textContent || '').trim();
        const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return ascending ? aNum - bNum : bNum - aNum;
        }
        return ascending
            ? aText.localeCompare(bText, 'fr', { numeric: true })
            : bText.localeCompare(aText, 'fr', { numeric: true });
    });
    rows.forEach(r => tbody.appendChild(r));
}

// ============================================
// DEBOUNCE
// ============================================

function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// ============================================
// FILTERS (URL params)
// ============================================

function applyFilters(formId) {
    const form = formId ? document.getElementById(formId) : null;
    const params = new URLSearchParams();

    const selects = form
        ? form.querySelectorAll('select, input')
        : document.querySelectorAll('.toolbar-filter select, .toolbar-filter input');

    selects.forEach(el => {
        if (el.name && el.value) params.append(el.name, el.value);
    });

    window.location.search = params.toString();
}

function clearFilters(formId) {
    const form = formId ? document.getElementById(formId) : null;
    if (form) form.reset();
    window.location.search = '';
}

// ============================================
// IMAGE PREVIEW
// ============================================

function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (!preview || !input.files || !input.files[0]) return;
    const reader = new FileReader();
    reader.onload = e => {
        preview.src = e.target.result;
        preview.style.display = 'block';
    };
    reader.readAsDataURL(input.files[0]);
}

// ============================================
// EXPORTS
// ============================================

function exportToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr'));
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        // Exclure la dernière colonne si c'est "Actions"
        const filtered = cells.filter((_, i) => {
            const header = table.querySelectorAll('thead th')[i];
            return !header || !header.classList.contains('actions-column');
        });
        return filtered
            .map(cell => {
                let text = cell.textContent.trim().replace(/\s+/g, ' ');
                if (text.includes(',') || text.includes('"') || text.includes('\n')) {
                    text = `"${text.replace(/"/g, '""')}"`;
                }
                return text;
            })
            .join(',');
    }).join('\n');

    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    _downloadBlob(blob, filename);
    showSuccess('Export CSV généré');
}

function exportToExcel(tableId, filename = 'export.xlsx') {
    // Si une URL serveur est définie, l'utiliser
    if (window._exportExcelUrl) { window.location.href = window._exportExcelUrl; return; }
    // Fallback CSV
    exportToCSV(tableId, filename.replace('.xlsx', '.csv'));
}

function exportToPDF(tableId, filename = 'export.pdf') {
    if (window._exportPdfUrl) { window.location.href = window._exportPdfUrl; return; }
    window.print();
}

function _downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// EXPORTS GLOBAUX
// ============================================

window.openModal      = openModal;
window.closeModal     = closeModal;
window.showToast      = showToast;
window.showSuccess    = showSuccess;
window.showError      = showError;
window.showWarning    = showWarning;
window.showInfo       = showInfo;
window.showLoading    = showLoading;
window.hideLoading    = hideLoading;
window.confirmDelete  = confirmDelete;
window.performDelete  = performDelete;
window.submitForm     = submitForm;
window.initDataTable  = initDataTable;
window.filterTable    = filterTable;
window.sortTable      = sortTable;
window.applyFilters   = applyFilters;
window.clearFilters   = clearFilters;
window.exportToCSV    = exportToCSV;
window.exportToExcel  = exportToExcel;
window.exportToPDF    = exportToPDF;
window.previewImage   = previewImage;
window.getCookie      = getCookie;
window.debounce       = debounce;
