"""
Opponent behavior analyzer for extracted gameplay data.

This module reads the SQLite database and aggregates opponent tendencies
(movement patterns, action frequencies) into a summary profile JSON.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
import logging
from collections import defaultdict, Counter
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpponentAnalyzer:
    def __init__(self, db_path: str = "./data/gameplay.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def connect_db(self) -> sqlite3.Connection:
        """Connect to SQLite database."""
        return sqlite3.connect(self.db_path)
    
    def extract_movement_patterns(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Extract and analyze opponent movement patterns from frames table."""
        cursor = conn.cursor()
        
        # Get all opponent positions
        cursor.execute('''
            SELECT opponent_x, opponent_y, timestamp, frame_number
            FROM frames 
            WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL
            ORDER BY timestamp
        ''')
        
        positions = cursor.fetchall()
        if not positions:
            logger.warning("No opponent positions found in database")
            return {}
        
        # Convert to numpy array for analysis
        data = np.array(positions, dtype=np.float32)
        
        patterns = {
            'total_frames_with_position': len(positions),
            'position_bounds': {
                'min_x': float(np.min(data[:, 0])),
                'max_x': float(np.max(data[:, 0])),
                'min_y': float(np.min(data[:, 1])),
                'max_y': float(np.max(data[:, 1]))
            },
            'movement_velocity': self._calculate_velocities(data),
            'spatial_distribution': self._analyze_spatial_distribution(data),
            'position_clusters': self._find_position_clusters(data),
            'movement_directions': self._analyze_movement_directions(data)
        }
        
        return patterns
    
    def _calculate_velocities(self, data: np.ndarray) -> Dict[str, Any]:
        """Calculate opponent movement velocities."""
        if len(data) < 2:
            return {'average_speed': 0, 'max_speed': 0, 'velocity_distribution': {}}
        
        velocities = []
        for i in range(1, len(data)):
            time_diff = data[i][2] - data[i-1][2]  # timestamp difference
            if time_diff > 0:  # Avoid division by zero
                dx = data[i][0] - data[i-1][0]
                dy = data[i][1] - data[i-1][1]
                speed = math.sqrt(dx**2 + dy**2) / time_diff
                velocities.append(speed)
        
        if not velocities:
            return {'average_speed': 0, 'max_speed': 0, 'velocity_distribution': {}}
        
        # Create velocity distribution bins
        velocity_dist = {}
        bins = [0, 10, 50, 100, 200, float('inf')]
        labels = ['<10', '10-50', '50-100', '100-200', '>200']
        
        for i, label in enumerate(labels):
            count = sum(1 for v in velocities if bins[i] <= v < bins[i+1])
            velocity_dist[label] = count
        
        return {
            'average_speed': float(np.mean(velocities)),
            'max_speed': float(np.max(velocities)),
            'min_speed': float(np.min(velocities)),
            'velocity_distribution': velocity_dist
        }
    
    def _analyze_spatial_distribution(self, data: np.ndarray) -> Dict[str, Any]:
        """Analyze spatial distribution of opponent positions."""
        positions = data[:, :2]  # x, y coordinates
        
        # Calculate centroid
        centroid_x = np.mean(positions[:, 0])
        centroid_y = np.mean(positions[:, 1])
        
        # Calculate standard deviation (spread)
        std_x = np.std(positions[:, 0])
        std_y = np.std(positions[:, 1])
        
        # Calculate distance from centroid for each point
        distances = np.sqrt((positions[:, 0] - centroid_x)**2 + (positions[:, 1] - centroid_y)**2)
        
        return {
            'centroid': {'x': float(centroid_x), 'y': float(centroid_y)},
            'spread': {
                'std_x': float(std_x),
                'std_y': float(std_y),
                'average_distance_from_center': float(np.mean(distances)),
                'max_distance': float(np.max(distances))
            },
            'zone_preference': self._identify_preferred_zones(positions)
        }
    
    def _identify_preferred_zones(self, positions: np.ndarray) -> List[Dict[str, Any]]:
        """Identify preferred zones in the game space."""
        # Define quadrants relative to centroid
        centroid_x = np.mean(positions[:, 0])
        centroid_y = np.mean(positions[:, 1])
        
        zones = {
            'top_left': {'count': 0, 'center': {'x': centroid_x/2, 'y': centroid_y/2}},
            'top_right': {'count': 0, 'center': {'x': centroid_x*1.5, 'y': centroid_y/2}},
            'bottom_left': {'count': 0, 'center': {'x': centroid_x/2, 'y': centroid_y*1.5}},
            'bottom_right': {'count': 0, 'center': {'x': centroid_x*1.5, 'y': centroid_y*1.5}}
        }
        
        for x, y in positions:
            if x < centroid_x and y < centroid_y:
                zones['top_left']['count'] += 1
            elif x >= centroid_x and y < centroid_y:
                zones['top_right']['count'] += 1
            elif x < centroid_x and y >= centroid_y:
                zones['bottom_left']['count'] += 1
            else:
                zones['bottom_right']['count'] += 1
        
        # Return zones sorted by frequency
        return sorted(zones.items(), key=lambda item: item[1]['count'], reverse=True)
    
    def _find_position_clusters(self, data: np.ndarray) -> List[Dict[str, Any]]:
        """Find clusters in opponent position data (simplified DBSCAN-like clustering)."""
        if len(data) < 3:
            return []
        
        positions = data[:, :2]
        clusters = []
        visited = set()
        
        # Simple clustering: group points that are close to each other
        for i in range(len(positions)):
            if i in visited:
                continue
            
            # Find all points within 100 pixels of this point
            cluster_points = [i]
            visited.add(i)
            
            for j in range(len(positions)):
                if j in visited:
                    continue
                
                dist = math.sqrt((positions[i][0] - positions[j][0])**2 + 
                               (positions[i][1] - positions[j][1])**2)
                if dist < 100:  # Cluster radius
                    cluster_points.append(j)
                    visited.add(j)
            
            if len(cluster_points) > 1:
                cluster_positions = positions[cluster_points]
                clusters.append({
                    'center': {
                        'x': float(np.mean(cluster_positions[:, 0])),
                        'y': float(np.mean(cluster_positions[:, 1]))
                    },
                    'size': len(cluster_points),
                    'bounds': {
                        'min_x': float(np.min(cluster_positions[:, 0])),
                        'max_x': float(np.max(cluster_positions[:, 0])),
                        'min_y': float(np.min(cluster_positions[:, 1])),
                        'max_y': float(np.max(cluster_positions[:, 1]))
                    }
                })
        
        return sorted(clusters, key=lambda c: c['size'], reverse=True)
    
    def _analyze_movement_directions(self, data: np.ndarray) -> Dict[str, Any]:
        """Analyze predominant movement directions."""
        if len(data) < 2:
            return {'directions': {}, 'changes': 0}
        
        directions = []
        direction_changes = 0
        
        for i in range(1, len(data)):
            dx = data[i][0] - data[i-1][0]
            dy = data[i][1] - data[i-1][1]
            
            # Normalize direction
            magnitude = math.sqrt(dx**2 + dy**2)
            if magnitude > 0:
                norm_dx = dx / magnitude
                norm_dy = dy / magnitude
                directions.append((norm_dx, norm_dy))
            
            # Simple direction change detection
            if i > 1:
                prev_dx = data[i-1][0] - data[i-2][0]
                prev_dy = data[i-1][1] - data[i-2][1]
                if magnitude > 0 and prev_dx > 0:
                    direction_changes += 1
        
        # Bin directions into cardinal directions
        direction_bins = {
            'right': [], 'left': [], 'up': [], 'down': [], 'stationary': []
        }
        
        for dx, dy in directions:
            if abs(dx) > abs(dy):
                if dx > 0:
                    direction_bins['right'].append((dx, dy))
                else:
                    direction_bins['left'].append((dx, dy))
            else:
                if dy > 0:
                    direction_bins['up'].append((dx, dy))
                else:
                    direction_bins['down'].append((dx, dy))
        
        # Calculate percentages
        total = len(directions)
        if total == 0:
            return {'directions': {}, 'changes': 0}
        
        direction_percentages = {}
        for direction, dir_list in direction_bins.items():
            percentage = (len(dir_list) / total) * 100
            direction_percentages[direction] = round(percentage, 2)
        
        return {
            'directions': direction_percentages,
            'changes': direction_changes
        }
    
    def analyze_action_states(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze opponent action states from game_states table."""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action_state, current_animation, COUNT(*) as frequency
            FROM game_states
            GROUP BY action_state, current_animation
            ORDER BY frequency DESC
        ''')
        
        action_data = cursor.fetchall()
        
        # Aggregate action frequencies
        action_frequencies = defaultdict(int)
        animation_frequencies = defaultdict(int)
        
        for action_state, animation, freq in action_data:
            action_frequencies[action_state] += freq
            animation_frequencies[animation] += freq
        
        return {
            'action_frequencies': dict(action_frequencies),
            'animation_frequencies': dict(animation_frequencies),
            'total_states_analyzed': sum(action_frequencies.values())
        }
    
    def generate_profile(self) -> Dict[str, Any]:
        """Generate complete opponent profile JSON."""
        conn = self.connect_db()
        
        try:
            profile = {
                'metadata': {
                    'generated_at': None,  # Will be filled by json.dumps
                    'data_source': str(self.db_path),
                    'analysis_version': '1.0'
                },
                'movement_patterns': self.extract_movement_patterns(conn),
                'action_states': self.analyze_action_states(conn),
                'behavioral_summary': self._generate_behavioral_summary(conn)
            }
            
            return profile
        finally:
            conn.close()
    
    def _generate_behavioral_summary(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Generate a high-level behavioral summary."""
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM frames')
        total_frames, min_time, max_time = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM game_states')
        total_states, state_min_time, state_max_time = cursor.fetchone()
        
        duration = max_time - min_time if max_time and min_time else 0
        
        return {
            'data_collection': {
                'total_frames': total_frames,
                'duration_seconds': round(duration, 2),
                'frames_per_second_estimated': round(total_frames / duration, 2) if duration > 0 else 0
            },
            'opponent_presence': {
                'states_analyzed': total_states,
                'percentage_of_frames_with_position': self._calculate_position_percentage(conn)
            }
        }
    
    def _calculate_position_percentage(self, conn: sqlite3.Connection) -> float:
        """Calculate percentage of frames where opponent was detected."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM frames')
        total_frames = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM frames WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL')
        detected_frames = cursor.fetchone()[0]
        
        return round((detected_frames / total_frames * 100), 2) if total_frames > 0 else 0
    
    def save_profile(self, output_path: str = None) -> str:
        """Generate and save opponent profile to JSON file."""
        profile = self.generate_profile()
        
        if output_path is None:
            output_path = self.db_path.parent / "opponent_profile.json"
        
        with open(output_path, 'w') as f:
            json.dump(profile, f, indent=2, default=str)
        
        logger.info(f"Opponent profile saved to {output_path}")
        return str(output_path)


def main():
    """Example usage of OpponentAnalyzer."""
    print("Analyzing opponent gameplay data...")
    
    try:
        analyzer = OpponentAnalyzer("./data/gameplay.db")
        profile_path = analyzer.save_profile()
        print(f"Profile generated: {profile_path}")
        
        # Display some key insights
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        
        movement = profile['movement_patterns']
        print(f"Movement patterns: {movement.get('position_bounds', {})}")
        print(f"Velocity stats: {movement.get('movement_velocity', {})}")
        
        actions = profile['action_states']
        print(f"Top actions: {list(actions.get('action_frequencies', {}).items())[:5]}")
        
    except FileNotFoundError as e:
        print(f"Database not found: {e}")
        print("Run the capture system first to generate gameplay data.")

if __name__ == "__main__":
    main()