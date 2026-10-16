"""
Player Profiler for analyzing gameplay patterns and creating play-style profiles.

This module analyzes gameplay data to create detailed player profiles that can be used
for behavior replay, training, and play-style based simulation.
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import time
from collections import defaultdict, Counter
import math
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlayStyleProfile:
    """Comprehensive player profile based on gameplay analysis."""
    
    def __init__(self, profile_id: str, data_source: str = "./data/gameplay.db"):
        self.profile_id = profile_id
        self.data_source = Path(data_source)
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # Core play style attributes
        self.movement_patterns = {}
        self.decision_making = {}
        self.tactical_preferences = {}
        self.physical_attributes = {}
        self.psychological_profile = {}
        
        # Performance metrics
        self.performance_metrics = {}
        self.weaknesses = []
        self.strengths = []
        
        # Behavioral fingerprints
        self.behavioral_signatures = {}
        self.response_patterns = {}
        self.pressure_handling = {}
    
    def analyze_database(self, conn: sqlite3.Connection) -> 'PlayStyleProfile':
        """Analyze database to create comprehensive player profile."""
        logger.info(f"Analyzing gameplay data for profile {self.profile_id}")
        
        # Get gameplay data
        frames_data = self._get_frames_data(conn)
        game_states_data = self._get_game_states_data(conn)
        
        if not frames_data:
            logger.warning("No frame data available for analysis")
            return self
        
        # Analyze different aspects of play style
        self._analyze_movement_style(frames_data)
        self._analyze_decision_patterns(frames_data, game_states_data)
        self._analyze_tactical_preferences(frames_data, game_states_data)
        self._analyze_physical_attributes(frames_data)
        self._analyze_psychological_profile(frames_data, game_states_data)
        self._analyze_performance_metrics(frames_data, game_states_data)
        self._identify_strengths_weaknesses(frames_data)
        
        return self
    
    def _get_frames_data(self, conn: sqlite3.Connection) -> List[Dict]:
        """Extract and normalize frame data."""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                timestamp, frame_number, opponent_x, opponent_y, opponent_state,
                roi_x, roi_y, roi_width, roi_height
            FROM frames 
            WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL
            ORDER BY timestamp
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        frames = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Normalize coordinates to 0-1 scale
        if frames:
            max_x = max(f['opponent_x'] for f in frames if f['opponent_x'] is not None)
            max_y = max(f['opponent_y'] for f in frames if f['opponent_y'] is not None)
            
            for frame in frames:
                if frame['opponent_x'] is not None:
                    frame['norm_x'] = frame['opponent_x'] / max_x if max_x > 0 else 0
                if frame['opponent_y'] is not None:
                    frame['norm_y'] = frame['opponent_y'] / max_y if max_y > 0 else 0
        
        return frames
    
    def _get_game_states_data(self, conn: sqlite3.Connection) -> List[Dict]:
        """Extract game states data."""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, player_health, current_animation, 
                   action_state, level, game_mode
            FROM game_states
            ORDER BY timestamp
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def _analyze_movement_style(self, frames: List[Dict]):
        """Analyze player's movement patterns and style."""
        if not frames:
            return
        
        positions = [(f['norm_x'], f['norm_y']) for f in frames]
        
        # Calculate movement characteristics
        movement_vectors = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            distance = math.sqrt(dx**2 + dy**2)
            movement_vectors.append((dx, dy, distance))
        
        if movement_vectors:
            distances = [v[2] for v in movement_vectors]
            
            self.movement_patterns = {
                'average_movement_distance': float(np.mean(distances)),
                'maximum_movement_distance': float(np.max(distances)),
                'movement_variance': float(np.var(distances)),
                'movement_consistency': 1.0 / (1.0 + float(np.var(distances))),
                'direction_changes': len([v for v in movement_vectors if v[2] > 0.1]),
                'pattern_recognition_score': self._calculate_pattern_score(positions)
            }
    
    def _calculate_pattern_score(self, positions: List[tuple]) -> float:
        """Calculate how predictable/structured the movement patterns are."""
        if len(positions) < 4:
            return 0.5
        
        # Simple pattern detection: look for repeating sequences
        patterns = []
        for i in range(len(positions) - 3):
            pattern = positions[i:i+3]
            patterns.append(pattern)
        
        # Look for similar patterns
        similar_patterns = 0
        total_comparisons = 0
        
        for i in range(len(patterns)):
            for j in range(i+1, len(patterns)):
                total_comparisons += 1
                # Simple similarity check (normalized coordinates)
                sim = sum(min(abs(p1[0] - p2[0]), 0.1) + min(abs(p1[1] - p2[1]), 0.1) 
                        for p1, p2 in zip(patterns[i], patterns[j])) / 3.0
                if sim < 0.3:  # Consider patterns similar if they're close
                    similar_patterns += 1
        
        return similar_patterns / total_comparisons if total_comparisons > 0 else 0.5
    
    def _analyze_decision_patterns(self, frames: List[Dict], game_states: List[Dict]):
        """Analyze decision-making patterns and timing."""
        if not game_states:
            return
        
        # Analyze animation and action state changes
        animation_changes = Counter()
        action_changes = Counter()
        
        for state in game_states:
            animation_changes[state['current_animation']] += 1
            action_changes[state['action_state']] += 1
        
        # Calculate decision consistency
        total_states = len(game_states)
        animation_consistency = max(animation_changes.values()) / total_states
        action_consistency = max(action_changes.values()) / total_states
        
        self.decision_making = {
            'dominant_animations': dict(animation_changes.most_common(3)),
            'dominant_action_states': dict(action_changes.most_common(3)),
            'animation_consistency': animation_consistency,
            'action_consistency': action_consistency,
            'decision_pattern_score': (animation_consistency + action_consistency) / 2,
            'adaptation_rate': self._calculate_adaptation_rate(game_states)
        }
    
    def _calculate_adaptation_rate(self, game_states: List[Dict]) -> float:
        """Calculate how quickly the player adapts to new situations."""
        if len(game_states) < 3:
            return 0.5
        
        # Look for changes in animation/action state
        changes = 0
        for i in range(1, len(game_states)):
            if (game_states[i]['current_animation'] != game_states[i-1]['current_animation'] or
                game_states[i]['action_state'] != game_states[i-1]['action_state']):
                changes += 1
        
        return changes / (len(game_states) - 1)
    
    def _analyze_tactical_preferences(self, frames: List[Dict], game_states: List[Dict]):
        """Analyze tactical preferences and strategies."""
        if not frames:
            return
        
        # Analyze positioning relative to centroid
        centroid_x = np.mean([f['norm_x'] for f in frames])
        centroid_y = np.mean([f['norm_y'] for f in frames])
        
        positions = [(f['norm_x'], f['norm_y']) for f in frames]
        
        # Calculate preferred zones
        zones = self._classify_zones(positions, centroid_x, centroid_y)
        
        # Analyze level preferences
        level_preferences = Counter()
        for state in game_states:
            level_preferences[state['level']] += 1
        
        self.tactical_preferences = {
            'positional_preferences': zones,
            'preferred_zones': dict(zones.most_common(3)),
            'level_preferences': dict(level_preferences),
            'centroid_position': {'x': float(centroid_x), 'y': float(centroid_y)},
            'tactical_flexibility': 1.0 - (zones.most_common(1)[0][1] / len(frames)),
            'engagement_pattern': self._analyze_engagement_pattern(frames)
        }
    
    def _classify_zones(self, positions: List[tuple], centroid_x: float, centroid_y: float) -> Counter:
        """Classify positions into tactical zones."""
        zones = Counter()
        
        for x, y in positions:
            # Classify based on relative position to centroid
            if x < centroid_x and y < centroid_y:
                zones['top_left'] += 1
            elif x >= centroid_x and y < centroid_y:
                zones['top_right'] += 1
            elif x < centroid_x and y >= centroid_y:
                zones['bottom_left'] += 1
            else:
                zones['bottom_right'] += 1
        
        return zones
    
    def _analyze_engagement_pattern(self, frames: List[Dict]) -> Dict:
        """Analyze engagement and disengagement patterns."""
        if len(frames) < 2:
            return {'engagement_score': 0.5, 'patrol_frequency': 0}
        
        # Look for engagement/disengagement based on proximity changes
        engagement_scores = []
        for i in range(1, len(frames)):
            prev_dist = self._calculate_position_distance(frames[i-1])
            curr_dist = self._calculate_position_distance(frames[i])
            
            # Simple engagement metric
            engagement = abs(curr_dist - prev_dist) / (prev_dist + 1)
            engagement_scores.append(engagement)
        
        return {
            'engagement_score': float(np.mean(engagement_scores)),
            'patrol_frequency': len([e for e in engagement_scores if e < 0.1]),
            'engagement_variance': float(np.var(engagement_scores))
        }
    
    def _calculate_position_distance(self, frame: Dict) -> float:
        """Calculate distance from origin for a frame."""
        x = frame.get('norm_x', 0) or 0
        y = frame.get('norm_y', 0) or 0
        return math.sqrt(x**2 + y**2)
    
    def _analyze_physical_attributes(self, frames: List[Dict]):
        """Analyze physical movement attributes."""
        if not frames:
            return
        
        positions = [(f['norm_x'], f['norm_y']) for f in frames]
        
        # Calculate speed, acceleration, and movement quality
        velocities = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            velocity = math.sqrt(dx**2 + dy**2)
            velocities.append(velocity)
        
        if velocities:
            self.physical_attributes = {
                'average_speed': float(np.mean(velocities)),
                'peak_speed': float(np.max(velocities)),
                'speed_consistency': 1.0 / (1.0 + float(np.var(velocities))),
                'agility_score': self._calculate_agility_score(positions),
                'movement_efficiency': self._calculate_movement_efficiency(positions)
            }
    
    def _calculate_agility_score(self, positions: List[tuple]) -> float:
        """Calculate agility based on movement changes."""
        if len(positions) < 3:
            return 0.5
        
        direction_changes = 0
        for i in range(1, len(positions) - 1):
            # Calculate direction vectors
            dx1 = positions[i][0] - positions[i-1][0]
            dy1 = positions[i][1] - positions[i-1][1]
            dx2 = positions[i+1][0] - positions[i][0]
            dy2 = positions[i+1][1] - positions[i][1]
            
            # Dot product to check if direction changed
            dot_product = dx1 * dx2 + dy1 * dy2
            if abs(dot_product) < 0.5:  # Significant direction change
                direction_changes += 1
        
        return direction_changes / (len(positions) - 2)
    
    def _calculate_movement_efficiency(self, positions: List[tuple]) -> float:
        """Calculate how efficiently movement achieves goals."""
        # For now, return a placeholder efficiency score
        return 0.7
    
    def _analyze_psychological_profile(self, frames: List[Dict], game_states: List[Dict]):
        """Analyze psychological and behavioral traits."""
        if not frames or not game_states:
            return
        
        # Analyze risk-taking behavior (movement distance)
        position_distances = [self._calculate_position_distance(f) for f in frames]
        avg_distance = np.mean(position_distances)
        
        # Analyze persistence (time in zones)
        centroids = self._get_centroid_from_profile()
        persistence = self._calculate_persistence_score(frames, centroids)
        
        # Analyze adaptability (changes in behavior)
        adaptability = self._calculate_adaptability(game_states)
        
        self.psychological_profile = {
            'risk_tolerance': min(avg_distance / 0.5, 1.0),  # Scale based on reasonable bounds
            'persistence_score': persistence,
            'adaptability_score': adaptability,
            'patience_level': self._calculate_patience_level(game_states),
            'stress_response': self._calculate_stress_response(frames),
            'decision_confidence': self._calculate_decision_confidence(game_states)
        }
    
    def _get_centroid_from_profile(self) -> Dict[str, float]:
        """Get centroid from movement data."""
        return {'x': 0.5, 'y': 0.5}  # Default
    
    def _calculate_persistence_score(self, frames: List[Dict], centroid: Dict) -> float:
        """Calculate how persistent the player is in maintaining positions."""
        if not frames:
            return 0.5
        
        # Calculate time spent in centroid area
        time_in_zone = sum(1 for f in frames 
                         if (abs(f.get('norm_x', 0) - centroid['x']) < 0.2 and
                             abs(f.get('norm_y', 0) - centroid['y']) < 0.2))
        
        return time_in_zone / len(frames)
    
    def _calculate_adaptability(self, game_states: List[Dict]) -> float:
        """Calculate adaptability to new situations."""
        if len(game_states) < 3:
            return 0.5
        
        unique_states = len(set((s['current_animation'], s['action_state']) 
                               for s in game_states))
        return min(unique_states / 3.0, 1.0)  # Cap at reasonable maximum
    
    def _calculate_patience_level(self, game_states: List[Dict]) -> float:
        """Calculate patience based on state persistence."""
        if not game_states:
            return 0.5
        
        most_common_state = Counter((s['current_animation'], s['action_state']) 
                                   for s in game_states).most_common(1)[0][1]
        return most_common_state / len(game_states)
    
    def _calculate_stress_response(self, frames: List[Dict]) -> float:
        """Calculate response under pressure (based on movement during high activity)."""
        if not frames:
            return 0.5
        
        # Simple stress response based on movement variability
        distances = [self._calculate_position_distance(f) for f in frames]
        return 1.0 / (1.0 + np.std(distances))
    
    def _calculate_decision_confidence(self, game_states: List[Dict]) -> float:
        """Calculate confidence in decision-making."""
        if not game_states:
            return 0.5
        
        # Higher consistency = higher confidence
        animation_consistency = max(Counter(s['current_animation'] for s in game_states).values()) / len(game_states)
        return animation_consistency
    
    def _analyze_performance_metrics(self, frames: List[Dict], game_states: List[Dict]):
        """Analyze performance metrics and statistics."""
        if not frames or not game_states:
            return
        
        # Calculate various performance metrics
        total_frames = len(frames)
        total_states = len(game_states)
        
        # Engagement metrics
        engagement_rate = sum(1 for f in frames 
                             if f.get('norm_x', 0) > 0.1 or f.get('norm_y', 0) > 0.1) / total_frames
        
        # Activity metrics
        avg_health = np.mean([s['player_health'] for s in game_states])
        health_variation = np.var([s['player_health'] for s in game_states])
        
        self.performance_metrics = {
            'engagement_rate': engagement_rate,
            'average_health': float(avg_health),
            'health_variation': float(health_variation),
            'activity_consistency': 1.0 / (1.0 + health_variation),
            'total_play_time': sum(s['timestamp'] for s in game_states) - game_states[0]['timestamp'],
            'frames_per_second': total_frames / self.performance_metrics.get('total_play_time', 1)
        }
    
    def _identify_strengths_weaknesses(self, frames: List[Dict]):
        """Identify player strengths and weaknesses based on analysis."""
        self.strengths = []
        self.weaknesses = []
        
        # Identify movement-related strengths
        movement_consistency = self.movement_patterns.get('movement_consistency', 0)
        if movement_consistency > 0.7:
            self.strengths.append("Consistent movement patterns")
        else:
            self.weaknesses.append("Inconsistent movement patterns")
        
        # Identify decision-related strengths
        decision_score = self.decision_making.get('decision_pattern_score', 0)
        if decision_score > 0.6:
            self.strengths.append("Predictable decision making")
        else:
            self.weaknesses.append("Inconsistent decision making")
        
        # Identify tactical strengths
        tactical_flexibility = self.tactical_preferences.get('tactical_flexibility', 0)
        if tactical_flexibility > 0.5:
            self.strengths.append("Tactically flexible")
        else:
            self.weaknesses.append("Tactically rigid")
        
        # Identify physical strengths
        speed_consistency = self.physical_attributes.get('speed_consistency', 0)
        if speed_consistency > 0.7:
            self.strengths.append("Consistent speed")
        else:
            self.weaknesses.append("Variable speed")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            'profile_id': self.profile_id,
            'created_at': self.created_at.isoformat(),
            'last_updated': datetime.now().isoformat(),
            'movement_patterns': self.movement_patterns,
            'decision_making': self.decision_making,
            'tactical_preferences': self.tactical_preferences,
            'physical_attributes': self.physical_attributes,
            'psychological_profile': self.psychological_profile,
            'performance_metrics': self.performance_metrics,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'behavioral_signatures': self.behavioral_signatures,
            'response_patterns': self.response_patterns,
            'pressure_handling': self.pressure_handling
        }
    
    def save_profile(self, output_path: str = None):
        """Save player profile to file."""
        if output_path is None:
            output_path = f"./profiles/{self.profile_id}_profile.json"
        
        Path(output_path).parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Player profile saved to {output_path}")
    
    def generate_behavioral_fingerprint(self) -> Dict[str, Any]:
        """Generate a behavioral fingerprint for player identification."""
        fingerprint = {
            'movement_signature': self._generate_movement_signature(),
            'decision_signature': self._generate_decision_signature(),
            'positional_signature': self._generate_positional_signature(),
            'temporal_patterns': self._generate_temporal_patterns()
        }
        
        self.behavioral_signatures = fingerprint
        return fingerprint
    
    def _generate_movement_signature(self) -> Dict[str, Any]:
        """Generate movement signature."""
        return {
            'avg_distance': self.movement_patterns.get('average_movement_distance', 0),
            'max_distance': self.movement_patterns.get('maximum_movement_distance', 0),
            'direction_changes': self.movement_patterns.get('direction_changes', 0)
        }
    
    def _generate_decision_signature(self) -> Dict[str, Any]:
        """Generate decision-making signature."""
        return {
            'animation_consistency': self.decision_making.get('animation_consistency', 0),
            'action_consistency': self.decision_making.get('action_consistency', 0),
            'adaptation_rate': self.decision_making.get('adaptation_rate', 0)
        }
    
    def _generate_positional_signature(self) -> Dict[str, Any]:
        """Generate positional signature."""
        return {
            'centroid': self.tactical_preferences.get('centroid_position', {'x': 0.5, 'y': 0.5}),
            'preferred_zones': list(self.tactical_preferences.get('preferred_zones', {}).keys()),
            'engagement_score': self.tactical_preferences.get('engagement_pattern', {}).get('engagement_score', 0)
        }
    
    def _generate_temporal_patterns(self) -> Dict[str, Any]:
        """Generate temporal patterns."""
        return {
            'activity_consistency': self.performance_metrics.get('activity_consistency', 0),
            'engagement_rate': self.performance_metrics.get('engagement_rate', 0),
            'fps_average': self.performance_metrics.get('fps_average', 0)
        }


def create_player_profile(profile_id: str, data_source: str = "./data/gameplay.db") -> PlayStyleProfile:
    """Create a new player profile from gameplay data."""
    profile = PlayStyleProfile(profile_id, data_source)
    
    # Connect and analyze database
    conn = sqlite3.connect(data_source)
    try:
        profile.analyze_database(conn)
        profile.generate_behavioral_fingerprint()
        return profile
    finally:
        conn.close()
    
    return profile


def main():
    """Example usage of Player Profiler."""
    print("Creating player profile from gameplay data...")
    
    try:
        # Create profile from existing gameplay data
        profile = create_player_profile("player_001", "./data/gameplay.db")
        
        # Save profile
        profile.save_profile()
        print(f"Player profile created and saved for {profile.profile_id}")
        
        # Display key insights
        print(f"Movement consistency: {profile.movement_patterns.get('movement_consistency', 0):.2f}")
        print(f"Decision score: {profile.decision_making.get('decision_pattern_score', 0):.2f}")
        print(f"Tactical flexibility: {profile.tactical_preferences.get('tactical_flexibility', 0):.2f}")
        print(f"Strengths: {', '.join(profile.strengths[:3])}")
        
        # Generate behavioral fingerprint
        fingerprint = profile.generate_behavioral_fingerprint()
        print(f"Behavioral fingerprint generated with {len(fingerprint)} components")
        
    except FileNotFoundError as e:
        print(f"Database not found: {e}")
        print("Please run the capture system first to generate gameplay data.")

if __name__ == "__main__":
    main()