package com.voiceai.client.data.local

import com.voiceai.client.data.local.dao.DeviceDao
import com.voiceai.client.data.local.entity.DeviceEntity
import kotlinx.coroutines.flow.Flow

class LocalDeviceRepository(private val deviceDao: DeviceDao) {
    val allDevices: Flow<List<DeviceEntity>> = deviceDao.getAllDevices()

    suspend fun upsertDevices(devices: List<DeviceEntity>) {
        deviceDao.upsertDevices(devices)
    }

    suspend fun deleteDevice(device: DeviceEntity) {
        deviceDao.deleteDevice(device)
    }

    suspend fun getDeviceById(id: Int): DeviceEntity? {
        return deviceDao.getDeviceById(id)
    }
}
