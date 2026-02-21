# reactions/cv_modules.py
import cv2
import math
import numpy as np
import mediapipe as mp

class HandTracker:
    """Real implementation using MediaPipe to find hand angle."""

    def __init__(self, mode=False, max_hands=1, detection_confidence=0.5, tracking_confidence=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=mode,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils

    def get_hand_position(self, frame):
        """
        Detect hand in frame, draw landmarks, and return the tilt angle.
        Returns None when no hand is detected.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if not results or not results.multi_hand_landmarks:
            return None

        hand = results.multi_hand_landmarks[0]
        
        # Draw the skeleton on the frame
        self.mp_draw.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)
        
        h, w, _ = frame.shape
        wrist = hand.landmark[0]
        fingertip = hand.landmark[12]
        
        dy = (wrist.y * h) - (fingertip.y * h)
        dx = (fingertip.x * w) - (wrist.x * w)
        
        angle = math.degrees(math.atan2(dy, dx))
        angle = abs(angle)
        if angle > 90:
            angle = 180 - angle
            
        # We return a dict to match the expected hand_pos signature
        return {"angle": angle}


class TestTube:
    """Real implementation of the interactive test tube."""
    def __init__(self, x=200, y=100, width=50, height=180):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.liquid_level = 0.7
        self.current_angle = 0
        self.is_pouring = False
        
    def set_angle(self, angle):
        """Update tilt angle from hand tracker"""
        self.current_angle = angle if angle else 0
        self.is_pouring = angle is not None and angle > 34
        
    def draw(self, frame, liquid_color):
        """Draw test tube and return whether pouring is active"""
        liquid_height = int(self.height * self.liquid_level)
        liquid_y = self.y + self.height - liquid_height
        
        # Draw liquid (filled rectangle)
        cv2.rectangle(frame,
                     (self.x + 3, liquid_y),
                     (self.x + self.width - 3, self.y + self.height - 5),
                     liquid_color, -1)
        
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
            self._draw_pouring_effect(frame, liquid_color)
            
        return self.is_pouring
    
    def _draw_pouring_effect(self, frame, liquid_color):
        """Draw liquid stream when pouring"""
        stream_start_x = self.x + self.width
        stream_start_y = self.y + 50
        stream_end_x = stream_start_x + 100
        stream_end_y = stream_start_y + 50
        
        cv2.line(frame, 
                (stream_start_x, stream_start_y),
                (stream_end_x, stream_end_y),
                liquid_color, 5)
        
        cv2.circle(frame, (stream_end_x, stream_end_y), 8, liquid_color, -1)


class VirtualLab:
    """Virtual lab that handles the full interaction logic and litmus paper."""

    def __init__(self):
        self.test_tube = TestTube(x=200, y=100)
        # Litmus paper position (placed where the stream droplet lands)
        self.litmus_rect = (330, 130, 80, 120)  # x, y, width, height
        self.reaction_triggered = False

    def draw_elements(self, frame, hand_pos, reaction_type):
        """
        Draw test tube, detect pour, and update litmus color directly on frame.
        """
        angle = hand_pos["angle"] if hand_pos else None
        self.test_tube.set_angle(angle)

        # Define colors (OpenCV uses BGR format)
        red_bgr = (40, 40, 220)
        blue_bgr = (220, 80, 40)
        
        # Setup logic based on which test is running
        if reaction_type == "red_litmus":
            # Testing with a Base: Liquid is blue, paper starts red and turns blue
            liquid_color = blue_bgr
            initial_paper_color = red_bgr
            final_paper_color = blue_bgr
        else: # "blue_litmus"
            # Testing with an Acid: Liquid is red, paper starts blue and turns red
            liquid_color = red_bgr
            initial_paper_color = blue_bgr
            final_paper_color = red_bgr

        # Draw the test tube and get pouring state
        is_pouring = self.test_tube.draw(frame, liquid_color)
        
        # If the user pours, trigger the chemical reaction permanently for this session
        if is_pouring:
            self.reaction_triggered = True

        # Draw the Litmus Paper on the screen
        current_paper_color = final_paper_color if self.reaction_triggered else initial_paper_color
        px, py, pw, ph = self.litmus_rect
        
        # Paper background
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), current_paper_color, -1)
        # Paper border
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), (200, 200, 200), 2)
        
        # Label the paper
        label = "Red Litmus" if reaction_type == "red_litmus" else "Blue Litmus"
        cv2.putText(frame, label, (px - 5, py - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Add a success message once the reaction occurs
        if self.reaction_triggered:
            cv2.putText(frame, "Reaction Complete!", (px - 30, py + ph + 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame