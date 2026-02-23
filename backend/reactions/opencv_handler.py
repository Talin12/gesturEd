# backend/reactions/opencv_handler.py

import sys
import math
import threading
import time
import cv2
import numpy as np

sys.path.insert(0, '/Users/talindaga/Desktop/Desktop/ChemLabs/opencv_modules')

from hand_tracker import HandTracker
from test_tube import TestTube
from litmus_paper import LitmusPaper
from .stream_state import state, HEARTBEAT_TIMEOUT

_latest_frame = None
_frame_lock   = threading.Lock()
_frame_ready  = threading.Event()
_lab_thread   = None

# All solutions are visually colorless/clear — chemistry drives paper color, not liquid color
CHEMICAL_COLORS = {
    "acid":    (245, 245, 245),
    "base":    (245, 245, 245),
    "neutral": (245, 245, 245),
}

# Initial paper colors per test type (BGR)
PAPER_INIT = {
    "red_litmus":  (40, 40, 220),   # red in BGR
    "blue_litmus": (220, 80, 40),   # blue in BGR
}

# Target paper color after a valid reaction (BGR)
REACTION_RESULT_COLOR = {
    "red_litmus":  (220, 80, 40),   # red litmus + base  → turns blue
    "blue_litmus": (40, 40, 220),   # blue litmus + acid → turns red
}


def get_latest_frame():
    with _frame_lock:
        return _latest_frame


def get_frame_event():
    """Expose the Event so the generator can wait on it."""
    return _frame_ready


def _run_lab():
    global _latest_frame

    print("DEBUG: _run_lab started")

    camera = None
    for idx in range(3):
        print(f"DEBUG: Trying camera index {idx}")
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            camera = cap
            print(f"DEBUG: Camera opened at index {idx}")
            break
        cap.release()

    if camera is None or not camera.isOpened():
        print("DEBUG: ERROR — no camera found")
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "CAMERA ERROR / ACCESS DENIED", (50, 240),
                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", error_frame)
        with _frame_lock:
            _latest_frame = buffer.tobytes()
        _frame_ready.set()
        print(f"DEBUG: Error frame written ({len(_latest_frame)} bytes)")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    tracker = HandTracker()
    tube    = TestTube(x=350, y=150, width=60, height=200)
    paper   = LitmusPaper(x=50, y=310, width=120, height=140)

    reaction_type    = state.get("reaction_type") or "red_litmus"
    current_reaction = reaction_type
    reaction_triggered = False

    init_color = PAPER_INIT.get(reaction_type, PAPER_INIT["red_litmus"])
    paper.base_color    = init_color
    paper.current_color = list(init_color)
    paper.target_color  = list(init_color)

    frame_count = 0

    try:
        while state.get("running", False):

            # ── Idle timeout ─────────────────────────────────────────────────
            last_hb = state.get("last_heartbeat", 0.0)
            if last_hb > 0.0 and (time.time() - last_hb) > HEARTBEAT_TIMEOUT:
                print("DEBUG: heartbeat timeout — releasing lab lock")
                state["running"]                = False
                state["owner"]                  = None
                state["reaction_type"]          = None
                state["chemical_id"]            = None
                state["chemical_type"]          = "neutral"
                state["reaction_complete_flag"] = False
                state["last_heartbeat"]         = 0.0
                break
            # ─────────────────────────────────────────────────────────────────

            success, frame = camera.read()
            print(f"DEBUG: camera.read() success={success}, frame_count={frame_count}")

            if not success:
                print("DEBUG: camera.read() failed — breaking loop")
                break

            frame = cv2.flip(frame, 1)

            new_reaction = state.get("reaction_type") or "red_litmus"
            if new_reaction != current_reaction:
                current_reaction   = new_reaction
                reaction_triggered = False
                init_color = PAPER_INIT.get(new_reaction, PAPER_INIT["red_litmus"])
                paper.base_color    = init_color
                paper.current_color = list(init_color)
                paper.target_color  = list(init_color)
                paper.wet_spots     = []

            chemical_type = state.get("chemical_type", "neutral")
            # All liquids render colorless — tube shows clear solution
            liquid_color  = CHEMICAL_COLORS.get(chemical_type, CHEMICAL_COLORS["neutral"])
            tube.liquid_color = liquid_color

            frame = tracker.find_hands(frame)
            angle = tracker.get_hand_angle(frame)
            tube.set_angle(angle)

            frame = paper.draw(frame)
            frame = tube.draw(frame)

            if tube.is_pouring and tube.liquid_level > 0:
                angle_rad   = math.radians(tube.display_angle)
                pivot_x     = tube.x + tube.width // 2
                pivot_y     = tube.y
                mouth_off_x = -(tube.width // 2)
                stream_x    = int(pivot_x + mouth_off_x * math.cos(angle_rad))
                stream_y    = int(pivot_y + mouth_off_x * math.sin(angle_rad))
                end_x       = stream_x - 45
                end_y       = stream_y + 130
                splash_y    = end_y + 85

                # Wet the paper (no hue shift — just wetness)
                paper.receive_liquid(end_x, splash_y, liquid_color)

                if not reaction_triggered:
                    reacts = (
                        (current_reaction == "blue_litmus" and chemical_type == "acid") or
                        (current_reaction == "red_litmus"  and chemical_type == "base")
                    )
                    px, py, pw, ph = paper.x, paper.y, paper.width, paper.height
                    if reacts and px <= end_x <= px + pw and py <= splash_y <= py + ph:
                        reaction_triggered = True
                        state["reaction_complete_flag"] = True
                        # Chemistry override: set paper to the correct indicator color
                        result_color = REACTION_RESULT_COLOR[current_reaction]
                        paper.target_color = list(result_color)

            if reaction_triggered:
                fh, fw = frame.shape[:2]
                by      = fh // 2 - 38
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, by), (fw, by + 68), (8, 8, 8), -1)
                cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
                cv2.putText(frame, "REACTION COMPLETE",
                            (fw // 2 - 188, by + 46),
                            cv2.FONT_HERSHEY_DUPLEX, 1.25, (0, 180, 80), 4, cv2.LINE_AA)
                cv2.putText(frame, "REACTION COMPLETE",
                            (fw // 2 - 188, by + 46),
                            cv2.FONT_HERSHEY_DUPLEX, 1.25, (0, 255, 120), 2, cv2.LINE_AA)

            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            with _frame_lock:
                _latest_frame = buffer.tobytes()

            _frame_ready.set()

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"DEBUG: {frame_count} frames written, latest={len(_latest_frame)} bytes")

    finally:
        print(f"DEBUG: _run_lab ending after {frame_count} frames")
        tracker.close()
        camera.release()
        _frame_ready.set()
        with _frame_lock:
            _latest_frame = None


def start_lab():
    global _lab_thread
    _frame_ready.clear()
    state["running"] = True
    if _lab_thread is None or not _lab_thread.is_alive():
        _lab_thread = threading.Thread(target=_run_lab, daemon=True)
        _lab_thread.start()
        print("DEBUG: lab thread started")
    else:
        print("DEBUG: lab thread already running")


def stop_lab():
    state["running"] = False