package com.pan123.unlimited

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.view.KeyEvent
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast

/** App 内嵌的网页面板，加载本机 HTTP 服务，不走外部浏览器。 */
class WebActivity : Activity() {

    private var web: WebView? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val view = WebView(this)
        web = view
        setContentView(view)
        view.settings.javaScriptEnabled = true
        view.settings.domStorageEnabled = true
        view.webViewClient = object : WebViewClient() {
            override fun onReceivedError(v: WebView, code: Int, description: String, failingUrl: String) {
                Toast.makeText(this@WebActivity, "加载失败：$description", Toast.LENGTH_LONG).show()
            }
        }
        view.loadUrl(intent.getStringExtra(EXTRA_URL) ?: "http://127.0.0.1:33333/")
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && web?.canGoBack() == true) {
            web?.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onDestroy() {
        web?.destroy()
        web = null
        super.onDestroy()
    }

    companion object {
        const val EXTRA_URL = "url"

        fun open(context: Context, url: String) {
            context.startActivity(Intent(context, WebActivity::class.java).putExtra(EXTRA_URL, url))
        }
    }
}

/** 开机 / 覆盖安装后按用户开关决定是否自动开始监听。 */
class BootReceiver : android.content.BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val prefs = context.getSharedPreferences(MainActivity.PREFS, Context.MODE_PRIVATE)
        if (prefs.getBoolean(MainActivity.KEY_AUTO_BOOT, false)) {
            PanService.start(context)
        }
    }
}
