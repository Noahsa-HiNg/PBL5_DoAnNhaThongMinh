#pragma once
#include "devices_config.h"
#include <ArduinoJson.h> 

void setup_fans() {
  // Ghi chú: Thực ra hàm setup_pins() ở file config đã gọi pinMode cho quạt rồi.
  // Nhưng nếu em vẫn muốn giữ hàm này để cài đặt riêng thì sửa lại như sau:
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].type == "fan") {
      // Chỉ còn cấu hình 1 chân duy nhất (pin)
      pinMode(myDevices[i].pin, OUTPUT);
      digitalWrite(myDevices[i].pin, LOW);
    }
  }
}

void control_fan(int id, String payload) {
    // 1. Giải mã chuỗi JSON từ MQTT
    DynamicJsonDocument doc(256);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
        Serial.print("❌ Lỗi đọc JSON quạt: ");
        Serial.println(error.c_str());
        return;
    }

    // 2. Chỉ còn lấy tốc độ (0-3), không còn swing
    int speed = doc["speed"];           
    
    for (int i = 0; i < deviceCount; i++) {
        if (myDevices[i].id == id && myDevices[i].type == "fan") {
            int pwmValue = 0;
            
            // Chuyển đổi mức tốc độ (1,2,3) sang giá trị băm xung PWM (0-255)
            if (speed == 1) pwmValue = 80;
            else if (speed == 2) pwmValue = 175;
            else if (speed == 3) pwmValue = 255;
            // Nếu speed == 0 thì pwmValue vẫn là 0 (Tắt)
            
            // 3. Xuất xung PWM ra chân của quạt
            analogWrite(myDevices[i].pin, pwmValue); 

            Serial.printf("🌀 Quạt ID %d: Đã chỉnh tốc độ mức %d (PWM: %d)\n", id, speed, pwmValue);
            break; // Tìm thấy thì dừng vòng lặp
        }
    }
}