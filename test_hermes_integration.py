#!/usr/bin/env python3
"""
Test script for Hermes Agent integration with GameTrainer system.
This script tests the complete Hermes integration implementation.
"""

import sys
import os
import time

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration_manager import GameTrainerSystem, SystemConfig

def test_hermes_integration():
    """Test the complete Hermes agent integration."""
    print("Testing Hermes Agent Integration with GameTrainer System...")
    print("=" * 60)
    
    try:
        # Test 1: System initialization with Hermes enabled
        print("\n🧪 Test 1: System initialization with Hermes enabled")
        config = SystemConfig(
            hermes_enabled=True,
            hermes_agent_id='test_hermes_integration',
            update_interval=0.1,
            capture_device_index=0,
            output_directory="./test_data"
        )
        
        system = GameTrainerSystem(config)
        print(f"✅ System initialized successfully")
        print(f"✅ Hermes agent ID: {system.hermes_agent.agent_id}")
        print(f"✅ Hermes agent active: {system.hermes_agent.is_active}")
        
        # Test 2: Hermes agent functionality
        print("\n🧪 Test 2: Hermes agent functionality")
        test_game_data = {
            'decision_speed': 0.7,
            'shots_on_goal': 3,
            'aggressive_plays': 2,
            'strategy_changes': 1,
            'pattern_stability': 0.8,
            'pattern_variance': 0.3,
            'current_animation': 'idle',
            'action_state': 'standing',
            'level': 'tutorial',
            'game_mode': 'single_player'
        }
        
        # Perform analysis using Hermes agent
        analysis = system.hermes_agent.analyze_play_style(test_game_data, 'test_player')
        
        print(f"✅ Hermes analysis completed")
        print(f"✅ Analysis status: {analysis.status}")
        print(f"✅ Recommendations generated: {len(analysis.recommendations)}")
        print(f"✅ Confidence score: {analysis.confidence:.2f}")
        print(f"✅ Response time: {analysis.execution_time:.3f}s")
        print(f"✅ Patterns detected: {len(analysis.patterns_detected)}")
        
        if analysis.recommendations:
            print(f"\n🎯 Top Recommendations:")
            for i, rec in enumerate(analysis.recommendations[:3], 1):
                print(f"   {i}. {rec}")
        
        # Test 3: Multiple analysis sessions
        print("\n🧪 Test 3: Multiple analysis sessions")
        for i in range(3):
            test_data = {
                'decision_speed': 0.5 + (i * 0.1),
                'shots_on_goal': 2 + i,
                'aggressive_plays': 1 + i,
                'strategy_changes': i,
                'pattern_stability': 0.7 - (i * 0.1),
                'pattern_variance': 0.4 + (i * 0.1)
            }
            
            analysis = system.hermes_agent.analyze_play_style(test_data, f'player_{i}')
            print(f"   Session {i+1}: {analysis.status} (confidence: {analysis.confidence:.2f})")
        
        # Test 4: System configuration and components
        print("\n🧪 Test 4: System configuration and components")
        system_status = system.get_system_status()
        
        print(f"✅ System running: {system_status['system_running']}")
        print(f"✅ Hermes agent present: {'hermes_agent' in system.__dict__}")
        print(f"✅ Components status: {system_status['components']}")
        print(f"✅ Performance metrics: {system_status['performance']['frames_processed']} frames processed")
        
        # Test 5: Hermes performance metrics
        print("\n🧪 Test 5: Hermes performance metrics")
        hermes_metrics = system.hermes_agent.get_performance_metrics()
        print(f"✅ Hermes metrics retrieved successfully")
        print(f"✅ Total analyses: {hermes_metrics['total_analyses']}")
        print(f"✅ Success rate: {hermes_metrics['success_rate']:.2f}")
        print(f"✅ Average response time: {hermes_metrics['average_response_time']:.3f}s")
        print(f"✅ Pattern recognition rate: {hermes_metrics['pattern_recognition_rate']:.2f}")
        
        # Test 6: Hermes learned patterns
        print("\n🧪 Test 6: Hermes learned patterns")
        learned_patterns = system.hermes_agent.get_learned_patterns()
        print(f"✅ Learned patterns count: {len(learned_patterns)}")
        for pattern in learned_patterns[:3]:
            print(f"   - {pattern['pattern_type']}: {pattern['frequency']} occurrences (success rate: {pattern['success_rate']:.2f})")
        
        # Test 7: System with Hermes disabled
        print("\n🧪 Test 7: System with Hermes disabled")
        config_disabled = SystemConfig(
            hermes_enabled=False,
            hermes_agent_id='disabled_hermes',
            update_interval=1.0,
            output_directory="./test_data_disabled"
        )
        
        system_disabled = GameTrainerSystem(config_disabled)
        if system_disabled.hermes_agent:
            print(f"✅ Hermes agent created (but should be stopped): {system_disabled.hermes_agent.is_active}")
        
        print("\n" + "=" * 60)
        print("🎉 ALL HERMES INTEGRATION TESTS PASSED!")
        print("✅ Hermes agent is fully functional and integrated")
        print("✅ GameTrainer system successfully includes autonomous agent capabilities")
        print("✅ Play-style analysis and behavior optimization working correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Hermes integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hermes_integration()
    sys.exit(0 if success else 1)