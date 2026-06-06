package com.voiceai.client.data.local.dao

import androidx.room.*
import com.voiceai.client.data.local.entity.AutomationRuleEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface AutomationRuleDao {
    @Query("SELECT * FROM automation_rules")
    fun getAllRules(): Flow<List<AutomationRuleEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRule(rule: AutomationRuleEntity)

    @Update
    suspend fun updateRule(rule: AutomationRuleEntity)

    @Delete
    suspend fun deleteRule(rule: AutomationRuleEntity)
}
