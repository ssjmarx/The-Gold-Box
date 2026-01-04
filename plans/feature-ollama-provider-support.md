# Feature: Ollama and Local Provider Support

## Overview
This feature adds comprehensive support for local AI providers (particularly Ollama) and improves the custom provider system to handle providers that don't require authentication or use non-standard model naming conventions.

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

### 2. API Keys Mandatory for All Providers
**File:** `backend/services/ai_services/ai_service.py` (lines 66-71)

**Issue:** System throws `APIKeyException` if no API key is configured, even for local providers like Ollama that don't require authentication.

**Impact:**
- Users must enter dummy API keys to satisfy validation
- Confusing UX for local provider setup
- Adds unnecessary friction

### 3. API Key Minimum Length Validation
**File:** `backend/services/system_services/key_manager.py` (lines 135-139)

**Issue:** Key manager requires API keys to be at least 8 characters long.

**Impact:**
- Cannot use empty string or short placeholder values
- Forces users to create arbitrary long dummy keys
- No way to indicate "no authentication needed"

### 4. No Model Discovery
**Issue:** No mechanism to query provider's `/v1/models` endpoint to discover available models.

**Impact:**
- Users must manually enter all model names
- Prone to typos and errors
- Cannot validate that models actually exist on the server

### 5. Pre-configured Ollama Provider Inadequate
**File:** `backend/shared/server_files/litellm_providers.json`

**Issue:** Pre-configured "ollama" provider assumes remote endpoint and requires authentication.

**Impact:**
- Cannot easily configure local Ollama instance
- Limited to sample models, not user's local models
- No differentiation between local and remote Ollama instances

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

### Solution 2: Add Optional Authentication Flag
**Files:** Multiple files require updates

**a. Update Provider JSON Schema**
**File:** `backend/shared/server_files/litellm_providers.json`

Add `requires_auth` field to provider details:
```json
"ollama": {
  "model_count": 29,
  "sample_models": [...],
  "requires_auth": false,
  "auth_type": "None",
  "default_base_url": "http://localhost:11434"
}
```

**b. Update ProviderManager**
**File:** `backend/services/system_services/provider_manager.py`

Add `requires_auth` field to provider configuration structure:
```python
self.default_providers[provider_slug] = {
    'slug': provider_slug,
    'name': provider_info.get('name', provider_slug.replace('_', ' ').title()),
    'description': provider_info.get('description', f'{model_count} models available'),
    'models': sample_models,
    'auth_type': provider_info.get('auth_type', 'Bearer Token'),
    'requires_auth': provider_info.get('requires_auth', True),  # Default: true
    'base_url': provider_info.get('base_url', ''),
    'completion_endpoint': provider_info.get('completion_endpoint', '/v1/chat/completions'),
    'is_custom': False
}
```

**c. Update Custom Provider Wizard**
**File:** `backend/shared/providers/custom_provider_wizard.py`

Add "None (Local Provider)" authentication option:
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

**d. Update AI Service**
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

**e. Update Key Manager**
**File:** `backend/services/system_services/key_manager.py`

Make API key entry optional for providers that don't require it:
```python
def add_key_flow(self):
    # ... provider selection ...
    
    # Check if provider requires authentication
    provider = self.provider_manager.get_provider(provider_slug)
    if not provider.get('requires_auth', True):
        print(f"\n{provider_name} does not require authentication.")
        print("Skipping API key entry.")
        return True
    
    # ... existing API key entry flow ...
```

Allow shorter/empty API keys:
```python
if api_key and len(api_key) < 8:
    print("ERROR: Key too short - API keys must be at least 8 characters long")
    print("Please enter a valid API key or try again.")
    continue

# Allow empty string for providers without auth
if not api_key:
    self.key_storage.add_key(provider_slug, '')
    print(f"\n{provider_name} configured without API key")
    return True
```

### Solution 3: Add Model Discovery Feature

**File:** `backend/shared/providers/custom_provider_wizard.py`

Add model discovery method:
```python
def discover_models(self, base_url: str, api_key: str = None, requires_auth: bool = False) -> List[str]:
    """
    Discover available models from /v1/models endpoint
    
    Args:
        base_url: Provider base URL (e.g., http://localhost:11434)
        api_key: Optional API key for authentication
        requires_auth: Whether provider requires authentication
        
    Returns:
        List of model IDs discovered from provider
    """
    try:
        headers = {}
        if api_key and requires_auth:
            headers['Authorization'] = f'Bearer {api_key}'
        
        # Ensure base_url doesn't have trailing slash
        base_url = base_url.rstrip('/')
        
        response = requests.get(
            f"{base_url}/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            model_ids = [model['id'] for model in models]
            
            print(f"✓ Discovered {len(model_ids)} models")
            return model_ids
        else:
            print(f"✗ Model discovery failed with status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return []
            
    except requests.exceptions.Timeout:
        print("✗ Connection timeout - server may be slow or unavailable")
        return []
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed - check URL or network connectivity")
        return []
    except requests.exceptions.SSLError:
        print("✗ SSL/TLS error - certificate issues or invalid HTTPS")
        return []
    except json.JSONDecodeError:
        print("✗ Invalid JSON response from /v1/models endpoint")
        return []
    except Exception as e:
        print(f"✗ Model discovery failed: {str(e)}")
        return []
```

Add model discovery UI flow:
```python
def _configure_models(self):
    """Configure model names for the provider"""
    from ui.cli_manager import CLIManager
    
    print("\nModel Configuration:")
    print("Choose how to add models:")
    print("1. Discover from /v1/models endpoint")
    print("2. Enter manually (comma-separated)")
    
    mode_choice = CLIManager.get_menu_choice([1, 2], "Choose method")
    
    if mode_choice == 1:
        # Discovery mode - requires base_url and optional api_key
        # These will be available from config if called in right order
        return self._discover_and_select_models()
    else:
        # Manual mode - existing logic
        return self._enter_models_manually()

def _discover_and_select_models(self) -> List[str]:
    """Discover models and let user select which to enable"""
    from ui.cli_manager import CLIManager
    
    # Get base URL from user or use default
    base_url = CLIManager.get_text_input(
        "Base URL for model discovery (e.g., http://localhost:11434): ",
        required=True
    )
    
    if not base_url.startswith(('http://', 'https://')):
        CLIManager.display_error("URL must start with http:// or https://")
        return self._discover_and_select_models()  # Retry
    
    # Check if provider requires auth
    requires_api_key = CLIManager.get_yes_no("Does this provider require API key?")
    api_key = None
    
    if requires_api_key:
        api_key = CLIManager.get_password_input("API Key (leave empty for public): ")
    
    print(f"\nAttempting to discover models from {base_url}...")
    
    # Discover models
    discovered_models = self.discover_models(
        base_url=base_url,
        api_key=api_key if api_key else None,
        requires_auth=requires_api_key
    )
    
    if not discovered_models:
        CLIManager.display_error("No models discovered or discovery failed.")
        fallback = CLIManager.get_yes_no("Enter models manually instead?")
        if fallback:
            return self._enter_models_manually()
        return []
    
    # Display discovered models
    print(f"\nDiscovered {len(discovered_models)} models:")
    for i, model in enumerate(discovered_models[:20], 1):  # Show first 20
        print(f"  {i:2d}. {model}")
    
    if len(discovered_models) > 20:
        print(f"  ... and {len(discovered_models) - 20} more")
    
    # Let user select
    print("\nOptions:")
    print("1. Select all models")
    print("2. Select specific models")
    print("3. Enter manually instead")
    
    selection = CLIManager.get_menu_choice([1, 2, 3], "Choose selection method")
    
    if selection == 1:
        return discovered_models[:10]  # Limit to 10
    elif selection == 2:
        print("\nEnter model numbers to enable (comma-separated, e.g., 1,3,5):")
        indices_input = input("> ").strip()
        
        try:
            indices = [int(idx.strip()) - 1 for idx in indices_input.split(',')]
            selected = [discovered_models[i] for i in indices if 0 <= i < len(discovered_models)]
            
            if selected:
                return selected[:10]  # Limit to 10
            else:
                CLIManager.display_error("No valid models selected.")
                return self._discover_and_select_models()  # Retry
        except ValueError:
            CLIManager.display_error("Invalid input. Please enter numbers separated by commas.")
            return self._discover_and_select_models()  # Retry
    else:
        return self._enter_models_manually()

def _enter_models_manually(self) -> List[str]:
    """Enter model names manually"""
    from ui.cli_manager import CLIManager
    
    print("\nEnter model names manually (comma-separated)")
    print("Examples: gpt-4, claude-3, qwen3:14b, llama3.2:3b")
    
    while True:
        models_input = CLIManager.get_text_input(
            "Models (comma-separated): ",
            required=False
        )
        
        if not models_input:
            return []  # Will generate default from slug
        
        # Parse models
        models = [model.strip() for model in models_input.split(',')]
        models = [model for model in models if model]
        
        if not models:
            CLIManager.display_error("At least one model is required.")
            continue
        
        # Validate with expanded pattern
        invalid_models = []
        for model in models:
            if not re.match(r'^[a-zA-Z0-9._:/-]+$', model):
                invalid_models.append(model)
        
        if invalid_models:
            CLIManager.display_error(f"Invalid model names: {', '.join(invalid_models)}")
            print("Model names can contain letters, numbers, dots, hyphens, underscores, colons, and slashes.")
            continue
        
        return models[:10]
```

## Implementation Plan

### Phase 1: Model Name Validation (Low Risk)
1. Update regex in `custom_provider_wizard.py`
2. Update validation error message to reflect new allowed characters
3. Test with various model name formats

### Phase 2: Optional Authentication (Medium Risk)
1. Add `requires_auth` field to `litellm_providers.json` for Ollama
2. Update `ProviderManager` to handle `requires_auth` flag
3. Update `CustomProviderWizard` to offer "None (Local Provider)" option
4. Update `AIService` to conditionally check for API keys
5. Update `KeyManager` to skip API key for providers without auth
6. Update `KeyManager` validation to allow empty keys
7. Test with local Ollama instance

### Phase 3: Model Discovery (Medium Risk)
1. Add `discover_models()` method to `CustomProviderWizard`
2. Add `_discover_and_select_models()` and `_enter_models_manually()` helper methods
3. Update `_configure_models()` to offer discovery option
4. Test with various providers (Ollama, OpenAI-compatible servers)
5. Handle edge cases (no models, network errors, authentication failures)

### Phase 4: Provider Configuration Updates (Low Risk)
1. Update pre-configured Ollama provider in `litellm_providers.json`
2. Add sample models with colons to demonstrate support
3. Update provider descriptions to indicate local vs remote usage

## Files to Modify

1. **backend/shared/providers/custom_provider_wizard.py**
   - Update model name validation regex (line 163)
   - Add "None (Local Provider)" auth option
   - Add `discover_models()` method
   - Add `_configure_models()` with discovery option
   - Add `_discover_and_select_models()` helper
   - Add `_enter_models_manually()` helper
   - Update validation error messages

2. **backend/shared/server_files/litellm_providers.json**
   - Add `requires_auth` field to Ollama provider
   - Update Ollama sample models to include colon format
   - Add `default_base_url` for local usage

3. **backend/services/system_services/provider_manager.py**
   - Add `requires_auth` field to provider structure in `load_default_providers()`

4. **backend/services/ai_services/ai_service.py**
   - Make API key check conditional based on `requires_auth` flag

5. **backend/services/system_services/key_manager.py**
   - Skip API key entry for providers without auth
   - Allow empty API keys in validation

## Testing Plan

### Test Case 1: Model Name Validation
- [ ] Enter model with colon: `qwen3:14b` → Should accept
- [ ] Enter model with slash: `openrouter/anthropic/claude-3` → Should accept
- [ ] Enter model with special chars: `model@name` → Should reject
- [ ] Enter empty model name → Should reject

### Test Case 2: Local Provider (No Auth)
- [ ] Create custom provider with "None (Local Provider)" auth
- [ ] Skip API key entry in key manager
- [ ] Configure base URL to `http://localhost:11434`
- [ ] Successfully call AI without API key

### Test Case 3: Model Discovery
- [ ] Discover models from local Ollama instance
- [ ] Select subset of discovered models
- [ ] Handle discovery failure gracefully
- [ ] Fallback to manual entry when discovery fails

### Test Case 4: Pre-configured Ollama Provider
- [ ] Select "ollama" provider from list
- [ ] Configure as local instance (no API key)
- [ ] Use model with colon: `qwen3:14b`
- [ ] Successfully complete AI call

### Test Case 5: Mixed Environment
- [ ] Configure both local (Ollama) and remote (OpenAI) providers
- [ ] Local provider works without API key
- [ ] Remote provider requires and uses API key
- [ ] Both providers work in same session

## Backward Compatibility

All changes are **backward compatible**:

1. **Model validation:** Expanding regex doesn't break existing valid names
2. **Optional auth:** Default is `requires_auth: true`, maintaining existing behavior
3. **Empty API keys:** Only for explicitly opt-in providers
4. **Model discovery:** Optional feature, doesn't affect manual entry

## Success Criteria

- ✅ Users can create local Ollama provider without entering dummy API keys
- ✅ Model names with colons (e.g., `qwen3:14b`) are accepted and work correctly
- ✅ Model discovery from `/v1/models` endpoint works for compatible providers
- ✅ System differentiates between authenticated and non-authenticated providers
- ✅ Existing providers (OpenAI, Anthropic, etc.) continue to work unchanged
- ✅ All changes are backward compatible

## Risks and Mitigations

### Risk 1: Security Concerns with Expanded Validation
**Mitigation:** The expanded pattern (`[a-zA-Z0-9._:/-]`) is still very restrictive. No special characters that could be used for injection are allowed. Colons and slashes are standard in model naming conventions.

### Risk 2: Breaking Changes with Optional Auth
**Mitigation:** Default behavior is `requires_auth: true`. Only explicitly configured providers skip authentication. Existing provider configurations are unaffected.

### Risk 3: Model Discovery Failures
**Mitigation:** Discovery is optional and falls back to manual entry. Clear error messages guide users when discovery fails. Timeout protection prevents hanging.

### Risk 4: Empty API Key Confusion
**Mitigation:** Clear UI indication when provider doesn't require authentication. "None (Local Provider)" option explicitly communicates no auth needed.

## Future Enhancements (Out of Scope)

1. Auto-refresh of model lists on startup
2. Model metadata discovery (context window, pricing, etc.)
3. Provider health checks before use
4. Multi-endpoint configuration per provider
5. Model aliases and friendly names
6. Rate limiting and retry configuration per provider

## References

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [LiteLLM Provider List](https://docs.litellm.ai/docs/providers)
- [OpenAI API Specification](https://platform.openai.com/docs/api-reference)
