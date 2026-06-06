package com.voiceai.client.data.local.dao

import androidx.room.*
import com.voiceai.client.data.local.entity.ConversationEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ConversationDao {
    @Query("SELECT * FROM conversations ORDER BY timestamp ASC")
    fun getAllConversations(): Flow<List<ConversationEntity>>

    @Upsert
    suspend fun upsertConversations(conversations: List<ConversationEntity>)

    @Query("DELETE FROM conversations")
    suspend fun deleteAll()
}
