#pragma once // Lệnh chống trùng lặp file
#include <WiFi.h>
#include <PubSubClient.h>
#include "devices_struct.h"
// ================= CẤU HÌNH =================
const char* ssid = "THE LIVING ROOM";       // Tên Wi-Fi
const char* password = "focusspace";        // Mật khẩu Wi-Fi
const char* mqtt_server = "192.168.123.25"; // IP của Raspberry Pi
const int mqtt_port = 1883;
// ============================================

WiFiClient espClient;
PubSubClient client(espClient);

// 1. Hàm nội bộ: Bắt sóng Wi-Fi (Chống treo)
void setup_wifi() {
  delay(10);
  Serial.print("\nDang ket noi vao Wi-Fi: "); Serial.println(ssid);
  WiFi.mode(WIFI_STA); 
  WiFi.disconnect();   
  delay(100);          
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print("."); attempts++;
    if (attempts > 30) {
      Serial.println("\n[LỖI] Khong the ket noi Wi-Fi! Tu dong Reset...");
      delay(3000); ESP.restart(); 
    }
  }
  Serial.println("\n✅ [XONG] WiFi da ket noi! IP: " + WiFi.localIP().toString());
}

// 2. Hàm nội bộ: Kết nối Bưu điện MQTT
void reconnect() {
  while (!client.connected()) {
    Serial.print("Dang thu ket noi MQTT Broker... ");
    if (client.connect("ESP32_Dev1_Client")) {
      Serial.println("✅ [THÀNH CÔNG] Da ket noi MQTT!");
    } else {
      Serial.print("❌ [THẤT BẠI] Ma loi rc="); Serial.print(client.state());
      Serial.println(" - Thu lai sau 5 giay...");
      delay(5000);
    }
  }
}

// ---------------------------------------------------------
// CÁC HÀM CÔNG CỤ ĐỂ FILE CHÍNH GỌI RA DÙNG (APIs)
// ---------------------------------------------------------

// Hàm A: Dùng ở setup() - Khởi động tất cả
void setup_wifi_mqtt() {
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

// Hàm B: Dùng ở loop() - Giữ mạng không bị đứt
void duy_tri_mqtt() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}

// Hàm C: Dùng để ném dữ liệu đi cho nhanh
void gui_len_mqtt(String topic, String  ) {
  Serial.print("📤 Dang gui len topic [" + topic + "]: "); 
  Serial.print(topic + " | ");
  Serial.println(payload);
  client.publish(topic.c_str(), payload.c_str());
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) message += (char)payload[i];
  
  String strTopic = String(topic);
  // Cắt chuỗi lấy ID từ topic "pbl5/control/device/4" -> 4
  int receivedID = strTopic.substring(strTopic.lastIndexOf('/') + 1).toInt();

  // Tìm trong danh sách myDevices
  for (int i = 0; i < deviceCount; i++) {
    if (myDevices[i].id == receivedID && myDevices[i].type == "actuator") {
      int state = (message == "ON") ? HIGH : LOW;
      digitalWrite(myDevices[i].pin, state);
      Serial.printf("🎯 Điều khiển thiết bị ID %d tại Pin %d -> %s\n", receivedID, myDevices[i].pin, message.c_str());
    }
  }
}

void fetchConfig() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(config_url);
    int httpCode = http.get();

    if (httpCode == 200) {
      String payload = http.getString();
      Serial.println("📥 Đã nhận cấu hình: " + payload);

      // Giải mã JSON từ Backend trả về
      DynamicJsonDocument doc(2048);
      deserializeJson(doc, payload);
      JsonArray root = doc.as<JsonArray>();

      deviceCount = root.size();
      for (int i = 0; i < deviceCount; i++) {
        myDevices[i].id = root[i]["id"];
        myDevices[i].type = root[i]["type"].as<String>();
        myDevices[i].pin = root[i]["pin"];

        // Tự động cấu hình chân Pin dựa trên loại thiết bị
        if (myDevices[i].type == "actuator") {
          pinMode(myDevices[i].pin, OUTPUT);
          digitalWrite(myDevices[i].pin, LOW); // Mặc định tắt
        } else {
          pinMode(myDevices[i].pin, INPUT);
        }
      }
      Serial.println("✅ Cấu hình chân Pin hoàn tất!");
    }
    http.end();
  }
}