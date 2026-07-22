#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 2
#define PH_SENSOR_PIN A1
#define CONDUCTIVITY_SENSOR_PIN A0

#define RED_LED 8
#define YELLOW_LED 9
#define GREEN_LED 10

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

const float PH_VREF = 5.0;
const float PH_SLOPE = 3.5;
const float PH_OFFSET = 0.0;

// Adjust these after calibration of your conductivity probe.
const float COND_OFFSET = 0.0;
const float COND_SCALE = 1.0;

float readPH() {
  const int samples = 10;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(PH_SENSOR_PIN);
    delay(10);
  }
  float adc = sum / (float)samples;
  float voltage = adc * (PH_VREF / 1023.0);
  float pH = 7.0 + ((2.5 - voltage) / PH_SLOPE) + PH_OFFSET;
  return pH;
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

  float conductivity = (voltage * COND_SCALE) + COND_OFFSET;
  return conductivity;
}

void setup() {
  Serial.begin(9600);
  sensors.begin();

  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);

  pinMode(PH_SENSOR_PIN, INPUT);
  pinMode(CONDUCTIVITY_SENSOR_PIN, INPUT);

  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
}

void loop() {
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);

  float pH = readPH();
  float conductivity = readConductivity();

  // Output must match Python serial_reader.F1_FIELDS:
  // ["pH", "conductivity", "temperature_C"]
  Serial.print(pH, 2);
  Serial.print(",");
  Serial.print(conductivity, 2);
  Serial.print(",");
  Serial.println(tempC, 2);

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

  delay(1000);
}