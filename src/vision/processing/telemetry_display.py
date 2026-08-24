import cv2 

class TelemetryDisplay: 

    @staticmethod
    def draw_element(element, frame):
            """
            Draws a bounding box and label around the detected element.
    
            Args:
                element (dict): Dictionary containing the detected element information.
                frame (numpy.ndarray): Original frame.
    
            Returns:
                numpy.ndarray: Frame with the element annotation.
            """
    
            if element is None:
                return frame
            
            x, y, w, h = element["x"], element["y"], element["w"], element["h"]
            color = element["color"]
    
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
                case _:
                    bgr = (255, 255, 255)
    
            cv2.rectangle(frame, (x, y), (x + w, y + h), bgr, 2)
            cv2.putText(frame, color, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
            
            return frame

    @staticmethod
    def draw_hud (frame, lap_tracker=None, nav_manager=None):
        """
        Draws the lap count (Lap 1, Lap 2, Lap 3) and the navigation direction
        onto the camera frame
            
        Args:
            frame (numpy.ndarray): Original frame.
            lap_tracker (LapTracker, optional): Instance tracking the laps.
            nav_magnager (NavigationManager, optional): Instance managing the direction
            
        Returns:
            numpy.ndarray: Frame with the telemetry HUD rendered.
        """
        current_lap = lap_tracker.current_lap if lap_tracker else 1
        total_laps = lap_tracker.TOTAL_LAPS if lap_tracker else 3
        lap_text = f"Lap: {current_lap} / {total_laps}"

        if lap_tracker:
            total_corners = lap_tracker.corners
            corners_in_lap = total_corners % lap_tracker.CORNERS_PER_LAP
            if corners_in_lap == 0 and total_corners > 0:
                corners_display = lap_tracker.CORNERS_PER_LAP
            else:
                corners_display = corners_in_lap
        else:
            corners_display = 0
            
        corners_text = f"Corners: {corners_display} / 4"

        if nav_manager and nav_manager.direction:
            dir_text = nav_manager.direction.value
        else: 
            dir_text = "Pending..."
        dir_text_label = f"Dir: {dir_text}"

        cv2.putText(frame, lap_text, (31, 41), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, lap_text, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, corners_text, (31, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, corners_text, (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, dir_text_label, (31, 101), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, dir_text_label, (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

        return frame
    