#pragma once
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "devices_config.h"
#include "light_device.h" // Kéo file xử lý vào
#include "fan_device.h"   // Kéo file xử lý vào
#include "door_device.h"
#include "buzzer_device.h"

const char* ssid = "hieu";       // Tên Wi-Fi
const char* password = "123456719";        // Mật khẩu Wi-Fi
const char* mqtt_server = "172.20.10.2"; // IP của máy tính chạy Server ras
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);
  
void callback(char* topic, byte* payload, unsigned int length) {
    String message = "";
    for (int i = 0; i < length; i++) message += (char)payload[i];
    String strTopic = String(topic);

    // Lấy ID thiết bị từ cuối chuỗi Topic
    int device_id = strTopic.substring(strTopic.lastIndexOf('/') + 1).toInt();

    // KIỂM TRA ID VÀ ĐIỀU KHIỂN
    if (device_id >= 1 && device_id <= 4) {
        control_light(device_id, message); // Hàm gọi đèn
    } 
    else if (device_id >= 5 && device_id <= 8) {
        control_fan(device_id, message);
    } 
    else if (device_id == 11) {
        control_door(device_id, message); // GỌI CỬA
    } 
    else if (device_id == 12) {
        control_buzzer(device_id, message); // GỌI LOA
        
        // Hoặc nếu Server gửi lệnh BEEP thì gọi beep_alarm
        if (message == "BEEP") {
            beep_alarm(device_id);
        }
    }
}

void setup_wifi_mqtt() {
  Serial.printf("\n🔄 Đang kết nối vào mạng Wi-Fi: %s", ssid);
  WiFi.mode(WIFI_STA); // Ép ESP32 làm thiết bị nhận Wi-Fi (không tự phát)
  WiFi.disconnect();
  delay(100);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print("-"); 
  }
  
  // IN RA KHI CÓ WI-FI
  Serial.println("\n✅ Đã kết nối Wi-Fi thành công!");
  Serial.print("🌐 Địa chỉ IP của ESP32 là: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void duy_tri_mqtt() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n⚠️ Mất kết nối Wi-Fi! Đang thử kết nối lại...");
    
    WiFi.disconnect();
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    // Cố gắng thử trong vòng 10 giây (20 lần x 500ms) để không làm treo toàn bộ code
    while (WiFi.status() != WL_CONNECTED && attempts < 20) { 
      delay(500);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n✅ Đã khôi phục kết nối Wi-Fi thành công!");
      Serial.print("🌐 Địa chỉ IP mới là: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("\n❌ Khôi phục Wi-Fi thất bại! Sẽ thử lại ở chu kỳ sau...");
      return; // Thoát hàm luôn, không chạy xuống phần MQTT nữa để tránh lỗi
    }
  }
  if (!client.connected()) {
    Serial.print("🔄 Đang thử kết nối tới MQTT Broker... ");
    
    if (client.connect("ESP32Client")) {
      // IN RA KHI KẾT NỐI BROKER THÀNH CÔNG
      Serial.println("✅ Đã kết nối MQTT Broker thành công! ");
      
      client.subscribe("home/control/device/#");
      Serial.println("📡 Đã đăng ký lắng nghe lệnh điều khiển!");
    } else {
      // IN RA MÃ LỖI NẾU THẤT BẠI ĐỂ DỄ BẮT BỆNH
      Serial.println(WiFi.localIP());
      Serial.print("❌ Thất bại! Mã lỗi (rc) = ");

      Serial.print(client.state());
      Serial.println(" -> Sẽ thử lại sau 5 giây...");
      delay(5000); // Đợi 5 giây rồi mới thử lại tránh làm treo board
    }
  }
  client.loop();
}