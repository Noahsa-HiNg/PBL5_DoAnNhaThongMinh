package com.voiceai.client.data.network

import com.voiceai.client.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AlarmRepository(private val apiService: ApiService) {

    suspend fun getActiveSchedules(): Result<List<Schedule>> = withContext(Dispatchers.IO) {
        runCatching { apiService.getActiveSchedules() }
    }

    suspend fun setAlarm(req: AlarmRequest): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.setSchedule(req) }
    }

    suspend fun setTimer(req: TimerRequest): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.setTimer(req) }
    }

    suspend fun cancelSchedule(id: Int): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.cancelSchedule(id) }
    }

    suspend fun cancelAllSchedules(): Result<MessageResponse> = withContext(Dispatchers.IO) {
        runCatching { apiService.cancelAllSchedules() }
    }
}