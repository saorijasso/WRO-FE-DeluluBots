import cv2

from camera.camera import Camera
from comms.ESP32bridge import ESP32Bridge
from config import saved_ranges
from processing.transform_image import VisionUtils
from processing.telemetry_display import TelemetryDisplay
from navigation.direction_manager import Direction, NavigationManager, LapTracker
from navigation.wall_follower_controller import WallFollowerController       


class ImageManager:

    def __init__(self):
        """
        Initializes the camera and creates the display windows.
        """

        self.camera = Camera()
        self.wall_follower = WallFollowerController(pic_width=700, pic_height=350)
        self.serial_bridge = ESP32Bridge()

        cv2.namedWindow("Walls")
        cv2.namedWindow("Pillars")
        cv2.namedWindow("Mask")

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
            return None, None, None

        best_element = method(elements)

        result = frame.copy()
        result = TelemetryDisplay.draw_element(best_element, result)
        result = VisionUtils.resize(result, 700, 350)

        mask = VisionUtils.resize(best_element["mask"], 700, 350)

        return best_element["color"], result, mask

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