#include "HX711.h"

const int DOUT_PIN = 3; 
const int SCK_PIN = 2;  

// Main calibration factor for the 40KPa sensor
const float CALIBRATION_FACTOR = 53687.0; 

HX711 scale;

void setup() {
  Serial.begin(9600);
  scale.begin(DOUT_PIN, SCK_PIN);
  
  Serial.println("==============================================");
  Serial.println("IMPORTANT: Let sensor warm up 2 mins, keep open!");
  Serial.println("Zeroing atmospheric pressure baseline...");
  Serial.println("==============================================");
  delay(3000); 
  
  scale.tare(); 
  scale.set_scale(CALIBRATION_FACTOR); 
  
  Serial.println("Setup Complete. Measuring pressure in BAR...");
}

void loop() {
  if (scale.is_ready()) {
    // 1. Get raw calibrated value (which is in kPa)
    float pressure_kPa = scale.get_units(5); 
    
    // 2. Convert kPa to bar (1 kPa = 0.01 bar)
    float pressure_bar = pressure_kPa * 0.01; 
    
    Serial.print("Pressure: ");
    // Prints with 5 decimal places so you can see fine changes in bar units
    Serial.print(pressure_bar, 5); 
    Serial.println(" bar");
    
  } else {
    Serial.println("HX711 not detected.");
  }
  delay(500); 
}
