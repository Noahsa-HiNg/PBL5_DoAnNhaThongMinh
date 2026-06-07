package com.voiceai.client.ui.devices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.model.Device
import com.voiceai.client.data.network.DeviceRepository
import com.voiceai.client.data.network.SocketEvent
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.preferences.UserPreferences
import com.voiceai.client.data.local.LocalDeviceRepository
import com.voiceai.client.data.local.entity.DeviceEntity
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class DevicesUiState(
    val lights: List<Device> = emptyList(),
    val fans: List<Device>   = emptyList(),
    val doors: List<Device>  = emptyList(),
    val buzzers: List<Device> = emptyList(),
    val sensors: List<Device> = emptyList(),
    val isMainDoorUnlocked: Boolean = false, // Trạng thái cửa chính
    val isLoading: Boolean   = false,
    val isOffline: Boolean   = false,
    val lastSyncTime: Long   = 0,
    val error: String?       = null
)

class DevicesViewModel(
    private val deviceRepository: DeviceRepository,
    private val socketRepository: SocketRepository,
    private val userPreferences: UserPreferences,
    private val localRepository: LocalDeviceRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DevicesUiState())
    val uiState: StateFlow<DevicesUiState> = _uiState.asStateFlow()

    init {
        // Collect từ Room Flow để UI luôn cập nhật khi DB thay đổi
        viewModelScope.launch {
            localRepository.allDevices.collect { entities ->
                val devices = entities.map { it.toDomain() }
                _uiState.update { s ->
                    s.copy(
                        lights    = devices.filter { d -> d.type.equals("light", ignoreCase = true) },
                        fans      = devices.filter { d -> d.type.equals("fan", ignoreCase = true) },
                        doors     = devices.filter { d -> d.type.equals("door", ignoreCase = true) },
                        buzzers   = devices.filter { d -> d.type.equals("buzzer", ignoreCase = true) },
                        sensors   = devices.filter { d -> d.type.equals("sensor", ignoreCase = true) }
                    )
                }
            }
        }

        loadDevices()
        viewModelScope.launch {
            socketRepository.events.collect { event ->
                when (event) {
                    is SocketEvent.DeviceUpdate -> {
                        val data = event.data
                        val deviceId = event.deviceId
                        val type = event.type
                        
                        val newStatus = when (type) {
                            "light", "buzzer" -> {
                                data.optString("state", "off").uppercase()
                            }
                            "fan" -> {
                                val state = data.optString("state", "off").uppercase()
                                if (state == "ON") {
                                    data.optInt("speed", 1).toString()
                                } else "OFF"
                            }
                            "door_lock" -> {
                                data.optString("state", "locked").uppercase()
                            }
                            else -> data.optString("state", "OFF").uppercase()
                        }
                        
                        // Cập nhật vào Database thay vì chỉ UI
                        updateDeviceInDatabase(deviceId, newStatus)
                    }
                    else -> {}
                }
            }
        }
    }

    private fun updateDeviceInDatabase(id: Int, status: String) {
        viewModelScope.launch {
            // Lấy thiết bị hiện tại từ DB để giữ các thông tin khác
            localRepository.allDevices.firstOrNull()?.find { it.id == id }?.let { current ->
                val updated = current.copy(status = status)
                localRepository.upsertDevices(listOf(updated))
            }
        }
    }

    fun loadDevices() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            deviceRepository.getAllDevices()
                .onSuccess { devices ->
                    // Lưu vào Room
                    localRepository.upsertDevices(devices.map { it.toEntity() })
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isOffline = false,
                            lastSyncTime = System.currentTimeMillis()
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { 
                        it.copy(
                            error = "Mất kết nối server. Đang dùng dữ liệu offline.", 
                            isLoading = false,
                            isOffline = true 
                        ) 
                    }
                }
        }
    }

    fun toggleLight(device: Device) {
        val newStatus = if (device.isOn) "OFF" else "ON"
        updateDeviceInDatabase(device.id, newStatus)
        viewModelScope.launch {
            deviceRepository.toggleLight(device.id, device.isOn)
                .onFailure { e ->
                    updateDeviceInDatabase(device.id, device.status)
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun setFanSpeed(device: Device, speed: Int) {
        val newStatus = if (speed > 0) speed.toString() else "OFF"
        updateDeviceInDatabase(device.id, newStatus)
        viewModelScope.launch {
            deviceRepository.setFanSpeed(device.id, speed)
                .onFailure { e ->
                    updateDeviceInDatabase(device.id, device.status)
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun toggleDoor(device: Device? = null) {
        val isCurrentlyUnlocked = device?.isOn ?: uiState.value.isMainDoorUnlocked
        val newUnlockState = !isCurrentlyUnlocked
        val newStatus = if (newUnlockState) "UNLOCKED" else "LOCKED"
        
        // Optimistic UI update
        if (device != null) {
            updateDeviceInDatabase(device.id, newStatus)
        } else {
            _uiState.update { it.copy(isMainDoorUnlocked = newUnlockState) }
        }

        viewModelScope.launch {
            // Sử dụng ID mặc định cho cửa chính từ Preferences nếu không truyền device cụ thể
            val targetId = device?.id ?: UserPreferences.DEFAULT_MAIN_DOOR_ID
            deviceRepository.controlDoor(targetId, newUnlockState)
                .onFailure { e ->
                    // Rollback on failure
                    if (device != null) {
                        updateDeviceInDatabase(device.id, device.status)
                    } else {
                        _uiState.update { it.copy(isMainDoorUnlocked = isCurrentlyUnlocked) }
                    }
                    _uiState.update { it.copy(error = "Lỗi điều khiển cửa: ${e.message}") }
                }
        }
    }

    fun toggleBuzzer(device: Device) {
        val newStatus = if (device.isOn) "OFF" else "ON"
        updateDeviceInDatabase(device.id, newStatus)
        viewModelScope.launch {
            deviceRepository.controlBuzzer(device.id, !device.isOn)
                .onFailure { e ->
                    updateDeviceInDatabase(device.id, device.status)
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun turnOnAllLights() {
        viewModelScope.launch {
            deviceRepository.turnOnAllLights()
                .onSuccess { loadDevices() }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun turnOffAllLights() {
        viewModelScope.launch {
            deviceRepository.turnOffAllLights()
                .onSuccess { loadDevices() }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun clearError() { _uiState.update { it.copy(error = null) } }

    private fun Device.toEntity() = DeviceEntity(
        id = id,
        name = name,
        type = type,
        status = status,
        roomId = roomId,
        pin = pin,
        timestamp = timestamp
    )

    private fun DeviceEntity.toDomain() = com.voiceai.client.data.model.Device(
        id = id,
        name = name,
        type = type,
        status = status,
        roomId = roomId,
        pin = pin,
        timestamp = timestamp
    )
}