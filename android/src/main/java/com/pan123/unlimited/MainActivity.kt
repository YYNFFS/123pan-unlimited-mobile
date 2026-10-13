package com.pan123.unlimited

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : Activity() {

    @Volatile private var polling = false
    private var last: JSONObject = JSONObject()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        askNotificationPermission()

        findViewById<Button>(R.id.toggleButton).setOnClickListener {
            if (last.optBoolean("running")) PanService.stop(this) else PanService.start(this)
        }
        findViewById<Button>(R.id.panelButton).setOnClickListener { openPanel() }
        findViewById<Button>(R.id.settingsButton).setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }
        findViewById<Button>(R.id.copyButton).setOnClickListener { copyUrls() }
        findViewById<Button>(R.id.logButton).setOnClickListener { showLog() }
        findViewById<Button>(R.id.downloadButton).setOnClickListener { downloadDatabase() }

        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        findViewById<Switch>(R.id.bootSwitch).apply {
            isChecked = prefs.getBoolean(KEY_AUTO_BOOT, false)
            setOnCheckedChangeListener { _, checked ->
                prefs.edit().putBoolean(KEY_AUTO_BOOT, checked).apply()
            }
        }

        // 打开 App 即开始监听
        PanService.start(this)
    }

    override fun onResume() {
        super.onResume()
        polling = true
        Thread {
            while (polling) {
                val result = PanPython.call("status")
                runOnUiThread { apply(result) }
                try {
                    Thread.sleep(2000)
                } catch (e: InterruptedException) {
                    return@Thread
                }
            }
        }.start()
    }

    override fun onPause() {
        polling = false
        super.onPause()
    }

    private fun apply(result: JSONObject) {
        last = result
        findViewById<TextView>(R.id.statusText).text =
            if (result.optBoolean("running")) "服务运行中" else "服务未运行"

        val urls = StringBuilder()
        urls.append("本机面板   ").append(result.optString("localUrl")).append("\n")
        urls.append("局域网面板 ").append(result.optString("panelUrl")).append("\n")
        urls.append("WebDAV     ").append(result.optString("webdavUrl")).append("\n")
        urls.append("管理后台   ").append(result.optString("panelUrl")).append(result.optString("adminPath")).append("/login")
        findViewById<TextView>(R.id.urlText).text = urls.toString()

        findViewById<Button>(R.id.toggleButton).setText(
            if (result.optBoolean("running")) R.string.stop else R.string.start
        )

        val hint = if (result.optString("host") == "127.0.0.1") {
            "当前仅手机本机可访问。要让电视/盒子连，去设置里打开「局域网共享」。"
        } else {
            "播放器里填 WebDAV 地址，用户名密码在设置页。手机需和播放器连同一个 WiFi。"
        }
        findViewById<TextView>(R.id.hintText).text = hint
    }

    private fun openPanel() {
        val url = last.optString("localUrl")
        if (url.isEmpty()) {
            toast("服务还没起来")
            return
        }
        startActivity(Intent(this, WebActivity::class.java).putExtra(WebActivity.EXTRA_URL, url))
    }

    private fun copyUrls() {
        val text = findViewById<TextView>(R.id.urlText).text.toString()
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("123Pan", text))
        toast("地址已复制")
    }

    private fun showLog() {
        val scroll = findViewById<ScrollView>(R.id.logScroll)
        if (scroll.visibility == ScrollView.VISIBLE) {
            scroll.visibility = ScrollView.GONE
            return
        }
        scroll.visibility = ScrollView.VISIBLE
        Thread {
            val day = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())
            val file = File(File(Paths.dataDir(this), "logs"), "$day.log")
            val tail = if (file.exists()) {
                val lines = file.readLines()
                lines.takeLast(200).joinToString("\n")
            } else {
                "还没有日志文件"
            }
            runOnUiThread {
                findViewById<TextView>(R.id.logText).text = tail
                scroll.post { scroll.fullScroll(ScrollView.FOCUS_DOWN) }
            }
        }.start()
    }

    private fun downloadDatabase() {
        toast("开始下载公共库，别切后台")
        Thread {
            val result = PanPython.call("download_database", Paths.dataDir(this))
            runOnUiThread {
                toast(if (result.optBoolean("ok")) result.optString("message") else result.optString("error"))
            }
        }.start()
    }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    private fun toast(text: String) {
        Toast.makeText(this, text, Toast.LENGTH_LONG).show()
    }

    companion object {
        const val PREFS = "pan"
        const val KEY_AUTO_BOOT = "auto_boot"
    }
}
