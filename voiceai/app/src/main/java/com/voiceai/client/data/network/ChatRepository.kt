package com.voiceai.client.data.network

import com.voiceai.client.data.model.ConversationHistoryResponse
import com.voiceai.client.data.model.VoiceMessageRequest
import com.voiceai.client.data.model.VoiceMessageResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

class ChatRepository(private val apiService: ApiService) {

    suspend fun sendVoiceMessage(message: String): Result<VoiceMessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.sendVoiceMessage(VoiceMessageRequest(message)) }
    }

    suspend fun uploadAudio(file: java.io.File): Result<VoiceMessageResponse> = withContext(Dispatchers.IO) {
        runCatching {
            // Server mong muốn .wav hoặc .flac, file từ AudioRepository thường là .wav
            val requestFile = file.asRequestBody("audio/wav".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
            apiService.uploadAudio(body)
        }
    }

    suspend fun getConversations(limit: Int = 100): Result<ConversationHistoryResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.getConversations(limit) }
    }
}
