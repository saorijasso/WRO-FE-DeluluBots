import numpy as np


class WallFollowerController:
    """
    Proportional-Derivative (PD) controller based on a virtual target point
    for wall-following navigation.

    Calculates steering angles and detects corner transitions by analyzing
    the position of the detected wall centroid relative to a set threshold.
    """

    def __init__(self, pic_width=700, pic_height=350):
        """
        Initializes the WallFollowerController with image dimensions and state variables.

        Args:
            pic_width (int, optional): Width of the processed camera frame in pixels.
            pic_height (int, optional): Height of the processed camera frame in pixels.
        """
        self.pic_width = pic_width
        self.pic_height = pic_height
        self.old_p_adjust = 0.0

    def calculate_target_yaw(
        self,
        avg_x,
        avg_y,
        direction,
        current_yaw,
        threshold=480,
    ):
        """Calculates the target IMU heading based on visual wall offset.

        Instead of computing servo angles directly, this function determines
        the desired IMU yaw target to be sent to an external microcontroller
        (e.g., ESP32) for low-level motor control.

        Args:
            avg_x (float): X-coordinate of wall centroid in pixels.
            avg_y (float): Y-coordinate of wall centroid in pixels.
            direction (str): Driving direction ("Clockwise" or "CounterClockwise").
            current_yaw (float): Current Yaw orientation angle from IMU in degrees.
            threshold (float, optional): Target baseline value for vision.
              Defaults to 480.

        Returns:
            tuple:
                - float: Desired target Yaw angle in degrees (0 to 360).
                - bool: True if a corner transition is detected, False otherwise.
        """
        # 1. Normalize horizontal coordinate based on driving direction
        new_avg_x = (
            avg_x
            if direction == "CounterClockwise"
            else (self.pic_width - avg_x)
        )

        # 2. Vision-based error calculation
        p_adjust = avg_y + new_avg_x - threshold
        p_compare = p_adjust - self.old_p_adjust
        self.old_p_adjust = p_adjust

        # 3. Detect corner condition
        is_corner = p_compare < (-1 * (self.pic_height // 2.5))

        if is_corner:
            # Corner detected: shift target heading by 90 degrees according to track direction
            turn_angle = 90 if direction == "CounterClockwise" else -90
            target_yaw = (current_yaw + turn_angle) % 360
        else:
            # Straight path: calculate minor angle offset based on wall distance
            # Converts pixel error into a slight angular offset (e.g., max +-10 to 15 degrees)
            angle_offset = (p_adjust * 0.05) * (
                -1 if direction == "Clockwise" else 1
            )
            target_yaw = (current_yaw + angle_offset) % 360

        return target_yaw, is_corner