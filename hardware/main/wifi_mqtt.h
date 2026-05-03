#pragma once
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "devices_config.h"
#include "light_device.h" 
#include "fan_device.h"   
#include "door_device.h"
#include "buzzer_device.h"

const char* ssid = "hieu";       
const char* password = "123456719";        
const char* mqtt_server = "172.20.10.3"; 
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

// === BIẾN TOÀN CỤC ĐỂ BẤM GIỜ BẰNG MILLIS ===
unsigned long lastWiFiCheck = 0;
unsigned long lastMQTTCheck = 0;
const unsigned long WIFI_RETRY_INTERVAL = 10000; // 10 giây thử lại WiFi 1 lần
const unsigned long MQTT_RETRY_INTERVAL = 5000;  // 5 giây thử lại MQTT 1 lần

void callback(char* topic, byte* payload, unsigned int length) {
    // Tối ưu: Chuyển payload sang String trực tiếp, không dùng vòng lặp for
    String message((char*)payload, length);
    String strTopic = String(topic);

    int device_id = strTopic.substring(strTopic.lastIndexOf('/') + 1).toInt();

    // KIỂM TRA ID VÀ ĐIỀU KHIỂN
    if (device_id >= 1 && device_id <= 4) {
        control_light(device_id, message); 
    } 
    else if (device_id >= 5 && device_id <= 8) {
        control_fan(device_id, message);
    } 
    else if (device_id == 11) {
        control_door(device_id, message); 
    } 
    else if (device_id == 12) {
        control_buzzer(device_id, message); 
    }
}

void setup_wifi_mqtt() {
  Serial.printf("\n🔄 Đang kết nối vào mạng Wi-Fi: %s\n", ssid);
  WiFi.mode(WIFI_STA); 
  WiFi.disconnect();
  delay(100);
  WiFi.begin(ssid, password);
  
  // Trong setup thì dùng while + delay được vì nó chỉ chạy 1 lần lúc khởi động
  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) { 
    delay(500); 
    Serial.print("-"); 
    timeout++;
  }
  
  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Đã kết nối Wi-Fi thành công!");
    Serial.print("🌐 Địa chỉ IP của ESP32 là: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠️ Không thể kết nối Wi-Fi lúc này. Sẽ thử lại trong loop()!");
  }

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void duy_tri_mqtt() {
  unsigned long currentMillis = millis();

  // 1. KIỂM TRA VÀ DUY TRÌ WI-FI
  if (WiFi.status() != WL_CONNECTED) {
    if (currentMillis - lastWiFiCheck >= WIFI_RETRY_INTERVAL) {
      Serial.println("\n⚠️ Mất kết nối Wi-Fi! Đang thử kết nối lại...");
      
      // FIX LỖI WATCHDOG TIMEOUT Ở ĐÂY:
      WiFi.disconnect();
      delay(10); // Cho CPU dọn dẹp tác vụ mạng cũ
      WiFi.mode(WIFI_STA);
      delay(10); // Nhường quyền xử lý một nhịp trước khi gọi lệnh begin nặng nề
      WiFi.begin(ssid, password); 
      
      lastWiFiCheck = currentMillis; 
    }
    return; // Đang rớt mạng WiFi thì thoát hàm luônádasd
  }

  // 2. KIỂM TRA VÀ DUY TRÌ MQTT
  if (!client.connected()) {
    if (currentMillis - lastMQTTCheck >= MQTT_RETRY_INTERVAL) {
      Serial.print("🔄 Đang thử kết nối tới MQTT Broker... ");
      lastMQTTCheck = currentMillis; 
      
      // Tạo Client ID ngẫu nhiên để tránh đụng độ và bị kick liên tục
      String clientId = "ESP32Client-";
      clientId += String(random(0xffff), HEX);
      
      if (client.connect(clientId.c_str())) {
        Serial.println("✅ Đã kết nối MQTT Broker thành công! ");
        client.subscribe("home/control/device/#");
        Serial.println("📡 Đã đăng ký lắng nghe lệnh điều khiển!");
      } else {
        Serial.print("❌ Thất bại! Mã lỗi (rc) = ");
        Serial.print(client.state());
        Serial.println(" -> Sẽ thử lại sau 5 giây...");
      }
    }
  } else {
    // 3. NẾU MỌI THỨ KẾT NỐI OK THÌ DUY TRÌ VÒNG LẶP MQTT
    client.loop();
  }
}