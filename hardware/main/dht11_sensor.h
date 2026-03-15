#include <DHT.h>

// Hàm đọc DHT11 (nhận vào chân Pin và loại dữ liệu cần đọc)
float read_dht11(int pin, String type) {
    DHT dht(pin, DHT11);
    dht.begin();
    delay(100); // Đợi cảm biến ổn định
    
    if (type == "temperature") return dht.readTemperature();
    if (type == "humidity") return dht.readHumidity();
    return 0.0;
}
