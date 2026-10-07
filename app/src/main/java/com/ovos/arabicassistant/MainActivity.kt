package com.ovos.arabicassistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.card.MaterialCardView
import com.ovos.arabicassistant.databinding.ActivityMainBinding
import kotlinx.coroutines.launch
import java.util.Locale

/**
 * شاشة المساعد الصوتي الرئيسية (MainActivity)
 * تدير التعرف الصوتي باللغة العربية، تحويل النص إلى كلام (TTS)، والتفاعل مع محرك OVOS
 */
class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityMainBinding
    private lateinit var ovosEngine: OvosAssistantEngine
    private var textToSpeech: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isTtsReady = false

    companion object {
        private const val REQUEST_RECORD_AUDIO_PERMISSION = 200
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // تهيئة محرك النوايا والمهارات OVOS
        ovosEngine = OvosAssistantEngine.getInstance(this)
        lifecycleScope.launch {
            binding.tvStatus.text = "جاري تهيئة نموذج OVOS والنوايا..."
            val initialized = ovosEngine.initialize()
            if (initialized) {
                binding.tvStatus.text = "المساعد جاهز ويعمل بدون إنترنت (Offline)"
            } else {
                binding.tvStatus.text = "تعذر تهيئة النموذج المحلي"
            }
        }

        // تهيئة محرك النطق العربي (TextToSpeech)
        textToSpeech = TextToSpeech(this, this)

        // إعداد التعرف الصوتي (SpeechRecognizer)
        setupSpeechRecognizer()

        // ربط أزرار الإدخال
        binding.btnSend.setOnClickListener {
            val userText = binding.etUserPrompt.text.toString().trim()
            if (userText.isNotEmpty()) {
                handleUserQuery(userText)
                binding.etUserPrompt.text.clear()
            }
        }

        binding.btnMic.setOnClickListener {
            checkAudioPermissionAndListen()
        }
    }

    /**
     * التحقق من صلاحية الميكروفون والبدء بالاستماع
     */
    private fun checkAudioPermissionAndListen() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                REQUEST_RECORD_AUDIO_PERMISSION
            )
        } else {
            startListening()
        }
    }

    /**
     * بدء جلسة التعرف على الصوت باللغة العربية
     */
    private fun startListening() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ar")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "ar")
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, "ar")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "تفضل بالتحدث باللغة العربية...")
        }
        binding.tvStatus.text = getString(R.string.listening_state)
        speechRecognizer?.startListening(intent)
    }

    private fun setupSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {
                    binding.tvStatus.text = getString(R.string.processing_state)
                }

                override fun onError(error: Int) {
                    binding.tvStatus.text = "حدث خطأ في التقاط الصوت ($error)"
                }

                override fun onResults(results: Bundle?) {
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!matches.isNullOrEmpty()) {
                        val spokenText = matches[0]
                        handleUserQuery(spokenText)
                    } else {
                        binding.tvStatus.text = getString(R.string.ready_state)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
    }

    /**
     * إرسال جملة المستخدم إلى محرك OVOS واستلام الرد الصوتي
     */
    private fun handleUserQuery(query: String) {
        // إضافة رسالة المستخدم إلى الواجهة
        addChatBubble(query, isUser = true)
        binding.tvStatus.text = getString(R.string.processing_state)

        lifecycleScope.launch {
            val result = ovosEngine.processUtterance(query)

            // تحديث الواجهة برد المساعد
            val responseText = result.response
            addChatBubble(responseText, isUser = false, intentInfo = "${result.intent} (${(result.confidence * 100).toInt()}%)")
            binding.tvStatus.text = "المهارة: ${result.intent} • الثقة: ${(result.confidence * 100).toInt()}%"

            // نطق الرد بالصوت العربي
            speakOut(responseText)
        }
    }

    /**
     * نطق النص العربي عبر محرك TextToSpeech
     */
    private fun speakOut(text: String) {
        if (isTtsReady && textToSpeech != null) {
            textToSpeech?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "OVOS_RESPONSE_ID")
        }
    }

    /**
     * إضافة فقاعة محادثة بتصميم عصري إلى واجهة المستخدم
     */
    private fun addChatBubble(message: String, isUser: Boolean, intentInfo: String? = null) {
        val card = MaterialCardView(this).apply {
            radius = 16f * resources.displayMetrics.density
            cardElevation = 2f * resources.displayMetrics.density
            setCardBackgroundColor(
                ContextCompat.getColor(
                    this@MainActivity,
                    if (isUser) R.color.chat_bubble_user else R.color.chat_bubble_assistant
                )
            )
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                gravity = if (isUser) Gravity.START else Gravity.END
                setMargins(8, 8, 8, 8)
            }
        }

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 16, 24, 16)
        }

        if (!isUser && intentInfo != null) {
            val infoView = TextView(this).apply {
                text = "⚡ نية OVOS: $intentInfo"
                textSize = 10f
                setTextColor(ContextCompat.getColor(this@MainActivity, R.color.teal_700))
                setPadding(0, 0, 0, 8)
            }
            layout.addView(infoView)
        }

        val textView = TextView(this).apply {
            text = message
            textSize = 15f
            setTextColor(ContextCompat.getColor(this@MainActivity, R.color.black))
            lineSpacingExtra = 4f
        }
        layout.addView(textView)
        card.addView(layout)

        binding.chatContainer.addView(card)
        binding.scrollView.post {
            binding.scrollView.fullScroll(View.FOCUS_DOWN)
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = textToSpeech?.setLanguage(Locale("ar"))
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                Toast.makeText(this, "اللغة العربية غير مدعومة بالكامل في محرك TTS بجهازك", Toast.LENGTH_SHORT).show()
            } else {
                isTtsReady = true
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_RECORD_AUDIO_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startListening()
            } else {
                Toast.makeText(this, "يلزم منح إذن الميكروفون لاستخدام المساعد صوتياً", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroy() {
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        speechRecognizer?.destroy()
        super.onDestroy()
    }
}
