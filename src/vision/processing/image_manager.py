import cv2

from camera.camera import Camera
from comms.ESP32bridge import ESP32Bridge
from config import saved_ranges
from processing.transform_image import VisionUtils
from processing.telemetry_display import TelemetryDisplay
from navigation.direction_manager import Direction, NavigationManager, LapTracker
from navigation.wall_follower_controller import WallFollowerController
from vision.navigation.crash_detector import CrashDetector
from vision.navigation.sign_navigation_controller import SignNavigation       


class ImageManager:

    def __init__(self):
        """
        Initializes the camera and creates the display windows.
        """

        self.camera = Camera()
        self.wall_follower = WallFollowerController(pic_width=700, pic_height=350)
        self.serial_bridge = ESP32Bridge()

    def process_walls(self, frame, direction, current_yaw):
        """
        Processes image frame to track wall boundaries and compute target IMU heading.

        Args:
            frame (numpy.ndarray): Input camera frame in BGR format.
            direction (str): Driving direction ("Clockwise" or "CounterClockwise").
            current_yaw (float): Current Yaw orientation angle from IMU in degrees.

        Returns:
            tuple:
                - numpy.ndarray: Rendered image with visual telemetry overlays.
                - float: Calculated target IMU Yaw angle in degrees (0 to 360).
                - bool: True if an upcoming corner turn is detected, False otherwise.
        """
        # Preprocessing pipeline
        image = VisionUtils.replace_color(
            frame, saved_ranges.color_ranges, ["Red", "Green"]
        )
        image = VisionUtils.resize(image, 700, 350)
        image = VisionUtils.grayscale(image)
        image = VisionUtils.blur(image)
        image = VisionUtils.binary(image)
        image = VisionUtils.clean_binary(image)
        image = VisionUtils.keep_largest_white(image)

        # Lateral wall centroid detection
        avg_x, avg_y = VisionUtils.find_wall_to_follow(image, direction)

        if avg_x is None or avg_y is None:
            # If no wall is detected, keep current heading and do not force a corner
            return None, current_yaw, False

        # Physical corner detection
        corner_x, corner_y = VisionUtils.find_real_corner(image, direction)

        should_turn = corner_y > 200 if (corner_x is not None and corner_y is not None) else False

        # Calculate target IMU heading via wall follower controller
        target_yaw, pd_corner = self.wall_follower.calculate_target_yaw(
            avg_x, avg_y, direction, current_yaw, threshold=480
        )

        # Combine corner detections (either physical vision corner or PD drop)
        is_corner = should_turn or pd_corner

        # Telemetry overlay drawing
        result = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Wall tracking point (Yellow)
        cv2.circle(result, (int(avg_x), int(avg_y)), 7, (0, 255, 255), -1)

        # Real corner point (Blue)
        if corner_x is not None and corner_y is not None:
            cv2.circle(result, (int(corner_x), int(corner_y)), 9, (255, 191, 0), -1)

        if is_corner:
            cv2.putText(result, "TURNING NOW!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return result, target_yaw, is_corner

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
        """Runs the continuous live execution loop using camera feed and IMU targets."""
        nav_manager = NavigationManager()
        lap_tracker = LapTracker()
        crash_detector = CrashDetector(pic_width=700, pic_height=350)

        current_yaw = 0.0
        base_heading = 0.0
        corner_cooldown = 0

        try:
            while True:
                frame = self.camera.read()
                if frame is None:
                    break

                if corner_cooldown > 0:
                    corner_cooldown -= 1

                # 1. RETROALIMENTACIÓN IMU
                if self.serial_bridge:
                    sensor_yaw = self.serial_bridge.read_current_yaw()
                    if sensor_yaw is not None:
                        current_yaw = sensor_yaw

                # 2. PROCESAMIENTO DE LÍNEAS / NAVEGACIÓN
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

                # 3. PROCESAMIENTO DE PAREDES
                walls, wall_target_yaw, is_corner = self.process_walls(
                    frame, current_dir, current_yaw
                )

                # 4. VERIFICACIÓN DE CHOQUES EN LA MÁSCARA
                wall_mask = walls
                outer_crash = crash_detector.check_outer_wall_crash(wall_mask)
                inner_crash = crash_detector.check_inner_wall_crash(wall_mask, current_dir)

                # =========================================================
                # 5. JERARQUÍA DE DECISIÓN (PRUEBA ABIERTA)
                # =========================================================

                # --- PRIORIDAD 0: CHOQUE FRONTAL / EXTERIOR ---
                if outer_crash:
                    turn_step = -90 if current_dir == "Clockwise" else 90
                    if corner_cooldown == 0:
                        base_heading = (base_heading + turn_step) % 360
                        corner_cooldown = 30
                    target_yaw = base_heading
                    mode_str = "ALERTA: Choque Frontal -> Giro Forzado!"

                # --- PRIORIDAD 0.5: CHOQUE EN PARED INTERNA ---
                elif inner_crash:
                    avoid_offset = -15 if current_dir == "Clockwise" else 15
                    target_yaw = (current_yaw + avoid_offset) % 360
                    mode_str = "ALERTA: Corrigiendo Pared Interna"

                # --- PRIORIDAD 1: ESQUINA DETECTADA POR VISIÓN ---
                elif is_corner and corner_cooldown == 0:
                    turn_step = -90 if current_dir == "Clockwise" else 90
                    base_heading = (base_heading + turn_step) % 360
                    target_yaw = base_heading
                    corner_cooldown = 30
                    mode_str = f"Esquina -> Nuevo Heading: {base_heading}°"

                # --- PRIORIDAD 2: SEGUIMIENTO NORMAL DE PAREDES ---
                else:
                    target_yaw = wall_target_yaw
                    mode_str = "Paredes"

                # 6. ENVIAR COMANDO A LA ESP32
                if self.serial_bridge:
                    self.serial_bridge.send_target_heading(target_yaw, is_corner)

                print(
                    f"Modo: {mode_str} | Base: {base_heading}° | Current: {current_yaw:.1f}° | Target: {target_yaw:.1f}° | Corner: {is_corner}"
                )

        except KeyboardInterrupt:
            print("\nEjecución detenida manualmente por el usuario (Ctrl + C).")

        finally:
            if self.serial_bridge:
                self.serial_bridge.close()
            self.camera.release()
            cv2.destroyAllWindows()


    def run_obstacle_test(self):
        nav_manager = NavigationManager()
        sign_nav = SignNavigation(camera_fov_x=60.0)
        wall_controller = WallFollowerController(pic_width=700, pic_height=350)
        crash_detector = CrashDetector(pic_width=700, pic_height=350)

        current_yaw = 0.0
        base_heading = 0.0
        corner_cooldown = 0

        try:
            while True:
                frame = self.camera.read()
                if frame is None:
                    break

                if corner_cooldown > 0:
                    corner_cooldown -= 1

                # 1. RETROALIMENTACIÓN IMU
                if self.serial_bridge:
                    sensor_yaw = self.serial_bridge.read_current_yaw()
                    if sensor_yaw is not None:
                        current_yaw = sensor_yaw

                # 2. PROCESAMIENTO DE PILARES Y PAREDES (Procesamos todo primero)
                pillars_color, pillar_frame, pillar_mask, target_pillar = self.process_elements(
                    frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar
                )

                current_dir = (
                    nav_manager.direction.value
                    if isinstance(nav_manager.direction, Direction)
                    else (nav_manager.direction or "Clockwise")
                )

                walls, wall_target_yaw, is_corner = self.process_walls(
                    frame, current_dir, current_yaw
                )

                # 3. VERIFICACIÓN DE CHOQUES EN LA MÁSCARA
                wall_mask = walls
                outer_crash = crash_detector.check_outer_wall_crash(wall_mask)
                inner_crash = crash_detector.check_inner_wall_crash(wall_mask, current_dir)

                frame_width = frame.shape[1]

                # =========================================================
                # 4. JERARQUÍA DE DECISIÓN (ORDEN DE PRIORIDAD CORREGIDO)
                # =========================================================

                # --- PRIORIDAD 0: CHOQUE FRONTÁL / EXTERIOR ---
                if outer_crash:
                    turn_step = -90 if current_dir == "Clockwise" else 90
                    if corner_cooldown == 0:
                        base_heading = (base_heading + turn_step) % 360
                        corner_cooldown = 30
                    target_yaw = base_heading
                    mode_str = "ALERTA: Choque Frontal -> Giro Forzado!"

                # --- PRIORIDAD 0.5: CHOQUE EN PARED INTERNA ---
                elif inner_crash:
                    avoid_offset = -15 if current_dir == "Clockwise" else 15
                    target_yaw = (current_yaw + avoid_offset) % 360
                    mode_str = "ALERTA: Corrigiendo Pared Interna"

                # --- PRIORIDAD 1: ESQUIVAR PILAR ---
                elif target_pillar is not None:
                    target_yaw = sign_nav.calculate_avoidance_yaw(
                        target_pillar, frame_width, base_heading
                    )
                    mode_str = f"Pilar ({target_pillar['color']})"

                # --- PRIORIDAD 2: ESQUINA DETECTADA ---
                elif is_corner and corner_cooldown == 0:
                    turn_step = -90 if current_dir == "Clockwise" else 90
                    base_heading = (base_heading + turn_step) % 360
                    target_yaw = base_heading
                    corner_cooldown = 30
                    mode_str = f"Esquina -> Nuevo Heading: {base_heading}°"

                # --- PRIORIDAD 3: SEGUIMIENTO NORMAL DE PAREDES ---
                else:
                    target_yaw = wall_target_yaw
                    mode_str = "Paredes"

                # 5. ENVIAR ÚNICAMENTE TARGET_YAW ABSOLUTO
                if self.serial_bridge:
                    self.serial_bridge.send_target_heading(target_yaw)

                print(
                    f"Modo: {mode_str} | Base: {base_heading}° | Current: {current_yaw:.1f}° | Target: {target_yaw:.1f}°"
                )

        except KeyboardInterrupt:
            print("\nPrueba de obstáculos detenida.")
        finally:
            if self.serial_bridge:
                self.serial_bridge.close()
            self.camera.release()