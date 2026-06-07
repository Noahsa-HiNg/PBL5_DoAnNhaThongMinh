package com.voiceai.client.data.network

import com.voiceai.client.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ScheduleRepository(private val apiService: ApiService) {

    suspend fun getScheduleDevices(): Result<ScheduleDevicesResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.getScheduleDevices() }
    }

    suspend fun getActiveSchedules(): Result<SchedulesResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.getActiveSchedules() }
    }

    suspend fun setSchedule(req: ScheduleSetRequest): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.setSchedule(req) }
    }

    suspend fun setTimer(req: TimerSetRequest): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.setTimer(req) }
    }

    suspend fun setBatchSchedule(req: BatchScheduleRequest): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.setBatchSchedule(req) }
    }

    suspend fun cancelSchedule(id: Int): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.cancelSchedule(id) }
    }

    suspend fun cancelAllSchedules(): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.cancelAllSchedules() }
    }
}
