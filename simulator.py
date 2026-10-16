"""
Game training simulator for opponent behavior reproduction.

This module provides a lightweight Pygame/Python environment that:
1. Loads opponent summary profiles from JSON
2. Recreates basic platform map layouts
3. Spawns recorded bot "mesh" that mirrors tracked opponent movement patterns
"""

import pygame
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

@dataclass
class Position:
    """2D position with optional metadata."""
    x: float
    y: float
    timestamp: float = 0.0
    state: str = "idle"
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class MovementVector:
    """Movement vector with magnitude and direction."""
    dx: float
    dy: float
    magnitude: float
    direction: float  # radians
    
    def __post_init__(self):
        self.magnitude = math.sqrt(self.dx**2 + self.dy**2)
        self.direction = math.atan2(self.dy, self.dx) if self.magnitude > 0 else 0.0

class GameObject:
    """Base game object with position and movement."""
    
    def __init__(self, x: float, y: float, width: int = 32, height: int = 32):
        self.position = Position(x, y)
        self.width = width
        self.height = height
        self.velocity = MovementVector(0, 0, 0, 0)
        self.state = GameState.IDLE
        self.bbox = pygame.Rect(x, y, width, height)
    
    def update_bbox(self):
        """Update bounding box based on position."""
        self.bbox.x = int(self.position.x)
        self.bbox.y = int(self.position.y)
    
    def collides_with(self, other: 'GameObject') -> bool:
        """Check collision with another game object."""
        return self.bbox.colliderect(other.bbox)

class Platform(GameObject):
    """Static platform object."""
    
    def __init__(self, x: float, y: float, width: int, height: int, color=(100, 100, 100)):
        super().__init__(x, y, width, height)
        self.color = color
        self.state = GameState.IDLE

class Player(GameObject):
    """Player character with control logic."""
    
    def __init__(self, x: float, y: float, color=(0, 255, 0)):
        super().__init__(x, y, 64, 64)
        self.color = color
        self.state = GameState.IDLE
        self.jump_power = -15
        self.gravity = 0.8
        self.on_ground = False
        self.health = 100
        self.movement_history = []
    
    def move_left(self, amount: float = 5.0):
        """Move player left."""
        self.position.x -= amount
        self.velocity.dx = -amount
        self.state = GameState.RUNNING
        self.movement_history.append(('left', self.position.x, self.position.y))
    
    def move_right(self, amount: float = 5.0):
        """Move player right."""
        self.position.x += amount
        self.velocity.dx = amount
        self.state = GameState.RUNNING
        self.movement_history.append(('right', self.position.x, self.position.y))
    
    def jump(self):
        """Make player jump if on ground."""
        if self.on_ground:
            self.velocity.dy = self.jump_power
            self.state = GameState.RUNNING
            self.movement_history.append(('jump', self.position.x, self.position.y))
            self.on_ground = False
    
    def apply_gravity(self):
        """Apply gravity to player."""
        self.velocity.dy += self.gravity
        self.position.y += self.velocity.dy
        self.on_ground = False
    
    def update(self):
        """Update player state."""
        self.apply_gravity()
        self.update_bbox()
        
        # Simple ground collision (bottom of screen)
        if self.position.y + self.height >= 600:  # Assuming screen height
            self.position.y = 600 - self.height
            self.velocity.dy = 0
            self.on_ground = True

class OpponentMesh(GameObject):
    """Opponent AI that reproduces recorded movement patterns."""
    
    def __init__(self, profile: Dict[str, Any], x: float = None, y: float = None):
        # Set starting position based on profile or default
        if x is None or y is None:
            x, y = self._get_start_position_from_profile(profile)
        
        super().__init__(x, y, 32, 32)
        self.color = (255, 0, 0)  # Red for opponent
        self.state = GameState.IDLE
        
        # Load movement patterns from profile
        self.movement_patterns = self._extract_movement_patterns(profile)
        self.current_pattern_index = 0
        self.current_pattern_step = 0
        self.current_action_state = "idle"
        self.action_timer = 0
        
        # Create predictive movement vectors
        self.predicted_positions = []
        self.generate_predicted_movement()
    
    def _get_start_position_from_profile(self, profile: Dict[str, Any]) -> tuple:
        """Get starting position from profile centroid."""
        movement = profile.get('movement_patterns', {})
        spatial = movement.get('spatial_distribution', {})
        centroid = spatial.get('centroid', {'x': 400, 'y': 300})
        return centroid['x'], centroid['y']
    
    def _extract_movement_patterns(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract movement patterns from opponent profile."""
        movement = profile.get('movement_patterns', {})
        
        return {
            'directions': movement.get('movement_directions', {}).get('directions', {}),
            'velocity_stats': movement.get('movement_velocity', {}),
            'clusters': movement.get('position_clusters', []),
            'preferred_zones': movement.get('spatial_distribution', {}).get('zone_preference', []),
            'actions': profile.get('action_states', {}).get('action_frequencies', {})
        }
    
    def generate_predicted_movement(self):
        """Generate predicted movement path based on recorded patterns."""
        if not self.movement_patterns:
            return
        
        directions = self.movement_patterns['directions']
        if not directions:
            return
        
        # Generate 100 predicted positions
        self.predicted_positions = []
        base_x, base_y = self.position.x, self.position.y
        
        for i in range(100):
            # Choose direction based on profile weights
            direction_weights = {
                'right': directions.get('right', 0),
                'left': directions.get('left', 0),
                'up': directions.get('up', 0),
                'down': directions.get('down', 0)
            }
            
            # Normalize weights
            total_weight = sum(direction_weights.values())
            if total_weight == 0:
                break
            
            # Choose direction
            rand_val = random.uniform(0, total_weight)
            cumulative = 0
            chosen_direction = None
            
            for direction, weight in direction_weights.items():
                cumulative += weight
                if rand_val <= cumulative:
                    chosen_direction = direction
                    break
            
            if chosen_direction:
                # Add some randomness and movement magnitude
                base_speed = self.movement_patterns['velocity_stats'].get('average_speed', 5.0)
                speed_variation = random.uniform(0.5, 1.5) * base_speed
                
                if chosen_direction == 'right':
                    dx = speed_variation * random.uniform(0.8, 1.2)
                    dy = random.uniform(-2, 2)
                elif chosen_direction == 'left':
                    dx = -speed_variation * random.uniform(0.8, 1.2)
                    dy = random.uniform(-2, 2)
                elif chosen_direction == 'up':
                    dx = random.uniform(-2, 2)
                    dy = -speed_variation * random.uniform(0.8, 1.2)
                else:  # down
                    dx = random.uniform(-2, 2)
                    dy = speed_variation * random.uniform(0.8, 1.2)
                
                base_x += dx
                base_y += dy
                
                self.predicted_positions.append(Position(base_x, base_y, i, chosen_direction))
    
    def update(self, player_pos: Position = None, dt: float = 1.0):
        """Update opponent mesh position and behavior."""
        # Use predicted movement if available
        if self.predicted_positions and self.current_pattern_index < len(self.predicted_positions):
            target_pos = self.predicted_positions[self.current_pattern_index]
            
            # Move toward target position
            dx = target_pos.x - self.position.x
            dy = target_pos.y - self.position.y
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 1:
                # Move with some speed
                speed = self.movement_patterns['velocity_stats'].get('average_speed', 3.0)
                move_factor = min(speed * dt / distance, 1.0)
                
                self.position.x += dx * move_factor
                self.position.y += dy * move_factor
                
                # Update velocity
                self.velocity = MovementVector(dx * move_factor, dy * move_factor, distance * move_factor, math.atan2(dy, dx))
                
                self.current_pattern_index += 1
                self.state = GameState.RUNNING
            else:
                # Reached target, generate new predictions
                self.current_pattern_index = 0
                self.generate_predicted_movement()
        else:
            # Fallback: random movement if no predictions available
            self.state = self._choose_random_action()
            self._execute_action()
        
        # Simple state machine based on player proximity
        if player_pos:
            distance_to_player = self.position.distance_to(player_pos)
            if distance_to_player < 50:  # Close proximity
                self.state = GameState.RUNNING
                # Could trigger recorded counter-attack here
                # This would be where you'd replay the opponent's recorded response
                self.current_action_state = "counter_attack"
            elif distance_to_player > 200:
                self.current_action_state = "patrol"
            else:
                self.current_action_state = "approach"
        
        self.update_bbox()
    
    def _choose_random_action(self) -> GameState:
        """Choose random action based on profile weights."""
        if not self.movement_patterns['directions']:
            return GameState.IDLE
        
        directions = self.movement_patterns['directions']
        # Choose direction with higher probability
        choices = ['right', 'left', 'up', 'down']
        weights = [directions.get(d, 0) for d in choices]
        
        if sum(weights) == 0:
            return GameState.IDLE
        
        return random.choices(choices, weights=weights)[0]
    
    def _execute_action(self):
        """Execute chosen action."""
        if not hasattr(self, 'current_action'):
            return
        
        if self.current_action == 'right':
            self.position.x += random.uniform(1, 3)
        elif self.current_action == 'left':
            self.position.x -= random.uniform(1, 3)
        elif self.current_action == 'up':
            self.position.y -= random.uniform(1, 3)
        elif self.current_action == 'down':
            self.position.y += random.uniform(1, 3)
    
    def draw(self, screen: pygame.Surface):
        """Draw opponent mesh to screen."""
        color = self._get_color_for_state()
        pygame.draw.rect(screen, color, self.bbox)
        
        # Draw predicted path (last 10 positions)
        if len(self.predicted_positions) > 10:
            for i in range(max(0, self.current_pattern_index - 10), self.current_pattern_index):
                if i < len(self.predicted_positions):
                    pos = self.predicted_positions[i]
                    pygame.draw.circle(screen, (255, 255, 255, 50), 
                                     (int(pos.x), int(pos.y)), 2)
    
    def _get_color_for_state(self) -> tuple:
        """Get color based on current state."""
        color_map = {
            GameState.IDLE: (100, 100, 100),
            GameState.RUNNING: (255, 0, 0),
            GameState.PAUSED: (255, 255, 0),
            GameState.COMPLETED: (0, 255, 0)
        }
        return color_map.get(self.state, (255, 0, 0))
class TrainingSimulator:
    """Main training simulator controller."""
    
    def __init__(self, profile_path: str = None, profile_data: Dict[str, Any] = None):
        pygame.init()
        
        # Initialize display
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Game Training Simulator")
        
        # Load profile
        if profile_path and Path(profile_path).exists():
            with open(profile_path, 'r') as f:
                self.profile = json.load(f)
        elif profile_data:
            self.profile = profile_data
        else:
            self.profile = self._get_default_profile()
        
        # Initialize game objects
        self.platforms = []
        self.player = None
        self.opponent = None
        self.state = GameState.IDLE
        
        # Create game world
        self._create_platform_map()
        self._spawn_player()
        self._spawn_opponent()
        
        # Create UI elements
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        logger.info("Training simulator initialized")
    
    def _get_default_profile(self) -> Dict[str, Any]:
        """Get default profile if none available."""
        return {
            'movement_patterns': {
                'spatial_distribution': {
                    'centroid': {'x': 400, 'y': 300},
                    'zone_preference': [('bottom_right', {'count': 1})]
                },
                'movement_directions': {
                    'directions': {'right': 25, 'up': 25, 'left': 25, 'down': 25}
                },
                'velocity_stats': {'average_speed': 5.0, 'max_speed': 15.0}
            },
            'action_states': {
                'action_frequencies': {'idle': 50, 'moving': 50}
            }
        }
    
    def _create_platform_map(self):
        """Create platform map based on game genre."""
        # Simple platform generation - could be enhanced for specific genres
        self.platforms = []
        
        # Ground platform
        ground = Platform(0, 550, 800, 50, (50, 50, 50))
        self.platforms.append(ground)
        
        # Random platforms for obstacle practice
        for i in range(5):
            x = random.randint(100, 700)
            y = random.randint(200, 400)
            width = random.randint(60, 120)
            height = random.randint(10, 20)
            platform = Platform(x, y, width, height, (100, 100, 100))
            self.platforms.append(platform)
    
    def _spawn_player(self):
        """Spawn player character."""
        self.player = Player(100, 500)
    
    def _spawn_opponent(self):
        """Spawn opponent based on profile."""
        self.opponent = OpponentMesh(self.profile, 600, 300)
    
    def handle_input(self):
        """Handle user input."""
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT]:
            self.player.move_left()
        if keys[pygame.K_RIGHT]:
            self.player.move_right()
        if keys[pygame.K_UP]:
            self.player.jump()
        if keys[pygame.K_SPACE]:
            self.player.jump()
        if keys[pygame.K_r]:
            # Reset opponent position
            if self.opponent:
                self.opponent.generate_predicted_movement()
        if keys[pygame.K_p]:
            # Pause/resume
            self.state = GameState.PAUSED if self.state == GameState.RUNNING else GameState.RUNNING
        if keys[pygame.K_ESCAPE]:
            self.state = GameState.COMPLETED
    
    def update(self, dt: float = 1.0):
        """Update game state."""
        if self.state != GameState.RUNNING:
            return
        
        # Handle player input and update
        self.handle_input()
        
        # Update player
        if self.player:
            self.player.update()
        
        # Update opponent
        if self.opponent:
            self.opponent.update(self.player.position if self.player else None, dt)
        
        # Check collisions
        self._check_collisions()
    
    def _check_collisions(self):
        """Check collisions between game objects."""
        # Platform collisions for player
        if self.player:
            for platform in self.platforms:
                if self.player.collides_with(platform):
                    # Simple platform collision response
                    if self.player.velocity.dy > 0:  # Falling down
                        self.player.position.y = platform.position.y - self.player.height
                        self.player.velocity.dy = 0
                        self.player.on_ground = True
                    elif self.player.velocity.dy < 0:  # Jumping up
                        self.player.position.y = platform.position.y + platform.height
                        self.player.velocity.dy = 0
        
        # Player-opponent collision detection
        if self.player and self.opponent and self.player.collides_with(self.opponent):
            # Trigger opponent response (replay recorded counter-play)
            self.opponent.current_action_state = "counter_attack"
            # Could trigger state machine replay here
    
    def draw(self):
        """Draw game world."""
        # Clear screen
        self.screen.fill((0, 0, 0))
        
        # Draw platforms
        for platform in self.platforms:
            pygame.draw.rect(self.screen, platform.color, platform.bbox)
        
        # Draw player
        if self.player:
            pygame.draw.rect(self.screen, self.player.color, self.player.bbox)
        
        # Draw opponent
        if self.opponent:
            self.opponent.draw(self.screen)
        
        # Draw UI
        self._draw_ui()
        
        # Update display
        pygame.display.flip()
    
    def _draw_ui(self):
        """Draw UI elements."""
        # FPS counter
        fps_text = self.small_font.render(f"FPS: {int(1/dt) if dt > 0 else 0}", True, (255, 255, 255))
        self.screen.blit(fps_text, (10, 10))
        
        # Game state
        state_text = self.small_font.render(f"State: {self.state.value}", True, (255, 255, 255))
        self.screen.blit(state_text, (10, 50))
        
        # Opponent status
        if self.opponent:
            status_text = self.small_font.render(f"Opponent: {self.opponent.current_action_state}", True, (255, 255, 255))
            self.screen.blit(status_text, (10, 90))
        
        # Instructions
        instructions = [
            "LEFT/RIGHT: Move",
            "UP/SPACE: Jump",
            "R: Reset Opponent",
            "P: Pause/Resume",
            "ESC: Quit"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (600, 10 + i * 30))
    
    def run(self, target_fps: int = 60):
        """Run the training simulator."""
        self.state = GameState.RUNNING
        clock = pygame.time.Clock()
        
        logger.info("Starting training simulator")
        
        while self.state != GameState.COMPLETED:
            dt = clock.tick(target_fps) / 1000.0  # Convert to seconds
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = GameState.COMPLETED
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.COMPLETED
            
            # Update game
            self.update(dt)
            
            # Draw game
            self.draw()
        
        # Cleanup
        pygame.quit()
        logger.info("Training simulator completed")


def main():
    """Example usage of TrainingSimulator."""
    print("Starting Game Training Simulator...")
    
    # Option 1: Load from existing profile
    simulator = TrainingSimulator()
    
    # Option 2: Run with a specific profile file
    # simulator = TrainingSimulator("./data/opponent_profile.json")
    
    # Option 3: Run with profile data
    # with open("./data/opponent_profile.json", 'r') as f:
    #     profile_data = json.load(f)
    # simulator = TrainingSimulator(profile_data=profile_data)
    
    simulator.run()

if __name__ == "__main__":
    main()