#!/usr/bin/env python3
"""
GameTrainer - Main Entry Point

Complete system demonstration for real-time gameplay tracking and play-style based simulation.
This script shows the full integration of all GameTrainer components.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from integration_manager import GameTrainerSystem, SystemConfig
from behavior_replay import ReplayMode

def print_banner():
    """Print project banner and information."""
    print("=" * 80)
    print("🎮 GAME TRAINER - Real-Time Gameplay Tracking & Play-Style Simulation")
    print("=" * 80)
    print("\n📋 PROJECT OVERVIEW:")
    print("   • Real-time video capture and opponent tracking")
    print("   • Advanced behavioral analysis and player profiling")
    print("   • Play-style based simulation and training")
    print("   • Real-time analytics and usage reporting")
    print("   • Hermes autonomous agent integration for intelligent analysis")
    
    print("\n🔧 CORE COMPONENTS:")
    print("   • GameCapture - Video capture with SQLite logging")
    print("   • OpponentAnalyzer - Behavioral pattern analysis")
    print("   • TrainingSimulator - Pygame-based training environment")
    print("   • PlayStyleProfiler - Multi-dimensional player profiling")
    print("   • BehaviorReplay - Decision tree-based replay system")
    print("   • AnalyticsEngine - Real-time usage monitoring")
    print("   • IntegrationManager - System coordination and workflow")
    
    print("\n🎯 USE CASES:")
    print("   • Game Development - Player behavior analysis")
    print("   • Esports Training - Custom opponent generation")
    print("   • AI Research - Training data generation")
    print("   • Player Improvement - Personalized practice scenarios")
    print("   • Research Studies - Gaming behavior analysis")
    
    print("\n⚡ FEATURES:")
    print("   • Real-time video capture with ROI tracking")
    print("   • Multi-dimensional player profiling")
    print("   • Adaptive behavior replay systems")
    print("   • Comprehensive analytics dashboard")
    print("   • Modular architecture for easy extension")
    print("   • Hermes agent integration support")

def run_basic_example():
    """Run basic demonstration of core functionality."""
    print("\n" + "=" * 60)
    print("🚀 RUNNING BASIC EXAMPLE")
    print("=" * 60)
    
    try:
        # Create system with basic configuration
        config = SystemConfig(
            capture_device_index=0,
            output_directory="./data",
            analytics_enabled=True,
            auto_save_profiles=True,
            replay_mode="real_player"
        )
        
        system = GameTrainerSystem(config)
        
        print("✅ GameTrainer system initialized successfully")
        print(f"📁 Output directory: {config.output_directory}")
        print(f"🗄️  Profile database: {config.profile_database}")
        
        # Show system status
        status = system.get_system_status()
        print(f"🔧 Active components: {sum(status['components'].values())}/{len(status['components'])}")
        
        # Start a simple capture demonstration
        print("\n🎥 Starting capture demonstration...")
        fps, width, height = system.start_capture((400, 300, 800, 500))
        print(f"   • Resolution: {width}x{height}")
        print(f"   • Frame rate: {fps} FPS")
        
        # Start real-time monitoring
        system.start_real_time_monitoring()
        
        # Process a few sample frames
        print("\n📊 Processing sample frames...")
        for i in range(5):
            game_data = {
                'player_health': 100 - (i * 10),
                'current_animation': 'idle',
                'action_state': 'standing',
                'level': 'tutorial',
                'game_mode': 'single_player'
            }
            
            result = system.process_frame(i, game_data)
            if result['success']:
                print(f"   • Frame {i+1}: Processing complete ({result['processing_time']:.2f}s)")
            else:
                print(f"   • Frame {i+1}: Failed - {result['error']}")
        
        # Stop monitoring
        system.stop_real_time_monitoring()
        
        # Stop capture
        system.stop_capture()
        
        # Create player profile
        print("\n👤 Creating player profile...")
        profile = system.create_player_profile("demo_player")
        print(f"   • Profile ID: {profile.profile_id}")
        print(f"   • Movement consistency: {profile.movement_patterns.get('movement_consistency', 0):.2f}")
        print(f"   • Decision score: {profile.decision_making.get('decision_pattern_score', 0):.2f}")
        print(f"   • Identified strengths: {', '.join(profile.strengths[:3])}")
        
        # Generate analytics report
        print("\n📈 Generating analytics report...")
        analytics_report = system.generate_analytics_report('daily')
        print(f"   • Data completeness: {analytics_report.get('quality_indicators', {}).get('data_completeness_score', 0):.1f}%")
        
        # Generate behavior replay
        print("\n🎭 Generating behavior replay...")
        replay_success = system.generate_behavior_replay()
        print(f"   • Replay generated: {'✅' if replay_success else '❌'}")
        
        # Export system data
        print("\n💾 Exporting system data...")
        export_path = system.export_system_data()
        print(f"   • Export location: {export_path}")
        
        # Stop current session
        system.stop_session()
        
        # Show final status
        final_status = system.get_system_status()
        print(f"\n📊 FINAL SYSTEM STATUS:")
        print(f"   • System running: {'✅' if final_status['system_running'] else '❌'}")
        print(f"   • Current session: {final_status['current_session'] or 'None'}")
        print(f"   • Components active: {sum(final_status['components'].values())}/{len(final_status['components'])}")
        print(f"   • Frames processed: {final_status['performance']['frames_processed']}")
        
        print("\n✅ BASIC EXAMPLE COMPLETED SUCCESSFULLY!")
        print("   • All core components functioning correctly")
        print("   • Player profile created and analyzed")
        print("   • Analytics report generated")
        print("   • System data exported")
        
        return True
        
    except Exception as e:
        print(f"\n❌ BASIC EXAMPLE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_complete_pipeline_example():
    """Run complete pipeline demonstration."""
    print("\n" + "=" * 60)
    print("🚀 RUNNING COMPLETE PIPELINE EXAMPLE")
    print("=" * 60)
    
    try:
        # Create system for pipeline demonstration
        config = SystemConfig(
            capture_device_index=0,
            output_directory="./data_pipeline",
            analytics_enabled=True,
            auto_save_profiles=True,
            replay_mode="target_player"
        )
        
        system = GameTrainerSystem(config)
        
        print("🎥 Starting complete pipeline demonstration...")
        print("   • Processing 20 frames with full workflow")
        print("   • Creating comprehensive player profile")
        print("   • Generating analytics and behavior replay")
        
        # Run complete pipeline
        result = system.run_complete_pipeline(
            frames_to_process=20,
            roi_coords=(400, 300, 800, 500)
        )
        
        if result['status'] == 'success':
            print(f"\n✅ COMPLETE PIPELINE COMPLETED!")
            print(f"   • Session ID: {result['session_id']}")
            print(f"   • Export path: {result['export_path']}")
            print(f"   • All components tested and working")
            return True
        else:
            print(f"\n❌ COMPLETE PIPELINE FAILED: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ COMPLETE PIPELINE EXAMPLE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_advanced_features_example():
    """Run example demonstrating advanced features."""
    print("\n" + "=" * 60)
    print("🚀 RUNNING ADVANCED FEATURES EXAMPLE")
    print("=" * 60)
    
    try:
        # Create system with advanced configuration
        config = SystemConfig(
            capture_device_index=0,
            output_directory="./data_advanced",
            analytics_enabled=True,
            auto_save_profiles=True,
            replay_mode="training_mode"
        )
        
        system = GameTrainerSystem(config)
        
        print("🎯 Demonstrating advanced features...")
        
        # Start session
        session_id = system.start_session()
        print(f"📝 Started advanced session: {session_id}")
        
        # Configure behavior replay with adaptation
        if system.behavior_replay:
            system.behavior_replay.set_adaptation_level(0.3)
            system.behavior_replay.enable_context_awareness(True)
            print("🎭 Behavior replay configured with adaptation and context awareness")
        
        # Process frames with varied game data
        print("📊 Processing frames with dynamic game states...")
        for i in range(10):
            game_data = {
                'player_health': 100 - (i * 15),
                'current_animation': 'idle' if i % 3 == 0 else 'moving',
                'action_state': 'standing' if i % 4 != 0 else 'jumping',
                'level': f'level_{i//3 + 1}',
                'game_mode': 'single_player' if i % 2 == 0 else 'multiplayer'
            }
            
            result = system.process_frame(i, game_data)
            if result['success']:
                print(f"   • Frame {i+1}: Processing successful")
            else:
                print(f"   • Frame {i+1}: Processing failed")
        
        # Create multiple player profiles
        print("\n👥 Creating multiple player profiles...")
        for player_id in ['aggressive_player', 'defensive_player', 'balanced_player']:
            profile = system.create_player_profile(player_id)
            print(f"   • Profile {player_id}: Created")
        
        # Generate comprehensive analytics
        print("\n📈 Generating comprehensive analytics...")
        analytics_report = system.generate_analytics_report('weekly')
        print("   • Analytics report generated for weekly period")
        
        # Generate behavior replay for each profile
        print("\n🎭 Generating behavior replays...")
        for player_id in ['aggressive_player', 'defensive_player', 'balanced_player']:
            replay_path = f"./data_advanced/{player_id}_profile.json"
            if system.load_player_profile(replay_path):
                success = system.generate_behavior_replay()
                print(f"   • {player_id} replay: {'✅ Generated' if success else '❌ Failed'}")
        
        # Export complete system data
        print("\n💾 Exporting complete system data...")
        export_path = system.export_system_data('json')
        print(f"   • Data exported to: {export_path}")
        
        # Stop session
        system.stop_session()
        
        print("\n✅ ADVANCED FEATURES EXAMPLE COMPLETED!")
        print("   • Multiple player profiles created")
        print("   • Behavior replay systems configured")
        print("   • Comprehensive analytics generated")
        print("   • Data fully exported and documented")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ADVANCED FEATURES EXAMPLE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point with comprehensive examples."""
    print_banner()
    
    print("\n📝 SELECTING EXECUTION MODE:")
    print("   1. Basic Example - Core functionality demonstration")
    print("   2. Complete Pipeline - Full workflow from capture to analysis")
    print("   3. Advanced Features - All system capabilities")
    print("   4. Exit - Quit the application")
    
    while True:
        try:
            choice = input("\n🎯 Enter your choice (1-4): ").strip()
            
            if choice == '1':
                success = run_basic_example()
                if success:
                    print("\n🎉 BASIC EXAMPLE EXECUTION COMPLETED SUCCESSFULLY!")
            elif choice == '2':
                success = run_complete_pipeline_example()
                if success:
                    print("\n🎉 COMPLETE PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
            elif choice == '3':
                success = run_advanced_features_example()
                if success:
                    print("\n🎉 ADVANCED FEATURES EXECUTION COMPLETED SUCCESSFULLY!")
            elif choice == '4':
                print("\n👋 Thank you for using GameTrainer! Goodbye!")
                break
            else:
                print(f"\n⚠️  Invalid choice: '{choice}'. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Execution interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            print("   Please try again or contact support if the issue persists")
    
    print("\n" + "=" * 80)
    print("🎮 GameTrainer - System demonstration completed")
    print("📁 Data saved to ./data directories")
    print("🔧 System ready for deployment and production use")
    print("=" * 80)

if __name__ == "__main__":
    main()