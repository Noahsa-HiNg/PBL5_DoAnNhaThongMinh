package com.voiceai.client.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: SettingsViewModel) {
    // Đọc state từ ViewModel — tất cả field đều tồn tại trong SettingsUiState
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    // LaunchedEffect chỉ gọi suspend fun (showSnackbar) — KHÔNG gọi Composable ở đây
    LaunchedEffect(uiState.isSaved, uiState.error) {
        when {
            uiState.isSaved -> {
                snackbarHostState.showSnackbar("Đã lưu — đang kết nối lại...")
                viewModel.dismissSnackbar()
            }
            uiState.error != null -> {
                snackbarHostState.showSnackbar(
                    message       = uiState.error!!,
                    withDismissAction = true
                )
                viewModel.dismissSnackbar()
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Cài đặt") })
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ── Section: Kết nối Server ─────────────────────────────
            SettingsSection(title = "Kết nối Server") {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {

                    // Row cho IP và Port
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // TextField nhập IP
                        OutlinedTextField(
                            value = uiState.inputIp,
                            onValueChange = { viewModel.onIpChange(it) },
                            label = { Text("Địa chỉ IP server") },
                            placeholder = { Text("192.168.1.100") },
                            leadingIcon = { Icon(Icons.Default.Dns, contentDescription = null) },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                            modifier = Modifier.weight(0.7f)
                        )

                        // TextField nhập Port
                        OutlinedTextField(
                            value = uiState.inputPort,
                            onValueChange = { viewModel.onPortChange(it) },
                            label = { Text("Port") },
                            placeholder = { Text("8000") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(0.3f)
                        )
                    }

                    // 2 nút hành động
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick  = { viewModel.saveAndReconnect() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Save, contentDescription = null,
                                modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Lưu & Kết nối")
                        }

                        OutlinedButton(
                            onClick  = { viewModel.checkHealth() },
                            enabled  = !uiState.isCheckingHealth,
                            modifier = Modifier.weight(1f)
                        ) {
                            if (uiState.isCheckingHealth) {
                                CircularProgressIndicator(
                                    modifier    = Modifier.size(16.dp),
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Icon(Icons.Default.NetworkCheck, contentDescription = null,
                                    modifier = Modifier.size(16.dp))
                            }
                            Spacer(Modifier.width(6.dp))
                            Text("Kiểm tra")
                        }
                    }

                    // Health badge — chỉ hiện khi healthStatus != null
                    uiState.healthStatus?.let { health ->
                        Surface(
                            shape = MaterialTheme.shapes.medium,
                            color = if (health.isOnline)
                                MaterialTheme.colorScheme.secondaryContainer
                            else
                                MaterialTheme.colorScheme.errorContainer,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = if (health.isOnline)
                                        Icons.Default.CheckCircle
                                    else
                                        Icons.Default.Cancel,
                                    contentDescription = null,
                                    tint = if (health.isOnline)
                                        Color(0xFF4CAF50)
                                    else
                                        MaterialTheme.colorScheme.error
                                )
                                Column {
                                    Text(
                                        text  = if (health.isOnline) "Server online" else "Server offline",
                                        fontWeight = FontWeight.SemiBold,
                                        style = MaterialTheme.typography.bodyMedium
                                    )
                                    Text(
                                        text  = health.message,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSecondaryContainer
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // ── Section: Về ứng dụng ────────────────────────────────
            SettingsSection(title = "Về ứng dụng") {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    InfoRow(label = "Package",  value = "com.voiceai.client")
                    InfoRow(label = "Server",   value = "http://${uiState.currentIp}:${uiState.currentPort}")
                    InfoRow(label = "Realtime", value = "Socket.IO WebSocket")
                    InfoRow(label = "STT",      value = "Whisper (PC Server)")
                    InfoRow(label = "AI",       value = "LLM trên Raspberry Pi")
                    InfoRow(label = "Backend",  value = "FastAPI + SQLite + MQTT")
                }
            }
        }
    }
}

// ── Reusable composables ────────────────────────────────────────────────────

@Composable
private fun SettingsSection(
    title: String,
    content: @Composable ColumnScope.() -> Unit
) {
    Column {
        Text(
            text     = title,
            style    = MaterialTheme.typography.labelLarge,
            color    = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(bottom = 8.dp)
        )
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), content = content)
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(
            text     = label,
            modifier = Modifier.width(100.dp),
            style    = MaterialTheme.typography.bodySmall,
            color    = MaterialTheme.colorScheme.outline
        )
        Text(text = value, style = MaterialTheme.typography.bodySmall)
    }
}