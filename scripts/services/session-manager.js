/**
 * Session Manager for Gold Box Backend
 * Handles all session lifecycle operations including initialization, refresh, and critical state management
 * Extracted from ConnectionManager for better separation of concerns
 */

/**
 * Session States
 */
const SessionState = {
  INVALID: 'invalid',
  VALID: 'valid',
  WARNING: 'warning',
  CRITICAL: 'critical',
  EXPIRED: 'expired'
};

/**
 * Session Manager Class
 */
class SessionManager {
  constructor(config = {}) {
    // Singleton pattern
    if (SessionManager.instance) {
      return SessionManager.instance;
    }
    
    SessionManager.instance = this;
    
    // Session state
    this.sessionId = null;
    this.sessionExpiry = null;
    
    // Refresh state
    this.refreshState = {
      isRefreshing: false,
      consecutiveFailures: 0,
      lastRefreshAttempt: null,
      circuitBreakerOpen: false,
      circuitBreakerResetTime: null
    };
    
    // Enhanced refresh configuration
    this.refreshConfig = {
      maxRetries: config.maxRetries || 3,
      baseDelay: config.baseDelay || 1000,        // 1 second base delay
      maxDelay: config.maxDelay || 30000,        // 30 second max delay
      criticalThreshold: config.criticalThreshold || 60000, // 1 minute critical threshold
      warningThreshold: config.warningThreshold || 300000, // 5 minute warning threshold
      minRefreshBuffer: config.minRefreshBuffer || 300000,  // 5 minute minimum buffer
      healthCheckInterval: config.healthCheckInterval || 30000, // 30 second health check
      circuitBreakerResetDelay: config.circuitBreakerResetDelay || 300000 // 5 minute circuit breaker reset
    };
    
    // Timing
    this.sessionRefreshInterval = null;
    this.sessionHealthInterval = null;
    this.visibilityChangeHandler = null;
    
    // Callbacks for external integration
    this.callbacks = {
      onSessionCreated: null,
      onSessionExtended: null,
      onSessionRefreshed: null,
      onCriticalState: null,
      onSessionExpired: null
    };
    
    console.log('SessionManager: Initialized singleton instance');
  }

  /**
   * Set callbacks for session events
   * @param {Object} callbacks - Callback functions
   */
  setCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Initialize a new session with backend
   * @param {string} baseUrl - Backend base URL
   * @param {Object} options - Initialization options
   * @returns {Promise<boolean>} - True if successful
   */
  async initializeSession(baseUrl, options = {}) {
    try {
      console.log('SessionManager: Initializing session...');
      
      const requestBody = {
        ...options
      };

      // Add session extension if requested
      if (options.extendExisting && this.sessionId) {
        requestBody.extend_existing = true;
        requestBody.session_id = this.sessionId;
      }
      
      const response = await fetch(`${baseUrl}/api/session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Handle session extension response
        if (data.was_extended) {
          this.sessionExpiry = new Date(data.expires_at);
          console.log('SessionManager: Session extended successfully');
          console.log('SessionManager: New expiry:', this.sessionExpiry);
          
          if (this.callbacks.onSessionExtended) {
            this.callbacks.onSessionExtended(data);
          }
        } else {
          // New session created
          this.sessionId = data.session_id;
          this.sessionExpiry = new Date(data.expires_at);
          
          console.log('SessionManager: Session initialized successfully');
          console.log('SessionManager: Session ID:', this.sessionId);
          console.log('SessionManager: Session expires:', this.sessionExpiry);
          
          if (this.callbacks.onSessionCreated) {
            this.callbacks.onSessionCreated(data);
          }
        }
        
        // Reset refresh state on successful initialization
        this.refreshState = {
          isRefreshing: false,
          consecutiveFailures: 0,
          lastRefreshAttempt: null,
          circuitBreakerOpen: false,
          circuitBreakerResetTime: null
        };
        
        return true;
      } else {
        console.error('SessionManager: Failed to initialize session:', response.status, response.statusText);
        return false;
      }
    } catch (error) {
      console.error('SessionManager: Error initializing session:', error);
      return false;
    }
  }

  /**
   * Try to extend existing session instead of creating new one
   * @param {string} baseUrl - Backend base URL
   * @returns {Promise<boolean>} - True if successful
   */
  async extendExistingSession(baseUrl) {
    if (!this.sessionId || !this.isSessionValid()) {
      return false;
    }

    try {
      console.log('SessionManager: Attempting to extend existing session...');
      
      return await this.initializeSession(baseUrl, {
        extendExisting: true
      });
      
    } catch (error) {
      console.error('SessionManager: Error extending session:', error);
      return false;
    }
  }

  /**
   * Refresh session token with retry logic and exponential backoff
   * @param {string} baseUrl - Backend base URL
   * @returns {Promise<boolean>} - True if successful
   */
  async refreshSession(baseUrl) {
    // Check if already refreshing to prevent concurrent refreshes
    if (this.refreshState.isRefreshing) {
      console.log('SessionManager: Refresh already in progress, skipping...');
      return false;
    }

    // Check circuit breaker
    if (this.refreshState.circuitBreakerOpen) {
      const now = Date.now();
      if (now < this.refreshState.circuitBreakerResetTime) {
        console.log('SessionManager: Circuit breaker is open, skipping refresh');
        return false;
      } else {
        console.log('SessionManager: Circuit breaker reset, allowing refresh');
        this.refreshState.circuitBreakerOpen = false;
        this.refreshState.consecutiveFailures = 0;
      }
    }

    this.refreshState.isRefreshing = true;
    this.refreshState.lastRefreshAttempt = Date.now();

    try {
      // Try to extend existing session first
      const wasExtended = await this.extendExistingSession(baseUrl);
      
      if (wasExtended) {
        console.log('SessionManager: Session extended successfully');
        this.refreshState.consecutiveFailures = 0;
        this.scheduleNextRefresh();
        
        if (this.callbacks.onSessionExtended) {
          this.callbacks.onSessionExtended({ wasExtended: true });
        }
        
        return true;
      }

      // If extension failed, try refresh with retry logic
      const refreshed = await this.refreshSessionWithRetry(baseUrl);
      
      if (refreshed) {
        this.refreshState.consecutiveFailures = 0;
        this.scheduleNextRefresh();
        
        if (this.callbacks.onSessionRefreshed) {
          this.callbacks.onSessionRefreshed({ wasRefreshed: true });
        }
        
        return true;
      }

      // All refresh attempts failed
      this.refreshState.consecutiveFailures++;
      console.error(`SessionManager: Session refresh failed after ${this.refreshState.consecutiveFailures} consecutive failures`);

      // Check for critical situation
      if (this.isSessionInCriticalState()) {
        this.handleCriticalState();
      }

      // Open circuit breaker if too many failures
      if (this.refreshState.consecutiveFailures >= this.refreshConfig.maxRetries) {
        this.refreshState.circuitBreakerOpen = true;
        this.refreshState.circuitBreakerResetTime = Date.now() + this.refreshConfig.circuitBreakerResetDelay;
        console.warn('SessionManager: Circuit breaker opened due to repeated failures');
      }

      return false;

    } finally {
      this.refreshState.isRefreshing = false;
    }
  }

  /**
   * Refresh session with exponential backoff retry logic
   * @param {string} baseUrl - Backend base URL
   * @returns {Promise<boolean>} - True if successful
   */
  async refreshSessionWithRetry(baseUrl) {
    for (let attempt = 0; attempt < this.refreshConfig.maxRetries; attempt++) {
      try {
        console.log(`SessionManager: Refresh attempt ${attempt + 1}/${this.refreshConfig.maxRetries}`);
        
        const response = await fetch(`${baseUrl}/api/session/init`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          this.sessionId = data.session_id;
          this.sessionExpiry = new Date(data.expires_at);
          
          console.log('SessionManager: Session refreshed successfully');
          console.log('SessionManager: New Session ID:', this.sessionId);
          console.log('SessionManager: New expiry:', this.sessionExpiry);
          
          return true;
        } else {
          console.error(`SessionManager: Refresh attempt ${attempt + 1} failed:`, response.status, response.statusText);
        }
      } catch (error) {
        console.error(`SessionManager: Refresh attempt ${attempt + 1} error:`, error);
      }

      // If not last attempt, wait with exponential backoff
      if (attempt < this.refreshConfig.maxRetries - 1) {
        const delay = this.calculateBackoffDelay(attempt);
        console.log(`SessionManager: Waiting ${delay}ms before retry...`);
        await this.sleep(delay);
      }
    }

    return false;
  }

  /**
   * Calculate exponential backoff delay with jitter
   * @param {number} attempt - Current attempt number (0-based)
   * @returns {number} - Delay in milliseconds
   */
  calculateBackoffDelay(attempt) {
    const exponentialDelay = this.refreshConfig.baseDelay * Math.pow(2, attempt);
    const jitter = Math.random() * 0.1 * exponentialDelay; // Add 10% jitter
    const totalDelay = exponentialDelay + jitter;
    return Math.min(totalDelay, this.refreshConfig.maxDelay);
  }

  /**
   * Sleep helper function
   * @param {number} ms - Milliseconds to sleep
   * @returns {Promise} - Promise that resolves after ms milliseconds
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Check if session is valid
   * @returns {boolean} - True if session is valid
   */
  isSessionValid() {
    return this.sessionId && this.sessionExpiry && Date.now() < this.sessionExpiry.getTime();
  }

  /**
   * Get current session state
   * @returns {string} - Current session state
   */
  getSessionState() {
    if (!this.sessionId || !this.sessionExpiry) {
      return SessionState.INVALID;
    }
    
    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;
    
    if (timeToExpiry <= 0) {
      return SessionState.EXPIRED;
    } else if (timeToExpiry < this.refreshConfig.criticalThreshold) {
      return SessionState.CRITICAL;
    } else if (timeToExpiry < this.refreshConfig.warningThreshold) {
      return SessionState.WARNING;
    } else {
      return SessionState.VALID;
    }
  }

  /**
   * Check if session is in critical state (expiring soon)
   * @returns {boolean} - True if session expires in less than critical threshold
   */
  isSessionInCriticalState() {
    return this.getSessionState() === SessionState.CRITICAL;
  }

  /**
   * Handle critical session state with user notification
   */
  handleCriticalState() {
    console.error('SessionManager: Session in critical state - showing user warning');
    
    // Call external callback if available
    if (this.callbacks.onCriticalState) {
      this.callbacks.onCriticalState({
        sessionId: this.sessionId,
        sessionExpiry: this.sessionExpiry,
        timeToExpiry: this.sessionExpiry.getTime() - Date.now()
      });
    }

    // Try to show user notification
    if (typeof ui !== 'undefined' && ui.notifications) {
      ui.notifications.error('WARNING: Session expiring soon! Server connection may be unstable. Please refresh page.', {
        permanent: true
      });
    }

    // Also show in chat if available
    if (typeof ChatMessage !== 'undefined') {
      const messageContent = `
        <div class="gold-box-critical-warning">
          <div class="gold-box-header">
            <strong>The Gold Box - Critical Session Warning</strong>
          </div>
          <div class="gold-box-content">
            <p><strong>WARNING: Session expiring soon!</strong></p>
            <p>The backend connection is unstable and may fail soon. Please refresh the page to restore connection.</p>
            <p><em>If this persists, the backend server may be down or experiencing issues.</em></p>
          </div>
        </div>
      `;
      
      ChatMessage.create({
        user: game?.user?.id || 'system',
        content: messageContent,
        speaker: {
          alias: 'The Gold Box System'
        }
      });
    }
  }

  /**
   * Schedule next refresh using smart timing
   */
  scheduleNextRefresh() {
    // Clear any existing timer
    if (this.sessionRefreshInterval) {
      clearTimeout(this.sessionRefreshInterval);
      this.sessionRefreshInterval = null;
    }

    if (!this.sessionExpiry) {
      console.log('SessionManager: No session expiry, cannot schedule refresh');
      return;
    }

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If already expired, refresh immediately
    if (timeToExpiry <= 0) {
      console.log('SessionManager: Session expired, refresh needed');
      if (this.callbacks.onSessionExpired) {
        this.callbacks.onSessionExpired();
      }
      return;
    }

    let refreshDelay;

    // If less than minimum buffer, refresh immediately
    if (timeToExpiry < this.refreshConfig.minRefreshBuffer) {
      refreshDelay = 1000; // 1 second
      console.log('SessionManager: Session expires soon, refresh needed immediately');
    }
    // If less than warning threshold, refresh more frequently
    else if (timeToExpiry < this.refreshConfig.warningThreshold) {
      refreshDelay = Math.max(30000, timeToExpiry - this.refreshConfig.criticalThreshold); // Every 30 seconds or critical threshold
      console.log('SessionManager: Session in warning zone, scheduling frequent refresh');
    }
    // Normal case: refresh 5 minutes before expiry
    else {
      refreshDelay = timeToExpiry - this.refreshConfig.minRefreshBuffer;
      console.log(`SessionManager: Scheduling normal refresh in ${refreshDelay / 1000} seconds`);
    }

    this.sessionRefreshInterval = setTimeout(() => {
      if (this.callbacks.onSessionExpired) {
        this.callbacks.onSessionExpired();
      }
    }, refreshDelay);
  }

  /**
   * Setup visibility change handler to handle tab background/foreground
   */
  setupVisibilityChangeHandler() {
    // Remove existing listener if any
    if (this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    }

    this.visibilityChangeHandler = () => {
      if (document.hidden) {
        console.log('SessionManager: Tab became hidden, adjusting refresh behavior');
        // When tab is hidden, be more conservative with refreshes
        this.adjustRefreshForBackground();
      } else {
        console.log('SessionManager: Tab became visible, checking session health');
        // When tab becomes visible, immediately check session health
        this.performImmediateHealthCheck();
      }
    };

    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    console.log('SessionManager: Visibility change handler setup complete');
  }

  /**
   * Perform immediate health check when tab becomes visible
   */
  async performImmediateHealthCheck(baseUrl) {
    if (!this.sessionId || !this.sessionExpiry) return;

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If session is expired, trigger expired callback
    if (timeToExpiry <= 0) {
      console.log('SessionManager: Tab visible with expired session, triggering refresh');
      if (this.callbacks.onSessionExpired) {
        this.callbacks.onSessionExpired();
      }
      return;
    }

    // If session is in warning zone, test connection
    if (timeToExpiry < this.refreshConfig.warningThreshold) {
      try {
        const testResult = await this.testConnection(baseUrl);
        if (!testResult.success) {
          console.warn('SessionManager: Connection test failed on tab visibility, triggering refresh');
          if (this.callbacks.onSessionExpired) {
            this.callbacks.onSessionExpired();
          }
        } else {
          console.log('SessionManager: Connection test passed on tab visibility');
        }
      } catch (error) {
        console.error('SessionManager: Error testing connection on tab visibility:', error);
        if (this.callbacks.onSessionExpired) {
          this.callbacks.onSessionExpired();
        }
      }
    }
  }

  /**
   * Adjust refresh behavior for background tab
   */
  adjustRefreshForBackground() {
    // Implement more conservative refresh behavior when tab is hidden
    console.log('SessionManager: Adjusting refresh for background tab');
    // This could involve longer intervals or pausing certain refreshes
  }

  /**
   * Start health monitoring for session
   */
  startHealthMonitoring(baseUrl) {
    // Clear existing health check
    if (this.sessionHealthInterval) {
      clearInterval(this.sessionHealthInterval);
      this.sessionHealthInterval = null;
    }

    // Start periodic health checks
    this.sessionHealthInterval = setInterval(() => {
      this.performHealthCheck(baseUrl);
    }, this.refreshConfig.healthCheckInterval);

    console.log('SessionManager: Started session health monitoring');
  }

  /**
   * Perform health check on session
   */
  async performHealthCheck(baseUrl) {
    if (!this.sessionId || !this.sessionExpiry) {
      return;
    }

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If session is expired, try to refresh
    if (timeToExpiry <= 0) {
      console.log('SessionManager: Health check detected expired session, triggering refresh');
      if (this.callbacks.onSessionExpired) {
        this.callbacks.onSessionExpired();
      }
      return;
    }

    // If session is in warning zone, be more aggressive
    if (timeToExpiry < this.refreshConfig.warningThreshold) {
      console.log('SessionManager: Health check detected session in warning zone');
      
      // Test connection to backend
      try {
        const testResult = await this.testConnection(baseUrl);
        if (!testResult.success) {
          console.warn('SessionManager: Health check failed, triggering refresh');
          if (this.callbacks.onSessionExpired) {
            this.callbacks.onSessionExpired();
          }
        }
      } catch (error) {
        console.error('SessionManager: Health check error:', error);
      }
    }
  }

  /**
   * Test backend connection
   * @param {string} baseUrl - Backend base URL
   * @returns {Promise<Object>} - Connection test result
   */
  async testConnection(baseUrl) {
    try {
      const response = await fetch(`${baseUrl}/api/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return {
          success: true,
          data: data
        };
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get session information
   * @returns {Object} - Session information
   */
  getSessionInfo() {
    return {
      sessionId: this.sessionId,
      sessionExpiry: this.sessionExpiry,
      sessionState: this.getSessionState(),
      isSessionValid: this.isSessionValid(),
      isSessionInCriticalState: this.isSessionInCriticalState(),
      timeToExpiry: this.sessionExpiry ? this.sessionExpiry.getTime() - Date.now() : null,
      refreshState: { ...this.refreshState }
    };
  }

  /**
   * Get session ID for external use
   * @returns {string|null} - Current session ID
   */
  getSessionId() {
    return this.sessionId;
  }

  /**
   * Get session expiry for external use
   * @returns {Date|null} - Current session expiry
   */
  getSessionExpiry() {
    return this.sessionExpiry;
  }

  /**
   * Get refresh state for external use
   * @returns {Object} - Current refresh state
   */
  getRefreshState() {
    return { ...this.refreshState };
  }

  /**
   * Clear session data and reset state
   */
  clearSession() {
    console.log('SessionManager: Clearing session data');
    
    // Clear timers
    if (this.sessionRefreshInterval) {
      clearTimeout(this.sessionRefreshInterval);
      this.sessionRefreshInterval = null;
    }
    
    if (this.sessionHealthInterval) {
      clearInterval(this.sessionHealthInterval);
      this.sessionHealthInterval = null;
    }
    
    // Remove visibility change handler
    if (this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
      this.visibilityChangeHandler = null;
    }
    
    // Clear session data
    this.sessionId = null;
    this.sessionExpiry = null;
    
    // Reset refresh state
    this.refreshState = {
      isRefreshing: false,
      consecutiveFailures: 0,
      lastRefreshAttempt: null,
      circuitBreakerOpen: false,
      circuitBreakerResetTime: null
    };
    
    console.log('SessionManager: Session cleared successfully');
  }
}

// Export for global access
window.SessionManager = SessionManager;
window.SessionState = SessionState;
