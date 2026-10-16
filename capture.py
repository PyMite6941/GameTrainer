"""
Capture system for tracking console gameplay via USB capture card feed.

This module handles:
1. Opening OpenCV video capture stream (index 0 or specified device)
2. Extracting specific Region-of-Interest (ROI) coordinates for opponent tracking
3. Logging frame data (timestamp, estimated X/Y coordinates, state) into local SQLite database
"""

import cv2
import numpy as np
import sqlite3
import time
from pathlib import Path
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameCapture:
    def __init__(self, device_index: int = 0, output_dir: str = "./data"):
        self.device_index = device_index
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.db_path = self.output_dir / "gameplay.db"
        self.cap = None
        self.roi_coords = None  # Format: (x1, y1, x2, y2)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with gameplay tracking tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create frames table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                frame_number INTEGER NOT NULL,
                roi_x INTEGER,
                roi_y INTEGER,
                roi_width INTEGER,
                roi_height INTEGER,
                opponent_x INTEGER,
                opponent_y INTEGER,
                opponent_state TEXT,
                frame_data BLOB
            )
        ''')
        
        # Create game_states table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                player_health INTEGER,
                current_animation TEXT,
                action_state TEXT,
                level TEXT,
                game_mode TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def set_roi(self, x1: int, y1: int, x2: int, y2: int):
        """Set Region-of-Interest coordinates for opponent tracking."""
        self.roi_coords = (x1, y1, x2, y2)
        logger.info(f"ROI set to: {self.roi_coords}")
    
    def start_capture(self):
        """Start video capture from device."""
        self.cap = cv2.VideoCapture(self.device_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video device {self.device_index}")
        
        # Get video properties
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Capture started: {self.width}x{self.height} @ {self.fps}fps")
        return self.fps, self.width, self.height
    
    def stop_capture(self):
        """Stop video capture."""
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("Capture stopped")
    
    def extract_roi(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Extract Region-of-Interest from frame."""
        if not self.roi_coords:
            return None
        
        x1, y1, x2, y2 = self.roi_coords
        return frame[y1:y2, x1:x2]
    
    def detect_opponent(self, roi_frame: np.ndarray) -> Tuple[Optional[int], Optional[int], str]:
        """
        Detect opponent in ROI frame.
        
        Returns:
            Tuple of (x, y, state) or (None, None, "none") if not detected
        """
        if roi_frame is None or roi_frame.size == 0:
            return None, None, "none"
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        
        # TODO: Implement actual opponent detection logic
        # This is a placeholder - would use template matching, YOLO, or other ML model
        # For now, return a simple test detection
        
        # Simple blob detection as placeholder
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour (most likely opponent)
            largest_contour = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"]) + self.roi_coords[0]
                cy = int(M["m01"] / M["m00"]) + self.roi_coords[1]
                return cx, cy, "detected"
        
        return None, None, "none"
    
    def log_frame(self, frame_num: int, opponent_x: Optional[int], 
                  opponent_y: Optional[int], opponent_state: str,
                  game_data: dict = None):
        """Log frame data to database."""
        timestamp = time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert frame to bytes for storage
        frame_bytes = None
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                _, frame_bytes = cv2.imencode('.jpg', frame)
                frame_bytes = frame_bytes.tobytes()
        
        cursor.execute('''
            INSERT INTO frames 
            (timestamp, frame_number, roi_x, roi_y, roi_width, roi_height,
             opponent_x, opponent_y, opponent_state, frame_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, frame_num,
            self.roi_coords[0] if self.roi_coords else None,
            self.roi_coords[1] if self.roi_coords else None,
            (self.roi_coords[2] - self.roi_coords[0]) if self.roi_coords else None,
            (self.roi_coords[3] - self.roi_coords[1]) if self.roi_coords else None,
            opponent_x, opponent_y, opponent_state, frame_bytes
        ))
        
        # Log game state if provided
        if game_data:
            cursor.execute('''
                INSERT INTO game_states
                (timestamp, player_health, current_animation, action_state, level, game_mode)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                game_data.get('player_health'),
                game_data.get('current_animation'),
                game_data.get('action_state'),
                game_data.get('level'),
                game_data.get('game_mode')
            ))
        
        conn.commit()
        conn.close()
    
    def process_frame(self, frame_num: int, game_data: dict = None):
        """Process a single frame: extract ROI, detect opponent, log data."""
        if not self.cap:
            return
        
        ret, frame = self.cap.read()
        if not ret:
            logger.warning(f"Failed to read frame {frame_num}")
            return
        
        # Extract ROI for opponent tracking
        roi_frame = self.extract_roi(frame)
        
        # Detect opponent in ROI
        opponent_x, opponent_y, opponent_state = self.detect_opponent(roi_frame)
        
        # Log frame data
        self.log_frame(frame_num, opponent_x, opponent_y, opponent_state, game_data)
        
        logger.debug(f"Frame {frame_num}: opponent at ({opponent_x}, {opponent_y}), state: {opponent_state}")
        
        return {
            'timestamp': time.time(),
            'frame_num': frame_num,
            'opponent_x': opponent_x,
            'opponent_y': opponent_y,
            'opponent_state': opponent_state,
            'roi_detected': roi_frame is not None
        }


def main():
    """Example usage of GameCapture."""
    # Initialize capture
    capture = GameCapture(device_index=0, output_dir="./data")
    
    # Set up ROI for opponent tracking (adjust coordinates based on your game)
    # Example: tracking an area in the bottom half of the screen
    _, _, height, _ = capture.start_capture()
    capture.set_roi(400, 300, 800, 500)  # (x1, y1, x2, y2)
    
    print("Starting frame capture (press Ctrl+C to stop)...")
    
    try:
        for frame_num in range(1000):  # Capture 1000 frames
            game_data = {
                'player_health': 100 - (frame_num * 0.1),
                'current_animation': 'idle',
                'action_state': 'standing',
                'level': 'tutorial',
                'game_mode': 'single_player'
            }
            
            result = capture.process_frame(frame_num, game_data)
            if result and result['roi_detected']:
                print(f"Frame {result['frame_num']}: Opponent detected at ({result['opponent_x']}, {result['opponent_y']})")
            
            time.sleep(1.0 / 30.0)  # 30 FPS target
    except KeyboardInterrupt:
        print("\nCapture stopped by user")
    finally:
        capture.stop_capture()

if __name__ == "__main__":
    main()