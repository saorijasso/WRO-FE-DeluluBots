import os
import time

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
    def draw_hud (frame, lap_tracker=None, nav_manager=None, mode_str="", extra_lines = None):
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
        total_laps = lap_tracker.TOTAL_LAPS if lap_tracker else 3

        if lap_tracker:
            # current_lap cuenta vueltas COMPLETADAS; mostramos la que va en curso.
            if lap_tracker.finished:
                current_lap = total_laps
            else:
                current_lap = min(lap_tracker.current_lap + 1, total_laps)
        else:
            current_lap = 1

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

        if mode_str:
            cv2.putText(frame, f"Modo: {mode_str}", (31, frame.shape[0] - 19), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, f"Modo: {mode_str}", (30, frame.shape[0] - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        if extra_lines:
            y = 130
            for text in extra_lines:
                cv2.putText(frame, text, (31, y + 1), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(frame, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 2, cv2.LINE_AA)
                y += 24

        return frame

class VideoWriterLogger:
    """Clase sencilla para guardar los frames en un archivo .avi"""

    def __init__(
        self,
        output_dir="logs_video",
        fps=20.0,
        frame_size=(700, 350),
        enabled=True,
    ):
        self.frame_size = frame_size
        self.enabled = enabled
        self.writer = None
        if self.enabled:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(
                output_dir, f"run_{time.strftime('%Y%m%d_%H%M%S')}.avi"
            )
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self.writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
            print(f"[VideoLogger] Grabando video en: {filename}")

    def write(self, frame):
        if frame is None or self.writer is None:
            return

        # 1. Si la imagen viene en escala de grises (2D), convertir a BGR (3D)
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        # 2. Redimensionar usando self.frame_size directamente
        target_w, target_h = self.frame_size
        if (frame.shape[1], frame.shape[0]) != (target_w, target_h):
            frame = cv2.resize(frame, (target_w, target_h))

        self.writer.write(frame)

    def release(self):
        if self.writer:
            self.writer.release()
            print("[VideoLogger] Grabación finalizada y guardada.")