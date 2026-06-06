package com.voiceai.client.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.voiceai.client.data.local.dao.*
import com.voiceai.client.data.local.entity.*

@Database(
    entities = [
        DeviceEntity::class,
        SensorReadingEntity::class,
        ConversationEntity::class,
        AutomationRuleEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun deviceDao(): DeviceDao
    abstract fun sensorReadingDao(): SensorReadingDao
    abstract fun conversationDao(): ConversationDao
    abstract fun automationRuleDao(): AutomationRuleDao
}
