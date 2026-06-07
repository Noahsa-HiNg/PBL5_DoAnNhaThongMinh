package com.voiceai.client.ui.alarms

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import com.voiceai.client.data.model.ScheduleDevice

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SchedulesScreen(viewModel: SchedulesViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.error) {
        uiState.error?.let {
            snackbarHostState.showSnackbar(it, withDismissAction = true)
            viewModel.clearError()
        }
    }

    if (uiState.showAddDialog) {
        AddScheduleDialog(
            devices = uiState.devices,
            isSending = uiState.isSending,
            onDismiss = { viewModel.dismissAddDialog() },
            onCreateSchedule = { name, cmd, time -> viewModel.setSchedule(name, cmd, time) },
            onCreateTimer = { name, cmd, delay -> viewModel.setTimer(name, cmd, delay) }
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
                    EmptySchedulesState(onAdd = { viewModel.showAddDialog() })
                }
                else -> {
                    LazyColumn(
                        contentPadding = PaddingValues(vertical = 8.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(uiState.schedules, key = { it.id }) { schedule ->
                            ScheduleItem(
                                schedule = schedule,
                                onCancel = { viewModel.cancelSchedule(schedule.id) }
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
                text = schedule.triggerTime.replace(" ", "\n"),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium
            )
        },
        supportingContent = {
            Column {
                Text(schedule.deviceName, style = MaterialTheme.typography.bodyMedium)
                AssistChip(
                    onClick = {},
                    label = { Text(schedule.command, style = MaterialTheme.typography.labelSmall) },
                    modifier = Modifier.height(24.dp)
                )
            }
        },
        leadingContent = {
            Icon(Icons.Default.Schedule, null, tint = MaterialTheme.colorScheme.primary)
        },
        trailingContent = {
            IconButton(onClick = onCancel) {
                Icon(Icons.Default.Cancel, contentDescription = "Hủy", tint = MaterialTheme.colorScheme.error)
            }
        }
    )
    HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp))
}

@Composable
private fun EmptySchedulesState(onAdd: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.AlarmOff, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outlineVariant)
        Spacer(Modifier.height(12.dp))
        Text("Chưa có lịch hẹn nào", color = MaterialTheme.colorScheme.outline)
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = onAdd) { Text("Thêm lịch hẹn") }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddScheduleDialog(
    devices: List<ScheduleDevice>,
    isSending: Boolean,
    onDismiss: () -> Unit,
    onCreateSchedule: (String, String, String) -> Unit,
    onCreateTimer: (String, String, Int) -> Unit
) {
    var selectedDevice by remember { mutableStateOf<ScheduleDevice?>(null) }
    var command by remember { mutableStateOf("ON") }
    var timeText by remember { mutableStateOf("") }
    var delayText by remember { mutableStateOf("") }
    var isTimerMode by remember { mutableStateOf(false) }
    var expanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isTimerMode) "Hẹn giờ sau phút" else "Đặt lịch hẹn") },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Mode Toggle
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Hẹn giờ sau phút", modifier = Modifier.weight(1f))
                    Switch(checked = isTimerMode, onCheckedChange = { isTimerMode = it })
                }

                // Device Dropdown
                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { expanded = !expanded }
                ) {
                    OutlinedTextField(
                        value = selectedDevice?.deviceName ?: "Chọn thiết bị",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Thiết bị") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = expanded,
                        onDismissRequest = { expanded = false }
                    ) {
                        devices.forEach { device ->
                            DropdownMenuItem(
                                text = { Text(device.deviceName) },
                                onClick = {
                                    selectedDevice = device
                                    expanded = false
                                }
                            )
                        }
                    }
                }

                // Command Toggle
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

                if (isTimerMode) {
                    OutlinedTextField(
                        value = delayText,
                        onValueChange = { delayText = it },
                        label = { Text("Số phút chờ") },
                        placeholder = { Text("15") },
                        modifier = Modifier.fillMaxWidth()
                    )
                } else {
                    OutlinedTextField(
                        value = timeText,
                        onValueChange = { timeText = it },
                        label = { Text("Thời gian (YYYY-MM-DD HH:MM:SS)") },
                        placeholder = { Text("2026-06-08 07:00:00") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val deviceName = selectedDevice?.deviceName ?: return@Button
                    if (isTimerMode) {
                        val delay = delayText.toIntOrNull() ?: return@Button
                        onCreateTimer(deviceName, command, delay)
                    } else {
                        if (timeText.isBlank()) return@Button
                        onCreateSchedule(deviceName, command, timeText)
                    }
                },
                enabled = !isSending && selectedDevice != null
            ) {
                if (isSending) CircularProgressIndicator(Modifier.size(16.dp))
                else Text("Tạo")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Hủy") }
        }
    )
}
