package mz.coupdigital.buzup_mobile

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

private const val INSTALLER_CHANNEL = "buzup/installer"
private const val LOG_TAG = "BUZUP_INSTALLER"

class MainActivity : FlutterActivity() {

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, INSTALLER_CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "installApk" -> {
                        val bytes = call.argument<ByteArray>("bytes")
                        val fileName = call.argument<String>("fileName").orEmpty().ifBlank { "buzup.apk" }
                        if (bytes == null || bytes.isEmpty()) {
                            result.error("install_error", "APK vazio.", null)
                            return@setMethodCallHandler
                        }
                        Thread {
                            try {
                                val apkFile = writePendingApk(bytes, fileName)
                                runOnUiThread {
                                    try {
                                        openApkInstaller(apkFile)
                                        result.success(true)
                                    } catch (e: Exception) {
                                        Log.e(LOG_TAG, "install intent failed", e)
                                        result.error("install_error", e.message, null)
                                    }
                                }
                            } catch (e: Exception) {
                                Log.e(LOG_TAG, "apk write failed", e)
                                runOnUiThread { result.error("install_error", e.message, null) }
                            }
                        }.start()
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun writePendingApk(bytes: ByteArray, fileName: String): File {
        val safe = fileName.replace(Regex("[^A-Za-z0-9._-]"), "_").ifBlank { "buzup.apk" }
        val dir = File(cacheDir, "updates")
        if (!dir.exists()) dir.mkdirs()
        val apk = File(dir, safe)
        FileOutputStream(apk).use { it.write(bytes); it.flush() }
        return apk
    }

    private fun openApkInstaller(apkFile: File) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !packageManager.canRequestPackageInstalls()) {
            val settings = Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:$packageName"),
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(settings)
            throw IOException("Autorize a instalacao de apps do BuzUp e tente novamente.")
        }
        val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            FileProvider.getUriForFile(this, "$packageName.fileprovider", apkFile)
        } else {
            Uri.fromFile(apkFile)
        }
        val install = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(install)
    }
}
