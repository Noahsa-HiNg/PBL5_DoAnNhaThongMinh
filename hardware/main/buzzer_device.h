#pragma once
#include "devices_config.h"

void beep_alarm(int id) {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].id == id && myDevices[i].type == "buzzer") {
      
      for (int j = 0; j < 3; j++) {
        digitalWrite(myDevices[i].pin, HIGH);
        delay(200); // Kêu 0.2 giây
        digitalWrite(myDevices[i].pin, LOW);
        delay(200); // Tắt 0.2 giây
      }
      
      break;
    }
  }
}

void control_buzzer(int id, String command) {
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].id == id && myDevices[i].type == "buzzer") {
      
      if (command == "ON") {
        digitalWrite(myDevices[i].pin, HIGH); // Bật loa kêu
        Serial.println("📢 Loa: BẬT KÊU");
      } 
      else if (command == "OFF") {
        digitalWrite(myDevices[i].pin, LOW);  // Tắt loa
        Serial.println("📢 Loa: TẮT");
      }
      else if (command == "BEEP") beep_alarm(id);
      
      break; // Tìm thấy thì dừng vòng lặp
    }
  }
}

// 💡 Tặng thêm: Hàm gọi loa kêu "Bíp Bíp Bíp" dùng làm chuông báo thức hoặc cảnh báo cháy
