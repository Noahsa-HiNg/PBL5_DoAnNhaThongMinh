package com.voiceai.client.ui.chat

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.model.ChatMessage
import com.voiceai.client.data.model.ConversationItem
import com.voiceai.client.data.audio.AudioRepository
import com.voiceai.client.data.network.ChatRepository
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.preferences.UserPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val inputText: String = "",
    val isLoadingHistory: Boolean = false,
    val isSendingMessage: Boolean = false,
    val isRecording: Boolean = false,
    val isConnected: Boolean = false,
    val connectionError: String? = null,
    val error: String? = null
)

class ChatViewModel(
    private val chatRepository: ChatRepository,
    private val socketRepository: SocketRepository,
    private val audioRepository: AudioRepository,
    private val userPreferences: UserPreferences,
    private val ttsHelper: com.voiceai.client.data.audio.TtsHelper
) : ViewModel() {

    companion object {
        private const val TAG = "ChatViewModel"
    }

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var recordingJob: Job? = null

    init {
        loadConversationHistory()
        observeSocketEvents()
    }

    private fun observeSocketEvents() {
        viewModelScope.launch {
            socketRepository.events.collect { event ->
                when (event) {
                    is com.voiceai.client.data.network.SocketEvent.Connected -> {
                        _uiState.update { it.copy(isConnected = true, connectionError = null) }
                    }
                    is com.voiceai.client.data.network.SocketEvent.Disconnected -> {
                        _uiState.update { it.copy(isConnected = false) }
                    }
                    is com.voiceai.client.data.network.SocketEvent.Error -> {
                        _uiState.update { it.copy(connectionError = event.message) }
                    }
                    else -> { /* Handle other events if needed */ }
                }
            }
        }
        // Đảm bảo socket được kết nối
        socketRepository.connect()
    }

    fun loadConversationHistory() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingHistory = true, error = null) }
            chatRepository.getConversations().onSuccess { response ->
                val chatMessages = response.data.map { item ->
                    ChatMessage(
                        id = item.id.toString(),
                        text = item.message,
                        isFromUser = item.sender == "user",
                        timestamp = item.timestamp 
                    )
                }.sortedBy { it.timestamp }
                _uiState.update { it.copy(messages = chatMessages, isLoadingHistory = false) }
            }.onFailure { throwable ->
                _uiState.update { it.copy(error = throwable.message, isLoadingHistory = false) }
                Log.e(TAG, "Error loading conversation history: ", throwable)
            }
        }
    }

    fun onInputTextChange(newText: String) {
        _uiState.update { it.copy(inputText = newText) }
    }

    fun sendTextMessage() {
        val messageText = _uiState.value.inputText.trim()
        if (messageText.isEmpty()) return

        val userMessage = ChatMessage(
            text = messageText,
            isFromUser = true,
            timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
        )
        
        _uiState.update { it.copy(
            messages = it.messages + userMessage,
            inputText = "",
            isSendingMessage = true,
            error = null 
        ) }

        viewModelScope.launch {
            chatRepository.sendVoiceMessage(messageText).onSuccess { response ->
                val systemResponseText = response.reply
                val systemResponse = ChatMessage(
                    text = systemResponseText,
                    isFromUser = false,
                    timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
                )
                _uiState.update { it.copy(messages = it.messages + systemResponse, isSendingMessage = false, error = null) }
                
                if (userPreferences.ttsEnabled) {
                    ttsHelper.speak(systemResponseText)
                }
            }.onFailure { throwable ->
                val errorMessage = throwable.message ?: "Unknown error"
                _uiState.update { it.copy(error = errorMessage, isSendingMessage = false) }
                Log.e(TAG, "Error sending message: ", throwable)
            }
        }
    }

    fun clearMessages() {
        _uiState.update { it.copy(messages = emptyList()) }
    }

    fun retryLastAction() {
        _uiState.update { it.copy(error = null) }
        loadConversationHistory()
    }

    fun startRecording() {
        isRecordingCancelled = false
        _uiState.update { it.copy(isRecording = true, error = null) }
        
        recordingJob?.cancel()
        recordingJob = viewModelScope.launch(Dispatchers.IO) {
            try {
                val file = audioRepository.startRecording()
                if (file != null && !isRecordingCancelled) {
                    withContext(Dispatchers.Main) {
                        uploadAudioFile(file)
                    }
                } else if (file == null) {
                    // Nếu không khởi tạo được Mic
                    _uiState.update { it.copy(
                        isRecording = false, 
                        error = "Không thể khởi động Micro. Hãy kiểm tra quyền truy cập."
                    ) }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Recording error", e)
                _uiState.update { it.copy(isRecording = false, error = "Lỗi ghi âm: ${e.message}") }
            }
        }
    }

    private var isRecordingCancelled = false

    fun stopRecording() {
        audioRepository.stopRecording()
        _uiState.update { it.copy(isRecording = false) }
    }

    fun cancelRecording() {
        isRecordingCancelled = true
        audioRepository.stopRecording()
        _uiState.update { it.copy(isRecording = false) }
    }

    private fun uploadAudioFile(file: java.io.File) {
        _uiState.update { it.copy(isSendingMessage = true) }
        
        val tempId = UUID.randomUUID().toString()
        val userMessage = ChatMessage(
            id = tempId,
            text = "Đang xử lý âm thanh...",
            isFromUser = true,
            isStreaming = true,
            timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
        )
        _uiState.update { it.copy(messages = it.messages + userMessage) }

        viewModelScope.launch {
            chatRepository.uploadAudio(file).onSuccess { response ->
                val systemResponseText = response.reply
                val userResultText = response.transcript
                
                val systemResponse = ChatMessage(
                    text = systemResponseText,
                    isFromUser = false,
                    timestamp = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
                )
                
                _uiState.update { current ->
                    val updatedMessages = current.messages.map { msg ->
                        if (msg.id == tempId) {
                            msg.copy(text = userResultText, isStreaming = false)
                        } else msg
                    }
                    current.copy(
                        messages = updatedMessages + systemResponse,
                        isSendingMessage = false,
                        error = null
                    )
                }

                if (userPreferences.ttsEnabled) {
                    ttsHelper.speak(systemResponseText)
                }
            }.onFailure { throwable ->
                val errorMessage = throwable.message ?: "Lỗi gửi âm thanh"
                _uiState.update { current ->
                    val updatedMessages = current.messages.filter { it.id != tempId }
                    current.copy(
                        messages = updatedMessages,
                        error = errorMessage,
                        isSendingMessage = false
                    )
                }
                Log.e(TAG, "Error uploading audio: ", throwable)
            }
        }
    }

    fun retryConnection() {
        socketRepository.reconnect()
    }
}
