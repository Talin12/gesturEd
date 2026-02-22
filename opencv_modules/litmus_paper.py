import cv2
import numpy as np
import math

class LitmusPaper:
    def __init__(self, x=320, y=420, width=80, height=120):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Litmus starts neutral — light yellow/cream
        self.base_color    = (210, 230, 240)  # BGR cream
        self.current_color = list(self.base_color)
        self.target_color  = list(self.base_color)

        # Wet zone — where liquid actually hit
        self.wet_spots = []         # list of (x, y, radius, progress)
        self.is_being_hit = False
        self.hit_x = 0
        self.hit_y = 0

    def receive_liquid(self, drop_x, drop_y, liquid_color):
        """Call this when a drop lands on the paper"""
        # Only react if drop is within paper bounds
        if self.x < drop_x < self.x + self.width and self.y < drop_y < self.y + self.height:
            self.wet_spots.append({
                'x': drop_x,
                'y': drop_y,
                'radius': 2,
                'max_radius': 18,
                'color': liquid_color,
                'alpha': 1.0
            })
            # Change paper color toward liquid color (acid = red, base = blue)
            for i in range(3):
                self.target_color[i] = int(
                    self.target_color[i] * 0.85 + liquid_color[i] * 0.15
                )

    def draw(self, frame):
        self._draw_paper_3d(frame)
        self._draw_wet_spots(frame)
        self._draw_paper_lines(frame)
        return frame

    def _draw_paper_3d(self, frame):
        x, y, w, h = self.x, self.y, self.width, self.height

        # ---- SHADOW beneath paper ----
        shadow_pts = np.array([
            [x + 6,     y + h + 4],
            [x + w + 6, y + h + 4],
            [x + w + 4, y + h + 8],
            [x + 4,     y + h + 8],
        ], np.int32)
        cv2.fillPoly(frame, [shadow_pts], (30, 30, 30))

        # ---- RIGHT side face (thickness illusion) ----
        right_face = np.array([
            [x + w,     y],
            [x + w + 5, y + 3],
            [x + w + 5, y + h + 3],
            [x + w,     y + h],
        ], np.int32)
        dark_color = tuple(int(c * 0.55) for c in self.current_color)
        cv2.fillPoly(frame, [right_face], dark_color)

        # ---- BOTTOM face ----
        bottom_face = np.array([
            [x,         y + h],
            [x + w,     y + h],
            [x + w + 5, y + h + 3],
            [x + 5,     y + h + 3],
        ], np.int32)
        darker_color = tuple(int(c * 0.45) for c in self.current_color)
        cv2.fillPoly(frame, [bottom_face], darker_color)

        # ---- MAIN FACE with vertical gradient ----
        for i in range(h):
            progress = i / h
            # Slight gradient: brighter at top, darker at bottom
            brightness = 1.0 - progress * 0.15
            color = tuple(int(c * brightness) for c in self.current_color)
            cv2.line(frame, (x, y + i), (x + w, y + i), color, 1)

        # ---- HIGHLIGHT: thin bright strip on left edge ----
        highlight = tuple(min(255, int(c * 1.25)) for c in self.current_color)
        cv2.line(frame, (x, y), (x, y + h), highlight, 2)

        # ---- TOP edge highlight ----
        cv2.line(frame, (x, y), (x + w, y), highlight, 1)

        # ---- OUTLINE ----
        cv2.rectangle(frame, (x, y), (x + w, y + h), (60, 60, 60), 1)

    def _draw_wet_spots(self, frame):
        for spot in self.wet_spots:
            cx, cy = spot['x'], spot['y']
            r      = int(spot['radius'])
            color  = spot['color']

            if r < 1:
                continue

            # Expand spot over time
            if spot['radius'] < spot['max_radius']:
                spot['radius'] += 0.4

            # Clip to paper bounds
            clip_x1 = max(self.x, cx - r)
            clip_x2 = min(self.x + self.width, cx + r)
            clip_y1 = max(self.y, cy - r)
            clip_y2 = min(self.y + self.height, cy + r)

            # Draw wet stain with 3D depth — dark ring, mid fill, bright center
            dark   = tuple(int(c * 0.6) for c in color)
            bright = tuple(min(255, int(c * 1.15)) for c in color)

            # Create a mask to clip circle to paper
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.circle(mask, (cx, cy), r, 255, -1)
            paper_mask = np.zeros_like(mask)
            cv2.rectangle(paper_mask, (self.x, self.y),
                          (self.x + self.width, self.y + self.height), 255, -1)
            mask = cv2.bitwise_and(mask, paper_mask)

            # Outer dark ring
            cv2.circle(frame, (cx, cy), r,     dark,  -1)
            # Mid color fill
            cv2.circle(frame, (cx, cy), max(1, r - 2), color, -1)
            # Bright wet center
            cv2.circle(frame, (cx, cy), max(1, r - 5), bright, -1)

            # Clip anything outside paper back to paper color
            inv_mask = cv2.bitwise_not(mask)
            for c in range(3):
                frame[:, :, c] = np.where(
                    (inv_mask > 0) &
                    (frame[:, :, c] != 0),
                    frame[:, :, c],
                    frame[:, :, c]
                )

    def _draw_paper_lines(self, frame):
        """Ruled lines on the paper for realism"""
        line_color = tuple(int(c * 0.82) for c in self.current_color)
        for i in range(1, 6):
            y_line = self.y + int(i * self.height / 6)
            cv2.line(frame,
                     (self.x + 4,          y_line),
                     (self.x + self.width - 4, y_line),
                     line_color, 1)