class SignNavigation:
    """
    Controlador de navegación para esquivar pilares según su color y posición en pantalla.
    """
    def __init__(self, camera_fov_x=60.0, safety_margin_mult=1.5):
        """
        Args:
            camera_fov_x (float): Campo de visión horizontal de la cámara en grados.
            safety_margin_mult (float): Multiplicador del ancho del pilar para el margen de paso.
        """
        self.camera_fov_x = camera_fov_x
        self.safety_margin_mult = safety_margin_mult

    def calculate_avoidance_yaw(self, sign, frame_width, current_yaw):
        """
        Calcula el target_yaw necesario para rodear el pilar.
        
        - Rojo  -> Pasa por la DERECHA
        - Verde -> Pasa por la IZQUIERDA
        """
        if sign is None:
            # Si no hay pilar o ya fue rebasado (descartado por distancia), mantiene el curso
            return current_yaw

        color = sign.get("color")
        x = sign.get("x")
        w = sign.get("w")
        sign_center_x = x + (w / 2.0)

        # Margen de seguridad horizontal en píxeles
        safety_margin_px = w * self.safety_margin_mult

        # Definir el punto X al que debe apuntar el vehículo
        if color == "Red":
            target_x = sign_center_x + safety_margin_px
        elif color == "Green":
            target_x = sign_center_x - safety_margin_px
        else:
            target_x = sign_center_x

        # Calcular desviación en grados con respecto al centro de la cámara
        center_screen_x = frame_width / 2.0
        pixel_offset = target_x - center_screen_x
        deg_per_pixel = self.camera_fov_x / frame_width
        angle_offset = pixel_offset * deg_per_pixel

        # Yaw absoluto resultante
        target_yaw = current_yaw + angle_offset

        return target_yaw