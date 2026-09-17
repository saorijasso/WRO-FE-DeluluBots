import numpy as np


class WallFollowerController:
    """
    Proportional-Derivative (PD) controller based on a virtual target point
    for wall-following navigation using discrete base headings (0, 90, 180, 270).
    """

    def __init__(self, pic_width=700, pic_height=350):
        self.pic_width = pic_width
        self.pic_height = pic_height
        self.old_p_adjust = 0.0

    def calculate_target_yaw(
        self,
        avg_x,
        avg_y,
        direction,
        base_heading,  # <--- AHORA PASAMOS EL BASE HEADING (0, 90, 180, 270)
        threshold=480,
    ):
        """
        Calcula el target_yaw sumando/restando una pequeña corrección visual
        al base_heading cardinal (0, 90, 180, 270).
        """
        # 1. Normalizar coordenada según la dirección de giro
        new_avg_x = (
            avg_x
            if direction == "CounterClockwise"
            else (self.pic_width - avg_x)
        )

        # 2. Error basado en la visión
        p_adjust = avg_y + new_avg_x - threshold
        p_compare = p_adjust - self.old_p_adjust
        self.old_p_adjust = p_adjust

        # 3. Detectar condición de esquina (desaparición de pared / punto azul)
        is_corner = p_compare < (-1 * (self.pic_height // 2.5))

        if is_corner:
            # 4A. SI ES ESQUINA: Cambiamos al siguiente ángulo cardinal (90°)
            turn_step = 90 if direction == "CounterClockwise" else -90
            new_base_heading = (base_heading + turn_step) % 360
            target_yaw = new_base_heading
        else:
            # 4B. SI ES RECTA: Corregimos suavemente alrededor del base_heading
            # Limitamos el offset a máximo +-15 grados para no descontrolar el coche
            angle_offset = (p_adjust * 0.05) * (
                -1 if direction == "Clockwise" else 1
            )
            angle_offset = max(-15.0, min(15.0, angle_offset)) # Clamp / Límite de seguridad
            
            target_yaw = (base_heading + angle_offset) % 360

        return target_yaw, is_corner