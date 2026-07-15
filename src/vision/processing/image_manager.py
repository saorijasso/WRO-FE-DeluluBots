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
        result = VisionUtils.draw_element(best_element, result)
        result = VisionUtils.resize(result, 700, 350)

        mask = VisionUtils.resize(best_element["mask"], 700, 350)

        return best_element["color"], result, mask

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
        Runs the processing pipeline using a saved image.

        Args:
            path (str): Image path.
        """

        frame = cv2.imread(path)

        if frame is None:
            print(f"Could not open image: {path}")
            return

        walls = self.process_walls(frame)

        pillars_color, pillars, pillar_mask = self.process_elements(frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar)
        line_color, line, line_mask = self.process_elements(frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line)

        self.show_results({
            "Walls": walls,
            "Pillars": pillars,
            "Pillar Mask": pillar_mask,
            "Lines": line,
            "Line Mask": line_mask
        })

        print("Pillar: " + str(pillars_color))
        print("Line: " + str(line_color))

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

            pillars_color, pillars, pillar_mask = self.process_elements(frame, ["Red", "Green"], 500, VisionUtils.select_target_pillar)
            line_color, line, line_mask = self.process_elements(frame, ["Orange", "Blue"], 200, VisionUtils.select_target_line)

            self.show_results({
                "Walls": walls,
                "Pillars": pillars,
                "Pillar Mask": pillar_mask,
                "Lines": line,
                "Line Mask": line_mask
            })

            print("Pillar: " + str(pillars_color))
            print("Line: " + str(line_color))

            if cv2.waitKey(1) == 27:
                break

        self.camera.release()
        cv2.destroyAllWindows()