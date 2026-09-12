import serial
import time

class ESP32Bridge:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200, timeout=1):
        """Initializes the UART serial connection with the ESP32."""
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connect()

    def connect(self):
        """Establishes connection and flushes serial buffers."""
        try:
            self.ser = serial.Serial(self.port_name, self.baudrate, timeout=self.timeout)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            print(f"[Serial] Connected to ESP32 on {self.port_name}")
        except serial.SerialException as e:
            print(f"[Serial Error] Could not open port {self.port_name}: {e}")
            self.ser = None

    def send_target_heading(self, target_yaw: float, is_corner: bool = False):
        """Sends target heading angle directly to the ESP32 via UART."""
        if self.ser and self.ser.is_open:
            # Formato ultra-simple: solo el valor flotante y salto de línea (ej: "45.5\n")
            message = f"{target_yaw:.1f}\n"
            try:
                self.ser.write(message.encode('utf-8'))
            except serial.SerialException as e:
                print(f"[Serial Error] Failed to send data: {e}")

    def read_current_yaw(self) -> float:
        """Reads real-time Yaw orientation sent by the ESP32."""
        if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    return float(line)
            except (ValueError, UnicodeDecodeError):
                pass
        return None  # Retorna None si no hay lectura válida

    def close(self):
        """Closes the serial port gracefully."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[Serial] Port closed.")