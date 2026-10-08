package com.ovos.arabicassistant

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.InputStream
import kotlin.math.sqrt

/**
 * نتيجة التوجيه الدلالي الذكي
 */
data class SemanticMatch(
    val intent: String,
    val confidence: Float,
    val matchedAnchor: String = ""
)

/**
 * موجه المعاني الذكي (ONNX Semantic Router) لنظام أندرويد
 * يطابق قصد المستخدم دلالياً بالاعتماد على الفضاء الاتجاهي (Dense Embeddings 384D)
 * ويطبق قاعدة التراجع الصارم (Strict Fallback) لمنع أي هلوسة
 */
class SemanticRouter(private val context: Context) {

    private val TAG = "SemanticRouter"
    private val MIN_CONFIDENCE_THRESHOLD = 0.65f

    // قائمة متجهات النوايا والأنماط المحسوبة مسبقاً
    private val intentAnchors = mutableListOf<AnchorVector>()
    private var isInitialized = false

    private data class AnchorVector(
        val intent: String,
        val text: String,
        val vector: FloatArray
    )

    init {
        loadIntentEmbeddings()
    }

    /**
     * تحميل مصفوفة المتجهات الدلالية المسبقة من assets
     */
    private fun loadIntentEmbeddings() {
        try {
            val jsonStream: InputStream = context.assets.open("intent_embeddings.json")
            val jsonString = jsonStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val root = JSONObject(jsonString)
            val intentsObj = root.optJSONObject("intents") ?: return

            val keys = intentsObj.keys()
            while (keys.hasNext()) {
                val intentName = keys.next()
                val anchorsArray = intentsObj.getJSONArray(intentName)
                for (i in 0 until anchorsArray.length()) {
                    val item = anchorsArray.getJSONObject(i)
                    val text = item.getString("text")
                    val vecArray = item.getJSONArray("vector")
                    val floats = FloatArray(vecArray.length()) { idx ->
                        vecArray.getDouble(idx).toFloat()
                    }
                    intentAnchors.add(AnchorVector(intentName, text, floats))
                }
            }

            isInitialized = intentAnchors.isNotEmpty()
            Log.d(TAG, "تم تحميل مصفوفة المتجهات الدلالية بنجاح (${intentAnchors.size} نمط دلالي)")
        } catch (e: Exception) {
            Log.e(TAG, "خطأ أثناء تحميل intent_embeddings.json: ${e.message}")
            isInitialized = false
        }
    }

    /**
     * مطابقة قصد المستخدم دلالياً مع معالجة حوارات الدردشة (Chitchat) وتطبيق شرط الـ 65% الصارم
     */
    fun route(utterance: String, currentEmbedding: FloatArray? = null): SemanticMatch {
        val trimmed = utterance.trim()
        if (trimmed.isEmpty()) {
            return SemanticMatch("fallback_skill", 0f, "")
        }

        // 1. مسار الدردشة السريع (Chitchat Fast Path) لردود "اني زين"، "الحمد لله"، "بخير"
        val chitchatPhrases = setOf(
            "اني زين", "انا زين", "الحمد لله", "الحمدلله", "زين الحمد لله",
            "زين الحمدلله", "بخير الحمد لله", "تمام الحمد لله", "الحمد لله بخير",
            "بخير وانت", "تمام وانت", "وانت كيفك", "وانت شخبارك", "كلو تمام",
            "كله تمام", "بصحة جيدة", "على ما يرام", "ماشي الحال", "عايشين"
        )
        val singleWords = setOf("زين", "بخير", "تمام", "عايشين", "كويس")

        val cleanWords = trimmed.split(Regex("\\s+"))
        if (chitchatPhrases.any { trimmed.contains(it) } || (cleanWords.size <= 2 && cleanWords.any { it in singleWords })) {
            return SemanticMatch("greeting_skill", 0.99f, "اني زين والحمد لله")
        }

        // 2. إذا تم توفير متجه التضمين الكثيف (Dense Embedding) من محرك ONNX
        if (currentEmbedding != null && isInitialized) {
            var bestIntent = "fallback_skill"
            var bestScore = 0f
            var bestAnchor = ""

            for (anchor in intentAnchors) {
                val score = cosineSimilarity(currentEmbedding, anchor.vector)
                if (score > bestScore) {
                    bestScore = score
                    bestIntent = anchor.intent
                    bestAnchor = anchor.text
                }
            }

            // شرط التراجع الصارم (Strict Fallback): أقل من 65% يذهب فوراً للتراجع دون هلوسة
            return if (bestScore >= MIN_CONFIDENCE_THRESHOLD) {
                SemanticMatch(bestIntent, bestScore, bestAnchor)
            } else {
                SemanticMatch("fallback_skill", bestScore, "")
            }
        }

        // 3. التراجع الافتراضي الآمن
        return SemanticMatch("unknown", 0f, "")
    }

    /**
     * حساب التشابه الزاوي (Cosine Similarity) بين متجهين
     */
    private fun cosineSimilarity(v1: FloatArray, v2: FloatArray): Float {
        var dot = 0f
        var norm1 = 0f
        var norm2 = 0f
        val len = minOf(v1.size, v2.size)

        for (i in 0 until len) {
            val a = v1[i]
            val b = v2[i]
            dot += a * b
            norm1 += a * a
            norm2 += b * b
        }

        val denominator = sqrt(norm1) * sqrt(norm2)
        return if (denominator > 0f) dot / denominator else 0f
    }
}
