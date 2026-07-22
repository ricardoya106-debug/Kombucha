#include <Wire.h>
#include "HX711.h"
#include <OneWire.h>
#include <DallasTemperature.h>

#define DOUT 2
#define CLK 3
#define TEMP_PIN 8

HX711 scale;

OneWire oneWire(TEMP_PIN);
DallasTemperature tempsensor(&oneWire);

void setup() {
  Serial.begin(9600);

  // Pressure sensor
  scale.begin(DOUT, CLK);
  scale.set_scale(2280.f);
  scale.tare();

  // Temperature sensor
  tempsensor.begin();

  // Optional: small delay to let everything settle
  delay(500);
}

void loop() {
  if (scale.is_ready()) {
    float pressure = scale.get_units(10) * 100.0;
    float pressure_kPa = pressure / 1000.0;

    // Read temperature
    tempsensor.requestTemperatures();
    float temperature = tempsensor.getTempCByIndex(0);

    // For Serial Plotter: send "Label:value" pairs, separated by comma, one line per time step
    Serial.print("Pressure_kPa:");
    Serial.print(pressure_kPa, 3);

    Serial.print(", Temperature_C:");
    if (temperature == -127.0) {
      // If sensor fails, send a fixed value so plotter doesn't break
      Serial.print(0.0, 2);
    } else {
      Serial.print(temperature, 2);
    }

    Serial.println();  // end of this time step
  }

  // Slow down a bit so plotter is readable
  delay(200);
}