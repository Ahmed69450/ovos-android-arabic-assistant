package com.ovos.arabicassistant

import android.app.Application
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * فئة التطبيق الرئيسية (Application Class)
 * تتولى تشغيل وتهيئة بيئة بايثون المدمجة عبر Chaquopy عند إقلاع التطبيق
 */
class OvosAssistantApp : Application() {

    override fun onCreate() {
        super.onCreate()
        
        // التحقق من بدء تشغيل بيئة بايثون وتهيئتها على منصة أندرويد
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
    }
}
