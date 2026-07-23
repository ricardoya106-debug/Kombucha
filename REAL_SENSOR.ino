#include "HX711.h"
#include <OneWire.h>
#include <DallasTemperature.h>

// --- PIN DEFINITIONS ---
// NOTE: Moved ONE_WIRE_BUS from 2 to 4 to avoid conflict with HX711 SCK_PIN
#define ONE_WIRE_BUS 4 
const int DOUT_PIN = 3;  
const int SCK_PIN = 2;   

#define PH_SENSOR_PIN A1
#define CONDUCTIVITY_SENSOR_PIN A0

#define RED_LED 8
#define YELLOW_LED 9
#define GREEN_LED 10

// --- SENSOR OBJECTS ---
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
HX711 scale;

// --- CONSTANTS & CALIBRATION ---
const float CALIBRATION_FACTOR = 53687.0; 
const float PH_VREF = 5.0;
const float PH_SLOPE = 3.5;
const float PH_OFFSET = 0.0;
const float COND_OFFSET = 0.0;
const float COND_SCALE = 1.0;

// --- HELPER FUNCTIONS ---
float readPH() {
  const int samples = 10;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(PH_SENSOR_PIN);
    delay(10);
  }
  float adc = sum / (float)samples;
  float voltage = adc * (PH_VREF / 1023.0);
  return 7.0 + ((2.5 - voltage) / PH_SLOPE) + PH_OFFSET;
}

float readConductivity() {
  const int samples = 10;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(CONDUCTIVITY_SENSOR_PIN);
    delay(10);
  }
  float adc = sum / (float)samples;
  float voltage = adc * (PH_VREF / 1023.0);
  return (voltage * COND_SCALE) + COND_OFFSET;
}

void setup() {
  Serial.begin(9600);
  
  // Initialize Sensors
  sensors.begin();
  scale.begin(DOUT_PIN, SCK_PIN);
  
  // LED Setup
  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);

  // Analog Pins
  pinMode(PH_SENSOR_PIN, INPUT);
  pinMode(CONDUCTIVITY_SENSOR_PIN, INPUT);

  // Tare the pressure sensor silently
  // A 2-second delay here is safe because it only runs once at startup
  delay(2000); 
  if (scale.is_ready()) {
    scale.tare(); 
    scale.set_scale(CALIBRATION_FACTOR); 
  }
}

void loop() {
  // 1. Read Temperature
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);

  // 2. Read pH & Conductivity
  float pH = readPH();
  float conductivity = readConductivity();

  // 3. Read Pressure
  float pressure_bar = 0.0;
  if (scale.is_ready()) {
    // Grab 1 sample instead of 5 so we don't block the loop
    float pressure_kPa = scale.get_units(1); 
    pressure_bar = pressure_kPa * 0.01; 
  }

  // 4. Output Clean CSV
  // Formatting strictly as: pH, conductivity, temperature_C, pressure_bar
  Serial.print(pH, 2);
  Serial.print(",");
  Serial.print(conductivity, 2);
  Serial.print(",");
  Serial.print(tempC, 2);
  Serial.print(",");
  Serial.println(pressure_bar, 5);

  // 5. LED Status Logic
  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);

  if (tempC > 29.0) {
    digitalWrite(RED_LED, HIGH);
  } else if (tempC < 25.0) {
    digitalWrite(YELLOW_LED, HIGH);
  } else {
    digitalWrite(GREEN_LED, HIGH);
  }

  // Loop delay (1 second is standard)
  delay(1000);
}