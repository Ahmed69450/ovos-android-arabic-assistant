package com.ovos.arabicassistant.voice

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import kotlin.math.sqrt

/**
 * خدمة التعرف الصوتي المستمر باستخدام Vosk في بيئة سيارات BYD DiLink
 * مصممة لتعمل بدون إنترنت (Offline)، بمعدل عينات 16000Hz وبكاشف نشاط صوتي (VAD)
 * مدمج لتقليل استهلاك طاقة ومعالج شاشة السيارة أثناء الصمت.
 */
class VoskSpeechService(
    private val context: Context,
    private val listener: VoskListener
) {

    interface VoskListener {
        fun onReady()
        fun onResult(hypothesis: String)
        fun onPartialResult(partial: String)
        fun onError(error: String)
        fun onListeningStateChanged(isListening: Boolean)
    }

    private var model: Model? = null
    private var recognizer: Recognizer? = null
    private var audioRecord: AudioRecord? = null
    private var isListening = false
    private var recordingJob: Job? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    companion object {
        private const val TAG = "VoskSpeechService"
        const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        
        // عتبة طاقة الصوت (VAD Energy Threshold) لتجاهل الصمت وضوضاء المحرك المنخفضة
        private const val SILENCE_ENERGY_THRESHOLD = 350.0
    }

    /**
     * تهيئة نموذج Vosk الصوتي من التخزين الداخلي للتطبيق
     */
    fun initialize(onInitialized: (Boolean) -> Unit) {
        serviceScope.launch {
            try {
                val modelDir = File(context.filesDir, "vosk-model-ar")
                if (!modelDir.exists() || !File(modelDir, "am").exists()) {
                    // إذا لم يتوفر الموديل محلياً، نبلغ المستمع
                    Log.w(TAG, "مجلد نموذج Vosk غير موجود في التخزين الداخلي: ${modelDir.absolutePath}")
                }

                if (modelDir.exists()) {
                    model = Model(modelDir.absolutePath)
                    recognizer = Recognizer(model, SAMPLE_RATE.toFloat())
                    withContext(Dispatchers.Main) {
                        listener.onReady()
                        onInitialized(true)
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        onInitialized(false)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "فشلت تهيئة نموذج Vosk: ${e.message}")
                withContext(Dispatchers.Main) {
                    listener.onError("تعذر تحميل نموذج Vosk الصوتي: ${e.localizedMessage}")
                    onInitialized(false)
                }
            }
        }
    }

    /**
     * بدء جلسة الاستماع الصوتي المستمر في الخلفية
     */
    fun startListening() {
        if (isListening) return

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT) * 2
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                listener.onError("تعذر تهيئة مسجل الصوت AudioRecord")
                return
            }

            audioRecord?.startRecording()
            isListening = true
            listener.onListeningStateChanged(true)

            recordingJob = serviceScope.launch {
                val audioBuffer = ShortArray(bufferSize / 2)
                val byteBuffer = ByteArray(bufferSize)

                while (isActive && isListening) {
                    val readCount = audioRecord?.read(audioBuffer, 0, audioBuffer.size) ?: 0
                    if (readCount > 0) {
                        // 1. حساب طاقة الصوت (VAD) لتفادي معالجة الصمت وتوفير المعالج
                        val energy = calculateRms(audioBuffer, readCount)
                        if (energy < SILENCE_ENERGY_THRESHOLD) {
                            continue
                        }

                        // تحويل Short إلى Byte لتقديمه لمحرك Vosk
                        var idx = 0
                        for (i in 0 until readCount) {
                            val sample = audioBuffer[i]
                            byteBuffer[idx++] = (sample.toInt() and 0xFF).toByte()
                            byteBuffer[idx++] = ((sample.toInt() shr 8) and 0xFF).toByte()
                        }

                        val rec = recognizer
                        if (rec != null) {
                            if (rec.acceptWaveForm(byteBuffer, readCount * 2)) {
                                val resultJson = rec.result
                                val text = parseVoskJson(resultJson, "text")
                                if (text.isNotBlank()) {
                                    withContext(Dispatchers.Main) {
                                        listener.onResult(text)
                                    }
                                }
                            } else {
                                val partialJson = rec.partialResult
                                val partialText = parseVoskJson(partialJson, "partial")
                                if (partialText.isNotBlank()) {
                                    withContext(Dispatchers.Main) {
                                        listener.onPartialResult(partialText)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (e: SecurityException) {
            listener.onError("صلاحية الميكروفون RECORD_AUDIO غير ممنوحة")
        } catch (e: Exception) {
            listener.onError("خطأ أثناء بدء التسجيل: ${e.message}")
        }
    }

    /**
     * إيقاف الاستماع مؤقتاً
     */
    fun stopListening() {
        isListening = false
        recordingJob?.cancel()
        try {
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
        } catch (e: Exception) {
            Log.e(TAG, "خطأ أثناء إيقاف AudioRecord: ${e.message}")
        }
        listener.onListeningStateChanged(false)
    }

    /**
     * حساب متوسط الطاقة الصوتية (Root Mean Square) لكشف النشاط الصوتي (VAD)
     */
    private fun calculateRms(buffer: ShortArray, length: Int): Double {
        var sum = 0.0
        for (i in 0 until length) {
            sum += buffer[i] * buffer[i]
        }
        return sqrt(sum / length)
    }

    /**
     * استخراج النص من نتيجة Vosk JSON
     */
    private fun parseVoskJson(jsonString: String, key: String): String {
        return try {
            val json = JSONObject(jsonString)
            json.optString(key, "").trim()
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * تحرير جميع موارد الذاكرة والصوت
     */
    fun destroy() {
        stopListening()
        serviceScope.cancel()
        recognizer?.close()
        model?.close()
    }
}
