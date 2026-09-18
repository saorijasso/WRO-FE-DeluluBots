from vision.navigation.corner_roi_detector import is_clockwise


class WallFollowerController:

    """
    Controlador de navegación basado en Heading-Lock (0°, 90°, 180°, 270°).
    Detecta esquinas mediante un ROI o altura Y de referencia (punto azul/sensor).
    """

    def __init__(self, pic_width=700, pic_height=350):
        self.pic_width = pic_width
        self.pic_height = pic_height
        self.old_p_adjust = 0.0

    def calculate_target_yaw(self, avg_x, avg_y, direction, base_heading,
                         threshold=480, gain=0.05, max_offset=12.0):
        """Returns target_yaw only: base_heading plus a clamped wall-following offset."""
        if avg_x is None or avg_y is None:
            return base_heading

        cw = is_clockwise(direction)
        new_avg_x = (self.pic_width - avg_x) if cw else avg_x

        p_adjust = avg_y + new_avg_x - threshold
        angle_offset = (p_adjust * gain) * (-1.0 if cw else 1.0)
        angle_offset = max(-max_offset, min(max_offset, angle_offset))

        return (base_heading + angle_offset) % 360 
