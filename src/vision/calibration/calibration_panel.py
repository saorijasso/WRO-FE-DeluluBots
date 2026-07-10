import cv2
import numpy as np

class CalibrationPanel:

    def __init__(self):
        """
        Initializes the calibration panel.

        Defines the background color, button colors, dimensions and
        spacing of the interface elements. It also computes the button
        positions and generates the panel image.
        """

        self.bg_color = (240, 240, 240)

        self.button_colors = {
            "Red": (180, 180, 255),
            "Green": (180, 255, 180),
            "Blue": (255, 200, 150),
            "Orange": (180, 220, 255),
            "Pink": (230, 200, 255),
            "White": (255, 255, 255),
            "Reset": (198, 162, 200),
            "Save & Quit": (198, 162, 200)
        }

        self.button_w = 200
        self.button_h = 60
        self.gap_x = 40
        self.gap_y = 20
        self.start_x = 40
        self.start_y = 40

        self.order = ["Red","Green","Blue","Orange","Pink","White"]

        self.positions = self._compute_positions()

        self.panel_img = self._draw_panel()

    def _compute_positions(self):
        """
        Computes the position of each button in the panel.

        The color buttons are arranged in two columns, while the
        control buttons are placed at the bottom.

        Returns:
            dict: Dictionary that maps each button name to its
                corresponding (x, y) position.
        """

        positions = {}

        for i, name in enumerate(self.order):

            col = i % 2
            row = i // 2

            x = self.start_x + col * (self.button_w + self.gap_x)
            y = self.start_y + row * (self.button_h + self.gap_y)

            positions[name] = (x, y)

        bottom_y = self.start_y + 3 * (self.button_h + self.gap_y) + 10

        #Add the control buttons below the color buttons
        positions["Reset"] = (self.start_x, bottom_y)

        positions["Save & Quit"] = (
            self.start_x + self.button_w + self.gap_x,
            bottom_y
        )

        return positions
    
    def _round_button(self, img, x, y, w, h, color):
        """
        Draws a rounded rectangle button.

        The button is built using rectangles and circles to simulate
        rounded corners.

        Args:
            img (numpy.ndarray): Image where the button will be drawn.
            x (int): Left position of the button.
            y (int): Top position of the button.
            w (int): Button width.
            h (int): Button height.
            color (tuple): Button color in BGR format.
        """

        radius = 15

        cv2.rectangle(img, (x+radius, y), (x+w-radius, y+h), color, -1)
        cv2.rectangle(img, (x, y+radius), (x+w, y+h-radius), color, -1)

        cv2.circle(img, (x+radius, y+radius), radius, color, -1)
        cv2.circle(img, (x+w-radius, y+radius), radius, color, -1)
        cv2.circle(img, (x+radius, y+h-radius), radius, color, -1)
        cv2.circle(img, (x+w-radius, y+h-radius), radius, color, -1)

    def _draw_panel(self):
        """
        Draws the complete calibration panel.

        Creates the background image, draws all buttons and centers
        their labels.

        Returns:
            numpy.ndarray: Generated panel image.
        """

        img = np.full((420, 520, 3), self.bg_color, dtype=np.uint8)

        for text, (x, y) in self.positions.items():

            color = self.button_colors.get(text, (200, 235, 200))

            self._round_button(
                img,
                x, y,
                self.button_w,
                self.button_h,
                color
            )

            (tw, th), _ = cv2.getTextSize(
                text,
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                1
            )

            tx = x + (self.button_w - tw) // 2
            ty = y + (self.button_h + th) // 2

            cv2.putText(
                img,
                text,
                (tx, ty),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (60, 60, 60),
                1
            )

        return img
    
    def get_clicked_button(self, x, y):
        """
        Determines which button was clicked.

        Args:
            x (int): Horizontal mouse position.
            y (int): Vertical mouse position.

        Returns:
            str: Name of the clicked button, or None if no button
                was selected.
        """

        for name, (bx, by) in self.positions.items():

            if (
                bx <= x <= bx + self.button_w and
                by <= y <= by + self.button_h
            ):
                return name

        return None
    
    def get_image(self):
        """
        Returns the calibration panel image.

        Returns:
            numpy.ndarray: Calibration panel.
        """

        return self.panel_img