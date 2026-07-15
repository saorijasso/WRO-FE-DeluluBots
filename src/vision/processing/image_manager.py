import cv2

from camera.camera import Camera
from config import saved_ranges
from processing.transform_image import VisionUtils


class ImageManager:

    def __init__(self):
        """
        Initializes the camera and creates the display windows.
        """

        self.camera = Camera()

        cv2.namedWindow("Walls")
        cv2.namedWindow("Pillars")
        cv2.namedWindow("Mask")

    def process_walls(self, frame):
        """
        Applies the wall detection pipeline.

        Args:
            frame (numpy.ndarray): Original frame.

        Returns:
            numpy.ndarray: Processed binary image containing the detected wall.
        """

        image = VisionUtils.replace_color(
            frame,
            saved_ranges.color_ranges,
            ["Red", "Green"]
        )

        image = VisionUtils.resize(image, 700, 350)
        image = VisionUtils.grayscale(image)
        image = VisionUtils.blur(image)
        image = VisionUtils.binary(image)
        image = VisionUtils.clean_binary(image)
        image = VisionUtils.keep_largest_white(image)

        return image

    def process_pillars(self, frame):
        """
        Detects the closest pillar and draws its bounding box.

        Args:
            frame (numpy.ndarray): Original frame.

        Returns:
            tuple: A tuple containing:

                - str: Pillar color.
                - numpy.ndarray: Frame with the pillar drawn.
                - numpy.ndarray: Pillar mask.

            Returns (None, None, None) if no pillar is detected.
        """

        MIN_AREA = 500
        elements = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red = VisionUtils.detect_element(hsv, saved_ranges.color_ranges, "Red", MIN_AREA)
        if red is not None:
            elements.append(red)

        green = VisionUtils.detect_element(hsv, saved_ranges.color_ranges, "Green", MIN_AREA)
        if green is not None:
            elements.append(green)
        
        if len(elements) == 0:
            return None, None, None

        best_pillar = VisionUtils.select_target_pillar(elements)

        result = frame.copy()
        result = VisionUtils.draw_element(best_pillar, result)
        result = VisionUtils.resize(result, 700, 350)

        mask = VisionUtils.resize(best_pillar["mask"], 700, 350)

        return best_pillar["color"], result, mask

    def show_results(self, walls, pillars, mask):
        """
        Displays all processing windows.

        Args:
            walls (numpy.ndarray): Wall detection result.
            pillars (numpy.ndarray): Frame with pillar annotations.
            mask (numpy.ndarray): Binary mask of the detected pillar.

        The method only displays windows for results that are available.
        """
        if walls is not None:
            cv2.imshow("Walls", walls)
        
        if pillars is not None:
            cv2.imshow("Pillars", pillars)

        if mask is not None:
            cv2.imshow("Mask", mask)

    def run_test_from_image(self, path):
        """
        Runs the processing pipeline using a saved image.

        Args:
            path (str): Image path.
        """

        frame = cv2.imread(path)

        if frame is None:
            print(f"Could not open image: {path}")
            return

        walls = self.process_walls(frame)

        color, pillars, mask = self.process_pillars(frame)

        self.show_results(walls, pillars, mask)

        print(color)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def run_test(self):
        """
        Runs the processing pipeline using the camera stream.
        """

        while True:

            frame = self.camera.read()

            if frame is None:
                break

            walls = self.process_walls(frame)

            color, pillars, mask = self.process_pillars(frame)

            self.show_results(walls, pillars, mask)

            print(color)

            if cv2.waitKey(1) == 27:
                break

        self.camera.release()
        cv2.destroyAllWindows()