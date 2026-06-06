package com.voiceai.client.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "devices")
data class DeviceEntity(
    @PrimaryKey val id: Int,
    val name: String,
    val type: String,
    val status: String,
    val roomId: Int?,
    val pin: Int?,
    val timestamp: String?,
    val lastUpdated: Long = System.currentTimeMillis()
)
