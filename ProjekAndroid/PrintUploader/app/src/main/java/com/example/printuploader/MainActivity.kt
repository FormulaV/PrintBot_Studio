package com.example.printuploader

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

class MainActivity : AppCompatActivity() {

    private lateinit var apiService: ApiService
    private lateinit var tvConnectionStatus: TextView
    private var baseUrl = ""
    private var isConnecting = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val btnConnect = findViewById<Button>(R.id.btnConnect)
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus)

        btnConnect.setOnClickListener {
            discoverServerAutomatically()
        }

        discoverServerAutomatically()
    }

    private fun discoverServerAutomatically() {
        if (isConnecting) return
        isConnecting = true
        tvConnectionStatus.text = "Mencari print server otomatis..."

        Thread {
            try {
                DatagramSocket().use { socket ->
                    socket.broadcast = true
                    socket.soTimeout = 4000

                    val requestData = "CETAKIN_DISCOVER".toByteArray()
                    val requestPacket = DatagramPacket(
                        requestData,
                        requestData.size,
                        InetAddress.getByName("255.255.255.255"),
                        50505
                    )
                    socket.send(requestPacket)

                    val buffer = ByteArray(1024)
                    val responsePacket = DatagramPacket(buffer, buffer.size)
                    socket.receive(responsePacket)

                    val payload = String(responsePacket.data, 0, responsePacket.length)
                    val discoveredUrl = JSONObject(payload).getString("base_url")

                    runOnUiThread {
                        tvConnectionStatus.text = "Server ditemukan. Menghubungkan..."
                        connectToServer(discoveredUrl)
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    isConnecting = false
                    tvConnectionStatus.text = "Server belum ditemukan. Pastikan PC dan HP berada di Wi-Fi yang sama, lalu tekan Reconnect."
                }
            }
        }.start()
    }

    private fun connectToServer(url: String) {
        baseUrl = url
        tvConnectionStatus.text = "Menghubungkan ke $baseUrl"

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        apiService = retrofit.create(ApiService::class.java)
        testConnection()
    }

    private fun testConnection() {
        apiService.checkServer(null).enqueue(object : Callback<Map<String, String>> {
            override fun onResponse(
                call: Call<Map<String, String>>,
                response: Response<Map<String, String>>
            ) {
                isConnecting = false
                if (response.isSuccessful) {
                    Toast.makeText(this@MainActivity, "Terhubung dengan desktop!", Toast.LENGTH_SHORT).show()

                    // Check if profile is already set up
                    if (UserProfileManager.hasProfile(this@MainActivity)) {
                        // Profile exists → register user to server and go to Menu
                        registerAndProceed()
                    } else {
                        // No profile → go to ProfileSetupActivity
                        val intent = Intent(this@MainActivity, ProfileSetupActivity::class.java)
                        intent.putExtra("BASE_URL", baseUrl)
                        startActivity(intent)
                        finish()
                    }
                } else {
                    tvConnectionStatus.text = "Server tidak merespon. Coba Connect manual."
                }
            }

            override fun onFailure(call: Call<Map<String, String>>, t: Throwable) {
                isConnecting = false
                tvConnectionStatus.text = "Gagal koneksi: ${t.message}"
            }
        })
    }

    private fun registerAndProceed() {
        val userId = UserProfileManager.getUserId(this)
        val userName = UserProfileManager.getUserName(this)

        // Register user to server (fire-and-forget)
        val request = RegisterUserRequest(userId, userName)
        apiService.registerUser(request).enqueue(object : Callback<Map<String, Any>> {
            override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {}
            override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {}
        })

        val intent = Intent(this@MainActivity, MenuActivity::class.java)
        intent.putExtra("BASE_URL", baseUrl)
        startActivity(intent)
        finish()
    }
}
