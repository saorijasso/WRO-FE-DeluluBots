import cv2

class HSVTrackbars:

    def __init__(self):
        """
        Creates the HSV trackbars.

        For each HSV channel, a lower and upper limit slider is created
        inside the Controls window.
        """

        cv2.namedWindow('Controls')
        for name, maxv in zip(["H","S","V"], [179,255,255]):
            cv2.createTrackbar(
                f"Low {name}",
                "Controls",
                0,
                maxv,
                lambda x: None
            )

            cv2.createTrackbar(
                f"High {name}",
                "Controls",
                maxv,
                maxv,
                lambda x: None
            )

    def get_values(self):
        """
        Retrieves the current HSV values from the trackbars.

        Returns:
            tuple:
                - tuple: Lower HSV limits.
                - tuple: Upper HSV limits.
        """

        low = (
            cv2.getTrackbarPos("Low H","Controls"),
            cv2.getTrackbarPos("Low S","Controls"),
            cv2.getTrackbarPos("Low V","Controls")
        )

        high = (
            cv2.getTrackbarPos("High H","Controls"),
            cv2.getTrackbarPos("High S","Controls"),
            cv2.getTrackbarPos("High V","Controls")
        )

        return low, high

    def reset_trackbars(self):
        """
        Restores the trackbars to their default values.

        The lower limits are set to zero, while the upper limits
        are reset to their maximum values.
        """

        for name, maxv in zip(["H", "S", "V"], [179, 255, 255]):
            #Create the lower and upper sliders for each HSV channel
            cv2.setTrackbarPos(f"Low {name}", "Controls", 0)
            cv2.setTrackbarPos(f"High {name}", "Controls", maxv)