package com.example.printuploader

data class UploadResponse(
    val status: String,
    val nama_file: String,
    val jenis_file: String,
    val ukuran_kb: Double,
    val jumlah_halaman: Any, // Menggunakan Any karena bisa berupa Int atau String "-"
    val ukuran_kertas: String
)