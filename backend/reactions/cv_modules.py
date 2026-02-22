# backend/reactions/cv_modules.py
# Place in: backend/reactions/cv_modules.py — REPLACE existing file entirely.
#
# IMPORTANT: opencv_handler.py must flip the frame BEFORE passing it here:
#   frame = cv2.flip(frame, 1)   ← add this after camera.read()
#
# With the flip, the tube sits on the right side of the frame and the
# litmus paper sits bottom-left. The bezier stream arcs left toward the paper.
#
# NOTE: Imports django.core.cache — must run inside a Django process.

import cv2
import math
import time
import numpy as np
import mediapipe as mp

from django.core.cache import cache

CACHE_KEY_CHEMICAL      = "active_chemical_type"
CACHE_KEY_REACTION_DONE = "reaction_complete_flag"


# ─────────────────────────────────────────────────────────────────────────────
# HandTracker — exact logic from hand_tracker.py
# [ADAPTED] Added get_hand_position() wrapper for opencv_handler.py contract
# ─────────────────────────────────────────────────────────────────────────────
class HandTracker:
    def __init__(self, mode=False, max_hands=1,
                 detection_confidence=0.5, tracking_confidence=0.5):
        self.mode = mode
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        self.prev_angle = 0
        self.alpha = 0.2

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

    def find_hands(self, frame, draw=True):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(rgb_frame)
        if self.results.multi_hand_landmarks and draw:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
        return frame

    def get_hand_angle(self, frame):
        if not self.results or not self.results.multi_hand_landmarks:
            return None

        hand = self.results.multi_hand_landmarks[0]
        h, w, _ = frame.shape

        wrist     = hand.landmark[0]
        fingertip = hand.landmark[12]

        wrist_x     = wrist.x     * w
        wrist_y     = wrist.y     * h
        fingertip_x = fingertip.x * w
        fingertip_y = fingertip.y * h

        dx = fingertip_x - wrist_x
        dy = wrist_y     - fingertip_y

        raw_angle = math.degrees(math.atan2(dy, dx))

        if dx >= 0:
            target_angle = 0
        else:
            target_angle = max(0, min(90, 180 - abs(raw_angle)))

        if target_angle < 10:
            target_angle = 0

        smoothed        = self.alpha * target_angle + (1 - self.alpha) * self.prev_angle
        self.prev_angle = smoothed
        return smoothed

    def is_pouring(self, angle):
        return angle is not None and angle < 50

    # [ADAPTED] Single-call wrapper used by opencv_handler.py
    def get_hand_position(self, frame):
        """
        Combines find_hands() + get_hand_angle() in one call.
        Returns {"angle": float, "x": int|None, "y": int|None}
        Never returns None — decays angle toward 0 when hand is lost.
        """
        frame = self.find_hands(frame, draw=True)
        angle = self.get_hand_angle(frame)

        if angle is None:
            self.prev_angle = self.alpha * 0 + (1 - self.alpha) * self.prev_angle
            return {"angle": self.prev_angle, "x": None, "y": None}

        h, w, _ = frame.shape
        wrist = self.results.multi_hand_landmarks[0].landmark[0]
        return {
            "angle": angle,
            "x": int(wrist.x * w),
            "y": int(wrist.y * h),
        }


# ─────────────────────────────────────────────────────────────────────────────
# TestTube — exact logic from test_tube.py
# [ADAPTED]:
#   • Anchored at x=430, y=80, width=80, height=240 (right side, post-flip)
#   • draw(frame, liquid_color) → (is_pouring, sx, sy, frame)
#   • _draw_rotated() uses RGBA alpha blend (no black halo)
#   • _draw_pouring_effect() returns (end_x, splash_y) for collision
#   • Bezier endpoint (120, 370) targets litmus paper centre (50–190, 320–460)
# ─────────────────────────────────────────────────────────────────────────────
class TestTube:
    def __init__(self, x=430, y=80, width=80, height=240):
        self.x             = x
        self.y             = y
        self.width         = width
        self.height        = height
        self.liquid_level  = 0.7
        self.liquid_color  = (200, 200, 255)
        self.display_angle = 0
        self.current_angle = 0
        self.is_pouring    = False
        self.MAX_ANGLE     = 90

    def set_angle(self, angle):
        if angle is None:
            self.current_angle = 0
            self.is_pouring    = False
            return
        self.current_angle = min(angle, self.MAX_ANGLE)
        self.is_pouring    = self.current_angle > 40

    # [ADAPTED] accepts liquid_color; returns (is_pouring, sx, sy, frame)
    def draw(self, frame, liquid_color):
        self.liquid_color   = liquid_color
        self.display_angle += (self.current_angle - self.display_angle) * 0.1

        if self.display_angle > 25 and self.liquid_level > 0:
            self.is_pouring    = True
            self.liquid_level -= 0.0008
            self.liquid_level  = max(0.0, self.liquid_level)
        else:
            self.is_pouring = False

        frame = self._draw_rotated(frame)

        sx, sy = None, None
        if self.display_angle > 25 and self.liquid_level > 0:
            sx, sy = self._draw_pouring_effect(frame)

        return self.is_pouring, sx, sy, frame

    # [ADAPTED] RGBA canvas + vectorised alpha composite → no black halos
    def _draw_rotated(self, frame):
        fh, fw = frame.shape[:2]
        canvas = np.zeros((fh, fw, 4), dtype=np.uint8)

        self._draw_tube_components(canvas)

        pivot = (self.x + self.width // 2, self.y)
        M = cv2.getRotationMatrix2D(pivot, self.display_angle, 1.0)
        rotated = cv2.warpAffine(
            canvas, M, (fw, fh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

        alpha = rotated[:, :, 3:4].astype(np.float32) / 255.0
        src   = rotated[:, :, :3].astype(np.float32)
        dst   = frame.astype(np.float32)
        frame = (src * alpha + dst * (1.0 - alpha)).astype(np.uint8)
        return frame

    def _draw_tube_components(self, canvas):
        self._draw_liquid_with_gravity(canvas)
        self._fill_rounded_bottom(canvas)
        self._draw_glass_outline(canvas)
        cv2.ellipse(canvas,
                    (self.x + self.width // 2, self.y + self.height),
                    (self.width // 2, 12),
                    0, 0, 180, (100, 100, 100, 255), 3)

    def _draw_liquid_with_gravity(self, canvas):
        angle_rad        = math.radians(-self.display_angle)
        tube_left        = self.x + 3
        tube_right       = self.x + self.width - 3
        tube_bottom      = self.y + self.height
        tube_top         = self.y
        liquid_height    = int(self.height * self.liquid_level)
        surface_center_y = tube_bottom - liquid_height
        cx               = (tube_left + tube_right) / 2.0
        surface_slope    = math.tan(angle_rad)

        for y in range(tube_bottom, tube_top, -1):
            ys_left  = surface_center_y - (tube_left  - cx) * surface_slope
            ys_right = surface_center_y - (tube_right - cx) * surface_slope
            lf, rf   = y >= ys_left, y >= ys_right

            if not lf and not rf:
                continue

            if lf and rf:
                dl, dr = tube_left, tube_right
            elif lf:
                xc = int(cx - (y - surface_center_y) / surface_slope) if abs(surface_slope) > 0.001 else tube_right
                dl, dr = tube_left, min(tube_right, xc)
            else:
                xc = int(cx - (y - surface_center_y) / surface_slope) if abs(surface_slope) > 0.001 else tube_left
                dl, dr = max(tube_left, xc), tube_right

            if dr <= dl:
                continue

            progress   = (tube_bottom - y) / max(liquid_height, 1)
            brightness = 1.0 - abs(0.5 - progress) * 0.4
            color      = tuple(int(c * brightness) for c in self.liquid_color)
            cv2.line(canvas, (dl, y), (dr, y), (*color, 220), 1)

        # Surface shimmer
        for px in range(tube_left, tube_right):
            ys = int(surface_center_y - (px - cx) * surface_slope)
            if tube_top < ys < tube_bottom:
                cv2.circle(canvas, (px, ys), 1, (220, 220, 255, 180), -1)

    def _fill_rounded_bottom(self, canvas):
        if self.liquid_level > 0:
            cv2.ellipse(canvas,
                        (self.x + self.width // 2, self.y + self.height),
                        (self.width // 2 - 3, 10),
                        0, 0, 180, (*self.liquid_color, 220), -1)

    def _draw_glass_outline(self, canvas):
        cv2.rectangle(canvas,
                      (self.x, self.y),
                      (self.x + self.width, self.y + self.height),
                      (80, 80, 80, 255), 3)
        cv2.line(canvas,
                 (self.x + 5, self.y + 10),
                 (self.x + 5, self.y + self.height - 20),
                 (180, 180, 180, 200), 2)

    # [ADAPTED] returns (end_x, splash_y) for collision detection
    # Bezier aims at litmus paper centre (~120, 390) which is inside bbox (50-190, 320-460)
    def _draw_pouring_effect(self, frame):
        angle_rad = math.radians(self.display_angle)
        pivot_x   = self.x + self.width // 2
        pivot_y   = self.y

        mo_x = -(self.width // 2)
        mo_y = 0
        stream_x = int(pivot_x + mo_x * math.cos(angle_rad) - mo_y * math.sin(angle_rad))
        stream_y = int(pivot_y + mo_x * math.sin(angle_rad) + mo_y * math.cos(angle_rad))

        ctrl_x, ctrl_y = stream_x - 80, stream_y + 100
        end_x,  end_y  = 120, 370   # paper bbox: x 50-190, y 320-460

        steps = 30
        prev_x, prev_y = stream_x, stream_y
        lc = self.liquid_color

        for i in range(1, steps + 1):
            t  = i / steps
            bx = int((1-t)**2 * stream_x + 2*(1-t)*t * ctrl_x + t**2 * end_x)
            by = int((1-t)**2 * stream_y + 2*(1-t)*t * ctrl_y + t**2 * end_y)

            w_px       = max(1, int(6 * (1 - t * 0.6)))
            dark_col   = tuple(int(c * 0.6) for c in lc)
            bright_col = tuple(min(255, int(c * 1.2)) for c in lc)

            cv2.line(frame, (prev_x, prev_y), (bx, by), dark_col,   w_px + 2)
            cv2.line(frame, (prev_x, prev_y), (bx, by), lc,          w_px)
            cv2.line(frame, (prev_x, prev_y), (bx, by), bright_col,  max(1, w_px - 2))
            prev_x, prev_y = bx, by

        # Animated 3D drops
        t_now = time.time()
        for i in range(5):
            phase  = (t_now * 2 + i * 0.4) % 1.0
            drop_x = end_x + int(math.sin(phase * math.pi) * 5) - i * 3
            drop_y = end_y + int(phase * 40)
            radius = max(2, 7 - i)
            cv2.circle(frame, (drop_x, drop_y), radius,
                       tuple(int(c * 0.5) for c in lc), -1)
            cv2.circle(frame, (drop_x, drop_y), max(1, radius - 1), lc, -1)
            cv2.circle(frame, (drop_x - radius//3, drop_y - radius//3),
                       max(1, radius // 3),
                       tuple(min(255, int(c * 1.3)) for c in lc), -1)

        # Splash
        splash_y = end_y + 20   # ≈ 390 — inside paper bbox
        for i in range(6):
            sa = math.radians(180 + i * 30)
            sx = int(end_x + math.cos(sa) * (8 + i * 2))
            sy = int(splash_y + math.sin(sa) * 4)
            cv2.circle(frame, (sx, sy), 2, lc, -1)

        return end_x, splash_y   # (120, 390)


# ─────────────────────────────────────────────────────────────────────────────
# VirtualLab — unchanged logic, coordinates aligned to post-flip frame
# ─────────────────────────────────────────────────────────────────────────────
class VirtualLab:
    """Litmus paper, chemistry logic, cache signalling."""

    # Bottom-left of the FLIPPED frame — stream splash (120, 390) lands here
    PAPER_X, PAPER_Y, PAPER_W, PAPER_H = 50, 320, 140, 140
    NEUTRAL_LIQUID = (200, 200, 200)

    def __init__(self):
        self.test_tube          = TestTube()
        self.reaction_triggered = False
        cache.set(CACHE_KEY_REACTION_DONE, False, timeout=3600)

    def _resolve_colors(self, reaction_type, chemical_type):
        RED   = (40,  40,  220)
        BLUE  = (220, 80,  40)
        initial = RED if reaction_type == "red_litmus" else BLUE

        if reaction_type == "blue_litmus" and chemical_type == "acid":
            return self.NEUTRAL_LIQUID, BLUE, RED,  True
        if reaction_type == "red_litmus"  and chemical_type == "base":
            return self.NEUTRAL_LIQUID, RED,  BLUE, True
        return self.NEUTRAL_LIQUID, initial, initial, False

    def _draw_litmus_paper(self, frame, paper_color, reaction_type):
        px, py, pw, ph = self.PAPER_X, self.PAPER_Y, self.PAPER_W, self.PAPER_H

        # Drop shadow
        cv2.rectangle(frame, (px + 6, py + 6), (px + pw + 6, py + ph + 6),
                      (20, 20, 20), -1)
        # Paper body
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), paper_color, -1)
        # Highlight strip
        highlight = tuple(min(c + 60, 255) for c in paper_color)
        cv2.rectangle(frame, (px + 6, py + 6), (px + pw - 6, py + 34), highlight, -1)
        # Borders
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), (210, 210, 210), 3)
        cv2.rectangle(frame, (px + 4, py + 4), (px + pw - 4, py + ph - 4),
                      (170, 170, 170), 1)
        # "TEST ZONE" header
        cv2.rectangle(frame, (px, py), (px + pw, py + 26), (35, 35, 35), -1)
        cv2.putText(frame, "TEST ZONE", (px + 18, py + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)
        # Label strip at bottom
        cv2.rectangle(frame, (px, py + ph - 32), (px + pw, py + ph), (18, 18, 18), -1)
        label = "RED LITMUS" if reaction_type == "red_litmus" else "BLUE LITMUS"
        cv2.putText(frame, label, (px + 8, py + ph - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (230, 230, 230), 1, cv2.LINE_AA)
        # Vertical centre line
        mid_x = px + pw // 2
        cv2.line(frame,
                 (mid_x, py + 30),
                 (mid_x, py + ph - 36),
                 tuple(max(c - 40, 0) for c in paper_color), 1)

    def draw_elements(self, frame, hand_pos, reaction_type):
        chemical_type = cache.get(CACHE_KEY_CHEMICAL, "neutral")
        liquid_color, initial_color, triggered_color, does_react = \
            self._resolve_colors(reaction_type, chemical_type)

        self.test_tube.set_angle(hand_pos["angle"] if hand_pos else None)
        is_pouring, sx, sy, frame = self.test_tube.draw(frame, liquid_color)

        px, py, pw, ph = self.PAPER_X, self.PAPER_Y, self.PAPER_W, self.PAPER_H
        if (is_pouring and sx is not None and sy is not None
                and does_react and not self.reaction_triggered):
            if px <= sx <= px + pw and py <= sy <= py + ph:
                self.reaction_triggered = True
                cache.set(CACHE_KEY_REACTION_DONE, True, timeout=60)

        paper_color = triggered_color if self.reaction_triggered else initial_color
        self._draw_litmus_paper(frame, paper_color, reaction_type)

        if self.reaction_triggered:
            fh, fw = frame.shape[:2]
            by = fh // 2 - 38
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, by), (fw, by + 68), (8, 8, 8), -1)
            cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
            cv2.putText(frame, "REACTION COMPLETE",
                        (fw // 2 - 188, by + 46),
                        cv2.FONT_HERSHEY_DUPLEX, 1.25, (0, 180, 80), 4, cv2.LINE_AA)
            cv2.putText(frame, "REACTION COMPLETE",
                        (fw // 2 - 188, by + 46),
                        cv2.FONT_HERSHEY_DUPLEX, 1.25, (0, 255, 120), 2, cv2.LINE_AA)

        return frame