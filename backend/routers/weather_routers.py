from fastapi import APIRouter, HTTPException
import requests

router = APIRouter(prefix="/api/weather", tags=["Thời tiết"])

OPENWEATHER_API_KEY = "" 
#6052a7b7ed8d97552e1d5b0b395639a4


@router.get("/current")
def get_current_weather(city: str = "Da Nang"): 
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=vi"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # 1. TRƯỜNG HỢP THÀNH CÔNG (Mã 200)
        if response.status_code == 200:
            return {
                "status": "success",
                "city": data["name"],
                "temperature": round(data["main"]["temp"], 1),
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"].capitalize(),
                "icon_url": f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png"
            }
            
        # 2. TRƯỜNG HỢP SAI TÊN THÀNH PHỐ (Mã 404)
        elif response.status_code == 404:
            # Quăng lỗi 404 về cho App biết
            raise HTTPException(
                status_code=404, 
                detail=f"Không tìm thấy dữ liệu thời tiết cho khu vực: '{city}'"
            )
            
        # 3. TRƯỜNG HỢP LỖI API KEY (Mã 401)
        elif response.status_code == 401:
            raise HTTPException(
                status_code=401, 
                detail="Lỗi hệ thống: API Key thời tiết không hợp lệ hoặc chưa được kích hoạt."
            )
            
        # 4. CÁC LỖI KHÁC TỪ OPENWEATHER
        else:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Lỗi từ máy chủ thời tiết: {data.get('message', 'Không rõ nguyên nhân')}"
            )
            
    except requests.exceptions.RequestException as e:
        # 5. TRƯỜNG HỢP SERVER CỦA EM BỊ MẤT MẠNG
        raise HTTPException(
            status_code=500, 
            detail="Máy chủ Smart Home đang mất kết nối Internet, không thể lấy thời tiết lúc này."
        )