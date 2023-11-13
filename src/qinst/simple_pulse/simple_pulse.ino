int pulseLenght = 5;

void setup() {
  for (int i=2; i<8; i++){
    pinMode(i, OUTPUT);
  }
  Serial.begin(9600);
  Serial.println("hello");
}

void loop() {
  if (Serial.available()>0){
    int selectedPin = Serial.parseInt();
    Serial.print("selected pin ");
    Serial.println(selectedPin);
    if (selectedPin>=2 &&selectedPin<8){
      sendPulse(selectedPin);
    }
    else if (selectedPin == 8){
      sendPulse(selectedPin);
      Serial.println("Reset");
    }
    else{
      Serial.println("pin not available");
    }
  }
}

void sendPulse(int pin){
  digitalWrite(pin, HIGH);
  delay(pulseLenght);
  digitalWrite(pin, LOW);
}
