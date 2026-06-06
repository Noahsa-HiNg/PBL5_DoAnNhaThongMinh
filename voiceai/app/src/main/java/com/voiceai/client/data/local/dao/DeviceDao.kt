package com.voiceai.client.data.local.dao

import androidx.room.*
import com.voiceai.client.data.local.entity.DeviceEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DeviceDao {
    @Query("SELECT * FROM devices")
    fun getAllDevices(): Flow<List<DeviceEntity>>

    @Query("SELECT * FROM devices WHERE id = :id")
    suspend fun getDeviceById(id: Int): DeviceEntity?

    @Upsert
    suspend fun upsertDevices(devices: List<DeviceEntity>)

    @Delete
    suspend fun deleteDevice(device: DeviceEntity)

    @Query("DELETE FROM devices")
    suspend fun deleteAllDevices()
}
