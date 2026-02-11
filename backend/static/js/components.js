// ============================================
// LONAB - Modals et Exports
// ============================================

// ============================================
// MODAL MANAGEMENT
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';

        // Reset form if exists
        const form = modal.querySelector('form');
        if (form) {
            form.reset();
            // Clear validation errors
            const errors = form.querySelectorAll('.error-message');
            errors.forEach(error => error.remove());
        }
    }
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal(e.target.id);
    }
});

// Close modal on ESC key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal-overlay.active');
        if (activeModal) {
            closeModal(activeModal.id);
        }
    }
});

// ============================================
// FORM HANDLING
// ============================================

function submitForm(formId, callback) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Show loading
        showLoading();

        const formData = new FormData(form);
        const url = form.action;
        const method = form.method || 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            const data = await response.json();

            hideLoading();

            if (response.ok) {
                showSuccess(data.message || 'Opération réussie');
                if (callback) callback(data);

                // Close modal if exists
                const modal = form.closest('.modal-overlay');
                if (modal) {
                    closeModal(modal.id);
                }

                // Reload page or update table
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showError(data.message || 'Une erreur est survenue');
                displayFormErrors(form, data.errors);
            }
        } catch (error) {
            hideLoading();
            showError('Erreur de connexion');
            console.error(error);
        }
    });
}

function displayFormErrors(form, errors) {
    // Clear previous errors
    const prevErrors = form.querySelectorAll('.error-message');
    prevErrors.forEach(error => error.remove());

    if (!errors) return;

    for (const [field, messages] of Object.entries(errors)) {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = 'color: var(--accent-red); font-size: 11px; margin-top: 4px;';
            errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
            input.parentElement.appendChild(errorDiv);
            input.style.borderColor = 'var(--accent-red)';
        }
    }
}

// ============================================
// DATA TABLE
// ============================================

function initDataTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    // Search functionality
    const searchInput = table.closest('.data-table-wrapper')?.querySelector('.data-table-search input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            filterTable(table, e.target.value);
        }, 300));
    }

    // Sort functionality
    const headers = table.querySelectorAll('th[data-sortable]');
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const column = this.cellIndex;
            const direction = this.dataset.sortDirection === 'asc' ? 'desc' : 'asc';
            this.dataset.sortDirection = direction;
            sortTable(table, column, direction === 'asc');

            // Update sort indicators
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            this.classList.add(`sort-${direction}`);
        });
    });
}

// ============================================
// EXPORTS
// ============================================

async function exportToPDF(tableId, filename = 'export.pdf') {
    showLoading('Génération du PDF...');

    try {
        const response = await fetch(`/api/export/pdf/?table=${tableId}`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, filename, 'application/pdf');
            showSuccess('PDF généré avec succès');
        } else {
            showError('Erreur lors de la génération du PDF');
        }
    } catch (error) {
        showError('Erreur de connexion');
        console.error(error);
    }

    hideLoading();
}

async function exportToExcel(tableId, filename = 'export.xlsx') {
    showLoading('Génération du fichier Excel...');

    try {
        const response = await fetch(`/api/export/excel/?table=${tableId}`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            showSuccess('Fichier Excel généré avec succès');
        } else {
            showError('Erreur lors de la génération du fichier Excel');
        }
    } catch (error) {
        showError('Erreur de connexion');
        console.error(error);
    }

    hideLoading();
}

function exportToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];

    // Headers
    const headers = Array.from(table.querySelectorAll('thead th'))
        .filter(th => !th.classList.contains('actions-column'))
        .map(th => th.textContent.trim());
    csv.push(headers.join(','));

    // Rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'))
            .filter((td, index) => !table.querySelectorAll('thead th')[index]?.classList.contains('actions-column'))
            .map(td => {
                let text = td.textContent.trim();
                // Escape commas and quotes
                if (text.includes(',') || text.includes('"')) {
                    text = `"${text.replace(/"/g, '""')}"`;
                }
                return text;
            });
        csv.push(cells.join(','));
    });

    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    downloadFile(blob, filename, 'text/csv');
    showSuccess('Fichier CSV exporté avec succès');
}

function downloadFile(blob, filename, mimeType) {
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ============================================
// DELETE CONFIRMATION
// ============================================

function confirmDelete(itemId, itemName, deleteUrl) {
    const modal = document.getElementById('deleteModal');
    if (!modal) {
        // Create modal if it doesn't exist
        createDeleteModal();
        return confirmDelete(itemId, itemName, deleteUrl);
    }

    // Update modal content
    modal.querySelector('.delete-item-name').textContent = itemName;
    modal.querySelector('.delete-confirm-btn').onclick = function() {
        performDelete(deleteUrl);
    };

    openModal('deleteModal');
}

function createDeleteModal() {
    const modalHTML = `
        <div class="modal-overlay" id="deleteModal">
            <div class="modal modal-small">
                <div class="modal-header">
                    <div class="modal-title">
                        <i class="fas fa-exclamation-triangle" style="color: var(--accent-red);"></i>
                        Confirmer la suppression
                    </div>
                    <button class="modal-close" onclick="closeModal('deleteModal')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <p style="margin-bottom: var(--spacing-md);">Êtes-vous sûr de vouloir supprimer cet élément ?</p>
                    <p style="font-weight: 600; color: var(--text-primary);"><span class="delete-item-name"></span></p>
                    <p style="margin-top: var(--spacing-md); font-size: 12px; color: var(--text-muted);">
                        <i class="fas fa-info-circle"></i> Cette action est irréversible.
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="closeModal('deleteModal')">
                        <i class="fas fa-times"></i> Annuler
                    </button>
                    <button class="btn btn-danger delete-confirm-btn">
                        <i class="fas fa-trash"></i> Supprimer
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

async function performDelete(url) {
    showLoading('Suppression en cours...');

    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        hideLoading();

        if (response.ok) {
            showSuccess('Suppression réussie');
            closeModal('deleteModal');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            const data = await response.json();
            showError(data.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        hideLoading();
        showError('Erreur de connexion');
        console.error(error);
    }
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
                <p id="loadingMessage">${message}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    document.getElementById('loadingMessage').textContent = message;
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ============================================
// FILTERS
// ============================================

function applyFilters(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const formData = new FormData(form);
    const params = new URLSearchParams(formData);

    // Reload page with filters
    window.location.search = params.toString();
}

function clearFilters(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        window.location.search = '';
    }
}

// ============================================
// IMAGE PREVIEW
// ============================================

function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (!preview) return;

    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================
window.openModal = openModal;
window.closeModal = closeModal;
window.submitForm = submitForm;
window.initDataTable = initDataTable;
window.exportToPDF = exportToPDF;
window.exportToExcel = exportToExcel;
window.exportToCSV = exportToCSV;
window.confirmDelete = confirmDelete;
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;
window.previewImage = previewImage;

