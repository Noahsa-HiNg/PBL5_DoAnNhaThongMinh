from fastapi import WebSocket
from typing import List
import json

class WebSocketManager:
    """
    Quản lý danh sách tất cả mobile đang kết nối WebSocket.
    Dùng chung toàn dự án — import ws_manager từ file này.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Chấp nhận kết nối mới từ mobile"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📱 Mobile kết nối WebSocket. Tổng: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Xóa mobile khỏi danh sách khi disconnect"""
        self.active_connections.remove(websocket)
        print(f"📴 Mobile ngắt WebSocket. Còn lại: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """
        Gửi JSON xuống TẤT CẢ mobile đang kết nối.
        Tự động xóa client nếu đã ngắt kết nối.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data, ensure_ascii=False))
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)

# Singleton — dùng chung toàn dự án
ws_manager = WebSocketManager()