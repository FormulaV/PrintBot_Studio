package com.example.printuploader

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.io.FileOutputStream

class MenuActivity : AppCompatActivity() {

    private val PICK_FILE = 1
    private lateinit var apiService: ApiService
    private var baseUrl = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_menu)

        // Ambil baseUrl yang dikirim dari MainActivity
        baseUrl = intent.getStringExtra("BASE_URL") ?: ""

        if (baseUrl.isEmpty()) {
            Toast.makeText(this, "Error: URL Server hilang", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // Inisialisasi ulang Retrofit di halaman ini
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        apiService = retrofit.create(ApiService::class.java)

        val btnMenuPrint = findViewById<LinearLayout>(R.id.btnMenuPrint)
        val btnMenuChatbot = findViewById<LinearLayout>(R.id.btnMenuChatbot)

        // =========================
        // AKSI TOMBOL PRINT
        // =========================
        btnMenuPrint.setOnClickListener {
            val intent = Intent(this, PrintActivity::class.java)
            intent.putExtra("BASE_URL", baseUrl)
            startActivity(intent)
        }

        // =========================
        // AKSI TOMBOL CHATBOT
        // =========================
        btnMenuChatbot.setOnClickListener {
            val intent = Intent(this, ChatActivity::class.java)
            // Bawa baseUrl agar ChatActivity tahu IP server Flask
            intent.putExtra("BASE_URL", baseUrl)
            startActivity(intent)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == PICK_FILE && resultCode == Activity.RESULT_OK) {
            val uri: Uri? = data?.data
            uri?.let { uploadFile(it) }
        }
    }

    private fun uploadFile(uri: Uri) {
        var fileName = "unknown_file"

        val cursor = contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (it.moveToFirst() && nameIndex != -1) {
                fileName = it.getString(nameIndex)
            }
        }

        val inputStream = contentResolver.openInputStream(uri)
        val file = File(cacheDir, fileName)
        val outputStream = FileOutputStream(file)

        inputStream?.copyTo(outputStream)
        outputStream.close()
        inputStream?.close()

        val requestFile = file.asRequestBody("*/*".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", fileName, requestFile)

        Toast.makeText(this, "Mengunggah file...", Toast.LENGTH_SHORT).show()

        apiService.uploadFile(body).enqueue(object : Callback<UploadResponse> {
            override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                Toast.makeText(this@MenuActivity, "Upload sukses: $fileName", Toast.LENGTH_LONG).show()
            }

            override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                Toast.makeText(this@MenuActivity, "Error: ${t.message}", Toast.LENGTH_LONG).show()
            }
        })
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isFinishing) {
            val userId = UserProfileManager.getUserId(this)
            if (userId.isNotBlank()) {
                val thread = Thread {
                    try {
                        apiService.disconnectUser(userId).execute()
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }
                thread.start()
                try {
                    thread.join(500)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
    }
}