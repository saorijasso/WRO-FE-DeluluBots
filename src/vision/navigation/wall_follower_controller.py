import numpy as np


class WallFollowerController:
    """
    Controlador de navegación basado en Heading-Lock (0°, 90°, 180°, 270°).
    Detecta esquinas mediante un ROI o altura Y de referencia (punto azul/sensor).
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
        base_heading,
        threshold=480,
        trigger_y=220,  # <-- Altura Y (en píxeles) equivalente a la posición del punto azul
    ):
        """
        Calcula el target_yaw sumando un offset suave al base_heading activo.
        Dispara 'is_corner' únicamente cuando la pared/línea alcanza la altura Y de referencia.
        """
        # Si no hay detección (avg_x/y son None o 0), no hay corner
        if avg_x is None or avg_y is None or (avg_x == 0 and avg_y == 0):
            return base_heading, False

        # 1. Normalización X según sentido de pista
        new_avg_x = (
            avg_x
            if direction == "CounterClockwise"
            else (self.pic_width - avg_x)
        )

        # 2. DETECCIÓN DE ESQUINA DIRECTA POR ALTURA (PUNTO AZUL)
        # Cuando avg_y sobrepasa el punto de disparo en pantalla, llegamos a la esquina
        is_corner = avg_y >= trigger_y

        if is_corner:
            # En esquina devolvemos la intención de girar 90° al nuevo rumbo cardinal
            turn_step = 90 if direction == "CounterClockwise" else -90
            target_yaw = (base_heading + turn_step) % 360
        else:
            # 3. CORRECCIÓN EN RECTA (Offset suave amarrado al base_heading)
            p_adjust = avg_y + new_avg_x - threshold
            
            angle_offset = (p_adjust * 0.05) * (
                -1 if direction == "Clockwise" else 1
            )
            # Clamp de seguridad: máximo +-12° de desviación sobre la recta
            angle_offset = max(-12.0, min(12.0, angle_offset))

            # El target NUNCA pierde el base_heading objetivo
            target_yaw = (base_heading + angle_offset) % 360

        return target_yaw, is_corner