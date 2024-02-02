/*
  RF switch Radiall R591722600
*/

#include "Arduino.h"
#include "Vrekrer_scpi_parser.h"

SCPI_Parser my_instrument;
int pulseLength = 5;
const int min_pin = 2;
const int max_pin = 7;
const int reset_pin = 8;
int open_pins[6] = {0, 0, 0, 0, 0, 0};

void setup() {
  my_instrument.RegisterCommand(F("*IDN?"), &Identify);
  my_instrument.RegisterCommand(F("*RST"), &ResetSwitch);
  my_instrument.RegisterCommand(F("DIGital:PINs?"), &GetDigitalPins);

  my_instrument.SetCommandTreeBase(F("PULse"));
  my_instrument.RegisterCommand(F(":LENgth"), &SetPulseLength);
  my_instrument.RegisterCommand(F(":LENgth?"), &GetPulseLength);

  my_instrument.SetCommandTreeBase(F("SWItch"));
  my_instrument.RegisterCommand(F(":ON"), &SetOpen);
  my_instrument.RegisterCommand(F(":ON?"), &GetOpen);

  for (int i = min_pin; i <= max_pin; i++) {
    pinMode(i, OUTPUT);
  }
  pinMode(reset_pin, OUTPUT);
  Serial.begin(9600);
}

void loop() { my_instrument.ProcessInput(Serial, "\n"); }

void Identify(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.println(F("Radiall, R591722600, A2146600495"));
  //*IDN? Suggested return string should be in the following format:
  // "<vendor>,<model>,<serial number>,<firmware>"
}

void SetPulseLength(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  // For simplicity no bad parameter check is done.
  if (parameters.Size() > 0) {
    pulseLength = constrain(String(parameters[0]).toInt(), 0, 1000);
  }
}

void GetPulseLength(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  interface.println(String(pulseLength));
}

void ResetSwitch(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  sendPulse(reset_pin);
  for (int i = 0; i < 6; i++) {
    open_pins[i] = 0;
  }
}

void SetOpen(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  if (parameters.Size() > 0) {
    int pin = constrain(String(parameters[0]).toInt(), 1, 6);
    if (open_pins[pin - 1] == 0) {
      sendPulse(pin - 1 + min_pin);
      open_pins[pin - 1] = 1;
    }
  }
}

void GetOpen(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  for (int i = 0; i < 6; i++) {
    if (open_pins[i] == 1) {
      interface.println(String(i + 1));
    }
  }
}

void sendPulse(int pin) {
  digitalWrite(pin, HIGH);
  delay(pulseLength);
  digitalWrite(pin, LOW);
}

void GetDigitalPins(SCPI_C commands, SCPI_P parameters, Stream &interface) {
  for (int i = min_pin; i <= max_pin; i++) {
    PrintPinState(i, interface);
  }
  PrintPinState(reset_pin, interface);
}

void PrintPinState(int pin, Stream &interface) {
  interface.print(String(pin));
  interface.print(F("\t"));
  if (digitalRead(pin) == HIGH) {
    interface.println(F("HIGH"));
  } else {
    interface.println(F("LOW"));
  }
}
