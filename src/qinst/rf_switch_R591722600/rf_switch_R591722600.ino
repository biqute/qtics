/*
RF switch Radiall R591722600
*/

#include "Arduino.h"
#include "Vrekrer_scpi_parser.h"

SCPI_Parser my_instrument;
int pulseLenght = 5;
const int min_pin = 2;
const int max_pin = 7;
const int reset_pin = 8;
int open_pins[6] = {0, 0, 0, 0, 0, 0};

void setup() {
  my_instrument.RegisterCommand(F("*IDN?"), &Identify);

  my_instrument.SetCommandTreeBase(F("PULse"));
  my_instrument.RegisterCommand(F(":LENght"), &SetPulseLenght);
  my_instrument.RegisterCommand(F(":LENght?"), &GetPulseLenght);

  my_instrument.SetCommandTreeBase(F("SWItch"));
  my_instrument.RegisterCommand(F(":RESet"), &ResetSwitch);
  my_instrument.RegisterCommand(F(":ON"), &SetOpen);
  my_instrument.RegisterCommand(F(":ON?"), &GetOpen);

  for (int i = min_pin; i < max_pin; i++) {
    pinMode(i, OUTPUT);
  }
  pinMode(reset_pin, OUTPUT);
  Serial.begin(9600);
}

void loop() { my_instrument.ProcessInput(Serial, "\n"); }

void Identify(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.println(F("Radiall, RF Switch, R591722600"));
  //*IDN? Suggested return string should be in the following format:
  // "<vendor>,<model>,<serial number>,<firmware>"
}

void SetPulseLenght(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  // For simplicity no bad parameter check is done.
  if (parameters.Size() > 0) {
    pulseLenght = constrain(String(parameters[0]).toInt(), 0, 1000);
  }
}

void GetPulseLenght(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.println(String(pulseLenght));
}

void ResetSwitch(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  sendPulse(reset_pin);
  for (int i = 0; i < 6; i++) {
    open_pins[i] = 0;
  }
}

void SetOpen(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  if (parameters.Size() > 0) {
    int pin = constrain(String(parameters[0]).toInt(), min_pin, max_pin);
    if (open_pins[pin - min_pin] == 0) {
      sendPulse(pin);
      open_pins[pin - min_pin] = 1;
    }
  }
}

void GetOpen(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  for (int i = 0; i < 6; i++) {
    if (open_pins[i] == 1) {
      interface.println(String(i + min_pin));
    }
  }
}

void sendPulse(int pin) {
  digitalWrite(pin, HIGH);
  delay(pulseLenght);
  digitalWrite(pin, LOW);
}
