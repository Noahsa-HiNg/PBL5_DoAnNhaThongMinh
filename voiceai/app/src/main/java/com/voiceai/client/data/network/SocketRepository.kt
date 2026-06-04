package com.voiceai.client.data.network

import android.util.Log
import com.voiceai.client.data.preferences.UserPreferences
import io.socket.client.IO
import io.socket.client.Socket
import io.socket.engineio.client.transports.WebSocket
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import org.json.JSONObject
import java.net.URISyntaxException

sealed class SocketEvent {
    data class SensorUpdate(val deviceId: Int, val type: String, val data: JSONObject) : SocketEvent()
    data class DeviceUpdate(val deviceId: Int, val type: String, val name: String, val data: JSONObject) : SocketEvent()
    object Connected : SocketEvent()
    object Disconnected : SocketEvent()
    data class Error(val message: String) : SocketEvent()
    data class AlarmTriggered(val label: String, val time: String) : SocketEvent()
}

class SocketRepository(private val userPreferences: UserPreferences) {

    companion object {
        private const val TAG = "SocketRepo"
    }

    private val _events = MutableSharedFlow<SocketEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<SocketEvent> = _events.asSharedFlow()

    private var mSocket: Socket? = null

    val isConnected: Boolean get() = mSocket?.connected() ?: false

    fun connect() {
        if (isConnected) return

        val ip = userPreferences.serverIp
        val port = userPreferences.serverPort
        if (ip.isBlank()) return

        // Socket.IO sử dụng URL dạng http/https, nó tự xử lý /socket.io/ path
        val socketUrl = "http://$ip:$port"
        Log.d(TAG, ">>> ĐANG KẾT NỐI SOCKET.IO: $socketUrl")

        try {
            val options = IO.Options().apply {
                forceNew = true
                reconnection = true
                reconnectionAttempts = Int.MAX_VALUE
                reconnectionDelay = 2000
                // Chỉ ưu tiên dùng websocket để tối ưu hiệu năng
                transports = arrayOf(WebSocket.NAME)
            }

            mSocket = IO.socket(socketUrl, options)

            mSocket?.on(Socket.EVENT_CONNECT) {
                Log.d(TAG, "✅ KẾT NỐI THÀNH CÔNG: $socketUrl")
                _events.tryEmit(SocketEvent.Connected)
            }

            mSocket?.on(Socket.EVENT_DISCONNECT) {
                Log.w(TAG, "🔌 ĐÃ NGẮT KẾT NỐI")
                _events.tryEmit(SocketEvent.Disconnected)
            }

            mSocket?.on(Socket.EVENT_CONNECT_ERROR) { args ->
                val err = args.getOrNull(0)?.toString() ?: "Unknown error"
                Log.e(TAG, "❌ Lỗi kết nối Socket.IO: $err")
                _events.tryEmit(SocketEvent.Error("Không thể kết nối tới $socketUrl ($err)"))
            }

            // --- Đăng ký lắng nghe các sự kiện từ Backend ---

            mSocket?.on("sensor_update") { args ->
                try {
                    val data = args[0] as JSONObject
                    _events.tryEmit(SocketEvent.SensorUpdate(
                        data.getInt("device_id"), 
                        data.getString("type"), 
                        data.getJSONObject("data")
                    ))
                } catch (e: Exception) {
                    Log.e(TAG, "Lỗi parse sensor_update: ${e.message}")
                }
            }

            mSocket?.on("device_update") { args ->
                try {
                    val data = args[0] as JSONObject
                    _events.tryEmit(SocketEvent.DeviceUpdate(
                        data.getInt("device_id"), 
                        data.getString("type"), 
                        data.optString("name", ""), 
                        data.getJSONObject("data")
                    ))
                } catch (e: Exception) {
                    Log.e(TAG, "Lỗi parse device_update: ${e.message}")
                }
            }

            mSocket?.on("alarm_triggered") { args ->
                try {
                    val data = args[0] as JSONObject
                    _events.tryEmit(SocketEvent.AlarmTriggered(
                        data.optString("label", "Báo thức"), 
                        data.optString("time", "")
                    ))
                } catch (e: Exception) {
                    Log.e(TAG, "Lỗi parse alarm_triggered: ${e.message}")
                }
            }

            mSocket?.connect()

        } catch (e: URISyntaxException) {
            Log.e(TAG, "❌ URL sai định dạng: ${e.message}")
            _events.tryEmit(SocketEvent.Error("Địa chỉ IP hoặc Port không hợp lệ"))
        }
    }

    fun disconnect() {
        mSocket?.disconnect()
        mSocket?.off()
        mSocket = null
        Log.d(TAG, "Đã đóng kết nối Socket")
    }

    fun reconnect() {
        Log.d(TAG, "Đang thử kết nối lại...")
        disconnect()
        connect()
    }

    /**
     * Gửi sự kiện lên server
     */
    fun emit(event: String, data: Any) {
        if (isConnected) {
            mSocket?.emit(event, data)
        } else {
            Log.w(TAG, "Không thể emit '$event': Chưa có kết nối")
        }
    }
}

