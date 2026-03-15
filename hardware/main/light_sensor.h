#pragma once // "Thần chú" giúp file này không bị lặp lại gây lỗi khi compile

int read_light_sensor(int pin) {
    return analogRead(pin);
}