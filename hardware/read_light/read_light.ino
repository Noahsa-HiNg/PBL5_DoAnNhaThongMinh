// Khai báo chân cắm cảm biến
#define LIGHT_SENSOR_PIN 34 

void setup() {
  // Mở cổng Serial để xem dữ liệu
  Serial.begin(115200);
  Serial.println("Dang khoi dong Cam bien anh sang...");
  
  // Thiết lập chân 34 là chân Nhận tín hiệu (INPUT)
  pinMode(LIGHT_SENSOR_PIN, INPUT);
}

void loop() {
  // ESP32 đọc giá trị Analog (Dải số từ 0 đến 4095)
  int gia_tri_anh_sang = analogRead(LIGHT_SENSOR_PIN);

  // In ra màn hình
  Serial.print("☀️ Cuong do anh sang (Raw): ");
  Serial.print(gia_tri_anh_sang);

  // Phân tích sơ bộ để hiển thị cho vui mắt
  if (gia_tri_anh_sang < 1000) {
    Serial.println("  => Troi dang rat SANG! 😎");
  } 
  else if (gia_tri_anh_sang < 3000) {
    Serial.println("  => Anh sang VUA PHAI. 🌤️");
  } 
  else {
    Serial.println("  => Troi TOI THUI! 🌙");
  }

  // Đợi 1 giây rồi đọc lại
  delay(1000);
}