
package com.example.printuploader

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.util.UUID

/**
 * Manages user profile (name + unique device ID) stored in internal file storage.
 * 
 * Key design decisions:
 * - Uses internal file storage (context.filesDir) NOT SharedPreferences
 * - This ensures the profile does NOT transfer when the APK is shared to another device
 * - Each device gets a unique UUID generated at first setup
 * - If the app is uninstalled and reinstalled, the profile is lost → user must re-enter
 */
object UserProfileManager {

    private const val PROFILE_FILE_NAME = "user_profile.json"
    private const val KEY_USER_ID = "user_id"
    private const val KEY_USER_NAME = "user_name"

    private fun getProfileFile(context: Context): File {
        return File(context.filesDir, PROFILE_FILE_NAME)
    }

    /**
     * Check if a profile has been set up on this device.
     */
    fun hasProfile(context: Context): Boolean {
        val file = getProfileFile(context)
        if (!file.exists()) return false
        return try {
            val json = JSONObject(file.readText())
            json.has(KEY_USER_ID) && json.has(KEY_USER_NAME) &&
                json.getString(KEY_USER_NAME).isNotBlank()
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Save profile with given name. Generates a unique UUID for this device.
     */
    fun saveProfile(context: Context, userName: String) {
        val userId = UUID.randomUUID().toString()
        val json = JSONObject().apply {
            put(KEY_USER_ID, userId)
            put(KEY_USER_NAME, userName.trim())
        }
        getProfileFile(context).writeText(json.toString())
    }

    /**
     * Get the stored user ID (UUID), or empty string if not set.
     */
    fun getUserId(context: Context): String {
        return try {
            val file = getProfileFile(context)
            if (!file.exists()) return ""
            val json = JSONObject(file.readText())
            json.optString(KEY_USER_ID, "")
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * Get the stored user name, or empty string if not set.
     */
    fun getUserName(context: Context): String {
        return try {
            val file = getProfileFile(context)
            if (!file.exists()) return ""
            val json = JSONObject(file.readText())
            json.optString(KEY_USER_NAME, "")
        } catch (e: Exception) {
            ""
        }
    }
}
