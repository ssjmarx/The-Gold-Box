/**
 * AI Session Manager for Gold Box Backend
 * Handles AI session lifecycle and persistence across multiple AI calls
 */

/**
 * AI Session Manager Class
 */
class AISessionManager {
  constructor(config = {}) {
    // Singleton pattern
    if (AISessionManager.instance) {
      return AISessionManager.instance;
    }
    
    AISessionManager.instance = this;
    
    // Session state
    this.sessionId = null;
    this.lastUsed = null;
    
    // Configuration
    this.config = {
      baseUrl: config.baseUrl || 'http://localhost:5000',
      sessionTimeout: config.sessionTimeout || 3600000, // 1 hour
      autoInit: config.autoInit !== false // Default to true
    };
    
    // Load session from storage
    this.loadSessionFromStorage();
    
    console.log('AISessionManager: Initialized singleton instance');
  }

  /**
   * Load session from localStorage
   */
  loadSessionFromStorage() {
    try {
      const stored = localStorage.getItem('goldbox_ai_session');
      if (stored) {
        const sessionData = JSON.parse(stored);
        
        // Check if session is still valid
        if (sessionData.sessionId && sessionData.lastUsed) {
          const age = Date.now() - sessionData.lastUsed;
          if (age < this.config.sessionTimeout) {
            this.sessionId = sessionData.sessionId;
            this.lastUsed = sessionData.lastUsed;
            console.log('AISessionManager: Restored session from storage:', this.sessionId);
            return;
          }
        }
      }
    } catch (error) {
      console.warn('AISessionManager: Failed to load session from storage:', error);
    }
    
    console.log('AISessionManager: No valid session in storage');
  }

  /**
   * Save session to localStorage
   */
  saveSessionToStorage() {
    try {
      if (this.sessionId) {
        const sessionData = {
          sessionId: this.sessionId,
          lastUsed: this.lastUsed || Date.now()
        };
        localStorage.setItem('goldbox_ai_session', JSON.stringify(sessionData));
        console.log('AISessionManager: Saved session to storage:', this.sessionId);
      }
    } catch (error) {
      console.warn('AISessionManager: Failed to save session to storage:', error);
    }
  }

  /**
   * Clear session from storage and memory
   */
  clearSession() {
    this.sessionId = null;
    this.lastUsed = null;
    try {
      localStorage.removeItem('goldbox_ai_session');
    } catch (error) {
      console.warn('AISessionManager: Failed to clear session from storage:', error);
    }
    console.log('AISessionManager: Session cleared');
  }

  /**
   * Initialize or continue AI session
   * @param {string} clientId - Client ID for session association
   * @param {Object} options - Additional options
   * @returns {Promise<string>} - Session ID
   */
  async initializeSession(clientId, options = {}) {
    try {
      const requestBody = {
        client_id: clientId,
        session_id: this.sessionId, // Pass existing session ID if available
        force_new: options.forceNew || false
      };

      const response = await fetch(`${this.config.baseUrl}/api/ai_session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Update session state
        this.sessionId = data.session_id;
        this.lastUsed = Date.now();
        
        // Save to storage
        this.saveSessionToStorage();
        
        console.log('AISessionManager: Session initialized/continued:', this.sessionId);
        
        if (data.is_new) {
          console.log('AISessionManager: New session created');
        } else {
          console.log('AISessionManager: Existing session continued');
        }
        
        return this.sessionId;
      } else {
        console.error('AISessionManager: Failed to initialize session:', response.status, response.statusText);
        throw new Error(`Session initialization failed: ${response.status}`);
      }
    } catch (error) {
      console.error('AISessionManager: Error initializing session:', error);
      throw error;
    }
  }

  /**
   * Force full context on next AI call
   */
  async forceFullContext() {
    if (!this.sessionId) {
      console.warn('AISessionManager: No session to force full context for');
      return false;
    }

    try {
      const response = await fetch(`${this.config.baseUrl}/api/ai_session/clear/${this.sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        console.log('AISessionManager: Forced full context for session:', this.sessionId);
        return true;
      } else {
        console.error('AISessionManager: Failed to force full context:', response.status, response.statusText);
        return false;
      }
    } catch (error) {
      console.error('AISessionManager: Error forcing full context:', error);
      return false;
    }
  }

  /**
   * Get session status
   */
  async getSessionStatus() {
    if (!this.sessionId) {
      return { hasSession: false };
    }

    try {
      const response = await fetch(`${this.config.baseUrl}/api/ai_session/status/${this.sessionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return {
          hasSession: true,
          ...data
        };
      } else {
        console.warn('AISessionManager: Session not found on server, clearing local session');
        this.clearSession();
        return { hasSession: false };
      }
    } catch (error) {
      console.error('AISessionManager: Error getting session status:', error);
      return { hasSession: false, error: error.message };
    }
  }

  /**
   * Get current session ID
   */
  getSessionId() {
    return this.sessionId;
  }

  /**
   * Check if session exists and is potentially valid
   */
  hasValidSession() {
    if (!this.sessionId || !this.lastUsed) {
      return false;
    }
    
    const age = Date.now() - this.lastUsed;
    return age < this.config.sessionTimeout;
  }

  /**
   * Update last used time
   */
  updateLastUsed() {
    this.lastUsed = Date.now();
    this.saveSessionToStorage();
  }

  /**
   * Get session info
   */
  getSessionInfo() {
    return {
      sessionId: this.sessionId,
      lastUsed: this.lastUsed,
      hasSession: this.hasValidSession(),
      age: this.lastUsed ? Date.now() - this.lastUsed : null
    };
  }

  /**
   * Create new session (force new)
   */
  async createNewSession(clientId) {
    return await this.initializeSession(clientId, { forceNew: true });
  }

  /**
   * Continue existing session or create new one
   */
  async continueOrCreateSession(clientId) {
    return await this.initializeSession(clientId, { forceNew: false });
  }
}

// Export for global access
window.AISessionManager = AISessionManager;

console.log('AI Session Manager module loaded');
