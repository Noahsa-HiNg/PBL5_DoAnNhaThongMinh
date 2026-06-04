package com.voiceai.client.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.network.ApiService
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.preferences.UserPreferences
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

// ── UiState — đây là single source of truth, SettingsScreen chỉ đọc từ đây ──
data class SettingsUiState(
    val currentIp: String          = "",      // IP đang dùng, hiện ở InfoRow
    val currentPort: Int           = 8000,    // Port đang dùng
    val inputIp: String            = "",      // giá trị đang nhập trong TextField
    val inputPort: String          = "8000",  // port đang nhập
    val isSaved: Boolean           = false,   // trigger snackbar "Đã lưu"
    val isCheckingHealth: Boolean  = false,   // loading indicator nút Kiểm tra
    val healthStatus: HealthStatus? = null,   // badge kết quả health check
    val error: String?             = null     // trigger snackbar lỗi
)

data class HealthStatus(
    val isOnline: Boolean,
    val message: String
)

class SettingsViewModel(
    private val userPreferences: UserPreferences,
    private val socketRepository: SocketRepository,
    private val apiService: ApiService
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        SettingsUiState(
            currentIp = userPreferences.serverIp,
            currentPort = userPreferences.serverPort,
            inputIp   = userPreferences.serverIp,
            inputPort = userPreferences.serverPort.toString()
        )
    )
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    fun onIpChange(newIp: String) {
        _uiState.update { it.copy(inputIp = newIp, isSaved = false) }
    }

    fun onPortChange(newPort: String) {
        _uiState.update { it.copy(inputPort = newPort, isSaved = false) }
    }

    fun saveAndReconnect() {
        val newIp = _uiState.value.inputIp.trim()
        val newPort = _uiState.value.inputPort.toIntOrNull() ?: 8000
        if (newIp.isBlank()) return
        userPreferences.serverIp = newIp
        userPreferences.serverPort = newPort
        _uiState.update { it.copy(currentIp = newIp, currentPort = newPort, isSaved = true, healthStatus = null) }
        socketRepository.reconnect()
    }

    fun checkHealth() {
        viewModelScope.launch {
            _uiState.update { it.copy(isCheckingHealth = true, healthStatus = null, error = null) }
            runCatching { apiService.getRoot() }
                .onSuccess { response ->
                    _uiState.update {
                        it.copy(
                            isCheckingHealth = false,
                            healthStatus = HealthStatus(
                                isOnline = true,
                                message  = response.message
                            )
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            isCheckingHealth = false,
                            error = "Không kết nối được: ${e.message}",
                            healthStatus = HealthStatus(isOnline = false, message = "Server offline")
                        )
                    }
                }
        }
    }

    fun dismissSnackbar() {
        _uiState.update { it.copy(isSaved = false, error = null) }
    }
}