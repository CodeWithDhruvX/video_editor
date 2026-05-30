// Main JavaScript file for Video Processor Pro

// Global state
const AppState = {
    selectedVideos: [],
    isAuthenticated: false,
    currentTaskId: null,
    uploadTaskId: null,
    processingConfig: {}
};

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function generateUniqueId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function showError(message) {
    console.error(message);
    alert('Error: ' + message);
}

function showSuccess(message) {
    console.log(message);
    // Could implement a toast notification here
}

// API helper functions
async function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (options.body && typeof options.body === 'object') {
        options.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(endpoint, { ...defaultOptions, ...options });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// File upload helper
async function uploadFile(file, endpoint = '/api/upload-video') {
    const formData = new FormData();
    formData.append('video', file);
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        return data;
    } catch (error) {
        console.error('File Upload Error:', error);
        throw error;
    }
}

// Status polling helper
function pollStatus(taskId, callback, interval = 2000) {
    const poll = async () => {
        try {
            const data = await apiRequest(`/api/status/${taskId}`);
            callback(data);
            
            if (data.status === 'processing') {
                setTimeout(poll, interval);
            }
        } catch (error) {
            console.error('Status polling error:', error);
        }
    };
    
    poll();
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Video Processor Pro initialized');
    
    // Check for existing config
    loadExistingConfig();
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Load existing configuration
async function loadExistingConfig() {
    try {
        const data = await apiRequest('/api/config/load');
        if (data.success && data.config) {
            AppState.processingConfig = data.config;
            console.log('Configuration loaded:', data.config);
        }
    } catch (error) {
        console.log('No existing configuration found');
    }
}

// Form validation helpers
function validateRequired(fields) {
    const missing = [];
    
    fields.forEach(field => {
        const element = document.getElementById(field.id);
        if (!element || !element.value) {
            missing.push(field.name);
        }
    });
    
    if (missing.length > 0) {
        showError(`Missing required fields: ${missing.join(', ')}`);
        return false;
    }
    
    return true;
}

// Progress bar updates
function updateProgressBar(elementId, progress) {
    const progressBar = document.getElementById(elementId);
    if (progressBar) {
        const progressText = progressBar.querySelector('.progress-bar');
        if (progressText) {
            progressText.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;
        }
        progressBar.style.display = 'block';
    }
}

// Status display updates
function updateStatusDisplay(elementId, data) {
    const statusDiv = document.getElementById(elementId);
    if (statusDiv) {
        const statusClass = `status-${data.status}`;
        statusDiv.innerHTML = `
            <p><strong>Status:</strong> <span class="${statusClass}">${data.status}</span></p>
            <p><strong>Message:</strong> ${data.message}</p>
            <p><strong>Progress:</strong> ${data.progress}%</p>
        `;
    }
}

// Log message helper
function logMessage(logElementId, message, type = 'info') {
    const logDiv = document.getElementById(logElementId);
    if (logDiv) {
        const timestamp = new Date().toLocaleTimeString();
        const messageElement = document.createElement('p');
        messageElement.className = 'mb-1';
        
        // Add color based on type
        if (type === 'error') {
            messageElement.style.color = '#dc3545';
        } else if (type === 'success') {
            messageElement.style.color = '#28a745';
        } else if (type === 'warning') {
            messageElement.style.color = '#ffc107';
        }
        
        messageElement.textContent = `[${timestamp}] ${message}`;
        logDiv.appendChild(messageElement);
        logDiv.scrollTop = logDiv.scrollHeight;
    }
}

// Download helper
function downloadFile(filename) {
    window.location.href = `/download/${filename}`;
}

// Cleanup helper
function cleanupTask(taskId) {
    // Could implement server-side cleanup here
    console.log(`Cleaning up task ${taskId}`);
}

// Error handling wrapper
function withErrorHandling(asyncFn) {
    return async function(...args) {
        try {
            return await asyncFn.apply(this, args);
        } catch (error) {
            showError(error.message);
            throw error;
        }
    };
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle helper
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Local storage helpers
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Storage set error:', error);
        }
    },
    
    get(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('Storage get error:', error);
            return null;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Storage remove error:', error);
        }
    },
    
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Storage clear error:', error);
        }
    }
};

// Session storage helpers
const SessionStorage = {
    set(key, value) {
        try {
            sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Session storage set error:', error);
        }
    },
    
    get(key) {
        try {
            const item = sessionStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('Session storage get error:', error);
            return null;
        }
    },
    
    remove(key) {
        try {
            sessionStorage.removeItem(key);
        } catch (error) {
            console.error('Session storage remove error:', error);
        }
    }
};

// URL parameter helpers
const UrlParams = {
    get(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    },
    
    getAll() {
        const urlParams = new URLSearchParams(window.location.search);
        const params = {};
        for (const [key, value] of urlParams) {
            params[key] = value;
        }
        return params;
    },
    
    set(name, value) {
        const url = new URL(window.location);
        url.searchParams.set(name, value);
        window.history.replaceState({}, '', url);
    },
    
    remove(name) {
        const url = new URL(window.location);
        url.searchParams.delete(name);
        window.history.replaceState({}, '', url);
    }
};

// Export for use in other files (if using modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AppState,
        apiRequest,
        uploadFile,
        pollStatus,
        formatFileSize,
        generateUniqueId,
        showError,
        showSuccess,
        validateRequired,
        updateProgressBar,
        updateStatusDisplay,
        logMessage,
        downloadFile,
        cleanupTask,
        withErrorHandling,
        debounce,
        throttle,
        Storage,
        SessionStorage,
        UrlParams
    };
}