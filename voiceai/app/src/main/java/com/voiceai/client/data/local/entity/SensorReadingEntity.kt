package com.voiceai.client.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sensor_readings")
data class SensorReadingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val deviceId: Int,
    val value1: Double,
    val value2: Double?,
    val unit1: String,
    val unit2: String?,
    val recordedAt: Long = System.currentTimeMillis()
)
