#pragma once
#include <Arduino.h>

struct Device {
  int id;
  String type;      // "light", "fan", "sensor", "light_sensor", "door_lock", "buzzer"
  int pin;          // Chân cắm trên ESP32 (Đổi từ pin_main thành pin)
};

const int deviceCount = 12; 


// Mảng giờ đây cực kỳ gọn gàng, nhìn vào là hiểu ngay!
Device myDevices[deviceCount] = {
  // 4 ĐÈN 
  {1, "light", 18},  
  {2, "light", 19}, 
  {3, "light", 21}, 
  {4, "light", 22}, 
  
  // 4 QUẠT 
  {5, "fan", 26},   
  {6, "fan", 25},   
  {7, "fan", 33},   
  {8, "fan", 32},   
  
  // 2 CẢM BIẾN
  {9, "sensor", 4}, 
  {10, "light_sensor", 35},

  // THIẾT BỊ MỚI
  {11, "door_lock", 13},
  {12, "buzzer", 16} 
};

void setup_pins() {
  Serial.println("⚙️ Đang cấu hình chân Pin tĩnh...");
  for (int i = 0; i < deviceCount; i++) {
    
    // Cài đặt chân cho Đèn, Loa, Quạt
    if (myDevices[i].type == "light" || myDevices[i].type == "buzzer" || myDevices[i].type == "fan") {
      pinMode(myDevices[i].pin, OUTPUT);
      digitalWrite(myDevices[i].pin, LOW); // Tắt mặc định
    } 
    // Cửa (door) dùng thư viện Servo tự lo, DHT11 thư viện tự lo.
  }
  Serial.println("✅ Cấu hình Pin hoàn tất!");
}