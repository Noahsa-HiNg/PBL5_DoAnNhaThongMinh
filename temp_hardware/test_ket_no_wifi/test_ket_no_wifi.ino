#include <WiFi.h>
#include <PubSubClient.h>

// --- 1. CẤU HÌNH MẠNG & SERVER ---
const char* ssid = "THE LIVING ROOM";             // <-- TÊN WIFI TỪ ĐIỆN THOẠI
const char* password = "focusspace";          // <-- MẬT KHẨU WIFI
const char* mqtt_server = "192.168.123.25"; // <-- IP CỦA RASPBERRY PI LẤY Ở BƯỚC 1
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

// --- 2. HÀM KẾT NỐI WIFI SIÊU CẤP ---
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
  Serial.println("\n✅ [XONG] WiFi da ket noi thanh cong! IP: " + WiFi.localIP().toString());
}

// --- 3. HÀM KẾT NỐI MQTT ---
void reconnect() {
  while (!client.connected()) {
    Serial.print("Dang thu ket noi MQTT Broker... ");
    String clientId = "ESP32_Dev1_Client"; 
    if (client.connect(clientId.c_str())) {
      Serial.println("✅ [THÀNH CÔNG] Da ket noi MQTT!");
    } else {
      Serial.print("❌ [THẤT BẠI] Ma loi rc="); Serial.print(client.state());
      Serial.println(" - Thu lai sau 5 giay...");
      delay(5000);
    }
  }
}

// --- 4. HÀM SETUP TRUNG TÂM ---
void setup() {
  Serial.begin(115200);
  setup_wifi(); 
  client.setServer(mqtt_server, mqtt_port); 
}

// --- 5. VÒNG LẶP CHÍNH ---
void loop() {
  if (!client.connected()) reconnect();
  client.loop(); 

  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  
  // Cứ 5 giây gửi dữ liệu 1 lần
  if (now - lastMsg > 5000) {
    lastMsg = now;
    
    // (Sau này em sẽ thay hàm random này bằng lệnh đọc cảm biến DHT11)
    String payload = "Nhiet do hien tai: " + String(random(25, 35)) + "*C";
    
    Serial.print("📤 Dang gui: "); Serial.println(payload);
    client.publish("pbl5/sensor", payload.c_str());
  }
}