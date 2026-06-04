package com.voiceai.client.ui.chat

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.voiceai.client.data.model.ChatMessage

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(viewModel: ChatViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    ChatContent(
        uiState = uiState,
        onInputChange = viewModel::onInputTextChange,
        onSendText = viewModel::sendTextMessage,
        onMicPress = viewModel::startRecording,
        onMicRelease = viewModel::stopRecording,
        onRetryConnection = viewModel::retryConnection,
        onClearMessages = viewModel::clearMessages
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatContent(
    uiState: ChatUiState,
    onInputChange: (String) -> Unit,
    onSendText: () -> Unit,
    onMicPress: () -> Unit,
    onMicRelease: () -> Unit,
    onRetryConnection: () -> Unit,
    onClearMessages: () -> Unit
) {
    val listState = rememberLazyListState()
    val messages = uiState.messages
    val lastMessageText = messages.lastOrNull()?.text

    // Auto-scroll khi có message mới hoặc streaming
    LaunchedEffect(messages.size, lastMessageText) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("AI Assistant")
                        Spacer(Modifier.width(8.dp))
                        // Connection status dot
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(
                                    if (uiState.isConnected) Color(0xFF4CAF50) else Color(0xFFE53935)
                                )
                        )
                    }
                },
                actions = {
                    if (messages.isNotEmpty()) {
                        IconButton(onClick = onClearMessages) {
                            Icon(Icons.Default.Delete, contentDescription = "Xóa hội thoại")
                        }
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Connection error banner
            AnimatedVisibility(visible = uiState.connectionError != null) {
                uiState.connectionError?.let { error ->
                    Surface(
                        color = MaterialTheme.colorScheme.errorContainer,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.WifiOff,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onErrorContainer,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = "Mất kết nối. $error",
                                color = MaterialTheme.colorScheme.onErrorContainer,
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.weight(1f)
                            )
                            TextButton(onClick = onRetryConnection) {
                                Text("Kết nối lại", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }

            // Message list
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                if (messages.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier.fillParentMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(
                                    Icons.Default.SmartToy,
                                    contentDescription = null,
                                    modifier = Modifier.size(64.dp),
                                    tint = MaterialTheme.colorScheme.outlineVariant
                                )
                                Spacer(Modifier.height(12.dp))
                                Text(
                                    "Xin chào! Tôi có thể giúp gì cho bạn?",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.outline
                                )
                                Text(
                                    "Hãy gõ hoặc nhấn giữ mic để nói",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.outlineVariant
                                )
                            }
                        }
                    }
                }
                items(messages, key = { it.id }) { message ->
                    ChatBubble(message = message)
                }
            }

            // Input bar
            InputBar(
                text = uiState.inputText,
                isRecording = uiState.isRecording,
                isConnected = uiState.isConnected,
                onTextChange = onInputChange,
                onSend = onSendText,
                onMicPress = onMicPress,
                onMicRelease = onMicRelease
            )
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage) {
    val isFromUser = message.isFromUser
    val alpha by animateFloatAsState(
        targetValue = if (message.isStreaming) 0.75f else 1.0f,
        label = "bubble_alpha"
    )

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isFromUser) Alignment.End else Alignment.Start
    ) {
        Surface(
            modifier = Modifier.widthIn(max = 280.dp),
            shape = if (isFromUser) {
                RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp)
            } else {
                RoundedCornerShape(20.dp, 20.dp, 20.dp, 4.dp)
            },
            color = if (isFromUser)
                MaterialTheme.colorScheme.primary.copy(alpha = alpha)
            else
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = alpha)
        ) {
            Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                if (message.isStreaming && message.text.isEmpty()) {
                    TypingIndicator()
                } else {
                    Text(
                        text = message.text,
                        color = if (isFromUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
                
                // Hiển thị thời gian nhỏ ở góc
                message.timestamp?.let { ts ->
                    val displayTime = try { ts.substring(11, 16) } catch (e: Exception) { "" }
                    if (displayTime.isNotEmpty()) {
                        Text(
                            text = displayTime,
                            style = MaterialTheme.typography.labelSmall,
                            color = (if (isFromUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant).copy(alpha = 0.6f),
                            modifier = Modifier.align(Alignment.End).padding(top = 2.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TypingIndicator(modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "typing")
    Row(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        repeat(3) { index ->
            val offsetY by infiniteTransition.animateFloat(
                initialValue = 0f,
                targetValue = -6f,
                animationSpec = infiniteRepeatable(
                    animation = keyframes {
                        durationMillis = 900
                        0f at (index * 150)
                        -6f at (index * 150 + 200)
                        0f at (index * 150 + 400)
                    },
                    repeatMode = RepeatMode.Restart
                ),
                label = "dot_$index"
            )
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .offset(y = offsetY.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f))
            )
        }
    }
}

@Composable
private fun InputBar(
    text: String,
    isRecording: Boolean,
    isConnected: Boolean,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    onMicPress: () -> Unit,
    onMicRelease: () -> Unit
) {
    val hasText = text.isNotBlank()

    Surface(
        tonalElevation = 8.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 8.dp, vertical = 8.dp)
                .navigationBarsPadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = if (isRecording) "Đang nghe..." else text,
                onValueChange = onTextChange,
                placeholder = {
                    if (!isRecording) {
                        Text("Nhắn tin...", style = MaterialTheme.typography.bodyMedium)
                    }
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(24.dp),
                enabled = !isRecording,
                maxLines = 4,
                colors = OutlinedTextFieldDefaults.colors(
                    unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                    disabledTextColor = MaterialTheme.colorScheme.primary,
                    disabledBorderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)
                ),
                textStyle = if (isRecording) 
                    MaterialTheme.typography.bodyMedium.copy(
                        color = MaterialTheme.colorScheme.primary,
                        fontStyle = FontStyle.Italic
                    ) 
                else 
                    LocalTextStyle.current
            )

            Spacer(Modifier.width(8.dp))

                // Nút Send / Mic (chuyển đổi theo trạng thái)
                if (hasText) {
                    FilledIconButton(
                        onClick = onSend,
                        enabled = true
                    ) {
                        Icon(Icons.Default.Send, contentDescription = "Gửi")
                    }
                } else {
                    // Hold-to-Talk mic button - Dùng Box để tránh bị swallow gesture
                    val micColor by animateColorAsState(
                        targetValue = if (isRecording)
                            MaterialTheme.colorScheme.error
                        else
                            MaterialTheme.colorScheme.primary,
                        label = "mic_color"
                    )
                    
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(CircleShape)
                            .background(micColor)
                            .pointerInput(Unit) {
                                awaitPointerEventScope {
                                    while (true) {
                                        awaitFirstDown()
                                        onMicPress()
                                        waitForUpOrCancellation()
                                        onMicRelease()
                                    }
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            if (isRecording) Icons.Default.MicOff else Icons.Default.Mic,
                            contentDescription = if (isRecording) "Đang thu" else "Giữ để nói",
                            tint = Color.White
                        )
                    }
                }
        }
    }
}