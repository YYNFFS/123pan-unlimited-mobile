package com.pan123.unlimited

import android.app.Application
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File

/** CPython 必须在任何 Python 调用之前启动，放在 Application.onCreate 里最稳。 */
class PanApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
    }
}

/** Kotlin 与 app/android_entry.py 之间唯一的桥，出入参都是 JSON 字符串。 */
object PanPython {
    private fun entry(): PyObject = Python.getInstance().getModule("android_entry")

    fun call(name: String, vararg args: Any): JSONObject {
        return try {
            JSONObject(entry().callAttr(name, *args).toString())
        } catch (e: Throwable) {
            JSONObject().put("ok", false).put("error", e.javaClass.name + ": " + e.message)
        }
    }
}

object Paths {
    fun dataDir(context: android.content.Context): String =
        File(context.filesDir, "pan").absolutePath

    fun webuiDir(context: android.content.Context): String =
        File(context.filesDir, "webui").absolutePath
}
