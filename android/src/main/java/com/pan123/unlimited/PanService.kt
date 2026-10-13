package com.pan123.unlimited

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * 常驻前台服务：CPython + waitress 跑在进程内的后台线程里，
 * 通知栏实时显示面板和 WebDAV 地址，带一个"停止"按钮。
 */
class PanService : Service() {

    private val executor = Executors.newSingleThreadExecutor()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        becomeForeground(getString(R.string.starting))
        when (intent?.action) {
            ACTION_STOP -> requestStop()
            ACTION_RESTART -> requestRestart()
            else -> requestStart()
        }
        // 被系统回收后自动重启（重启后 intent 为空，走 requestStart 重新监听）
        return START_STICKY
    }

    override fun onDestroy() {
        // 进程还活着，必须真的把服务关掉，否则端口和 sqlite 句柄会一直悬着
        executor.execute { PanPython.call("stop") }
        executor.shutdown()
        super.onDestroy()
    }

    private fun requestStart() {
        executor.execute {
            val context = applicationContext
            val webui = Webui.extract(context)
            show(PanPython.call("start", Paths.dataDir(context), webui))
        }
    }

    private fun requestRestart() {
        executor.execute {
            val context = applicationContext
            val webui = Webui.extract(context)
            show(PanPython.call("restart", Paths.dataDir(context), webui))
        }
    }

    private fun requestStop() {
        executor.execute {
            PanPython.call("stop")
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private fun show(result: JSONObject) {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (result.optBoolean("ok")) {
            val text = "面板  " + result.optString("panelUrl") + "\nWebDAV  " + result.optString("webdavUrl")
            manager.notify(NOTIFICATION_ID, buildNotification("123Pan 正在运行", text))
        } else {
            manager.notify(
                NOTIFICATION_ID,
                buildNotification("123Pan 启动失败", result.optString("error"))
            )
        }
    }

    private fun becomeForeground(text: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW
            )
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(channel)
        }
        startForeground(NOTIFICATION_ID, buildNotification("123Pan", text))
    }

    private fun buildNotification(title: String, text: String): Notification {
        val openMain = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), pendingFlags()
        )
        val stopIntent = PendingIntent.getService(
            this, 1, Intent(this, PanService::class.java).setAction(ACTION_STOP), pendingFlags()
        )

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setSmallIcon(R.drawable.ic_stat_pan)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setContentIntent(openMain)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(R.drawable.ic_stat_pan, getString(R.string.stop), stopIntent)
            .build()
    }

    private fun pendingFlags(): Int =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }

    companion object {
        const val ACTION_STOP = "com.pan123.unlimited.STOP"
        const val ACTION_RESTART = "com.pan123.unlimited.RESTART"
        private const val CHANNEL_ID = "pan_service"
        private const val NOTIFICATION_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, PanService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun restart(context: Context) {
            val intent = Intent(context, PanService::class.java).setAction(ACTION_RESTART)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(Intent(context, PanService::class.java).setAction(ACTION_STOP))
        }
    }
}
