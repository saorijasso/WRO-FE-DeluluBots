import cv2

from camera.camera import Camera
from processing.transform_image import VisionUtils
from calibration.trackbars import HSVTrackbars
from config.color_ranges import ColorRangeManager
from calibration.calibration_panel import CalibrationPanel

class ColorCalibrator:

    def __init__(self):
        """
        Initializes all components required for the color calibration tool.

        Creates the camera stream, the HSV trackbars, the color manager
        and the calibration panel. It also configures the mouse callback
        used to interact with the interface.
        """

        self.camera = Camera()

        self.trackbar = HSVTrackbars()

        self.manager = ColorRangeManager()

        self.current_selected_color = None

        self.ui = CalibrationPanel()

        cv2.namedWindow("Controls")
        cv2.setMouseCallback("Controls", ColorCalibrator.mouse, (self.ui, self))

    def run(self):
        """
        Starts the calibration loop.

        Continuously reads frames from the camera, updates the HSV mask
        using the current trackbar values and displays the calibration
        interface.

        The selected color range is updated in real time.

        Press ESC to exit.
        """

        while True:

            frame = self.camera.read()

            if frame is None:
                break

            low, high = self.trackbar.get_values()

            if self.current_selected_color:
                self.manager.color_ranges[self.current_selected_color] = [low, high]

            mask = VisionUtils.hsv_binary_mask(frame, low, high)

            resized = VisionUtils.resize(mask, 700, 350)

            cv2.imshow("Mask", resized)
            cv2.imshow("Controls", self.ui.get_image())

            if cv2.waitKey(1) == 27:
                break

        self.camera.release()
        cv2.destroyAllWindows()

    def stop(self):
        """
        Releases all resources and closes the application.

        Stops the camera stream, destroys all OpenCV windows
        and exits the program.
        """

        self.camera.release()
        cv2.destroyAllWindows()
        exit()

    @staticmethod
    def mouse(event, x, y, flags, param):
        """
        Handles mouse events on the calibration panel.

        Detects clicks on the interface buttons and delegates
        the corresponding action to the calibrator.

        Args:
            event (int): OpenCV mouse event.
            x (int): Horizontal cursor position.
            y (int): Vertical cursor position.
            flags (int): Additional event flags.
            param (tuple): Tuple containing the calibration panel
                and the calibrator instance.
        """

        if event == cv2.EVENT_LBUTTONDOWN:

            panel, calibrator = param

            clicked = panel.get_clicked_button(x, y)

            if clicked:
                #Execute the action associated with the clicked button
                calibrator.handle_button(clicked)

    def handle_button(self, name):
        """
        Processes the action associated with the clicked button.

        Depending on the selected button, the method can:

        - Load the HSV values of a color.
        - Reset the trackbars.
        - Save the current calibration and exit.

        Args:
            name (str): Name of the clicked button.
        """

        if name in self.manager.color_ranges:

            #Load the saved HSV values into the trackbars
            self.current_selected_color = name
            low, high = self.manager.color_ranges[name]
            for i, (hsvname, val_low, val_high) in enumerate(zip(["H","S","V"], low, high)):
                cv2.setTrackbarPos(f"Low {hsvname}", "Controls", val_low)
                cv2.setTrackbarPos(f"High {hsvname}", "Controls", val_high)

        elif name == "Reset":

            self.reset_trackbars()

        elif name == "Save & Quit":
            #Save the current values before closing the application
            if self.current_selected_color:
                #Update the HSV range of the selected color
                low, high = self.trackbar.get_values()
                self.manager.color_ranges[self.current_selected_color] = [low, high]
            
            self.manager.save_ranges()
            self.stop()