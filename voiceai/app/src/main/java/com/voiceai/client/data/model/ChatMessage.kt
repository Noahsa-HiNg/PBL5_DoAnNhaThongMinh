package com.voiceai.client.data.model

import java.util.UUID

/**
 * Model đại diện cho một tin nhắn trong cuộc trò chuyện.
 *
 * @param id         Định danh duy nhất cho mỗi bubble. Dùng UUID để tránh conflict khi update.
 * @param text       Nội dung tin nhắn. Có thể thay đổi liên tục khi isStreaming = true.
 * @param isFromUser true = tin nhắn của người dùng, false = tin nhắn AI.
 * @param isStreaming true = đang stream (partial STT hoặc AI đang "gõ"), false = đã hoàn chỉnh.
 */
data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val isFromUser: Boolean,
    val isStreaming: Boolean = false,
    val timestamp: String? = null
)
