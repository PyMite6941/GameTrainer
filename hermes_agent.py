"""
Hermes Agent for GameTrainer - Autonomous Play-Style Analysis and Behavior Optimization

This module implements the Hermes autonomous agent that provides:
1. Real-time play-style analysis and optimization
2. Autonomous behavior pattern recognition
3. Intelligent recommendation generation
4. Adaptive learning from gameplay data
5. Integration with GameTrainer system for comprehensive gameplay analysis

The Hermes agent acts as an intelligent assistant that analyzes gameplay
patterns, provides actionable recommendations, and continuously learns
from player behavior to enhance performance.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisStatus(Enum):
    """Status of Hermes agent analysis operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class PatternType(Enum):
    """Types of play patterns Hermes can recognize."""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    ADAPTIVE = "adaptive"
    PREDICTABLE = "predictable"
    UNPREDICTABLE = "unpredictable"

@dataclass
class AnalysisResult:
    """Result of a Hermes agent analysis."""
    timestamp: float
    player_id: str
    analysis_type: str
    status: AnalysisStatus
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    behavioral_features: Dict[str, Any] = field(default_factory=dict)
    patterns_detected: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error_message: Optional[str] = None

@dataclass
class PlayPattern:
    """Representation of a learned play pattern."""
    pattern_id: str
    pattern_type: PatternType
    characteristics: Dict[str, float]
    frequency: int = 0
    success_rate: float = 0.0
    last_observed: float = 0.0
    contextual_triggers: List[str] = field(default_factory=list)

@dataclass
class BehavioralMetrics:
    """Collection of behavioral metrics for analysis."""
    decision_speed: float = 0.5
    aggression_level: float = 0.5
    adaptation_rate: float = 0.5
    pattern_consistency: float = 0.5
    predictability_score: float = 0.5
    risk_assessment: float = 0.5
    creativity_index: float = 0.5
    consistency_score: float = 0.5

class HermesAgent:
    """
    Autonomous agent for play-style analysis and behavior optimization.
    
    The Hermes agent continuously analyzes gameplay data to provide
    intelligent insights and optimization recommendations. It uses
    machine learning algorithms to recognize patterns and suggest
    improvements to player performance.
    """
    
    def __init__(self, agent_id: str = "hermes_main", config: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.config = config or self._get_default_config()
        
        # Core state
        self.is_active = False
        self.current_analysis: Optional[AnalysisResult] = None
        self.learned_patterns: Dict[str, PlayPattern] = {}
        self.behavioral_history: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'average_confidence': 0.0,
            'average_response_time': 0.0,
            'pattern_recognition_rate': 0.0
        }
        
        # Threading
        self.analysis_queue: List[Dict[str, Any]] = []
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize with sample patterns
        self._initialize_sample_patterns()
        
        logger.info(f"Hermes Agent '{agent_id}' initialized successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Hermes agent."""
        return {
            'update_interval': 0.5,
            'max_patterns': 100,
            'confidence_threshold': 0.7,
            'learning_rate': 0.1,
            'min_pattern_frequency': 5,
            'auto_analyze': True,
            'generate_recommendations': True,
            'continuous_learning': True,
            'pattern_matching_enabled': True,
            'behavior_clustering': True,
            'anomaly_detection': True
        }
    
    def start_agent(self):
        """Start Hermes autonomous agent operations."""
        if self.is_active:
            logger.warning("Hermes Agent is already active")
            return
        
        self.is_active = True
        self.stop_event.clear()
        
        # Start worker thread for continuous analysis
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"hermes-worker-{self.agent_id}"
        )
        self.worker_thread.start()
        
        logger.info(f"Hermes Agent '{self.agent_id}' started and monitoring gameplay patterns")
    
    def stop_agent(self):
        """Stop Hermes agent operations."""
        if not self.is_active:
            logger.warning("Hermes Agent is not active")
            return
        
        self.is_active = False
        self.stop_event.set()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
            self.worker_thread = None
        
        logger.info(f"Hermes Agent '{self.agent_id}' stopped")
    
    def analyze_play_style(self, game_data: Dict[str, Any], player_id: str = "current_player") -> AnalysisResult:
        """
        Analyze play style using autonomous learning algorithms.
        
        Args:
            game_data: Current gameplay data containing actions, decisions, and behaviors
            player_id: Identifier for the player being analyzed
            
        Returns:
            AnalysisResult containing recommendations and insights
        """
        if not self.is_active:
            return AnalysisResult(
                timestamp=time.time(),
                player_id=player_id,
                analysis_type="play_style",
                status=AnalysisStatus.INACTIVE,
                recommendations=["Agent is not active. Start the agent to enable analysis."],
                confidence=0.0
            )
        
        start_time = time.time()
        
        try:
            # Add to analysis queue
            analysis_request = {
                'timestamp': start_time,
                'game_data': game_data,
                'player_id': player_id,
                'priority': 'normal'
            }
            
            if self.config['auto_analyze']:
                # Process synchronously for immediate results
                return self._perform_analysis(analysis_request)
            else:
                self.analysis_queue.append(analysis_request)
                return AnalysisResult(
                    timestamp=start_time,
                    player_id=player_id,
                    analysis_type="queued",
                    status=AnalysisStatus.PENDING,
                    recommendations=["Analysis queued for processing"],
                    confidence=0.0
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Hermes Agent analysis failed for player {player_id}: {e}")
            
            # Update metrics
            self._update_performance_metrics(False, execution_time)
            
            return AnalysisResult(
                timestamp=start_time,
                player_id=player_id,
                analysis_type="play_style",
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def add_pattern_feedback(self, pattern_id: str, success: bool, outcome_data: Dict[str, Any]):
        """
        Provide feedback to Hermes agent about pattern success/failure.
        
        Args:
            pattern_id: ID of the pattern that was used
            success: Whether the pattern led to a successful outcome
            outcome_data: Additional data about the outcome
        """
        if pattern_id in self.learned_patterns:
            pattern = self.learned_patterns[pattern_id]
            pattern.success_rate = (
                pattern.success_rate * pattern.frequency + (1.0 if success else 0.0)
            ) / (pattern.frequency + 1)
            pattern.frequency += 1
            pattern.last_observed = time.time()
            
            # Update pattern characteristics based on outcome
            self._update_pattern_characteristics(pattern, outcome_data, success)
            
            logger.debug(f"Pattern feedback for {pattern_id}: success={success}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for the Hermes agent."""
        return self.performance_metrics.copy()
    
    def get_learned_patterns(self) -> List[Dict[str, Any]]:
        """Get list of learned patterns."""
        return [
            {
                'pattern_id': pid,
                'pattern_type': pattern.pattern_type.value,
                'characteristics': pattern.characteristics,
                'frequency': pattern.frequency,
                'success_rate': pattern.success_rate,
                'last_observed': pattern.last_observed
            }
            for pid, pattern in self.learned_patterns.items()
        ]
    
    def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent analyses for reference."""
        # In a real implementation, this would retrieve from a database
        # For now, return the current analysis if available
        analyses = []
        if self.current_analysis:
            analyses.append(self._analysis_to_dict(self.current_analysis))
        return analyses[:limit]
    
    def generate_adaptive_recommendations(self, game_context: Dict[str, Any]) -> List[str]:
        """
        Generate adaptive recommendations based on current game context.
        
        Args:
            game_context: Current game state and situational factors
            
        Returns:
            List of context-aware recommendations
        """
        recommendations = []
        
        # Analyze current game state
        opponent_advantage = game_context.get('opponent_advantage', 0.0)
        player_health = game_context.get('player_health', 100)
        game_phase = game_context.get('game_phase', 'mid_game')
        
        # Generate context-aware recommendations
        if opponent_advantage > 0.7:
            recommendations.extend([
                " defensive posture - focus on survival and counter-play",
                " gather information before committing to attacks",
                " utilize escape routes and positioning advantages"
            ])
        
        if player_health < 30 and game_phase != 'final':
            recommendations.extend([
                " aggressive push while health allows",
                " create scoring opportunities before healing",
                " force opponent errors with calculated risks"
            ])
        
        if game_phase == 'final':
            recommendations.extend([
                " maximize current advantage or fight to the end",
                " execute clutch plays and capitalize on pressure",
                " use all resources strategically"
            ])
        
        # Add pattern-based recommendations
        if self.config['pattern_matching_enabled']:
            pattern_recs = self._get_pattern_based_recommendations(game_context)
            recommendations.extend(pattern_recs)
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _perform_analysis(self, analysis_request: Dict[str, Any]) -> AnalysisResult:
        """Perform the actual analysis for a given request."""
        analysis_start = time.time()
        game_data = analysis_request['game_data']
        player_id = analysis_request['player_id']
        
        try:
            # Extract behavioral features
            behavioral_metrics = self._extract_behavioral_features(game_data)
            
            # Detect patterns in current behavior
            detected_patterns = self._detect_patterns(behavioral_metrics)
            
            # Generate recommendations
            recommendations = self._generate_adaptive_recommendations({
                'opponent_advantage': game_data.get('opponent_advantage', 0.0),
                'player_health': game_data.get('player_health', 100),
                'game_phase': game_data.get('game_phase', 'mid_game')
            })
            
            # Calculate confidence score
            confidence = self._calculate_analysis_confidence(
                behavioral_metrics, detected_patterns
            )
            
            # Store analysis result
            analysis_result = AnalysisResult(
                timestamp=analysis_start,
                player_id=player_id,
                analysis_type="play_style",
                status=AnalysisStatus.COMPLETED,
                recommendations=recommendations,
                confidence=confidence,
                behavioral_features=self._metrics_to_dict(behavioral_metrics),
                patterns_detected=detected_patterns,
                execution_time=time.time() - analysis_start
            )
            
            # Update performance metrics
            self._update_performance_metrics(True, analysis_result.execution_time)
            
            # Update current analysis
            self.current_analysis = analysis_result
            
            # Store in behavioral history
            self.behavioral_history.append({
                'timestamp': analysis_start,
                'player_id': player_id,
                'behavioral_metrics': self._metrics_to_dict(behavioral_metrics),
                'patterns': detected_patterns,
                'outcome': analysis_request.get('expected_outcome')
            })
            
            # Update learned patterns if needed
            if self.config['continuous_learning']:
                self._update_learned_patterns(behavioral_metrics, detected_patterns, success=True)
            
            logger.info(f"Hermes Agent analysis completed for player {player_id}: "
                       f"confidence={confidence:.2f}, patterns={len(detected_patterns)}")
            
            return analysis_result
            
        except Exception as e:
            execution_time = time.time() - analysis_start
            logger.error(f"Hermes Agent analysis error: {e}")
            
            # Update metrics
            self._update_performance_metrics(False, execution_time)
            
            return AnalysisResult(
                timestamp=analysis_start,
                player_id=player_id,
                analysis_type="play_style",
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _extract_behavioral_features(self, game_data: Dict[str, Any]) -> BehavioralMetrics:
        """Extract behavioral features from gameplay data."""
        metrics = BehavioralMetrics()
        
        # Decision speed - based on reaction time and decision latency
        metrics.decision_speed = min(1.0, max(0.0, game_data.get('decision_speed', 0.5)))
        
        # Aggression level - based on offensive actions and risk-taking
        aggression_factors = [
            game_data.get('shots_on_goal', 0) * 0.2,
            game_data.get('aggressive_plays', 0) * 0.3,
            game_data.get('risky_passes', 0) * 0.2,
            game_data.get('pressure_plays', 0) * 0.3
        ]
        metrics.aggression_level = min(1.0, sum(aggression_factors))
        
        # Adaptation rate - based on response to changing situations
        adaptation_factors = [
            game_data.get('strategy_changes', 0) * 0.4,
            game_data.get('response_to_opponent', 0) * 0.3,
            game_data.get('tactical_adjustments', 0) * 0.3
        ]
        metrics.adaptation_rate = min(1.0, sum(adaptation_factors))
        
        # Pattern consistency - based on behavioral stability
        metrics.pattern_consistency = min(1.0, max(0.0, game_data.get('pattern_stability', 0.5)))
        
        # Predictability score - based on pattern variability
        metrics.predictability_score = min(1.0, game_data.get('pattern_variance', 0.5))
        
        # Risk assessment - based on high-risk actions
        risk_factors = [
            game_data.get('high_risk_plays', 0) * 0.3,
            game_data.get('turnover_after_mistake', 0) * 0.4,
            game_data.get('loss_in_pressure', 0) * 0.3
        ]
        metrics.risk_assessment = min(1.0, sum(risk_factors))
        
        # Creativity index - based on novel actions
        metrics.creativity_index = min(1.0, game_data.get('creative_plays', 0) * 0.2)
        
        # Consistency score - based on performance under pressure
        metrics.consistency_score = min(1.0, game_data.get('performance_consistency', 0.5))
        
        return metrics
    
    def _detect_patterns(self, behavioral_metrics: BehavioralMetrics) -> List[str]:
        """Detect patterns in behavioral metrics."""
        detected_patterns = []
        
        # Pattern detection logic
        if behavioral_metrics.aggression_level > 0.7:
            detected_patterns.append("aggressive_playstyle")
        elif behavioral_metrics.aggression_level < 0.3:
            detected_patterns.append("defensive_playstyle")
        
        if behavioral_metrics.adaptation_rate > 0.7:
            detected_patterns.append("highly_adaptive")
        elif behavioral_metrics.adaptation_rate < 0.3:
            detected_patterns.append("rigid_playstyle")
        
        if behavioral_metrics.predictability_score < 0.3:
            detected_patterns.append("unpredictable_playstyle")
        elif behavioral_metrics.predictability_score > 0.7:
            detected_patterns.append("predictable_playstyle")
        
        if behavioral_metrics.decision_speed > 0.7:
            detected_patterns.append("impulsive_decisions")
        elif behavioral_metrics.decision_speed < 0.3:
            detected_patterns.append("over_analysis")
        
        # Check against learned patterns
        if self.config['pattern_matching_enabled']:
            for pattern_id, pattern in self.learned_patterns.items():
                if self._matches_pattern(behavioral_metrics, pattern):
                    detected_patterns.append(f"known_pattern:{pattern_id}")
        
        return detected_patterns
    
    def _matches_pattern(self, metrics: BehavioralMetrics, pattern: PlayPattern) -> bool:
        """Check if behavioral metrics match a stored pattern."""
        for characteristic, target_value in pattern.characteristics.items():
            current_value = getattr(metrics, characteristic, 0.0)
            if abs(current_value - target_value) < 0.2:  # Allow some variance
                continue
            else:
                return False
        return True
    
    def _generate_adaptive_recommendations(self, game_context: Dict[str, Any]) -> List[str]:
        """Generate adaptive recommendations based on game context."""
        recommendations = []
        
        opponent_advantage = game_context.get('opponent_advantage', 0.0)
        player_health = game_context.get('player_health', 100)
        game_phase = game_context.get('game_phase', 'mid_game')
        
        # Context-aware recommendations
        if opponent_advantage > 0.7:
            recommendations.extend([
                " defensive positioning - absorb pressure",
                " patient approach - wait for opponent mistakes",
                " strategic withdrawals - preserve resources"
            ])
        
        if player_health < 30 and game_phase != 'final':
            recommendations.extend([
                " controlled aggression - use burst opportunities",
                " create space before committing to attacks",
                " utilize support abilities defensively"
            ])
        
        if game_phase == 'final':
            recommendations.extend([
                " maximize current advantage",
                " clutch performance under pressure",
                " decisive action to secure victory"
            ])
        
        return recommendations[:3]
    
    def _calculate_analysis_confidence(self, metrics: BehavioralMetrics, patterns: List[str]) -> float:
        """Calculate confidence level of the analysis."""
        confidence_factors = []
        
        # Base confidence from data quality
        confidence_factors.append(0.3 if len(self.behavioral_history) > 10 else 0.1)
        
        # Confidence from pattern matching
        if patterns:
            confidence_factors.append(0.4)
        
        # Confidence from consistency
        consistency_score = metrics.pattern_consistency
        confidence_factors.append(0.2 * consistency_score)
        
        # Confidence from behavioral diversity
        diversity_score = 1.0 - (
            metrics.decision_speed + metrics.aggression_level + metrics.risk_assessment
        ) / 3.0
        confidence_factors.append(0.1 * diversity_score)
        
        return min(1.0, sum(confidence_factors))
    
    def _update_learned_patterns(self, metrics: BehavioralMetrics, detected_patterns: List[str], success: bool):
        """Update learned patterns based on new analysis."""
        if not detected_patterns:
            return
        
        # For each detected pattern, update or create
        for pattern_name in detected_patterns:
            if pattern_name.startswith("known_pattern:"):
                pattern_id = pattern_name.split(":")[1]
                if pattern_id in self.learned_patterns:
                    pattern = self.learned_patterns[pattern_id]
                    pattern.frequency += 1
                    pattern.last_observed = time.time()
            else:
                # Create new pattern entry
                pattern_id = f"{pattern_name}_{int(time.time())}"
                pattern_characteristics = self._extract_pattern_characteristics(metrics)
                
                new_pattern = PlayPattern(
                    pattern_id=pattern_id,
                    pattern_type=self._classify_pattern(pattern_name),
                    characteristics=pattern_characteristics,
                    frequency=1,
                    success_rate=1.0 if success else 0.0,
                    last_observed=time.time()
                )
                
                self.learned_patterns[pattern_id] = new_pattern
                
                # Clean up old patterns if limit exceeded
                if len(self.learned_patterns) > self.config['max_patterns']:
                    self._cleanup_old_patterns()
    
    def _extract_pattern_characteristics(self, metrics: BehavioralMetrics) -> Dict[str, float]:
        """Extract characteristics for a new pattern."""
        return {
            'decision_speed': metrics.decision_speed,
            'aggression_level': metrics.aggression_level,
            'adaptation_rate': metrics.adaptation_rate,
            'pattern_consistency': metrics.pattern_consistency,
            'predictability_score': metrics.predictability_score,
            'risk_assessment': metrics.risk_assessment,
            'creativity_index': metrics.creativity_index,
            'consistency_score': metrics.consistency_score
        }
    
    def _classify_pattern(self, pattern_name: str) -> PatternType:
        """Classify pattern name into PatternType enum."""
        classification_map = {
            "aggressive_playstyle": PatternType.AGGRESSIVE,
            "defensive_playstyle": PatternType.DEFENSIVE,
            "balanced_playstyle": PatternType.BALANCED,
            "highly_adaptive": PatternType.ADAPTIVE,
            "unpredictable_playstyle": PatternType.UNPREDICTABLE,
            "predictable_playstyle": PatternType.PREDICTABLE,
            "impulsive_decisions": PatternType.AGGRESSIVE,
            "over_analysis": PatternType.DEFENSIVE
        }
        
        return classification_map.get(pattern_name, PatternType.BALANCED)
    
    def _cleanup_old_patterns(self):
        """Remove old or low-frequency patterns."""
        patterns_to_remove = []
        
        for pattern_id, pattern in self.learned_patterns.items():
            # Remove patterns with low frequency or success rate
            if (pattern.frequency < self.config['min_pattern_frequency'] or
                pattern.success_rate < 0.3):
                patterns_to_remove.append(pattern_id)
        
        for pattern_id in patterns_to_remove:
            del self.learned_patterns[pattern_id]
    
    def _initialize_sample_patterns(self):
        """Initialize with sample patterns for better initial analysis."""
        sample_patterns = {
            "balanced_aggressive": PlayPattern(
                pattern_id="balanced_aggressive_001",
                pattern_type=PatternType.BALANCED,
                characteristics={
                    'decision_speed': 0.6,
                    'aggression_level': 0.7,
                    'adaptation_rate': 0.6,
                    'pattern_consistency': 0.7,
                    'predictability_score': 0.4,
                    'risk_assessment': 0.5,
                    'creativity_index': 0.6,
                    'consistency_score': 0.8
                },
                frequency=10,
                success_rate=0.75,
                last_observed=time.time() - 3600
            ),
            "defensive_adaptive": PlayPattern(
                pattern_id="defensive_adaptive_002",
                pattern_type=PatternType.ADAPTIVE,
                characteristics={
                    'decision_speed': 0.4,
                    'aggression_level': 0.3,
                    'adaptation_rate': 0.8,
                    'pattern_consistency': 0.8,
                    'predictability_score': 0.3,
                    'risk_assessment': 0.2,
                    'creativity_index': 0.5,
                    'consistency_score': 0.9
                },
                frequency=8,
                success_rate=0.82,
                last_observed=time.time() - 2400
            ),
            "aggressive_impulsive": PlayPattern(
                pattern_id="aggressive_impulsive_003",
                pattern_type=PatternType.AGGRESSIVE,
                characteristics={
                    'decision_speed': 0.8,
                    'aggression_level': 0.9,
                    'adaptation_rate': 0.4,
                    'pattern_consistency': 0.5,
                    'predictability_score': 0.8,
                    'risk_assessment': 0.7,
                    'creativity_index': 0.7,
                    'consistency_score': 0.6
                },
                frequency=12,
                success_rate=0.68,
                last_observed=time.time() - 1800
            )
        }
        
        self.learned_patterns.update(sample_patterns)
    
    def _update_performance_metrics(self, success: bool, response_time: float):
        """Update Hermes agent performance metrics."""
        metrics = self.performance_metrics
        
        metrics['total_analyses'] += 1
        if success:
            metrics['successful_analyses'] += 1
        
        # Update average confidence (would be calculated from actual confidence values)
        # For now, maintain a simple success rate calculation
        if metrics['total_analyses'] > 0:
            metrics['success_rate'] = metrics['successful_analyses'] / metrics['total_analyses']
        
        # Update average response time
        if metrics['total_analyses'] > 1:
            metrics['average_response_time'] = (
                (metrics['average_response_time'] * (metrics['total_analyses'] - 1)) +
                response_time
            ) / metrics['total_analyses']
        
        # Calculate pattern recognition rate
        if metrics['total_analyses'] > 0:
            total_patterns_found = sum(
                1 for analysis in self.behavioral_history
                if analysis.get('patterns')
            )
            metrics['pattern_recognition_rate'] = total_patterns_found / metrics['total_analyses']
    
    def _worker_loop(self):
        """Main worker loop for continuous processing."""
        while not self.stop_event.is_set():
            try:
                if self.analysis_queue:
                    # Process queued analysis
                    analysis_request = self.analysis_queue.pop(0)
                    self._perform_analysis(analysis_request)
                
                # Sleep before next iteration
                time.sleep(self.config['update_interval'])
                
            except Exception as e:
                logger.error(f"Hermes Agent worker loop error: {e}")
                time.sleep(1.0)  # Wait before retrying
    
    def _get_pattern_based_recommendations(self, game_context: Dict[str, Any]) -> List[str]:
        """Get recommendations based on known patterns."""
        recommendations = []
        
        # Analyze current context against patterns
        current_behavior = self._extract_behavioral_features(game_context)
        
        # Find best matching patterns
        best_matches = []
        for pattern_id, pattern in self.learned_patterns.items():
            if self._matches_pattern(current_behavior, pattern):
                similarity = self._calculate_pattern_similarity(current_behavior, pattern)
                best_matches.append((similarity, pattern_id, pattern))
        
        # Sort by similarity
        best_matches.sort(reverse=True)
        
        # Add recommendations from best matching patterns
        for similarity, pattern_id, pattern in best_matches[:2]:
            if similarity > 0.7:  # High confidence match
                recommendations.append(f"Adopt {pattern.pattern_type.value} strategy")
        
        return recommendations
    
    def _calculate_pattern_similarity(self, metrics: BehavioralMetrics, pattern: PlayPattern) -> float:
        """Calculate similarity between current metrics and pattern."""
        similarities = []
        
        for characteristic, target_value in pattern.characteristics.items():
            current_value = getattr(metrics, characteristic, 0.0)
            similarity = 1.0 - abs(current_value - target_value)
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def __del__(self):
        """Cleanup when agent is destroyed."""
        self.stop_agent()
    
    def _analysis_to_dict(self, analysis: AnalysisResult) -> Dict[str, Any]:
        """Convert AnalysisResult to dictionary."""
        return {
            'timestamp': analysis.timestamp,
            'player_id': analysis.player_id,
            'analysis_type': analysis.analysis_type.value,
            'status': analysis.status.value,
            'recommendations': analysis.recommendations,
            'confidence': analysis.confidence,
            'behavioral_features': analysis.behavioral_features,
            'patterns_detected': analysis.patterns_detected,
            'execution_time': analysis.execution_time,
            'error_message': analysis.error_message
        }
    
    def _metrics_to_dict(self, metrics: BehavioralMetrics) -> Dict[str, Any]:
        """Convert BehavioralMetrics to dictionary."""
        return {
            'decision_speed': metrics.decision_speed,
            'aggression_level': metrics.aggression_level,
            'adaptation_rate': metrics.adaptation_rate,
            'pattern_consistency': metrics.pattern_consistency,
            'predictability_score': metrics.predictability_score,
            'risk_assessment': metrics.risk_assessment,
            'creativity_index': metrics.creativity_index,
            'consistency_score': metrics.consistency_score
        }

# Create convenience function for easy initialization


def create_hermes_agent(agent_id: str = "hermes_main", config: Dict[str, Any] = None) -> HermesAgent:
    """
    Convenience function to create a Hermes agent.
    
    Args:
        agent_id: Unique identifier for the agent
        config: Configuration dictionary
        
    Returns:
        Initialized HermesAgent instance
    """
    return HermesAgent(agent_id, config)

# Export commonly used classes and functions

__all__ = [
    'HermesAgent',
    'create_hermes_agent',
    'HermesAgentConfig',
    'AnalysisResult',
    'PlayPattern',
    'BehavioralMetrics',
    'AnalysisStatus',
    'PatternType'
]