# Panduan Lengkap: Kloning, Instalasi, dan Penggunaan Cetakin (Aplikasi Skripsi)

Dokumen ini menjelaskan langkah-langkah lengkap untuk menyiapkan dan menjalankan sistem **Cetakin** dari awal. Sistem ini terdiri dari dua komponen utama:
1. **Desktop Print Server** (Flask Web Server + PyQt5 GUI + RNN Chatbot) yang berjalan di PC/Laptop operator.
2. **Android Client App** (PrintUploader) yang berjalan di handphone pengguna/mahasiswa.

---

## Daftar Isi
1. [Prasyarat Sistem](#prasyarat-sistem)
2. [Langkah 1: Kloning Repository dari GitHub](#langkah-1-kloning-repository-dari-github)
3. [Langkah 2: Instalasi dan Konfigurasi Desktop Print Server](#langkah-2-instalasi-dan-konfigurasi-desktop-print-server)
4. [Langkah 3: Build dan Install Aplikasi Android (Client)](#langkah-3-build-dan-install-aplikasi-android-client)
5. [Langkah 4: Menghubungkan Aplikasi Android ke Print Server](#langkah-4-menghubungkan-aplikasi-android-ke-print-server)
6. [Langkah 5: Alur Penggunaan Aplikasi (Demo)](#langkah-5-alur-penggunaan-aplikasi-demo)
7. [Troubleshooting (Pemecahan Masalah)](#troubleshooting-pemecahan-masalah)

---

## Prasyarat Sistem

Sebelum memulai, pastikan PC/Laptop dan Handphone Anda memiliki *software* berikut:
*   **Untuk PC/Laptop:**
    *   [Git](https://git-scm.com/) (Untuk kloning repository).
    *   [Python 3.9 atau 3.10](https://www.python.org/downloads/) (Direkomendasikan agar kompatibel dengan TensorFlow).
    *   Koneksi internet (untuk mengunduh library python).
    *   Jaringan **Wi-Fi yang sama** untuk PC dan HP agar fitur *auto-discovery* berfungsi.
*   **Untuk Pengembangan Android (HP/Emulator):**
    *   [Android Studio](https://developer.android.com/studio) (Untuk melakukan build & install aplikasi Android).
    *   Handphone Android fisik (lebih direkomendasikan untuk uji coba koneksi Wi-Fi asli) atau emulator dengan setelan network khusus.

---

## Langkah 1: Kloning Repository dari GitHub

1. Buka **Command Prompt (CMD)**, **PowerShell**, atau **Git Bash** di PC Anda.
2. Masuk ke direktori penyimpanan yang Anda inginkan (misalnya `D:\`):
   ```cmd
   cd /d D:\
   ```
3. Jalankan perintah `git clone` untuk mengunduh source code project:
   ```cmd
   git clone https://github.com/FormulaV/PrintBot_Studio.git
   ```
4. Setelah selesai, masuk ke dalam folder hasil kloning:
   ```cmd
   cd AplikasiSkripsi
   ```

---

## Langkah 2: Instalasi dan Konfigurasi Desktop Print Server

Langkah ini dilakukan di PC/Laptop operator yang terhubung ke printer.

### 2.1. Masuk ke Folder `print_server`
Arahkan terminal Anda ke dalam folder `print_server`:
```cmd
cd print_server
```

### 2.2. Membuat Virtual Environment (Sangat Direkomendasikan)
Buat *virtual environment* Python agar library project ini terisolasi dan tidak merusak instalasi library global Anda:
```cmd
python -m venv venv
```

Aktifkan *virtual environment* tersebut:
*   **Command Prompt (CMD):**
    ```cmd
    venv\Scripts\activate
    ```
*   **PowerShell:**
    ```powershell
    .\venv\Scripts\activate
    ```
*(Jika berhasil aktif, akan muncul tulisan `(venv)` di bagian kiri prompt perintah).*

### 2.3. Menginstal Seluruh Dependensi
1. Upgrade package manager `pip` ke versi terbaru terlebih dahulu:
   ```cmd
   python -m pip install --upgrade pip
   ```
2. Instal semua dependensi yang tertera di dalam `requirements.txt`:
   ```cmd
   pip install -r requirements.txt
   ```
   *Catatan: Langkah ini akan mengunduh Flask, TensorFlow, NumPy, PyPDF2, PyMuPDF, PyQt5, python-docx, pywin32, dan requests.*

### 2.4. Registrasi Modul Windows API (`pywin32`)
Karena print server menggunakan modul native Windows API untuk berkomunikasi langsung dengan printer fisik, daftarkan file DLL dengan perintah berikut:
```cmd
python venv\Scripts\pywin32_postinstall.py -install
```

### 2.5. Melatih Model AI Chatbot (Wajib apabila tidak memiliki model .h5)
Sebelum server Flask dijalankan untuk pertama kali, Anda harus melatih (*training*) model chatbot berbasis RNN agar chatbot bisa mengenali intent teks/pesan dari HP.
Jalankan skrip training berikut:
```cmd
python train_chatbot.py
```
*Tunggu hingga proses training selesai (berjalan 12 epoch). Setelah selesai, skrip ini akan menghasilkan file model `chatbot_rnn_model.h5`, file tokenizer, dan file classes di dalam folder `print_server`.*

### 2.6. Menjalankan Desktop Print Server
Sekarang server siap digunakan. Jalankan aplikasi menggunakan file penengah:
```cmd
python run_app.py
```
Aplikasi GUI **PrintBot Studio - Operator** akan terbuka di layar desktop Anda. Tekan tombol **"Start Server"** pada layar awal GUI untuk mengaktifkan web server Flask dan mengaktifkan fitur pencarian otomatis (*UDP Discovery*).

---

## Langkah 3: Build dan Install Aplikasi Android (Client)

Langkah ini dilakukan untuk memasang aplikasi pengunggah dokumen (*PrintUploader*) ke handphone pengguna.

1. Buka aplikasi **Android Studio** di PC Anda.
2. Pilih menu **File > Open**, lalu arahkan ke folder project Android Anda:
   `D:\AplikasiSkripsi\ProjekAndroid\PrintUploader`
3. Tunggu hingga proses *Gradle Sync* dan indeksasi selesai (pastikan PC Anda terhubung ke internet karena Android Studio akan mengunduh dependensi Gradle).
4. Aktifkan mode **Developer Options** dan **USB Debugging** pada handphone Android Anda, lalu sambungkan handphone ke PC menggunakan kabel data.
5. Pada bagian atas Android Studio, pilih perangkat handphone Anda dan klik tombol **Run** (ikon segitiga hijau ⏵).
6. Aplikasi akan terinstal otomatis di handphone dengan nama **PrintUploader**.

---

## Langkah 4: Menghubungkan Aplikasi Android ke Print Server

Untuk menghubungkan handphone ke komputer server tanpa perlu mengetikkan IP address secara manual:

1. **Pastikan PC/Laptop (Server) dan Handphone (Client) tersambung ke jaringan Wi-Fi/Hotspot yang sama.**
2. Di PC Anda, pastikan aplikasi **PrintBot Studio** telah masuk ke menu utama (Server berstatus *Running*).
3. Buka aplikasi **PrintUploader** di handphone.
4. Aplikasi akan secara otomatis menyiarkan sinyal UDP (*auto-discovery*) ke port `50505`.
5. Desktop server akan merespons dengan mengirimkan alamat IP komputer secara otomatis.
6. Handphone akan menampilkan status *"Server ditemukan. Menghubungkan..."* lalu masuk ke halaman registrasi profil/menu utama.
7. Jika koneksi gagal, periksa apakah ada firewall Windows yang memblokir lalu lintas port `5000` (HTTP) dan `50505` (UDP).

---

## Langkah 5: Alur Penggunaan Aplikasi (Demo)

Setelah status koneksi antara handphone dan PC berhasil terjalin:

### 5.1. Di Handphone Pengguna (Android Client):
1. **Membuat Profil:** Masukkan nama Anda jika baru pertama kali membuka aplikasi.
2. **Chatting dengan Chatbot:** Buka menu Chatting. Coba ketikkan pertanyaan seperti:
   * *"Halo"* (sapaan)
   * *"Berapa biaya cetak per halaman?"*
   * *"Printer apa saja yang tersedia?"*
   * Chatbot akan merespons secara real-time berdasarkan hasil training sebelumnya.
3. **Mengunggah File:**
   * Masuk ke menu **Cetak Dokumen** di aplikasi Android.
   * Pilih file dokumen Anda (Format `.pdf` atau `.docx`).
   * Tentukan setelan cetak di HP, misalnya: Halaman yang ingin dicetak (contoh: `1-3`), jumlah rangkap, dan pilihan warna (Grayscale / Color).
   * Klik tombol **Unggah/Kirim**.
4. **Konfirmasi Chatbot:** Setelah file terunggah, chatbot akan mengirimi Anda rincian cetak dan menanyakan persetujuan Anda. Balas dengan mengetik *"Iya"* atau *"Setuju"*.

### 5.2. Di Laptop Operator (Desktop Server):
1. Ketika pengguna mengunggah dokumen, nama pengguna tersebut akan muncul di sidebar **Daftar Chat User** pada aplikasi desktop operator dengan ikon file `📄`.
2. Klik nama pengguna tersebut untuk membuka detail chat.
3. Di panel tengah (**Panel Dokumen**), operator akan disajikan:
   * **Visual Preview** halaman pertama dan halaman selanjutnya dari file PDF yang diunggah.
   * **Metadata file** (Nama, ukuran kb, jenis file, jumlah halaman total).
   * **Instruksi Cetak** yang dikirimkan oleh pengguna secara otomatis terisi pada form (range halaman, rangkap, dan mode warna).
4. Operator memilih printer fisik tujuan pada menu dropdown **Target Printer**.
5. Operator mengklik tombol **"PRINT DOKUMEN"**.
6. Dokumen akan langsung terkirim ke antrean mesin pencetak (*printer spooler* Windows) untuk dicetak secara fisik.
7. Status pencetakan akan dikirimkan kembali ke HP pengguna secara otomatis oleh sistem.

---

## Troubleshooting (Pemecahan Masalah)

### 1. Error: `ModuleNotFoundError: No module named 'tensorflow'`
*   **Penyebab:** Library TensorFlow belum terinstal atau Anda lupa mengaktifkan *virtual environment* (`venv`).
*   **Solusi:** Pastikan terminal menampilkan tulisan `(venv)`. Jika tidak, jalankan perintah `venv\Scripts\activate` lalu ulangi `pip install -r requirements.txt`.

### 2. Handphone Tidak Bisa Menemukan Server (UDP Discovery Gagal)
*   **Penyebab:** Handphone dan PC terhubung ke Wi-Fi yang berbeda, atau Windows Firewall memblokir koneksi UDP/HTTP port server.
*   **Solusi:**
    1. Pastikan kedua perangkat berada di Wi-Fi yang sama (atau nyalakan hotspot di HP dan hubungkan laptop ke hotspot tersebut).
    2. Nonaktifkan sementara Windows Defender Firewall atau buat aturan baru (*Inbound Rules*) di Advanced Security Settings Windows untuk mengizinkan port `5000` (TCP) dan `50505` (UDP).

### 3. Error saat mencetak: `win32print error`
*   **Penyebab:** Driver printer target belum terpasang di Windows atau nama printer tidak cocok.
*   **Solusi:** Pastikan printer Anda sudah terpasang dengan benar di menu *Settings > Devices > Printers & Scanners* pada Windows. Gunakan fitur **"Test Print"** atau **"Cek Koneksi"** pada aplikasi desktop untuk memeriksa kesiapan printer.

### 4. File PDF/Docx Tidak Menampilkan Preview Gambar
*   **Penyebab:** PDF rusak atau modul `fitz` (`PyMuPDF`) gagal mengekstrak halaman.
*   **Solusi:** Pastikan dokumen PDF yang dikirim valid dan tidak ber-password. Untuk file `.docx` (Microsoft Word), sistem akan langsung menggunakan API Windows `ShellExecute` untuk mencetak melalui Microsoft Word secara langsung tanpa preview gambar.
