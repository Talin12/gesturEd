# reactions/opencv_handler.py
import cv2
import math
import sys
import os
import threading

# ── Point to your opencv_modules folder ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../opencv_modules'))

from hand_tracker import HandTracker
from test_tube import TestTube
from litmus_paper import LitmusPaper

# ── Color map: chemical type → (liquid_color BGR, paper_color BGR) ────────────
CHEMICAL_COLORS = {
    'acid':    ((60,  60,  220), (60,  60,  220)),  # red liquid, red paper
    'base':    ((200, 80,  40),  (200, 80,  40)),   # blue liquid, blue paper
    'neutral': ((200, 200, 255), (210, 230, 240)),  # clear liquid, cream paper
}

def generate_frames(reaction_type):
    """
    Drop-in replacement for the original generate_frames.
    Reads chemical type from Django cache each frame so color
    updates live when user clicks a chemical in the UI.
    """
    from django.core.cache import cache

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        return

    tracker = HandTracker()
    tube    = TestTube(x=350, y=150, width=60, height=200)
    paper   = LitmusPaper(x=310, y=420, width=90, height=130)

    # Set initial paper color based on reaction type
    # red_litmus starts red, blue_litmus starts blue
    if reaction_type == 'red_litmus':
        paper.base_color    = (60, 60, 220)
        paper.current_color = [60, 60, 220]
        paper.target_color  = [60, 60, 220]
    elif reaction_type == 'blue_litmus':
        paper.base_color    = (200, 80, 40)
        paper.current_color = [200, 80, 40]
        paper.target_color  = [200, 80, 40]

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)

            # ── Read selected chemical from cache (set by set_chemical_view) ──
            chemical_type = cache.get('active_chemical_type', 'neutral')
            liquid_color, _ = CHEMICAL_COLORS.get(chemical_type, CHEMICAL_COLORS['neutral'])
            tube.liquid_color = liquid_color

            # ── Hand tracking ─────────────────────────────────────────────────
            frame = tracker.find_hands(frame)
            angle = tracker.get_hand_angle(frame)
            tube.set_angle(angle)

            # ── Draw paper first (behind tube) ────────────────────────────────
            frame = paper.draw(frame)

            # ── Draw tube ─────────────────────────────────────────────────────
            frame = tube.draw(frame)

            # ── Connect pour stream to litmus paper ───────────────────────────
            if tube.is_pouring and tube.liquid_level > 0:
                angle_rad   = math.radians(tube.display_angle)
                pivot_x     = tube.x + tube.width // 2
                pivot_y     = tube.y
                mouth_off_x = -(tube.width // 2)
                stream_x    = int(pivot_x + mouth_off_x * math.cos(angle_rad))
                stream_y    = int(pivot_y + mouth_off_x * math.sin(angle_rad))
                end_x       = stream_x - 45
                end_y       = stream_y + 130
                paper.receive_liquid(end_x, end_y + 85, liquid_color)

            # ── HUD: show current chemical type ───────────────────────────────
            cv2.putText(frame, f"Chemical: {chemical_type}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)
            if tube.is_pouring:
                cv2.putText(frame, "POURING",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 60, 220), 2)

            # ── Encode and yield MJPEG frame ──────────────────────────────────
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            )

    finally:
        camera.release()