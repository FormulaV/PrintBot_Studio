# 🏗️ Arsitektur Sistem: Print Server (Python) + Android App (Kotlin)

## 📊 Diagram 1: Android App Architecture

```mermaid
graph TB
    subgraph AndroidApp["📱 ANDROID APP (Kotlin 38.1%)"]
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
    
    MainActivity -->|Select Print| PrintActivity
    PrintActivity -->|File Operations| FilePicker
    FilePicker -->|Load PDF| PdfRenderer
    PdfRenderer -->|Display Preview| PrintActivity
    PrintActivity -->|Network Request| ApiService
    
    ChatActivity -->|Show Messages| ChatAdapter
    ChatActivity -->|Store Session| ChatSessionStore
    ChatActivity -->|Send to Server| ApiService
    
    ApiService -->|Get User Profile| UserProfileManager
    
    style AndroidApp fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style PrintModule fill:#66BB6A,color:#fff
    style ChatModule fill:#66BB6A,color:#fff
    style DataManagement fill:#81C784,color:#fff
    style FileHandling fill:#81C784,color:#fff
```

---

## 🌐 Diagram 2: Backend Architecture (Python Flask)

```mermaid
graph TB
    subgraph Network["🌐 NETWORK LAYER"]
        HTTPClient["HTTP REST API<br/>BaseURL: 0.0.0.0:5000"]
    end
    
    subgraph PythonBackend["⚙️ PYTHON BACKEND (Flask 59.5%)"]
        subgraph AppStructure["APP LAYER app.py"]
            FlaskApp["Flask Application<br/>at app.route"]
            FileUpload["slash upload<br/>PDF Upload Endpoint"]
            StateManagement["slash api slash state<br/>State Management"]
            PrinterAPI["slash api slash printers<br/>Printer Detection"]
        end
        
        subgraph ChatBot["🤖 CHATBOT ENGINE"]
            ChatBotModel["Chatbot RNN Model<br/>chatbot_rnn_model.h5"]
            Tokenizer["Tokenizer<br/>tokenizer.pickle"]
            Classes["Classes<br/>classes.pickle"]
            ChatEndpoint["slash api slash chat<br/>Message Processing"]
        end
        
        subgraph DataStorage["💾 DATA STORAGE"]
            DatabaseJson["database.json<br/>Local State Store"]
            UploadsDir["uploads folder<br/>Received Files"]
            DownloadsDir["downloads folder<br/>Generated Files"]
        end
        
        subgraph FileProcessing["📄 FILE PROCESSING"]
            PyPDF2["PyPDF2<br/>PDF Analysis"]
            PythonDocx["python-docx<br/>DOCX Convert"]
            PyMuPDF["PyMuPDF<br/>PDF Metadata"]
        end
        
        subgraph DesktopQT["🖥️ DESKTOP APP (PyQt5 GUI)"]
            QtWindow["Desktop App Qt<br/>desktop_app_qt.py"]
            Printer["System Printer API<br/>pywin32"]
            PrintExecution["Print Queue<br/>Execution Engine"]
        end
    end
    
    HTTPClient --> FlaskApp
    HTTPClient --> FileUpload
    HTTPClient --> StateManagement
    HTTPClient --> PrinterAPI
    HTTPClient --> ChatEndpoint
    
    FileUpload --> UploadsDir
    FileUpload --> PyPDF2
    PyPDF2 --> DatabaseJson
    PyMuPDF --> DatabaseJson
    
    ChatEndpoint --> Tokenizer
    Tokenizer --> ChatBotModel
    ChatBotModel --> Classes
    
    StateManagement --> DatabaseJson
    PrinterAPI --> Printer
    PrintExecution --> Printer
    
    style Network fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style PythonBackend fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style AppStructure fill:#64B5F6,color:#fff
    style ChatBot fill:#42A5F5,color:#fff
    style DataStorage fill:#1E88E5,color:#fff
    style FileProcessing fill:#1565C0,color:#fff
    style DesktopQT fill:#1565C0,color:#fff
```

---

## 🔗 Diagram 3: Complete System Integration Flow

```mermaid
graph TB
    subgraph User["👤 USERS"]
        AndroidUser["📱 User Android<br/>(Print & Chat)"]
        PCOperator["🖥️ Operator PC<br/>(Desktop Qt)"]
    end
    
    subgraph Android["📱 Android Layer"]
        PrintFlow["Print Module"]
        ChatFlow["Chat Module"]
        Network["ApiService"]
    end
    
    subgraph Server["⚙️ Server Layer"]
        PrintHandler["Print Handler<br/>slash upload<br/>slash api slash state"]
        ChatHandler["Chat Handler<br/>slash api slash chat<br/>RNN Bot"]
        Execution["Execution<br/>Database<br/>File Processing"]
    end
    
    subgraph Hardware["🖨️ Hardware"]
        SystemPrinter["System Printer<br/>pywin32"]
    end
    
    AndroidUser -->|1. Upload PDF| PrintFlow
    PrintFlow -->|2. HTTP Request| Network
    Network -->|3. POST slash upload| PrintHandler
    PrintHandler -->|4. Process PDF| Execution
    Execution -->|5. Store Metadata| Execution
    PrintFlow -->|6. Polling| Network
    Network -->|7. GET slash api slash state| PrintHandler
    PrintHandler -->|8. Check Status| Execution
    Execution -->|9. Execute Print| SystemPrinter
    SystemPrinter -->|10. Print Done| Execution
    Execution -->|11. Update Status| PrintHandler
    
    AndroidUser -->|12. Send Message| ChatFlow
    ChatFlow -->|13. HTTP Request| Network
    Network -->|14. POST slash api slash chat| ChatHandler
    ChatHandler -->|15. RNN Inference| ChatHandler
    ChatHandler -->|16. Parse Command| Execution
    Execution -->|17. Trigger Print| SystemPrinter
    SystemPrinter -->|18. Print| SystemPrinter
    ChatHandler -->|19. Response| Network
    Network -->|20. Display Result| ChatFlow
    
    PCOperator -->|21. Manual Control| SystemPrinter
    PCOperator -->|22. View Queue| Execution
    
    style User fill:#FFC107,stroke:#F57F17,stroke-width:2px,color:#000
    style Android fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style Server fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    style Hardware fill:#FF5722,stroke:#D84315,stroke-width:2px,color:#fff
```

---

## 🔄 Print Flow: Sequence Diagram

```mermaid
sequenceDiagram
    participant User as 📱 User
    participant App as PrintActivity
    participant Api as ApiService
    participant Server as Flask
    participant Exec as Print Executor
    participant Printer as System Printer
    
    User->>App: 1. Select PDF
    App->>App: 2. Preview PDF
    User->>App: 3. Configure Print
    App->>Api: 4. Upload PDF
    Api->>Server: 5. POST slash upload
    Server->>Server: 6. Extract Metadata
    Server-->>Api: 7. File Info
    Api-->>App: 8. Display Info
    
    User->>App: 9. Click Print
    App->>Api: 10. Send State
    Api->>Server: 11. Update Settings
    App->>Api: 12. Poll Status
    Api->>Server: 13. GET State
    Server->>Exec: 14. Load File
    Exec->>Printer: 15. Print
    Printer-->>Exec: 16. Done
    Exec->>Server: 17. Update Status
    Server-->>Api: 18. Status OK
    Api-->>App: 19. Show Success
```

---

## 🤖 Chat Bot Flow: Sequence Diagram

```mermaid
sequenceDiagram
    participant User as 📱 User
    participant Chat as ChatActivity
    participant Api as ApiService
    participant Server as Flask
    participant Bot as RNN Model
    participant Executor as Executor
    
    User->>Chat: 1. Send Message
    Chat->>Api: 2. POST slash api slash chat
    Api->>Server: 3. Message
    Server->>Bot: 4. Tokenize
    Bot->>Bot: 5. RNN Inference
    Bot->>Server: 6. Response
    
    alt Bot Detects Print Command
        Server->>Executor: 7a. Parse Instruction
        Executor->>Server: 8a. Execute Print
    else Bot Sends Normal Response
        Server->>Server: 7b. Just Respond
    end
    
    Server-->>Api: 9. ChatResponse
    Api-->>Chat: 10. Display Message
    Chat->>Chat: 11. Store in Session
```

---

## 📁 Struktur File Sistem

```mermaid
graph TD
    Root["AplikasiSkripsi slash"]
    
    subgraph PrintServer["print_server slash"]
        AppPy["app.py<br/>Flask Server"]
        DesktopQt["desktop_app_qt.py<br/>PyQt5 GUI"]
        RunApp["run_app.py<br/>Multi-threading"]
        TrainBot["train_chatbot.py<br/>Model Training"]
        
        DatabaseJson["database.json"]
        DatasetJson["dataset_chatbot.json"]
        
        Models["Models"]
        ChatbotH5["chatbot_rnn_model.h5"]
        Tokenizer["tokenizer.pickle"]
        Classes["classes.pickle"]
        
        Uploads["uploads slash"]
        Downloads["downloads slash"]
    end
    
    subgraph AndroidApp["ProjekAndroid slash"]
        PrintUploader["PrintUploader slash"]
        
        subgraph KotlinClasses["Kotlin Classes"]
            MainActivity["MainActivity.kt"]
            PrintActivity["PrintActivity.kt"]
            ChatActivity["ChatActivity.kt"]
            ApiService["ApiService.kt"]
            Other["UserProfileManager.kt<br/>ChatAdapter.kt<br/>etc"]
        end
    end
    
    Root --> PrintServer
    Root --> AndroidApp
    PrintServer --> AppPy
    PrintServer --> DesktopQt
    PrintServer --> RunApp
    PrintServer --> TrainBot
    PrintServer --> DatabaseJson
    PrintServer --> DatasetJson
    PrintServer --> Models
    PrintServer --> Uploads
    PrintServer --> Downloads
    Models --> ChatbotH5
    Models --> Tokenizer
    Models --> Classes
    
    AndroidApp --> PrintUploader
    PrintUploader --> KotlinClasses
    
    style Root fill:#FFC107,stroke:#F57F17,stroke-width:3px,color:#000
    style PrintServer fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    style AndroidApp fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    style Models fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## 🔑 API Endpoints Reference

| Endpoint | Method | Purpose | From |
|----------|--------|---------|------|
| `/upload` | POST | Upload PDF file | PrintActivity, ChatActivity |
| `/api/state` | GET/POST | Get/Set print state | PrintActivity |
| `/api/printers` | GET | Get available printers | PrintActivity |
| `/api/chat` | POST | Send message to bot | ChatActivity |
| `/api/print_status` | GET | Get print status | ChatActivity |
| `/api/check_server` | GET | Health check | ChatActivity |
| `/register` | POST | Register user | ChatActivity |

---

## 💾 database.json Structure

```json
{
  "files": [
    {
      "nama_file": "dokumen.pdf",
      "ukuran_kb": 250,
      "jumlah_halaman": 5,
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

## ⚡ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Android Frontend | Kotlin, Retrofit, OkHttp | Mobile UI and HTTP |
| Desktop Frontend | PyQt5 | GUI for operator |
| Web Server | Flask | REST API |
| PDF Processing | PyPDF2, PyMuPDF, python-docx | File analysis |
| AI Model | TensorFlow Keras RNN | Chatbot |
| System Integration | pywin32 | Printer control |
| Database | JSON file | State persistence |

---

## 🎯 Main Features

### Android Print Module
- Select and preview PDF
- Control page range
- Set number of copies
- Choose color mode (Grayscale/Color)
- Detect printer from PC
- Real-time state sync
- Status polling every 3 seconds

### Android Chat Module
- Chat with RNN Chatbot
- Send PDF for analysis
- Bot gives natural language print instructions
- Bot executes print based on instructions
- Chat notifications
- Download bot results
- Server health check every 2 seconds

### Python Backend (Flask)
- Multi-threading Flask and PyQt5
- PDF upload and metadata extraction
- RNN chatbot inference
- Print queue management
- JSON state storage
- System printer detection

### Desktop App (PyQt5)
- Real-time file preview
- Execute print jobs
- Operator manual control
- Print queue visualization

---

**Updated: 2026-06-07** ✨
