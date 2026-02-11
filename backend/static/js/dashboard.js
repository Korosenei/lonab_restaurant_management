// ============================================
// LONAB - Dashboard JavaScript
// ============================================

// Sidebar toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');

    // Save state to localStorage
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebarCollapsed', isCollapsed);
}

// Restore sidebar state
document.addEventListener('DOMContentLoaded', function() {
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed) {
        document.getElementById('sidebar').classList.add('collapsed');
    }

    // Initialize dropdowns
    initDropdowns();

    // Initialize search
    initGlobalSearch();

    // Mobile menu
    initMobileMenu();
});

// ============================================
// Dropdown Management
// ============================================
function initDropdowns() {
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        const dropdowns = document.querySelectorAll('.dropdown.active');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });
    });
}

function toggleDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    const allDropdowns = document.querySelectorAll('.dropdown');

    // Close other dropdowns
    allDropdowns.forEach(d => {
        if (d.id !== dropdownId) {
            d.classList.remove('active');
        }
    });

    // Toggle current dropdown
    dropdown.classList.toggle('active');
}

// ============================================
// Global Search
// ============================================
function initGlobalSearch() {
    const searchInput = document.getElementById('globalSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', debounce(function(e) {
        const query = e.target.value.trim();
        if (query.length >= 3) {
            performSearch(query);
        }
    }, 300));
}

async function performSearch(query) {
    try {
        const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
        const results = await response.json();
        displaySearchResults(results);
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(results) {
    // Implementation for search results dropdown
    console.log('Search results:', results);
}

// ============================================
// Mobile Menu
// ============================================
function initMobileMenu() {
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'mobile-menu-toggle';
    toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
    toggleBtn.style.cssText = `
        display: none;
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 1001;
        width: 40px;
        height: 40px;
        background: var(--primary-green);
        color: white;
        border: none;
        border-radius: 50%;
        cursor: pointer;
    `;

    toggleBtn.addEventListener('click', function() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('mobile-open');
    });

    document.body.appendChild(toggleBtn);

    // Show button on mobile
    if (window.innerWidth <= 768) {
        toggleBtn.style.display = 'flex';
        toggleBtn.style.alignItems = 'center';
        toggleBtn.style.justifyContent = 'center';
    }

    // Handle resize
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            toggleBtn.style.display = 'flex';
            toggleBtn.style.alignItems = 'center';
            toggleBtn.style.justifyContent = 'center';
        } else {
            toggleBtn.style.display = 'none';
            document.getElementById('sidebar').classList.remove('mobile-open');
        }
    });
}

// ============================================
// Table Utilities
// ============================================
function sortTable(table, column, ascending = true) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
        const aValue = a.cells[column].textContent.trim();
        const bValue = b.cells[column].textContent.trim();

        if (ascending) {
            return aValue.localeCompare(bValue);
        } else {
            return bValue.localeCompare(aValue);
        }
    });

    // Remove existing rows
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }

    // Add sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

function filterTable(table, searchTerm) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// ============================================
// Chart Helpers
// ============================================
function createSimpleChart(canvasId, data) {
    // Simple chart implementation
    // In production, use Chart.js or similar library
    console.log('Chart data:', data);
}

// ============================================
// Form Utilities
// ============================================
function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = 'var(--accent-red)';
            isValid = false;
        } else {
            input.style.borderColor = 'var(--border-color)';
        }
    });

    return isValid;
}

function resetForm(formId) {
    const form = document.getElementById(formId);
    form.reset();

    // Reset any error states
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.style.borderColor = 'var(--border-color)';
    });
}

// ============================================
// Modal Utilities
// ============================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// ============================================
// Data Refresh
// ============================================
function refreshData(callback) {
    showLoading('mainContent');
    setTimeout(() => {
        if (callback) callback();
        hideLoading('mainContent');
    }, 1000);
}

function hideLoading(elementId) {
    // Implementation depends on your loading indicator
    console.log('Hide loading for:', elementId);
}

// ============================================
// Notifications
// ============================================
function markNotificationAsRead(notificationId) {
    makeRequest(`/api/notifications/${notificationId}/mark-read/`, 'POST')
        .then(() => {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                const count = parseInt(badge.textContent) - 1;
                if (count > 0) {
                    badge.textContent = count;
                } else {
                    badge.remove();
                }
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
}

function markAllNotificationsAsRead() {
    makeRequest('/api/notifications/mark-all-read/', 'POST')
        .then(() => {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                badge.remove();
            }
            showSuccess('Toutes les notifications ont été marquées comme lues');
        })
        .catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
}

// ============================================
// Export Functions
// ============================================
window.toggleSidebar = toggleSidebar;
window.toggleDropdown = toggleDropdown;
window.sortTable = sortTable;
window.filterTable = filterTable;
window.validateForm = validateForm;
window.resetForm = resetForm;
window.openModal = openModal;
window.closeModal = closeModal;
window.refreshData = refreshData;
window.markNotificationAsRead = markNotificationAsRead;
window.markAllNotificationsAsRead = markAllNotificationsAsRead;