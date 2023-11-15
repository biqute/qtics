/*
RF attenuator 3494-6
BASIC USAGE: send the required attenuation in dB
CONNECTIONS: 11 PINS
AVAILABLE RANGE: 0 to -64 dB
 */

#include "Arduino.h"
#include "Vrekrer_scpi_parser.h"

SCPI_Parser my_instrument;

const float map_db[11] = {0.03, 0.06, 0.13, 0.25, 0.5, 1.0,
                          2.0,  4.0,  8.0,  16.0, 32.0};

const int min_pin = 3;
const int max_pin = 13;
float attenuation = 0.;

void setup() {
  my_instrument.RegisterCommand(F("*IDN?"), &Identify);
  my_instrument.RegisterCommand(F("ATTenuation"), &SetAttenuation);
  my_instrument.RegisterCommand(F("ATTenuation?"), &GetAttenuation);

  for (int i = min_pin; i <= max_pin; i++) {
    pinMode(i, OUTPUT);
  }
  Serial.begin(9600);
}

void loop() { my_instrument.ProcessInput(Serial, "\n"); }

int *find_bitstring(float val) {
  // convert float decimal to binary considering the pin mapping
  static int bitstring[11];

  for (int i = 10; i >= 0; i--) {
    int bit_i;
    if (map_db[i] > val)
      bit_i = 0;
    else {
      val = val - map_db[i];
      bit_i = 1;
    }
    bitstring[i] = bit_i;
  }
  return bitstring;
}

void Identify(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.println(F("KRATOS General Microwave, RF attenuator, 3494-64"));
  //*IDN? Suggested return string should be in the following format:
  // "<vendor>,<model>,<serial number>,<firmware>"
}

void SetAttenuation(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  if (parameters.Size() > 0) {
    float att = constrain(String(parameters[0]).toFloat(), 0, 64);
    int *binaryNum = find_bitstring(att);
    for (int i = 0; i < 11; i++) {
      if (binaryNum[i] == 1) {
        digitalWrite(i + min_pin, HIGH);
      } else {
        digitalWrite(i + min_pin, LOW);
      }
    }
    attenuation = att;
  }
}

void GetAttenuation(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.print(String(attenuation));
  interface.println(F(" dB"));
}
