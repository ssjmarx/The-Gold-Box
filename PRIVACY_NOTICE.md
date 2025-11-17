# Privacy Notice for The Gold Box

## 🔒 Data Collection and Usage

### **What Data We Collect**

#### **API Keys** 
- **Purpose**: Authenticate with external AI services (OpenAI, NovelAI, etc.)
- **Storage**: Stored in environment variables only (not in code)
- **Transmission**: Sent securely to AI service providers for processing
- **Logging**: API key validation status logged (success/failure) with client IP
- **Retention**: Not stored permanently - only used for session authentication

#### **Request Logs**
- **Content**: API request metadata (timestamps, endpoints, validation results)
- **Personal Data**: Client IP addresses, request timing, error status
- **AI Prompts**: NOT logged in production mode (only length/status for monitoring)
- **Storage**: Local log files (`goldbox.log`) on your server
- **Retention**: Logs persist until manually deleted by server administrator

#### **System Information**
- **Content**: Server status, health metrics, security configuration
- **Purpose**: System monitoring and troubleshooting
- **Storage**: Local files only, never transmitted externally

### **How We Use Your Data**

1. **API Keys**: 
   - Authenticate requests to AI service providers
   - Generate responses to your prompts
   - Validate key format and permissions

2. **Request Logs**:
   - Monitor server performance and security
   - Debug connection issues
   - Track abuse attempts

3. **System Data**:
   - Provide health status via `/api/health` endpoint
   - Display configuration via `/api/info` endpoint

### **Data We DON'T Collect**

- ❌ **AI Prompt Content**: Your actual prompts and AI responses are NOT logged in production
- ❌ **Foundry VTT Data**: Game content, characters, scenes, etc.
- ❌ **Personal Information**: Names, emails, personal details
- ❌ **Browser Data**: Cookies, localStorage, session data
- ❌ **Analytics**: User behavior tracking, usage patterns

### **🚨 Security & Privacy Risks**

#### **Running This Server**
- **Exposure**: Server accessible from network (if configured with CORS)
- **API Keys**: Must be kept secure and never shared
- **Logs**: Contain IP addresses that could identify users
- **Network Traffic**: AI service providers can see your IP and requests

#### **Mitigations**
- ✅ **Local Processing**: Prompts not logged on server side
- ✅ **Secure Defaults**: Development mode restricted to localhost
- ✅ **Rate Limiting**: Prevents abuse and data harvesting
- ✅ **Input Validation**: Protects against injection attacks
- ✅ **No Analytics**: No user tracking or behavior analysis

### **🔐 API Key Security**

#### **Best Practices**
1. **Environment Variables**: Store API keys in `.env` files, not in code
2. **Minimal Permissions**: Use API keys with least required permissions
3. **Regular Rotation**: Change API keys periodically
4. **Monitoring**: Check API service usage for unusual activity
5. **Never Share**: Don't commit API keys to version control

#### **Warning**
- API keys allow access to paid AI services
- Compromised keys could result in unauthorized charges
- Lost keys should be revoked immediately through your AI provider

### **🌐 Network Exposure**

#### **Development Mode** (Default)
- **Binding**: `localhost` only (127.0.0.1)
- **Access**: Only from your computer
- **Risk**: Minimal - local network access only

#### **Production Mode** (Custom CORS)
- **Binding**: All network interfaces (`0.0.0.0`)
- **Access**: Anyone who can reach your server
- **Risk**: Higher - requires proper security configuration
- **Mitigation**: Configure specific CORS origins only

### **📋 Your Rights and Choices**

#### **Data Access**
- You can request deletion of request logs by contacting server administrator
- You can view all data collected via `/api/info` endpoint
- You can disable logging by setting `LOG_LEVEL=ERROR`

#### **Control**
- **Opt-out**: Don't use the service if you disagree with data handling
- **Local Only**: Run in development mode for local processing only
- **Self-Host**: Host your own backend for full control

### **⚖️ Legal Compliance**

- **No Personal Data**: We don't collect PII beyond technical connection data
- **Minimal Collection**: Only what's necessary for service operation
- **Transparent**: All data practices documented here
- **Rights**: You maintain control over your AI service accounts

### **📞 Questions and Concerns**

For privacy-related questions:
1. Review this privacy notice
2. Check the security configuration in `/api/info` endpoint
3. Examine your local log files
4. Contact the project maintainer through GitHub issues

---

## **🔒 Privacy Summary**

**The Gold Box is designed with privacy-first principles:**
- **Minimal Data Collection**: Only essential operational data
- **No Content Logging**: Your prompts and responses remain private
- **Local Control**: You control server exposure and configuration
- **Transparent Practices**: All data handling clearly documented
- **Security Focused**: Protection against unauthorized access and abuse

**Use this service with confidence that your privacy is respected and protected.** 🛡️

---

*This privacy notice applies to The Gold Box backend server version 0.1.0 and later. Last updated: November 2025*
