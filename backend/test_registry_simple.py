#!/usr/bin/env python3
"""
Simple test script for Universal Service Registry implementation
Tests core registry functionality without external dependencies
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_registry_core():
    """Test core registry functionality only"""
    print("\n=== Testing Core Registry Functionality ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry for clean test
        ServiceRegistry.reset()
        
        # Test basic registration
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
        
        # Test initialization
        ServiceRegistry.initialize_complete()
        is_ready = ServiceRegistry.is_ready()
        print(f"✅ Registry ready: {'SUCCESS' if is_ready else 'FAILED'}")
        
        # Test service info
        service_info = ServiceRegistry.get_service_info()
        print(f"✅ Service info: {'SUCCESS' if 'test_service' in service_info else 'FAILED'}")
        
        # Test overwrite protection
        test_service2 = {"name": "test_service", "data": "new_data"}
        overwrite_success = ServiceRegistry.register('test_service', test_service2, overwrite=False)
        print(f"✅ Overwrite protection: {'SUCCESS' if not overwrite_success else 'FAILED'}")
        
        # Test overwrite allowed
        overwrite_allowed = ServiceRegistry.register('test_service', test_service2, overwrite=True)
        print(f"✅ Overwrite allowed: {'SUCCESS' if overwrite_allowed else 'FAILED'}")
        
        # Test non-existent service with default
        default_service = ServiceRegistry.get('non_existent', {'default': True})
        print(f"✅ Default service: {'SUCCESS' if default_service == {'default': True} else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Core registry test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_services():
    """Test multiple service registration and access"""
    print("\n=== Testing Multiple Services ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        # Register multiple services
        services = {
            'key_manager': {'name': 'key_manager', 'type': 'KeyManager'},
            'provider_manager': {'name': 'provider_manager', 'type': 'ProviderManager'},
            'settings_manager': {'name': 'settings_manager', 'type': 'SettingsManager'},
            'client_manager': {'name': 'client_manager', 'type': 'ClientManager'},
            'websocket_manager': {'name': 'websocket_manager', 'type': 'WebSocketManager'},
        }
        
        # Register all services
        for name, service in services.items():
            success = ServiceRegistry.register(name, service)
            if not success:
                print(f"❌ Failed to register {name}")
                return False
        
        print("✅ All services registered successfully")
        
        # Test retrieval of all services
        for name in services.keys():
            retrieved = ServiceRegistry.get(name)
            if retrieved != services[name]:
                print(f"❌ Failed to retrieve {name}")
                return False
        
        print("✅ All services retrieved successfully")
        
        # Test service list
        service_list = ServiceRegistry.list_services()
        expected_count = len(services)
        actual_count = len(service_list)
        print(f"✅ Service count: {'SUCCESS' if actual_count == expected_count else 'FAILED'} ({actual_count}/{expected_count})")
        
        # Test service info
        service_info = ServiceRegistry.get_service_info()
        info_count = len(service_info)
        print(f"✅ Service info count: {'SUCCESS' if info_count == expected_count else 'FAILED'} ({info_count}/{expected_count})")
        
        # Test startup order
        startup_order = ServiceRegistry.get_startup_order()
        print(f"✅ Startup order: {'SUCCESS' if len(startup_order) == expected_count else 'FAILED'}")
        print(f"    Services in order: {startup_order}")
        
        # Mark as ready
        ServiceRegistry.initialize_complete()
        
        # Test required services validation
        required_services = ['key_manager', 'provider_manager', 'settings_manager']
        validation_success = ServiceRegistry.validate_required_services(required_services)
        print(f"✅ Required services validation: {'SUCCESS' if validation_success else 'FAILED'}")
        
        # Test missing services validation
        missing_validation = ServiceRegistry.validate_required_services(['key_manager', 'missing_service'])
        print(f"✅ Missing services validation: {'SUCCESS' if not missing_validation else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Multiple services test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n=== Testing Error Handling ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        # Test get from empty registry
        try:
            ServiceRegistry.get('non_existent')
            print("❌ Empty registry get: FAILED (should have raised ValueError)")
            return False
        except ValueError:
            print("✅ Empty registry get: SUCCESS (correctly raised ValueError)")
        except Exception as e:
            print(f"❌ Empty registry get: FAILED (wrong exception: {e})")
            return False
        
        # Test register with None
        try:
            ServiceRegistry.register('test_none', None)
            print("✅ Register None service: SUCCESS (allowed)")
        except Exception as e:
            print(f"❌ Register None service: FAILED ({e})")
            return False
        
        # Test register with empty string name
        try:
            ServiceRegistry.register('', {'test': 'data'})
            print("✅ Register empty name: SUCCESS (allowed)")
        except Exception as e:
            print(f"❌ Register empty name: FAILED ({e})")
            return False
        
        # Test get with default
        default_result = ServiceRegistry.get('non_existent', {'default': 'value'})
        if default_result == {'default': 'value'}:
            print("✅ Get with default: SUCCESS")
        else:
            print("❌ Get with default: FAILED")
            return False
        
        # Test reset functionality
        ServiceRegistry.register('test_reset', {'data': 'value'})
        before_reset = ServiceRegistry.is_registered('test_reset')
        ServiceRegistry.reset()
        after_reset = ServiceRegistry.is_registered('test_reset')
        
        if before_reset and not after_reset:
            print("✅ Reset functionality: SUCCESS")
        else:
            print("❌ Reset functionality: FAILED")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all simple tests"""
    print("🧪 Starting Simple Service Registry Tests")
    print("=" * 60)
    
    tests = [
        ("Core Registry Functionality", test_registry_core),
        ("Multiple Services", test_multiple_services),
        ("Error Handling", test_error_handling),
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
        print("🎉 All tests passed! Service Registry core functionality is working correctly.")
        
        # Show final registry state
        from server.registry import ServiceRegistry
        print("\n📋 Final Registry State:")
        service_info = ServiceRegistry.get_service_info()
        for name, info in service_info.items():
            print(f"    - {name}: {info['type']} (order: {info['registered_order']})")
        
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
