import threading
import time

from app import app
from desktop_app_qt import run_gui

# =========================
def run_flask():
    try:
        # PENTING: use_reloader=False wajib ditambahkan jika run di dalam thread
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print("Flask Error:", e)

# =========================
if __name__ == "__main__":
    print("Starting application...")

    # Jalankan Flask Server di Background Thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Tunggu 2 detik agar server Flask siap sebelum GUI muncul
    time.sleep(2)

    print("Starting GUI...")
    # Jalankan GUI di Main Thread
    run_gui()