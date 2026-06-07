package com.voiceai.client.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.voiceai.client.data.local.dao.SensorReadingDao
import com.voiceai.client.data.local.entity.SensorReadingEntity
import com.voiceai.client.data.network.ApiService
import com.voiceai.client.data.network.SocketRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class SensorDashboardViewModel(
    private val apiService: ApiService,
    private val socketRepository: SocketRepository,
    private val sensorReadingDao: SensorReadingDao
) : ViewModel() {

    private val _tempHumidHistory = MutableStateFlow<List<SensorReadingEntity>>(emptyList())
    val tempHumidHistory: StateFlow<List<SensorReadingEntity>> = _tempHumidHistory.asStateFlow()

    private val _lightHistory = MutableStateFlow<List<SensorReadingEntity>>(emptyList())
    val lightHistory: StateFlow<List<SensorReadingEntity>> = _lightHistory.asStateFlow()

    private val _currentTemp = MutableStateFlow<Double?>(null)
    val currentTemp: StateFlow<Double?> = _currentTemp.asStateFlow()

    private val _currentHumid = MutableStateFlow<Double?>(null)
    val currentHumid: StateFlow<Double?> = _currentHumid.asStateFlow()

    private val _currentLight = MutableStateFlow<Double?>(null)
    val currentLight: StateFlow<Double?> = _currentLight.asStateFlow()

    init {
        observeSocketEvents()
        loadLocalData()
    }

    private fun observeSocketEvents() {
        viewModelScope.launch {
            socketRepository.events.collect { event ->
                if (event is com.voiceai.client.data.network.SocketEvent.SensorUpdate) {
                    val deviceId = event.deviceId
                    val dataObj = event.data
                    
                    val value1 = dataObj.optDouble("value1", 0.0)
                    val value2 = if (dataObj.isNull("value2")) null else dataObj.optDouble("value2")
                    val unit1 = dataObj.optString("unit1", "")
                    val unit2 = if (dataObj.isNull("unit2")) null else dataObj.optString("unit2")

                    val entity = SensorReadingEntity(
                        deviceId = deviceId,
                        value1 = value1,
                        value2 = value2,
                        unit1 = unit1,
                        unit2 = unit2
                    )

                    // Save to Room
                    sensorReadingDao.insertReading(entity)

                    // Update UI State (limit 50)
                    updateUiState(entity)
                    
                    // Update current values
                    if (deviceId == 9) {
                        _currentTemp.value = value1
                        _currentHumid.value = value2
                    } else if (deviceId == 10) {
                        _currentLight.value = value1
                    }
                }
            }
        }
    }

    private fun loadLocalData() {
        viewModelScope.launch {
            sensorReadingDao.getReadingsByDevice(9).take(1).collect { list ->
                _tempHumidHistory.value = list.take(50).reversed()
                list.firstOrNull()?.let {
                    _currentTemp.value = it.value1
                    _currentHumid.value = it.value2
                }
            }
            sensorReadingDao.getReadingsByDevice(10).take(1).collect { list ->
                _lightHistory.value = list.take(50).reversed()
                list.firstOrNull()?.let {
                    _currentLight.value = it.value1
                }
            }
        }
    }

    private fun updateUiState(entity: SensorReadingEntity) {
        if (entity.deviceId == 9) {
            _tempHumidHistory.value = (_tempHumidHistory.value + entity).takeLast(50)
        } else if (entity.deviceId == 10) {
            _lightHistory.value = (_lightHistory.value + entity).takeLast(50)
        }
    }

    fun loadHistory(deviceId: Int) {
        viewModelScope.launch {
            try {
                val response = apiService.getSensorHistory(deviceId)
                if (response.status == "success") {
                    val entities = response.data.map { dto ->
                        SensorReadingEntity(
                            deviceId = deviceId,
                            value1 = dto.value1 ?: 0.0,
                            value2 = dto.value2,
                            unit1 = if (deviceId == 9) "°C" else "lux",
                            unit2 = if (deviceId == 9) "%" else null,
                            // Simplification: parse timestamp or use current for now if format is tricky
                            recordedAt = System.currentTimeMillis() 
                        )
                    }
                    // Upsert to Room (dao insert handles replace)
                    entities.forEach { sensorReadingDao.insertReading(it) }
                    
                    // Refresh UI
                    if (deviceId == 9) _tempHumidHistory.value = entities.reversed()
                    else if (deviceId == 10) _lightHistory.value = entities.reversed()
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
