import cv2 

class Camera:

    def __init__(self, index=0):
        """
        Initializes the camera capture.

        Args:
            index (int, optional): Camera index used by OpenCV.
                Defaults to 0.
        """

        self.cap = cv2.VideoCapture(index)

    def read(self):
        """
        Reads a frame from the camera.

        Returns:
            numpy.ndarray: Captured frame if the operation succeeds.
            None: Returned when no frame could be read.
        """

        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def release(self):
        """
        Releases the camera resource.

        This method should be called when the camera is no longer
        needed to free the device.
        """
        
        self.cap.release()