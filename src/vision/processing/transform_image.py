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