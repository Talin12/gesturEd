import cv2
import mediapipe as mp
import math

class HandTracker:
    def __init__(self, mode=False, max_hands=1, detection_confidence=0.5, tracking_confidence=0.5):
        self.mode = mode
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

    def find_hands(self, frame, draw=True):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(rgb_frame)

        if self.results.multi_hand_landmarks and draw:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
        return frame
    
    def get_hand_angle(self, frame):
        """Returns tilt angle (0-90) or None if no hand detected"""
        if not self.results or not self.results.multi_hand_landmarks:
            return None
        
        hand = self.results.multi_hand_landmarks[0]
        h, w, _ = frame.shape
        
        # Get wrist (landmark 0) and middle fingertip (landmark 12)
        wrist = hand.landmark[0]
        fingertip = hand.landmark[12]
        
        # Convert to pixel coordinates
        wrist_y = wrist.y * h
        fingertip_y = fingertip.y * h
        wrist_x = wrist.x * w
        fingertip_x = fingertip.x * w
        
        # Calculate angle
        dy = wrist_y - fingertip_y
        dx = fingertip_x - wrist_x
        
        # convert radians to degrees
        angle = math.degrees(math.atan2(dy, dx))
        
        # Normalize to 0-90 range (0 = upright, 90 = horizontal tilt)
        angle = abs(angle)
        if angle > 90:
            angle = 180 - angle
            
        return angle
    
    def is_pouring(self, angle):
        """Returns True if hand is tilted enough to pour"""
        return angle is not None and angle < 50