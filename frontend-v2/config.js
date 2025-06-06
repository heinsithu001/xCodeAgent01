// Frontend Configuration
// Automatically detects environment and sets appropriate API base URL

function getApiBaseUrl() {
    // Check if we're in development or production
    const hostname = window.location.hostname;
    const port = window.location.port;
    const protocol = window.location.protocol;
    
    console.log('Detecting environment:', { hostname, port, protocol });
    
    // If running on localhost, use local backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return `http://localhost:12000`;
    }
    
    // If running in production runtime environment
    if (hostname.includes('prod-runtime') || hostname.includes('all-hands.dev')) {
        // Use the same hostname with the correct port
        return `https://${hostname}`;
    }
    
    // If running in Docker or other production
    if (hostname.includes('docker')) {
        return `http://${hostname}:12000`;
    }
    
    // Default fallback
    return 'http://localhost:12000';
}

// Export configuration
const apiBaseUrl = getApiBaseUrl();
window.APP_CONFIG = {
    API_BASE_URL: apiBaseUrl,
    WEBSOCKET_URL: apiBaseUrl.replace('http', 'ws') + '/ws',
    VLLM_URL: 'http://localhost:8000',
    DEBUG: window.location.hostname === 'localhost'
};

// Make API_BASE_URL globally available
window.API_BASE_URL = window.APP_CONFIG.API_BASE_URL;

console.log('Frontend Config:', window.APP_CONFIG);