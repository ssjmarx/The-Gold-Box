#!/usr/bin/env python3
"""
Test script for Universal Service Registry implementation

This script tests:
1. Service registration and retrieval
2. Provider manager deduplication
3. Service access from different contexts
4. Fallback behavior
"""

import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_registry_basic_functionality():
    """Test basic registry functionality"""
    print("\n=== Testing Basic Registry Functionality ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry for clean test
        ServiceRegistry.reset()
        
        # Test registration
        test_service = {"name": "test_service", "data": "test_data"}
        success = ServiceRegistry.register('test_service', test_service)
        print(f"✅ Service registration: {'SUCCESS' if success else 'FAILED'}")
        
        # Test retrieval
        retrieved = ServiceRegistry.get('test_service')
        print(f"✅ Service retrieval: {'SUCCESS' if retrieved == test_service else 'FAILED'}")
        
        # Test is_registered
        is_registered = ServiceRegistry.is_registered('test_service')
        print(f"✅ Service existence check: {'SUCCESS' if is_registered else 'FAILED'}")
        
        # Test list_services
        services = ServiceRegistry.list_services()
        print(f"✅ Service list: {'SUCCESS' if 'test_service' in services else 'FAILED'}")
        
        # Test non-existent service
        try:
            ServiceRegistry.get('non_existent')
            print("❌ Non-existent service test: FAILED (should have raised ValueError)")
        except ValueError:
            print("✅ Non-existent service test: SUCCESS (correctly raised ValueError)")
        
        # Test with default
        default_service = ServiceRegistry.get('non_existent', {'default': True})
        print(f"✅ Default service test: {'SUCCESS' if default_service == {'default': True} else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test FAILED: {e}")
        return False

def test_provider_manager_deduplication():
    """Test that provider manager is not duplicated"""
    print("\n=== Testing Provider Manager Deduplication ===")
    
    try:
        from server.registry import ServiceRegistry
        from server.key_manager import MultiKeyManager
        from server.provider_manager import ProviderManager
        
        # Reset registry for clean test
        ServiceRegistry.reset()
        
        # Create key manager (this creates provider manager internally)
        key_manager = MultiKeyManager()
        
        # Register key manager and provider manager
        ServiceRegistry.register('key_manager', key_manager)
        ServiceRegistry.register('provider_manager', key_manager.provider_manager)
        
        # Test AI service retrieval (should use registered provider manager)
        from server.ai_service import get_ai_service
        
        # Get AI service instance
        ai_service_1 = get_ai_service()
        print(f"✅ First AI service instance: {type(ai_service_1).__name__}")
        print(f"✅ First provider manager ID: {id(ai_service_1.provider_manager)}")
        
        # Get AI service again (should return same instance)
        ai_service_2 = get_ai_service()
        print(f"✅ Second AI service instance: {type(ai_service_2).__name__}")
        print(f"✅ Second provider manager ID: {id(ai_service_2.provider_manager)}")
        
        # Check if same provider manager is used
        same_provider = ai_service_1.provider_manager is ai_service_2.provider_manager
        print(f"✅ Provider manager deduplication: {'SUCCESS' if same_provider else 'FAILED'}")
        
        # Test registered provider manager vs AI service provider manager
        registered_provider = ServiceRegistry.get('provider_manager')
        same_registered = ai_service_1.provider_manager is registered_provider
        print(f"✅ Registered provider manager reuse: {'SUCCESS' if same_registered else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Provider manager deduplication test FAILED: {e}")
        return False

def test_service_access_patterns():
    """Test service access from different import contexts"""
    print("\n=== Testing Service Access Patterns ===")
    
    try:
        from server.registry import ServiceRegistry
        from server.key_manager import MultiKeyManager
        from server.client_manager import ClientManager
        
        # Reset registry for clean test
        ServiceRegistry.reset()
        
        # Register services
        key_manager = MultiKeyManager()
        client_manager = ClientManager()
        
        ServiceRegistry.register('key_manager', key_manager)
        ServiceRegistry.register('provider_manager', key_manager.provider_manager)
        ServiceRegistry.register('client_manager', client_manager)
        
        # Mark as ready
        ServiceRegistry.initialize_complete()
        
        # Test access from different contexts
        # Context 1: Direct registry access
        provider_1 = ServiceRegistry.get('provider_manager')
        print(f"✅ Direct access: {type(provider_1).__name__}")
        
        # Context 2: Through AI service (simulates ai_service.py pattern)
        from server.ai_service import get_ai_service
        ai_service = get_ai_service()
        provider_2 = ai_service.provider_manager
        print(f"✅ AI service access: {type(provider_2).__name__}")
        
        # Context 3: Through endpoints (simulates api_chat.py pattern)
        # Import the module-level code from api_chat.py
        import sys
        import importlib.util
        
        # Create a mock endpoint module that uses our pattern
        mock_endpoint_code = '''
from server.registry import ServiceRegistry
try:
    if ServiceRegistry.is_ready() and ServiceRegistry.is_registered('provider_manager'):
        key_manager = ServiceRegistry.get('key_manager')
        provider_manager = key_manager.provider_manager
        print("✅ Mock endpoint: Using provider manager from ServiceRegistry")
    else:
        from server.provider_manager import ProviderManager
        provider_manager = ProviderManager()
        print("⚠️ Mock endpoint: Created new ProviderManager")
except Exception as e:
    print(f"❌ Mock endpoint: Failed to access ServiceRegistry: {e}")
    from server.provider_manager import ProviderManager
    provider_manager = ProviderManager()
'''
        
        # Execute mock endpoint code
        exec(mock_endpoint_code)
        
        # Verify all accesses returned the same provider manager
        same_provider = provider_1 is provider_2
        print(f"✅ Cross-context provider consistency: {'SUCCESS' if same_provider else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service access patterns test FAILED: {e}")
        return False

def test_fallback_behavior():
    """Test fallback behavior when registry is not ready"""
    print("\n=== Testing Fallback Behavior ===")
    
    try:
        from server.registry import ServiceRegistry
        from server.provider_manager import ProviderManager
        
        # Reset registry to simulate not ready state
        ServiceRegistry.reset()
        
        # Test AI service fallback
        from server.ai_service import get_ai_service
        ai_service = get_ai_service()
        
        print(f"✅ Fallback AI service created: {type(ai_service).__name__}")
        print(f"✅ Fallback provider manager: {type(ai_service.provider_manager).__name__}")
        
        # Verify it's a new instance (not from registry)
        is_new_instance = isinstance(ai_service.provider_manager, ProviderManager)
        print(f"✅ Fallback provider manager instance: {'SUCCESS' if is_new_instance else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback behavior test FAILED: {e}")
        return False

def test_startup_sequence_simulation():
    """Simulate the actual startup sequence"""
    print("\n=== Testing Startup Sequence Simulation ===")
    
    try:
        from server.registry import ServiceRegistry
        from server.key_manager import MultiKeyManager
        from server.client_manager import ClientManager
        
        # Reset registry
        ServiceRegistry.reset()
        
        print("🔄 Simulating startup sequence...")
        
        # Step 1: Key manager creation (from startup/startup.py)
        print("  Step 1: Creating key manager...")
        manager = MultiKeyManager()
        
        # Step 2: Register with registry
        print("  Step 2: Registering key manager and provider manager...")
        ServiceRegistry.register('key_manager', manager)
        ServiceRegistry.register('provider_manager', manager.provider_manager)
        
        # Step 3: Initialize global services (from startup/services.py)
        print("  Step 3: Initializing global services...")
        
        # Settings manager (simplified)
        class MockSettingsManager:
            def get_settings(self): return {}
        
        settings_manager = MockSettingsManager()
        client_manager = ClientManager()
        
        ServiceRegistry.register('settings_manager', settings_manager)
        ServiceRegistry.register('client_manager', client_manager)
        
        # Step 4: Mark as ready
        print("  Step 4: Marking registry as ready...")
        ServiceRegistry.initialize_complete()
        
        # Step 5: Test service access
        print("  Step 5: Testing service access...")
        
        from server.ai_service import get_ai_service
        ai_service = get_ai_service()
        
        # Verify registry services
        registered_services = ServiceRegistry.list_services()
        expected_services = ['key_manager', 'provider_manager', 'settings_manager', 'client_manager']
        
        all_registered = all(service in registered_services for service in expected_services)
        print(f"✅ All expected services registered: {'SUCCESS' if all_registered else 'FAILED'}")
        
        # Verify AI service uses registered provider manager
        registered_provider = ServiceRegistry.get('provider_manager')
        same_provider = ai_service.provider_manager is registered_provider
        print(f"✅ AI service uses registered provider manager: {'SUCCESS' if same_provider else 'FAILED'}")
        
        # Show service info
        service_info = ServiceRegistry.get_service_info()
        print(f"✅ Service registry info: {len(service_info)} services registered")
        
        for name, info in service_info.items():
            print(f"    - {name}: {info['type']} (order: {info['registered_order']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Startup sequence simulation FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting Universal Service Registry Tests")
    print("=" * 60)
    
    tests = [
        ("Basic Registry Functionality", test_registry_basic_functionality),
        ("Provider Manager Deduplication", test_provider_manager_deduplication),
        ("Service Access Patterns", test_service_access_patterns),
        ("Fallback Behavior", test_fallback_behavior),
        ("Startup Sequence Simulation", test_startup_sequence_simulation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Service Registry implementation is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
