# Sistem Arsitektur: Android (Kotlin) + Python Backend

## 📊 Complete End-to-End System Architecture

```mermaid
graph TB
    subgraph User["👤 USER LAYER"]
        EndUser["End User<br/>Using Mobile App"]
    end
    
    subgraph Android["📱 ANDROID APPLICATION<br/>(Kotlin 38.1%)"]
        subgraph UI["UI Layer"]
            LoginScreen["Login Screen"]
            HomeScreen["Home Screen"]
            DetailScreen["Detail Screen"]
        end
        
        subgraph VM["State Management Layer"]
            AuthVM["AuthViewModel"]
            HomeVM["HomeViewModel"]
            DetailVM["DetailViewModel"]
        end
        
        subgraph Data["Data Layer"]
            Repository["Repository<br/>Data Abstraction"]
            LocalCache["Local Database<br/>Room SQLite"]
        end
        
        subgraph Network["Network Layer"]
            RetrofitClient["Retrofit<br/>HTTP Client"]
            Interceptor["Interceptor<br/>Token Injection"]
        end
    end
    
    subgraph Internet["🌐 INTERNET"]
        HTTPS["HTTPS/TLS<br/>Encrypted Channel"]
    end
    
    subgraph Backend["⚙️ PYTHON BACKEND<br/>(Flask/FastAPI 59.5%)"]
        subgraph API["API Layer"]
            AuthEndpoint["/auth/login<br/>POST /api/data<br/>GET /api/detail"]
            RouteHandler["Route Handler<br/>@app.route()"]
        end
        
        subgraph Security["Security Layer"]
            CORSHandler["CORS Handler"]
            JWTValidator["JWT Token<br/>Validator"]
            InputValidator["Input Validator<br/>Sanitization"]
        end
        
        subgraph Business["Business Logic Layer"]
            AuthService["Auth Service<br/>Login, Register"]
            DataService["Data Service<br/>CRUD Operations"]
            DetailService["Detail Service<br/>Data Processing"]
        end
        
        subgraph DatabaseLayer["Database Layer"]
            PostgreSQL[("PostgreSQL<br/>Primary Database")]
            RedisCache[("Redis<br/>Cache")]
        end
    end
    
    subgraph Native["⚡ NATIVE CODE<br/>(C++ 2.4%)"]
        CPPModule["C++ Algorithm<br/>for Performance<br/>Tasks"]
    end
    
    %% User Interaction Flow
    EndUser -->|Opens App| LoginScreen
    LoginScreen -->|Input Email/Password| AuthVM
    
    %% Authentication Flow
    AuthVM -->|Validate Input| Repository
    Repository -->|Check Local Cache| LocalCache
    LocalCache -->|No Token Found| RetrofitClient
    RetrofitClient -->|Add Auth Header| Interceptor
    Interceptor -->|POST /auth/login| HTTPS
    HTTPS -->|Forward Request| AuthEndpoint
    AuthEndpoint -->|Route to Handler| RouteHandler
    RouteHandler -->|Check CORS| CORSHandler
    CORSHandler -->|Forward Request| InputValidator
    InputValidator -->|Sanitize Input| AuthService
    AuthService -->|Query User| PostgreSQL
    PostgreSQL -->|Return User Data| AuthService
    AuthService -->|Generate JWT Token| JWTValidator
    JWTValidator -->|Return Token| RouteHandler
    RouteHandler -->|JSON Response| HTTPS
    HTTPS -->|Return to Client| RetrofitClient
    RetrofitClient -->|Parse JWT| Interceptor
    Interceptor -->|Save Token| LocalCache
    Repository -->|Update UI State| AuthVM
    AuthVM -->|Navigate to Home| HomeScreen
    
    %% Data Fetching Flow
    HomeScreen -->|User Views List| HomeVM
    HomeVM -->|Request Data| Repository
    Repository -->|Check Cache First| LocalCache
    LocalCache -->|Cache Expired| RetrofitClient
    RetrofitClient -->|Add JWT Token| Interceptor
    Interceptor -->|GET /api/data| HTTPS
    HTTPS -->|Receive Request| AuthEndpoint
    AuthEndpoint -->|Route| RouteHandler
    RouteHandler -->|Validate Token| JWTValidator
    JWTValidator -->|Token Valid| DataService
    DataService -->|Complex Logic| CPPModule
    CPPModule -->|Process Data| DataService
    DataService -->|Query Data| PostgreSQL
    PostgreSQL -->|Fetch from Cache| RedisCache
    RedisCache -->|Return| PostgreSQL
    PostgreSQL -->|Return Data| DataService
    DataService -->|Format Response| RouteHandler
    RouteHandler -->|JSON Response| HTTPS
    HTTPS -->|Return to Client| RetrofitClient
    RetrofitClient -->|Parse Data| Repository
    Repository -->|Store in Cache| LocalCache
    Repository -->|Update State| HomeVM
    HomeVM -->|Render List| HomeScreen
    
    %% Detail View Flow
    HomeScreen -->|User Clicks Item| DetailScreen
    DetailScreen -->|Load Detail| DetailVM
    DetailVM -->|Request Specific Data| Repository
    Repository -->|Check Local Cache| LocalCache
    LocalCache -->|Cache Hit| Repository
    Repository -->|Return Cached Data| DetailVM
    DetailVM -->|Display Detail| DetailScreen
    
    %% Styling
    style User fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style Android fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff
    style UI fill:#81C784,color:#fff
    style VM fill:#66BB6A,color:#fff
    style Data fill:#4CAF50,color:#fff
    style Network fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    style Internet fill:#FFB74D,stroke:#E65100,stroke-width:2px,color:#000
    style Backend fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff
    style API fill:#64B5F6,color:#fff
    style Security fill:#F44336,stroke:#C62828,color:#fff
    style Business fill:#42A5F5,color:#fff
    style DatabaseLayer fill:#1565C0,color:#fff
    style Native fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff
    style HTTPS fill:#FFC107,stroke:#F57F17,stroke-width:2px,color:#000
```

---

## 🔄 Alur Proses Lengkap: Login → Home → Detail

### **FASE 1: INITIALIZATION**
```
User Opens App
    ↓
Check Local Token
    ├─ Token Valid → Go to Home Screen
    └─ Token Expired/None → Go to Login Screen
```

### **FASE 2: AUTHENTICATION (Login)**
```
1. User Input Email & Password
   ↓
2. AuthViewModel Validate Input
   ↓
3. Repository Check Local Cache (Token)
   ↓
4. Retrofit POST /auth/login dengan credentials
   ↓
5. Interceptor Tambah Headers (HTTPS)
   ↓
6. Backend Auth Service:
   - Validate Email/Password
   - Query Database User
   - Check Password Hash
   ↓
7. Generate JWT Token
   ↓
8. Return Token ke Android
   ↓
9. Save Token di SharedPreferences
   ↓
10. Navigate to Home Screen
```

### **FASE 3: DATA FETCHING (Home Screen)**
```
1. User Navigate ke Home
   ↓
2. HomeViewModel Request Data
   ↓
3. Repository Check Local Cache
   ├─ Hit → Return Cached Data (Fast) → Display
   └─ Miss → Continue to Network Request
   ↓
4. Retrofit GET /api/data dengan JWT Token
   ↓
5. Backend Service:
   - JWT Token Validation ✓
   - Input Sanitization ✓
   - Business Logic Processing
   - Call C++ Module for Heavy Computation
   - Query PostgreSQL Database
   - Check Redis Cache Layer
   ↓
6. Format Response (JSON)
   ↓
7. Return ke Android
   ↓
8. Repository Store di Local Database
   ↓
9. ViewModel Update State (LiveData)
   ↓
10. RecyclerView Render List UI
```

### **FASE 4: DETAIL VIEW (Detail Screen)**
```
1. User Click Item di List
   ↓
2. DetailViewModel Request Data
   ↓
3. Repository Check Local Cache
   ├─ Available → Return Immediately
   └─ Not Available → Network Request
   ↓
4. Display Detail Information
   ↓
5. Optional: Real-time Updates via WebSocket
```

---

## 📈 Request Flow Diagram

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant Android as 📱 Android App
    participant Cache as 💾 Local Cache
    participant Network as 🌐 Network
    participant Backend as ⚙️ Backend
    participant DB as 🗄️ Database
    
    User->>Android: 1. Click Login Button
    activate Android
    Android->>Cache: 2. Check Token
    deactivate Android
    
    alt Token Exists
        Cache-->>Android: Return Token
        Android->>User: ✓ Go to Home
    else Token Not Found
        activate Android
        Android->>Network: 3. POST /auth/login
        activate Network
        Network->>Backend: 4. Forward Request
        activate Backend
        Backend->>DB: 5. Query User
        DB-->>Backend: Return User Data
        Backend->>Backend: 6. Generate JWT
        Backend-->>Network: 7. JWT Token
        deactivate Backend
        Network-->>Android: 8. Token Response
        deactivate Network
        Android->>Cache: 9. Save Token
        Android->>User: ✓ Go to Home
        deactivate Android
    end
    
    Note over User,DB: FASE 2: HOME SCREEN LOAD
    
    User->>Android: 10. View Home Screen
    activate Android
    Android->>Cache: 11. Check Cache
    
    alt Cache Hit
        Cache-->>Android: Return Data
        Android->>User: ✓ Display Immediately
    else Cache Miss
        Android->>Network: 12. GET /api/data
        activate Network
        Network->>Backend: 13. Forward + JWT
        activate Backend
        Backend->>Backend: 14. Validate Token ✓
        Backend->>Backend: 15. Business Logic
        Backend->>DB: 16. Query Data
        DB-->>Backend: Return Data
        Backend-->>Network: 17. JSON Response
        deactivate Backend
        Network-->>Android: 18. Data
        deactivate Network
        Android->>Cache: 19. Store Cache
        Android->>User: ✓ Display
    end
    deactivate Android
```

---

## 🔐 Security Implementation

```
User Input (Android)
    ↓
Frontend Validation
    ↓
Encrypt with HTTPS/TLS
    ↓
Backend Receives
    ↓
CORS Validation ✓
    ↓
Input Sanitization & Validation ✓
    ↓
JWT Token Verification ✓
    ↓
Rate Limiting ✓
    ↓
SQL Injection Prevention (ORM) ✓
    ↓
Database Operation
    ↓
Encrypt Response
    ↓
Send to Android
    ↓
Decrypt & Store Securely
```

---

## 📊 Key Components Communication

| Android Component | ↔️ | Backend Component | Purpose |
|------------------|-----|------------------|---------|
| LoginScreen | POST | /auth/login | Authentication |
| HomeScreen | GET | /api/data | Fetch List Data |
| DetailScreen | GET | /api/detail/{id} | Fetch Detail Data |
| Repository | - | Services | Business Logic |
| LocalDatabase | - | PostgreSQL | Data Persistence |
| ViewModel | - | - | State Management |
| - | - | JWTValidator | Security Check |
| - | - | CPPModule | Performance Tasks |

---

## 🎯 Performance Optimizations

1. **Caching Strategy**
   - Local Cache untuk data yang jarang berubah
   - Redis Cache di backend untuk query intensive
   - LRU Cache untuk memory optimization

2. **Network Optimization**
   - HTTP/2 Multiplexing
   - GZIP Compression
   - Request Batching

3. **Database Optimization**
   - Indexed Queries
   - Connection Pooling
   - Lazy Loading

4. **Native Code**
   - C++ untuk komputasi heavy
   - JNI Bridge untuk integrasi

---

## ✅ Error Handling & Retry Strategy

```
Request Sent
    ↓
Check Response Status
    ├─ 200 OK → Success ✓
    ├─ 401 Unauthorized → Refresh Token → Retry
    ├─ 5xx Server Error → Retry (Exponential Backoff)
    ├─ Network Error → Store Queue → Retry Later
    └─ Invalid Input → Show Error to User
```

---

Terakhir diperbarui: 2026-06-07
Diagram format: Mermaid (Compatible dengan draw.io)
```
