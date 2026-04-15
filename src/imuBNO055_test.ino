#include <Wire.h>                // I2C communication library
#include <Adafruit_Sensor.h>    // Base sensor structures
#include <Adafruit_BNO055.h>    // BNO055 sensor library
#include <utility/imumaths.h>   // Math utilities for orientation data

// Create BNO055 object with ID 55 and default I2C address (0x28)
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);

void setup(void) 
{
  Serial.begin(115200);   // Initialize serial communication for debugging
  delay(1000);            // Short delay to allow system startup

  // Initialize I2C communication on ESP32
  // SDA = GPIO 21, SCL = GPIO 22 (standard pins)
  Wire.begin(21, 22);

  Serial.println("BNO055 Test - ESP32");
  Serial.println("");

  // Attempt to initialize the sensor
  // If it fails, stop execution here
  if(!bno.begin())
  {
    Serial.println("BNO055 not detected. Check wiring or I2C address.");
    while(1); // Infinite loop to prevent further execution
  }

  delay(1000); // Allow sensor to stabilize

  // Enable external crystal for better accuracy
  bno.setExtCrystalUse(true);

  Serial.println("Sensor initialized successfully!");
}

void loop(void) 
{
  sensors_event_t event;   // Structure to store sensor data
  
  // Get a new orientation reading
  bno.getEvent(&event);

  // Print orientation data in degrees
  // X = Yaw (heading)
  // Y = Pitch (forward/backward tilt)
  // Z = Roll (side tilt)
  Serial.print("X (Yaw): ");
  Serial.print(event.orientation.x, 4);

  Serial.print("\tY (Pitch): ");
  Serial.print(event.orientation.y, 4);

  Serial.print("\tZ (Roll): ");
  Serial.print(event.orientation.z, 4);

  Serial.println(""); 

  delay(100); // Small delay to avoid flooding the serial monitor
}