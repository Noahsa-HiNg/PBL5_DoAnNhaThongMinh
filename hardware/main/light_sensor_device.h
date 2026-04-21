#pragma once
#include "devices_config.h"
#include <ArduinoJson.h>

unsigned long lastLightSendTime = 0;
const int DARK_THRESHOLD = 1000;
void setup_light_sensors() {
  for (int i = 0; i < deviceCount; i++) {
    // Tìm thiết bị nào là cảm biến ánh sáng để cấu hình
    if (myDevices[i].type == "light_sensor") {
      pinMode(myDevices[i].pin, INPUT); 
      Serial.printf("☀️ Đã bật Cảm biến Ánh sáng tại chân %d (ID: %d)\n", myDevices[i].pin, myDevices[i].id);
    }
  }
}

void read_and_send_light_sensors() {
  unsigned long now = millis();
  
  // Đọc ánh sáng mỗi 5 giây 1 lần
  if (now - lastLightSendTime > 5000) {
    lastLightSendTime = now;

    for (int i = 0; i < deviceCount; i++) {
      if (myDevices[i].type == "light_sensor") {
        
        // Đọc giá trị Analog của chân 32 (Từ 0 đến 4095)
        int light_value = analogRead(myDevices[i].pin);
        
        // Đóng gói JSON gửi đi. VD: {"light": 2500}
        DynamicJsonDocument doc(128);
        doc["light"] = light_value;
        String payload;
        serializeJson(doc, payload);

        // Gửi lên Topic: home/sensors/10
        String topic = "home/sensors/" + String(myDevices[i].id);
        client.publish(topic.c_str(), payload.c_str());
        
        Serial.printf("📤 Gửi Ánh sáng [%s]: Mức %d\n", topic.c_str(), light_value);
      }     // ← đóng if(light_sensor)
    }       // ← đóng for
  }         // ← đóng if(millis)
}