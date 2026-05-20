import cv2

class HSVTrackbars:

    def __init__(self):
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
        for name, maxv in zip(["H", "S", "V"], [179, 255, 255]):
            cv2.setTrackbarPos(f"Low {name}", "Controls", 0)
            cv2.setTrackbarPos(f"High {name}", "Controls", maxv)