import cv2
import numpy as np

class VisionUtils:

    @staticmethod
    def resize(image, width, height):
        """
        Resizes the image to the specified dimensions.

        Args:
            image (numpy.ndarray): Image to resize.
            width (int): Desired width in pixels.
            height (int): Desired height in pixels.

        Returns:
            numpy.ndarray: Resized image.
        """

        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def hsv_binary_mask(frame, low, high):
        """
        Creates a binary mask using an HSV color range.

        Args:
            frame (numpy.ndarray): Original frame in BGR format.
            low (tuple): Lower HSV limit.
            high (tuple): Upper HSV limit.

        Returns:
            numpy.ndarray: Binary mask containing the selected color.
        """

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return cv2.inRange(hsv, np.array(low), np.array(high))
    
    @staticmethod
    def replace_color(frame, color_ranges, colors_to_white,):
        """
        Replaces the specified colors with white in the given frame.

        Args:
            frame (numpy.ndarray): Original image in BGR format.
            color_ranges (dict): Dictionary containing the HSV ranges
                associated with each color.
            colors_to_white (tuple): Colors that will be replaced with white.

        Returns:
            numpy.ndarray: Processed image with the selected colors replaced.
        """

        result = frame.copy()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for color in colors_to_white:
            if color not in color_ranges:
                continue
            low, high = color_ranges[color]
            mask = cv2.inRange(hsv, np.array(low), np.array(high))
            result[mask > 0] = (255, 255, 255)

        if "Pink" in color_ranges:
            low, high = color_ranges["Pink"]
            mask = cv2.inRange(hsv, np.array(low), np.array(high))
            result[mask > 0] = (0, 0, 0)

        return result
    
    @staticmethod
    def grayscale(frame):
        """
        Converts a BGR image to grayscale.

        Args:
            frame (numpy.ndarray): Original frame in BGR format.

        Returns:
            numpy.ndarray: Grayscale image.
        """

        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    @staticmethod
    def blur(frame):
        """
        Applies a bilateral filter to reduce noise while preserving edges.

        Args:
            frame (numpy.ndarray): Input image.

        Returns:
            numpy.ndarray: Smoothed image.
        """

        return cv2.bilateralFilter(frame, 8, 60, 60)
    
    @staticmethod
    def binary(frame, threshold = 100):
        """
        Converts an image into a binary image using a threshold value.

        Args:
            frame (numpy.ndarray): Grayscale image.
            threshold (int, optional): Threshold value. Defaults to 100.

        Returns:
            numpy.ndarray: Binary image.
        """

        _, binary = cv2.threshold(frame, threshold, 255, cv2.THRESH_BINARY)
        return binary
    
    @staticmethod
    def clean_binary(frame):
        """
        Removes small gaps and noise from a binary image using
        morphological closing.

        Args:
            frame (numpy.ndarray): Binary image.

        Returns:
            numpy.ndarray: Cleaned binary image.
        """

        kernel = np.ones((5, 5), np.uint8)
        return cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)  
    
    @staticmethod
    def keep_largest_white(frame, min_area_fraction=0.05, confirm_fraction=0.75):
        """
        Keeps only the largest valid white region in a binary image.

        A contour is considered valid if its area exceeds the minimum
        fraction of the image area and if it reaches the confirmation
        region near the bottom of the frame.

        Args:
            frame (numpy.ndarray): Binary image.
            min_area_fraction (float, optional): Minimum contour area
                relative to the image size.
            confirm_fraction (float, optional): Vertical position used
                to validate contours.

        Returns:
            numpy.ndarray: Binary image containing only the largest
                valid contour.
        """

        h, w = frame.shape[:2]
        min_area = h * w * min_area_fraction
        confirm_y = int(h * confirm_fraction) 

        contours, _ = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid = []
        for c in contours:
            if cv2.contourArea(c) < min_area:
                continue
            _, y, _, ch = cv2.boundingRect(c)
            if y + ch >= confirm_y: 
                valid.append(c)

        result = np.zeros_like(frame)

        if not valid:
            return result

        largest = max(valid, key=cv2.contourArea)
        cv2.drawContours(result, [largest], -1, 255, thickness=cv2.FILLED)

        return result
    
    @staticmethod
    def detect_element(frame, color_ranges, color, min_area):
        """
        Detects an element of a given color and returns its information.

        Args:
            frame (numpy.ndarray): Image in HSV format.
            color_ranges (dict): Dictionary containing HSV ranges.
            color (str): Color to detect.
            min_area (int): Minimum contour area.

        Returns:
            dict: Dictionary containing:

                - color (str): Detected color.
                - contour (numpy.ndarray): Largest valid contour.
                - mask (numpy.ndarray): Binary mask.
                - area (float): Contour area.
                - x (int): X-coordinate (horizontal) of the top-left corner.
                - y (int): Y-coordinate (vertical) of the top-left corner.
                - w (int): Total width of the bounding box.
                - h (int): Total height of the bounding box.

            Returns None if no valid element is found.
        """

        if color not in color_ranges:
            return None
        
        low, high = color_ranges[color]
        mask = cv2.inRange(frame, np.array(low), np.array(high))

        kernel = np.ones((5, 5), np.uint8)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []

        for contour in contours:

            area = cv2.contourArea(contour)

            if area >= min_area:
                valid_contours.append(contour)

        if len(valid_contours) == 0:
            return None

        best_contour = max(valid_contours, key=cv2.contourArea)
        best_area = cv2.contourArea(best_contour)

        x, y, w, h = cv2.boundingRect(best_contour)

        return {
            "color": color,
            "contour": best_contour,
            "mask": mask,
            "area": best_area,
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }
    
    @staticmethod
    def select_target_pillar(elements):
        """
        Selects the pillar that should be used as the target.

        The method compares the detected red and green pillars to determine
        which one is closer to the camera. If both pillars have similar
        areas, the pillar located lower in the image is selected.

        Args:
            elements (list): List containing the detected pillars.

        Returns:
            dict: Dictionary containing the selected pillar information.

            Returns None if no pillar is detected.
        """

        AREA_THRESHOLD = 0.15 #Maximum relative area difference to use vertical position as a tie breaker

        if len(elements) == 0:
            return None

        if len(elements) == 1:
            return elements[0]

        area1 = elements[0]["area"]
        area2 = elements[1]["area"]

        difference = abs(area1 - area2) / max(area1, area2)

        if difference < AREA_THRESHOLD:
            bottom1 = elements[0]["y"] + elements[0]["h"]
            bottom2 = elements[1]["y"] + elements[1]["h"]

            if bottom1 > bottom2:
                return elements[0]
            else:
                return elements[1]
        else:
            if area1 > area2:
                return elements[0]
            else:
                return elements[1]
            
    @staticmethod
    def select_target_line(elements):
        """
        Selects the line that will be used to determine the robot's
        initial orientation.

        The method compares the detected lines and determines which one
        is closer to the camera. The vertical position is used as the
        main criterion, while the contour area is used to break ties.

        Args:
            elements (list): List containing the detected lines.

        Returns:
            dict: Dictionary containing the selected line information.

            Returns None if no line is detected.
        """

        BOTTOM_THRESHOLD = 0.10 #Maximum relative area difference to use vertical position as a tie breaker

        if len(elements) == 0:
            return None

        if len(elements) == 1:
            return elements[0]

        bottom1 = elements[0]["y"] + elements[0]["h"]
        bottom2 = elements[1]["y"] + elements[1]["h"]

        difference = abs(bottom1 - bottom2) / max(bottom1, bottom2)

        if difference < BOTTOM_THRESHOLD:
            area1 = elements[0]["area"]
            area2 = elements[1]["area"]

            if area1 > area2:
                return elements[0]
            else:
                return elements[1]
        else:
            if bottom1 > bottom2:
                return elements[0]
            else:
                return elements[1]
           
    @staticmethod
    def draw_element(element, frame):
        """
        Draws a bounding box and label around the detected element.

        Args:
            element (dict): Dictionary containing the detected element information.
            frame (numpy.ndarray): Original frame.

        Returns:
            numpy.ndarray: Frame with the element annotation.
        """

        if element is None:
            return frame
        
        x, y, w, h = element["x"], element["y"], element["w"], element["h"]
        color = element["color"]

        match color:
            case "Green":
                bgr = (0, 255, 0)
            case "Red":
                bgr = (0, 0, 255)
            case "Pink":
                bgr = (255, 0, 255)
            case "Blue":
                bgr = (255, 0, 0)
            case "Orange":
                bgr = (0, 165, 255)
            case _:
                bgr = (255, 255, 255)

        cv2.rectangle(frame, (x, y), (x + w, y + h), bgr, 2)
        cv2.putText(frame, color, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
        
        return frame