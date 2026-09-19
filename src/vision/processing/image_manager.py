import time
import os

import cv2

from camera.camera import Camera
from comms.ESP32bridge import ESP32Bridge
from config import saved_ranges
from processing.transform_image import VisionUtils
from processing.telemetry_display import TelemetryDisplay, VideoWriterLogger
from navigation.direction_manager import Direction, NavigationManager, LapTracker
from vision.config import saved_ranges
from vision.navigation.corner_roi_detector import CornerROIDetector, angle_diff, build_wall_mask, is_clockwise, wall_follow_point
from vision.navigation.direction_manager import LapTracker, NavigationManager
from vision.navigation.wall_follower_controller import WallFollowerController
from vision.processing.telemetry_display import VideoWriterLogger
from vision.processing.transform_image import VisionUtils
from vision.navigation.sign_navigation_controller import SignNavigation

HEADLESS = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

YAW_CW_SIGN = +1

class ImageManager:

    def __init__(self):
        """
        Initializes the camera and creates the display windows.
        """

        self.pic_width = 700
        self.pic_height = 350
        self.camera = Camera()
        self.wall_follower = WallFollowerController(
            pic_width=self.pic_width, pic_height=self.pic_height
        )
        self.serial_bridge = ESP32Bridge()


    def process_walls(self, frame, direction, base_heading):
        """
        Returns:
            (debug_bgr, wall_mask, target_yaw)
            wall_mask: 255 = wall, 0 = floor
            target_yaw: heading to hold while driving straight
        """
        wall_mask = build_wall_mask(
            frame,
            width=self.pic_width,
            height=self.pic_height,
            color_ranges=saved_ranges.color_ranges,
        )

        avg_x, avg_y = wall_follow_point(wall_mask, direction)

        debug = cv2.cvtColor(wall_mask, cv2.COLOR_GRAY2BGR)

        if avg_x is None:
            # No inner wall in sight: hold the cardinal heading, do not invent a turn.
            return debug, wall_mask, base_heading

        target_yaw = self.wall_follower.calculate_target_yaw(
            avg_x, avg_y, direction, base_heading
        )

        cv2.circle(debug, (int(avg_x), int(avg_y)), 7, (0, 255, 255), -1)
        return debug, wall_mask, target_yaw

    def process_elements(self, frame, colors, min_area, method):
        """
        Detects and processes a group of elements.

        The method detects the specified colors, selects one element
        using the provided selection method and draws its bounding box.

        Args:
            frame (numpy.ndarray): Original frame in BGR format.
            colors (list[str]): Colors to detect.
            min_area (int): Minimum contour area required for an element
                to be considered valid.
            method (callable): Function used to select the target element
                from the detected elements.

        Returns:
            tuple: A tuple containing:

                - str: Selected element color.
                - numpy.ndarray: Frame with the selected element drawn.
                - numpy.ndarray: Binary mask of the selected element.

            Returns (None, None, None) if no element is detected.
        """

        elements = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        element1 = VisionUtils.detect_element(hsv, saved_ranges.color_ranges, colors[0], min_area)
        if element1 is not None:
            elements.append(element1)

        element2 = VisionUtils.detect_element(hsv, saved_ranges.color_ranges, colors[1], min_area)
        if element2 is not None:
            elements.append(element2)
        
        if len(elements) == 0:
            return None, None, None, None

        best_element = method(elements)
        
        # Validar si el método de selección devolvió None
        if best_element is None:
            return None, None, None, None

        result = frame.copy()
        result = TelemetryDisplay.draw_element(best_element, result)
        result = VisionUtils.resize(result, 700, 350)

        mask = VisionUtils.resize(best_element["mask"], 700, 350)

        return best_element["color"], result, mask, best_element

    def process_navigation(self, line_color, line, nav_manager, lap_tracker):
        """
        Handles the direction assignment logic, lap tracking updates, 
        and telemetry HUD rendering.
        """
        if line_color and not nav_manager.direction:
            nav_manager.line_direction(line_color)
            lap_tracker.set_direction(nav_manager.direction)
            
        if line_color:
            lap_tracker.update(line_color)

        if line is not None:
            line = TelemetryDisplay.draw_hud(line, lap_tracker, nav_manager)
            
        return line

    def show_results(self, images):
        """
        Displays all processing windows.

        Args:
            images (dict): Dictionary where the key is the window name
            and the value is the image to display.

        The method only displays windows for results that are available.
        """

        for name, image in images.items():
            if image is not None:
                cv2.imshow(name, image)

    def run_test_from_image(self, path):
        """
        Runs navigation pipeline on a single static image file for testing.

        Args:
            path (str): File system path to input image.
        """
        nav_manager = NavigationManager()

        frame = cv2.imread(path)

        if frame is None:
            print(f"Could not open image: {path}")
            return

        pillars_color, pillars, pillar_mask = self.process_elements(
            frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar
        )
        line_color, line, line_mask = self.process_elements(
            frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line
        )

        if line_color:
            nav_manager.line_direction(line_color)

        current_dir = "Clockwise"

        walls, target_yaw, is_corner = self.process_walls(frame, current_dir, current_yaw=0)

        self.show_results({
            "Walls": walls,
            "Pillars": pillars,
            "Pillar Mask": pillar_mask,
            "Lines": line,
            "Line Mask": line_mask
        })

        print("Pillar: " + str(pillars_color))
        print("Line: " + str(line_color))
        print(f"Robot Angle: {target_yaw}° | Corner: {is_corner} | Dir: {current_dir}")

        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def run_test(self):
        """Runs the continuous live execution loop using camera feed and IMU targets."""
        nav_manager = NavigationManager()
        lap_tracker = LapTracker()

        current_yaw = 0.0

        try:
            while True:
                frame = self.camera.read()
                if frame is None:
                    break

                # 1. RETROALIMENTACIÓN: Leer el Yaw real que envía la ESP32 (si está disponible)
                if self.serial_bridge:
                    sensor_yaw = self.serial_bridge.read_current_yaw()
                    if sensor_yaw is not None:
                        current_yaw = sensor_yaw

                # 2. Procesamiento de elementos de visión
                pillars_color, pillars, pillar_mask = self.process_elements(
                    frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar
                )
                line_color, line, line_mask = self.process_elements(
                    frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line
                )

                line = self.process_navigation(
                    line_color, line, nav_manager, lap_tracker
                )

                if nav_manager.direction:
                    current_dir = (
                        nav_manager.direction.value
                        if isinstance(nav_manager.direction, Direction)
                        else nav_manager.direction
                    )
                else:
                    current_dir = "Clockwise"

                # 3. Calcular target_yaw usando la pared y el current_yaw actual
                walls, target_yaw, is_corner = self.process_walls(
                    frame, current_dir, current_yaw
                )

                # 4. ENVIAR COMANDO A LA ESP32
                if self.serial_bridge:
                    self.serial_bridge.send_target_heading(target_yaw, is_corner)

                # 5. Renderizado y Telemetría
                self.show_results({
                    "Walls": walls,
                    "Pillars": pillars,
                    "Pillar Mask": pillar_mask,
                    "Lines": line,
                    "Line Mask": line_mask,
                })

                print(
                    f"Current Yaw: {current_yaw:.1f}° | Target Yaw: {target_yaw:.1f}° | Corner: {is_corner}"
                )

                if cv2.waitKey(1) == 27:
                    break

        finally:
            # Asegura cerrar el puerto serie correctamente al salir con ESC o interrupción
            if self.serial_bridge:
                self.serial_bridge.close()
            self.camera.release()
            cv2.destroyAllWindows()

    def run_open_test(self):
        nav_manager = NavigationManager()
        lap_tracker = LapTracker()

        corner_detector = CornerROIDetector(
            pic_width=self.pic_width,
            pic_height=self.pic_height,
            mode="front_wall",   # "inner_floor" for the inner-wall variant
            confirm_frames=3,
            cooldown_s=2.0,
        )

        video_logger = VideoWriterLogger(
            output_dir="logs_video", fps=20.0,
            frame_size=(self.pic_width, self.pic_height),
        )

        current_yaw = 0.0
        base_heading = 0.0
        turning = False
        turn_deadline = 0.0
        TURN_TOLERANCE_DEG = 12.0
        TURN_TIMEOUT_S = 3.0

        try:
            while True:
                frame = self.camera.read()
                if frame is None:
                    break

                now = time.time()

                # 1. IMU feedback (drain the buffer: keep only the newest yaw)
                if self.serial_bridge:
                    sensor_yaw = self.serial_bridge.read_current_yaw()
                    if sensor_yaw is not None:
                        current_yaw = sensor_yaw

                # 2. Lines -> direction and lap counting
                line_color, line, line_mask, target_line = self.process_elements(
                    frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line
                )
                line = self.process_navigation(line_color, line, nav_manager, lap_tracker)

                current_dir = nav_manager.direction or "Clockwise"
                turn_step = (90 if is_clockwise(current_dir) else -90) * YAW_CW_SIGN

                # 3. Walls -> mask + straight-line steering target
                walls_dbg, wall_mask, wall_target_yaw = self.process_walls(
                    frame, current_dir, base_heading
                )

                # 4. Corner decision: ONE source of truth
                info = corner_detector.update(wall_mask, current_dir, now=now)

                # 5. Decision hierarchy
                if info["corner"] and not turning:
                    base_heading = (base_heading + turn_step) % 360
                    turning = True
                    turn_deadline = now + TURN_TIMEOUT_S
                    mode_str = f"CORNER -> base {base_heading:.0f}"

                if turning:
                    # Commit to the cardinal heading until the turn is finished.
                    target_yaw = base_heading
                    err = abs(angle_diff(current_yaw, base_heading))
                    if err < TURN_TOLERANCE_DEG or now > turn_deadline:
                        turning = False
                        corner_detector.reset()
                    mode_str = f"TURNING -> {base_heading:.0f} (err {err:.0f})"
                else:
                    offset = angle_diff(wall_target_yaw, base_heading)
                    offset = max(-12.0, min(12.0, offset))
                    target_yaw = (base_heading + offset) % 360
                    mode_str = f"STRAIGHT base {base_heading:.0f} off {offset:+.0f}"

                # 6. Command out
                if self.serial_bridge:
                    self.serial_bridge.send_target_heading(target_yaw, info["corner"])

                print(
                    f"{mode_str} | ratio {info['ratio']:.2f} armed {info['armed']} "
                    f"cd {info['cooldown']:.1f} | cur {current_yaw:.1f} tgt {target_yaw:.1f}"
                )

                # 7. Debug view: draw the ROI on the mask so you can tune it live
                walls_dbg = corner_detector.draw(walls_dbg, current_dir, info)
                walls_dbg = TelemetryDisplay.draw_hud(
                    walls_dbg,
                    lap_tracker=lap_tracker,
                    nav_manager=nav_manager,
                    mode_str=mode_str,
                    extra_lines=[
                        f"ROI {info['ratio']:.2f}  armed {info['armed']}",
                        f"Yaw {current_yaw:.0f} -> {target_yaw:.0f}",
                    ],
                )
                video_logger.write(walls_dbg)


                if not HEADLESS:
                    cv2.imshow("Walls + ROI", walls_dbg)
                    if cv2.waitKey(1) == 27:
                        break

                if lap_tracker.finished:
                    break

        except KeyboardInterrupt:
            print("\nStopped by user (Ctrl + C).")
        finally:
            video_logger.release()
            if self.serial_bridge:
                self.serial_bridge.close()
            self.camera.release()
            if not HEADLESS:
                cv2.destroyAllWindows()


    def run_obstacle_test(self):
        """Ejecuta el Obstacle Test sin abrir ventanas."""
        nav_manager = NavigationManager()

        # --- Direccion: se mide SOLO al inicio y queda congelada ---
        current_dir = None
        direction_locked = False
        direction_samples = 0
        direction_votes = {"Clockwise": 0, "Counter-Clockwise": 0}
        direction_objs = {}
        DIRECTION_SAMPLE_FRAMES = 20
        DIRECTION_MAX_FRAMES = 60

        corner_detector = CornerROIDetector(
            pic_width=self.pic_width,
            pic_height=self.pic_height,
            mode="front_wall",
            confirm_frames=3,
            cooldown_s=2.0,
        )

        video_logger = VideoWriterLogger(
            output_dir="logs_video",
            fps=20.0,
            frame_size=(self.pic_width, self.pic_height),
        )

        current_yaw = 0.0
        base_heading = 0.0

        turning = False
        turn_deadline = 0.0

        TURN_TOLERANCE_DEG = 12.0
        TURN_TIMEOUT_S = 3.0

        # --- Evasion del pilar en 3 fases ---
        avoiding_pillar = False
        avoidance_phase = "NONE"
        active_pillar = None
        avoidance_side = 0.0
        phase_frames = 0
        pillar_clear_frames = 0

        PILLAR_STEER_DEG = 18.0
        PILLAR_PASS_DEG = 12.0
        PILLAR_STEER_FRAMES = 6
        PILLAR_CLEAR_FRAMES = 8
        PILLAR_RECOVER_FRAMES = 10

        try:
            while True:
                frame = self.camera.read()

                if frame is None:
                    break

                now = time.time()

                # Leer yaw actual
                if self.serial_bridge:
                    sensor_yaw = self.serial_bridge.read_current_yaw()

                    if sensor_yaw is not None:
                        current_yaw = sensor_yaw

                # 1. Detectar pilares antes de tomar decisiones de pared
                pillars_color, pillar_frame, pillar_mask, target_pillar = (
                    self.process_elements(
                        frame,
                        ["Red", "Green"],
                        500,
                        VisionUtils.select_target_pillar,
                    )
                )

                # Mientras no hay direccion fijada se usa "Clockwise"
                # solo para poder procesar la imagen.
                processing_direction = (
                    current_dir if direction_locked else "Clockwise"
                )

                # Obtener mascara y objetivo de pared
                walls_dbg, wall_mask, wall_target_yaw = self.process_walls(
                    frame,
                    processing_direction,
                    base_heading,
                )

                # 2. Direccion: SOLO durante los primeros frames.
                #    Una vez fijada no se vuelve a medir nunca.
                # 2. Direccion: SOLO durante los primeros frames.
                #    Una vez fijada no se vuelve a medir nunca.
                if not direction_locked:
                    # wall_mask: blanco = pared, negro = piso.
                    # park_direction necesita blanco = espacio libre.
                    track_mask = cv2.bitwise_not(wall_mask)
                    sampled = nav_manager.park_direction(track_mask)

                    # Comparar por texto: el enum puede venir de otro
                    # modulo y entonces nunca coincide por identidad.
                    sampled_value = getattr(sampled, "value", str(sampled))

                    if sampled_value in direction_votes:
                        direction_votes[sampled_value] += 1
                        direction_objs[sampled_value] = sampled
                        direction_samples += 1

                    # No usar ni mostrar la direccion hasta confirmarla
                    nav_manager.direction = None

                    cw_votes = direction_votes["Clockwise"]
                    ccw_votes = direction_votes["Counter-Clockwise"]

                    print(
                        f"[DIR] muestra {direction_samples}"
                        f"/{DIRECTION_SAMPLE_FRAMES} "
                        f"-> {sampled_value} "
                        f"(CW={cw_votes} CCW={ccw_votes})"
                    )

                    if direction_samples >= DIRECTION_SAMPLE_FRAMES:
                        winner = (
                            "Counter-Clockwise"
                            if ccw_votes > cw_votes
                            else "Clockwise"
                        )

                        current_dir = winner
                        nav_manager.direction = direction_objs[winner]
                        direction_locked = True

                        print(
                            f"[DIR] Direccion fijada: {current_dir} "
                            f"(CW={cw_votes} CCW={ccw_votes})"
                        )

                 # 3. Entrar o mantenerse en la evasion del pilar
                if not avoiding_pillar and target_pillar is not None:
                    avoiding_pillar = True
                    avoidance_phase = "PILLAR_STEER"
                    active_pillar = target_pillar.copy()

                    # Rojo se pasa por la DERECHA, verde por la IZQUIERDA
                    avoidance_side = (
                        1.0 if target_pillar["color"] == "Red" else -1.0
                    )

                    phase_frames = 0
                    pillar_clear_frames = 0

                    # Cancelar cualquier giro de pared pendiente
                    turning = False
                    corner_detector.reset()

                elif avoiding_pillar and target_pillar is not None:
                    active_pillar = target_pillar.copy()
                    pillar_clear_frames = 0

                    # Si reaparece durante la recuperacion,
                    # todavia no terminamos de rebasarlo.
                    if avoidance_phase == "PILLAR_RECOVER":
                        avoidance_phase = "PILLAR_PASS"
                        phase_frames = 0

                if avoiding_pillar:
                    phase_frames += 1

                    if target_pillar is None:
                        pillar_clear_frames += 1

                    # Mientras se evade el pilar, la pared queda ignorada
                    info = {
                        "corner": False,
                        "ratio": corner_detector.last_ratio,
                        "armed": False,
                        "cooldown": 0.0,
                    }

                else:
                    # El detector de esquinas solo trabaja fuera de la evasión
                    if direction_locked:
                        info = corner_detector.update(
                            wall_mask,
                            current_dir,
                            now=now,
                        )
                    else:
                        info = {
                            "corner": False,
                            "ratio": 0.0,
                            "armed": False,
                            "cooldown": 0.0,
                        }

                # =========================================================
                # PRIORIDAD 1: EVASION DEL PILAR (3 fases)
                # =========================================================
                if avoiding_pillar:
                    color = active_pillar["color"]
                    side = "DERECHA" if avoidance_side > 0 else "IZQUIERDA"

                    if avoidance_phase == "PILLAR_STEER":
                        target_yaw = (
                            base_heading + avoidance_side * PILLAR_STEER_DEG
                        ) % 360
                        mode_str = f"PILLAR_STEER {color} -> {side}"

                        if phase_frames >= PILLAR_STEER_FRAMES:
                            avoidance_phase = "PILLAR_PASS"
                            phase_frames = 0

                    elif avoidance_phase == "PILLAR_PASS":
                        target_yaw = (
                            base_heading + avoidance_side * PILLAR_PASS_DEG
                        ) % 360
                        mode_str = f"PILLAR_PASS {color} -> {side}"

                        if pillar_clear_frames >= PILLAR_CLEAR_FRAMES:
                            avoidance_phase = "PILLAR_RECOVER"
                            phase_frames = 0

                    else:
                        avoidance_phase = "PILLAR_RECOVER"
                        target_yaw = base_heading
                        mode_str = f"PILLAR_RECOVER {color}"

                        if phase_frames >= PILLAR_RECOVER_FRAMES:
                            avoiding_pillar = False
                            avoidance_phase = "NONE"
                            active_pillar = None
                            avoidance_side = 0.0
                            phase_frames = 0
                            pillar_clear_frames = 0

                            corner_detector.reset()

                    corner_command = False

                # =========================================================
                # PRIORIDAD 2: ESPERAR LA DIRECCION
                # =========================================================
                elif not direction_locked:
                    target_yaw = base_heading
                    mode_str = "DETERMINANDO DIRECCION"
                    corner_command = False

                # =========================================================
                # PRIORIDAD 2 Y 3: ESQUINAS Y PARED
                # =========================================================
                else:
                    turn_step = (
                        90 if is_clockwise(current_dir) else -90
                    ) * YAW_CW_SIGN

                    # Detectar esquina
                    if info["corner"] and not turning:
                        base_heading = (
                            base_heading + turn_step
                        ) % 360

                        turning = True
                        turn_deadline = now + TURN_TIMEOUT_S

                    # Ejecutar giro
                    if turning:
                        target_yaw = base_heading

                        error = abs(
                            angle_diff(
                                current_yaw,
                                base_heading,
                            )
                        )

                        if (
                            error < TURN_TOLERANCE_DEG
                            or now > turn_deadline
                        ):
                            turning = False
                            corner_detector.reset()

                        mode_str = (
                            f"TURNING -> "
                            f"{base_heading:.0f} "
                            f"(error {error:.0f})"
                        )

                    # Seguir pared normalmente
                    else:
                        offset = angle_diff(
                            wall_target_yaw,
                            base_heading,
                        )

                        offset = max(
                            -12.0,
                            min(12.0, offset),
                        )

                        target_yaw = (
                            base_heading + offset
                        ) % 360

                        mode_str = (
                            f"PAREDES "
                            f"base {base_heading:.0f} "
                            f"offset {offset:+.0f}"
                        )

                    corner_command = info["corner"]

                # Enviar heading absoluto
                if self.serial_bridge:
                    self.serial_bridge.send_target_heading(
                        target_yaw,
                        corner_command,
                    )

                print(
                    f"Modo: {mode_str} | "
                    f"Base: {base_heading:.0f}° | "
                    f"Actual: {current_yaw:.1f}° | "
                    f"Objetivo: {target_yaw:.1f}°"
                )

                # Dibujar información sobre el video
                walls_dbg = corner_detector.draw(
                    walls_dbg,
                    processing_direction,
                    info,
                )

                walls_dbg = TelemetryDisplay.draw_hud(
                    walls_dbg,
                    nav_manager=nav_manager,
                    mode_str=mode_str,
                    extra_lines=[
                        f"Pilar: {pillars_color or 'Ninguno'}",
                        f"Fase: {avoidance_phase}",
                        (
                            f"Yaw {current_yaw:.0f} "
                            f"-> {target_yaw:.0f}"
                        ),
                    ],
                )

                # Guardar video
                video_logger.write(walls_dbg)

                # No agregar imshow(), waitKey() ni destroyAllWindows()

        except KeyboardInterrupt:
            print("\nPrueba de obstáculos detenida.")

        finally:
            video_logger.release()

            if self.serial_bridge:
                self.serial_bridge.close()

            self.camera.release()
