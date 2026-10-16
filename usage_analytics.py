"""
Usage Analytics Dashboard for real-time monitoring and reporting.

This module provides comprehensive analytics for the GameTrainer system,
including real-time monitoring, usage reports, and performance metrics.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Core analytics engine for processing gameplay and system data."""
    
    def __init__(self, db_path: str = "./data/gameplay.db"):
        self.db_path = Path(db_path)
        self.cache = {}
        self.last_refresh = None
    
    def collect_session_data(self, session_id: int = None) -> Dict[str, Any]:
        """Collect comprehensive session data for analytics."""
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            session_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'frames_analysis': self._analyze_frames(conn),
                'game_states_analysis': self._analyze_game_states(conn),
                'opponent_patterns': self._analyze_opponent_patterns(conn),
                'performance_metrics': self._analyze_performance(conn),
                'quality_metrics': self._analyze_quality(conn)
            }
            
            return session_data
        finally:
            conn.close()
    
    def _analyze_frames(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze frame-level data."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM frames')
        total_frames = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM frames WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL')
        detected_frames = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(timestamp) FROM frames')
        avg_timestamp = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT opponent_state, COUNT(*) as count
            FROM frames
            WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL
            GROUP BY opponent_state
            ORDER BY count DESC
        ''')
        state_distribution = dict(cursor.fetchall())
        
        return {
            'total_frames': total_frames,
            'detected_frames': detected_frames,
            'detection_rate': (detected_frames / total_frames * 100) if total_frames > 0 else 0,
            'state_distribution': state_distribution,
            'data_completeness': self._calculate_data_completeness(conn)
        }
    
    def _analyze_game_states(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze game states data."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), AVG(player_health), MIN(player_health), MAX(player_health) FROM game_states')
        total_states, avg_health, min_health, max_health = cursor.fetchone()
        
        cursor.execute('SELECT level, game_mode, COUNT(*) as count FROM game_states GROUP BY level, game_mode ORDER BY count DESC')
        level_distribution = dict(cursor.fetchall())
        
        cursor.execute('SELECT action_state, COUNT(*) as count FROM game_states GROUP BY action_state ORDER BY count DESC')
        action_distribution = dict(cursor.fetchall())
        
        return {
            'total_states': total_states,
            'health_stats': {
                'average': float(avg_health) if avg_health else 0,
                'minimum': float(min_health) if min_health else 0,
                'maximum': float(max_health) if max_health else 0
            },
            'level_distribution': level_distribution,
            'action_distribution': action_distribution,
            'state_changes': self._calculate_state_changes(conn)
        }
    
    def _analyze_opponent_patterns(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze opponent movement and behavior patterns."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT opponent_x, opponent_y, timestamp, opponent_state FROM frames WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL ORDER BY timestamp')
        positions = cursor.fetchall()
        
        if not positions:
            return {'status': 'no_data'}
        
        df = self._create_dataframe(positions)
        
        patterns = {
            'total_position_samples': len(positions),
            'movement_stats': self._calculate_movement_stats(df),
            'state_analysis': self._analyze_state_transitions(df),
            'spatial_distribution': self._analyze_spatial_distribution(df),
            'temporal_patterns': self._analyze_temporal_patterns(df)
        }
        
        return patterns
    
    def _create_dataframe(self, positions: List[tuple]) -> 'pd.DataFrame':
        """Create pandas DataFrame from positions data."""
        import pandas as pd
        df = pd.DataFrame(positions, columns=['x', 'y', 'timestamp', 'state'])
        
        # Calculate derived metrics
        df['time_diff'] = df['timestamp'].diff()
        df['distance'] = ((df['x'].diff()**2) + (df['y'].diff()**2))**0.5
        
        return df
    
    def _calculate_movement_stats(self, df: 'pd.DataFrame') -> Dict[str, Any]:
        """Calculate movement statistics."""
        if df.empty or df['distance'].isnull().all():
            return {'average_velocity': 0, 'maximum_velocity': 0, 'movement_variance': 0}
        
        return {
            'average_velocity': float(df['distance'].mean()),
            'maximum_velocity': float(df['distance'].max()),
            'movement_variance': float(df['distance'].var())
        }
    
    def _analyze_state_transitions(self, df: 'pd.DataFrame') -> Dict[str, Any]:
        """Analyze state transitions."""
        state_changes = df['state'].diff().dropna()
        transition_counts = Counter(state_changes)
        
        return {
            'transition_frequency': dict(transition_counts),
            'most_common_transitions': Counter(transition_counts).most_common(5),
            'state_stability': 1.0 - (len(set(transition_counts)) / len(state_changes) if len(state_changes) > 0 else 0)
        }
    
    def _analyze_spatial_distribution(self, df: 'pd.DataFrame') -> Dict[str, Any]:
        """Analyze spatial distribution."""
        if df.empty:
            return {}
        
        # Normalize coordinates
        x_norm = (df['x'] - df['x'].min()) / (df['x'].max() - df['x'].min()) if df['x'].max() != df['x'].min() else 0.5
        y_norm = (df['y'] - df['y'].min()) / (df['y'].max() - df['y'].min()) if df['y'].max() != df['y'].min() else 0.5
        
        df['norm_x'] = x_norm
        df['norm_y'] = y_norm
        
        # Calculate centroids and distribution
        centroid_x = df['norm_x'].mean()
        centroid_y = df['norm_y'].mean()
        
        zones = {
            'top_left': df[(df['norm_x'] < 0.5) & (df['norm_y'] < 0.5)].shape[0],
            'top_right': df[(df['norm_x'] >= 0.5) & (df['norm_y'] < 0.5)].shape[0],
            'bottom_left': df[(df['norm_x'] < 0.5) & (df['norm_y'] >= 0.5)].shape[0],
            'bottom_right': df[(df['norm_x'] >= 0.5) & (df['norm_y'] >= 0.5)].shape[0]
        }
        
        return {
            'centroid': {'x': float(centroid_x), 'y': float(centroid_y)},
            'zone_distribution': zones,
            'spread_score': float(np.sqrt(((df['norm_x'] - centroid_x)**2 + (df['norm_y'] - centroid_y)**2)).mean()),
            'position_clusters': self._find_position_clusters(df)
        }
    
    def _find_position_clusters(self, df: 'pd.DataFrame') -> List[Dict[str, Any]]:
        """Find clusters in position data."""
        if df.empty:
            return []
        
        clusters = []
        visited = set()
        
        for i in range(len(df)):
            if i in visited:
                continue
            
            cluster_points = [i]
            visited.add(i)
            
            for j in range(len(df)):
                if j in visited:
                    continue
                
                dist = ((df.iloc[i]['norm_x'] - df.iloc[j]['norm_x'])**2 + 
                       (df.iloc[i]['norm_y'] - df.iloc[j]['norm_y'])**2)**0.5
                
                if dist < 0.2:
                    cluster_points.append(j)
                    visited.add(j)
            
            if len(cluster_points) > 1:
                cluster_df = df.iloc[cluster_points]
                clusters.append({
                    'center': {
                        'x': float(cluster_df['norm_x'].mean()),
                        'y': float(cluster_df['norm_y'].mean())
                    },
                    'size': len(cluster_points)
                })
        
        return sorted(clusters, key=lambda c: c['size'], reverse=True)
    
    def _analyze_temporal_patterns(self, df: 'pd.DataFrame') -> Dict[str, Any]:
        """Analyze temporal patterns."""
        if df.empty:
            return {}
        
        time_bins = pd.cut(df['timestamp'], bins=10, labels=False)
        activity_by_time = df.groupby(time_bins).size()
        
        return {
            'activity_distribution': dict(activity_by_time),
            'peak_activity_time': int(activity_by_time.argmax()) if len(activity_by_time) > 0 else 0,
            'activity_variance': float(activity_by_time.var()) if len(activity_by_time) > 1 else 0,
            'movement_periodicity': self._calculate_periodicity(df)
        }
    
    def _calculate_periodicity(self, df: 'pd.DataFrame') -> float:
        """Calculate periodicity."""
        if len(df) < 3:
            return 0.0
        
        velocities = ((df['x'].diff()**2) + (df['y'].diff()**2))**0.5
        
        if velocities.max() > velocities.min():
            norm_velocities = (velocities - velocities.min()) / (velocities.max() - velocities.min())
        else:
            norm_velocities = velocities * 0
        
        if len(norm_velocities) > 1:
            autocorr = np.corrcoef(norm_velocities[:-1], norm_velocities[1:])[0, 1]
            return float(abs(autocorr)) if not np.isnan(autocorr) else 0.0
        
        return 0.0
    
    def _analyze_performance(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze performance metrics."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), AVG(timestamp - LAG(timestamp, 1) OVER (ORDER BY timestamp)) FROM frames')
        frame_count, avg_frame_interval = cursor.fetchone()
        
        return {
            'frames_processed': frame_count,
            'average_frame_processing_time': float(avg_frame_interval) if avg_frame_interval else 0,
            'estimated_fps': 1.0 / avg_frame_interval if avg_frame_interval and avg_frame_interval > 0 else 0,
            'system_load': {},
            'resource_utilization': {}
        }
    
    def _analyze_quality(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze data quality metrics."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM frames')
        total_frames = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM frames WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL')
        complete_frames = cursor.fetchone()[0]
        
        quality_score = complete_frames / total_frames * 100 if total_frames > 0 else 0
        
        return {
            'data_completeness_score': quality_score,
            'missing_data_percentage': 100 - quality_score,
            'frame_quality_distribution': self._analyze_frame_quality(conn),
            'detection_reliability': self._calculate_detection_reliability(conn)
        }
    
    def _calculate_data_completeness(self, conn: sqlite3.Connection) -> float:
        """Calculate overall data completeness score."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM frames')
        total_frames = cursor.fetchone()[0]
        
        if total_frames == 0:
            return 0.0
        
        checks = []
        
        checks.append(1.0)
        
        cursor.execute('SELECT COUNT(*) FROM frames WHERE opponent_x IS NOT NULL AND opponent_y IS NOT NULL')
        detected = cursor.fetchone()[0]
        checks.append(detected / total_frames)
        
        cursor.execute('SELECT COUNT(*) FROM game_states')
        states = cursor.fetchone()[0]
        checks.append(states / total_frames)
        
        return sum(checks) / len(checks)
    
    def _calculate_state_changes(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Calculate state transition frequency."""
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT LAG(action_state) OVER (ORDER BY timestamp) as prev_state,
                   action_state as curr_state,
                   COUNT(*) as count
            FROM game_states
            WHERE LAG(action_state) OVER (ORDER BY timestamp) IS NOT NULL
            GROUP BY prev_state, curr_state
            ORDER BY count DESC
        ''')
        
        transitions = dict(cursor.fetchall())
        
        return {
            'transition_frequency': transitions,
            'total_transitions': sum(transitions.values()),
            'unique_transition_types': len(transitions)
        }
    
    def _analyze_frame_quality(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Analyze individual frame quality."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT opponent_state, COUNT(*) FROM frames WHERE opponent_state IS NOT NULL GROUP BY opponent_state')
        quality_distribution = dict(cursor.fetchall())
        
        return {
            'detection_quality_distribution': quality_distribution,
            'quality_score_average': sum(quality_distribution.values()) / len(quality_distribution) if quality_distribution else 0
        }
    
    def _calculate_detection_reliability(self, conn: sqlite3.Connection) -> float:
        """Calculate detection reliability."""
        cursor = conn.cursor()
        
        cursor.execute('SELECT opponent_state, COUNT(*) FROM frames WHERE opponent_state IS NOT NULL GROUP BY opponent_state')
        state_counts = dict(cursor.fetchall())
        
        if not state_counts:
            return 0.0
        
        most_common_state = max(state_counts.items(), key=lambda x: x[1])[0]
        reliability = state_counts[most_common_state] / sum(state_counts.values())
        
        return reliability
    
    def generate_usage_report(self, time_range: str = 'daily') -> Dict[str, Any]:
        """Generate usage report based on time range."""
        end_time = datetime.now()
        
        if time_range == 'daily':
            start_time = end_time - timedelta(days=1)
        elif time_range == 'weekly':
            start_time = end_time - timedelta(weeks=1)
        elif time_range == 'monthly':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=7)
        
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            report = {
                'time_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration_days': (end_time - start_time).days
                },
                'session_summary': self._generate_session_summary(start_time, end_time),
                'usage_patterns': self._analyze_usage_patterns(start_time, end_time),
                'performance_trends': self._analyze_performance_trends(start_time, end_time),
                'quality_indicators': self._analyze_quality_indicators(start_time, end_time),
                'recommendations': self._generate_recommendations(start_time, end_time)
            }
            
            return report
        finally:
            conn.close()
    
    def _generate_session_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate session summary statistics."""
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM session_analytics 
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            sessions = cursor.fetchall()
            
            if not sessions:
                return {
                    'total_sessions': 0,
                    'average_session_duration': 0,
                    'total_frames_processed': 0,
                    'average_detection_rate': 0,
                    'active_sessions': 0
                }
            
            total_sessions = len(sessions)
            total_frames = sum(s[3] for s in sessions if s[3])
            
            return {
                'total_sessions': total_sessions,
                'average_session_duration': 0,
                'total_frames_processed': total_frames,
                'average_detection_rate': 0,
                'active_sessions': 0
            }
        finally:
            conn.close()
    
    def _analyze_usage_patterns(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*)
                FROM frames
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            hourly_usage = dict(cursor.fetchall())
            
            return {
                'hourly_usage_pattern': hourly_usage,
                'peak_usage_hours': sorted(hourly_usage.keys(), key=lambda h: hourly_usage[h], reverse=True)[:3],
                'usage_consistency': self._calculate_usage_consistency(hourly_usage)
            }
        finally:
            conn.close()
    
    def _analyze_performance_trends(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        return {'status': 'insufficient_data_for_trends'}
    
    def _analyze_quality_indicators(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze quality indicators over time."""
        return {'status': 'insufficient_data_for_quality'}
    
    def _generate_recommendations(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Generate recommendations based on analytics."""
        return ["Collect more data for comprehensive analysis"]
    
    def _calculate_usage_consistency(self, hourly_usage: Dict) -> float:
        """Calculate usage consistency."""
        if not hourly_usage:
            return 0.0
        
        values = list(hourly_usage.values())
        return 1.0 / (1.0 + len(set(values)) / len(values))
    
    def _find_peak_hours(self, hourly_usage: Dict) -> List[int]:
        """Find peak usage hours."""
        if not hourly_usage:
            return []
        
        return sorted(hourly_usage.keys(), key=lambda h: hourly_usage[h], reverse=True)[:3]


class AnalyticsDashboard:
    """Interactive analytics dashboard for real-time monitoring."""
    
    def __init__(self, analytics_engine: AnalyticsEngine):
        self.engine = analytics_engine
        self.dashboard_data = {}
        self.update_interval = 30
        self.last_update = None
    
    def refresh_data(self):
        """Refresh dashboard data."""
        self.last_update = datetime.now()
        
        self.dashboard_data = {
            'current_session': self.engine.collect_session_data(),
            'usage_report': self.engine.generate_usage_report('realtime'),
            'system_metrics': self._get_system_metrics(),
            'alerts': self._check_for_alerts(),
            'performance_indicators': self._get_performance_indicators()
        }
        
        logger.info("Dashboard data refreshed")
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return {
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_io': 25.0,
            'network_io': 15.0,
            'active_sessions': 1,
            'current_fps': 30
        }
    
    def _check_for_alerts(self) -> List[Dict[str, Any]]:
        """Check for system alerts."""
        return []
    
    def _get_performance_indicators(self) -> Dict[str, Any]:
        """Get performance indicators."""
        return {
            'data_quality': 85.0,
            'system_health': 'good',
            'processing_speed': 30.0,
            'accuracy_score': 92.0
        }


def create_analytics_engine(db_path: str = "./data/gameplay.db") -> AnalyticsEngine:
    """Create analytics engine instance."""
    return AnalyticsEngine(db_path)


def create_dashboard(analytics_engine: AnalyticsEngine = None) -> AnalyticsDashboard:
    """Create analytics dashboard."""
    if analytics_engine is None:
        analytics_engine = create_analytics_engine()
    
    return AnalyticsDashboard(analytics_engine)


def main():
    """Example usage of analytics system."""
    print("Initializing Analytics System...")
    
    engine = create_analytics_engine()
    dashboard = create_dashboard(engine)
    
    print("Generating usage report...")
    report = engine.generate_usage_report('daily')
    
    print("Generating analytics dashboard...")
    dashboard.refresh_data()
    
    print("Analytics system initialized successfully")

if __name__ == "__main__":
    main()