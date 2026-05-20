import cv2

from camera.camera import Camera
from processing.transform_image import VisionUtils
from calibration.trackbars import HSVTrackbars
from config.color_ranges import ColorRangeManager
from calibration.calibration_panel import CalibrationPanel

class ColorCalibrator:

    def __init__(self):

        self.camera = Camera()

        self.trackbar = HSVTrackbars()

        self.manager = ColorRangeManager()

        self.current_selected_color = None

        self.ui = CalibrationPanel()

        cv2.namedWindow("Controls")
        cv2.setMouseCallback("Controls", ColorCalibrator.mouse, (self.ui, self))

    def run(self):

        while True:

            frame = self.camera.read()

            if frame is None:
                break

            low, high = self.trackbar.get_values()

            if self.current_selected_color:
                self.manager.color_ranges[self.current_selected_color] = [low, high]

            mask = VisionUtils.hsv_mask(frame, low, high)

            resized = VisionUtils.resize(mask, 700, 350)

            cv2.imshow("Mask", resized)
            cv2.imshow("Controls", self.ui.get_image())

            if cv2.waitKey(1) == 27:
                break

        self.camera.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.camera.release()
        cv2.destroyAllWindows()
        exit()

    @staticmethod
    def mouse(event, x, y, flags, param):

        if event == cv2.EVENT_LBUTTONDOWN:

            panel, calibrator = param

            clicked = panel.get_clicked_button(x, y)

            if clicked:
                calibrator.handle_button(clicked)

    def handle_button(self, name):

        if name in self.manager.color_ranges:

            self.current_selected_color = name
            low, high = self.manager.color_ranges[name]
            for i, (hsvname, val_low, val_high) in enumerate(zip(["H","S","V"], low, high)):
                cv2.setTrackbarPos(f"Low {hsvname}", "Controls", val_low)
                cv2.setTrackbarPos(f"High {hsvname}", "Controls", val_high)

        elif name == "Reset":

            self.reset_trackbars()

        elif name == "Save & Quit":
            if self.current_selected_color:
                low, high = self.trackbar.get_values()
                self.manager.color_ranges[self.current_selected_color] = [low, high]
            
            self.manager.save_ranges()
            self.stop()