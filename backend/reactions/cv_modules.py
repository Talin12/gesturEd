# reactions/cv_modules.py
# Create this file inside your `reactions` app folder (same level as reactions/opencv_handler.py)
#
# ─── FOR PERSON 1 ────────────────────────────────────────────────────────────
# This file is your integration point. Replace the two mock classes below with
# your real implementations. The method signatures MUST stay the same so the
# pipeline in opencv_handler.py doesn't break.
#
#   HandTracker.get_hand_position(frame)
#       → receives a raw BGR frame (numpy array)
#       → return anything that describes hand position (dict, tuple, None, etc.)
#         the return value is passed directly into VirtualLab.draw_elements()
#
#   VirtualLab.draw_elements(frame, hand_pos, reaction_type)
#       → receives the raw frame, your hand_pos output, and the reaction_type
#         string ("red_litmus" or "blue_litmus")
#       → must return the processed frame (numpy array, same shape as input)
# ─────────────────────────────────────────────────────────────────────────────

import cv2


class HandTracker:
    """Mock hand tracker — replace with your MediaPipe/CV implementation."""

    def __init__(self):
        # Person 1: initialize your hand tracking model here
        pass

    def get_hand_position(self, frame):
        """
        Detect hand in frame and return position data.
        Returns None when no hand is detected.
        """
        # Mock: always returns a fixed centre point
        h, w = frame.shape[:2]
        return {"x": w // 2, "y": h // 2}


class VirtualLab:
    """Mock virtual lab — replace with your test tube / litmus logic."""

    def __init__(self):
        # Person 1: initialize any state (collision tracking, color state) here
        pass

    def draw_elements(self, frame, hand_pos, reaction_type):
        """
        Draw test tube, detect collision with hand, and update litmus color.
        Must return the annotated frame (numpy array).
        """
        # Mock: just overlays a placeholder text so the stream looks alive
        color = (0, 0, 255) if reaction_type == "red_litmus" else (255, 0, 0)
        label = f"[MOCK] reaction: {reaction_type}"
        cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        if hand_pos:
            cv2.circle(frame, (hand_pos["x"], hand_pos["y"]), 10, color, -1)

        return frame