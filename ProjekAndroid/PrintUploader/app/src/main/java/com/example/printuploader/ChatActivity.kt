package com.example.printuploader

import android.Manifest
import android.app.Activity
import android.app.DownloadManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.RingtoneManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import android.widget.EditText
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.floatingactionbutton.FloatingActionButton
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.io.FileOutputStream

class ChatActivity : AppCompatActivity() {

    private val PICK_PDF_CHAT = 3
    private val botDelayMillis = 1000L
    private val fileDetailDelayMillis = 3500L
    private val notificationChannelId = "cetakin_chat_messages"

    private lateinit var apiService: ApiService
    private var baseUrl = ""

    // User profile
    private var userId = ""
    private var userName = ""

    private lateinit var chatAdapter: ChatAdapter
    private lateinit var messageList: ArrayList<ChatMessage>
    private lateinit var rvChat: RecyclerView
    private val handler = Handler(Looper.getMainLooper())
    private var pendingUploadFile: File? = null
    private var pendingUploadFileName: String = ""
    private var waitingPrinterReconnect = false
    private var isChatVisible = false
    private var isServerConnected = true

    private val healthCheckRunnable = object : Runnable {
        override fun run() {
            val runnable = this
            apiService.checkServer(userId).enqueue(object : Callback<Map<String, String>> {
                override fun onResponse(call: Call<Map<String, String>>, response: Response<Map<String, String>>) {
                    if (response.isSuccessful) {
                        isServerConnected = true
                    } else {
                        handleServerDisconnected()
                    }
                    handler.postDelayed(runnable, 2000L)
                }
                override fun onFailure(call: Call<Map<String, String>>, t: Throwable) {
                    handleServerDisconnected()
                    handler.postDelayed(runnable, 2000L)
                }
            })
        }
    }

    private fun handleServerDisconnected() {
        if (isServerConnected) {
            isServerConnected = false
            addSystemMessage("Server telah dinonaktifkan")
        }
    }

    private fun addSystemMessage(text: String) {
        if (messageList.isNotEmpty() &&
            messageList.last().type == ChatAdapter.TYPE_SYSTEM &&
            messageList.last().text == text
        ) {
            return
        }
        messageList.add(ChatMessage(text = text, isUser = false, type = ChatAdapter.TYPE_SYSTEM))
        chatAdapter.notifyItemInserted(messageList.size - 1)
        rvChat.scrollToPosition(messageList.size - 1)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chat)
        isChatVisible = true
        createNotificationChannel()
        requestNotificationPermissionIfNeeded()

        baseUrl = intent.getStringExtra("BASE_URL") ?: ""
        
        // Load user profile
        userId = UserProfileManager.getUserId(this)
        userName = UserProfileManager.getUserName(this)
        
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        apiService = retrofit.create(ApiService::class.java)

        val etMessage = findViewById<EditText>(R.id.etMessage)
        val btnSend = findViewById<FloatingActionButton>(R.id.btnSend)
        val btnAttachPdf = findViewById<ImageButton>(R.id.btnAttachPdf)
        val btnBackChat = findViewById<ImageButton>(R.id.btnBackChat)

        rvChat = findViewById(R.id.rvChat)
        messageList = ChatSessionStore.messages
        chatAdapter = ChatAdapter(messageList) { message ->
            downloadBotFile(message)
        }

        val layoutManager = LinearLayoutManager(this)
        layoutManager.stackFromEnd = true
        rvChat.layoutManager = layoutManager
        rvChat.adapter = chatAdapter
        chatAdapter.notifyDataSetChanged()

        if (!ChatSessionStore.greeted) {
            val greeting = if (userName.isNotBlank()) {
                "Halo $userName! Saya Cetakin Dong. Kirim PDF dulu, nanti saya cek printer dan bantu susun instruksi cetaknya."
            } else {
                "Halo! Saya Cetakin Dong. Kirim PDF dulu, nanti saya cek printer dan bantu susun instruksi cetaknya."
            }
            addMessage(greeting, isUser = false)
            ChatSessionStore.greeted = true
        } else if (messageList.isNotEmpty()) {
            rvChat.scrollToPosition(messageList.size - 1)
        }

        // Register user to server (fire-and-forget, ensures server knows this user)
        if (userId.isNotBlank()) {
            val request = RegisterUserRequest(userId, userName)
            apiService.registerUser(request).enqueue(object : Callback<Map<String, Any>> {
                override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {}
                override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {}
            })
        }

        btnSend.setOnClickListener {
            val msg = etMessage.text.toString().trim()
            if (msg.isNotEmpty()) {
                etMessage.setText("")
                addMessage(msg, isUser = true)
                sendToBot(msg)
            }
        }

        btnAttachPdf.setOnClickListener {
            val intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.type = "application/pdf"
            startActivityForResult(intent, PICK_PDF_CHAT)
        }

        btnBackChat.setOnClickListener {
            finish()
        }
    }

    private fun sendToBot(message: String) {
        if (waitingPrinterReconnect && isPrinterRetryMessage(message)) {
            showBotMessageWithDelay("Baik kak, saya cek ulang koneksi printer di PC...") {
                checkPrinterAndUploadPendingFile()
            }
            return
        }

        val typingIndex = addTypingMessage()
        val request = ChatRequest(message, userId)

        apiService.sendMessageToBot(request).enqueue(object : Callback<ChatResponse> {
            override fun onResponse(call: Call<ChatResponse>, response: Response<ChatResponse>) {
                val botReply = if (response.isSuccessful && response.body() != null) {
                    response.body()!!.response
                } else {
                    "Maaf, Cetakin Dong belum bisa membaca respon server."
                }

                val chatResponse = response.body()
                val shouldPollPrint = chatResponse?.action == "print_started"
                val pdfReady = chatResponse?.action == "pdf_ready" &&
                    !chatResponse.file_name.isNullOrBlank() &&
                    !chatResponse.file_url.isNullOrBlank()
                showBotReplyAfterDelay(typingIndex, botReply) {
                    if (shouldPollPrint) {
                        waitForPrintFinished()
                    } else if (pdfReady) {
                        addBotFileMessage(
                            chatResponse!!.file_name!!,
                            "PDF siap diunduh",
                            chatResponse.file_url!!
                        )
                    }
                }
            }

            override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                showBotReplyAfterDelay(typingIndex, "Maaf, koneksi ke server terputus.")
            }
        })
    }

    private fun uploadFileToChatServer(file: File, fileName: String) {
        val requestFile = file.asRequestBody("application/pdf".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", fileName, requestFile)

        if (userId.isNotBlank()) {
            val userIdBody = userId.toRequestBody("text/plain".toMediaTypeOrNull())
            apiService.uploadFileWithUser(body, userIdBody).enqueue(object : Callback<UploadResponse> {
                override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                    handleUploadResponse(response)
                }
                override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                    showBotMessageWithDelay("Maaf, file gagal dikirim ke server: ${t.message}")
                }
            })
        } else {
            apiService.uploadFile(body).enqueue(object : Callback<UploadResponse> {
                override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                    handleUploadResponse(response)
                }
                override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                    showBotMessageWithDelay("Maaf, file gagal dikirim ke server: ${t.message}")
                }
            })
        }
    }

    private fun handleUploadResponse(response: Response<UploadResponse>) {
        if (response.isSuccessful && response.body() != null) {
            showBotMessageWithDelay(formatFileDetail(response.body()!!), fileDetailDelayMillis) {
                showBotMessageWithDelay(
                    "Sekarang tuliskan instruksi cetaknya ya kak. Berikut beberapa contoh cara memberikan instruksi yang benar:\n" +
                    "1. \"Cetak warna, halaman 1-5, 2 rangkap\"\n" +
                    "2. \"Hitam putih, semua halaman, 1 rangkap, A4\"\n" +
                    "3. \"Print halaman 2, 4 rangkap, bolak-balik\""
                )
            }
        } else {
            showBotMessageWithDelay("Maaf, file belum berhasil dicek oleh server.")
        }
    }

    private fun waitForPrintFinished(attempt: Int = 0) {
        if (attempt == 0) {
            showBotMessageWithDelay("Saya tunggu sampai proses cetaknya selesai ya kak...")
        }

        handler.postDelayed({
            val statusCall = if (userId.isNotBlank()) {
                apiService.getPrintStatusForUser(userId)
            } else {
                apiService.getPrintStatus()
            }
            statusCall.enqueue(object : Callback<PrintStatusResponse> {
                override fun onResponse(
                    call: Call<PrintStatusResponse>,
                    response: Response<PrintStatusResponse>
                ) {
                    val status = response.body()
                    when (status?.status) {
                        "done" -> {
                            val printerName = status.printer_name.ifBlank { "printer yang dipilih" }
                            showBotMessageWithDelay(
                                "File telah berhasil dicetak ✅\nSilahkan diambil pada printer $printerName"
                            )
                        }
                        "error" -> {
                            showBotMessageWithDelay("Maaf kak, proses cetak gagal: ${status.message}")
                        }
                        else -> {
                            if (attempt < 30) {
                                waitForPrintFinished(attempt + 1)
                            } else {
                                showBotMessageWithDelay("Proses cetak masih berjalan. Silakan cek layar PC atau printer yang dipilih ya kak.")
                            }
                        }
                    }
                }

                override fun onFailure(call: Call<PrintStatusResponse>, t: Throwable) {
                    if (attempt < 30) {
                        waitForPrintFinished(attempt + 1)
                    } else {
                        showBotMessageWithDelay("Saya belum bisa membaca status cetak dari PC. Silakan cek printer yang dipilih ya kak.")
                    }
                }
            })
        }, 1500L)
    }

    private fun formatFileDetail(res: UploadResponse): String {
        return """
            File berhasil dicek! Ini dia detail dari file tersebut:
            - Nama: ${res.nama_file}
            - Besar File: ${res.ukuran_kb} KB
            - Jumlah Halaman: ${res.jumlah_halaman}
            - Ukuran Kertas: ${res.ukuran_kertas}
            - Jenis File: ${res.jenis_file.uppercase()}
        """.trimIndent()
    }

    private fun syncMessageToServer(sender: String, message: String) {
        val req = AppendChatRequest(sender, message, userId)
        apiService.appendChat(req).enqueue(object : Callback<Map<String, Any>> {
            override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {}
            override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {}
        })
    }

    private fun addMessage(text: String, isUser: Boolean) {
        messageList.add(ChatMessage(text, isUser))
        chatAdapter.notifyItemInserted(messageList.size - 1)
        rvChat.scrollToPosition(messageList.size - 1)
        if (!isUser) {
            showIncomingChatNotification(text)
        }
        syncMessageToServer(if (isUser) "user" else "bot", text)
    }

    private fun addFileMessage(fileName: String, fileSize: String) {
        messageList.add(
            ChatMessage(
                text = fileName,
                isUser = true,
                type = ChatAdapter.TYPE_FILE,
                fileName = fileName,
                fileSize = fileSize
            )
        )
        chatAdapter.notifyItemInserted(messageList.size - 1)
        rvChat.scrollToPosition(messageList.size - 1)
        syncMessageToServer("user", "Mengirim file: $fileName ($fileSize)")
    }

    private fun addBotFileMessage(fileName: String, fileSize: String, fileUrl: String) {
        messageList.add(
            ChatMessage(
                text = fileName,
                isUser = false,
                type = ChatAdapter.TYPE_BOT_FILE,
                fileName = fileName,
                fileSize = fileSize,
                fileUrl = fileUrl
            )
        )
        chatAdapter.notifyItemInserted(messageList.size - 1)
        rvChat.scrollToPosition(messageList.size - 1)
        showIncomingChatNotification("File PDF siap diunduh: $fileName")
        syncMessageToServer("bot", "File PDF siap diunduh: $fileName")
    }

    private fun addTypingMessage(): Int {
        messageList.add(
            ChatMessage(
                text = "Cetakin Dong sedang mengetik...",
                isUser = false,
                type = ChatAdapter.TYPE_TYPING
            )
        )
        val position = messageList.size - 1
        chatAdapter.notifyItemInserted(position)
        rvChat.scrollToPosition(position)
        return position
    }

    private fun showBotMessageWithDelay(text: String, afterShown: (() -> Unit)? = null) {
        val typingIndex = addTypingMessage()
        showBotReplyAfterDelay(typingIndex, text, afterShown = afterShown)
    }

    private fun showBotMessageWithDelay(
        text: String,
        delayMillis: Long,
        afterShown: (() -> Unit)? = null
    ) {
        val typingIndex = addTypingMessage()
        showBotReplyAfterDelay(typingIndex, text, delayMillis, afterShown)
    }

    private fun showBotReplyAfterDelay(
        typingIndex: Int,
        text: String,
        delayMillis: Long = botDelayMillis,
        afterShown: (() -> Unit)? = null
    ) {
        handler.postDelayed({
            removeTypingMessage(typingIndex)
            addMessage(text, isUser = false)
            afterShown?.invoke()
        }, delayMillis)
    }

    private fun removeTypingMessage(position: Int) {
        if (
            position in messageList.indices &&
            messageList[position].type == ChatAdapter.TYPE_TYPING
        ) {
            messageList.removeAt(position)
            chatAdapter.notifyItemRemoved(position)
            return
        }

        val fallbackPosition = messageList.indexOfFirst { it.type == ChatAdapter.TYPE_TYPING }
        if (fallbackPosition != -1) {
            messageList.removeAt(fallbackPosition)
            chatAdapter.notifyItemRemoved(fallbackPosition)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == PICK_PDF_CHAT && resultCode == Activity.RESULT_OK) {
            data?.data?.let { uri ->
                handleSelectedPdf(uri)
            }
        }
    }

    private fun handleSelectedPdf(uri: Uri) {
        val fileName = getFileName(uri)
        val fileSize = getFileSizeLabel(uri)
        val cachedFile = copyUriToCache(uri, fileName)

        if (cachedFile == null) {
            showBotMessageWithDelay("Maaf, file tidak bisa dibaca. Coba pilih file PDF lain ya.")
            return
        }

        addFileMessage(fileName, fileSize)
        pendingUploadFile = cachedFile
        pendingUploadFileName = fileName
        showBotMessageWithDelay("File diterima. Saya cek dulu apakah printer di PC sedang siap...") {
            checkPrinterAndUploadPendingFile()
        }
    }

    private fun checkPrinterAndUploadPendingFile() {
        apiService.getPrinters().enqueue(object : Callback<PrinterResponse> {
            override fun onResponse(call: Call<PrinterResponse>, response: Response<PrinterResponse>) {
                val res = response.body()
                val hasPrinter = response.isSuccessful && res?.connected == true
                if (!hasPrinter) {
                    waitingPrinterReconnect = true
                    showBotMessageWithDelay("Printer sedang tidak tersambung, mohon segera kontak kepada operator. Kalau sudah dicek, balas \"coba cek lagi\" ya kak.")
                    return
                }

                val file = pendingUploadFile
                val fileName = pendingUploadFileName
                if (file == null || fileName.isBlank()) {
                    showBotMessageWithDelay("Printer sudah terdeteksi, tapi file sebelumnya tidak bisa saya baca lagi. Tolong lampirkan ulang ya kak.")
                    return
                }

                waitingPrinterReconnect = false
                showBotMessageWithDelay("Printer terhubung! Saya lanjut membaca detail file dulu...") {
                    uploadFileToChatServer(file, fileName)
                }
            }

            override fun onFailure(call: Call<PrinterResponse>, t: Throwable) {
                waitingPrinterReconnect = true
                showBotMessageWithDelay("Saya belum bisa mengecek printer dari PC. Mohon kontak operator, lalu balas \"coba cek lagi\" setelah PC/printer siap.")
            }
        })
    }

    private fun isPrinterRetryMessage(message: String): Boolean {
        val text = message.lowercase()
        return listOf("cek", "coba", "lagi", "ulang", "printer", "sudah", "ready", "siap").any { it in text }
    }

    private fun formatPrinterOptions(res: PrinterResponse?): String {
        val printers = when {
            !res?.usable_printers.isNullOrEmpty() -> res!!.usable_printers
            !res?.printers.isNullOrEmpty() -> res!!.printers
            else -> emptyList()
        }

        if (printers.isEmpty()) {
            return "Printer PC belum terdeteksi."
        }

        val pdfPrinters = res?.pdf_printers ?: emptyList()
        val lines = printers.mapIndexed { index, printerName ->
            val marker = if (pdfPrinters.contains(printerName)) " (Save/Print to PDF)" else ""
            "${index + 1}. $printerName$marker"
        }
        return "Printer yang tersedia di PC:\n${lines.joinToString("\n")}\nBalas nomor printer atau nama printernya untuk memilih."
    }

    private fun copyUriToCache(uri: Uri, fileName: String): File? {
        return try {
            val safeFileName = fileName.ifBlank { "dokumen.pdf" }
            val outputFile = File(cacheDir, safeFileName)

            contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(outputFile).use { output ->
                    input.copyTo(output)
                }
            } ?: return null

            outputFile
        } catch (e: Exception) {
            Toast.makeText(this, "Gagal membaca file: ${e.message}", Toast.LENGTH_SHORT).show()
            null
        }
    }

    private fun getFileName(uri: Uri): String {
        var result = "dokumen.pdf"
        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (it.moveToFirst() && nameIndex != -1) {
                result = it.getString(nameIndex)
            }
        }
        return result
    }

    private fun getFileSizeLabel(uri: Uri): String {
        var sizeBytes = 0L
        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            val sizeIndex = it.getColumnIndex(OpenableColumns.SIZE)
            if (it.moveToFirst() && sizeIndex != -1 && !it.isNull(sizeIndex)) {
                sizeBytes = it.getLong(sizeIndex)
            }
        }

        if (sizeBytes <= 0L) return "Ukuran tidak diketahui"

        val sizeKb = sizeBytes / 1024.0
        return if (sizeKb < 1024) {
            String.format("%.1f KB", sizeKb)
        } else {
            String.format("%.2f MB", sizeKb / 1024.0)
        }
    }

    private fun downloadBotFile(message: ChatMessage) {
        if (message.fileUrl.isBlank()) {
            Toast.makeText(this, "Link download belum tersedia.", Toast.LENGTH_SHORT).show()
            return
        }

        try {
            val request = DownloadManager.Request(Uri.parse(message.fileUrl))
                .setTitle(message.fileName.ifBlank { "CetakinDong.pdf" })
                .setDescription("Mengunduh file dari Cetakin Dong")
                .setMimeType("application/pdf")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(
                    Environment.DIRECTORY_DOWNLOADS,
                    message.fileName.ifBlank { "CetakinBot.pdf" }
                )
                .setAllowedOverMetered(true)
                .setAllowedOverRoaming(true)

            val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            manager.enqueue(request)
            Toast.makeText(this, "File disimpan ke folder Download.", Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            Toast.makeText(this, "Gagal mulai download: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    override fun onResume() {
        super.onResume()
        isChatVisible = true
        isServerConnected = true
        handler.removeCallbacks(healthCheckRunnable)
        handler.post(healthCheckRunnable)
    }

    override fun onPause() {
        super.onPause()
        isChatVisible = false
        handler.removeCallbacks(healthCheckRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                notificationChannelId,
                "Pesan Cetakin Dong",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifikasi pesan masuk dari Cetakin Dong"
                setSound(null, null)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 42)
        }
    }

    private fun showIncomingChatNotification(text: String) {
        if (isChatVisible) return
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val intent = Intent(this, ChatActivity::class.java).apply {
            putExtra("BASE_URL", baseUrl)
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            7,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, notificationChannelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Pesan masuk dari Cetakin Dong")
            .setContentText(text.take(90))
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setDefaults(NotificationCompat.DEFAULT_SOUND or NotificationCompat.DEFAULT_VIBRATE)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        playCustomNotificationTone()
        NotificationManagerCompat.from(this).notify(1007, notification)
    }

    private fun playCustomNotificationTone() {
        try {
            val tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 70)
            tone.startTone(ToneGenerator.TONE_PROP_ACK, 120)
            handler.postDelayed({
                tone.startTone(ToneGenerator.TONE_PROP_BEEP2, 100)
                handler.postDelayed({ tone.release() }, 180L)
            }, 140L)
        } catch (_: Exception) {
        }
    }
}
