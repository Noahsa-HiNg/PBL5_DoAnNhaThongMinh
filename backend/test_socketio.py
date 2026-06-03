import websocket
import json
import time

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connection opened")
    # Keep connection alive
    while True:
        time.sleep(10)

if __name__ == "__main__":
    # Test WebSocket connection directly
    ws_url = "ws://localhost:8000/socket.io/?EIO=4&transport=websocket"
    ws = websocket.WebSocketApp(ws_url,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)

    ws.run_forever()