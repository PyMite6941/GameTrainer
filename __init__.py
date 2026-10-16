"""
GameTrainer - Real-time Gameplay Tracking and Play-Style Based Simulation

A comprehensive Python-based pipeline for:
- Real-time video capture and opponent tracking
- Advanced behavioral analysis and profiling
- Play-style based simulation and training
- Real-time analytics and reporting
- Integration with autonomous agents (Hermes)

Main Components:
- capture.py: Video capture with SQLite logging
- analyzer.py: Opponent behavior analysis and profile generation
- simulator.py: Pygame-based training simulator
- player_profiler.py: Player profiling system
- behavior_replay.py: Behavior replay engine
- usage_analytics.py: Analytics dashboard and reporting
- integration_manager.py: System integration and coordination

Usage:
    python -m gametracer                # Run basic example
    python main.py                      # Run complete system demo
"""

__version__ = "1.0.0"
__author__ = "GameTrainer Team"

from .capture import GameCapture
from .analyzer import OpponentAnalyzer
from .simulator import TrainingSimulator
from .player_profiler import PlayStyleProfile, create_player_profile
from .behavior_replay import BehaviorReplay, create_behavior_replay, ReplayMode
from .usage_analytics import AnalyticsEngine, create_analytics_engine, AnalyticsDashboard
from .integration_manager import GameTrainerSystem, create_game_trainer_system, SystemConfig

__all__ = [
    'GameCapture',
    'OpponentAnalyzer', 
    'TrainingSimulator',
    'PlayStyleProfile',
    'create_player_profile',
    'BehaviorReplay',
    'create_behavior_replay',
    'ReplayMode',
    'AnalyticsEngine',
    'create_analytics_engine',
    'AnalyticsDashboard',
    'GameTrainerSystem',
    'create_game_trainer_system',
    'SystemConfig'
]