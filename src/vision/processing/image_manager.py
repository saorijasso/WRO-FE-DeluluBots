import cv2

from camera.camera import Camera
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

        cv2.namedWindow("Walls")
        cv2.namedWindow("Pillars")
        cv2.namedWindow("Mask")

    def process_walls(self, frame, direction):
        """
        Processes image frame to track wall boundaries and compute steering parameters.

        Args:
            frame (numpy.ndarray): Input camera frame in BGR format.
            direction (str): Driving direction ("Clockwise" or "CounterClockwise").

        Returns:
            tuple:
                - numpy.ndarray: Rendered image with visual telemetry overlays.
                - int: Calculated steering angle in degrees.
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
            return None, 90, False

        # Physical corner detection
        corner_x, corner_y = VisionUtils.find_real_corner(image, direction)

        should_turn = corner_y > 200 if (corner_x is not None and corner_y is not None) else False

        # Calculate base steering via PD controller
        steering_angle, pd_corner = self.wall_follower.calculate_steering(
            avg_x, avg_y, direction, kp=0.35, kd=0.25, threshold=480
        )

        # Override steering angle if corner is nearby
        if should_turn:
            steering_angle = 60 if direction == "Clockwise" else 120

        # Telemetry overlay drawing
        result = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Wall tracking point (Yellow)
        cv2.circle(result, (int(avg_x), int(avg_y)), 7, (0, 255, 255), -1)

        # Real corner point (Blue)
        if corner_x is not None and corner_y is not None:
            cv2.circle(result, (int(corner_x), int(corner_y)), 9, (255, 191, 0), -1)

        if should_turn:
            cv2.putText(result, "TURNING NOW!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return result, steering_angle, should_turn

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

        if nav_manager.direction:
            current_dir = nav_manager.direction.value if isinstance(nav_manager.direction, Direction) else nav_manager.direction
        else:
            current_dir = "Clockwise"

        walls, steering_angle, is_corner = self.process_walls(frame, current_dir)

        self.show_results({
            "Walls": walls,
            "Pillars": pillars,
            "Pillar Mask": pillar_mask,
            "Lines": line,
            "Line Mask": line_mask
        })

        print("Pillar: " + str(pillars_color))
        print("Line: " + str(line_color))
        print(f"Servo Angle: {steering_angle}° | Corner: {is_corner} | Dir: {current_dir}")

        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def run_test(self):
        """
        Runs the continuous live execution loop using camera feed.
        """
        nav_manager = NavigationManager()
        lap_tracker = LapTracker()

        while True:
            frame = self.camera.read()
            if frame is None:
                break

            pillars_color, pillars, pillar_mask = self.process_elements(
                frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar
            )
            line_color, line, line_mask = self.process_elements(
                frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line
            )

            line = self.process_navigation(line_color, line, nav_manager, lap_tracker)

            if nav_manager.direction:
                current_dir = nav_manager.direction.value if isinstance(nav_manager.direction, Direction) else nav_manager.direction
            else:
                current_dir = "Clockwise"

            walls, steering_angle, is_corner = self.process_walls(frame, current_dir)

            self.show_results({
                "Walls": walls,
                "Pillars": pillars,
                "Pillar Mask": pillar_mask,
                "Lines": line,
                "Line Mask": line_mask
            })

            print(f"Corners: {lap_tracker.corners} | Phase: {lap_tracker.phase.name} | Dir: {current_dir}")
            print(f"Servo Angle: {steering_angle}° | Corner: {is_corner}")

            if cv2.waitKey(1) == 27: 
                break

        self.camera.release()
        cv2.destroyAllWindows()