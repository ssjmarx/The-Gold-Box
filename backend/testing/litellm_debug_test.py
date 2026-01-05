#!/usr/bin/env python3
"""
LiteLLM Debug Test Script
Tests all Ollama provider variants with llama3.2:3b model
Uses full LiteLLM debugging to diagnose issues
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(BACKEND_DIR))

print("=" * 80)
print("LiteLLM Ollama Provider Debug Test")
print("=" * 80)
print()

# Test configuration
BASE_MODEL_NAME = "llama3.2:3b"
TEST_MESSAGE = "Hello! Please respond with just 'Test successful' to confirm you're working."

# Providers to test - use prefixed model names for auto-detection
PROVIDERS_TO_TEST = [
    {
        "name": "ollama",
        "description": "Native Ollama API (with prefixed model)",
        "base_url": "http://localhost:11434",
        "model": f"ollama/{BASE_MODEL_NAME}",
        "requires_custom_llm_provider": False
    },
    {
        "name": "ollama_chat",
        "description": "Ollama Chat endpoint (with prefixed model)",
        "base_url": "http://localhost:11434",
        "model": f"ollama_chat/{BASE_MODEL_NAME}",
        "requires_custom_llm_provider": False
    },
    {
        "name": "ollama_openai",
        "description": "Ollama via OpenAI-compatible API (with prefixed model)",
        "base_url": "http://localhost:11434/v1",
        "model": f"ollama_openai/{BASE_MODEL_NAME}",
        "requires_custom_llm_provider": False
    },
    {
        "name": "custom_openai",
        "description": "Custom OpenAI-compatible (manual config + custom_llm_provider)",
        "base_url": "http://localhost:11434/v1",
        "model": BASE_MODEL_NAME,
        "requires_custom_llm_provider": True
    }
]

async def test_provider(provider_config, test_index):
    """Test a single provider configuration"""
    provider_name = provider_config["name"]
    description = provider_config["description"]
    base_url = provider_config["base_url"]
    model_name = provider_config["model"]
    
    print(f"\n{'=' * 80}")
    print(f"TEST {test_index}: {provider_name} - {description}")
    print(f"{'=' * 80}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model_name}")
    print()
    
    try:
        import litellm
        from litellm import acompletion
        
        # Turn on debug mode
        print("Enabling LiteLLM debug mode...")
        litellm.set_verbose = True
        litellm.debug = True
        print("LiteLLM debug mode enabled\n")
        
        # Prepare completion parameters
        completion_params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": TEST_MESSAGE}
            ],
            "temperature": 0.1,
            "max_tokens": 100,
            "stream": False
        }
        
        # Add base_url if provided
        if base_url:
            completion_params["api_base"] = base_url
            print(f"Using custom base_url: {base_url}")
        
        # Set custom_llm_provider if needed
        if provider_config.get("requires_custom_llm_provider"):
            completion_params["custom_llm_provider"] = provider_name
            print(f"Using custom_llm_provider: {provider_name}")
        
        # Set dummy API key (not needed for local Ollama but required by LiteLLM)
        completion_params["api_key"] = "dummy-key-not-required"
        print("Using dummy API key (local provider)\n")
        
        print("-" * 80)
        print("Calling LiteLLM acompletion()...")
        print("-" * 80)
        
        # Make the API call with timeout
        try:
            response = await asyncio.wait_for(
                acompletion(**completion_params),
                timeout=30
            )
            
            print("-" * 80)
            print("SUCCESS! Response received:")
            print("-" * 80)
            
            # Print response details
            if response and response.choices:
                choice = response.choices[0]
                content = choice.message.content if choice.message else ""
                
                print(f"Finish Reason: {getattr(choice, 'finish_reason', 'unknown')}")
                print(f"Content: {content}")
                
                if hasattr(response, 'usage') and response.usage:
                    print(f"Tokens Used: {response.usage.total_tokens}")
                    print(f"  - Prompt: {response.usage.prompt_tokens}")
                    print(f"  - Completion: {response.usage.completion_tokens}")
                
                return {
                    "success": True,
                    "provider": provider_name,
                    "response": content,
                    "tokens": getattr(response.usage, 'total_tokens', 0) if response.usage else 0,
                    "finish_reason": getattr(choice, 'finish_reason', 'unknown')
                }
            else:
                return {
                    "success": False,
                    "provider": provider_name,
                    "error": "No choices in response"
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "provider": provider_name,
                "error": "Request timed out after 30 seconds"
            }
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print("-" * 80)
        print(f"ERROR: {error_type}")
        print("-" * 80)
        print(f"Error Message: {error_msg}")
        print()
        
        # Print detailed error info
        import traceback
        print("Full Traceback:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        
        return {
            "success": False,
            "provider": provider_name,
            "error": f"{error_type}: {error_msg}"
        }

async def main():
    """Run all provider tests"""
    print("Initializing test environment...")
    print()
    
    # Check if Ollama is running
    print("Checking if Ollama is accessible...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            available_models = [m.get("name") for m in models]
            print(f"✓ Ollama is running")
            print(f"  Available models: {', '.join(available_models[:5])}")
            
            if BASE_MODEL_NAME not in available_models:
                print(f"\n⚠ WARNING: Model '{BASE_MODEL_NAME}' not found in available models!")
                print(f"  You may need to pull it with: ollama pull {BASE_MODEL_NAME}")
            else:
                print(f"  ✓ Model '{BASE_MODEL_NAME}' is available")
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            print("  Please ensure Ollama is running on http://localhost:11434")
            return
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        print("  Please ensure Ollama is running on http://localhost:11434")
        return
    
    print()
    
    # Check LiteLLM version
    try:
        import litellm
        # Try to get version, handle different LiteLLM versions
        try:
            version = litellm.__version__
            print(f"LiteLLM version: {version}")
        except AttributeError:
            # Version attribute not available in this version
            print("LiteLLM installed (version information not available)")
        print()
    except ImportError:
        print("ERROR: LiteLLM not installed!")
        print("Please install it with: pip install litellm")
        return
    
    # Run tests for each provider
    results = []
    for i, provider_config in enumerate(PROVIDERS_TO_TEST, 1):
        result = await test_provider(provider_config, i)
        results.append(result)
        
        # Add delay between tests
        if i < len(PROVIDERS_TO_TEST):
            print(f"\nWaiting 2 seconds before next test...")
            await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print()
    
    if successful:
        print("✓ SUCCESSFUL PROVIDERS:")
        for r in successful:
            print(f"  • {r['provider']}: {r.get('tokens', 0)} tokens - {r.get('finish_reason', 'unknown')}")
        print()
    
    if failed:
        print("✗ FAILED PROVIDERS:")
        for r in failed:
            print(f"  • {r['provider']}: {r.get('error', 'Unknown error')}")
        print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if len(successful) == 0:
        print("⚠ All providers failed. Possible issues:")
        print("  1. Ollama is not running or not accessible")
        print("  2. Model 'llama3.2:3b' is not pulled")
        print("  3. LiteLLM version incompatibility")
        print("  4. Network/firewall issues")
    elif len(successful) == 1:
        successful_provider = successful[0]['provider']
        print(f"✓ Only '{successful_provider}' is working.")
        print(f"  Recommendation: Use '{successful_provider}' for Ollama in production.")
        print()
        print("  To use this provider in your frontend:")
        print(f"  - Set 'General LLM Provider' to '{successful_provider}'")
        print(f"  - Set 'General LLM Model' to '{BASE_MODEL_NAME}'")
    else:
        print("✓ Multiple providers are working!")
        print("  Here are your options:")
        for r in successful:
            desc = next(p['description'] for p in PROVIDERS_TO_TEST if p['name'] == r['provider'])
            print(f"  • {r['provider']}: {desc}")
        print()
        print("  Recommended: Use 'ollama_openai' for best compatibility with function calling")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
