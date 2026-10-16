"""
Behavior Replay Engine for playing as the person based on play-style profiles.

This module provides the capability to simulate playing as a specific player
based on their behavioral profile, enabling users to experience gameplay
through the lens of their own play style or target opponents.
"""

import json
import numpy as np
import pygame
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import time
import math
import random
from dataclasses import dataclass
from enum import Enum
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReplayMode(Enum):
    REAL_PLAYER = "real_player"  # Replicate the actual player's behavior
    TARGET_PLAYER = "target_player"  # Simulate playing as a specific target
    HISTORICAL_PLAYER = "historical_player"  # Replay from historical data
    TRAINING_MODE = "training_mode"  # Optimized for training scenarios

class DecisionNode:
    """Represents a decision point in gameplay with associated patterns."""
    
    def __init__(self, timestamp: float, position: tuple, 
                 state: str, confidence: float, action: str = None):
        self.timestamp = timestamp
        self.position = position  # (x, y) normalized coordinates
        self.state = state
        self.confidence = confidence
        self.action = action
        self.potential_actions = []
        self.outcome_probability = {}
        self.context_features = {}
    
    def add_potential_action(self, action: str, probability: float):
        """Add a potential action with its probability."""
        self.potential_actions.append((action, probability))
        self.outcome_probability[action] = probability

class BehaviorTree:
    """Hierarchical decision-making tree for replay behavior."""
    
    def __init__(self, profile_data: Dict[str, Any]):
        self.profile_data = profile_data
        self.decision_tree = {}
        self.current_node = None
        self.replay_speed = 1.0
        self.adaptation_factor = 0.1
        
        self._build_decision_tree()
    
    def _build_decision_tree(self):
        """Build hierarchical decision tree from player profile."""
        # Extract behavioral patterns from profile
        movement = self.profile_data.get('movement_patterns', {})
        decisions = self.profile_data.get('decision_making', {})
        tactics = self.profile_data.get('tactical_preferences', {})
        
        # Build root nodes based on strategic preferences
        self.decision_tree = {
            'aggressive tendencies': self._create_aggressive_branch(movement, decisions),
            'defensive strategies': self._create_defensive_branch(movement, decisions),
            'tactical positioning': self._create_positioning_branch(tactics, decisions),
            'response_patterns': self._create_response_branch(decisions)
        }
    
    def _create_aggressive_branch(self, movement: Dict, decisions: Dict) -> Dict:
        """Create aggressive play style branch."""
        return {
            'weight': movement.get('average_movement_distance', 0.5),
            'decision_threshold': decisions.get('decision_pattern_score', 0.5),
            'actions': ['attack', 'push', 'charge', 'dive'],
            'trigger_conditions': {
                'distance_below': 0.3,
                'health_above': 0.7,
                'position_advantage': True
            }
        }
    
    def _create_defensive_branch(self, movement: Dict, decisions: Dict) -> Dict:
        """Create defensive play style branch."""
        return {
            'weight': 1.0 - movement.get('average_movement_distance', 0.5),
            'decision_threshold': 1.0 - decisions.get('decision_pattern_score', 0.5),
            'actions': ['defend', 'dodge', 'guard', 'counter'],
            'trigger_conditions': {
                'distance_above': 0.7,
                'health_below': 0.4,
                'position_disadvantage': True
            }
        }
    
    def _create_positioning_branch(self, tactics: Dict, decisions: Dict) -> Dict:
        """Create positioning-based branch."""
        preferred_zones = tactics.get('preferred_zones', {})
        if preferred_zones:
            dominant_zone = list(preferred_zones.keys())[0]
        else:
            dominant_zone = 'center'
        
        return {
            'dominant_zone': dominant_zone,
            'positional_weight': tactics.get('tactical_flexibility', 0.5),
            'actions': ['position', 'rotate', 'flank', 'center'],
            'trigger_conditions': {
                'zone_occupancy': 0.6,
                'team_coordination': True,
                'map_phase': 'middle_game'
            }
        }
    
    def _create_response_branch(self, decisions: Dict) -> Dict:
        """Create response pattern branch."""
        return {
            'adaptation_rate': decisions.get('adaptation_rate', 0.5),
            'pattern_recognition': decisions.get('decision_pattern_score', 0.5),
            'actions': ['react', 'counter', 'predict', 'exploit'],
            'trigger_conditions': {
                'opponent_action': True,
                'unexpected_input': True,
                'pressure_points': True
            }
        }
    
    def get_next_action(self, current_state: Dict[str, Any], game_context: Dict[str, Any]) -> Dict:
        """Get next action based on current state and game context."""
        # Calculate weighted scores for each branch
        branch_scores = {}
        
        for branch_name, branch_data in self.decision_tree.items():
            score = self._calculate_branch_score(branch_data, current_state, game_context)
            branch_scores[branch_name] = score
        
        # Select best branch
        selected_branch = max(branch_scores.items(), key=lambda x: x[1])
        
        # Get action from selected branch
        action_data = branch_data.copy()
        
        return {
            'action': self._select_action_from_branch(action_data),
            'confidence': selected_branch[1],
            'reasoning': f"Selected {selected_branch[0]} branch with score {selected_branch[1]:.2f}"
        }
    
    def _calculate_branch_score(self, branch_data: Dict, current_state: Dict, game_context: Dict) -> float:
        """Calculate score for a decision branch."""
        score = 0.0
        
        # Weight based on profile characteristics
        if 'weight' in branch_data:
            score += branch_data['weight'] * 0.4
        
        # Match current state to branch logic
        if 'trigger_conditions' in branch_data:
            trigger_score = self._evaluate_trigger_conditions(branch_data['trigger_conditions'], current_state, game_context)
            score += trigger_score * 0.3
        
        # Decision consistency from profile
        if 'decision_threshold' in branch_data:
            consistency_bonus = (1.0 - abs(0.5 - branch_data['decision_threshold'])) * 0.3
            score += consistency_bonus
        
        return min(score, 1.0)
    
    def _evaluate_trigger_conditions(self, conditions: Dict, current_state: Dict, game_context: Dict) -> float:
        """Evaluate if trigger conditions are met."""
        met_conditions = 0
        total_conditions = len(conditions)
        
        for condition_name, condition_value in conditions.items():
            if self._check_condition(condition_name, condition_value, current_state, game_context):
                met_conditions += 1
        
        return met_conditions / total_conditions if total_conditions > 0 else 0.0
    
    def _check_condition(self, condition_name: str, condition_value: Any, 
                        current_state: Dict, game_context: Dict) -> bool:
        """Check if a specific condition is met."""
        # Handle different condition types
        if condition_name.startswith('distance'):
            return self._check_distance_condition(condition_name, condition_value, current_state, game_context)
        elif condition_name.startswith('health'):
            return self._check_health_condition(condition_name, condition_value, current_state)
        elif condition_name.startswith('position'):
            return self._check_position_condition(condition_name, condition_value, current_state)
        elif condition_name.startswith('zone'):
            return self._check_zone_condition(condition_name, condition_value, current_state)
        elif condition_name.startswith('game'):
            return self._check_game_condition(condition_name, condition_value, game_context)
        
        return False
    
    def _check_distance_condition(self, condition_name: str, condition_value: Any, 
                                 current_state: Dict, game_context: Dict) -> bool:
        """Check distance-based conditions."""
        player_pos = current_state.get('position', (0.5, 0.5))
        opponent_pos = current_state.get('opponent_position', (0.5, 0.5))
        
        distance = math.sqrt((player_pos[0] - opponent_pos[0])**2 + 
                           (player_pos[1] - opponent_pos[1])**2)
        
        if 'below' in condition_name:
            return distance < condition_value
        elif 'above' in condition_name:
            return distance > condition_value
        return False
    
    def _check_health_condition(self, condition_name: str, condition_value: Any, 
                               current_state: Dict) -> bool:
        """Check health-based conditions."""
        player_health = current_state.get('player_health', 0.5)
        
        if 'above' in condition_name:
            return player_health > condition_value
        elif 'below' in condition_name:
            return player_health < condition_value
        return False
    
    def _check_position_condition(self, condition_name: str, condition_value: Any, 
                                 current_state: Dict) -> bool:
        """Check position-based conditions."""
        player_pos = current_state.get('position', (0.5, 0.5))
        
        if condition_name == 'center_zone':
            return abs(player_pos[0] - 0.5) < 0.2 and abs(player_pos[1] - 0.5) < 0.2
        return False
    
    def _check_zone_condition(self, condition_name: str, condition_value: Any, 
                             current_state: Dict) -> bool:
        """Check zone-based conditions."""
        player_pos = current_state.get('position', (0.5, 0.5))
        dominant_zone = self.decision_tree.get('tactical_positioning', {}).get('dominant_zone', 'center')
        
        zone_centers = {
            'top_left': (0.25, 0.25),
            'top_right': (0.75, 0.25),
            'bottom_left': (0.25, 0.75),
            'bottom_right': (0.75, 0.75),
            'center': (0.5, 0.5)
        }
        
        if dominant_zone in zone_centers:
            zone_center = zone_centers[dominant_zone]
            distance = math.sqrt((player_pos[0] - zone_center[0])**2 + 
                               (player_pos[1] - zone_center[1])**2)
            return distance < 0.3  # Within zone bounds
        
        return False
    
    def _check_game_condition(self, condition_name: str, condition_value: Any, 
                             game_context: Dict) -> bool:
        """Check game phase conditions."""
        game_phase = game_context.get('game_phase', 'middle_game')
        return game_phase == condition_value
    
    def _select_action_from_branch(self, branch_data: Dict) -> str:
        """Select action from branch data based on weighted probability."""
        actions = branch_data.get('actions', ['idle'])
        
        # Weight actions by profile characteristics
        if 'weight' in branch_data and branch_data['weight'] > 0.7:
            # Aggressive branch - prefer aggressive actions
            priority_actions = [a for a in actions if a in ['attack', 'charge', 'push']]
        elif 'weight' in branch_data and branch_data['weight'] < 0.3:
            # Defensive branch - prefer defensive actions
            priority_actions = [a for a in actions if a in ['defend', 'guard', 'dodge']]
        else:
            priority_actions = actions
        
        # Select action with some randomness for natural variation
        return random.choice(priority_actions)

class BehaviorReplay:
    """Main behavior replay system for playing as specific players."""
    
    def __init__(self, replay_mode: ReplayMode = ReplayMode.REAL_PLAYER):
        self.replay_mode = replay_mode
        self.current_profile = None
        self.decision_tree = None
        self.replay_history = deque(maxlen=1000)  # Store recent decisions
        self.adaptation_level = 0.5
        self.context_awareness = True
        
        # Initialize game state tracking
        self.game_state = {
            'position': (0.5, 0.5),
            'opponent_position': (0.5, 0.5),
            'player_health': 1.0,
            'opponent_health': 1.0,
            'game_phase': 'loading',
            'last_actions': [],
            'decision_patterns': []
        }
        
        # Performance tracking
        self.performance_metrics = {
            'accuracy': 0.0,
            'adaptation_score': 0.0,
            'decision_time_avg': 0.0,
            'action_success_rate': 0.0,
            'pattern_recognition': 0.0
        }
    
    def load_player_profile(self, profile_path: str = None, profile_data: Dict[str, Any] = None):
        """Load player profile from file or data."""
        if profile_path and Path(profile_path).exists():
            with open(profile_path, 'r') as f:
                self.current_profile = json.load(f)
        elif profile_data:
            self.current_profile = profile_data
        else:
            raise ValueError("Must provide either profile_path or profile_data")
        
        # Initialize decision tree
        self.decision_tree = BehaviorTree(self.current_profile)
        
        logger.info(f"Loaded player profile for replay mode: {self.replay_mode.value}")
        return self
    
    def update_game_state(self, new_state: Dict[str, Any]):
        """Update game state for replay decisions."""
        # Merge new state with existing
        self.game_state.update(new_state)
        
        # Update performance metrics based on new state
        self._update_performance_metrics()
    
    def make_decision(self, game_context: Dict[str, Any]) -> Dict:
        """Make decision based on loaded player profile."""
        if not self.current_profile:
            raise RuntimeError("No player profile loaded. Use load_player_profile() first.")
        
        start_time = time.time()
        
        # Get action from decision tree
        decision = self.decision_tree.get_next_action(self.game_state, game_context)
        
        # Apply adaptation if needed
        if self.adaptation_level > 0:
            decision = self._adapt_decision(decision, game_context)
        
        # Record decision
        self.replay_history.append({
            'timestamp': time.time(),
            'decision': decision,
            'game_state': self.game_state.copy(),
            'game_context': game_context.copy(),
            'decision_time': time.time() - start_time
        })
        
        return decision
    
    def _adapt_decision(self, decision: Dict, game_context: Dict) -> Dict:
        """Adapt decision based on current game context and adaptation level."""
        if self.adaptation_level <= 0:
            return decision
        
        # Apply adaptation logic based on adaptation level
        adapted_action = decision['action']
        
        # Example adaptation: if in learning phase, add some randomness
        if random.random() < self.adaptation_level * 0.5:
            # Introduce slight variation for learning
            alternative_actions = [a for a in self.current_profile.get('available_actions', ['idle']) 
                                 if a != adapted_action]
            if alternative_actions:
                adapted_action = random.choice(alternative_actions)
        
        return {
            'action': adapted_action,
            'confidence': decision['confidence'] * (1 - self.adaptation_level * 0.2),
            'reasoning': f"Adapted decision with adaptation level {self.adaptation_level}"
        }
    
    def _update_performance_metrics(self):
        """Update performance metrics based on recent decisions."""
        if not self.replay_history:
            return
        
        # Calculate metrics from recent history
        recent_decisions = list(self.replay_history)[-10:]  # Last 10 decisions
        
        if recent_decisions:
            avg_decision_time = np.mean([d['decision_time'] for d in recent_decisions])
            self.performance_metrics['decision_time_avg'] = avg_decision_time
            
            # Calculate accuracy based on action success (placeholder)
            success_rate = random.uniform(0.6, 0.9)  # Would be calculated based on actual game outcomes
            self.performance_metrics['action_success_rate'] = success_rate
            
            # Pattern recognition from decision consistency
            actions = [d['decision']['action'] for d in recent_decisions]
            consistency = max(Counter(actions).values()) / len(actions) if actions else 0.5
            self.performance_metrics['pattern_recognition'] = consistency
    
    def enable_context_awareness(self, enabled: bool = True):
        """Enable or disable context awareness in replay."""
        self.context_awareness = enabled
        logger.info(f"Context awareness {'enabled' if enabled else 'disabled'}")
    
    def set_adaptation_level(self, level: float):
        """Set adaptation level (0.0 to 1.0)."""
        self.adaptation_level = max(0.0, min(1.0, level))
        logger.info(f"Adaptation level set to {self.adaptation_level}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report based on replay history."""
        if not self.replay_history:
            return {'status': 'no_data', 'message': 'No replay decisions recorded yet'}
        
        recent_decisions = list(self.replay_history)[-50:]  # Last 50 decisions
        
        report = {
            'replay_summary': {
                'total_decisions': len(self.replay_history),
                'recent_decisions': len(recent_decisions),
                'replay_mode': self.replay_mode.value,
                'adaptation_level': self.adaptation_level
            },
            'performance_metrics': self.performance_metrics.copy(),
            'action_distribution': self._get_action_distribution(recent_decisions),
            'pattern_analysis': self._analyze_decision_patterns(recent_decisions),
            'recommendations': self._generate_recommendations(recent_decisions)
        }
        
        return report
    
    def _get_action_distribution(self, decisions: List[Dict]) -> Dict:
        """Get distribution of actions taken."""
        action_counts = Counter()
        for decision in decisions:
            action_counts[decision['decision']['action']] += 1
        
        total = len(decisions)
        return {action: count / total for action, count in action_counts.items()}
    
    def _analyze_decision_patterns(self, decisions: List[Dict]) -> Dict:
        """Analyze patterns in decision-making."""
        if not decisions:
            return {}
        
        action_sequence = [d['decision']['action'] for d in decisions]
        
        # Analyze patterns
        patterns = {
            'most_frequent_action': Counter(action_sequence).most_common(1)[0][0],
            'action_variance': len(set(action_sequence)) / len(action_sequence),
            'decision_consistency': max(Counter(action_sequence).values()) / len(action_sequence),
            'adaptation_speed': self._calculate_adaptation_speed(decisions)
        }
        
        return patterns
    
    def _calculate_adaptation_speed(self, decisions: List[Dict]) -> float:
        """Calculate how quickly behavior adapts."""
        if len(decisions) < 3:
            return 0.0
        
        # Simple adaptation measure: change in action frequency over time
        action_changes = 0
        for i in range(1, len(decisions)):
            if decisions[i]['decision']['action'] != decisions[i-1]['decision']['action']:
                action_changes += 1
        
        return action_changes / (len(decisions) - 1)
    
    def _generate_recommendations(self, decisions: List[Dict]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if not decisions:
            return recommendations
        
        action_dist = self._get_action_distribution(decisions)
        
        # Generate recommendations based on patterns
        most_frequent = max(action_dist.items(), key=lambda x: x[1])
        if most_frequent[1] > 0.7:
            recommendations.append(f"Focus on diversifying away from frequent action: {most_frequent[0]}")
        
        consistency = self._analyze_decision_patterns(decisions).get('decision_consistency', 0)
        if consistency < 0.6:
            recommendations.append("Work on decision consistency to improve predictability")
        
        adaptation = self._analyze_decision_patterns(decisions).get('adaptation_speed', 0)
        if adaptation < 0.1:
            recommendations.append("Increase behavioral adaptation for better responsiveness")
        
        return recommendations


def create_behavior_replay(replay_mode: ReplayMode = ReplayMode.REAL_PLAYER, 
                          profile_path: str = None) -> BehaviorReplay:
    """Create a new behavior replay system."""
    replay = BehaviorReplay(replay_mode)
    
    if profile_path:
        replay.load_player_profile(profile_path)
    
    return replay


def main():
    """Example usage of Behavior Replay system."""
    print("Initializing Behavior Replay system...")
    
    # Create replay system
    replay = create_behavior_replay()
    
    # Load sample player profile
    sample_profile = {
        'profile_id': 'demo_player_001',
        'movement_patterns': {
            'average_movement_distance': 0.6,
            'maximum_movement_distance': 0.9,
            'direction_changes': 15
        },
        'decision_making': {
            'animation_consistency': 0.8,
            'action_consistency': 0.7,
            'adaptation_rate': 0.3
        },
        'tactical_preferences': {
            'preferred_zones': ['bottom_right', 'top_right'],
            'tactical_flexibility': 0.6
        },
        'physical_attributes': {
            'average_speed': 0.5,
            'agility_score': 0.7
        },
        'psychological_profile': {
            'risk_tolerance': 0.7,
            'adaptability_score': 0.6
        }
    }
    
    # Load profile
    replay.load_player_profile(profile_data=sample_profile)
    
    # Simulate gameplay
    print("Simulating gameplay decisions...")
    game_context = {
        'game_phase': 'middle_game',
        'match_time': 45.0,
        'score_difference': 0,
        'map_control': 'balanced'
    }
    
    for i in range(10):
        # Update game state with realistic variations
        current_state = {
            'position': (random.uniform(0.3, 0.7), random.uniform(0.3, 0.7)),
            'opponent_position': (random.uniform(0.3, 0.7), random.uniform(0.3, 0.7)),
            'player_health': random.uniform(0.5, 1.0),
            'game_phase': random.choice(['early_game', 'middle_game', 'late_game'])
        }
        
        replay.update_game_state(current_state)
        decision = replay.make_decision(game_context)
        
        print(f"Decision {i+1}: Action={decision['action']}, Confidence={decision['confidence']:.2f}")
    
    # Generate performance report
    print("\nGenerating performance report...")
    report = replay.get_performance_report()
    print(f"Total decisions made: {report['replay_summary']['total_decisions']}")
    print(f"Most frequent action: {report['action_distribution']}")
    print(f"Recommendations: {report['recommendations']}")

if __name__ == "__main__":
    main()