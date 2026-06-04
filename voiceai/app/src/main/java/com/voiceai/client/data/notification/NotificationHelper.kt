package com.voiceai.client.data.notification

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

class NotificationHelper(private val context: Context) {

    companion object {
        const val ALARM_CHANNEL_ID = "alarm_channel"
        private const val ALARM_CHANNEL_NAME = "Báo thức"
        private var notificationId = 1000
    }

    init { createNotificationChannel() }

    private fun createNotificationChannel() {
        // SDK_INT luôn >= 26 (minSdk), bỏ if check đi
        val channel = NotificationChannel(
            ALARM_CHANNEL_ID,
            ALARM_CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Thông báo báo thức từ AI Assistant"
            enableVibration(true)
        }
        val notificationManager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.createNotificationChannel(channel)
    }

    fun showAlarmNotification(label: String, time: String) {
        // Kiểm tra permission POST_NOTIFICATIONS (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) return
        }

        val notificationManager =
            context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Dùng android.R.drawable.ic_lock_idle_alarm — icon có sẵn trong AOSP
        val notification = NotificationCompat.Builder(context, ALARM_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("⏰ Báo thức: $time")
            .setContentText(label)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(notificationId++, notification)
    }
}