package com.pan123.unlimited

import android.content.Context
import android.content.res.AssetManager
import java.io.File

/**
 * Flask 的模板和静态文件打包在 assets/webui 里，运行时解压到应用目录，
 * 再通过 PAN123_WEBUI_DIR 告诉 Python 侧去哪找它们。
 */
object Webui {
    private const val ASSET_ROOT = "webui"

    fun extract(context: Context): String {
        val root = File(Paths.webuiDir(context))
        val stamp = File(root, ".stamp")
        val version = try {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: "0"
        } catch (e: Exception) {
            "0"
        }
        if (stamp.exists() && stamp.readText() == version) return root.absolutePath

        root.deleteRecursively()
        root.mkdirs()
        copyDir(context.assets, ASSET_ROOT, root)
        stamp.writeText(version)
        return root.absolutePath
    }

    private fun copyDir(assets: AssetManager, path: String, target: File) {
        val children = assets.list(path) ?: return
        if (children.isEmpty()) return
        target.mkdirs()
        for (name in children) {
            val childPath = "$path/$name"
            val grandChildren = assets.list(childPath)
            if (grandChildren != null && grandChildren.isNotEmpty()) {
                copyDir(assets, childPath, File(target, name))
            } else {
                assets.open(childPath).use { input ->
                    File(target, name).outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
            }
        }
    }
}
