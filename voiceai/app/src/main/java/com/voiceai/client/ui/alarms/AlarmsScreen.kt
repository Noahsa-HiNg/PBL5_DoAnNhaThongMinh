package com.voiceai.client.ui.alarms

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.voiceai.client.data.model.Schedule

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlarmsScreen(viewModel: AlarmsViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.error) {
        uiState.error?.let {
            snackbarHostState.showSnackbar(it, withDismissAction = true)
            viewModel.clearError()
        }
    }

    // Dialog báo thức triggered từ socket
    uiState.triggeredAlarm?.let { (label, time) ->
        AlertDialog(
            onDismissRequest = { viewModel.dismissTriggeredAlarm() },
            icon = { Icon(Icons.Default.Alarm, null) },
            title = { Text("⏰ Báo thức!") },
            text = { Text("$time — $label") },
            confirmButton = {
                TextButton(onClick = { viewModel.dismissTriggeredAlarm() }) { Text("Tắt") }
            }
        )
    }

    // Dialog thêm lịch hẹn mới
    if (uiState.showAddDialog) {
        AddScheduleDialog(
            onDismiss = { viewModel.dismissAddDialog() },
            onCreateAlarm = { deviceId, command, time ->
                viewModel.setAlarm(deviceId, command, time)
            },
            onCreateTimer = { deviceId, command, delayMin ->
                viewModel.setTimer(deviceId, command, delayMin)
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Hẹn giờ") },
                actions = {
                    if (uiState.schedules.isNotEmpty()) {
                        IconButton(onClick = { viewModel.cancelAllSchedules() }) {
                            Icon(Icons.Default.DeleteSweep, contentDescription = "Hủy tất cả")
                        }
                    }
                    IconButton(onClick = { viewModel.loadSchedules() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Tải lại")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.showAddDialog() }) {
                Icon(Icons.Default.Add, contentDescription = "Thêm lịch hẹn")
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        Box(Modifier.fillMaxSize().padding(paddingValues)) {
            when {
                uiState.isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                uiState.schedules.isEmpty() -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(Icons.Default.AlarmOff, null,
                            modifier = Modifier.size(64.dp),
                            tint = MaterialTheme.colorScheme.outlineVariant)
                        Text("Chưa có lịch hẹn nào",
                            color = MaterialTheme.colorScheme.outline)
                        OutlinedButton(onClick = { viewModel.showAddDialog() }) {
                            Text("Thêm lịch hẹn")
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        contentPadding = PaddingValues(vertical = 8.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(uiState.schedules, key = { it.schedule_id }) { schedule ->
                            ScheduleItem(
                                schedule = schedule,
                                onCancel = { viewModel.cancelSchedule(schedule.schedule_id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ScheduleItem(schedule: Schedule, onCancel: () -> Unit) {
    ListItem(
        headlineContent = {
            Text(
                // Chỉ hiện phần giờ HH:mm nếu có
                text = schedule.trigger_time.take(16),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium
            )
        },
        supportingContent = {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Thiết bị #${schedule.device_id}",
                    style = MaterialTheme.typography.bodySmall)
                AssistChip(
                    onClick = {},
                    label = { Text(schedule.command,
                        style = MaterialTheme.typography.labelSmall) },
                    modifier = Modifier.height(20.dp)
                )
            }
        },
        leadingContent = {
            Icon(Icons.Default.Schedule, null,
                tint = MaterialTheme.colorScheme.primary)
        },
        trailingContent = {
            IconButton(onClick = onCancel) {
                Icon(Icons.Default.Cancel, contentDescription = "Hủy",
                    tint = MaterialTheme.colorScheme.error)
            }
        }
    )
    HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))
}

@Composable
private fun AddScheduleDialog(
    onDismiss: () -> Unit,
    onCreateAlarm: (deviceId: Int, command: String, time: String) -> Unit,
    onCreateTimer: (deviceId: Int, command: String, delayMinutes: Int) -> Unit
) {
    var deviceIdText by remember { mutableStateOf("") }
    var command by remember { mutableStateOf("ON") }
    var timeText by remember { mutableStateOf("") }
    var delayText by remember { mutableStateOf("") }
    var isTimerMode by remember { mutableStateOf(false) } // false = alarm, true = timer

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.AddAlarm, null) },
        title = { Text(if (isTimerMode) "Hẹn giờ sau N phút" else "Đặt báo thức") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {

                // Toggle alarm/timer mode
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Hẹn giờ sau phút", modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyMedium)
                    Switch(checked = isTimerMode, onCheckedChange = { isTimerMode = it })
                }

                // Device ID
                OutlinedTextField(
                    value = deviceIdText,
                    onValueChange = { deviceIdText = it },
                    label = { Text("ID thiết bị") },
                    placeholder = { Text("1") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Command ON/OFF
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("ON", "OFF").forEach { cmd ->
                        FilterChip(
                            selected = command == cmd,
                            onClick = { command = cmd },
                            label = { Text(cmd) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                // Alarm: input giờ cụ thể | Timer: input số phút
                if (!isTimerMode) {
                    OutlinedTextField(
                        value = timeText,
                        onValueChange = { timeText = it },
                        label = { Text("Thời gian") },
                        placeholder = { Text("2025-01-01 07:30:00") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                } else {
                    OutlinedTextField(
                        value = delayText,
                        onValueChange = { delayText = it },
                        label = { Text("Sau bao nhiêu phút") },
                        placeholder = { Text("30") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val deviceId = deviceIdText.toIntOrNull() ?: return@TextButton
                    if (isTimerMode) {
                        val delay = delayText.toIntOrNull() ?: return@TextButton
                        onCreateTimer(deviceId, command, delay)
                    } else {
                        if (timeText.isBlank()) return@TextButton
                        onCreateAlarm(deviceId, command, timeText)
                    }
                },
                enabled = deviceIdText.toIntOrNull() != null &&
                        (if (isTimerMode) delayText.toIntOrNull() != null
                        else timeText.isNotBlank())
            ) { Text("Tạo") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Hủy") }
        }
    )
}