# Architecture Diagrams - Mermaid Code

Berikut adalah kumpulan diagram arsitektur dalam format Mermaid yang dapat diimpor langsung ke draw.io atau tools Mermaid lainnya.

---

## 1. Diagram Arsitektur Lengkap (Main Architecture)

```mermaid
graph TB
    User["👤 User"]
    
    subgraph Android["📱 ANDROID LAYER<br/>(Kotlin 38.1%)"]
        Activity["Activity/Fragment"]
        ViewModel["ViewModel<br/>State Management"]
        Repository["Repository Pattern"]
        LocalDB["Room Database<br/>Local Storage"]
        Adapter["Adapter<br/>UI Controller"]
    end
    
    subgraph NetworkLayer["🌐 NETWORK LAYER"]
        Retrofit["Retrofit<br/>HTTP Client"]
        OkHttp["OkHttp<br/>Interceptor"]
    end
    
    subgraph Backend["⚙️ BACKEND<br/>(Python 59.5%)"]
        Router["Flask Router<br/>API Endpoints"]
        AuthMiddleware["Auth Middleware<br/>JWT Validation"]
        Controller["Controller<br/>Request Handler"]
        Service["Business Logic<br/>Service Layer"]
        BackendDB[(Database<br/>PostgreSQL)]
    end
    
    subgraph Native["⚡ NATIVE LAYER<br/>(C++ 2.4%)"]
        JNI["JNI Bridge"]
        CPPCode["C++ Algorithm<br/>Performance Tasks"]
    end
    
    User -->|Input Action| Activity
    Activity --> Adapter
    Adapter --> ViewModel
    ViewModel -->|Update State| Activity
    ViewModel -->|Data Request| Repository
    Repository -->|Cache Check| LocalDB
    Repository -->|HTTP Request| Retrofit
    Retrofit --> OkHttp
    OkHttp -->|POST/GET| Router
    
    Router --> AuthMiddleware
    AuthMiddleware -->|Valid Token| Controller
    Controller --> Service
    Service -->|Query/Store| BackendDB
    Service -.->|Response| Controller
    Controller -.->|JSON Response| OkHttp
    OkHttp -.->|Response| Retrofit
    Retrofit -->|Parse JSON| Repository
    Repository -->|Cache Store| LocalDB
    Repository -.->|Data| ViewModel
    
    ViewModel -->|Performance Task| JNI
    JNI --> CPPCode
    CPPCode -.->|Result| JNI
    JNI -.->|Result| ViewModel
    
    style Android fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style NetworkLayer fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style Backend fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style Native fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff
    style User fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style Repository fill:#66BB6A,stroke:#2E7D32,color:#fff
    style Service fill:#64B5F6,stroke:#1565C0,color:#fff
```

---

## 2. Detailed Component Architecture

```mermaid
graph TB
    subgraph Presentation["📱 PRESENTATION LAYER"]
        Activity["Activity<br/>Screen Controller"]
        Fragment["Fragment<br/>Reusable UI"]
        Dialog["Dialog<br/>Popups"]
    end
    
    subgraph StateManagement["🔄 STATE MANAGEMENT"]
        ViewModel["ViewModel<br/>Lifecycle Aware"]
        LiveData["LiveData/StateFlow<br/>Observable Data"]
        Binding["Data Binding<br/>Auto UI Update"]
    end
    
    subgraph DataLayer["💾 DATA LAYER"]
        Repository["Repository<br/>Data Abstraction"]
        LocalData["Local Database<br/>Room/SQLite"]
        Cache["Cache Manager<br/>Preference"]
    end
    
    subgraph Network["🌐 NETWORK"]
        Retrofit["Retrofit<br/>REST Client"]
        Interceptor["Interceptor<br/>Request/Response"]
    end
    
    subgraph Models["📦 DATA MODELS"]
        Entity["Entity<br/>DB Model"]
        DTO["DTO<br/>API Model"]
        Domain["Domain Model<br/>Business Logic"]
    end
    
    Presentation --> StateManagement
    StateManagement --> DataLayer
    DataLayer --> LocalData
    DataLayer --> Network
    Network --> Interceptor
    Interceptor --> Retrofit
    
    Presentation --> Models
    DataLayer --> Models
    
    style Presentation fill:#4CAF50,stroke:#2E7D32,color:#fff
    style StateManagement fill:#81C784,stroke:#2E7D32,color:#fff
    style DataLayer fill:#66BB6A,stroke:#2E7D32,color:#fff
    style Network fill:#FF9800,stroke:#E65100,color:#fff
    style Models fill:#FFC107,stroke:#F57F17,color:#000
```

---

## 3. Backend Architecture (Python)

```mermaid
graph TB
    Client["🔹 Client Request<br/>from Android"]
    
    subgraph Server["⚙️ SERVER LAYER"]
        Endpoint["Flask Routes<br/>@app.route()"]
        Blueprint["Blueprint<br/>Modular Routes"]
    end
    
    subgraph Middleware["🔐 MIDDLEWARE"]
        CORS["CORS Handler"]
        Auth["Authentication<br/>JWT Token Check"]
        Validation["Request Validation"]
    end
    
    subgraph BusinessLogic["💼 BUSINESS LOGIC"]
        UserService["User Service<br/>User Management"]
        ProductService["Product Service<br/>Product Management"]
        OrderService["Order Service<br/>Order Processing"]
        PaymentService["Payment Service<br/>Payment Processing"]
    end
    
    subgraph Repository["📊 DATA ACCESS"]
        UserRepo["User Repository"]
        ProductRepo["Product Repository"]
        OrderRepo["Order Repository"]
    end
    
    subgraph Database["🗄️ DATABASE"]
        PostgreSQL[("PostgreSQL<br/>Primary DB")]
        Cache[("Redis<br/>Cache Layer")]
    end
    
    Client --> Endpoint
    Endpoint --> Blueprint
    Blueprint --> CORS
    CORS --> Auth
    Auth --> Validation
    
    Validation --> UserService
    Validation --> ProductService
    Validation --> OrderService
    Validation --> PaymentService
    
    UserService --> UserRepo
    ProductService --> ProductRepo
    OrderService --> OrderRepo
    
    UserRepo --> PostgreSQL
    ProductRepo --> PostgreSQL
    OrderRepo --> PostgreSQL
    
    UserService -.->|Cache| Cache
    ProductService -.->|Cache| Cache
    OrderService -.->|Cache| Cache
    
    style Server fill:#2196F3,stroke:#1565C0,color:#fff
    style Middleware fill:#F44336,stroke:#C62828,color:#fff
    style BusinessLogic fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Repository fill:#FF9800,stroke:#E65100,color:#fff
    style Database fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Client fill:#FFC107,stroke:#F57F17,color:#000
```

---

## 4. Data Flow - Complete Request Cycle

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant App as 📱 Android<br/>App
    participant Repository as 📊 Repository
    participant LocalDB as 💾 Local DB
    participant Retrofit as 🌐 Retrofit
    participant Backend as ⚙️ Backend
    participant MainDB as 🗄️ Database
    
    User->>App: Click Button
    App->>Repository: requestData()
    Repository->>LocalDB: checkCache()
    
    alt Cache Available
        LocalDB-->>Repository: Return Cached Data
        Repository-->>App: Data from Cache
        App-->>User: Display Data ✓
    else Cache Expired/Empty
        Repository->>Retrofit: HTTP GET /api/data
        Retrofit->>Backend: Forward Request
        Backend->>MainDB: Query Data
        MainDB-->>Backend: Return Result
        Backend-->>Retrofit: JSON Response
        Retrofit-->>Repository: Parse Response
        Repository->>LocalDB: Store in Cache
        Repository-->>App: Return Data
        App-->>User: Display Data ✓
    end
```

---

## 5. MVC/MVVM Pattern Flow

```mermaid
graph LR
    subgraph MVVM["MVVM PATTERN"]
        View["View<br/>Activity/Fragment"]
        ViewModel["ViewModel<br/>UI Logic"]
        Model["Model<br/>Data & Logic"]
    end
    
    subgraph Binding["Data Binding"]
        LiveData["LiveData<br/>Observable"]
        StateFlow["StateFlow<br/>Coroutine"]
    end
    
    User["👤 User Input"]
    UI["📱 UI Update"]
    
    User -->|User Action| View
    View -->|Observe State| Binding
    Binding -->|Update| View
    View -->|Request| ViewModel
    ViewModel -->|Process| Model
    Model -->|State Change| ViewModel
    ViewModel -->|Update| LiveData
    LiveData -->|Emit| View
    View -->|Render| UI
    
    style View fill:#4CAF50,stroke:#2E7D32,color:#fff
    style ViewModel fill:#81C784,stroke:#2E7D32,color:#fff
    style Model fill:#66BB6A,stroke:#2E7D32,color:#fff
    style Binding fill:#FFC107,stroke:#F57F17,color:#000
```

---

## 6. Native Code Integration (C++ with JNI)

```mermaid
graph TB
    subgraph Kotlin["Kotlin Code"]
        KotlinClass["Kotlin Class<br/>loadLibrary()"]
        NativeMethod["Native Method<br/>@ExperimentalForeignApi"]
    end
    
    subgraph JNI["JNI BRIDGE"]
        JNILoader["JNI Loader<br/>System.loadLibrary"]
        JNIBinding["JNI Binding<br/>native interface"]
    end
    
    subgraph Native["C++ Code"]
        CPPHeader["Header File<br/>jni.h"]
        CPPImpl["Implementation<br/>Algorithm"]
        CPPNative["Native Function<br/>JNIEXPORT"]
    end
    
    subgraph HardwareAccess["Hardware & Resources"]
        CPU["CPU"]
        Memory["Memory"]
        Storage["Storage"]
    end
    
    KotlinClass -->|load| JNILoader
    KotlinClass -->|call| NativeMethod
    NativeMethod --> JNIBinding
    JNIBinding -->|invoke| CPPNative
    CPPNative -->|access| CPPImpl
    CPPImpl -->|include| CPPHeader
    CPPImpl -->|optimize| HardwareAccess
    
    style Kotlin fill:#4CAF50,stroke:#2E7D32,color:#fff
    style JNI fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Native fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style HardwareAccess fill:#424242,stroke:#000,color:#fff
```

---

## 7. Authentication & Security Flow

```mermaid
graph TB
    subgraph Client["📱 Client"]
        Login["Login Screen"]
        SharedPref["SharedPreferences<br/>Token Storage"]
    end
    
    subgraph Network["🌐 Network"]
        HTTPClient["HTTP Client<br/>Encrypted"]
        Certificate["SSL/TLS<br/>Certificate"]
    end
    
    subgraph Backend["⚙️ Backend"]
        AuthService["Auth Service"]
        JWTHandler["JWT Handler<br/>Token Generation"]
    end
    
    subgraph Database["🗄️ Database"]
        UserTable["User Table"]
    end
    
    Login -->|username/password| HTTPClient
    HTTPClient -->|HTTPS| Certificate
    Certificate -->|Secure| AuthService
    AuthService -->|Validate| UserTable
    UserTable -->|Found| JWTHandler
    JWTHandler -->|Generate Token| AuthService
    AuthService -->|Return Token| HTTPClient
    HTTPClient -->|Encrypted| SharedPref
    SharedPref -->|Store| Login
    
    style Client fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Network fill:#FF9800,stroke:#E65100,color:#fff
    style Backend fill:#2196F3,stroke:#1565C0,color:#fff
    style Database fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## 8. Database Schema Relationship

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER ||--o{ PROFILE : has
    PRODUCT ||--o{ ORDER_ITEM : "is in"
    ORDER ||--o{ ORDER_ITEM : contains
    PRODUCT ||--o{ CATEGORY : "belongs to"
    
    USER {
        int id PK
        string email UK
        string password
        string phone
        datetime created_at
        datetime updated_at
    }
    
    PROFILE {
        int id PK
        int user_id FK
        string full_name
        string avatar_url
        string address
    }
    
    PRODUCT {
        int id PK
        string name
        string description
        decimal price
        int stock
        int category_id FK
    }
    
    CATEGORY {
        int id PK
        string name
        string slug
    }
    
    ORDER {
        int id PK
        int user_id FK
        decimal total_price
        string status
        datetime order_date
    }
    
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal price
    }
```

---

## 9. Deployment Architecture

```mermaid
graph TB
    subgraph Development["🔧 DEVELOPMENT"]
        IDE["IDE<br/>Android Studio"]
        Emulator["Emulator<br/>Test Device"]
    end
    
    subgraph Testing["✅ TESTING"]
        UnitTest["Unit Tests<br/>JUnit"]
        UITest["UI Tests<br/>Espresso"]
        IntegrationTest["Integration Tests"]
    end
    
    subgraph CI_CD["🚀 CI/CD PIPELINE"]
        GitHub["GitHub Actions<br/>Auto Build"]
        Build["Build APK/AAB"]
    end
    
    subgraph Distribution["📦 DISTRIBUTION"]
        PlayStore["Google Play Store"]
        InternalTesting["Internal Testing"]
    end
    
    subgraph Production["🌍 PRODUCTION"]
        Server["Backend Server<br/>AWS/Heroku"]
        Database["Database<br/>PostgreSQL"]
        CDN["CDN<br/>Static Files"]
    end
    
    IDE --> Emulator
    Emulator --> Testing
    Testing --> CI_CD
    CI_CD --> Build
    Build --> Distribution
    Distribution -->|Production Build| PlayStore
    Distribution -->|Beta Build| InternalTesting
    PlayStore -->|Install| Production
    InternalTesting -.->|Feedback| Development
    
    style Development fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Testing fill:#2196F3,stroke:#1565C0,color:#fff
    style CI_CD fill:#FF9800,stroke:#E65100,color:#fff
    style Distribution fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Production fill:#F44336,stroke:#C62828,color:#fff
```

---

## 10. Folder Structure as Architecture

```mermaid
graph TB
    Root["AplikasiSkripsi/"]
    
    subgraph AndroidProject["📱 android/"]
        App["app/"]
        Build["build.gradle<br/>Dependencies"]
    end
    
    subgraph AndroidSrc["app/src/main/"]
        Java["java/"]
        Res["res/"]
        Manifest["AndroidManifest.xml"]
    end
    
    subgraph JavaStructure["java/com/app/"]
        Activities["activities/"]
        Fragments["fragments/"]
        ViewModels["viewmodels/"]
        Repositories["repositories/"]
        Models["models/"]
        Services["services/"]
        Utils["utils/"]
        DB["database/"]
        API["api/"]
    end
    
    subgraph Backend["⚙️ python_backend/"]
        AppFolder["app/"]
        Venv["venv/"]
        Requirements["requirements.txt"]
    end
    
    subgraph BackendStructure["app/"]
        Models["models/"]
        Routes["routes/"]
        Services["services/"]
        Config["config.py"]
    end
    
    subgraph CPP["🔧 cpp_native/"]
        Src["src/"]
        Include["include/"]
        CMake["CMakeLists.txt"]
    end
    
    subgraph Docs["📚 docs/"]
        Architecture["ARCHITECTURE.md"]
        API["API.md"]
        Setup["SETUP.md"]
    end
    
    Root --> AndroidProject
    Root --> Backend
    Root --> CPP
    Root --> Docs
    
    AndroidProject --> App
    AndroidProject --> Build
    App --> AndroidSrc
    AndroidSrc --> Java
    AndroidSrc --> Res
    Java --> JavaStructure
    
    Backend --> AppFolder
    Backend --> Requirements
    AppFolder --> BackendStructure
    
    CPP --> Src
    CPP --> Include
    
    style Root fill:#FFC107,stroke:#F57F17,color:#000,stroke-width:3px
    style AndroidProject fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Backend fill:#2196F3,stroke:#1565C0,color:#fff
    style CPP fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Docs fill:#424242,stroke:#000,color:#fff
```

---

## Cara Menggunakan Diagram di draw.io:

1. **Buka draw.io** → https://draw.io
2. **Klik File** → **New** → **Blank Diagram**
3. **Klik File** → **Import from** → **Paste URL or Code**
4. **Copy-paste salah satu kode Mermaid di atas**
5. **Klik Import** - Diagram akan otomatis terbentuk
6. **Edit dan customize** sesuai kebutuhan

---

**Tips:**
- ✅ Setiap diagram dapat di-zoom dan diedit
- ✅ Bisa diexport sebagai PNG, SVG, PDF
- ✅ Gunakan untuk dokumentasi atau presentasi
- ✅ Share dengan team untuk review

