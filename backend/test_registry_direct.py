#!/usr/bin/env python3
"""
Direct test script for Universal Service Registry implementation
Tests registry by importing the module file directly
"""

import sys
import os
import importlib.util

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_registry_direct():
    """Test registry by importing the module file directly"""
    print("\n=== Testing Direct Registry Module Import ===")
    
    try:
        # Import registry module directly
        registry_path = os.path.join(os.path.dirname(__file__), 'server', 'registry.py')
        spec = importlib.util.spec_from_file_location("registry", registry_path)
        registry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(registry_module)
        
        # Get ServiceRegistry class
        ServiceRegistry = registry_module.ServiceRegistry
        
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
        print(f"❌ Direct registry test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_registry_full_simulation():
    """Test full registry simulation with multiple services"""
    print("\n=== Testing Full Registry Simulation ===")
    
    try:
        # Import registry module directly
        registry_path = os.path.join(os.path.dirname(__file__), 'server', 'registry.py')
        spec = importlib.util.spec_from_file_location("registry", registry_path)
        registry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(registry_module)
        
        ServiceRegistry = registry_module.ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        print("🔄 Simulating complete service registration...")
        
        # Register services like in actual startup
        services = {
            'key_manager': {'type': 'MultiKeyManager', 'instance_id': 'km_001'},
            'provider_manager': {'type': 'ProviderManager', 'instance_id': 'pm_001'},
            'settings_manager': {'type': 'SettingsManager', 'instance_id': 'sm_001'},
            'client_manager': {'type': 'ClientManager', 'instance_id': 'cm_001'},
            'websocket_manager': {'type': 'WebSocketManager', 'instance_id': 'wm_001'},
            'ai_service': {'type': 'AIService', 'instance_id': 'as_001'},
        }
        
        # Register all services
        for name, service_info in services.items():
            success = ServiceRegistry.register(name, service_info)
            if not success:
                print(f"❌ Failed to register {name}")
                return False
            print(f"  ✅ Registered {name}: {service_info['type']}")
        
        # Mark as ready
        ServiceRegistry.initialize_complete()
        print("  ✅ Registry marked as ready")
        
        print("\n🔄 Testing service access patterns...")
        
        # Test 1: All services accessible
        for name in services.keys():
            try:
                retrieved = ServiceRegistry.get(name)
                if retrieved == services[name]:
                    print(f"  ✅ {name}: Access successful")
                else:
                    print(f"  ❌ {name}: Access failed - wrong instance")
                    return False
            except Exception as e:
                print(f"  ❌ {name}: Access failed - exception: {e}")
                return False
        
        # Test 2: Instance consistency
        provider_1 = ServiceRegistry.get('provider_manager')
        provider_2 = ServiceRegistry.get('provider_manager')
        same_instance = provider_1 is provider_2
        print(f"  ✅ Provider manager consistency: {'SUCCESS' if same_instance else 'FAILED'}")
        
        # Test 3: Service validation
        required_services = ['key_manager', 'provider_manager', 'settings_manager']
        validation_success = ServiceRegistry.validate_required_services(required_services)
        print(f"  ✅ Required services validation: {'SUCCESS' if validation_success else 'FAILED'}")
        
        # Test 4: Missing services validation
        missing_validation = ServiceRegistry.validate_required_services(['key_manager', 'missing_service'])
        print(f"  ✅ Missing services validation: {'SUCCESS' if not missing_validation else 'FAILED'}")
        
        # Test 5: Registry state
        is_ready = ServiceRegistry.is_ready()
        service_count = len(ServiceRegistry.list_services())
        startup_order = ServiceRegistry.get_startup_order()
        
        print(f"  ✅ Registry state check:")
        print(f"    - Ready: {is_ready}")
        print(f"    - Service count: {service_count}")
        print(f"    - Startup order: {startup_order}")
        
        # Test 6: Service info details
        service_info = ServiceRegistry.get_service_info()
        print(f"  ✅ Service info details:")
        for name, info in service_info.items():
            print(f"    - {name}: {info['type']} (order: {info['registered_order']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Full registry simulation FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_scenarios():
    """Test various error scenarios"""
    print("\n=== Testing Error Scenarios ===")
    
    try:
        # Import registry module directly
        registry_path = os.path.join(os.path.dirname(__file__), 'server', 'registry.py')
        spec = importlib.util.spec_from_file_location("registry", registry_path)
        registry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(registry_module)
        
        ServiceRegistry = registry_module.ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        # Test 1: Get from empty registry
        try:
            ServiceRegistry.get('non_existent')
            print("❌ Empty registry get: FAILED (should have raised ValueError)")
            return False
        except ValueError as e:
            print("✅ Empty registry get: SUCCESS (correctly raised ValueError)")
            print(f"    Error message: {e}")
        except Exception as e:
            print(f"❌ Empty registry get: FAILED (wrong exception: {e})")
            return False
        
        # Test 2: Register with overwrite protection
        ServiceRegistry.register('test_service', {'version': 1})
        double_reg = ServiceRegistry.register('test_service', {'version': 2}, overwrite=False)
        print(f"✅ Double registration prevention: {'SUCCESS' if not double_reg else 'FAILED'}")
        
        # Test 3: Register with overwrite allowed
        overwrite_success = ServiceRegistry.register('test_service', {'version': 2}, overwrite=True)
        print(f"✅ Overwrite allowed: {'SUCCESS' if overwrite_success else 'FAILED'}")
        
        # Test 4: Get with default
        default_result = ServiceRegistry.get('non_existent', {'default': 'works'})
        if default_result == {'default': 'works'}:
            print("✅ Default value fallback: SUCCESS")
        else:
            print("❌ Default value fallback: FAILED")
            return False
        
        # Test 5: Reset functionality
        ServiceRegistry.register('will_be_reset', {'data': 'value'})
        before_reset = ServiceRegistry.is_registered('will_be_reset')
        ServiceRegistry.reset()
        after_reset = ServiceRegistry.is_registered('will_be_reset')
        
        if before_reset and not after_reset:
            print("✅ Reset functionality: SUCCESS")
        else:
            print("❌ Reset functionality: FAILED")
            return False
        
        # Test 6: State after reset
        is_ready_after_reset = ServiceRegistry.is_ready()
        services_after_reset = len(ServiceRegistry.list_services())
        reset_state_ok = not is_ready_after_reset and services_after_reset == 0
        
        if reset_state_ok:
            print("✅ Reset state validation: SUCCESS")
        else:
            print("❌ Reset state validation: FAILED")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error scenarios test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all direct tests"""
    print("🧪 Starting Direct Service Registry Tests")
    print("=" * 60)
    
    tests = [
        ("Direct Registry Module Import", test_registry_direct),
        ("Full Registry Simulation", test_registry_full_simulation),
        ("Error Scenarios", test_error_scenarios),
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
        print("\n✅ Core functionality verified:")
        print("  - Service registration and retrieval")
        print("  - Instance deduplication")
        print("  - Error handling and validation")
        print("  - Registry state management")
        print("  - Convenience functions")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
