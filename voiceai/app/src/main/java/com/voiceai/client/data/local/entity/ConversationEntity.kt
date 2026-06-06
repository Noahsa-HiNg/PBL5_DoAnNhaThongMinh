package com.voiceai.client.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "conversations")
data class ConversationEntity(
    @PrimaryKey val id: Int,
    val sender: String,
    val message: String,
    val timestamp: String
)
