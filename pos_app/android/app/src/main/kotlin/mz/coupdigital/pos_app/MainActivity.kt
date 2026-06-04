package mz.coupdigital.pos_app

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.Log
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * Native NFC reader-mode bridge for the BuzUp POS.
 *
 * Why native (not the Flutter plugin):
 *  - We need `FLAG_READER_SKIP_NDEF_CHECK` so the OS NEVER falls back to its
 *    "New tag collected" / "Empty Tag" dispatcher for empty / non-NDEF cards.
 *  - We need reader mode to stay engaged across reads (long-lived session)
 *    so the agent can tap card after card without gaps.
 *
 * Flutter calls:
 *   `buzup.nfc#start`  -> enables reader mode while the activity is resumed
 *   `buzup.nfc#stop`   -> disables reader mode
 * Flutter receives:
 *   `onTag` with the UID as an uppercase hex string (no separator).
 */
class MainActivity : FlutterActivity() {

    private val channelName = "buzup.nfc"
    private val installerChannelName = "buzup/installer"
    private var methodChannel: MethodChannel? = null
    private var installerChannel: MethodChannel? = null
    private var nfcAdapter: NfcAdapter? = null
    private var readerEnabled: Boolean = false
    private val uiHandler = Handler(Looper.getMainLooper())

    private val readerCallback = NfcAdapter.ReaderCallback { tag: Tag ->
        val uid = tag.id?.joinToString("") { String.format("%02X", it) } ?: ""
        if (uid.isNotEmpty()) {
            uiHandler.post {
                methodChannel?.invokeMethod("onTag", uid)
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        methodChannel = MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            channelName,
        )
        methodChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "isAvailable" -> result.success(nfcAdapter != null && nfcAdapter?.isEnabled == true)
                "start" -> {
                    enableReaderMode()
                    result.success(readerEnabled)
                }
                "stop" -> {
                    disableReaderMode()
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }

        installerChannel = MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            installerChannelName,
        )
        installerChannel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "installApk" -> {
                    val bytes = call.argument<ByteArray>("bytes")
                    val fileName = call.argument<String>("fileName").orEmpty().ifBlank { "buzup-pos.apk" }
                    if (bytes == null || bytes.isEmpty()) {
                        result.error("install_error", "APK vazio.", null)
                        return@setMethodCallHandler
                    }
                    Thread {
                        try {
                            val apkFile = writePendingApk(bytes, fileName)
                            uiHandler.post {
                                try {
                                    openApkInstaller(apkFile)
                                    result.success(true)
                                } catch (e: Exception) {
                                    Log.e("BUZUP_INSTALLER", "install intent failed", e)
                                    result.error("install_error", e.message, null)
                                }
                            }
                        } catch (e: Exception) {
                            Log.e("BUZUP_INSTALLER", "apk write failed", e)
                            uiHandler.post { result.error("install_error", e.message, null) }
                        }
                    }.start()
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun writePendingApk(bytes: ByteArray, fileName: String): File {
        val safe = fileName.replace(Regex("[^A-Za-z0-9._-]"), "_").ifBlank { "buzup-pos.apk" }
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

    override fun onResume() {
        super.onResume()
        if (readerEnabled) {
            enableReaderMode() // re-arm after the activity comes back to foreground
        }
    }

    override fun onPause() {
        if (readerEnabled) {
            // Keep readerEnabled=true so onResume re-arms; just remove the
            // adapter's reader to avoid leaks while paused.
            nfcAdapter?.disableReaderMode(this)
        }
        super.onPause()
    }

    override fun onDestroy() {
        try {
            nfcAdapter?.disableReaderMode(this)
        } catch (_: Throwable) {}
        methodChannel?.setMethodCallHandler(null)
        installerChannel?.setMethodCallHandler(null)
        super.onDestroy()
    }

    private fun enableReaderMode() {
        val adapter = nfcAdapter ?: return
        val flags = (NfcAdapter.FLAG_READER_NFC_A
                or NfcAdapter.FLAG_READER_NFC_B
                or NfcAdapter.FLAG_READER_NFC_F
                or NfcAdapter.FLAG_READER_NFC_V
                or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK)
        val extras = Bundle().apply {
            // 0 -> system default (~125 ms). Higher means we wait longer
            // before re-firing for the same card; small values improve
            // perceived responsiveness.
            putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY, 250)
        }
        adapter.enableReaderMode(this, readerCallback, flags, extras)
        readerEnabled = true
    }

    private fun disableReaderMode() {
        val adapter = nfcAdapter ?: return
        try {
            adapter.disableReaderMode(this)
        } catch (_: Throwable) {}
        readerEnabled = false
    }
}
