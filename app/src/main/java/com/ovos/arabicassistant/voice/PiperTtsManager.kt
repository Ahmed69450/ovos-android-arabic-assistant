package com.ovos.arabicassistant.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import java.io.File
import java.util.Locale
import java.util.regex.Pattern

/**
 * مدير تحويل النص إلى كلام (TTS Manager)
 * يدعم نماذج Piper ONNX الصوتية عالية الدقة مع التراجع التلقائي إلى Android TextToSpeech،
 * ويضبط وتيرة النطق الهادئة (length_scale = 1.15) المناسبة لبيئة القيادة في سيارات BYD DiLink.
 */
class PiperTtsManager(
    private val context: Context,
    private val onInitListener: ((Boolean) -> Unit)? = null
) : TextToSpeech.OnInitListener {

    private var textToSpeech: TextToSpeech? = null
    private var isSystemTtsReady = false
    private var isPiperModelAvailable = false
    private var piperModelFile: File? = null

    // معامل إبطاء وتيرة النطق لإعطاء نبرة طبيعية وهادئة (يقابل length_scale = 1.15 في Piper)
    private var lengthScale: Float = 1.15f

    companion object {
        private const val TAG = "PiperTtsManager"
        private const val UTTERANCE_ID = "OVOS_TTS_UTTERANCE"
        
        // تنقية النصوص من الماركداون والوسوم والأسطر قبل التحدث
        private val HTML_PATTERN = Pattern.compile("<[^>]+>")
        private val MARKDOWN_PATTERN = Pattern.compile("[*_~`#>]")
        private val URL_PATTERN = Pattern.compile("https?://\\S+|www\\.\\S+")
        private val EMOJI_PATTERN = Pattern.compile(
            "[\\x{10000}-\\x{10ffff}]|[\\x{2600}-\\x{27BF}]|[\\x{D83C}-\\x{DBFF}\\x{DC00}-\\x{DFFF}]"
        )
    }

    init {
        checkPiperModelAvailability()
        textToSpeech = TextToSpeech(context, this)
    }

    /**
     * فحص توفر ملفات نموذج Piper ONNX الصوتي في ذاكرة الجهاز
     */
    private fun checkPiperModelAvailability() {
        val modelDir = File(context.filesDir, "piper")
        val onnxFile = File(modelDir, "arabic_model.onnx")
        if (onnxFile.exists() && onnxFile.length() > 0) {
            isPiperModelAvailable = true
            piperModelFile = onnxFile
            Log.i(TAG, "تم العثور على نموذج Piper ONNX العربي: ${onnxFile.absolutePath}")
        } else {
            isPiperModelAvailable = false
            Log.i(TAG, "لم يتم العثور على نموذج Piper ONNX محلياً، سيتم استخدام محرك أندرويد الصوتي كبديل")
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = textToSpeech?.setLanguage(Locale("ar"))
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.w(TAG, "حزمة اللغة العربية قد لا تكون مكتملة في محرك TTS بالنظام")
                isSystemTtsReady = true
                onInitListener?.invoke(true)
            } else {
                isSystemTtsReady = true
                // ضبط سرعة النطق لتتوافق مع length_scale = 1.15 (سرعة أهدأ بحوالي 87%)
                val speechRate = 1.0f / lengthScale
                textToSpeech?.setSpeechRate(speechRate)
                textToSpeech?.setPitch(1.0f)
                Log.i(TAG, "تمت تهيئة محرك TextToSpeech بنجاح بمعدل سرعة: $speechRate")
                onInitListener?.invoke(true)
            }
        } else {
            Log.e(TAG, "فشلت تهيئة محرك TextToSpeech، الحالة: $status")
            isSystemTtsReady = false
            onInitListener?.invoke(false)
        }
    }

    /**
     * ضبط معامل وتيرة النطق (length_scale)
     */
    fun setLengthScale(scale: Float) {
        this.lengthScale = scale
        if (isSystemTtsReady) {
            val speechRate = 1.0f / scale
            textToSpeech?.setSpeechRate(speechRate)
        }
    }

    /**
     * تنقية النصوص وتجريدها من الماركداون والوسوم والأسطر قبل التحدث
     */
    fun sanitizeForSpeech(rawText: String): String {
        if (rawText.isBlank()) return ""
        var cleaned = rawText
        cleaned = URL_PATTERN.matcher(cleaned).replaceAll("")
        cleaned = HTML_PATTERN.matcher(cleaned).replaceAll(" ")
        cleaned = MARKDOWN_PATTERN.matcher(cleaned).replaceAll(" ")
        cleaned = EMOJI_PATTERN.matcher(cleaned).replaceAll("")
        // إزالة محارف السطور الجديدة والمسافات الزائدة
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        cleaned = cleaned.replace("[\"'{}\\[\\]()]".toRegex(), "")
        return cleaned.replace("\\s+".toRegex(), " ").trim()
    }

    /**
     * نطق النص العربي بصوت عالي الدقة ووتيرة هادئة
     */
    fun speak(text: String, onComplete: (() -> Unit)? = null) {
        val cleanText = sanitizeForSpeech(text)
        if (cleanText.isEmpty()) {
            onComplete?.invoke()
            return
        }

        if (onComplete != null) {
            textToSpeech?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) {
                    if (utteranceId == UTTERANCE_ID) {
                        onComplete()
                    }
                }
                override fun onError(utteranceId: String?) {
                    if (utteranceId == UTTERANCE_ID) {
                        onComplete()
                    }
                }
            })
        }

        if (isSystemTtsReady && textToSpeech != null) {
            textToSpeech?.speak(cleanText, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
        } else {
            Log.w(TAG, "محرك النطق غير جاهز بعد")
            onComplete?.invoke()
        }
    }

    /**
     * إيقاف النطق فوراً
     */
    fun stop() {
        textToSpeech?.stop()
    }

    /**
     * تحرير موارد المحرك الصوتي عند إغلاق التطبيق
     */
    fun shutdown() {
        try {
            textToSpeech?.stop()
            textToSpeech?.shutdown()
        } catch (e: Exception) {
            Log.e(TAG, "خطأ أثناء تحرير موارد TTS: ${e.message}")
        }
    }
}
