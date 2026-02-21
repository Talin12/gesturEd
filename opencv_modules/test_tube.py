import cv2
import numpy as np

class TestTube:
    def __init__(self, x=300, y=300, width=50, height=180):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.liquid_level = 0.7
        self.liquid_color = (200, 200, 255)  # Light blue (BGR)
        self.current_angle = 0  # Tilt angle
        self.is_pouring = False
        
    def set_angle(self, angle):
        """Update tilt angle from hand tracker"""
        self.current_angle = angle if angle else 0
        self.is_pouring = angle is not None and angle > 34
        
    def draw(self, frame):
        """Draw test tube at current angle"""
        
        # Calculate liquid height
        liquid_height = int(self.height * self.liquid_level)
        liquid_y = self.y + self.height - liquid_height
        
        # Draw liquid (filled rectangle)
        cv2.rectangle(frame,
                     (self.x + 3, liquid_y),
                     (self.x + self.width - 3, self.y + self.height - 5),
                     self.liquid_color, -1)
        
        # Draw glass outline
        cv2.rectangle(frame,
                     (self.x, self.y),
                     (self.x + self.width, self.y + self.height),
                     (100, 100, 100), 3)
        
        # Draw rounded bottom
        cv2.ellipse(frame,
                   (self.x + self.width // 2, self.y + self.height),
                   (self.width // 2, 12),
                   0, 0, 180,
                   (100, 100, 100), 3)
        
        # Draw pouring effect if tilted
        if self.is_pouring:
            self._draw_pouring_effect(frame)
            
        return frame
    
    def _draw_pouring_effect(self, frame):
        """Draw liquid stream when pouring"""
        # Stream starts from tube opening
        stream_start_x = self.x + self.width
        stream_start_y = self.y + 50
        
        # Stream goes toward litmus paper (right side)
        stream_end_x = stream_start_x + 100
        stream_end_y = stream_start_y + 50
        
        # Draw stream line
        cv2.line(frame, 
                (stream_start_x, stream_start_y),
                (stream_end_x, stream_end_y),
                self.liquid_color, 5)
        
        # Draw droplet at end
        cv2.circle(frame, (stream_end_x, stream_end_y), 8, self.liquid_color, -1)