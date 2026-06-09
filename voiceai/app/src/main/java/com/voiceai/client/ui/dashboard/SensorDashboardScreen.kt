package com.voiceai.client.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.*
import com.voiceai.client.data.local.entity.SensorReadingEntity
import org.koin.androidx.compose.koinViewModel
import java.util.Locale

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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Current Values Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                ModernSensorCard(
                    label = "Nhiệt độ",
                    value = currentTemp?.let { String.format(Locale.US, "%.1f°C", it) } ?: "--",
                    icon = Icons.Default.Thermostat,
                    colors = listOf(Color(0xFFFF8A65), Color(0xFFE57373)),
                    modifier = Modifier.weight(1f)
                )
                ModernSensorCard(
                    label = "Độ ẩm",
                    value = currentHumid?.let { String.format(Locale.US, "%.1f%%", it) } ?: "--",
                    icon = Icons.Default.WaterDrop,
                    colors = listOf(Color(0xFF64B5F6), Color(0xFF42A5F5)),
                    modifier = Modifier.weight(1f)
                )
                ModernSensorCard(
                    label = "Ánh sáng",
                    value = currentLight?.let { String.format(Locale.US, "%d lx", it.toInt()) } ?: "--",
                    icon = Icons.Default.WbSunny,
                    colors = listOf(Color(0xFFFFD54F), Color(0xFFFFB300)),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text("Lịch sử Nhiệt độ & Độ ẩm", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Card(
                modifier = Modifier.fillMaxWidth().height(250.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                TemperatureHumidityChart(tempHumidHistory)
            }

            Text("Lịch sử Ánh sáng", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Card(
                modifier = Modifier.fillMaxWidth().height(250.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                LightBarChart(lightHistory)
            }
        }
    }
}

@Composable
fun ModernSensorCard(
    label: String,
    value: String,
    icon: ImageVector,
    colors: List<Color>,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent)
    ) {
        Box(
            modifier = Modifier
                .background(Brush.verticalGradient(colors))
                .padding(16.dp)
                .fillMaxWidth()
        ) {
            Column {
                Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(28.dp))
                Spacer(modifier = Modifier.height(12.dp))
                Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.ExtraBold, color = Color.White)
                Text(label, style = MaterialTheme.typography.labelMedium, color = Color.White.copy(alpha = 0.8f))
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
                legend.textColor = Color.Gray.toArgb()
            }
        },
        update = { chart ->
            val tempEntries = history.mapIndexed { index, entity ->
                Entry(index.toFloat(), entity.value1.toFloat())
            }
            val humidEntries = history.mapIndexed { index, entity ->
                Entry(index.toFloat(), (entity.value2 ?: 0.0).toFloat())
            }

            val tempDataSet = LineDataSet(tempEntries, "Nhiệt độ (°C)").apply {
                color = Color.Red.toArgb()
                setCircleColor(Color.Red.toArgb())
                lineWidth = 2f
                mode = LineDataSet.Mode.CUBIC_BEZIER
                setDrawValues(false)
            }
            val humidDataSet = LineDataSet(humidEntries, "Độ ẩm (%)").apply {
                color = Color.Blue.toArgb()
                setCircleColor(Color.Blue.toArgb())
                lineWidth = 2f
                mode = LineDataSet.Mode.CUBIC_BEZIER
                setDrawValues(false)
            }

            chart.data = LineData(tempDataSet, humidDataSet)
            chart.invalidate()
        },
        modifier = Modifier.fillMaxSize().padding(8.dp)
    )
}

@Composable
fun LightBarChart(history: List<SensorReadingEntity>) {
    AndroidView(
        factory = { context ->
            BarChart(context).apply {
                description.isEnabled = false
                xAxis.position = XAxis.XAxisPosition.BOTTOM
                axisRight.isEnabled = false
                legend.textColor = Color.Gray.toArgb()
            }
        },
        update = { chart ->
            val entries = history.mapIndexed { index, entity ->
                BarEntry(index.toFloat(), entity.value1.toFloat())
            }
            val dataSet = BarDataSet(entries, "Ánh sáng (Lux)").apply {
                color = Color(0xFFFFB300).toArgb()
                setDrawValues(false)
            }
            chart.data = BarData(dataSet)
            chart.invalidate()
        },
        modifier = Modifier.fillMaxSize().padding(8.dp)
    )
}
