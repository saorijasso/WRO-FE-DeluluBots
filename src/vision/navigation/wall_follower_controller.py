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

    def calculate_steering(
        self, avg_x, avg_y, direction, kp=0.35, kd=0.25, threshold=480
    ):
        """
        Calculates the steering angle using a PD algorithm and checks for corners.

        Normalizes the horizontal position based on the driving direction,
        computes proportional and derivative error adjustments, and applies
        a direction-dependent sign so that corners trigger turns in the
        correct physical direction.

        Args:
            avg_x (float): X-coordinate of the wall centroid in pixels.
            avg_y (float): Y-coordinate of the wall centroid in pixels.
            direction (str): Driving direction ("Clockwise" or "CounterClockwise").
            kp (float, optional): Proportional gain for steering adjustment.
            kd (float, optional): Derivative gain for damping rapid changes.
            threshold (float, optional): Reference target value for error calculation.

        Returns:
            tuple:
                - int: Clipped steering servo angle in degrees (70 to 130).
                - bool: True if a corner transition is detected based on a sudden
                  derivative error drop, False otherwise.
        """
        # Normalize X according to driving direction
        new_avg_x = (
            avg_x
            if direction == "CounterClockwise"
            else (self.pic_width - avg_x)
        )

        # Proportional error (Virtual Target Error)
        p_adjust = avg_y + new_avg_x - threshold

        # Derivative calculation
        p_compare = p_adjust - self.old_p_adjust
        d_adjust = p_compare * kd

        # Corner drop detection
        is_corner = p_compare < (-1 * (self.pic_height // 2.5))

        # Direction-dependent steering angle (Angle < 90° turns right in Clockwise)
        dir_sign = -1 if direction == "Clockwise" else 1
        raw_angle = 90 + dir_sign * ((p_adjust * kp) + d_adjust)

        self.old_p_adjust = p_adjust

        # Clip angle to servo physical limits
        steering_angle = int(np.clip(raw_angle, 70, 130))

        return steering_angle, is_corner