import cv2
import numpy as np

class VisionUtils:

    @staticmethod
    def resize(image, width, height):
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def hsv_mask(frame, low, high):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return cv2.inRange(hsv, np.array(low), np.array(high))
    
    @staticmethod
    def replace_color(frame, color_ranges, colors_to_white,):
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
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    @staticmethod
    def blur(frame):
        return cv2.bilateralFilter(frame, 8, 60, 60)
    
    @staticmethod
    def binary(frame, treshold = 100):
        _, binary = cv2.threshold(frame, treshold, 255, cv2.THRESH_BINARY)
        return binary
    
    @staticmethod
    def clean_binary(frame):
        kernel = np.ones((5, 5), np.uint8)
        return cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel)  
    
    @staticmethod
    def keep_largest_white(frame, min_area_fraction=0.05, confirm_fraction=0.75):
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