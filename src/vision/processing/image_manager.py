import cv2

from camera.camera import Camera
from config import saved_ranges
from processing.transform_image import VisionUtils


class ImageManager:

    def __init__(self):

        self.camera = Camera()
        cv2.namedWindow("Walls")

    def run_from_image(self, path):
        frame = cv2.imread(path)
        
        if frame is None:
            print(f"Could not open image: {path}")
            return
        
        mask = VisionUtils.replace_color(frame, saved_ranges.color_ranges ,["Red", "Green", "Blue", "Orange"])
        mask = VisionUtils.resize(mask, 700, 350)
        mask = VisionUtils.grayscale(mask)
        mask = VisionUtils.blur(mask)
        mask = VisionUtils.binary(mask)
        mask = VisionUtils.clean_binary(mask)
        mask = VisionUtils.keep_largest_white(mask)

        cv2.imshow("Walls", mask)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def run(self):
        
        while True:
            frame = self.camera.read();

            if frame is None:
                break
            
            mask = VisionUtils.replace_color(frame, saved_ranges.color_ranges ,["Red", "Green", "Blue", "Orange"])
            #mask = VisionUtils.resize(mask, 700, 350)
            mask = VisionUtils.grayscale(mask)
            mask = VisionUtils.blur(mask)
            mask = VisionUtils.binary(mask)
            mask = VisionUtils.clean_binary(mask)
            mask = VisionUtils.keep_largest_white(mask)
            cv2.imshow("Walls", mask)

            if cv2.waitKey(1) == 27:
                break

        self.camera.release()
        cv2.destroyAllWindows()