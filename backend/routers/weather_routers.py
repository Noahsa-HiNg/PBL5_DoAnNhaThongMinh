from fastapi import APIRouter, HTTPException
from core.config import OPENWEATHER_API_KEY, DEFAULT_CITY
import requests
from datetime import datetime

router = APIRouter(prefix="/api/weather", tags=["Thời tiết"])

@router.get("/current")
def get_current_weather(city: str = DEFAULT_CITY): 
    """Lấy thời tiết hiện tại từ OpenWeatherMap"""
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=vi"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "status": "success",
                "data": {
                    "city": data["name"],
                    "temperature": round(data["main"]["temp"], 1),
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"].capitalize(),
                    "icon_url": f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
                    "timestamp": datetime.now().isoformat()
                }
            }
        elif response.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail={"error_code": "CITY_NOT_FOUND", "message": f"Không tìm thấy dữ liệu thời tiết cho khu vực: '{city}'"}
            )
        elif response.status_code == 401:
            raise HTTPException(
                status_code=401, 
                detail={"error_code": "API_KEY_INVALID", "message": "API Key thời tiết không hợp lệ hoặc chưa được kích hoạt"}
            )
        else:
            raise HTTPException(
                status_code=response.status_code, 
                detail={"error_code": "WEATHER_API_ERROR", "message": f"Lỗi từ máy chủ thời tiết: {data.get('message', 'Không rõ')}"}
            )
            
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=500, 
            detail={"error_code": "NETWORK_ERROR", "message": "Máy chủ đang mất kết nối Internet"}
        )
