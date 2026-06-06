package com.voiceai.client.data.local.dao

import androidx.room.*
import com.voiceai.client.data.local.entity.SensorReadingEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SensorReadingDao {
    @Query("SELECT * FROM sensor_readings WHERE deviceId = :deviceId ORDER BY recordedAt DESC")
    fun getReadingsByDevice(deviceId: Int): Flow<List<SensorReadingEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertReading(reading: SensorReadingEntity)

    @Query("DELETE FROM sensor_readings WHERE recordedAt < :timestamp")
    suspend fun deleteOldReadings(timestamp: Long)
}
