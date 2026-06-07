package com.example.printuploader

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ProfileSetupActivity : AppCompatActivity() {

    private var baseUrl = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_profile_setup)

        baseUrl = intent.getStringExtra("BASE_URL") ?: ""

        val etName = findViewById<EditText>(R.id.etProfileName)
        val btnContinue = findViewById<Button>(R.id.btnContinue)

        btnContinue.setOnClickListener {
            val name = etName.text.toString().trim()
            if (name.length < 2) {
                Toast.makeText(this, "Nama harus minimal 2 karakter", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Save profile locally
            UserProfileManager.saveProfile(this, name)

            // Register user to server
            registerUserToServer(name)
        }
    }

    private fun registerUserToServer(userName: String) {
        if (baseUrl.isEmpty()) {
            proceedToMenu()
            return
        }

        try {
            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            val apiService = retrofit.create(ApiService::class.java)

            val userId = UserProfileManager.getUserId(this)
            val request = RegisterUserRequest(userId, userName)

            apiService.registerUser(request).enqueue(object : Callback<Map<String, Any>> {
                override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {
                    proceedToMenu()
                }

                override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {
                    // Still proceed even if registration fails — it will retry later
                    proceedToMenu()
                }
            })
        } catch (e: Exception) {
            proceedToMenu()
        }
    }

    private fun proceedToMenu() {
        Toast.makeText(this, "Selamat datang, ${UserProfileManager.getUserName(this)}!", Toast.LENGTH_SHORT).show()
        val intent = Intent(this, MenuActivity::class.java)
        intent.putExtra("BASE_URL", baseUrl)
        startActivity(intent)
        finish()
    }
}
