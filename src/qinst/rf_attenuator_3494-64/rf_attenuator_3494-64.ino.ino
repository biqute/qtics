
/* CONNECTIONS 11 PINS
 *
 */

void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  for (int i=13; i >= 3; i--){
    pinMode(i, OUTPUT);
  }
  Serial.begin(9600);
}

float read_attenuation(float val){
  if (val > 64) val = 64;
  if (val < 0) val = 0;
  return val;
}

const float map_db[11] = {0.03, 0.06, 0.13, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0};

int * find_bitstring(float val){

  static int bitstring[11];

  for (int i = 10; i >= 0; i-- ){
    int bit_i;
    if (map_db[i] > val)
      bit_i = 0;
    else{
      val = val - map_db[i];
      bit_i = 1;
    }
    bitstring[i] = bit_i;
  }

  return bitstring;

}


void loop() {

  if (Serial.available()) {

    float attenuation = read_attenuation(Serial.parseFloat());

    int *binaryNum = find_bitstring (attenuation);

    for (int i = 0; i < 11; i++){
      if (binaryNum[i] == 1){
        digitalWrite(i+3, HIGH);
        Serial.println((String)"LED " + (i+3) + " HIGH " + map_db[i]);
      }
      else{
        digitalWrite(i+3, LOW);
        Serial.println((String)"LED " + (i+3) + " LOW " + map_db[i]);
      }

    }
  Serial.println("\n\n");

  delay(10);
  }

}
