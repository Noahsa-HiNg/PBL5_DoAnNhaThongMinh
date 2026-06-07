package com.voiceai.client.ui.alarms

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.model.*
import com.voiceai.client.data.network.ScheduleRepository
import com.voiceai.client.data.network.SocketEvent
import com.voiceai.client.data.network.SocketRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class SchedulesUiState(
    val schedules: List<Schedule> = emptyList(),
    val devices: List<ScheduleDevice> = emptyList(),
    val isLoading: Boolean = false,
    val isSending: Boolean = false,
    val error: String? = null,
    val showAddDialog: Boolean = false
)

class SchedulesViewModel(
    private val scheduleRepository: ScheduleRepository,
    private val socketRepository: SocketRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SchedulesUiState())
    val uiState: StateFlow<SchedulesUiState> = _uiState.asStateFlow()

    init {
        loadSchedules()
        loadDevices()
        observeSocketEvents()
    }

    private fun observeSocketEvents() {
        viewModelScope.launch {
            socketRepository.events.collect { event ->
                when (event) {
                    is SocketEvent.ScheduleUpdated -> {
                        loadSchedules()
                    }
                    is SocketEvent.Connected -> {
                        // Tự động xóa lỗi và tải lại dữ liệu khi có kết nối mới thành công
                        _uiState.update { it.copy(error = null) }
                        loadSchedules()
                        loadDevices()
                    }
                    is SocketEvent.Error -> {
                        _uiState.update { it.copy(error = event.message) }
                    }
                    else -> {}
                }
            }
        }
    }

    fun loadSchedules() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            scheduleRepository.getActiveSchedules()
                .onSuccess { response ->
                    _uiState.update { it.copy(schedules = response.data.schedules, isLoading = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message, isLoading = false) }
                }
        }
    }

    fun loadDevices() {
        viewModelScope.launch {
            scheduleRepository.getScheduleDevices()
                .onSuccess { response ->
                    _uiState.update { it.copy(devices = response.data.devices) }
                }
        }
    }

    fun setSchedule(deviceName: String, command: String, time: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSending = true) }
            scheduleRepository.setSchedule(ScheduleSetRequest(deviceName, command, time))
                .onSuccess {
                    _uiState.update { it.copy(isSending = false, showAddDialog = false) }
                    // Socket will trigger refresh
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message, isSending = false) }
                }
        }
    }

    fun setTimer(deviceName: String, command: String, delayMinutes: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSending = true) }
            scheduleRepository.setTimer(TimerSetRequest(deviceName, command, delayMinutes))
                .onSuccess {
                    _uiState.update { it.copy(isSending = false, showAddDialog = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message, isSending = false) }
                }
        }
    }

    fun setBatchSchedule(deviceType: String, command: String, delayMinutes: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSending = true) }
            scheduleRepository.setBatchSchedule(BatchScheduleRequest(deviceType, command, delayMinutes))
                .onSuccess {
                    _uiState.update { it.copy(isSending = false, showAddDialog = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message, isSending = false) }
                }
        }
    }

    fun cancelSchedule(scheduleId: Int) {
        viewModelScope.launch {
            scheduleRepository.cancelSchedule(scheduleId)
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun cancelAllSchedules() {
        viewModelScope.launch {
            scheduleRepository.cancelAllSchedules()
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun showAddDialog() { _uiState.update { it.copy(showAddDialog = true) } }
    fun dismissAddDialog() { _uiState.update { it.copy(showAddDialog = false) } }
    fun clearError() { _uiState.update { it.copy(error = null) } }
}
