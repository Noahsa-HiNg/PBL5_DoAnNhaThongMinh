#pragma once
#include "devices_config.h"
#include <ESP32Servo.h>

Servo doorServo; // Tạo đối tượng Servo

void setup_door() {
  // Cấu hình chuẩn PWM cho Servo trên ESP32
  ESP32PWM::allocateTimer(0);
  doorServo.setPeriodHertz(50); // Servo chuẩn chạy ở 50Hz
  
  // Tự động quét mảng myDevices để tìm chân của Cửa
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].type == "door") {
      doorServo.attach(myDevices[i].pin, 500, 2400); 
      doorServo.write(0); // Mặc định góc 0 độ (Đóng cửa)
      Serial.printf("🚪 Cửa chính đã khởi tạo tại chân GPIO %d (Góc 0 độ)\n", myDevices[i].pin);
      break; // Tìm thấy rồi thì thoát vòng lặp
    }
  }
}

void control_door(int id, String command) {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].id == id && myDevices[i].type == "door") {
      if (command == "OPEN") {
        doorServo.write(90); // Quay 90 độ để mở cửa
        Serial.println("🚪 Cửa đang MỞ");
      } 
      else if (command == "CLOSE" || command == "CLOSED") {
        doorServo.write(0);  // Quay về 0 độ để đóng cửa
        Serial.println("🚪 Cửa đang ĐÓNG");
      }
      break;
    }
  }
}