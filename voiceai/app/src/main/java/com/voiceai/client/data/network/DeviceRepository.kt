package com.voiceai.client.data.network

import com.voiceai.client.data.model.Device
import com.voiceai.client.data.model.DoorCommand
import com.voiceai.client.data.model.FanCommand
import com.voiceai.client.data.model.LightCommand
import com.voiceai.client.data.model.MessageResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class DeviceRepository(private val apiService: ApiService) {

    suspend fun getAllDevices(): Result<List<Device>> = withContext(Dispatchers.IO) {
        runCatching { 
            apiService.getAllDevices().data.devices 
        }
    }

    suspend fun turnOnLight(deviceId: Int): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.controlLight(deviceId, LightCommand("on")) }
    }

    suspend fun turnOffLight(deviceId: Int): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.controlLight(deviceId, LightCommand("off")) }
    }

    suspend fun toggleLight(deviceId: Int, currentlyOn: Boolean): Result<MessageResponse> {
        return if (currentlyOn) turnOffLight(deviceId) else turnOnLight(deviceId)
    }

    suspend fun turnOffAllLights(): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.controlAllLights(LightCommand("off")) }
    }

    suspend fun turnOnAllLights(): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.controlAllLights(LightCommand("on")) }
    }

    suspend fun setFanSpeed(deviceId: Int, speed: Int): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching {
            require(speed in 0..3) { "Tốc độ quạt phải từ 0 đến 3" }
            val state = if (speed > 0) "on" else "off"
            apiService.controlFan(deviceId, FanCommand(state, speed))
        }
    }

    suspend fun controlDoor(deviceId: Int, unlock: Boolean): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching {
            val action = if (unlock) "unlock" else "lock"
            apiService.controlDoor(deviceId, DoorCommand(action))
        }
    }

    suspend fun controlBuzzer(deviceId: Int, turnOn: Boolean): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching {
            val action = if (turnOn) "on" else "off"
            apiService.controlBuzzer(mapOf("action" to action))
        }
    }
}
