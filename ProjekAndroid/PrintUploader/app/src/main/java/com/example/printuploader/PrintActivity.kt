package com.example.printuploader

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
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

class PrintActivity : AppCompatActivity() {

    private val PICK_PDF = 2
    private lateinit var apiService: ApiService
    private var baseUrl = ""
    private var userId = ""

    // UI Components
    private lateinit var ivPreview: ImageView
    private lateinit var btnPrev: Button
    private lateinit var btnNext: Button
    private lateinit var tvPageInfo: TextView
    private lateinit var etPageRange: EditText
    private lateinit var etCopies: EditText
    private lateinit var spColorMode: Spinner
    private lateinit var btnExecutePrint: Button
    private lateinit var layoutFileInfo: LinearLayout
    private lateinit var tvFileDetails: TextView
    private lateinit var spPrinter: Spinner

    // PDF Renderer Variables
    private var pdfRenderer: PdfRenderer? = null
    private var currentPageRenderer: PdfRenderer.Page? = null
    private var cachedPdfFile: File? = null

    // State Variables (Menyamakan dengan Desktop PC)
    private var totalPages = 0
    private var currentPage = 0
    private var pageStart = 0
    private var pageEnd = 0
    private var currentFileName = ""
    private var selectedPrinter = ""
    private var printerNames = emptyList<String>()
    private var pageIndices = emptyList<Int>()
    private var currentPageIdx = 0
    private var copies = 1
    private var colorMode = "Grayscale"
    private var isProgrammaticColorSelection = false
    private var isProgrammaticPrinterSelection = false
    private val colorOptions = listOf("Grayscale", "Color")

    private val statePollHandler = Handler(Looper.getMainLooper())
    private var lastStateCommandId = -1

    private val statePollRunnable = object : Runnable {
        override fun run() {
            pollServerState()
            statePollHandler.postDelayed(this, 3000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_print)

        baseUrl = intent.getStringExtra("BASE_URL") ?: ""
        userId = UserProfileManager.getUserId(this)

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        apiService = retrofit.create(ApiService::class.java)

        // Init UI
        val btnSelectFile = findViewById<LinearLayout>(R.id.btnSelectFile)
        val btnBackPrint = findViewById<ImageButton>(R.id.btnBackPrint)
        ivPreview = findViewById(R.id.ivPreview)
        btnPrev = findViewById(R.id.btnPrev)
        btnNext = findViewById(R.id.btnNext)
        tvPageInfo = findViewById(R.id.tvPageInfo)
        etPageRange = findViewById(R.id.etPageRange)
        etCopies = findViewById(R.id.etCopies)
        spColorMode = findViewById(R.id.spColorMode)
        layoutFileInfo = findViewById(R.id.layoutFileInfo)
        tvFileDetails = findViewById(R.id.tvFileDetails)
        spPrinter = findViewById(R.id.spPrinter)
        val btnApplyRange = findViewById<Button>(R.id.btnApplyRange)
        val btnApplyCopies = findViewById<Button>(R.id.btnApplyCopies)
        btnExecutePrint = findViewById(R.id.btnExecutePrint)

        val colorAdapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, colorOptions)
        colorAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spColorMode.adapter = colorAdapter

        spColorMode.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                if (isProgrammaticColorSelection) {
                    isProgrammaticColorSelection = false
                    return
                }
                val selected = colorOptions[position]
                if (selected != colorMode) {
                    colorMode = selected
                    sendRemoteState(execute = false)
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        spPrinter.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                if (isProgrammaticPrinterSelection) {
                    isProgrammaticPrinterSelection = false
                    return
                }
                if (position in printerNames.indices) {
                    val selected = printerNames[position]
                    if (selected != selectedPrinter) {
                        selectedPrinter = selected
                        sendRemoteState(execute = false)
                    }
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        loadPrinters()

        btnBackPrint.setOnClickListener {
            finish()
        }

        btnSelectFile.setOnClickListener {
            val intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.type = "application/pdf" // Batasi hanya PDF
            startActivityForResult(intent, PICK_PDF)
        }

        btnPrev.setOnClickListener {
            if (pageIndices.isNotEmpty() && currentPageIdx > 0) {
                currentPageIdx--
                currentPage = pageIndices[currentPageIdx]
                renderPdfPage(currentPage)
            }
        }

        btnNext.setOnClickListener {
            if (pageIndices.isNotEmpty() && currentPageIdx < pageIndices.size - 1) {
                currentPageIdx++
                currentPage = pageIndices[currentPageIdx]
                renderPdfPage(currentPage)
            }
        }

        // Terapkan Range Halaman secara manual
        btnApplyRange.setOnClickListener {
            applyPageRange()
        }

        btnApplyCopies.setOnClickListener {
            applyCopies()
        }

        btnExecutePrint.setOnClickListener {
            selectedPrinter = selectedPrinterFromSpinner()
            if (selectedPrinter.isEmpty()) {
                Toast.makeText(this, "Belum ada printer yang dipilih dari PC", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Langsung eksekusi print di PC
            sendRemoteState(execute = true)
        }
    }

    private fun loadPrinters() {
        apiService.getPrinters().enqueue(object : Callback<PrinterResponse> {
            override fun onResponse(call: Call<PrinterResponse>, response: Response<PrinterResponse>) {
                val res = response.body()
                val printers = when {
                    !res?.usable_printers.isNullOrEmpty() -> res!!.usable_printers
                    !res?.printers.isNullOrEmpty() -> res!!.printers
                    else -> emptyList()
                }
                printerNames = printers
                val pdfPrinters = res?.pdf_printers ?: emptyList()
                val readyPrinters = res?.ready_printers ?: emptyList()
                val labels = printers.map { printer ->
                    val status = when {
                        pdfPrinters.contains(printer) -> "Save/Print to PDF"
                        readyPrinters.contains(printer) -> "Aktif di PC"
                        else -> "Terdeteksi"
                    }
                    "$printer - $status"
                }
                val adapter = ArrayAdapter(
                    this@PrintActivity,
                    android.R.layout.simple_spinner_item,
                    labels
                )
                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                spPrinter.adapter = adapter

                selectedPrinter = res?.selected_printer ?: ""
                val selectedIndex = printerNames.indexOf(selectedPrinter)
                if (selectedIndex >= 0 && selectedIndex != spPrinter.selectedItemPosition) {
                    isProgrammaticPrinterSelection = true
                    spPrinter.setSelection(selectedIndex)
                }
            }

            override fun onFailure(call: Call<PrinterResponse>, t: Throwable) {
                Toast.makeText(this@PrintActivity, "Gagal mengambil daftar printer PC", Toast.LENGTH_SHORT).show()
            }
        })
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == PICK_PDF && resultCode == Activity.RESULT_OK) {
            data?.data?.let { uri ->
                loadPdfFromUri(uri)
            }
        }
    }

    private fun loadPdfFromUri(uri: Uri) {
        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (it.moveToFirst() && nameIndex != -1) {
                currentFileName = it.getString(nameIndex)
            }
        }

        cachedPdfFile = File(cacheDir, currentFileName)
        val inputStream = contentResolver.openInputStream(uri)
        val outputStream = FileOutputStream(cachedPdfFile)
        inputStream?.copyTo(outputStream)
        outputStream.close()
        inputStream?.close()

        try {
            val fileDescriptor = ParcelFileDescriptor.open(cachedPdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
            pdfRenderer?.close()
            pdfRenderer = PdfRenderer(fileDescriptor)

            totalPages = pdfRenderer!!.pageCount
            pageStart = 0
            pageEnd = totalPages - 1
            currentPage = 0
            pageIndices = (0 until totalPages).toList()
            currentPageIdx = 0
            etPageRange.setText("")
            copies = 1
            etCopies.setText("1")

            // Reset Info Layout saat memuat file baru
            layoutFileInfo.visibility = android.view.View.GONE

            renderPdfPage(currentPage)

            // [BARU] LANGSUNG UPLOAD AGAR PC BISA MUNCUL PREVIEW
            uploadFileBackground(cachedPdfFile!!)

        } catch (e: Exception) {
            Toast.makeText(this, "Gagal memuat PDF: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun uploadFileBackground(file: File) {
        val requestFile = file.asRequestBody("application/pdf".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", currentFileName, requestFile)

        Toast.makeText(this, "Mengirim ke Desktop...", Toast.LENGTH_SHORT).show()

        val callback = object : Callback<UploadResponse> {
            override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                val res = response.body()

                if (response.isSuccessful && res != null) {
                    Toast.makeText(this@PrintActivity, "Terkoneksi dengan Layar PC!", Toast.LENGTH_SHORT).show()
                    btnExecutePrint.isEnabled = true

                    // [BARU] Munculkan layout info dan set teksnya
                    layoutFileInfo.visibility = android.view.View.VISIBLE

                    val infoText = """
                        Nama File: ${res.nama_file}
                        Ukuran: ${res.ukuran_kb} KB
                        Halaman: ${res.jumlah_halaman}
                        Kertas: ${res.ukuran_kertas}
                        Jenis: ${res.jenis_file.uppercase()}
                    """.trimIndent()

                    tvFileDetails.text = infoText
                }
            }

            override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                Toast.makeText(this@PrintActivity, "Gagal kirim ke PC: ${t.message}", Toast.LENGTH_LONG).show()
            }
        }

        if (userId.isNotBlank()) {
            val userIdBody = userId.toRequestBody("text/plain".toMediaTypeOrNull())
            apiService.uploadFileWithUser(body, userIdBody).enqueue(callback)
        } else {
            apiService.uploadFile(body).enqueue(callback)
        }
    }

    private fun sendRemoteState(execute: Boolean) {
        if (currentFileName.isEmpty()) return

        selectedPrinter = selectedPrinterFromSpinner().ifBlank { selectedPrinter }

        val pagesText = formatPageRangeText(pageIndices, totalPages)
        val request = StateRequest(
            nama_file = currentFileName,
            page_start = pageStart,
            page_end = pageEnd,
            execute_print = execute,
            printer_name = selectedPrinter,
            copies = copies,
            color_mode = colorMode,
            page_indices = pageIndices,
            pages = pagesText,
            user_id = userId
        )

        apiService.updateState(request).enqueue(object : Callback<UpdateStateResponse> {
            override fun onResponse(call: Call<UpdateStateResponse>, response: Response<UpdateStateResponse>) {
                if (response.isSuccessful) {
                    val res = response.body()
                    res?.state?.let { serverState ->
                        lastStateCommandId = serverState.command_id
                    }
                }
                if (execute) {
                    Toast.makeText(this@PrintActivity, "Memerintahkan PC untuk Cetak...", Toast.LENGTH_LONG).show()
                }
            }
            override fun onFailure(call: Call<UpdateStateResponse>, t: Throwable) {
                Toast.makeText(this@PrintActivity, "Koneksi terputus: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun selectedPrinterFromSpinner(): String {
        val index = spPrinter.selectedItemPosition
        return if (index in printerNames.indices) {
            printerNames[index]
        } else {
            spPrinter.selectedItem?.toString()?.substringBefore(" - ") ?: ""
        }
    }

    private fun renderPdfPage(pageIndex: Int) {
        if (pdfRenderer == null || pageIndex < 0 || pageIndex >= totalPages) return

        // Tutup halaman sebelumnya
        currentPageRenderer?.close()

        // Buka halaman baru
        currentPageRenderer = pdfRenderer!!.openPage(pageIndex)
        val page = currentPageRenderer!!

        // Buat bitmap (ukuran dikali 2 agar tidak pecah/blur di HP)
        val bitmap = Bitmap.createBitmap(
            page.width * 2,
            page.height * 2,
            Bitmap.Config.ARGB_8888
        )

        // Render PDF ke warna latar putih (defaultnya transparan)
        bitmap.eraseColor(Color.WHITE)
        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

        ivPreview.setImageBitmap(bitmap)

        if (pageIndices.contains(pageIndex)) {
            currentPageIdx = pageIndices.indexOf(pageIndex)
        }

        updateNavState()
    }

    private fun applyPageRange() {
        if (pdfRenderer == null) return

        val text = etPageRange.text.toString().trim()

        if (text.isEmpty()) {
            pageStart = 0
            pageEnd = totalPages - 1
            currentPage = 0
            pageIndices = (0 until totalPages).toList()
            currentPageIdx = 0
            renderPdfPage(currentPage)
            return
        }

        try {
            val selected = ArrayList<Int>()
            val maxIndex = totalPages - 1
            for (part in text.split(Regex("[,;]"))) {
                val trimmed = part.trim()
                if (trimmed.isEmpty()) continue
                if ("-" in trimmed) {
                    val bounds = trimmed.split("-")
                    val start = (bounds[0].toInt() - 1).coerceIn(0, maxIndex)
                    val end = (bounds[1].toInt() - 1).coerceIn(start, maxIndex)
                    for (i in start..end) {
                        selected.add(i)
                    }
                } else {
                    val num = (trimmed.toInt() - 1).coerceIn(0, maxIndex)
                    selected.add(num)
                }
            }

            val uniqueSorted = selected.distinct().sorted()
            if (uniqueSorted.isEmpty()) {
                pageStart = 0
                pageEnd = totalPages - 1
                currentPage = 0
                pageIndices = (0 until totalPages).toList()
                currentPageIdx = 0
            } else {
                pageIndices = uniqueSorted
                pageStart = pageIndices.first()
                pageEnd = pageIndices.last()
                currentPage = pageStart
                currentPageIdx = 0
            }

        } catch (e: Exception) {
            Toast.makeText(this, "Format salah. Contoh: 1,3,5 atau 1-3", Toast.LENGTH_SHORT).show()
            etPageRange.setText("")
            pageStart = 0
            pageEnd = totalPages - 1
            currentPage = 0
            pageIndices = (0 until totalPages).toList()
            currentPageIdx = 0
        }

        renderPdfPage(currentPage)

        // [BARU] Kirim perubahan ke PC
        sendRemoteState(execute = false)
    }

    private fun updateNavState() {
        if (pageIndices.isEmpty()) {
            btnPrev.isEnabled = false
            btnNext.isEnabled = false
            tvPageInfo.text = "Page: 0 / 0"
            return
        }

        // Kontrol Tombol
        btnPrev.isEnabled = currentPageIdx > 0
        btnNext.isEnabled = currentPageIdx < pageIndices.size - 1

        // Kontrol Teks Info (Sama seperti PC)
        val displayPage = currentPage + 1
        val input = etPageRange.text.toString().trim()

        if (input.isEmpty()) {
            tvPageInfo.text = "Page: $displayPage / $totalPages"
        } else {
            val totalSelected = pageIndices.size
            tvPageInfo.text = "Page: $displayPage ($totalSelected halaman terpilih)"
        }
    }

    private fun formatPageRangeText(indices: List<Int>, totalPagesCount: Int): String {
        if (indices.size == totalPagesCount && indices == (0 until totalPagesCount).toList()) {
            return ""
        }
        var isContiguous = true
        for (i in 1 until indices.size) {
            if (indices[i] != indices[i - 1] + 1) {
                isContiguous = false
                break
            }
        }
        return if (isContiguous) {
            if (indices.size == 1) {
                "${indices[0] + 1}"
            } else {
                "${indices.first() + 1}-${indices.last() + 1}"
            }
        } else {
            indices.map { it + 1 }.joinToString(",")
        }
    }

    private fun executeUploadAndPrint(file: File) {
        val requestFile = file.asRequestBody("application/pdf".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", currentFileName, requestFile)

        Toast.makeText(this, "Mengirim ke server...", Toast.LENGTH_SHORT).show()

        // Saat ini mengeksekusi upload.
        // Karena di PC menggunakan sistem polling (10 detik terakhir), PC akan
        // otomatis menerima file ini dan operator di PC tinggal meng-klik Print.
        apiService.uploadFile(body).enqueue(object : Callback<UploadResponse> {
            override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                Toast.makeText(this@PrintActivity, "File berhasil dikirim ke Desktop!", Toast.LENGTH_LONG).show()
            }

            override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                Toast.makeText(this@PrintActivity, "Error: ${t.message}", Toast.LENGTH_LONG).show()
            }
        })
    }

    override fun onResume() {
        super.onResume()
        statePollHandler.post(statePollRunnable)
    }

    override fun onPause() {
        super.onPause()
        statePollHandler.removeCallbacks(statePollRunnable)
    }

    private fun pollServerState() {
        val stateCall = if (userId.isNotBlank()) apiService.getStateForUser(userId) else apiService.getState()
        stateCall.enqueue(object : Callback<RemoteStateResponse> {
            override fun onResponse(call: Call<RemoteStateResponse>, response: Response<RemoteStateResponse>) {
                val state = response.body() ?: return
                if (state.nama_file.isNullOrBlank()) {
                    if (currentFileName.isNotEmpty()) {
                        resetPrintActivityUI()
                    }
                    return
                }

                if (state.command_id != lastStateCommandId || state.nama_file != currentFileName) {
                    val isNewFile = state.nama_file != currentFileName
                    lastStateCommandId = state.command_id
                    currentFileName = state.nama_file

                    fetchFileMetadataAndSync(state, isNewFile)
                }
            }

            override fun onFailure(call: Call<RemoteStateResponse>, t: Throwable) {
                // Ignore failure in background
            }
        })
    }

    private fun fetchFileMetadataAndSync(state: RemoteStateResponse, isNewFile: Boolean) {
        val metadataCall = if (userId.isNotBlank()) apiService.getLatestFileForUser(userId) else apiService.getLatestFile()
        metadataCall.enqueue(object : Callback<FileMetadataResponse> {
            override fun onResponse(call: Call<FileMetadataResponse>, response: Response<FileMetadataResponse>) {
                val metadata = response.body() ?: return

                if (isNewFile || pdfRenderer == null) {
                    val fileName = state.nama_file ?: return
                    downloadFileFromServer(fileName) { file ->
                        if (file != null) {
                            cachedPdfFile = file
                            loadPdfFromFile(file, state, metadata)
                        } else {
                            Toast.makeText(this@PrintActivity, "Gagal sinkron file PDF dari server", Toast.LENGTH_SHORT).show()
                        }
                    }
                } else {
                    totalPages = pdfRenderer?.pageCount ?: 0
                    if (totalPages > 0) {
                        val remoteIndices = state.page_indices
                        if (remoteIndices != null && remoteIndices.isNotEmpty()) {
                            pageIndices = remoteIndices.map { it.coerceIn(0, totalPages - 1) }
                            pageStart = pageIndices.first()
                            pageEnd = pageIndices.last()
                            currentPage = pageStart
                            currentPageIdx = 0
                        } else {
                            pageStart = state.page_start.coerceIn(0, totalPages - 1)
                            pageEnd = state.page_end.coerceIn(pageStart, totalPages - 1)
                            pageIndices = (pageStart..pageEnd).toList()
                            currentPage = pageStart
                            currentPageIdx = 0
                        }

                        val rangeText = state.pages ?: formatPageRangeText(pageIndices, totalPages)
                        etPageRange.setText(rangeText)

                        renderPdfPage(currentPage)
                    }

                    val sizeKb = metadata.ukuran_file_kb?.toString() ?: "-"
                    val infoText = """
                        Nama File: ${metadata.nama_file ?: "-"}
                        Ukuran: ${sizeKb} KB
                        Halaman: ${metadata.jumlah_halaman ?: "-"}
                        Kertas: ${metadata.ukuran_kertas ?: "-"}
                        Jenis: ${metadata.jenis_file?.uppercase() ?: "-"}
                    """.trimIndent()
                    tvFileDetails.text = infoText
                    layoutFileInfo.visibility = android.view.View.VISIBLE

                    state.printer_name?.let { pName ->
                        if (pName.isNotEmpty() && printerNames.isNotEmpty()) {
                            val index = printerNames.indexOf(pName)
                            if (index >= 0 && index != spPrinter.selectedItemPosition) {
                                isProgrammaticPrinterSelection = true
                                spPrinter.setSelection(index)
                            }
                        }
                        copies = state.copies
                        etCopies.setText(copies.toString())
                    }

                    state.color_mode?.let { cMode ->
                        if (cMode.isNotEmpty() && cMode != colorMode) {
                            colorMode = cMode
                            val index = colorOptions.indexOf(cMode)
                            if (index >= 0 && index != spColorMode.selectedItemPosition) {
                                isProgrammaticColorSelection = true
                                spColorMode.setSelection(index)
                            }
                        }
                    }
                }
            }

            override fun onFailure(call: Call<FileMetadataResponse>, t: Throwable) {
                // Fail silently
            }
        })
    }

    private fun downloadFileFromServer(fileName: String, callback: (File?) -> Unit) {
        val fileUrl = "${baseUrl.removeSuffix("/")}/uploads/$fileName"
        Thread {
            try {
                val url = java.net.URL(fileUrl)
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.requestMethod = "GET"
                connection.connect()

                if (connection.responseCode == 200) {
                    val cacheFile = File(cacheDir, fileName)
                    connection.inputStream.use { input ->
                        FileOutputStream(cacheFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                    runOnUiThread { callback(cacheFile) }
                } else {
                    runOnUiThread { callback(null) }
                }
            } catch (e: Exception) {
                e.printStackTrace()
                runOnUiThread { callback(null) }
            }
        }.start()
    }

    private fun loadPdfFromFile(file: File, remoteState: RemoteStateResponse?, metadata: FileMetadataResponse?) {
        try {
            val fileDescriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            pdfRenderer?.close()
            pdfRenderer = PdfRenderer(fileDescriptor)

            totalPages = pdfRenderer!!.pageCount

            if (remoteState != null) {
                val remoteIndices = remoteState.page_indices
                if (remoteIndices != null && remoteIndices.isNotEmpty()) {
                    pageIndices = remoteIndices.map { it.coerceIn(0, totalPages - 1) }
                    pageStart = pageIndices.first()
                    pageEnd = pageIndices.last()
                    currentPage = pageStart
                    currentPageIdx = 0
                } else {
                    pageStart = remoteState.page_start.coerceIn(0, totalPages - 1)
                    pageEnd = remoteState.page_end.coerceIn(pageStart, totalPages - 1)
                    pageIndices = (pageStart..pageEnd).toList()
                    currentPage = pageStart
                    currentPageIdx = 0
                }

                val rangeText = remoteState.pages ?: formatPageRangeText(pageIndices, totalPages)
                etPageRange.setText(rangeText)
                copies = remoteState.copies
                etCopies.setText(copies.toString())
                
                colorMode = remoteState.color_mode ?: "Grayscale"
                val colorIndex = colorOptions.indexOf(colorMode)
                if (colorIndex >= 0 && colorIndex != spColorMode.selectedItemPosition) {
                    isProgrammaticColorSelection = true
                    spColorMode.setSelection(colorIndex)
                }
            } else {
                pageStart = 0
                pageEnd = totalPages - 1
                currentPage = 0
                pageIndices = (0 until totalPages).toList()
                currentPageIdx = 0
                etPageRange.setText("")
                copies = 1
                etCopies.setText("1")
                
                colorMode = "Grayscale"
                if (spColorMode.selectedItemPosition != 0) {
                    isProgrammaticColorSelection = true
                    spColorMode.setSelection(0)
                }
            }

            renderPdfPage(currentPage)

            if (metadata != null) {
                layoutFileInfo.visibility = android.view.View.VISIBLE
                val sizeKb = metadata.ukuran_file_kb?.toString() ?: "-"
                val infoText = """
                    Nama File: ${metadata.nama_file ?: "-"}
                    Ukuran: ${sizeKb} KB
                    Halaman: ${metadata.jumlah_halaman ?: "-"}
                    Kertas: ${metadata.ukuran_kertas ?: "-"}
                    Jenis: ${metadata.jenis_file?.uppercase() ?: "-"}
                """.trimIndent()
                tvFileDetails.text = infoText
            } else {
                layoutFileInfo.visibility = android.view.View.GONE
            }

            remoteState?.printer_name?.let { pName ->
                if (pName.isNotEmpty() && printerNames.isNotEmpty()) {
                    val index = printerNames.indexOf(pName)
                    if (index >= 0 && index != spPrinter.selectedItemPosition) {
                        isProgrammaticPrinterSelection = true
                        spPrinter.setSelection(index)
                    }
                }
            }

            btnExecutePrint.isEnabled = true

        } catch (e: Exception) {
            Toast.makeText(this, "Gagal memuat PDF: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun applyCopies() {
        val copiesStr = etCopies.text.toString().trim()
        if (copiesStr.isNotEmpty()) {
            val parsed = copiesStr.toIntOrNull()
            if (parsed != null && parsed > 0) {
                copies = parsed
                sendRemoteState(execute = false)
                Toast.makeText(this, "Jumlah rangkap diubah ke $copies", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "Masukkan jumlah rangkap yang valid", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun resetPrintActivityUI() {
        runOnUiThread {
            try {
                currentPageRenderer?.close()
            } catch (e: Exception) {}
            currentPageRenderer = null
            try {
                pdfRenderer?.close()
            } catch (e: Exception) {}
            pdfRenderer = null
            
            totalPages = 0
            currentPage = 0
            pageStart = 0
            pageEnd = 0
            currentFileName = ""
            pageIndices = emptyList()
            currentPageIdx = 0
            cachedPdfFile = null
            copies = 1
            colorMode = "Grayscale"
            isProgrammaticColorSelection = true
            spColorMode.setSelection(0)
            
            ivPreview.setImageBitmap(null)
            tvPageInfo.text = "Page: 0/0"
            etPageRange.setText("")
            etCopies.setText("")
            layoutFileInfo.visibility = android.view.View.GONE
            tvFileDetails.text = ""
            btnExecutePrint.isEnabled = false
            btnPrev.isEnabled = false
            btnNext.isEnabled = false
            
            Toast.makeText(this@PrintActivity, "Dokumen dihapus oleh operator PC", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        currentPageRenderer?.close()
        pdfRenderer?.close()
    }
}
