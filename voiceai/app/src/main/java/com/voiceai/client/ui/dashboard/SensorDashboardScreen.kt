package com.voiceai.client.ui.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import com.voiceai.client.data.local.entity.SensorReadingEntity
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SensorDashboardScreen(
    viewModel: SensorDashboardViewModel = koinViewModel()
) {
    val tempHumidHistory by viewModel.tempHumidHistory.collectAsState()
    val lightHistory by viewModel.lightHistory.collectAsState()
    val currentTemp by viewModel.currentTemp.collectAsState()
    val currentHumid by viewModel.currentHumid.collectAsState()
    val currentLight by viewModel.currentLight.collectAsState()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Cảm biến") }) }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            // Current Values Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                SensorValueCard(
                    label = "Nhiệt độ",
                    value = currentTemp?.let { "$it°C" } ?: "--",
                    icon = Icons.Default.Thermostat,
                    color = Color(0xFFE57373),
                    modifier = Modifier.weight(1f)
                )
                SensorValueCard(
                    label = "Độ ẩm",
                    value = currentHumid?.let { "$it%" } ?: "--",
                    icon = Icons.Default.WaterDrop,
                    color = Color(0xFF64B5F6),
                    modifier = Modifier.weight(1f)
                )
                SensorValueCard(
                    label = "Ánh sáng",
                    value = currentLight?.let { "$it lx" } ?: "--",
                    icon = Icons.Default.WbSunny,
                    color = Color(0xFFFFD54F),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text("Temperature & Humidity (Device 9)", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(250.dp)
            ) {
                TemperatureHumidityChart(tempHumidHistory)
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text("Light Level (Device 10)", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(250.dp)
            ) {
                LightBarChart(lightHistory)
            }
        }
    }
}

@Composable
fun TemperatureHumidityChart(history: List<SensorReadingEntity>) {
    AndroidView(
        factory = { context ->
            LineChart(context).apply {
                description.isEnabled = false
                setTouchEnabled(true)
                setPinchZoom(true)
                xAxis.position = XAxis.XAxisPosition.BOTTOM
                axisRight.isEnabled = false
            }
        },
        update = { chart ->
            val tempEntries = history.mapIndexed { index, entity ->
                Entry(index.toFloat(), entity.value1.toFloat())
            }
            val humidEntries = history.mapIndexed { index, entity ->
                Entry(index.toFloat(), (entity.value2 ?: 0.0).toFloat())
            }

            val tempDataSet = LineDataSet(tempEntries, "Temp (°C)").apply {
                color = Color.Red.toArgb()
                setCircleColor(Color.Red.toArgb())
                lineWidth = 2f
            }
            val humidDataSet = LineDataSet(humidEntries, "Humid (%)").apply {
                color = Color.Blue.toArgb()
                setCircleColor(Color.Blue.toArgb())
                lineWidth = 2f
            }

            chart.data = LineData(tempDataSet, humidDataSet)
            chart.invalidate()
        },
        modifier = Modifier.fillMaxSize().padding(8.dp)
    )
}

@Composable
fun SensorValueCard(
    label: String,
    value: String,
    icon: ImageVector,
    color: Color,
    modifier: Modifier = Modifier
) {
    ElevatedCard(
        modifier = modifier,
        colors = CardDefaults.elevatedCardColors(containerColor = color.copy(alpha = 0.1f))
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(24.dp))
            Spacer(modifier = Modifier.height(4.dp))
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = color)
        }
    }
}

@Composable
fun LightBarChart(history: List<SensorReadingEntity>) {
    AndroidView(
        factory = { context ->
            BarChart(context).apply {
                description.isEnabled = false
                xAxis.position = XAxis.XAxisPosition.BOTTOM
                axisRight.isEnabled = false
            }
        },
        update = { chart ->
            val entries = history.mapIndexed { index, entity ->
                BarEntry(index.toFloat(), entity.value1.toFloat())
            }
            val dataSet = BarDataSet(entries, "Light (Lux)").apply {
                color = Color.Yellow.toArgb()
            }
            chart.data = BarData(dataSet)
            chart.invalidate()
        },
        modifier = Modifier.fillMaxSize().padding(8.dp)
    )
}
