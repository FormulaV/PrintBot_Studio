# 🏗️ Arsitektur Sistem: Print Server (Python) + Android App (Kotlin)

## 📊 Diagram Arsitektur End-to-End Lengkap

```mermaid
graph TB
    subgraph User["👤 USER INTERACTION"]
        AndroidUser["📱 User di Android<br/>(Print/Chat)"]
        PCOperator["🖥️ Operator PC<br/>(Desktop App Qt)"]
    end
    
    subgraph AndroidApp["📱 ANDROID APP<br/>(Kotlin 38.1%)"]
        subgraph PrintModule["PRINT MODULE"]
            MainActivity["MainActivity<br/>Menu Navigation"]
            PrintActivity["PrintActivity<br/>PDF Preview & Control"]
            PrintAdapter["Print Adapter<br/>UI Components"]
        end
        
        subgraph ChatModule["CHAT MODULE"]
            ChatActivity["ChatActivity<br/>Chat Interface"]
            ChatAdapter["ChatAdapter<br/>Message List"]
            ChatSessionStore["ChatSessionStore<br/>Session Memory"]
        end
        
        subgraph DataManagement["DATA MANAGEMENT"]
            ApiService["ApiService<br/>Retrofit HTTP Client"]
            UserProfileManager["UserProfileManager<br/>Local SharedPreferences"]
        end
        
        subgraph FileHandling["FILE HANDLING"]
            FilePicker["File Picker<br/>Uri to File"]
            PdfRenderer["PdfRenderer<br/>PDF Preview"]
        end
    end
    
    subgraph Network["🌐 NETWORK LAYER"]
        HTTPClient["HTTP REST API<br/>BaseURL: 0.0.0.0:5000"]
    end
    
    subgraph PythonBackend["⚙️ PYTHON BACKEND<br/>(Flask 59.5%)"]
        subgraph AppStructure["APP LAYER (app.py)"]
            FlaskApp["Flask Application<br/>@app.route()"]
            FileUpload["/upload<br/>PDF Upload Endpoint"]
            StateManagement["/api/state<br/>State Management"]
            PrinterAPI["/api/printers<br/>Printer Detection"]
        end
        
        subgraph ChatBot["🤖 CHATBOT ENGINE"]
            ChatBot["Chatbot RNN Model<br/>chatbot_rnn_model.h5"]
            Tokenizer["Tokenizer<br/>tokenizer.pickle"]
            Classes["Classes<br/>classes.pickle"]
            ChatEndpoint["/api/chat<br/>Message Processing"]
        end
        
        subgraph DataStorage["💾 DATA STORAGE"]
            DatabaseJson["database.json<br/>Local State Store<br/>- files: []<br/>- print_jobs: []"]
            UploadsDir["uploads/<br/>Received Files"]
            DownloadsDir["downloads/<br/>Generated Files"]
        end
        
        subgraph FileProcessing["📄 FILE PROCESSING"]
            PyPDF2["PyPDF2<br/>PDF Analysis"]
            PythonDocx["python-docx<br/>DOCX Convert"]
            PyMuPDF["PyMuPDF<br/>PDF Metadata"]
        end
        
        subgraph DesktopQT["🖥️ DESKTOP APP<br/>(PyQt5 GUI)"]
            QtWindow["Desktop App Qt<br/>desktop_app_qt.py"]
            Printer["System Printer API<br/>pywin32"]
            PrintExecution["Print Queue<br/>Execution Engine"]
        end
    end
    
    subgraph Training["🎓 MODEL TRAINING"]
        TrainChatbot["train_chatbot.py<br/>RNN Model Training"]
        DatasetChatbot["dataset_chatbot.json<br/>Training Data"]
    end
    
    %% Android User Flow - Print Module
    AndroidUser -->|1. Open App| MainActivity
    MainActivity -->|2. Select Print| PrintActivity
    AndroidUser -->|3. Pick PDF| FilePicker
    FilePicker -->|4. Load PDF| PdfRenderer
    PdfRenderer -->|5. Display Preview| PrintActivity
    AndroidUser -->|6. Configure<br/>Range, Copies, Color| PrintActivity
    PrintActivity -->|7. Upload PDF| ApiService
    
    %% Android to Backend - File Upload
    ApiService -->|8. POST /upload<br/>MultipartBody| HTTPClient
    HTTPClient -->|9. HTTP Request| FileUpload
    FileUpload -->|10. Save File| UploadsDir
    FileUpload -->|11. Process PDF<br/>PyPDF2, PyMuPDF| FileProcessing
    FileProcessing -->|12. Extract Metadata<br/>Pages, Size, Format| DatabaseJson
    FileUpload -->|13. JSON Response| HTTPClient
    HTTPClient -->|14. UploadResponse| ApiService
    PrintActivity -->|15. Display File Info<br/>Name, Size, Pages| PrintActivity
    
    %% State Synchronization - Print Control
    PrintActivity -->|16. Send State<br/>Range, Copies, Color| ApiService
    ApiService -->|17. POST /api/state| HTTPClient
    HTTPClient -->|18. Update State| StateManagement
    StateManagement -->|19. Polling (3s)| DatabaseJson
    StateManagement -->|20. Update Remote State| StateManagement
    
    %% Printer Detection
    PrintActivity -->|21. Load Printers| ApiService
    ApiService -->|22. GET /api/printers| HTTPClient
    HTTPClient -->|23. Query| PrinterAPI
    PrinterAPI -->|24. Detect System Printers<br/>pywin32| Printer
    Printer -->|25. Return Available<br/>Ready Printers| PrinterAPI
    PrinterAPI -->|26. JSON Response| HTTPClient
    HTTPClient -->|27. PrinterResponse| ApiService
    PrintActivity -->|28. Display Printer List| PrintActivity
    
    %% Execute Print
    AndroidUser -->|29. Click Execute Print| PrintActivity
    PrintActivity -->|30. Set execute=true| ApiService
    ApiService -->|31. POST /api/state<br/>execute_print: true| HTTPClient
    HTTPClient -->|32. Trigger Print| PrintExecution
    PrintExecution -->|33. Load File<br/>from uploads/| UploadsDir
    PrintExecution -->|34. Execute Print Job<br/>to Selected Printer| Printer
    PrintExecution -->|35. Mark as Done<br/>in database.json| DatabaseJson
    
    %% Android Polling - Print Status
    PrintActivity -->|36. Poll State (3s)| ApiService
    ApiService -->|37. GET /api/state| HTTPClient
    HTTPClient -->|38. Check Status| DatabaseJson
    DatabaseJson -->|39. Return State| HTTPClient
    HTTPClient -->|40. RemoteStateResponse| ApiService
    ApiService -->|41. Update UI| PrintActivity
    
    %% Android User Flow - Chat Module
    AndroidUser -->|42. Open Chat| ChatActivity
    ChatActivity -->|43. Register User| ApiService
    ApiService -->|44. POST /register| HTTPClient
    HTTPClient -->|45. Store User ID| DatabaseJson
    ChatActivity -->|46. Show Greeting| ChatSessionStore
    AndroidUser -->|47. Send Message| ChatActivity
    ChatActivity -->|48. Add to List| ChatSessionStore
    
    %% Chat with Bot
    ChatActivity -->|49. POST /api/chat<br/>ChatRequest| ApiService
    ApiService -->|50. Send Message| HTTPClient
    HTTPClient -->|51. Process Message| ChatEndpoint
    ChatEndpoint -->|52. Tokenize Input| Tokenizer
    Tokenizer -->|53. Feed to RNN| ChatBot
    ChatBot -->|54. Generate Response<br/>Using Classes| Classes
    ChatEndpoint -->|55. ChatResponse| HTTPClient
    HTTPClient -->|56. Bot Reply| ApiService
    ApiService -->|57. Show Bot Message| ChatActivity
    ChatActivity -->|58. Store Message| ChatSessionStore
    
    %% Chat - File Upload
    AndroidUser -->|59. Attach PDF| ChatActivity
    FilePicker -->|60. Pick PDF| ChatActivity
    ChatActivity -->|61. Upload File| ApiService
    ApiService -->|62. POST /upload| HTTPClient
    HTTPClient -->|63. Save File| UploadsDir
    FileProcessing -->|64. Process| FileProcessing
    FileUpload -->|65. File Metadata| DatabaseJson
    FileUpload -->|66. JSON Response| ApiService
    ChatActivity -->|67. Show File Details<br/>Name, Size, Pages| ChatActivity
    
    %% Chat - Print Instructions
    AndroidUser -->|68. Type Print Instructions<br/>e.g., Cetak warna| ChatActivity
    ChatActivity -->|69. Send Instruction| ChatEndpoint
    ChatEndpoint -->|70. Parse Instruction<br/>RNN Model| ChatBot
    ChatBot -->|71. Update Print State<br/>Color, Pages, Copies| DatabaseJson
    ChatBot -->|72. Trigger Print| PrintExecution
    PrintExecution -->|73. Execute Print| Printer
    PrintExecution -->|74. Mark Status| DatabaseJson
    ChatActivity -->|75. Poll Print Status| ApiService
    ApiService -->|76. GET /api/print_status| HTTPClient
    HTTPClient -->|77. Check Status| DatabaseJson
    DatabaseJson -->|78. Return Status: done| HTTPClient
    ApiService -->|79. Show Success Message| ChatActivity
    
    %% Desktop PC Operator Flow
    PCOperator -->|80. Run desktop_app_qt.py| QtWindow
    QtWindow -->|81. Connect to Server| FlaskApp
    QtWindow -->|82. Load Recent Files<br/>from database.json| DatabaseJson
    QtWindow -->|83. Select File & Options| QtWindow
    QtWindow -->|84. Click Print| PrintExecution
    PrintExecution -->|85. Execute Print| Printer
    
    %% Styling
    style User fill:#FFC107,stroke:#F57F17,stroke-width:2px,color:#000
    style AndroidApp fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style PrintModule fill:#66BB6A,color:#fff
    style ChatModule fill:#66BB6A,color:#fff
    style DataManagement fill:#81C784,color:#fff
    style FileHandling fill:#81C784,color:#fff
    style Network fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style PythonBackend fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style AppStructure fill:#64B5F6,color:#fff
    style ChatBot fill:#42A5F5,color:#fff
    style DataStorage fill:#1E88E5,color:#fff
    style FileProcessing fill:#1565C0,color:#fff
    style DesktopQT fill:#1565C0,color:#fff
    style Training fill:#FFC107,stroke:#F57F17,color:#000
```

---

## 🔄 Proses Lengkap: Print Flow

```mermaid
sequenceDiagram
    participant User as 📱 User Android
    participant App as PrintActivity
    participant Api as ApiService
    participant Network as Flask Server
    participant Desktop as 🖥️ PyQt5 Desktop
    participant Printer as 🖨️ System Printer
    
    User->>App: 1. Pilih PDF dari file
    App->>App: 2. Load PDF & Render Preview
    
    App->>Api: 3. Upload File<br/>POST /upload
    Api->>Network: 4. Multipart Body
    Network->>Network: 5. Save ke uploads/<br/>Process with PyPDF2
    Network->>Network: 6. Extract metadata<br/>pages, size, format
    Network-->>Api: 7. UploadResponse<br/>(nama, ukuran, halaman)
    Api-->>App: 8. Display File Info
    
    User->>App: 9. Set print options<br/>Range, Copies, Color
    App->>Api: 10. Send State<br/>POST /api/state
    Api->>Network: 11. Update database.json
    
    User->>App: 12. Klik Execute Print
    App->>Api: 13. Send execute=true
    Api->>Network: 14. Trigger print
    Network->>Desktop: 15. Signal print job ready
    
    Desktop->>Desktop: 16. Load file from uploads/
    Desktop->>Printer: 17. Execute print dengan options
    Printer->>Printer: 18. Print ke printer fisik
    Desktop->>Network: 19. Mark status: done
    
    App->>Api: 20. Poll State (setiap 3s)
    Api->>Network: 21. GET /api/state
    Network-->>Api: 22. Status: done
    Api-->>App: 23. Show success message
```

---

## 🤖 Chat Bot Flow

```mermaid
sequenceDiagram
    participant User as 📱 User
    participant Chat as ChatActivity
    participant Api as ApiService
    participant Server as Flask Server
    participant Bot as RNN Model
    
    User->>Chat: 1. Send Message<br/>e.g., "Cetak warna"
    Chat->>Api: 2. POST /api/chat<br/>ChatRequest
    Api->>Server: 3. Send message
    
    Server->>Bot: 4. Tokenize text<br/>using tokenizer.pickle
    Bot->>Bot: 5. Feed to RNN model<br/>chatbot_rnn_model.h5
    Bot->>Bot: 6. Generate response<br/>using classes.pickle
    
    alt Bot Detects Print Command
        Bot->>Server: 7a. Parse print instruction<br/>Extract: color, pages, copies
        Server->>Server: 8a. Update database.json<br/>with print settings
    else Bot Sends General Response
        Bot->>Server: 7b. Generate normal response
    end
    
    Server-->>Api: 9. ChatResponse<br/>(response text, action)
    Api-->>Chat: 10. Display bot message
    Chat->>Chat: 11. Store in ChatSessionStore
    
    alt Action == "print_started"
        Chat->>Api: 12. Poll Print Status
        Api->>Server: 13. GET /api/print_status
        Server-->>Api: 14. Return Status
        Api-->>Chat: 15. Show print result
    else Action == "pdf_ready"
        Chat->>Chat: 16. Show download button
    end
```

---

## 📁 Struktur File Sistem

```mermaid
graph TD
    Root["AplikasiSkripsi/"]
    
    subgraph PrintServer["print_server/"]
        AppPy["app.py<br/>Flask Application<br/>- Routes & APIs"]
        DesktopQt["desktop_app_qt.py<br/>PyQt5 GUI"]
        TrainBot["train_chatbot.py<br/>Model Training"]
        RunApp["run_app.py<br/>Multi-threading<br/>Flask + GUI"]
        
        DatabaseJson["database.json<br/>State Storage<br/>files: []<br/>print_jobs: []"]
        DatasetJson["dataset_chatbot.json<br/>Training Data"]
        
        Models["Models"]
        ChatbotH5["chatbot_rnn_model.h5<br/>Trained RNN Model"]
        Tokenizer["tokenizer.pickle<br/>Word Tokenizer"]
        Classes["classes.pickle<br/>Output Classes"]
        
        Uploads["uploads/<br/>User Uploaded PDFs"]
        Downloads["downloads/<br/>Generated Files"]
        
        Requirements["requirements.txt<br/>- flask<br/>- PyPDF2<br/>- python-docx<br/>- pywin32<br/>- PyMuPDF<br/>- PyQt5"]
    end
    
    subgraph AndroidApp["ProjekAndroid/"]
        PrintUploader["PrintUploader/"]
        
        subgraph AndroidSrc["app/src/main/"]
            Manifest["AndroidManifest.xml"]
            Java["java/com/example/printuploader/"]
            Res["res/"]
        end
        
        subgraph KotlinClasses["Kotlin Classes"]
            MainActivity["MainActivity.kt"]
            PrintActivity["PrintActivity.kt<br/>PDF Preview & Control"]
            PrintAdapter["PrintAdapter.kt"]
            
            ChatActivity["ChatActivity.kt<br/>Chat Interface"]
            ChatAdapter["ChatAdapter.kt"]
            ChatSessionStore["ChatSessionStore.kt"]
            
            ApiService["ApiService.kt<br/>Retrofit Interface"]
            UserProfileManager["UserProfileManager.kt"]
            UploadResponse["UploadResponse.kt"]
        end
        
        BuildGradle["build.gradle<br/>Dependencies:<br/>- Retrofit<br/>- OkHttp<br/>- RecyclerView"]
    end
    
    Root --> PrintServer
    Root --> AndroidApp
    
    PrintServer --> AppPy
    PrintServer --> DesktopQt
    PrintServer --> TrainBot
    PrintServer --> RunApp
    PrintServer --> DatabaseJson
    PrintServer --> DatasetJson
    PrintServer --> Models
    PrintServer --> Uploads
    PrintServer --> Downloads
    PrintServer --> Requirements
    
    Models --> ChatbotH5
    Models --> Tokenizer
    Models --> Classes
    
    AndroidApp --> PrintUploader
    PrintUploader --> AndroidSrc
    PrintUploader --> BuildGradle
    AndroidSrc --> Manifest
    AndroidSrc --> Java
    AndroidSrc --> Res
    
    Java --> KotlinClasses
    KotlinClasses --> MainActivity
    KotlinClasses --> PrintActivity
    KotlinClasses --> ChatActivity
    KotlinClasses --> ApiService
    
    style Root fill:#FFC107,stroke:#F57F17,stroke-width:3px,color:#000
    style PrintServer fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    style AndroidApp fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style Models fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style KotlinClasses fill:#66BB6A,color:#fff
```

---

## 🔑 Key API Endpoints (Flask)

| Endpoint | Method | Android | Purpose |
|----------|--------|---------|---------|
| `/upload` | POST | PrintActivity, ChatActivity | Upload PDF file |
| `/api/state` | GET/POST | PrintActivity | Get/Set print state |
| `/api/printers` | GET | PrintActivity | Get list of available printers |
| `/api/chat` | POST | ChatActivity | Send message to RNN bot |
| `/api/print_status` | GET | ChatActivity | Get current print status |
| `/api/check_server` | GET | ChatActivity | Health check |
| `/register` | POST | ChatActivity | Register user |

---

## 💾 Data Flow: database.json

```json
{
  "files": [
    {
      "nama_file": "dokumen.pdf",
      "ukuran_kb": 250,
      "jumlah_halaman": 5,
      "ukuran_kertas": "A4",
      "jenis_file": "pdf",
      "upload_time": "2024-01-01T10:00:00"
    }
  ],
  "print_jobs": [
    {
      "nama_file": "dokumen.pdf",
      "printer_name": "HP Printer",
      "pages": "1-3",
      "copies": 2,
      "color_mode": "Color",
      "status": "done",
      "execution_time": "2024-01-01T10:05:00"
    }
  ]
}
```

---

## 🎯 Fitur Utama Sistem

### **Android Print Module**
- ✅ Pilih & preview PDF dari device
- ✅ Kontrol page range (1-3, 2,4,6, dll)
- ✅ Pengaturan jumlah copy
- ✅ Pilih mode warna (Grayscale/Color)
- ✅ Deteksi printer dari PC
- ✅ Real-time sync state dengan desktop
- ✅ Polling status (setiap 3 detik)

### **Android Chat Module**
- ✅ Chat dengan RNN Chatbot
- ✅ Kirim PDF ke bot untuk analisis
- ✅ Bot memberikan instruksi cetak natural language
- ✅ Bot execute print berdasarkan instruksi
- ✅ Notifikasi masuk chat
- ✅ Download file hasil bot
- ✅ Health check server (setiap 2 detik)

### **Python Backend (Flask)**
- ✅ Multi-threading: Flask + PyQt5 GUI
- ✅ PDF upload & metadata extraction
- ✅ RNN chatbot inference
- ✅ Print queue management
- ✅ JSON-based state storage
- ✅ System printer detection (pywin32)

### **Desktop App (PyQt5)**
- ✅ Real-time file preview
- ✅ Execute print jobs
- ✅ Operator manual control
- ✅ Print queue visualization

---

## ⚡ Teknologi Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Android Frontend | Kotlin, Retrofit, OkHttp | Mobile UI & HTTP requests |
| Desktop Frontend | PyQt5 | GUI for operator |
| Web Server | Flask | REST API & request handling |
| PDF Processing | PyPDF2, PyMuPDF, python-docx | File analysis & conversion |
| AI Model | TensorFlow/Keras RNN | Chatbot inference |
| System Integration | pywin32 | Printer detection & control |
| Database | JSON file | State persistence |
| HTTP Client | Retrofit (Android), Requests (Python) | API communication |

---

## 🔄 Data Synchronization Strategy

1. **Print State Sync**: Android mengirim state setiap kali ada perubahan → Server update database.json
2. **File Metadata**: Saat upload, server parse PDF dan update database.json
3. **Print Status**: Android poll setiap 3 detik untuk mendapat status terbaru
4. **Chat History**: Disimpan di ChatSessionStore (in-memory) di Android
5. **User Profile**: Tersimpan di SharedPreferences Android

---

**Diagram ini mencakup semua aspek dari kedua aplikasi Anda secara detail!** 🎉

Terakhir diperbarui: 2026-06-07
```
