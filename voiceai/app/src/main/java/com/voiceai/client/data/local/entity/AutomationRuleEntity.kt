package com.voiceai.client.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "automation_rules")
data class AutomationRuleEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val conditionType: String,
    val conditionDeviceId: Int,
    val conditionOperator: String,
    val conditionValue: String,
    val actionDeviceId: Int,
    val actionCommand: String,
    val isEnabled: Boolean,
    val createdAt: Long = System.currentTimeMillis()
)
