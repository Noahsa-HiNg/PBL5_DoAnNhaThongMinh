#pragma once
#include "devices_config.h"
#include <DHT.h>
#include <ArduinoJson.h>

#define DHTTYPE DHT11
const int CO2_HIGH_THRESHOLD = 500;
// Tạo một mảng lưu trữ các bộ cảm biến (Kích thước bằng tổng số thiết bị)
DHT* dht_sensors[deviceCount]; 
unsigned long lastSendTime = 0;

void setup_sensors() {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].type == "sensor") {
      // Dùng từ khóa 'new' để cấp phát bộ nhớ tạo ra một cảm biến mới
      dht_sensors[i] = new DHT(myDevices[i].pin, DHTTYPE);
      dht_sensors[i]->begin();
      Serial.printf("🌡️ Đã bật Cảm biến DHT11 tại chân %d (ID: %d)\n", myDevices[i].pin, myDevices[i].id);
    } else {
      dht_sensors[i] = nullptr; // Nếu là đèn/quạt thì để trống
    }
  }
}

void read_and_send_sensors() {
  unsigned long now = millis();
  
  // Cứ 5 giây duyệt qua đọc tất cả các cảm biến một lượt
  if (now - lastSendTime > 5000) {
    lastSendTime = now;

    for (int i = 0; i < deviceCount; i++) {
      // Nếu thiết bị này là sensor và đã được khởi tạo
      if (myDevices[i].type == "sensor" && dht_sensors[i] != nullptr) {
        
        float t = dht_sensors[i]->readTemperature();
        float h = dht_sensors[i]->readHumidity();

        if (!isnan(t) && !isnan(h)) {
          DynamicJsonDocument doc(256);
          doc["temp"] = t;
          doc["humi"] = h;
          String payload;
          serializeJson(doc, payload);

          // Lắp ráp Topic động dựa theo ID của từng cảm biến
          String topic = "home/sensors/" + String(myDevices[i].id);
          client.publish(topic.c_str(), payload.c_str());
          
          Serial.printf("📤 Gửi lên [%s]: Temp=%.1f, Humi=%.1f\n", topic.c_str(), t, h);
        } else {
          Serial.printf("❌ Lỗi đọc Cảm biến ID %d\n", myDevices[i].id);
        }
        // int co2_value = analogRead(myDevices[i].pin_main); 
        // if (co2_value > CO2_HIGH_THRESHOLD) {
        //   // Nếu CO2 cao: Bật quạt (Giả sử quạt ID là 5) ở tốc độ cao nhất (3) và có xoay
        //   control_fan(5, "{\"speed\":3, \"swing\":\"ON\"}");
        //   Serial.println("⚠️ CO2 cao! Tự động bật quạt thông gió.");
        //   client.publish("home/status/device/5", "{\"speed\":3, \"swing\":\"ON\"}");
        // } else {
        //   // Nếu CO2 ổn định: Tắt quạt
        //   control_fan(5, "{\"speed\":0, \"swing\":\"OFF\"}");
        //   client.publish("home/status/device/5", "{\"speed\":0, \"swing\":\"OFF\"}");
        // }
      }
    }
  }
}