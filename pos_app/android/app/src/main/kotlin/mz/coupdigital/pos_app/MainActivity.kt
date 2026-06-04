package mz.coupdigital.pos_app

import android.app.Activity
import android.content.Context
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

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
    private var methodChannel: MethodChannel? = null
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
