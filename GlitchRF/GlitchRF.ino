/*
 * GlitchRF Firmware - esp32 + nRf24L01+
 * Flash this single file using Arduino IDE
 * no Mods needed - just pick your eps-board and upload
 * creaper = promiscuous, it just looks cleaner also cuz im dyslexic so don't hate me
 * Created by: embededbuild
 */

#include <SPI.h>
#include <RF24.h>

//pin definition - basic wiring
#define CE_PIN 22
#define CSN_PIN 21

RF24 radio(CE_PIN, CSN_PIN);

//buffer for serial commands and radio payloads
char cmdBuffer[128];
uint8_t payloadBuffer[32];
unsigned long sniffStartTime = 0;
bool sniffing = false;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  //initialize radio shit
  if (!radio.begin()) {
    Serial.println("ERROR: Radio_Init_failed");
    while (1);
  }

  radio.setChannel(76);   //2476 Mhz defualt
  radio.setPALevel(RF24_PA_MAX);
  radio.setDataRate(RF24_1MBPS);
  radio.setAutoAck(false);    //crit for creaper sniffing
  radio.setCRCLength(RF24_CRC_DISABLED); //creeper mode
  
  // FIX: Cast to uint64_t explicitly to resolve the ambiguous overload
  uint64_t creeper_addr = 0x0000000000ULL;
  radio.openReadingPipe(1, creeper_addr); //short address for creeper

  Serial.println("READY");
}

void loop() {
  //Process incoming serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    // FIX: function name is processCommand (singular)
    processCommand(cmd);
  }

  //if in sniffing mode, continue to check for packets
  if (sniffing) {
    if (millis() - sniffStartTime > 10000) {
      sniffing = false;
      radio.stopListening();
      Serial.println("SNIFF_DONE");
    } else {
      checkForPacket();
    }
  }
}

void processCommand(String cmd) {
  // ====SYSTEM COMMANDS====
  if (cmd == "PING") {
    Serial.println("PONG:GlitchRF:V1.0");
  }

  //=====radio config=====
  else if (cmd.startsWith("SET_CHANNEL:")) {
    int ch = cmd.substring(12).toInt();
    if (ch >= 0 && ch <= 125) {
      radio.setChannel(ch);
      Serial.println("OK:CHANNEL:" + String(ch));
    } else {
      Serial.println("ERROR:Invalid_channel");
    }
  }

  else if (cmd.startsWith("SET_POWER:")) {
    int pwr = cmd.substring(10).toInt();
    // 0=MIN, 1=LOW, 2=HIGH, 3=MAX
    // FIX: setPALevel takes uint8_t as first argument, not a string
    // Send the OK response separately after setting power level
    if (pwr >= 0 && pwr <= 3) {
      radio.setPALevel(pwr);
      Serial.println("OK:POWER:" + String(pwr));
    } else {
      Serial.println("ERROR:Invalid_power_level");
    }
  }

  else if (cmd.startsWith("SET_RATE:")) {
    int rate = cmd.substring(9).toInt();
    //0=250kbps 1=1mbps 2=2mbps
    if (rate == 0) radio.setDataRate(RF24_250KBPS);
    else if (rate == 1) radio.setDataRate(RF24_1MBPS);
    else if (rate == 2) radio.setDataRate(RF24_2MBPS);
    Serial.println("OK:RATE:" + String(rate));
  }

  // FIX: Missing colon in "SET_ADDRESS:" - the startsWith check needs the colon
  else if (cmd.startsWith("SET_ADDRESS:")) {
    String addrStr = cmd.substring(12);
    // FIX: stroull -> strtoull (correct function name)
    uint64_t addr = strtoull(addrStr.c_str(), NULL, 16);
    radio.openReadingPipe(1, addr);
    radio.openWritingPipe(addr);
    // FIX: radio.println doesn't exist - use Serial.println
    Serial.println("OK:ADDRESS:" + addrStr);
  }

  // === passive recon commands ===
  else if (cmd == "SCAN_START") {
    // begin energy scan sweep
    Serial.println("SCAN:BEGIN");
    for (int ch = 0; ch <= 125; ch++) {
      radio.setChannel(ch);
      delayMicroseconds(200); //let the radio smoke a joint
      //use testCarrier() as simplified energy detection
      radio.startConstCarrier(RF24_PA_MIN, ch);
      delayMicroseconds(128);
      bool carrier = radio.testCarrier();
      radio.stopConstCarrier();
      Serial.println("SCAN:CH:" + String(ch) + ":RSSI:" + String(carrier ? 1 : 0));
    }
    Serial.println("SCAN:END");
  }

  //====ass sniffing i mean packet sniffing======
  else if (cmd == "SNIFF_START") {
    sniffing = true;
    sniffStartTime = millis();
    radio.startListening();
    Serial.println("SNIFF:START");
  }

  else if (cmd == "SNIFF_STOP") {
    sniffing = false; 
    radio.stopListening();
    Serial.println("SNIFF:STOP");
  }
  
  // PACKET transmissiobn
  // FIX: Added closing brace for SNIFF_STOP else-if, and properly structured the TX block
  else if (cmd.startsWith("TX:")) {
    String hexPayload = cmd.substring(3);
    // FIX: Divide by 2 because hex string is twice as long as byte array
    int len = hexPayload.length() / 2;
    for (int i = 0; i < len && i < 32; i++) {
      payloadBuffer[i] = strtoul(hexPayload.substring(i*2, i*2+2).c_str(), NULL, 16);
    }

    radio.stopListening();
    bool success = radio.write(payloadBuffer, len);
    if (success) {
      Serial.println("OK:TX_SUCCESS");
    } else {  // FIX: "} else if {" was invalid syntax - changed to "} else {"
      Serial.println("ERROR:TX_FAILED");
    }
  }

  // === relay mode commands ===
  else if (cmd == "RELAY_START") {
    // Enter transparent relay mode
    //all recived packets are immediately forwarded over serial
    // all serial TX commands are immediately transmitted
    Serial.println("RELAY:MODE_ACTIVE");
    relayMode();
  }
  
  else {
    Serial.println("ERROR:UNKNOWN_CMD:" + cmd);
  }
}

void checkForPacket() {
  if (radio.available()) {
    uint8_t len = radio.getDynamicPayloadSize();
    if (len > 0 && len <= 32) {
      radio.read(payloadBuffer, len);

      //send packet to host as hex string like a good little hacker
      Serial.print("PKT:");  // FIX: Added missing colon for consistent parsing
      for (int i = 0; i < len; i++) {
        // FIX: oayloadBuffer -> payloadBuffer (typo)
        if (payloadBuffer[i] < 0x10) Serial.print("0");
        Serial.print(payloadBuffer[i], HEX);
      }
      Serial.print(":LEN:");
      Serial.print(len);
      Serial.print(":RSSI:");
      Serial.println(radio.testRPD() ? "HIGH" : "LOW");  // FIX: Serial.print -> Serial.println to add newline
    }
  }
}

void relayMode() {
  //stay in relay mode until RELAY_STOP command recrived
  radio.startListening();  // FIX: Make sure we're listening when relay starts
  while (true) {
    //check you're ass crack did you wash it??
    //check for packet to forward to host
    if (radio.available()) {
      uint8_t len = radio.getDynamicPayloadSize();
      if (len > 0 && len <= 32) {
        radio.read(payloadBuffer, len);
        Serial.print("RELAY_FWD:");
        for (int i = 0; i < len; i++) {
          if (payloadBuffer[i] < 0x10) Serial.print("0");
          Serial.print(payloadBuffer[i], HEX);
        }
        Serial.println();
      }
    }

    //check for packets from host to transmit
    if (Serial.available()) {
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();

      if (cmd == "RELAY_STOP") {
        Serial.println("RELAY:STOPPED");
        return;
      }

      if (cmd.startsWith("TX:")) {
        String hexPayload = cmd.substring(3);
        int len = hexPayload.length() / 2;
        for (int i = 0; i < len && i < 32; i++) {
          payloadBuffer[i] = strtoul(hexPayload.substring(i*2, i*2+2).c_str(), NULL, 16);
        }
        radio.stopListening();
        radio.write(payloadBuffer, len);
        radio.startListening();
        Serial.println("RELAY_TX:OK");
      }
    }
  }
}