// ============================================
// LONAB - Main JavaScript
// ============================================

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('LONAB System initialized');

    // Initialize auto-hide alerts
    initAlerts();
});

// ============================================
// Alerts Management
// ============================================
function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Auto-hide after 5 seconds
        setTimeout(() => {
            fadeOut(alert);
        }, 5000);
    });
}

function fadeOut(element) {
    element.style.transition = 'opacity 0.3s ease';
    element.style.opacity = '0';
    setTimeout(() => {
        element.remove();
    }, 300);
}

// ============================================
// Utility Functions
// ============================================

// Format number with spaces (1000 => 1 000)
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

// Format currency
function formatCurrency(amount, currency = 'FCFA') {
    return `${formatNumber(amount)} ${currency}`;
}

// Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
    return new Date(dateString).toLocaleDateString('fr-FR', options);
}

// Format datetime
function formatDateTime(dateString) {
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleString('fr-FR', options);
}

// Show loading spinner
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: var(--text-muted);">Chargement...</p>
            </div>
        `;
    }
}

// Show success message
function showSuccess(message) {
    showNotification(message, 'success');
}

// Show error message
function showError(message) {
    showNotification(message, 'error');
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; animation: slideInRight 0.3s ease;';

    const icon = type === 'error' ? 'exclamation-circle' :
                 type === 'success' ? 'check-circle' : 'info-circle';

    notification.innerHTML = `
        <i class="fas fa-${icon}"></i>
        ${message}
        <button onclick="this.parentElement.remove()" style="margin-left: auto; padding: 4px 8px; background: none; border: none; color: inherit; cursor: pointer;">
            <i class="fas fa-times"></i>
        </button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        fadeOut(notification);
    }, 5000);
}

// Confirm dialog
function confirm(message, callback) {
    if (window.confirm(message)) {
        callback();
    }
}

// AJAX request helper
async function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || 'Une erreur est survenue');
        }

        return result;
    } catch (error) {
        showError(error.message);
        throw error;
    }
}

// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showSuccess('Copié dans le presse-papiers');
    }).catch(() => {
        showError('Erreur lors de la copie');
    });
}

// Print page
function printPage() {
    window.print();
}

// Export to CSV
function exportToCSV(data, filename = 'export.csv') {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function convertToCSV(data) {
    const array = typeof data !== 'object' ? JSON.parse(data) : data;
    let str = '';

    // Header
    const header = Object.keys(array[0]).join(',');
    str += header + '\r\n';

    // Rows
    for (let i = 0; i < array.length; i++) {
        let line = '';
        for (let index in array[i]) {
            if (line !== '') line += ',';
            line += array[i][index];
        }
        str += line + '\r\n';
    }

    return str;
}