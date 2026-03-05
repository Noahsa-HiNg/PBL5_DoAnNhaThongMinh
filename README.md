# 🏡 PBL5: Smart Home Edge AI - Điều khiển bằng Tiếng Việt Offline

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%7C%20ESP32-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> [cite_start]**Đề tài:** Thiết kế và triển khai hệ thống Smart Home tích hợp trí tuệ nhân tạo tại biên (Edge AI) hỗ trợ điều khiển bằng ngôn ngữ tự nhiên tiếng Việt[cite: 1].

[cite_start]Hệ thống nhà thông minh vận hành độc lập (Offline), không phụ thuộc vào Internet hay Cloud[cite: 26]. [cite_start]Hệ thống tích hợp xử lý ngôn ngữ tự nhiên tiếng Việt ngay trên Raspberry Pi để điều khiển mạng lưới thiết bị IoT (ESP32) qua giao thức MQTT, đảm bảo tốc độ phản hồi nhanh và quyền riêng tư tuyệt đối[cite: 5].

---

## ✨ Tính năng nổi bật

- [cite_start]**🗣️ Điều khiển bằng giọng nói tự nhiên:** Nhận diện và hiểu ý định từ câu lệnh tiếng Việt tự nhiên (VD: "Trời hơi nóng" -> Tự bật quạt)[cite: 27].
- [cite_start]**⚡ Hoạt động tại biên (Edge Processing):** Xử lý STT (Vosk) và NLP (JointBERT Int8) trực tiếp trên phần cứng nội bộ, độ trễ < 2 giây[cite: 17, 18, 31].
- **🔒 Offline & Bảo mật:** Hoàn toàn không cần Internet. [cite_start]Không gửi dữ liệu âm thanh/hình ảnh ra ngoài lưới mạng gia đình[cite: 26].
- [cite_start]**📊 Dashboard Giám sát Real-time:** Xem luồng Camera trực tiếp, theo dõi nhiệt độ, độ ẩm và điều khiển thiết bị qua giao diện Web[cite: 24].

---

## 🏗️ Kiến trúc Hệ thống

[cite_start]Dự án được xây dựng theo mô hình 3 lớp[cite: 14]:
1. [cite_start]**Edge Gateway (Raspberry Pi 4):** Đóng vai trò bộ não, chạy Web Server (FastAPI), AI Engine (Vosk + ONNX) và MQTT Broker (Mosquitto)[cite: 15, 17, 18, 20].
2. [cite_start]**Nodes (ESP32):** Các vi điều khiển đầu cuối, nhận lệnh qua Wi-Fi nội bộ để đóng/ngắt Relay và đọc cảm biến DHT11[cite: 21, 22, 23].
3. [cite_start]**Frontend Dashboard:** Giao diện người dùng Web/App giám sát hệ thống[cite: 24].

---

## 🛠️ Yêu cầu Phần cứng

- **Gateway:** Raspberry Pi 4 (4GB/8GB RAM), Microphone USB, Pi Camera V2.
- **Nodes:** ESP32 DevKit V1 (30 chân), Relay Module 4 kênh (Opto cách ly), Cảm biến DHT11/DHT22.
- **Mạng:** 01 Router Wi-Fi (Tạo mạng LAN Local).

---

## 📂 Cấu trúc Thư mục (Monorepo)

Dự án được chia thành 4 phân hệ chính để nhóm phát triển song song:

```text
pbl5-smarthome-edge-ai/
├── ai_engine/       # Xử lý STT (Vosk) và NLP (JointBERT)
├── backend/         # Web Server FastAPI, Camera Stream & MQTT Handler
├── frontend/        # Giao diện Web Dashboard (HTML/CSS/JS)
└── hardware/        # Code C++ (PlatformIO) nạp cho ESP32 & Sơ đồ mạch

ping pbl5.local -4 #để lấy ip ras
ssh pi@192.168.1.100 #để vào ras
mật khẩu : 123456
port: 1883 #port mqtt