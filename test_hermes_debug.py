#!/usr/bin/env python3
"""
Debug Hermes parameter validation issues.
This script tests the Hermes agent parameter validation to identify "invalid params" errors.
"""

import sys
import traceback

print("=== DEBUGGING HERMES PARAMETER VALIDATION ===")

# Test 1: Check Hermes agent implementation for parameter validation issues
print("\n1. Checking Hermes agent parameter validation...")

try:
    from hermes_agent import HermesAgent
    print("✅ HermesAgent imported successfully")
    
    # Create agent
    agent = HermesAgent(agent_id="debug_param_test")
    print("✅ HermesAgent created successfully")
    
    # Check agent config
    print(f"\nAgent config: {agent.config}")
    print(f"Agent config type: {type(agent.config)}")
    
    # Test 2: Test analyze_play_style method with various parameter combinations
    print("\n2. Testing analyze_play_style with different parameters...")
    
    # Test with valid parameters
    valid_params = {
        'decision_speed': 0.7,
        'shots_on_goal': 3,
        'aggressive_plays': 2,
        'strategy_changes': 1,
        'pattern_stability': 0.8,
        'pattern_variance': 0.3
    }
    
    print(f"\nTesting with valid parameters: {valid_params}")
    agent.start_agent()
    result = agent.analyze_play_style(valid_params, 'test_player')
    print(f"✅ Analysis completed: status={result.status}, confidence={result.confidence}")
    
    # Test with empty parameters
    print(f"\nTesting with empty parameters: {{}}")
    result2 = agent.analyze_play_style({}, 'test_player_empty')
    print(f"✅ Analysis completed: status={result2.status}, confidence={result2.confidence}")
    
    # Test with None parameters
    print(f"\nTesting with None parameters (player_id)...")
    try:
        result3 = agent.analyze_play_style(valid_params, None)
        print(f"✅ Analysis completed: status={result3.status}")
    except Exception as e:
        print(f"❌ Error with None player_id: {e}")
    
    # Test with invalid parameter types
    print(f"\nTesting with invalid parameter types...")
    invalid_params = {
        'decision_speed': 'invalid_string',  # Should be float
        'shots_on_goal': 'invalid_number',   # Should be int
    }
    
    try:
        result4 = agent.analyze_play_style(invalid_params, 'test_player_invalid')
        print(f"Analysis completed: status={result4.status}")
    except Exception as e:
        print(f"❌ Error with invalid parameter types: {e}")
    
    # Test 3: Check method signature and parameter validation
    print("\n3. Checking analyze_play_style method signature...")
    
    import inspect
    sig = inspect.signature(agent.analyze_play_style)
    print(f"Method signature: {sig}")
    
    # Check parameter annotations
    params = sig.parameters
    print(f"Parameters: {list(params.keys())}")
    
    for param_name, param in params.items():
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'No annotation'}")
    
    agent.stop_agent()
    
except Exception as e:
    print(f"❌ Error in parameter debugging: {e}")
    traceback.print_exc()

print("\n=== PARAMETER DEBUGGING COMPLETE ===")
print("If 'invalid params' errors are occurring, they might be in:")
print("1. Parameter type validation in hermes_agent.py")
print("2. Parameter handling in the analyze_play_style method")
print("3. Integration issues in integration_manager.py")

# Test 4: Check the specific analyze_play_style method in hermes_agent
print("\n4. Examining analyze_play_style method in hermes_agent...")

try:
    from hermes_agent import HermesAgent
    import inspect
    
    agent = HermesAgent(agent_id="method_inspect_test")
    
    # Get the source code of analyze_play_style
    try:
        source = inspect.getsource(agent.analyze_play_style)
        print("Method source code (first 20 lines):")
        lines = source.split('\n')
        for line in lines[:20]:
            print(f"  {line}")
    except:
        print("Could not get source code, but method exists")
    
    agent.stop_agent()
    
except Exception as e:
    print(f"❌ Error examining method: {e}")

print("\n=== DEBUGGING COMPLETE ===")
print("The Hermes agent parameter validation should handle:")
print("- Type checking for numeric parameters")
print("- Default values for missing parameters")
print("- Error handling for invalid parameter types")
print("- Graceful fallbacks for incomplete data")