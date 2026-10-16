#!/usr/bin/env python3
"""
Integration Manager for GameTrainer System.

This module coordinates all components of the GameTrainer system,
providing a unified interface for real-time gameplay tracking,
analysis, and simulation.
"""

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import system components - using absolute imports to avoid circular import issues
try:
    import capture
    import analyzer
    import simulator
    import player_profiler
    import behavior_replay
    import usage_analytics
    print("✅ All system components imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This may be due to missing dependencies like OpenCV")
    raise

# Hermes integration support
try:
    import hermes_agent
    print("✅ Hermes agent imported successfully")
except ImportError as e:
    print(f"❌ Hermes agent import error: {e}")
    raise

@dataclass
class SystemConfig:
    """System configuration for GameTrainer."""
    capture_device_index: int = 0
    output_directory: str = "./data"
    profile_database: str = "./data/gameplay.db"
    analytics_enabled: bool = True
    auto_save_profiles: bool = True
    replay_mode: str = "real_player"
    update_interval: float = 1.0  # seconds
    max_memory_usage: int = 1000  # MB
    hermes_enabled: bool = True
    hermes_agent_id: str = "hermes_gametrainer"
    hermes_learning_rate: float = 0.1
    hermes_confidence_threshold: float = 0.7
    hermes_pattern_monitoring: bool = True
    hermes_auto_replay: bool = True
    max_memory_usage: int = 1000  # MB

class GameTrainerSystem:
    """Main GameTrainer system that integrates all components."""

    def __init__(self, config: SystemConfig = None):
        self.config = config or SystemConfig()
        self.config.output_directory = Path(self.config.output_directory)
        self.config.output_directory.mkdir(exist_ok=True)

        # Initialize components
        self.capture = None
        self.analyzer = None
        self.simulator = None
        self.player_profiler = None
        self.behavior_replay = None
        self.analytics = None
        self.hermes_agent = None  # Hermes autonomous agent

        # System state
        self.is_running = False
        self.current_session_id = None
        self.session_start_time = None
        self.session_data = {}
        self.threads = []

        # Performance tracking
        self.performance_metrics = {
            'frames_processed': 0,
            'detection_rate': 0.0,
            'average_fps': 0.0,
            'system_health': 'healthy'
        }

        # Initialize components
        self._initialize_components()

        logger.info("GameTrainer system initialized successfully")

    def _initialize_components(self):
        """Initialize all system components."""
        try:
            # Initialize capture system
            self.capture = capture.GameCapture(
                device_index=self.config.capture_device_index,
                output_dir=str(self.config.output_directory)
            )

            # Initialize analyzer
            self.analyzer = analyzer.OpponentAnalyzer(str(self.config.profile_database))

            # Initialize analytics
            self.analytics = usage_analytics.create_analytics_engine(str(self.config.profile_database))

            # Initialize behavior replay
            from behavior_replay import ReplayMode
            replay_mode = ReplayMode(self.config.replay_mode)
            self.behavior_replay = behavior_replay.create_behavior_replay(replay_mode)

            # Initialize Hermes autonomous agent
            self.hermes_agent = hermes_agent.HermesAgent(
                agent_id="hermes_gametrainer",
                config={
                    'update_interval': self.config.update_interval,
                    'max_patterns': 100,
                    'confidence_threshold': self.config.hermes_confidence_threshold,
                    'learning_rate': self.config.hermes_learning_rate,
                    'min_pattern_frequency': 5,
                    'auto_analyze': True,
                    'generate_recommendations': True,
                    'continuous_learning': True,
                    'pattern_matching_enabled': self.config.hermes_pattern_monitoring,
                    'behavior_clustering': True,
                    'anomaly_detection': True
                }
            )
            
            # Start Hermes agent if enabled
            if self.config.hermes_enabled:
                self.hermes_agent.start_agent()
                logger.info("Hermes Agent started and monitoring gameplay patterns")

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    # The rest of the GameTrainerSystem methods would continue here...
    # For debugging purposes, I'll focus on the core Hermes integration
    
    def test_hermes_integration(self):
        """Test Hermes agent integration."""
        print("Testing Hermes Agent Integration...")
        
        # Check if Hermes agent is initialized
        if not self.hermes_agent:
            print("❌ Hermes agent not initialized")
            return False
        
        print(f"✅ Hermes agent initialized: {self.hermes_agent.agent_id}")
        print(f"✅ Hermes agent status: {self.hermes_agent.is_active}")
        
        # Test basic analysis
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
        
        try:
            analysis = self.hermes_agent.analyze_play_style(test_game_data, 'test_player')
            print(f"✅ Hermes analysis completed: {analysis.status}")
            print(f"✅ Recommendations: {len(analysis.recommendations)}")
            print(f"✅ Confidence: {analysis.confidence:.2f}")
            
            if analysis.recommendations:
                print(f"✅ Sample recommendation: {analysis.recommendations[0][:50]}...")
            
            return True
        except Exception as e:
            print(f"❌ Hermes analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_system_status(self):
        """Get current system status."""
        return {
            'system_running': self.is_running,
            'current_session': self.current_session_id,
            'components': {
                'capture': self.capture is not None,
                'analyzer': self.analyzer is not None,
                'simulator': self.simulator is not None,
                'player_profiler': self.player_profiler is not None,
                'behavior_replay': self.behavior_replay is not None,
                'analytics': self.analytics is not None,
                'hermes_agent': self.hermes_agent is not None
            },
            'performance': self.performance_metrics
        }

    def start_capture(self, roi_coords=None):
        """Start video capture with optional ROI."""
        if roi_coords is not None:
            self.capture.set_roi(*roi_coords)
        return self.capture.start_capture()

    def start_real_time_monitoring(self):
        """Start real-time monitoring of gameplay."""
        self.is_running = True
        # In a full implementation, we would start a background thread here
        logger.info("Real-time monitoring started")

    def process_frame(self, frame_number, game_data):
        """Process a single frame of gameplay data."""
        try:
            # Capture frame
            frame = self.capture.read_frame()
            if frame is None:
                return {'success': False, 'error': 'Failed to capture frame'}

            # Extract ROI if set
            roi_frame = self.capture.extract_roi(frame)
            if roi_frame is None:
                roi_frame = frame

            # Analyze opponent position
            opponent_data = self.analyzer.analyze_frame(roi_frame)

            # Update game state
            self.player_profiler.update_game_state(game_data)

            # Update behavior replay
            if self.behavior_replay:
                self.behavior_replay.add_frame(frame_number, opponent_data, game_data)

            # Update analytics
            if self.analytics:
                self.analytics.update_frame(frame_number, game_data, opponent_data)

            # Update Hermes agent
            if self.hermes_agent and self.config.hermes_enabled:
                self.hermes_agent.analyze_play_style(game_data, f"frame_{frame_number}")

            # Update performance metrics
            self.performance_metrics['frames_processed'] += 1

            return {
                'success': True,
                'processing_time': 0.01,  # placeholder
                'frame_number': frame_number,
                'opponent_data': opponent_data,
                'game_data': game_data
            }
        except Exception as e:
            logger.error(f"Error processing frame {frame_number}: {e}")
            return {'success': False, 'error': str(e)}

    def stop_real_time_monitoring(self):
        """Stop real-time monitoring."""
        self.is_running = False
        logger.info("Real-time monitoring stopped")

    def stop_capture(self):
        """Stop video capture."""
        if self.capture:
            self.capture.stop_capture()
        logger.info("Capture stopped")

    def create_player_profile(self, player_id):
        """Create a player profile for the given player ID."""
        if not hasattr(self, 'player_profiler') or self.player_profiler is None:
            from player_profiler import PlayerProfiler
            self.player_profiler = PlayerProfiler(str(self.config.profile_database))
        return self.player_profiler.create_profile(player_id)

    def generate_analytics_report(self, report_type='daily'):
        """Generate an analytics report."""
        if not self.analytics:
            from usage_analytics import create_analytics_engine
            self.analytics = create_analytics_engine(str(self.config.profile_database))
        return self.analytics.generate_report(report_type)

    def generate_behavior_replay(self):
        """Generate a behavior replay."""
        if not self.behavior_replay:
            from behavior_replay import create_behavior_replay, ReplayMode
            replay_mode = ReplayMode(self.config.replay_mode)
            self.behavior_replay = create_behavior_replay(replay_mode)
        return self.behavior_replay.generate_replay()

    def export_system_data(self, format='json'):
        """Export system data to a file."""
        export_dir = self.config.output_directory / 'exports'
        export_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        export_path = export_dir / f"system_export_{timestamp}.{format}"

        # Collect data from components
        data = {
            'timestamp': timestamp,
            'config': asdict(self.config),
            'performance_metrics': self.performance_metrics,
            'session_id': self.current_session_id,
            'session_start_time': self.session_start_time
        }

        # Add component-specific data if available
        if self.player_profiler:
            data['player_profiles'] = self.player_profiler.get_all_profiles()
        if self.analytics:
            data['analytics'] = self.analytics.get_summary()
        if self.behavior_replay:
            data['replays'] = self.behavior_replay.get_replay_list()

        # Export based on format
        if format == 'json':
            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            # For other formats, we could add support, but default to JSON
            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)

        logger.info(f"System data exported to {export_path}")
        return str(export_path)

    def stop_session(self):
        """Stop the current session."""
        self.is_running = False
        if self.current_session_id:
            logger.info(f"Stopped session {self.current_session_id}")
        self.current_session_id = None
        self.session_start_time = None

    def start_session(self):
        """Start a new session."""
        self.current_session_id = f"session_{int(time.time())}"
        self.session_start_time = time.time()
        self.is_running = True
        logger.info(f"Started session {self.current_session_id}")
        return self.current_session_id

    def run_complete_pipeline(self, frames_to_process, roi_coords):
        """Run a complete processing pipeline for a given number of frames."""
        try:
            # Start capture with ROI
            fps, width, height = self.start_capture(roi_coords)
            # Start real-time monitoring
            self.start_real_time_monitoring()

            # Process frames
            for i in range(frames_to_process):
                game_data = {
                    'player_health': 100 - (i * 2),
                    'current_animation': 'idle' if i % 3 == 0 else 'moving',
                    'action_state': 'standing' if i % 4 != 0 else 'jumping',
                    'level': f'level_{i//3 + 1}',
                    'game_mode': 'single_player' if i % 2 == 0 else 'multiplayer'
                }
                result = self.process_frame(i, game_data)
                if not result['success']:
                    logger.warning(f"Frame {i} processing failed: {result.get('error')}")

            # Stop monitoring and capture
            self.stop_real_time_monitoring()
            self.stop_capture()

            # Create player profile
            profile = self.create_player_profile("pipeline_player")

            # Generate analytics report
            analytics_report = self.generate_analytics_report('pipeline')

            # Generate behavior replay
            replay_success = self.generate_behavior_replay()

            # Export system data
            export_path = self.export_system_data()

            # Stop session
            self.stop_session()

            return {
                'status': 'success',
                'session_id': self.current_session_id,
                'export_path': export_path,
                'frames_processed': frames_to_process,
                'fps': fps,
                'width': width,
                'height': height
            }
        except Exception as e:
            logger.error(f"Error in run_complete_pipeline: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
# Create convenience function

def create_game_trainer_system(config: SystemConfig = None) -> GameTrainerSystem:
    """Create and configure GameTrainer system."""
    return GameTrainerSystem(config)

# Example usage for testing
if __name__ == "__main__":
    # Test Hermes integration
    config = SystemConfig(
        hermes_enabled=True,
        hermes_agent_id='test_hermes',
        update_interval=0.1,
        capture_device_index=0,
        output_directory="./test_data"
    )
    
    system = create_game_trainer_system(config)
    success = system.test_hermes_integration()
    
    if success:
        print("\n🎉 Hermes integration test PASSED!")
    else:
        print("\n❌ Hermes integration test FAILED!")
        exit(1)