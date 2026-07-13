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
    def color_mask(frame, color_ranges, color):
        """
        Creates a mask for a specific color.

        Args:
            frame (numpy.ndarray): Image in HSV format.
            color_ranges (dict): Dictionary containing HSV ranges.
            color (str): Color to detect.

        Returns:
            numpy.ndarray: Binary mask of the selected color, or None
                if the color is not found.
        """

        if color not in color_ranges:
            return None
        
        low, high = color_ranges[color]
        return cv2.inRange(frame, np.array(low), np.array(high))
    
    @staticmethod
    def find_closest_pillar(frame, color_ranges):
        """
        Detects the closest pillar between the red and green pillars.

        The method filters both colors, removes noise and compares the
        contour areas to determine which pillar is closest to the camera.

        Args:
            frame (numpy.ndarray): Original frame in BGR format.
            color_ranges (dict): Dictionary containing HSV color ranges.

        Returns:
            tuple: A tuple containing:

                - str: Detected pillar color ("Red" or "Green").
                - numpy.ndarray: Largest contour found.
                - numpy.ndarray: Binary mask of the detected pillar.

            Returns (None, None, None) if no pillar is detected.
        """

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red_mask = VisionUtils.color_mask(hsv, color_ranges, "Red")
        green_mask = VisionUtils.color_mask(hsv, color_ranges, "Green")

        kernel = np.ones((5, 5), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.bitwise_or(green_mask, red_mask)

        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        MIN_PILLAR_AREA = 500 #Modify depending on your camera's image size

        green_contours = [c for c in green_contours if cv2.contourArea(c) >= MIN_PILLAR_AREA]
        red_contours = [c for c in red_contours if cv2.contourArea(c) >= MIN_PILLAR_AREA]

        best_green = max(green_contours, key=cv2.contourArea) if green_contours else None
        best_red = max(red_contours, key=cv2.contourArea) if red_contours else None

        green_area = cv2.contourArea(best_green) if best_green is not None else 0
        red_area = cv2.contourArea(best_red) if best_red is not None else 0

        if green_area == 0 and red_area == 0:
            return None, None, None 

        if green_area > red_area:
            return "Green", best_green, green_mask
        else:
            return "Red", best_red, red_mask
           
    @staticmethod
    def draw_element(frame, contour, color):
        """
        Draws a bounding box and label around the detected element.

        Args:
            frame (numpy.ndarray): Original frame.
            contour (numpy.ndarray): Element contour.
            color (str): Element color ("Red" or "Green").

        Returns:
            numpy.ndarray: Frame with the element annotation.
        """

        if contour is None:
            return frame
        
        x, y, w, h = cv2.boundingRect(contour)
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
        cv2.rectangle(frame, (x, y), (x + w, y + h), bgr, 2)
        cv2.putText(frame, color, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
        
        return frame