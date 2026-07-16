from enum import Enum, auto
import numpy as np
import time


class Direction(Enum):
    """
    Enum class representing the possible directions for navigation.
    """
    LEFT = "Counter-Clockwise"
    RIGHT = "Clockwise"


class LapPhase(Enum):
    """
    Enum class representing the internal states of the lap counting
    state machine.
    """
    WAITING_FIRST = auto()
    WAITING_SECOND = auto()
    DEBOUNCE = auto()


# Maps each direction to the order in which the lines are expected to be
# crossed at every corner of the track.
LINE_SEQUENCE = {
    Direction.LEFT: ("Blue", "Orange"),
    Direction.RIGHT: ("Orange", "Blue"),
}


class NavigationManager:
    """
    Decides which way to go and keeps track of the current run direction.
    """

    def __init__(self):
        """
        Initializes the NavigationManager with no current direction.
        """

        self.direction = None

    def line_direction(self, dominant_line_color):
        """
        Determines the driving direction for the Open Challenge based on
        the detected line color.

        Args:
            dominant_line_color (str): Color of the line detected as closest
                by the vision system. Expected values are "Blue" or "Orange".

        Returns:
            Direction: Assigned direction (Direction.LEFT or Direction.RIGHT).
                Returns None if no direction has been assigned yet and the
                color doesn't match either line.
        """

        if dominant_line_color == "Blue":
            self.direction = Direction.LEFT
        elif dominant_line_color == "Orange":
            self.direction = Direction.RIGHT
        return self.direction

    def park_direction(self, track_mask):
        """
        Determines the driving direction for the Obstacle Challenge by
        analyzing which side of the track has more free space.

        Splits the track mask in half and counts the non-zero (white)
        pixels on each side to find the open path.

        Args:
            track_mask (numpy.ndarray): Binary mask of the detected track.

        Returns:
            Direction: Direction.LEFT if the left side has more free space,
                otherwise Direction.RIGHT.
        """

        width = track_mask.shape[1]
        midpoint = width // 2
        left_clearance = np.count_nonzero(track_mask[:, :midpoint])
        right_clearance = np.count_nonzero(track_mask[:, midpoint:])
        self.direction = Direction.LEFT if left_clearance > right_clearance else Direction.RIGHT
        return self.direction


class LapTracker:
    """
    Counts laps using a single state machine that works for either
    LEFT or RIGHT direction.
    """

    TOTAL_LAPS = 3
    CORNERS_PER_LAP = 4
    DEBOUNCE_SECONDS = 1.5

    def __init__(self, direction=None):
        """
        Initializes the tracker at the first lap, with no corners counted.

        Args:
            direction (Direction, optional): Direction to start tracking with.
                If not provided, it can be assigned later through set_direction.
        """

        self.phase = LapPhase.WAITING_FIRST
        self.current_lap = 1
        self.corners = 0
        self._debounce_until = 0.0

        self.first_line = None
        self.second_line = None

        if direction is not None:
            self.set_direction(direction)

    def set_direction(self, direction):
        """
        Assigns (or reassigns) the direction and updates the expected
        line order accordingly.

        Args:
            direction (Direction): Direction determined by NavigationManager.
        """

        if direction not in LINE_SEQUENCE:
            raise ValueError(f"Invalid direction: {direction}")
        self.first_line, self.second_line = LINE_SEQUENCE[direction]

    def update(self, detected_line_color):
        """
        Advances the state machine based on the line detected in the
        current frame.

        Args:
            detected_line_color (str): Detected line color ("Blue", "Orange",
                or None if no line was detected in this frame).
        """

        if detected_line_color is None or self.first_line is None:
            return

        now = time.time()

        if self.phase is LapPhase.DEBOUNCE:
            if now >= self._debounce_until:
                self.phase = LapPhase.WAITING_FIRST
            return

        if self.phase is LapPhase.WAITING_FIRST and detected_line_color == self.first_line:
            self.phase = LapPhase.WAITING_SECOND

        elif self.phase is LapPhase.WAITING_SECOND and detected_line_color == self.second_line:
            self._register_corner(now)

    def _register_corner(self, now):
        """
        Registers that a corner was completed, updates the lap count if
        a full lap was closed, and starts the debounce period.

        Args:
            now (float): Current timestamp (time.time()), passed in from
                update so it doesn't need to be read twice.
        """

        self.corners += 1
        if self.corners % self.CORNERS_PER_LAP == 0:
            self.current_lap += 1
        self._debounce_until = now + self.DEBOUNCE_SECONDS
        self.phase = LapPhase.DEBOUNCE

    @property
    def finished(self):
        """
        Indicates whether all laps have been completed.

        Returns:
            bool: True if current_lap has gone past TOTAL_LAPS.
        """

        return self.current_lap > self.TOTAL_LAPS

    