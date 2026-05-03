from fastapi import APIRouter, HTTPException
from core.config import OPENWEATHER_API_KEY, DEFAULT_CITY
import requests
from datetime import datetime

router = APIRouter(prefix="/api/weather", tags=["Thời tiết"])

# ============================================================
# MAPPING: OpenWeatherMap description (English) → Tiếng Việt
# Nguồn: https://openweathermap.org/weather-conditions
# ============================================================
WEATHER_VI_MAP: dict[str, str] = {
    # --- Nhóm 2xx: Thunderstorm ---
    "thunderstorm with light rain":     "Dông kèm mưa nhẹ",
    "thunderstorm with rain":           "Dông kèm mưa",
    "thunderstorm with heavy rain":     "Dông kèm mưa to",
    "light thunderstorm":               "Dông nhẹ",
    "thunderstorm":                     "Dông",
    "heavy thunderstorm":               "Dông mạnh",
    "ragged thunderstorm":              "Dông thất thường",
    "thunderstorm with light drizzle":  "Dông kèm mưa phùn nhẹ",
    "thunderstorm with drizzle":        "Dông kèm mưa phùn",
    "thunderstorm with heavy drizzle":  "Dông kèm mưa phùn nặng hạt",

    # --- Nhóm 3xx: Drizzle ---
    "light intensity drizzle":          "Mưa phùn nhẹ",
    "drizzle":                          "Mưa phùn",
    "heavy intensity drizzle":          "Mưa phùn nặng hạt",
    "light intensity drizzle rain":     "Mưa phùn nhẹ",
    "drizzle rain":                     "Mưa phùn",
    "heavy intensity drizzle rain":     "Mưa phùn nặng hạt",
    "shower rain and drizzle":          "Mưa rào kèm mưa phùn",
    "heavy shower rain and drizzle":    "Mưa rào nặng hạt kèm mưa phùn",
    "shower drizzle":                   "Mưa phùn rào",

    # --- Nhóm 5xx: Rain ---
    "light rain":                       "Mưa nhỏ",
    "moderate rain":                    "Mưa vừa",
    "heavy intensity rain":             "Mưa to",
    "very heavy rain":                  "Mưa rất to",
    "extreme rain":                     "Mưa cực lớn",
    "freezing rain":                    "Mưa đóng băng",
    "light intensity shower rain":      "Mưa rào nhẹ",
    "shower rain":                      "Mưa rào",
    "heavy intensity shower rain":      "Mưa rào nặng hạt",
    "ragged shower rain":               "Mưa rào thất thường",

    # --- Nhóm 6xx: Snow ---
    "light snow":                       "Tuyết nhẹ",
    "snow":                             "Tuyết",
    "heavy snow":                       "Tuyết dày",
    "sleet":                            "Mưa tuyết",
    "light shower sleet":               "Mưa tuyết nhẹ",
    "shower sleet":                     "Mưa tuyết rào",
    "light rain and snow":              "Mưa nhẹ và tuyết",
    "rain and snow":                    "Mưa và tuyết",
    "light shower snow":                "Tuyết rào nhẹ",
    "shower snow":                      "Tuyết rào",
    "heavy shower snow":                "Tuyết rào dày",

    # --- Nhóm 7xx: Atmosphere ---
    "mist":                             "Sương mù nhẹ",
    "smoke":                            "Khói",
    "haze":                             "Sương mù",
    "sand/dust whirls":                 "Lốc cát",
    "fog":                              "Sương mù dày",
    "sand":                             "Cát",
    "dust":                             "Bụi",
    "volcanic ash":                     "Tro núi lửa",
    "squalls":                          "Gió giật",
    "tornado":                          "Lốc xoáy",

    # --- Nhóm 800: Clear ---
    "clear sky":                        "Bầu trời quang đãng",

    # --- Nhóm 80x: Clouds ---
    "few clouds":                       "Ít mây",
    "scattered clouds":                 "Mây rải rác",
    "broken clouds":                    "Nhiều mây",
    "overcast clouds":                  "Mây phủ kín",
}

def translate_weather(description_en: str) -> str:
    """Dịch description tiếng Anh sang tiếng Việt, fallback về chính nó nếu không có."""
    return WEATHER_VI_MAP.get(description_en.lower(), description_en.capitalize())


@router.get("/current")
def get_current_weather(city: str = DEFAULT_CITY):
    """Lấy thời tiết hiện tại từ OpenWeatherMap"""

    # Không dùng lang=vi — nhận tiếng Anh rồi tự map
    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if response.status_code == 200:
            desc_en = data["weather"][0]["description"]   # tiếng Anh gốc
            desc_vi = translate_weather(desc_en)           # tiếng Việt đã map

            return {
                "status": "success",
                "data": {
                    "city":           data["name"],
                    "temperature":    round(data["main"]["temp"], 1),
                    "feels_like":     round(data["main"]["feels_like"], 1),
                    "humidity":       data["main"]["humidity"],
                    "description":    desc_vi,
                    "description_en": desc_en.capitalize(),
                    "icon_url":       f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
                    "timestamp":      datetime.now().isoformat()
                }
            }

        elif response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "CITY_NOT_FOUND",
                        "message": f"Không tìm thấy dữ liệu thời tiết cho khu vực: '{city}'"}
            )
        elif response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail={"error_code": "API_KEY_INVALID",
                        "message": "API Key thời tiết không hợp lệ hoặc chưa được kích hoạt"}
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail={"error_code": "WEATHER_API_ERROR",
                        "message": f"Lỗi từ máy chủ thời tiết: {data.get('message', 'Không rõ')}"}
            )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "NETWORK_ERROR",
                    "message": "Máy chủ đang mất kết nối Internet"}
        )
