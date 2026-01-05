# Feature: Local Model Support and LiteLLM Update

## Overview
This feature adds comprehensive support for local AI providers and updates The Gold Box's LiteLLM provider configuration to match the latest available providers. Users can configure local models directly in Foundry VTT settings without needing to manage API keys in the key manager.

**Research Summary (2026-01-03):**
- **Total LiteLLM Providers:** 103
- **Local Providers Verified:** 6 (lemonade, llamafile, lm_studio, ollama, vllm, xinference)
- **Remote Providers:** 97
- **Current litellm_providers.json:** 73 providers (18 outdated, 48 missing)
- **Model Validation Impact:** 5 of 9 test models fail with current regex

## Problems Identified

### 1. Model Name Validation Too Restrictive
**File:** `backend/shared/providers/custom_provider_wizard.py` (line 163)

**Issue:** Model name validation regex only allows: `[a-zA-Z0-9._-]`

**Impact:** 
- Rejects Ollama model names with colons: `qwen3:14b`, `llama3.2:3b`, `gemma3:latest`
- Forces users to modify model names (e.g., `qwen3-14b`), which breaks actual model identification

**Example Error:**
```
ERROR: Invalid model names: qwen3:14b, llama3.2:3b
Model names can only contain letters, numbers, dots, hyphens, and underscores.
```

### 2. Mandatory API Keys Block Local Providers
**File:** `backend/services/ai_services/ai_service.py` (lines 66-71)

**Issue:** System throws `APIKeyException` if no API key is configured, even for local providers like Ollama that don't require authentication.

**Impact:**
- Users must enter dummy API keys to satisfy validation
- Confusing UX for local provider setup
- Adds unnecessary friction

### 3. Outdated LiteLLM Provider List
**File:** `backend/shared/server_files/litellm_providers.json`

**Issue:** Current provider list has 73 providers but LiteLLM now supports 103.

**Outdated Providers (18 to remove):**
- Image resolution providers: `1024-x-1024`, `256-x-256`, `512-x-512`, `hd`, `high`, `low`, `max-x-max`, `medium`, `standard`
- Deprecated providers: `anyscale`, `dataforseo`, `exa_ai`, `firecrawl`, `google`, `google_pse`, `palm`, `parallel_ai`, `searxng`, `tavily`

**Missing Providers (48 to add):**
- New AI providers: `ai21`, `ai21_chat`, `aiohttp_openai`, `anthropic_text`, `auto_router`, `azure_text`, `baseten`, `bytez`, `clarifai`, `cohere_chat`, `cometapi`, `compactifai`, `custom`, `custom_openai`, `datarobot`, `dotprompt`, `empower`, `galadriel`, `github`, `github_copilot`, `hosted_vllm`, `huggingface`, `humanloop`, `infinity`, `jina_ai`, `langfuse`, `litellm_proxy`, `maritalk`, `milvus`, `nebius`, `nlp_cloud`, `novita`, `ollama_chat`, `oobabooga`, `openai_like`, `petals`, `pg_vector`, `predibase`, `sagemaker_chat`, `text-completion-openai`, `topaz`, `triton`, `vertex_ai_beta`, `volcengine`, `watsonx_text`
- Local providers: `llamafile`, `lm_studio`, `vllm`, `xinference`

## Proposed Solutions

### Solution 1: Expand Model Name Validation
**File:** `backend/shared/providers/custom_provider_wizard.py`

**Change:** Update regex pattern to allow colons and slashes
```python
# Current: r'^[a-zA-Z0-9._-]+$'
# Updated: r'^[a-zA-Z0-9._:/-]+$'  # Allow colons and forward slashes
```

**Rationale:** 
- Ollama uses `model:tag` format (e.g., `qwen3:14b`)
- Some providers use `org/model` format (e.g., `openrouter/anthropic/claude-3`)
- This is a safe expansion with no security implications

### Solution 2: Optional Authentication for Local Providers
**Files:** Multiple files require updates

**Workflow Change:**
User configures local model in Foundry VTT settings (provider + model) → Settings sent to backend → Backend recognizes provider doesn't require API key → Attempts to use model without API key → Either works or fails with descriptive error

**a. Add Provider Type Field to litellm_providers.json**

Keep existing structure but add `requires_auth` field:

```json
{
  "total_providers": 103,
  "providers": [
    "ollama",
    "vllm",
    "lm_studio",
    ...
  ],
  "provider_details": {
    "ollama": {
      "model_count": 0,
      "sample_models": [
        "qwen3:14b",
        "llama3.2:3b",
        "gemma3:latest"
      ],
      "requires_auth": false,
      "auth_type": "None",
      "provider_type": "local",
      "description": "Local Ollama instance - no API key required"
    },
    "openai": {
      "model_count": 3,
      "sample_models": [
        "openai/container",
        "openai/sora-2"
      ],
      "requires_auth": true,
      "auth_type": "Bearer Token",
      "provider_type": "remote",
      "description": "OpenAI API"
    }
  }
}
```

**b. Update ProviderManager**
**File:** `backend/services/system_services/provider_manager.py`

Add `requires_auth` and `provider_type` fields to provider configuration:
```python
self.default_providers[provider_slug] = {
    'slug': provider_slug,
    'name': provider_info.get('name', provider_slug.replace('_', ' ').title()),
    'description': provider_info.get('description', f'{model_count} models available'),
    'models': sample_models,
    'auth_type': provider_info.get('auth_type', 'Bearer Token'),
    'requires_auth': provider_info.get('requires_auth', True),  # Default: true
    'provider_type': provider_info.get('provider_type', 'remote'),  # Default: remote
    'base_url': provider_info.get('base_url', ''),
    'completion_endpoint': provider_info.get('completion_endpoint', '/v1/chat/completions'),
    'is_custom': False
}
```

**c. Update AI Service to Support Optional Authentication**
**File:** `backend/services/ai_services/ai_service.py`

Make API key check conditional:
```python
# Get provider configuration
provider = self.provider_manager.get_provider(provider_id)
if not provider:
    raise ProviderException(f'Provider "{provider_id}" not found')

# Only check for API key if provider requires authentication
if provider.get('requires_auth', True):
    api_key = key_manager.keys_data.get(provider_id)
    if not api_key:
        raise APIKeyException(f"API key not configured for provider '{provider_id}' in key manager")
else:
    api_key = None  # No authentication needed
```

**d. Update Custom Provider Wizard**
**File:** `backend/shared/providers/custom_provider_wizard.py`

Add "None (Local Provider)" authentication option and provider type selection:
```python
def _configure_authentication(self):
    from ui.cli_manager import CLIManager
    
    while True:
        print("\nAuthentication Type:")
        print("1. Bearer Token (Standard JWT/API token)")
        print("2. API Key in Header (Custom header name)")
        print("3. API Key in Query Parameter")
        print("4. Basic Authentication (Username:Password)")
        print("5. Custom Header (Specify header name and value)")
        print("6. None (Local Provider - No Authentication)")
        
        auth_choice = CLIManager.get_menu_choice([1, 2, 3, 4, 5, 6], "Choose auth type")
        
        if auth_choice == 6:
            return {
                'auth_type': 'None',
                'requires_auth': False
            }
        # ... existing options ...
```

Add provider type selection:
```python
def _configure_provider_type(self):
    """Configure provider type (local vs remote)"""
    from ui.cli_manager import CLIManager
    
    print("\nProvider Type:")
    print("1. Remote Provider (Cloud API - requires authentication)")
    print("2. Local Provider (Self-hosted - no authentication required)")
    
    type_choice = CLIManager.get_menu_choice([1, 2], "Choose provider type")
    
    if type_choice == 2:
        return 'local'
    else:
        return 'remote'
```

**e. Update Key Manager to Skip Local Providers**
**File:** `backend/services/system_services/key_manager.py`

Skip API key entry for providers without auth requirement:
```python
def add_key_flow(self, provider_slug: str = None):
    """Enhanced key addition with provider type awareness"""
    self.display_header()
    
    if not provider_slug:
        # Display providers and let user choose
        provider_list = self.provider_manager.get_provider_list()
        
        print("\nAvailable Providers:")
        for provider in provider_list:
            provider_details = self.provider_manager.get_provider(provider['slug'])
            requires_auth = provider_details.get('requires_auth', True)
            
            if requires_auth:
                print(f"  - {provider['name']} (API Key Required)")
            else:
                print(f"  - {provider['name']} (Local - No API Key Needed)")
        
        provider_slug = input("\nEnter provider name: ").strip()
    
    # Get provider details
    provider = self.provider_manager.get_provider(provider_slug)
    if not provider:
        print(f"ERROR: Provider '{provider_slug}' not found")
        return False
    
    # Check if provider requires authentication
    if not provider.get('requires_auth', True):
        print(f"\n{provider['name']} is a LOCAL provider")
        print("Local providers do not require API keys.")
        confirm = input("Mark as configured and ready to use? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            # Store empty key to mark as configured
            self.key_storage.add_key(provider_slug, '')
            print(f"\n{provider['name']} configured successfully")
        return True
    
    # Remote provider - requires API key
    print(f"\n{provider['name']} is a REMOTE provider")
    print("API key required for authentication.")
    
    # ... existing key entry logic ...
```

### Solution 3: Foundry VTT Settings Integration
**Files to update:**
- `scripts/services/settings-manager.js` - Handle local provider settings
- `scripts/api/backend-communicator.js` - Send provider/model to backend
- `backend/api/session.py` - Accept provider/model from frontend
- `backend/services/ai_services/ai_service.py` - Use provider/model without API key if local

**Frontend Settings Structure:**
```javascript
// Foundry VTT settings for AI providers
const aiSettings = {
  generalProvider: "ollama",      // General chat provider
  generalModel: "qwen3:14b",      // General chat model
  tacticalProvider: "ollama",     // Tactical AI provider
  tacticalModel: "llama3.2:3b",   // Tactical AI model
  
  // Optional: Base URL for local providers
  providers: {
    ollama: {
      baseUrl: "http://localhost:11434"
    },
    vllm: {
      baseUrl: "http://localhost:8000/v1"
    }
  }
};

// Send to backend
sendToBackend('updateAIConfig', aiSettings);
```

**Backend API Endpoint:**
```python
@router.post("/session/configure-ai")
async def configure_ai(
    session_id: str,
    general_provider: str,
    general_model: str,
    tactical_provider: str = None,
    tactical_model: str = None,
    provider_configs: dict = None
):
    """
    Configure AI providers from Foundry VTT settings.
    
    Local providers (e.g., ollama, vllm) do not require API keys.
    The backend will attempt to use them directly.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Configure general provider
    general_provider_info = provider_manager.get_provider(general_provider)
    if not general_provider_info:
        raise HTTPException(status_code=400, detail=f"Provider '{general_provider}' not found")
    
    # Check if provider requires authentication
    if general_provider_info.get('requires_auth', True):
        api_key = key_manager.keys_data.get(general_provider)
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{general_provider}' requires API key. Please configure in key manager."
            )
    else:
        api_key = None
    
    # Store provider configuration
    session.ai_config = {
        'general': {
            'provider': general_provider,
            'model': general_model,
            'api_key': api_key  # None for local providers
        }
    }
    
    # Configure tactical provider (optional)
    if tactical_provider and tactical_model:
        tactical_provider_info = provider_manager.get_provider(tactical_provider)
        if not tactical_provider_info:
            raise HTTPException(status_code=400, detail=f"Provider '{tactical_provider}' not found")
        
        if tactical_provider_info.get('requires_auth', True):
            api_key = key_manager.keys_data.get(tactical_provider)
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider '{tactical_provider}' requires API key. Please configure in key manager."
                )
        else:
            api_key = None
        
        session.ai_config['tactical'] = {
            'provider': tactical_provider,
            'model': tactical_model,
            'api_key': api_key  # None for local providers
        }
    
    return {"status": "success", "message": "AI configuration updated"}
```

**Dual Model Support:**
- Users can configure different models for general chat and tactical AI
- Seamless switching between providers (local/local, local/remote, remote/remote)
- Each provider independently authenticated based on `requires_auth` flag

### Solution 4: Update LiteLLM Provider List
**File:** `backend/shared/server_files/litellm_providers.json`

**Actions:**
1. Remove 18 outdated providers
2. Add 48 missing providers
3. Add `requires_auth` and `provider_type` fields to all providers
4. Update sample models to include colon format for local providers

**Final Structure:**
```json
{
  "total_providers": 103,
  "providers": [
    "ai21",
    "ai21_chat",
    "aiohttp_openai",
    "anthropic",
    "anthropic_text",
    ...
    "ollama",
    "vllm",
    "lm_studio",
    "llamafile",
    "lemonade",
    "xinference",
    ...
  ],
  "provider_details": {
    "ai21": {
      "model_count": 0,
      "sample_models": [],
      "requires_auth": true,
      "auth_type": "Bearer Token",
      "provider_type": "remote",
      "description": "AI21 Labs API"
    },
    "ollama": {
      "model_count": 0,
      "sample_models": [
        "qwen3:14b",
        "llama3.2:3b",
        "gemma3:latest"
      ],
      "requires_auth": false,
      "auth_type": "None",
      "provider_type": "local",
      "description": "Local Ollama instance - no API key required",
      "default_base_url": "http://localhost:11434"
    },
    "vllm": {
      "model_count": 0,
      "sample_models": [],
      "requires_auth": false,
      "auth_type": "None",
      "provider_type": "local",
      "description": "vLLM OpenAI-compatible server",
      "default_base_url": "http://localhost:8000/v1"
    },
    ...
  }
}
```

## Implementation Plan

### Phase 1: Model Name Validation (Low Risk)
1. Update regex in `custom_provider_wizard.py` to `^[a-zA-Z0-9._:/-]+$`
2. Update validation error message to reflect new allowed characters
3. Test with various model name formats (colons, slashes, standard)

### Phase 2: Optional Authentication (Medium Risk)
1. Add `requires_auth` and `provider_type` fields to `litellm_providers.json`
2. Update `ProviderManager.load_default_providers()` to handle new fields
3. Update `CustomProviderWizard` to offer "None (Local Provider)" option
4. Update `AIService` to conditionally check for API keys
5. Update `KeyManager` to skip API key entry for local providers
6. Test with local Ollama instance (no API key)

### Phase 3: Foundry VTT Integration (Medium Risk)
1. Update `settings-manager.js` to handle provider/model configuration
2. Update `backend-communicator.js` to send AI config to backend
3. Add `/session/configure-ai` endpoint in `session.py`
4. Update `AIService` to accept provider/model from session config
5. Test dual model configuration (general + tactical)
6. Test seamless switching between providers

### Phase 4: Provider Configuration Updates (Low Risk)
1. Remove 18 outdated providers from `litellm_providers.json`
2. Add 48 missing providers with proper metadata
3. Add `requires_auth: false` to 6 local providers
4. Update sample models to include colon format
5. Verify all 103 providers load correctly

## Files to Modify

1. **backend/shared/providers/custom_provider_wizard.py**
   - Update model name validation regex (line 163)
   - Add "None (Local Provider)" auth option
   - Add provider type selection
   - Update validation error messages

2. **backend/shared/server_files/litellm_providers.json**
   - Remove 18 outdated providers
   - Add 48 missing providers
   - Add `requires_auth` field to all providers
   - Add `provider_type` field to all providers
   - Add `default_base_url` for local providers
   - Update sample models

3. **backend/services/system_services/provider_manager.py**
   - Add `requires_auth` and `provider_type` fields in `load_default_providers()`

4. **backend/services/ai_services/ai_service.py**
   - Make API key check conditional based on `requires_auth` flag
   - Support provider/model configuration from session
   - Handle both general and tactical AI configurations

5. **backend/services/system_services/key_manager.py**
   - Skip API key entry for providers without auth
   - Display provider type (local/remote) in UI
   - Allow empty API keys for local providers

6. **backend/api/session.py**
   - Add `/session/configure-ai` endpoint
   - Accept general and tactical provider/model configuration
   - Validate provider authentication requirements
   - Store configuration in session

7. **scripts/services/settings-manager.js**
   - Add provider/model configuration methods
   - Handle local vs remote provider differences
   - Support dual model configuration

8. **scripts/api/backend-communicator.js**
   - Send AI configuration to backend
   - Handle configuration success/error responses

## Testing Plan

### Test Case 1: Model Name Validation
- [ ] Enter model with colon: `qwen3:14b` → Should accept
- [ ] Enter model with slash: `openrouter/anthropic/claude-3` → Should accept
- [ ] Enter model with special chars: `model@name` → Should reject
- [ ] Enter empty model name → Should reject

### Test Case 2: Local Provider (No Auth)
- [ ] Select "ollama" provider in Foundry settings
- [ ] Enter model: `qwen3:14b`
- [ ] Configure base URL: `http://localhost:11434`
- [ ] Send to backend without API key
- [ ] Backend accepts configuration
- [ ] AI call succeeds without API key

### Test Case 3: Remote Provider (With Auth)
- [ ] Select "openai" provider in Foundry settings
- [ ] Enter model: `gpt-4`
- [ ] Send to backend
- [ ] Backend rejects (no API key)
- [ ] User configures API key in key manager
- [ ] Retry configuration succeeds

### Test Case 4: Dual Model Configuration
- [ ] Configure general: ollama/qwen3:14b
- [ ] Configure tactical: openai/gpt-4
- [ ] General chat uses ollama (no API key)
- [ ] Tactical AI uses openai (with API key)
- [ ] Seamless switching between providers works

### Test Case 5: Provider List Updates
- [ ] All 103 providers load correctly
- [ ] Local providers have `requires_auth: false`
- [ ] Remote providers have `requires_auth: true`
- [ ] Outdated providers removed
- [ ] New providers included

## Backward Compatibility

All changes are **backward compatible**:

1. **Model validation:** Expanding regex doesn't break existing valid names
2. **Optional auth:** Default is `requires_auth: true`, maintaining existing behavior
3. **Empty API keys:** Only for explicitly opt-in providers
4. **Foundry integration:** Optional endpoint, existing CLI key manager still works
5. **Provider updates:** Existing provider configurations work with new fields

## Success Criteria

- ✅ Users can configure local Ollama provider in Foundry without entering dummy API keys
- ✅ Model names with colons (e.g., `qwen3:14b`) are accepted and work correctly
- ✅ System differentiates between authenticated and non-authenticated providers automatically
- ✅ Users can configure different models for general and tactical AI
- ✅ Seamless switching between providers works (local/local, local/remote, remote/remote)
- ✅ Existing providers (OpenAI, Anthropic, etc.) continue to work unchanged
- ✅ Provider list updated to match LiteLLM's current 103 providers
- ✅ All changes are backward compatible

## Risks and Mitigations

### Risk 1: Security Concerns with Expanded Validation
**Mitigation:** The expanded pattern (`[a-zA-Z0-9._:/-]`) is still very restrictive. No special characters that could be used for injection are allowed. Colons and slashes are standard in model naming conventions.

### Risk 2: Breaking Changes with Optional Auth
**Mitigation:** Default behavior is `requires_auth: true`. Only explicitly configured providers skip authentication. Existing provider configurations are unaffected.

### Risk 3: Foundry Integration Complexity
**Mitigation:** Backend validates configuration before use. Clear error messages guide users. Fallback to CLI key manager for remote providers.

### Risk 4: Provider List Conflicts
**Mitigation:** Provider list updated from research data. Testing ensures all providers load correctly. Rollback available if issues arise.

## Design Decisions

### Why Not Separate `litellm_local_providers.json`?
A single `litellm_providers.json` is sufficient and simpler:
- All providers have `provider_type` field (local vs remote)
- No need for duplicate configuration management
- Easier to maintain and update
- Clearer separation via `requires_auth` flag

### Why Remove Model Discovery?
User feedback: "Model discovery seems unnecessary since we're relying on user to configure their local model correctly either way."
- Users manually enter provider and model in Foundry settings
- Backend validates and attempts to use
- Simpler implementation, less complexity
- Discovery can be added later as enhancement if needed

### Why Foundry Settings Workflow?
User feedback: "Models that don't have api keys should simply be able to be specified in Foundry without setting them up in key manager"
- Direct configuration in Foundry VTT is more user-friendly
- Reduces configuration steps
- Better for VTT-native workflow
- Key manager still available for remote providers

## Future Enhancements (Out of Scope)

1. Model discovery via `/v1/models` endpoint (optional feature)
2. Provider health checks before use
3. Multi-endpoint configuration per provider
4. Model aliases and friendly names
5. Rate limiting and retry configuration per provider
6. Auto-refresh of provider lists on startup

## References

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [LiteLLM Provider List](https://docs.litellm.ai/docs/providers)
- [OpenAI API Specification](https://platform.openai.com/docs/api-reference)
- Research output: `scripts/output/RESEARCH_SUMMARY.md`
- Research data: `scripts/output/litellm-local-providers-research.json`
