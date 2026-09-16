import cv2


class CrashDetector:
    """
    Sistema de defensas virtuales (Virtual Bumpers).
    Analiza puntos clave en la máscara binaria de la pared para detectar colisiones inminentes.
    
    Máscara de Paredes:
      - 255 (Blanco): Pista / Espacio libre
      - 0   (Negro) : Pared / Obstáculo
    """

    def __init__(self, pic_width=700, pic_height=350):
        self.pic_width = pic_width
        self.pic_height = pic_height

    def check_outer_wall_crash(self, wall_mask):
        """
        Detecta si el robot está a punto de chocar de frente contra la pared exterior.
        """
        if wall_mask is None:
            return False

        # Punto al frente-centro del robot (abajo en la imagen)
        check_x = self.pic_width // 2
        check_y = self.pic_height - 60

        # Si el píxel es 0 (negro), hay pared justo enfrente
        return bool(wall_mask[check_y, check_x] == 0)

    def check_inner_wall_crash(self, wall_mask, direction):
        """
        Detecta si el robot se está pegando demasiado a la pared interna durante un giro.
        """
        if wall_mask is None:
            return False

        # Definir 3 puntos en diagonal según el sentido de la pista
        if direction == "Clockwise":
            # Girando a la derecha -> Pared interna está a la DERECHA
            points = [
                (self.pic_height - 120, self.pic_width - 180),
                (self.pic_height - 80,  self.pic_width - 140),
                (self.pic_height - 40,  self.pic_width - 100),
            ]
        else:
            # Girando a la izquierda -> Pared interna está a la IZQUIERDA
            points = [
                (self.pic_height - 120, 180),
                (self.pic_height - 80,  140),
                (self.pic_height - 40,  100),
            ]

        # Si CUALQUIERA de los puntos toca la pared (0), hay riesgo de choque interno
        for y, x in points:
            if wall_mask[y, x] == 0:
                return True

        return False

    def draw_debug_points(self, debug_frame, direction):
        """
        Dibuja los puntos de prueba en la imagen para poder calibrar en pantalla.
        """
        if debug_frame is None:
            return debug_frame

        # Punto Outer (Azul)
        cv2.circle(debug_frame, (self.pic_width // 2, self.pic_height - 60), 5, (255, 0, 0), -1)

        # Puntos Inner (Amarillo)
        if direction == "Clockwise":
            points = [
                (self.pic_height - 120, self.pic_width - 180),
                (self.pic_height - 80,  self.pic_width - 140),
                (self.pic_height - 40,  self.pic_width - 100),
            ]
        else:
            points = [
                (self.pic_height - 120, 180),
                (self.pic_height - 80,  140),
                (self.pic_height - 40,  100),
            ]

        for y, x in points:
            cv2.circle(debug_frame, (x, y), 5, (0, 255, 255), -1)

        return debug_frame