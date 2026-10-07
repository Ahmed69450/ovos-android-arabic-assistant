package com.ovos.arabicassistant

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
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
import com.ovos.arabicassistant.voice.PiperTtsManager
import com.ovos.arabicassistant.voice.VoskSpeechService
import kotlinx.coroutines.launch

/**
 * شاشة المساعد الصوتي الرئيسية (MainActivity) لسيارات BYD DiLink
 * تدير الاستماع المستمر في خلفية السيارة (Vosk STT) مع كاشف النشاط الصوتي (VAD)،
 * ونظام النطق عالي الدقة (Piper TTS مع التراجع التلقائي)، وخفض صوت الوسائط (Audio Ducking).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var ovosEngine: OvosAssistantEngine
    private lateinit var piperTts: PiperTtsManager
    private var voskService: VoskSpeechService? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var isVoskReady = false
    private var isListening = false
    private var audioManager: AudioManager? = null

    companion object {
        private const val REQUEST_RECORD_AUDIO_PERMISSION = 200
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        audioManager = getSystemService(Context.AUDIO_SERVICE) as? AudioManager

        // 1. تهيئة مدير النطق الصوتي عالي الدقة (Piper TTS مع التراجع لنظام أندرويد)
        piperTts = PiperTtsManager(this) { ready ->
            if (ready) {
                runOnUiThread {
                    binding.tvStatus.text = "محرك النطق الصوتي جاهز (length_scale=1.15)"
                }
            }
        }

        // 2. تهيئة محرك النوايا والمهارات OVOS وذاكرة السياق FSM
        ovosEngine = OvosAssistantEngine.getInstance(this)
        lifecycleScope.launch {
            binding.tvStatus.text = "جاري تهيئة نموذج OVOS وخوارزميات NLU و FSM..."
            val initialized = ovosEngine.initialize()
            if (initialized) {
                binding.tvStatus.text = "المساعد جاهز ومزود بذاكرة السياق والـ NLU الهجين"
            } else {
                binding.tvStatus.text = "تعذر تهيئة النموذج المحلي"
            }
        }

        // 3. إعداد خدمة التعرف الصوتي المستمر (Vosk STT)
        setupVoskService()

        // 4. إعداد المساعد الصوتي البديل (SpeechRecognizer الافتراضي)
        setupSystemSpeechRecognizer()

        // 5. ربط عناصر واجهة المستخدم
        binding.btnSend.setOnClickListener {
            val userText = binding.etUserPrompt.text.toString().trim()
            if (userText.isNotEmpty()) {
                handleUserQuery(userText)
                binding.etUserPrompt.text.clear()
            }
        }

        binding.btnMic.setOnClickListener {
            checkAudioPermissionAndToggleListening()
        }
    }

    private fun setupVoskService() {
        voskService = VoskSpeechService(this, object : VoskSpeechService.VoskListener {
            override fun onReady() {
                isVoskReady = true
                runOnUiThread {
                    binding.tvStatus.text = "محرك Vosk الصوتي المستمر جاهز (16kHz Offline)"
                }
            }

            override fun onResult(hypothesis: String) {
                runOnUiThread {
                    if (hypothesis.isNotBlank()) {
                        handleUserQuery(hypothesis)
                    }
                }
            }

            override fun onPartialResult(partial: String) {
                runOnUiThread {
                    binding.tvStatus.text = "جاري الاستماع: $partial"
                }
            }

            override fun onError(error: String) {
                runOnUiThread {
                    binding.tvStatus.text = "تنبيه صوتي: $error"
                }
            }

            override fun onListeningStateChanged(listening: Boolean) {
                isListening = listening
                runOnUiThread {
                    if (listening) {
                        binding.tvStatus.text = getString(R.string.listening_state)
                    } else {
                        binding.tvStatus.text = getString(R.string.ready_state)
                    }
                }
            }
        })

        voskService?.initialize { success ->
            isVoskReady = success
        }
    }

    private fun setupSystemSpeechRecognizer() {
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
                        handleUserQuery(matches[0])
                    } else {
                        binding.tvStatus.text = getString(R.string.ready_state)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
    }

    private fun checkAudioPermissionAndToggleListening() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                REQUEST_RECORD_AUDIO_PERMISSION
            )
        } else {
            if (isListening) {
                stopListening()
            } else {
                startListening()
            }
        }
    }

    private fun startListening() {
        requestAudioFocus()
        if (isVoskReady && voskService != null) {
            voskService?.startListening()
        } else {
            // التراجع إلى SpeechRecognizer الافتراضي إذا لم يتم تحميل موديل Vosk
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ar")
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "ar")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "تفضل بالتحدث باللغة العربية...")
            }
            binding.tvStatus.text = getString(R.string.listening_state)
            speechRecognizer?.startListening(intent)
        }
    }

    private fun stopListening() {
        if (isVoskReady) {
            voskService?.stopListening()
        } else {
            speechRecognizer?.stopListening()
        }
        abandonAudioFocus()
    }

    /**
     * إرسال جملة المستخدم إلى محرك OVOS المطور واستلام الرد الصوتي المنقى
     */
    private fun handleUserQuery(query: String) {
        addChatBubble(query, isUser = true)
        binding.tvStatus.text = getString(R.string.processing_state)

        lifecycleScope.launch {
            val result = ovosEngine.processUtterance(query)

            val responseText = result.response
            val intentTag = result.intent
            val confidencePercent = (result.confidence * 100).toInt()

            addChatBubble(responseText, isUser = false, intentInfo = "$intentTag ($confidencePercent%)")
            binding.tvStatus.text = "المهارة: $intentTag • الثقة: $confidencePercent%"

            // خفض صوت السيارة ونطق الرد بأسلوب طبيعي هادئ
            requestAudioFocus()
            piperTts.speak(responseText) {
                abandonAudioFocus()
            }
        }
    }

    /**
     * طلب التركيز الصوتي لخفض صوت وسائط السيارة مؤقتاً (Audio Ducking)
     */
    private fun requestAudioFocus() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val focusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .build()
            audioManager?.requestAudioFocus(focusRequest)
        } else {
            @Suppress("DEPRECATION")
            audioManager?.requestAudioFocus(null, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
        }
    }

    private fun abandonAudioFocus() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val focusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .build()
            audioManager?.abandonAudioFocusRequest(focusRequest)
        } else {
            @Suppress("DEPRECATION")
            audioManager?.abandonAudioFocus(null)
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
            setLineSpacing(4f, 1f)
        }
        layout.addView(textView)
        card.addView(layout)

        binding.chatContainer.addView(card)
        binding.scrollView.post {
            binding.scrollView.fullScroll(View.FOCUS_DOWN)
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
        piperTts.shutdown()
        voskService?.destroy()
        speechRecognizer?.destroy()
        abandonAudioFocus()
        super.onDestroy()
    }
}
