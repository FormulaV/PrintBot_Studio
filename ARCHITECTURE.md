# Arsitektur Aplikasi Android

## Diagram Arsitektur Umum

```mermaid
graph TB
    User["👤 User Interface<br/>Android App<br/>(Kotlin)"]
    
    subgraph Android["📱 Android Layer (Kotlin 38.1%)"]
        UI["UI Components<br/>Activities/Fragments"]
        ViewModel["ViewModel<br/>Data Binding"]
        Repository["Repository Pattern"]
        LocalDB["Local Database<br/>SQLite/Room"]
    end
    
    subgraph Network["🌐 Network Layer"]
        API["REST API<br/>HTTP Client"]
        Socket["WebSocket/<br/>Real-time"]
    end
    
    subgraph Backend["⚙️ Backend (Python 59.5%)"]
        Flask["Flask/FastAPI<br/>API Server"]
        Business["Business Logic<br/>Services"]
        Auth["Authentication<br/>JWT/OAuth"]
        Database["Database<br/>PostgreSQL/MySQL"]
    end
    
    subgraph Native["⚡ Native Layer (C++ 2.4%)"]
        NDK["NDK Module<br/>Performance Critical<br/>Tasks"]
    end
    
    User -->|User Input| UI
    UI -->|State Management| ViewModel
    ViewModel -->|Data Access| Repository
    Repository -->|Local Cache| LocalDB
    Repository -->|Network Request| API
    API -->|HTTP| Backend
    Flask -->|Process| Business
    Business -->|Store/Retrieve| Database
    Business -->|Auth Check| Auth
    Repository -->|Performance<br/>Tasks| NDK
    Backend -.->|Response| API
    API -.->|JSON| Repository
    
    style Android fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Backend fill:#2196F3,stroke:#1565C0,color:#fff
    style Network fill:#FF9800,stroke:#E65100,color:#fff
    style Native fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style User fill:#F44336,stroke:#C62828,color:#fff
```

## Layer Details

### 1. **Presentation Layer (UI - Kotlin)**
- **Activities & Fragments**: Komponen UI utama
- **ViewModel**: Manajemen state dan lifecycle
- **Data Binding**: Binding otomatis antara UI dan data
- **Adapters**: Untuk RecyclerView dan ListView

```mermaid
graph LR
    A["Activity/Fragment"] --> B["ViewModel"]
    B --> C["LiveData/StateFlow"]
    C --> A
    A --> D["UI Components"]
    style A fill:#4CAF50,color:#fff
    style B fill:#81C784,color:#fff
    style C fill:#A5D6A7,color:#fff
    style D fill:#C8E6C9,color:#fff
```

### 2. **Data Layer (Kotlin)**
- **Repository Pattern**: Abstraksi akses data
- **Local Database**: SQLite/Room untuk cache
- **Network Service**: HTTP client (Retrofit/OkHttp)

```mermaid
graph TB
    API["REST API Client<br/>(Retrofit)"]
    LocalDB["Room Database"]
    Repository["Repository"]
    
    Repository -->|Network Call| API
    Repository -->|Local Cache| LocalDB
    
    API --> Backend["Python Backend"]
    
    style Repository fill:#66BB6A,color:#fff
    style API fill:#FF9800,color:#fff
    style LocalDB fill:#2196F3,color:#fff
    style Backend fill:#2196F3,color:#fff
```

### 3. **Backend Layer (Python)**
- **Flask/FastAPI**: Web framework
- **Business Logic**: Service classes
- **Authentication**: JWT/OAuth implementation
- **Database**: Koneksi ke database

```mermaid
graph TB
    Request["HTTP Request<br/>from Android"]
    Router["API Router"]
    Auth["Authentication<br/>Middleware"]
    Controller["Controller/Handler"]
    Service["Business Logic<br/>Service"]
    Database[(("Database<br/>PostgreSQL"))]
    
    Request --> Router
    Router --> Auth
    Auth -->|Valid| Controller
    Controller --> Service
    Service --> Database
    Service -->|Response| Controller
    Controller -->|JSON| Request
    
    style Request fill:#FF9800,color:#fff
    style Auth fill:#F44336,color:#fff
    style Service fill:#2196F3,color:#fff
    style Database fill:#1565C0,color:#fff
```

### 4. **Native Layer (C++)**
- **JNI Binding**: Koneksi Java/Kotlin ke C++
- **Performance Critical**: Operasi berat/komputasi
- **NDK Module**: Optimisasi native

```mermaid
graph LR
    Kotlin["Kotlin<br/>Code"]
    JNI["JNI Bridge"]
    CPP["C++ Code"]
    System["System<br/>Resources"]
    
    Kotlin --> JNI
    JNI --> CPP
    CPP --> System
    
    style Kotlin fill:#4CAF50,color:#fff
    style JNI fill:#9C27B0,color:#fff
    style CPP fill:#9C27B0,color:#fff
    style System fill:#424242,color:#fff
```

## Data Flow

### User Action Flow
```mermaid
sequenceDiagram
    User->>Activity: Input Action
    Activity->>ViewModel: Request Data
    ViewModel->>Repository: Fetch Data
    Repository->>LocalDB: Check Cache
    alt Cache Hit
        LocalDB-->>Repository: Return Data
    else Cache Miss
        Repository->>API: HTTP Request
        API->>Backend: Forward Request
        Backend->>Database: Query
        Database-->>Backend: Return Data
        Backend-->>API: JSON Response
        API-->>Repository: Parse Response
        Repository->>LocalDB: Store Cache
    end
    Repository-->>ViewModel: Return Data
    ViewModel-->>Activity: Update UI
    Activity-->>User: Display Data
```

## Component Details

### Folder Structure
```
AplikasiSkripsi/
├── android/                 # Android Project (Kotlin)
│   ├── app/
│   │   ├── src/
│   │   │   ├── main/
│   │   │   │   ├── java/
│   │   │   │   │   ├── activities/
│   │   │   │   │   ├── fragments/
│   │   │   │   │   ├── viewmodels/
│   │   │   │   │   ├── repositories/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── adapters/
│   │   │   │   │   ├── services/
│   │   │   │   │   └── utils/
│   │   │   │   ├── res/
│   │   │   │   │   ├── layout/
│   │   │   │   │   ├── values/
│   │   │   │   │   ├── drawable/
│   │   │   │   │   └── menu/
│   │   │   │   └── AndroidManifest.xml
│   │   │   └── test/
│   │   └── build.gradle
│   └── settings.gradle
├── python_backend/         # Python Backend (59.5%)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   └── ...
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── api.py
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── user_service.py
│   │   │   ├── product_service.py
│   │   │   └── ...
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   └── ...
│   │   ├── utils/
│   │   │   └── helpers.py
│   │   └── config.py
│   ├── requirements.txt
│   └── .env
├── cpp_native/             # C++ Native Code (2.4%)
│   ├── src/
│   │   ├── jni_bridge.cpp
│   │   ├── algorithms.cpp
│   │   └── ...
│   ├── include/
│   │   └── ...
│   └── CMakeLists.txt
├── docs/
│   └── ARCHITECTURE.md
└── README.md
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Mobile** | Kotlin, Jetpack | Android development |
| **UI** | MaterialDesign, DataBinding | User interface |
| **Database** | Room, SQLite | Local storage |
| **Network** | Retrofit, OkHttp | HTTP communication |
| **Async** | Coroutines, LiveData | Async operations |
| **Backend** | Python, Flask/FastAPI | Server logic |
| **ORM** | SQLAlchemy | Python database ORM |
| **Database** | PostgreSQL/MySQL | Backend database |
| **Auth** | JWT, OAuth2 | Authentication |
| **Native** | C++, JNI, NDK | Performance tasks |

## Design Patterns

- **MVP/MVVM**: Model-View-ViewModel pattern
- **Repository Pattern**: Data access abstraction
- **Singleton**: Database dan API client
- **Observer**: LiveData dan StateFlow
- **Dependency Injection**: Hilt atau Dagger2
- **Factory**: Object creation
- **Builder**: Complex object construction

## Security Considerations

- ✅ JWT token untuk authentication
- ✅ HTTPS untuk semua komunikasi
- ✅ Encryption untuk sensitive data
- ✅ Input validation di frontend dan backend
- ✅ Database encryption (SQLCipher untuk lokal)
- ✅ Secure SharedPreferences untuk tokens
- ✅ ProGuard/R8 untuk obfuscation

## Performance Optimization

- 🚀 Caching strategy (local database)
- 🚀 Lazy loading untuk data besar
- 🚀 Image compression dan caching
- 🚀 Database indexing
- 🚀 C++ untuk operasi compute-intensive
- 🚀 Coroutines untuk non-blocking operations

---

Terakhir diperbarui: 2026-06-07
