package com.pan123.unlimited

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

class SettingsActivity : Activity() {

    private var loaded = JSONObject()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        findViewById<Button>(R.id.saveButton).setOnClickListener { save() }

        Thread {
            // init 只负责把数据目录告诉 Python，不会启动服务
            PanPython.call("init", Paths.dataDir(this), Paths.webuiDir(this))
            val result = PanPython.call("read_settings")
            runOnUiThread { fill(result) }
        }.start()
    }

    private fun fill(result: JSONObject) {
        if (!result.optBoolean("ok")) {
            Toast.makeText(this, result.optString("error"), Toast.LENGTH_LONG).show()
            return
        }
        loaded = result.optJSONObject("settings") ?: JSONObject()
        findViewById<TextView>(R.id.settingsHint).text =
            "配置文件：" + result.optString("path")

        findViewById<Switch>(R.id.lanSwitch).isChecked =
            loaded.optString("BIND_HOST") == "0.0.0.0"
        findViewById<EditText>(R.id.portInput).setText(loaded.optInt("PORT", 33333).toString())
        findViewById<EditText>(R.id.panUserInput).setText(loaded.optString("123PAN_USERNAME"))
        findViewById<EditText>(R.id.panPassInput).setText(loaded.optString("123PAN_PASSWORD"))
        findViewById<EditText>(R.id.davUserInput).setText(loaded.optString("WEBDAV_USERNAME"))
        findViewById<EditText>(R.id.davPassInput).setText(loaded.optString("WEBDAV_PASSWORD"))
        findViewById<EditText>(R.id.adminUserInput).setText(loaded.optString("ADMIN_USERNAME"))
        findViewById<EditText>(R.id.adminPassInput).setText(loaded.optString("ADMIN_PASSWORD"))
        findViewById<Switch>(R.id.splitSwitch).isChecked = loaded.optBoolean("SPLIT_FOLDER", false)
        findViewById<TextView>(R.id.adminPathText).text =
            "后台登录地址：/" + loaded.optString("ADMIN_ENTRY") + "/login"
    }

    private fun save() {
        val settings = JSONObject(loaded.toString())
        settings.put("BIND_HOST", if (findViewById<Switch>(R.id.lanSwitch).isChecked) "0.0.0.0" else "127.0.0.1")
        settings.put("PORT", findViewById<EditText>(R.id.portInput).text.toString().trim().toIntOrNull() ?: 0)
        settings.put("123PAN_USERNAME", findViewById<EditText>(R.id.panUserInput).text.toString().trim())
        settings.put("123PAN_PASSWORD", findViewById<EditText>(R.id.panPassInput).text.toString())
        settings.put("WEBDAV_USERNAME", findViewById<EditText>(R.id.davUserInput).text.toString().trim())
        settings.put("WEBDAV_PASSWORD", findViewById<EditText>(R.id.davPassInput).text.toString())
        settings.put("ADMIN_USERNAME", findViewById<EditText>(R.id.adminUserInput).text.toString().trim())
        settings.put("ADMIN_PASSWORD", findViewById<EditText>(R.id.adminPassInput).text.toString())
        settings.put("SPLIT_FOLDER", findViewById<Switch>(R.id.splitSwitch).isChecked)

        Thread {
            val result = PanPython.call("write_settings", settings.toString())
            runOnUiThread {
                Toast.makeText(this, if (result.optBoolean("ok")) "已保存" else result.optString("error"),
                    Toast.LENGTH_LONG).show()
                if (result.optBoolean("ok")) {
                    loaded = result.optJSONObject("settings") ?: loaded
                    PanService.restart(this)
                    finish()
                }
            }
        }.start()
    }
}
