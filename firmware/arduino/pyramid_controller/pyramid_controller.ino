/*
 * This Arduino code combines two functionalities: emergency button detection and motor control with RFID and flame sensor integration.
 * 
 * Functionality Overview:
 * 1. Emergency Button Detection: 
 *    - Monitors two buttons (connected to pins 6 and 7).
 *    - If either button is pressed, an "EMERGENCY" message is sent via Serial communication to raspberry pi .
 * 
 * 2. Motor Control:
 *    - Controls a stepper motor using two pins (DIR_PIN for direction and STEP_PIN for step control).
 *    - Motor speed, direction, and steps can be controlled via Serial commands to raspberry pi.
 * 
 * 3. RFID Reader:
 *    - Uses an MFRC522 RFID reader (connected to SPI pins 5 and 4) to detect RFID tags.
 *    - Reads and prints the RFID tag ID to Serial when a new card is detected via Serial commands to raspberry pi .
 * 
 * 4. Flame Sensor:
 *    - Monitors a flame sensor connected to pin 2.
 *    - If the flame sensor detects a fire (above a threshold), it sends a "FIRE" message via Serial communication to raspberry pi.
 * 
 * Necessary Libraries:
 * - SPI.h: Enables communication with SPI devices (used for the RFID reader).
 * - MFRC522.h: Library for interfacing with the MFRC522 RFID reader module.
 * 
 * Note: Ensure that you install the necessary libraries via the Arduino IDE's Library Manager.
 *       Search for "MFRC522" and install the "MFRC522" library by GithubCommunity.
 *       The "SPI" library comes pre-installed with the Arduino IDE.
 */

// Include necessary libraries
#include <SPI.h>
#include <MFRC522.h>

// Button Pins
#define BUTTON_PIN_1 6
#define BUTTON_PIN_2 7

// Motor Control Pins
#define DIR_PIN 9
#define STEP_PIN 8

// Flame Sensor Pin
int flameSensorPin = 2;  // Flame sensor connected to pin 2
int flameThreshold = 300; // based on the sensor's sensitivity

// RFID Reader Pins
#define SS_PIN 5
#define RST_PIN 4
MFRC522 mfrc522(SS_PIN, RST_PIN); 

// Motor Control Variables
float RPM = 0;  // Revolutions per minute
float RPS;  // Revolutions per second
float SPS;  // Steps per second
float rolls;  // Number of rolls
long steps;  // Number of steps to move
unsigned long stepDelay;  // Delay between steps in microseconds

bool direction = true;  // true for forward, false for backward
bool running = false;  // Motor running state

void setup() {
  // Initialize Button Pins
  pinMode(BUTTON_PIN_1, INPUT);
  pinMode(BUTTON_PIN_2, INPUT);

  // Motor Control Setup
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);  // Enable the motor driver

  // Flame Sensor Setup
  pinMode(flameSensorPin, INPUT);

  // RFID Setup
  SPI.begin();
  mfrc522.PCD_Init();

  // Serial Communication Setup
  Serial.begin(9600);
}

void loop() {
  // Handle Button Press
  if (digitalRead(BUTTON_PIN_1) == HIGH || digitalRead(BUTTON_PIN_2) == HIGH) {
    Serial.println("EMERGENCY");
    delay(1000); // Debounce delay to prevent multiple messages
  }

  // Motor Control Loop
  if (running) {
    for (long i = 0; i < steps; i++) {
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(stepDelay);
      digitalWrite(STEP_PIN, LOW);
      delayMicroseconds(stepDelay);

      if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');
        processMotorCommand(input);
        if (!running) break;
      }
    }
    running = false;
  }

  // Flame Sensor Loop
  int sensorValue = analogRead(flameSensorPin);  // Use analogRead for flame sensor if using a sensor with analog output
  if (sensorValue >= flameThreshold) {
    Serial.println("FIRE");
  }

  // RFID Reader Loop
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String rfidTag = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfidTag += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      rfidTag += String(mfrc522.uid.uidByte[i], HEX);
    }
    rfidTag.toUpperCase();
    rfidTag.trim();

    Serial.println(rfidTag);
  }

  // Handle Serial Input for Motor and RFID
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("R ") || input.startsWith("D ") || input.startsWith("S ") || input.equalsIgnoreCase("START") || input.equalsIgnoreCase("STOP")) {
      processMotorCommand(input);
    } else if (input == "check-in" || input == "check-out") {
      processRFIDCommand(input);
    }
  }

  delay(100); // General delay to avoid spamming serial communication
}

void processMotorCommand(String input) {
  if (input.startsWith("R ")) {
    RPM = input.substring(2).toFloat();
    RPS = RPM / 60.0;
    SPS = RPS * 6400.0;  // Assuming 6400 steps per revolution for 1/32 microstepping
    stepDelay = 1000000.0 / (SPS * 2.0);
  } else if (input.startsWith("D ")) {
    int dir = input.substring(2).toInt();
    direction = (dir == 1);
    digitalWrite(DIR_PIN, direction);
  } else if (input.startsWith("S ")) {
    rolls = input.substring(2).toFloat();
    steps = rolls * 6400.0;
  } else if (input.equalsIgnoreCase("START")) {
    running = true;
  } else if (input.equalsIgnoreCase("STOP")) {
    running = false;
  }
}

void processRFIDCommand(String command) {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    Serial.println("No RFID Card Detected");
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    Serial.println("Error reading RFID card");
    return;
  }

  String rfidTag = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    rfidTag += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    rfidTag += String(mfrc522.uid.uidByte[i], HEX);
  }
  rfidTag.toUpperCase();
  rfidTag.trim();

  Serial.println(rfidTag);
}
