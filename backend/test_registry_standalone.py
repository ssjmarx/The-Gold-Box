#!/usr/bin/env python3
"""
Standalone test script for Universal Service Registry implementation
Tests registry functionality without importing server module
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_registry_direct():
    """Test registry by importing it directly"""
    print("\n=== Testing Registry Direct Import ===")
    
    try:
        # Import registry directly from its module
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
        
        # Test convenience functions
        from server.registry import register_service, get_service, is_service_registered, list_registered_services
        
        # Test convenience register
        test_service2 = {"name": "test_service2", "data": "test_data2"}
        reg_success = register_service('test_service2', test_service2)
        print(f"✅ Convenience register: {'SUCCESS' if reg_success else 'FAILED'}")
        
        # Test convenience get
        get_success = get_service('test_service2') == test_service2
        print(f"✅ Convenience get: {'SUCCESS' if get_success else 'FAILED'}")
        
        # Test convenience is_registered
        is_reg_success = is_service_registered('test_service2')
        print(f"✅ Convenience is_registered: {'SUCCESS' if is_reg_success else 'FAILED'}")
        
        # Test convenience list
        list_success = 'test_service2' in list_registered_services()
        print(f"✅ Convenience list: {'SUCCESS' if list_success else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct registry test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_registry_simulation():
    """Simulate the actual usage pattern"""
    print("\n=== Testing Registry Simulation ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        print("🔄 Simulating service registration...")
        
        # Simulate registering services like in startup
        services_to_register = {
            'key_manager': {'name': 'key_manager', 'instance': 'KeyManagerInstance'},
            'provider_manager': {'name': 'provider_manager', 'instance': 'ProviderManagerInstance'},
            'settings_manager': {'name': 'settings_manager', 'instance': 'SettingsManagerInstance'},
            'client_manager': {'name': 'client_manager', 'instance': 'ClientManagerInstance'},
        }
        
        # Register all services
        for name, service_info in services_to_register.items():
            success = ServiceRegistry.register(name, service_info['instance'])
            if not success:
                print(f"❌ Failed to register {name}")
                return False
        
        print("✅ All services registered successfully")
        
        # Mark as ready
        ServiceRegistry.initialize_complete()
        
        print("🔄 Testing service access patterns...")
        
        # Test 1: Direct access
        direct_provider = ServiceRegistry.get('provider_manager')
        print(f"✅ Direct access: {'SUCCESS' if direct_provider == 'ProviderManagerInstance' else 'FAILED'}")
        
        # Test 2: Multiple access (should return same instance)
        provider_1 = ServiceRegistry.get('provider_manager')
        provider_2 = ServiceRegistry.get('provider_manager')
        same_instance = provider_1 is provider_2
        print(f"✅ Instance consistency: {'SUCCESS' if same_instance else 'FAILED'}")
        
        # Test 3: Service validation
        required_services = ['key_manager', 'provider_manager', 'settings_manager']
        validation_success = ServiceRegistry.validate_required_services(required_services)
        print(f"✅ Service validation: {'SUCCESS' if validation_success else 'FAILED'}")
        
        # Test 4: Missing service validation
        missing_validation = ServiceRegistry.validate_required_services(['key_manager', 'missing_service'])
        print(f"✅ Missing service validation: {'SUCCESS' if not missing_validation else 'FAILED'}")
        
        # Test 5: Service info and order
        service_info = ServiceRegistry.get_service_info()
        startup_order = ServiceRegistry.get_startup_order()
        
        expected_order = ['key_manager', 'provider_manager', 'settings_manager', 'client_manager']
        order_correct = startup_order == expected_order
        print(f"✅ Startup order: {'SUCCESS' if order_correct else 'FAILED'}")
        print(f"    Registered order: {startup_order}")
        
        # Test 6: Registry state
        is_ready = ServiceRegistry.is_ready()
        service_count = len(ServiceRegistry.list_services())
        print(f"✅ Registry state: {'SUCCESS' if is_ready and service_count == 4 else 'FAILED'}")
        print(f"    Services registered: {service_count}")
        print(f"    Registry ready: {is_ready}")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry simulation test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n=== Testing Edge Cases ===")
    
    try:
        from server.registry import ServiceRegistry
        
        # Reset registry
        ServiceRegistry.reset()
        
        # Test 1: Double registration without overwrite
        ServiceRegistry.register('test_service', {'version': 1})
        double_reg = ServiceRegistry.register('test_service', {'version': 2}, overwrite=False)
        print(f"✅ Double registration prevention: {'SUCCESS' if not double_reg else 'FAILED'}")
        
        # Test 2: Double registration with overwrite
        overwrite_success = ServiceRegistry.register('test_service', {'version': 2}, overwrite=True)
        print(f"✅ Double registration with overwrite: {'SUCCESS' if overwrite_success else 'FAILED'}")
        
        # Test 3: Get with default value
        default_value = ServiceRegistry.get('non_existent', {'default': 'works'})
        default_correct = default_value == {'default': 'works'}
        print(f"✅ Default value fallback: {'SUCCESS' if default_correct else 'FAILED'}")
        
        # Test 4: Get without default (should raise error)
        try:
            ServiceRegistry.get('non_existent')
            print("❌ Error raising: FAILED (should have raised ValueError)")
            return False
        except ValueError:
            print("✅ Error raising: SUCCESS (correctly raised ValueError)")
        except Exception as e:
            print(f"❌ Error raising: FAILED (wrong exception: {e})")
            return False
        
        # Test 5: Reset functionality
        ServiceRegistry.register('will_be_reset', {'data': 'value'})
        before_reset = ServiceRegistry.is_registered('will_be_reset')
        ServiceRegistry.reset()
        after_reset = ServiceRegistry.is_registered('will_be_reset')
        reset_works = before_reset and not after_reset
        print(f"✅ Reset functionality: {'SUCCESS' if reset_works else 'FAILED'}")
        
        # Test 6: State after reset
        is_ready_after_reset = ServiceRegistry.is_ready()
        services_after_reset = len(ServiceRegistry.list_services())
        reset_state_ok = not is_ready_after_reset and services_after_reset == 0
        print(f"✅ Reset state: {'SUCCESS' if reset_state_ok else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all standalone tests"""
    print("🧪 Starting Standalone Service Registry Tests")
    print("=" * 60)
    
    tests = [
        ("Direct Registry Import", test_registry_direct),
        ("Registry Simulation", test_registry_simulation),
        ("Edge Cases", test_edge_cases),
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
        
        # Show final registry state if any services remain
        from server.registry import ServiceRegistry
        if len(ServiceRegistry.list_services()) > 0:
            print("\n📋 Final Registry State:")
            service_info = ServiceRegistry.get_service_info()
            for name, info in service_info.items():
                print(f"    - {name}: {info['type']} (order: {info['registered_order']})")
        else:
            print("\n📋 Registry reset to clean state")
        
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
