package com.voiceai.client.ui.alarms

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.model.AlarmRequest
import com.voiceai.client.data.model.Schedule
import com.voiceai.client.data.model.TimerRequest
import com.voiceai.client.data.network.AlarmRepository
import com.voiceai.client.data.network.SocketEvent
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.notification.NotificationHelper
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class AlarmsUiState(
    val schedules: List<Schedule> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val showAddDialog: Boolean = false,
    val triggeredAlarm: Pair<String, String>? = null  // label, time
)

class AlarmsViewModel(
    private val alarmRepository: AlarmRepository,
    private val socketRepository: SocketRepository,
    private val notificationHelper: NotificationHelper
) : ViewModel() {

    private val _uiState = MutableStateFlow(AlarmsUiState())
    val uiState: StateFlow<AlarmsUiState> = _uiState.asStateFlow()

    init {
        loadSchedules()
        viewModelScope.launch {
            socketRepository.events
                .filterIsInstance<SocketEvent.AlarmTriggered>()
                .collect { event ->
                    notificationHelper.showAlarmNotification(event.label, event.time)
                    _uiState.update { it.copy(triggeredAlarm = Pair(event.label, event.time)) }
                }
        }
    }

    fun loadSchedules() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            alarmRepository.getActiveSchedules()
                .onSuccess { schedules ->
                    _uiState.update { it.copy(schedules = schedules, isLoading = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message, isLoading = false) }
                }
        }
    }

    /** Đặt báo thức theo giờ cố định cho 1 thiết bị */
    fun setAlarm(deviceId: Int, command: String, time: String) {
        viewModelScope.launch {
            alarmRepository.setAlarm(AlarmRequest(deviceId, command, time))
                .onSuccess {
                    loadSchedules()
                    _uiState.update { it.copy(showAddDialog = false) }
                }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    /** Hẹn giờ sau N phút cho 1 thiết bị */
    fun setTimer(deviceId: Int, command: String, delayMinutes: Int) {
        viewModelScope.launch {
            alarmRepository.setTimer(TimerRequest(deviceId, command, delayMinutes))
                .onSuccess { loadSchedules() }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun cancelSchedule(scheduleId: Int) {
        viewModelScope.launch {
            alarmRepository.cancelSchedule(scheduleId)
                .onSuccess {
                    _uiState.update { s ->
                        s.copy(schedules = s.schedules.filter { it.schedule_id != scheduleId })
                    }
                }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun cancelAllSchedules() {
        viewModelScope.launch {
            alarmRepository.cancelAllSchedules()
                .onSuccess { _uiState.update { it.copy(schedules = emptyList()) } }
                .onFailure { e -> _uiState.update { it.copy(error = e.message) } }
        }
    }

    fun showAddDialog() { _uiState.update { it.copy(showAddDialog = true) } }
    fun dismissAddDialog() { _uiState.update { it.copy(showAddDialog = false) } }
    fun dismissTriggeredAlarm() { _uiState.update { it.copy(triggeredAlarm = null) } }
    fun clearError() { _uiState.update { it.copy(error = null) } }
}