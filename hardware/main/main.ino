#include "light_device.h"        
#include "fan_device.h"          
#include "wifi_mqtt.h"
#include "sensor_device.h"
#include "light_sensor_device.h"
#include "devices_config.h"
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
}