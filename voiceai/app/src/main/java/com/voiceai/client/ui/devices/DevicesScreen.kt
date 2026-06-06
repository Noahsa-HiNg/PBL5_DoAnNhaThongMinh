package com.voiceai.client.ui.devices

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.voiceai.client.data.model.Device

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicesScreen(viewModel: DevicesViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.error) {
        uiState.error?.let {
            snackbarHostState.showSnackbar(it, withDismissAction = true)
            viewModel.clearError()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Thiết bị") },
                actions = {
                    IconButton(onClick = { viewModel.loadDevices() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Tải lại")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        if (uiState.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // ── Banner offline ──────────────────────────
            if (uiState.isOffline && uiState.lastSyncTime > 0) {
                val timeStr = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                    .format(java.util.Date(uiState.lastSyncTime))
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.small
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Default.CloudOff, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.error)
                        Text(
                            text = "Dữ liệu offline — cập nhật lúc $timeStr",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                    }
                }
            }

            // ── Section Đèn ──────────────────────────────
            if (uiState.lights.isNotEmpty()) {
                DeviceSection(
                    title = "💡 Đèn",
                    actions = {
                        TextButton(onClick = { viewModel.turnOnAllLights() }) { Text("Bật tất cả") }
                        TextButton(onClick = { viewModel.turnOffAllLights() }) { Text("Tắt tất cả") }
                    }
                ) {
                    uiState.lights.forEach { light ->
                        LightCard(device = light, onToggle = { viewModel.toggleLight(light) })
                    }
                }
            }

            // ── Section Quạt ─────────────────────────────
            if (uiState.fans.isNotEmpty()) {
                DeviceSection(title = "🌀 Quạt") {
                    uiState.fans.forEach { fan ->
                        FanCard(device = fan, onSpeedChange = { speed -> viewModel.setFanSpeed(fan, speed) })
                    }
                }
            }

            // ── Section Cửa ──────────────────────────────
            DeviceSection(title = "🚪 Cửa") {
                if (uiState.doors.isNotEmpty()) {
                    uiState.doors.forEach { door ->
                        DoorCard(device = door, onToggle = { viewModel.toggleDoor(door) })
                    }
                } else {
                    // Hiển thị nút điều khiển Cửa chính nếu không có thiết bị cụ thể nào được tìm thấy
                    MainDoorCard(
                        isUnlocked = uiState.isMainDoorUnlocked,
                        onToggle = { viewModel.toggleDoor(null) }
                    )
                }
            }

            // ── Section Loa ──────────────────────────────
            if (uiState.buzzers.isNotEmpty()) {
                DeviceSection(title = "🔊 Cảnh báo") {
                    uiState.buzzers.forEach { buzzer ->
                        BuzzerCard(device = buzzer, onToggle = { viewModel.toggleBuzzer(buzzer) })
                    }
                }
            }

            // ── Section Cảm biến ──────────────────────────
            if (uiState.sensors.isNotEmpty()) {
                DeviceSection(title = "🌡️ Cảm biến") {
                    uiState.sensors.forEach { sensor ->
                        SensorCard(device = sensor)
                    }
                }
            }

            if (uiState.lights.isEmpty() && uiState.fans.isEmpty() && uiState.doors.isEmpty() && uiState.buzzers.isEmpty() && uiState.sensors.isEmpty()) {
                EmptyState(onRetry = { viewModel.loadDevices() })
            }
        }
    }
}

@Composable
private fun DeviceSection(
    title: String,
    actions: (@Composable RowScope.() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            actions?.invoke(this)
        }
        content()
    }
}

@Composable
private fun LightCard(device: Device, onToggle: () -> Unit) {
    val containerColor by animateColorAsState(
        targetValue = if (device.isOn) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
        label = "light_card_color"
    )

    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = containerColor), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.LightbulbCircle, null, modifier = Modifier.size(28.dp), tint = if (device.isOn) Color(0xFFFFC107) else MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(device.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                Text(device.displayStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(checked = device.isOn, onCheckedChange = { onToggle() })
        }
    }
}

@Composable
private fun FanCard(device: Device, onSpeedChange: (Int) -> Unit) {
    val isOn = device.isOn
    val containerColor by animateColorAsState(
        targetValue = if (isOn) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant,
        label = "fan_card_color"
    )

    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = containerColor), modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Air, null, modifier = Modifier.size(28.dp), tint = if (isOn) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(device.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                    Text(device.displayStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                listOf(0 to "Tắt", 1 to "1", 2 to "2", 3 to "Max").forEach { (speed, label) ->
                    FilterChip(selected = device.fanSpeed == speed, onClick = { onSpeedChange(speed) }, label = { Text(label) }, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun DoorCard(device: Device, onToggle: () -> Unit) {
    val isOpen = device.isOn
    val containerColor by animateColorAsState(
        targetValue = if (isOpen) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.surfaceVariant,
        label = "door_card_color"
    )

    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = containerColor), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(if (isOpen) Icons.Default.MeetingRoom else Icons.Default.DoorBack, null, modifier = Modifier.size(28.dp), tint = if (isOpen) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(device.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                Text(device.displayStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Button(
                onClick = onToggle,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isOpen) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                )
            ) {
                Text(if (isOpen) "Khóa" else "Mở")
            }
        }
    }
}

@Composable
private fun MainDoorCard(isUnlocked: Boolean, onToggle: () -> Unit) {
    val containerColor by animateColorAsState(
        targetValue = if (isUnlocked) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.surfaceVariant,
        label = "main_door_card_color"
    )

    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = containerColor), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if (isUnlocked) Icons.Default.MeetingRoom else Icons.Default.DoorBack,
                null,
                modifier = Modifier.size(28.dp),
                tint = if (isUnlocked) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("Cửa chính", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                Text(
                    if (isUnlocked) "Đang mở khóa" else "Đang khóa",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Button(
                onClick = onToggle,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isUnlocked) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                )
            ) {
                Text(if (isUnlocked) "Khóa" else "Mở")
            }
        }
    }
}

@Composable
private fun BuzzerCard(device: Device, onToggle: () -> Unit) {
    val isOn = device.isOn
    val containerColor by animateColorAsState(
        targetValue = if (isOn) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.surfaceVariant,
        label = "buzzer_card_color"
    )

    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = containerColor), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.VolumeUp, null, modifier = Modifier.size(28.dp), tint = if (isOn) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(device.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                Text(device.displayStatus, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(checked = isOn, onCheckedChange = { onToggle() })
        }
    }
}

@Composable
private fun SensorCard(device: Device) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            val icon = when {
                device.name.contains("nhiệt", true) -> Icons.Default.Thermostat
                device.name.contains("ẩm", true) -> Icons.Default.WaterDrop
                device.name.contains("sáng", true) -> Icons.Default.WbSunny
                else -> Icons.Default.Sensors
            }
            Icon(icon, null, modifier = Modifier.size(32.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(device.name, style = MaterialTheme.typography.bodyMedium)
                Text(text = device.status, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            }
            if (device.timestamp != null) {
                Text(text = device.timestamp.takeLast(8), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
            }
        }
    }
}

@Composable
private fun EmptyState(onRetry: () -> Unit) {
    Box(modifier = Modifier.fillMaxWidth().height(300.dp), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Default.DevicesOther, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outlineVariant)
            Spacer(Modifier.height(12.dp))
            Text("Không tìm thấy thiết bị", color = MaterialTheme.colorScheme.outline)
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = onRetry) { Text("Thử lại") }
        }
    }
}