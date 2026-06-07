#include <windows.h>
#include <string>
#include <vector>
#include <iostream>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")

// Helper to check if a file exists
bool FileExists(const std::wstring& path) {
    DWORD dwAttrib = GetFileAttributesW(path.c_str());
    return (dwAttrib != INVALID_FILE_ATTRIBUTES && 
           !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY));
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // 1. Get executable path to set directory
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    
    std::wstring exeDir = exePath;
    size_t lastSlash = exeDir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) {
        exeDir = exeDir.substr(0, lastSlash);
    }
    
    // Set current directory to executable directory
    SetCurrentDirectoryW(exeDir.c_str());
    
    // 2. Parse command line arguments to check for debug mode
    int argc;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    bool debugMode = false;
    
    if (argv != NULL) {
        for (int i = 1; i < argc; ++i) {
            if (wcscmp(argv[i], L"--debug") == 0 || wcscmp(argv[i], L"-d") == 0) {
                debugMode = true;
                break;
            }
        }
        LocalFree(argv);
    }
    
    // 3. Allocate console if debug mode is requested
    if (debugMode) {
        AllocConsole();
        // Redirect stdout/stderr/stdin to console
        FILE* fDummy;
        freopen_s(&fDummy, "CONOUT$", "w", stdout);
        freopen_s(&fDummy, "CONOUT$", "w", stderr);
        freopen_s(&fDummy, "CONIN$", "r", stdin);
        std::wcout.clear();
        std::wcerr.clear();
        std::wcin.clear();
        std::wcout << L"Debug mode activated. Console allocated.\n";
    }
    
    // 4. Decide python executable name and look for virtual environments
    std::wstring pythonExe = debugMode ? L"python.exe" : L"pythonw.exe";
    
    // Paths to search for python local venv
    std::vector<std::wstring> searchPaths = {
        L"venv\\Scripts\\" + pythonExe,
        L".venv\\Scripts\\" + pythonExe,
        L"print_server\\venv\\Scripts\\" + pythonExe,
        L"print_server\\.venv\\Scripts\\" + pythonExe
    };
    
    std::wstring chosenPython = pythonExe; // Fallback to PATH search
    for (const auto& path : searchPaths) {
        if (FileExists(path)) {
            chosenPython = L".\\" + path;
            if (debugMode) {
                std::wcout << L"Found local virtual environment Python: " << chosenPython << L"\n";
            }
            break;
        }
    }
    
    // Check if Python file to run exists
    std::wstring scriptPath = L"print_server\\run_app.py";
    if (!FileExists(scriptPath)) {
        MessageBoxW(NULL, 
            L"Error: 'print_server\\run_app.py' not found.\nMake sure the launcher is placed in the project root directory.", 
            L"Python Launcher Error", 
            MB_ICONERROR | MB_OK);
        return 1;
    }
    
    // 5. Build command line string: "python_exe" "print_server\run_app.py"
    // We quote paths to be safe.
    std::wstring cmdLine = L"\"" + chosenPython + L"\" \"" + scriptPath + L"\"";
    
    if (debugMode) {
        std::wcout << L"Executing: " << cmdLine << L"\n";
    }
    
    // 6. Launch the Python process
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    
    // If we're not in debug mode, suppress console window creation for python
    DWORD creationFlags = 0;
    if (!debugMode) {
        creationFlags |= CREATE_NO_WINDOW;
    }
    
    // We need to copy command line to a modifiable buffer as CreateProcessW can modify it
    std::vector<wchar_t> cmdLineBuf(cmdLine.begin(), cmdLine.end());
    cmdLineBuf.push_back(L'\0');
    
    BOOL success = CreateProcessW(
        NULL,                   // Application name
        cmdLineBuf.data(),      // Command line
        NULL,                   // Process handle not inheritable
        NULL,                   // Thread handle not inheritable
        FALSE,                  // Set handle inheritance to FALSE
        creationFlags,          // Creation flags
        NULL,                   // Use parent's environment block
        NULL,                   // Use parent's starting directory 
        &si,                    // Pointer to STARTUPINFO structure
        &pi                     // Pointer to PROCESS_INFORMATION structure
    );
    
    if (!success) {
        DWORD err = GetLastError();
        std::wstring errMsg = L"Failed to start Python process.\nCommand: " + cmdLine + 
                              L"\nError Code: " + std::to_wstring(err) +
                              L"\n\nPlease ensure Python is installed and in your system PATH, or a venv is set up.";
        MessageBoxW(NULL, errMsg.c_str(), L"Launcher Error", MB_ICONERROR | MB_OK);
        return 1;
    }
    
    if (debugMode) {
        std::wcout << L"Process started successfully. PID: " << pi.dwProcessId << L"\n";
        std::wcout << L"Waiting for process to exit...\n";
        // In debug mode, wait for the python process to exit
        WaitForSingleObject(pi.hProcess, INFINITE);
    }
    
    // Close process and thread handles
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    
    return 0;
}
