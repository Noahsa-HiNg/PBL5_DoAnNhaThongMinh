#include "light_sensor.h"
#include "wifi_mqtt.h"
#include "dht11_sensor.h"

unsigned long lastMsg = 0;
enum DeviceType { LIGHT, FAN, DHT11_TEMP, DHT11_HUMID, LIGHT_SENSOR };
void setup() {
  Serial.begin(115200);
  setup_dht11();
  setup_light_sensor(); 
  setup_wifi_mqtt();    
  fetchConfig();
}




void loop() {
  duy_tri_mqtt();

  unsigned long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;

    int muc_anh_sang = read_light_sensor();
    String payload_anh_sang = "{\"light\": " + String(muc_anh_sang) + "}";
    gui_len_mqtt("pbl5/sensor/light", payload_anh_sang);

    float muc_nhiet_do = read_nhiet_do();
    if (muc_nhiet_do != -999.0) { 
      String payload_nhiet_do = "{\"temperature\": " + String(muc_nhiet_do) + "}";
      gui_len_mqtt("pbl5/sensor/temperature", payload_nhiet_do); 
    }

    float muc_do_am = read_do_am();
    if (muc_do_am != -999.0) {
      String payload_do_am = "{\"humidity\": " + String(muc_do_am) + "}"; 
      gui_len_mqtt("pbl5/sensor/humidity", payload_do_am); 
    }
  }
}