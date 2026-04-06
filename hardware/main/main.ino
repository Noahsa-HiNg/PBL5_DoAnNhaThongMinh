#include "light_device.h"        
#include "fan_device.h"          
#include "wifi_mqtt.h"
#include "sensor_device.h"
#include "light_sensor_device.h"
#include "devices_config.h"
#include "sensor_device.h"
void setup() {
  Serial.begin(115200);
  
  // 1. Khởi động từng phần cứng cứng
  setup_lights();
  setup_fans();
  setup_sensors();
  setup_light_sensors();
  // 2. Bật mạng lên
  setup_door();
  setup_pins();
  setup_wifi_mqtt();
}

void loop() {
  duy_tri_mqtt();
  read_and_send_sensors();
  read_and_send_light_sensors();
  
  if (Serial.available()) {
    char c = Serial.read();
    if (c == '1') {
      analogWrite(18, 255); // Gõ '1' bật quạt tối đa
      Serial.println("Fan ON");
    } else if (c == '0') {
      analogWrite(18, 0);   // Gõ '0' tắt quạt
      Serial.println("Fan OFF");
    }
  
}
}