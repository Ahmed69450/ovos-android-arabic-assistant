package com.ovos.arabicassistant

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

/**
 * نتيجة معالجة الأمر الصوتي من محرك OVOS
 */
data class OvosResult(
    val response: String,
    val intent: String,
    val confidence: Float,
    val utterance: String
)

/**
 * المحرك الوسيط (Engine Wrapper) بلغة Kotlin للربط مع مكتبة بايثون وOVOS
 */
class OvosAssistantEngine private constructor(private val context: Context) {

    private var bridgeModule: PyObject? = null
    private var semanticRouter: SemanticRouter? = null
    private var isInitialized = false

    companion object {
        @Volatile
        private var instance: OvosAssistantEngine? = null

        fun getInstance(context: Context): OvosAssistantEngine {
            return instance ?: synchronized(this) {
                instance ?: OvosAssistantEngine(context.applicationContext).also { instance = it }
            }
        }
    }

    /**
     * تهيئة المحرك ونسخ ملفات الأوزان والنوايا إلى الذاكرة الداخلية وتشغيل جسر بايثون
     */
    suspend fun initialize(): Boolean = withContext(Dispatchers.IO) {
        if (isInitialized) return@withContext true

        try {
            // نسخ ملفات الأوزان وبيانات النوايا من assets إلى التخزين الداخلي للتطبيق
            val modelFile = copyAssetToInternalStorage("model_weights.json")
            val intentsFile = copyAssetToInternalStorage("intents.json")

            // الحصول على بيئة بايثون المدمجة
            val py = Python.getInstance()
            bridgeModule = py.getModule("ovos_bridge")

            // استدعاء دالة التهيئة في بايثون
            val success = bridgeModule?.callAttr("initialize", modelFile.absolutePath, intentsFile.absolutePath)?.toBoolean() ?: false
            
            // تهيئة موجه المعاني الدلالي (ONNX Semantic Router)
            semanticRouter = SemanticRouter(context)

            isInitialized = success
            success
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * معالجة نص المستخدم صوتياً أو كتابياً وإرجاع النتيجة
     */
    suspend fun processUtterance(utterance: String): OvosResult = withContext(Dispatchers.IO) {
        if (!isInitialized) {
            initialize()
        }

        try {
            // فحص التوجيه الدلالي الذكي أولاً
            val routeResult = semanticRouter?.route(utterance)
            val resultJsonStr = if (routeResult != null && routeResult.intent != "unknown") {
                bridgeModule?.callAttr("process_utterance", utterance, routeResult.intent, routeResult.confidence.toDouble())?.toString() ?: ""
            } else {
                bridgeModule?.callAttr("process_utterance", utterance)?.toString() ?: ""
            }
            val json = JSONObject(resultJsonStr)

            OvosResult(
                response = json.optString("response", "عذراً، لم أتلق رداً مناسباً."),
                intent = json.optString("intent", "unknown"),
                confidence = json.optDouble("confidence", 0.0).toFloat(),
                utterance = utterance
            )
        } catch (e: Exception) {
            e.printStackTrace()
            OvosResult(
                response = "حدث خطأ غير متوقع أثناء معالجة الأمر محلياً.",
                intent = "error",
                confidence = 0f,
                utterance = utterance
            )
        }
    }

    /**
     * نسخ ملف من مجلد الأصول (assets) إلى التخزين الداخلي ليسهل قراءته في بايثون
     */
    private fun copyAssetToInternalStorage(fileName: String): File {
        val destinationFile = File(context.filesDir, fileName)
        if (!destinationFile.exists() || destinationFile.length() == 0L) {
            context.assets.open(fileName).use { inputStream ->
                FileOutputStream(destinationFile).use { outputStream ->
                    inputStream.copyTo(outputStream)
                }
            }
        }
        return destinationFile
    }
}
