package com.example.printuploader
import okhttp3.MultipartBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

data class StateRequest(
    val nama_file: String,
    val page_start: Int,
    val page_end: Int,
    val execute_print: Boolean,
    val printer_name: String = "",
    val color_mode: String = "Grayscale",
    val copies: Int = 1,
    val page_indices: List<Int>? = null,
    val pages: String? = null,
    val user_id: String = ""
)

data class ChatRequest(val message: String, val user_id: String = "")
data class ChatResponse(
    val response: String,
    val action: String? = null,
    val printer_name: String? = null,
    val file_name: String? = null,
    val file_url: String? = null
)

data class PrinterResponse(
    val printers: List<String>,
    val ready_printers: List<String> = emptyList(),
    val pdf_printers: List<String> = emptyList(),
    val usable_printers: List<String> = emptyList(),
    val selected_printer: String,
    val connected: Boolean = false,
    val message: String = ""
)

data class PrintStatusResponse(
    val status: String,
    val message: String,
    val printer_name: String,
    val command_id: Int
)

data class AppendChatRequest(val sender: String, val message: String, val user_id: String = "")

data class RegisterUserRequest(val user_id: String, val user_name: String)

data class RemoteStateResponse(
    val nama_file: String?,
    val page_start: Int,
    val page_end: Int,
    val execute_print: Boolean,
    val printer_name: String?,
    val color_mode: String?,
    val copies: Int,
    val page_indices: List<Int>?,
    val pages: String?,
    val command_id: Int
)

data class FileMetadataResponse(
    val id: Int?,
    val nama_file: String?,
    val jenis_file: String?,
    val ukuran_file_kb: Any?,
    val jumlah_halaman: Any?,
    val ukuran_kertas: String?,
    val waktu_upload: String?
)

interface ApiService {

    @Multipart
    @POST("upload")
    fun uploadFile(
        @Part file: MultipartBody.Part
    ): Call<UploadResponse>

    @Multipart
    @POST("upload")
    fun uploadFileWithUser(
        @Part file: MultipartBody.Part,
        @Part("user_id") userId: okhttp3.RequestBody
    ): Call<UploadResponse>

    @GET("ping")
    fun checkServer(@Query("user_id") userId: String?): Call<Map<String, String>>

    @POST("/update_state")
    fun updateState(@Body request: StateRequest): Call<Map<String, Any>>

    @POST("/chat")
    fun sendMessageToBot(@Body request: ChatRequest): Call<ChatResponse>

    @GET("/printers")
    fun getPrinters(): Call<PrinterResponse>

    @GET("/print_status")
    fun getPrintStatus(): Call<PrintStatusResponse>

    @GET("/print_status")
    fun getPrintStatusForUser(@Query("user_id") userId: String): Call<PrintStatusResponse>

    @POST("/append_chat")
    fun appendChat(@Body request: AppendChatRequest): Call<Map<String, Any>>

    @GET("/get_state")
    fun getState(): Call<RemoteStateResponse>

    @GET("/get_state")
    fun getStateForUser(@Query("user_id") userId: String): Call<RemoteStateResponse>

    @GET("/data_json")
    fun getLatestFile(): Call<FileMetadataResponse>

    @GET("/data_json")
    fun getLatestFileForUser(@Query("user_id") userId: String): Call<FileMetadataResponse>

    @POST("/register_user")
    fun registerUser(@Body request: RegisterUserRequest): Call<Map<String, Any>>

    @POST("/disconnect")
    fun disconnectUser(@Query("user_id") userId: String): Call<Map<String, Any>>
}
