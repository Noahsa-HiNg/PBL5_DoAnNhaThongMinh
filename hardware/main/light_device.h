#pragma once
#include "devices_config.h"

void setup_lights() {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].type == "light") {
      pinMode(myDevices[i].pin, OUTPUT);
      digitalWrite(myDevices[i].pin, LOW); 
    }
  }
}

void control_light(int id, String command) {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].id == id && myDevices[i].type == "light") {
      int state = (command == "ON") ? HIGH : LOW;
      digitalWrite(myDevices[i].pin, state);
      Serial.printf("💡 Đèn ID %d -> %s\n", id, command.c_str());
      break; // Xử lý xong thì thoát vòng lặp cho nhẹ máy
    }
  }
}