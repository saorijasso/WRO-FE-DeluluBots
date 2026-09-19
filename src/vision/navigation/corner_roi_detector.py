"""
ROI-based corner detection for the WRO Future Engineers Open Challenge.

Drop this file in:  src/vision/navigation/corner_roi_detector.py

Mask convention used EVERYWHERE in this module
----------------------------------------------
    WALL  = 255  (white pixels = wall)
    FLOOR =   0  (black pixels = floor / free space)

This is the opposite of what crash_detector.py assumes, so build the mask
only with build_wall_mask() below and pass that same array to every consumer.
"""

import time

import cv2
import numpy as np

WALL = 255
FLOOR = 0


# ----------------------------------------------------------------------
# Direction helpers
# ----------------------------------------------------------------------
def is_clockwise(direction):
    """
    Robust direction test.

    Accepts Direction.LEFT / Direction.RIGHT, "Clockwise",
    "CounterClockwise", "Counter-Clockwise", "counter clockwise", etc.
    The old code compared raw strings, so "Counter-Clockwise" (the value
    stored in Direction.LEFT) never matched "CounterClockwise" and was
    silently treated as clockwise.
    """
    raw = getattr(direction, "value", direction)
    s = str(raw).upper().replace("-", "").replace("_", "").replace(" ", "")
    return "COUNTER" not in s and "CLOCKWISE" in s


def angle_diff(a, b):
    """Signed smallest difference a-b, in (-180, 180]."""
    return (float(a) - float(b) + 180.0) % 360.0 - 180.0


# ----------------------------------------------------------------------
# Wall / floor mask
# ----------------------------------------------------------------------
def build_wall_mask(
    frame,
    width=700,
    height=350,
    color_ranges=None,
    colors_to_wall=("Red", "Green"),
    use_otsu=True,
    fixed_threshold=100,
    auto_polarity=True,
):
    """
    Build a binary wall/floor mask: 255 = wall, 0 = floor.

    Args:
        frame: BGR camera frame.
        width, height: working resolution (keep it the same everywhere).
        color_ranges: saved_ranges.color_ranges, or None to skip color work.
        colors_to_wall: pillar colors that should be treated as wall so the
            robot does not try to drive through them (Open Challenge: leave
            it, there are no pillars, it is harmless).
        use_otsu: adaptive threshold instead of a hardcoded 100. This is the
            single biggest robustness win when the venue lighting changes.
        auto_polarity: if the strip right in front of the robot comes out
            mostly white, the mask is inverted and gets flipped. That strip
            is always floor on a real run, so it is a reliable reference.

    Returns:
        numpy.ndarray: uint8 mask, shape (height, width), values 0 or 255.
    """
    img = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)

    if color_ranges:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        for color in colors_to_wall:
            if color in color_ranges:
                low, high = color_ranges[color]
                m = cv2.inRange(hsv, np.array(low), np.array(high))
                img[m > 0] = (255, 255, 255)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 8, 60, 60)

    if use_otsu:
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, mask = cv2.threshold(gray, fixed_threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    if auto_polarity:
        strip = mask[int(height * 0.78):int(width * 0.88):, int(width * 0.30):int(width * 0.70)]
        if strip.size and float(np.count_nonzero(strip)) / strip.size > 0.80:
            mask = cv2.bitwise_not(mask)

    return mask


def wall_follow_point(wall_mask, direction, band=(0.35, 0.85), row_step=4, cols=15):
    """
    Point on the inner wall used for straight-line steering.

    Scans from the inner side of the image towards the center and returns the
    mean position of the wall/floor boundary.

    Returns:
        (avg_x, avg_y) as floats, or (None, None) when the wall is not visible.
    """
    h, w = wall_mask.shape[:2]
    y0, y1 = int(h * band[0]), int(h * band[1])

    if is_clockwise(direction):          # inner wall on the RIGHT
        x_outer, x_inner, step = w - 1, int(w * 0.50), -1
        edge_cols = range(max(0, w - cols), w)
    else:                                # inner wall on the LEFT
        x_outer, x_inner, step = 0, int(w * 0.50), 1
        edge_cols = range(0, min(cols, w))

    xs, ys = [], []

    for y in range(y0, y1, row_step):
        for x in range(x_outer, x_inner, step):
            if wall_mask[y, x] == WALL:
                xs.append(x)
                ys.append(y)
                break

    for x in edge_cols:
        for y in range(y1 - 1, y0, -1):
            if wall_mask[y, x] == WALL:
                ys.append(y)
                break

    if not xs or not ys:
        return None, None

    return float(np.mean(xs)), float(np.mean(ys))


# ----------------------------------------------------------------------
# Corner detection by region of interest
# ----------------------------------------------------------------------
class CornerROIDetector:
    """
    Fires one clean corner event using a single rectangular ROI.

    Two modes:

    "front_wall"  (recommended, default)
        ROI sits in the lower-center of the image, looking ahead.
        While driving straight that ROI is FLOOR; the corner event fires
        when it fills up with WALL (the front wall is close enough).

    "inner_floor"
        ROI sits on the inner side of the track (right when clockwise, left
        when counter-clockwise), where the inner wall normally is.
        The corner event fires when that wall disappears and FLOOR shows up,
        i.e. the opening at the corner.

    Both modes require the opposite class to be seen first (require_flip),
    need `confirm_frames` consecutive frames over the trigger ratio, use
    hysteresis (trigger_ratio / release_ratio) and a time cooldown. That
    combination is what stops the continuous re-triggering.
    """

    PRESETS = {
        # mode          roi_x  roi_y  roi_w  roi_h  trigger  release
        "front_wall": (0.50, 0.60, 0.30, 0.20, 0.55, 0.25),
        "inner_floor": (0.72, 0.55, 0.22, 0.22, 0.75, 0.45),
    }

    def __init__(
        self,
        pic_width=700,
        pic_height=350,
        mode="front_wall",
        roi_x_frac=None,
        roi_y_frac=None,
        roi_w_frac=None,
        roi_h_frac=None,
        trigger_ratio=None,
        release_ratio=None,
        confirm_frames=3,
        cooldown_s=2.0,
        require_flip=True,
    ):
        if mode not in self.PRESETS:
            raise ValueError("mode must be 'front_wall' or 'inner_floor'")

        px, py, pw, ph, ptr, prl = self.PRESETS[mode]

        self.pic_width = pic_width
        self.pic_height = pic_height
        self.mode = mode
        self.roi_x_frac = px if roi_x_frac is None else roi_x_frac
        self.roi_y_frac = py if roi_y_frac is None else roi_y_frac
        self.roi_w_frac = pw if roi_w_frac is None else roi_w_frac
        self.roi_h_frac = ph if roi_h_frac is None else roi_h_frac
        self.trigger_ratio = ptr if trigger_ratio is None else trigger_ratio
        self.release_ratio = prl if release_ratio is None else release_ratio
        self.confirm_frames = confirm_frames
        self.cooldown_s = cooldown_s
        self.require_flip = require_flip

        self._hits = 0
        self._flipped = not require_flip
        self._cooldown_until = 0.0
        self.last_ratio = 0.0
        self.last_roi = (0, 0, 0, 0)

    # -- geometry ------------------------------------------------------
    def roi_rect(self, direction):
        """Returns the ROI as (x0, y0, x1, y1) in mask pixels."""
        w, h = self.pic_width, self.pic_height
        cx = self.roi_x_frac

        # In inner_floor mode the ROI mirrors with the lap direction.
        if self.mode == "inner_floor" and not is_clockwise(direction):
            cx = 1.0 - cx

        half_w = self.roi_w_frac * 0.5
        half_h = self.roi_h_frac * 0.5

        x0 = int(max(0, (cx - half_w) * w))
        x1 = int(min(w, (cx + half_w) * w))
        y0 = int(max(0, (self.roi_y_frac - half_h) * h))
        y1 = int(min(h, (self.roi_y_frac + half_h) * h))
        return x0, y0, x1, y1

    def ratio(self, wall_mask, direction):
        """Fraction of the ROI occupied by the class this mode triggers on."""
        x0, y0, x1, y1 = self.roi_rect(direction)
        self.last_roi = (x0, y0, x1, y1)

        roi = wall_mask[y0:y1, x0:x1]
        if roi.size == 0:
            return 0.0

        white = float(np.count_nonzero(roi)) / roi.size
        return white if self.mode == "front_wall" else 1.0 - white

    # -- state machine -------------------------------------------------
    def update(self, wall_mask, direction, now=None):
        """
        Call once per frame.

        Returns dict:
            corner (bool)   True on exactly one frame per real corner
            ratio (float)   current ROI ratio, for tuning on screen
            armed (bool)    whether the opposite class was already seen
            cooldown (float) seconds left of cooldown
        """
        now = time.time() if now is None else now

        if wall_mask is None:
            return {"corner": False, "ratio": 0.0, "armed": self._flipped, "cooldown": 0.0}

        r = self.ratio(wall_mask, direction)
        self.last_ratio = r
        cooling = now < self._cooldown_until

        if r <= self.release_ratio:
            self._hits = 0
            self._flipped = True          # opposite class confirmed -> armed
        elif r >= self.trigger_ratio:
            self._hits += 1

        corner = (
            not cooling
            and self._flipped
            and self._hits >= self.confirm_frames
        )

        if corner:
            self._hits = 0
            self._flipped = not self.require_flip
            self._cooldown_until = now + self.cooldown_s

        return {
            "corner": corner,
            "ratio": r,
            "armed": self._flipped,
            "cooldown": max(0.0, self._cooldown_until - now),
        }

    def reset(self):
        self._hits = 0
        self._flipped = not self.require_flip
        self._cooldown_until = 0.0

    # -- debug ---------------------------------------------------------
    def draw(self, image, direction, info=None):
        """Draws the ROI and its ratio. Accepts a mask or a BGR frame."""
        if image is None:
            return image

        out = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image
        x0, y0, x1, y1 = self.roi_rect(direction)
        r = self.last_ratio if info is None else info["ratio"]
        hot = r >= self.trigger_ratio
        color = (0, 0, 255) if hot else (0, 255, 0)

        cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
        cv2.putText(
            out, f"{self.mode} {r:.2f}", (x0, max(18, y0 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )
        if info is not None and info.get("corner"):
            cv2.putText(out, "CORNER", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        return out
