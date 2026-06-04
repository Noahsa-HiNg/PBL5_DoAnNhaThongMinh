package com.voiceai.client.data.audio

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException

class AudioRepository(private val context: Context) {

    companion object {
        private const val TAG = "AudioRepo"
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    private var audioRecord: AudioRecord? = null
    @Volatile
    private var isRecording = false

    @Suppress("MissingPermission")
    suspend fun startRecording(): File? = withContext(Dispatchers.IO) {
        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (minBufferSize <= 0) {
            Log.e(TAG, "Invalid buffer size: $minBufferSize")
            return@withContext null
        }
        
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                minBufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord initialization failed!")
                return@withContext null
            }

            val pcmFile = File(context.cacheDir, "recording.pcm")
            val wavFile = File(context.cacheDir, "recording.wav")
            
            audioRecord?.startRecording()
            isRecording = true
            Log.d(TAG, "Started recording to ${pcmFile.absolutePath}")
            
            FileOutputStream(pcmFile).use { outputStream ->
                val buffer = ByteArray(minBufferSize)
                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        outputStream.write(buffer, 0, read)
                    } else if (read < 0) {
                        Log.e(TAG, "Error reading audio data: $read")
                        break
                    }
                }
            }
            
            Log.d(TAG, "Stopped recording, converting to WAV")
            // Chuyển đổi PCM sang WAV
            pcmToWav(pcmFile, wavFile)
            return@withContext wavFile
        } catch (e: Exception) {
            Log.e(TAG, "Recording failed", e)
            return@withContext null
        } finally {
            stopRecordingInternal()
        }
    }

    fun stopRecording() {
        isRecording = false
    }

    private fun stopRecordingInternal() {
        isRecording = false
        try {
            if (audioRecord?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                audioRecord?.stop()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping AudioRecord", e)
        }
        audioRecord?.release()
        audioRecord = null
    }

    private fun pcmToWav(pcmFile: File, wavFile: File) {
        val pcmData = pcmFile.readBytes()
        FileOutputStream(wavFile).use { out ->
            val totalAudioLen = pcmData.size.toLong()
            val totalDataLen = totalAudioLen + 36
            val channels = 1
            val byteRate = (SAMPLE_RATE * channels * 16 / 8).toLong()
            
            writeWavHeader(out, totalAudioLen, totalDataLen, SAMPLE_RATE.toLong(), channels, byteRate)
            out.write(pcmData)
        }
    }

    private fun writeWavHeader(
        out: FileOutputStream, 
        totalAudioLen: Long, 
        totalDataLen: Long, 
        longSampleRate: Long, 
        channels: Int, 
        byteRate: Long
    ) {
        val header = ByteArray(44)
        header[0] = 'R'.code.toByte()
        header[1] = 'I'.code.toByte()
        header[2] = 'F'.code.toByte()
        header[3] = 'F'.code.toByte()
        header[4] = (totalDataLen and 0xff).toByte()
        header[5] = (totalDataLen shr 8 and 0xff).toByte()
        header[6] = (totalDataLen shr 16 and 0xff).toByte()
        header[7] = (totalDataLen shr 24 and 0xff).toByte()
        header[8] = 'W'.code.toByte()
        header[9] = 'A'.code.toByte()
        header[10] = 'V'.code.toByte()
        header[11] = 'E'.code.toByte()
        header[12] = 'f'.code.toByte()
        header[13] = 'm'.code.toByte()
        header[14] = 't'.code.toByte()
        header[15] = ' '.code.toByte()
        header[16] = 16
        header[17] = 0
        header[18] = 0
        header[19] = 0
        header[20] = 1
        header[21] = 0
        header[22] = channels.toByte()
        header[23] = 0
        header[24] = (longSampleRate and 0xff).toByte()
        header[25] = (longSampleRate shr 8 and 0xff).toByte()
        header[26] = (longSampleRate shr 16 and 0xff).toByte()
        header[27] = (longSampleRate shr 24 and 0xff).toByte()
        header[28] = (byteRate and 0xff).toByte()
        header[29] = (byteRate shr 8 and 0xff).toByte()
        header[30] = (byteRate shr 16 and 0xff).toByte()
        header[31] = (byteRate shr 24 and 0xff).toByte()
        header[32] = (channels * 16 / 8).toByte()
        header[33] = 0
        header[34] = 16
        header[35] = 0
        header[36] = 'd'.code.toByte()
        header[37] = 'a'.code.toByte()
        header[38] = 't'.code.toByte()
        header[39] = 'a'.code.toByte()
        header[40] = (totalAudioLen and 0xff).toByte()
        header[41] = (totalAudioLen shr 8 and 0xff).toByte()
        header[42] = (totalAudioLen shr 16 and 0xff).toByte()
        header[43] = (totalAudioLen shr 24 and 0xff).toByte()
        out.write(header, 0, 44)
    }
}
