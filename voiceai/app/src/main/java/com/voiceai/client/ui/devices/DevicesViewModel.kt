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
                        val newStatus = event.data.optString("state", "").uppercase()
                            .ifEmpty { event.data.optInt("speed", 0).toString() }
                        updateDeviceStatus(event.deviceId, newStatus)
                    }
                    is SocketEvent.SensorUpdate -> {
                        // Cập nhật giá trị cảm biến trong list sensors
                        _uiState.update { s ->
                            s.copy(sensors = s.sensors.map { 
                                if (it.id == event.deviceId) {
                                    // Giả sử Device model có field để chứa dữ liệu sensor phức tạp hoặc ta map vào status
                                    val sensorText = if (event.type == "dht11") {
                                        "${event.data.optDouble("temperature")}°C - ${event.data.optDouble("humidity")}%"
                                    } else {
                                        event.data.optString("light_value")
                                    }
                                    it.copy(status = sensorText)
                                } else it
                            })
                        }
                    }
                    else -> {}
                }
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
        updateDeviceStatus(device.id, newStatus)
        viewModelScope.launch {
            deviceRepository.toggleLight(device.id, device.isOn)
                .onFailure { e ->
                    updateDeviceStatus(device.id, device.status)
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun setFanSpeed(device: Device, speed: Int) {
        updateDeviceStatus(device.id, speed.toString())
        viewModelScope.launch {
            deviceRepository.setFanSpeed(device.id, speed)
                .onFailure { e ->
                    updateDeviceStatus(device.id, device.status)
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun toggleDoor(device: Device? = null) {
        val isCurrentlyUnlocked = device?.isOn ?: uiState.value.isMainDoorUnlocked
        val newUnlockState = !isCurrentlyUnlocked
        
        // Optimistic UI update
        if (device != null) {
            updateDeviceStatus(device.id, if (newUnlockState) "unlocked" else "locked")
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
                        updateDeviceStatus(device.id, device.status)
                    } else {
                        _uiState.update { it.copy(isMainDoorUnlocked = isCurrentlyUnlocked) }
                    }
                    _uiState.update { it.copy(error = "Lỗi điều khiển cửa: ${e.message}") }
                }
        }
    }

    fun toggleBuzzer(device: Device) {
        val newStatus = if (device.isOn) "OFF" else "ON"
        updateDeviceStatus(device.id, newStatus)
        viewModelScope.launch {
            deviceRepository.controlBuzzer(device.id, !device.isOn)
                .onFailure { e ->
                    updateDeviceStatus(device.id, device.status)
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

    private fun updateDeviceStatus(id: Int, newStatus: String) {
        _uiState.update { s ->
            s.copy(
                lights = s.lights.map { if (it.id == id) it.copy(status = newStatus) else it },
                fans   = s.fans.map   { if (it.id == id) it.copy(status = newStatus) else it },
                doors  = s.doors.map  { if (it.id == id) it.copy(status = newStatus) else it },
                buzzers = s.buzzers.map { if (it.id == id) it.copy(status = newStatus) else it }
            )
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