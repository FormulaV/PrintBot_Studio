from datetime import datetime
from pathlib import Path
import json
import os
import pickle
import random
import re
import socket
import threading

from flask import Flask, jsonify, render_template_string, request, send_from_directory
from PyPDF2 import PdfReader, PdfWriter
from tensorflow.keras.utils import pad_sequences
import numpy as np
import tensorflow as tf

try:
    import win32print
except Exception:
    win32print = None


import sys

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    BASE_DIR = BUNDLE_DIR

UPLOAD_FOLDER = BASE_DIR / "uploads"
DOWNLOAD_FOLDER = BASE_DIR / "downloads"
DATABASE_PATH = BASE_DIR / "database.json"
DISCOVERY_PORT = 50505
DISCOVERY_REQUEST = "CETAKIN_DISCOVER"

UPLOAD_FOLDER.mkdir(exist_ok=True)
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_database():
    return {
        "files": [],
        "print_jobs": [],
    }


def load_database():
    if not DATABASE_PATH.exists():
        return default_database()

    try:
        with DATABASE_PATH.open(encoding="utf-8") as file:
            data = json.load(file)
            data.setdefault("files", [])
            data.setdefault("print_jobs", [])
            return data
    except json.JSONDecodeError:
        return default_database()


def save_database(data):
    with DATABASE_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def insert_file_document(info):
    data = load_database()
    files = data["files"]
    next_id = (max([item.get("id", 0) for item in files], default=0) + 1)
    document = {
        "id": next_id,
        "nama_file": info["nama_file"],
        "jenis_file": info["jenis_file"],
        "ukuran_file_kb": info["ukuran_file_kb"],
        "jumlah_halaman": info["jumlah_halaman"],
        "ukuran_kertas": info["ukuran_kertas"],
        "waktu_upload": now_text(),
        "user_id": info.get("user_id", ""),
    }
    files.append(document)
    save_database(data)
    return document


def latest_file_document(max_age_seconds=None, user_id=None):
    files = load_database()["files"]
    if not files:
        return None

    if user_id:
        files = [f for f in files if f.get("user_id", "") == user_id]
        if not files:
            return None

    latest = max(files, key=lambda item: item.get("id", 0))
    if max_age_seconds is None:
        return latest

    try:
        uploaded_at = datetime.strptime(latest["waktu_upload"], "%Y-%m-%d %H:%M:%S")
        age = (datetime.now() - uploaded_at).total_seconds()
        return latest if age <= max_age_seconds else None
    except Exception:
        return latest


# =========================
# PER-USER SESSION SYSTEM
# =========================

user_sessions = {}
user_sessions_lock = threading.RLock()


def default_remote_state():
    return {
        "nama_file": "",
        "page_start": 0,
        "page_end": 0,
        "page_indices": [],
        "pages": "Semua halaman",
        "execute_print": False,
        "printer_name": "",
        "color_mode": "Grayscale",
        "copies": 1,
        "command_id": 0,
    }


def default_pending_print():
    return {
        "file": None,
        "instructions": {},
        "summary": "",
        "awaiting_confirmation": False,
        "awaiting_printer_choice": False,
    }


def default_print_status():
    return {
        "status": "idle",
        "message": "",
        "printer_name": "",
        "command_id": 0,
        "updated_at": now_text(),
    }


def get_user_session(user_id):
    """Get or create a session for a given user_id."""
    if not user_id:
        user_id = "__anonymous__"
    with user_sessions_lock:
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "user_name": user_id,
                "messages": [],
                "bot_typing": False,
                "last_active": now_text(),
                "remote_state": default_remote_state(),
                "pending_print": default_pending_print(),
                "print_status": default_print_status(),
            }
        return user_sessions[user_id]


def clear_previous_session():
    global user_sessions
    # 1. Clear database
    save_database(default_database())
    # 2. Clear upload and download folders
    for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
        if folder.exists():
            for item in folder.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                    except Exception as e:
                        print(f"Error deleting file {item}: {e}")
                elif item.is_dir():
                    try:
                        import shutil
                        shutil.rmtree(item)
                    except Exception as e:
                        print(f"Error deleting dir {item}: {e}")
    # 3. Reset all user sessions
    with user_sessions_lock:
        user_sessions.clear()

clear_previous_session()


def delete_user_files_and_reset(user_id):
    session = get_user_session(user_id)
    session["remote_state"] = default_remote_state()
    session["pending_print"] = default_pending_print()
    session["print_status"] = default_print_status()

    # Load database
    db = load_database()
    files = db.get("files", [])
    
    updated_files = []
    for f in files:
        if f.get("user_id") == user_id:
            file_name = f.get("nama_file")
            if file_name:
                # 1. Delete from uploads
                upload_path = UPLOAD_FOLDER / file_name
                if upload_path.exists():
                    try:
                        upload_path.unlink()
                        print(f"Deleted upload file: {upload_path}")
                    except Exception as e:
                        print(f"Error deleting upload file {upload_path}: {e}")
                # 2. Delete from downloads
                for item in DOWNLOAD_FOLDER.iterdir():
                    if item.is_file() and file_name in item.name:
                        try:
                            item.unlink()
                            print(f"Deleted download file: {item}")
                        except Exception as e:
                            print(f"Error deleting download file {item}: {e}")
        else:
            updated_files.append(f)
            
    db["files"] = updated_files
    save_database(db)


def check_offline_users():
    import time
    while True:
        time.sleep(2)
        now = datetime.now()
        with user_sessions_lock:
            for uid, session in list(user_sessions.items()):
                if uid == "__anonymous__":
                    continue
                if session.get("online", True):
                    try:
                        last_active_dt = datetime.strptime(session["last_active"], "%Y-%m-%d %H:%M:%S")
                        elapsed = (now - last_active_dt).total_seconds()
                        if elapsed > 600.0:
                            session["online"] = False
                            user_name = session.get("user_name", uid)
                            session["messages"].append({
                                "sender": "system",
                                "message": f"{user_name} telah offline",
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            })
                            delete_user_files_and_reset(uid)
                    except Exception as e:
                        print(f"Error in offline check for {uid}: {e}")

threading.Thread(target=check_offline_users, daemon=True).start()


@app.before_request
def update_user_activity():
    user_id = request.args.get("user_id")
    if not user_id and request.is_json:
        try:
            req_json = request.json
            if isinstance(req_json, dict):
                user_id = req_json.get("user_id")
        except Exception:
            pass
    if not user_id and request.form:
        user_id = request.form.get("user_id")
    
    if user_id and user_id != "__anonymous__":
        ua = request.headers.get("User-Agent", "").lower()
        if "python-requests" not in ua:
            session = get_user_session(user_id)
            session["last_active"] = now_text()
            if not session.get("online", False):
                session["online"] = True
                # Set user_name early if provided in request to avoid showing UUID
                if not session.get("user_name") or session["user_name"] == user_id:
                    req_user_name = None
                    if request.is_json:
                        try:
                            req_user_name = request.json.get("user_name")
                        except Exception:
                            pass
                    if not req_user_name:
                        req_user_name = request.args.get("user_name") or request.form.get("user_name")
                    if req_user_name:
                        session["user_name"] = req_user_name
                
                display_name = session.get("user_name", user_id)
                session["messages"].append({
                    "sender": "system",
                    "message": f"{display_name} telah online",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })


try:
    bot_model = tf.keras.models.load_model(BUNDLE_DIR / "chatbot_rnn_model.h5")
    with (BUNDLE_DIR / "tokenizer.pickle").open("rb") as handle:
        bot_tokenizer = pickle.load(handle)
    with (BUNDLE_DIR / "classes.pickle").open("rb") as handle:
        bot_classes = pickle.load(handle)
    with (BUNDLE_DIR / "dataset_chatbot.json").open(encoding="utf-8") as file:
        bot_data = json.load(file)
except Exception as exc:
    bot_model = None
    bot_tokenizer = None
    bot_classes = []
    bot_data = {"intents": []}
    print(f"Model chatbot belum siap. Jalankan train_chatbot.py terlebih dahulu. Detail: {exc}")


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def discovery_responder():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", DISCOVERY_PORT))
    except OSError as exc:
        print(f"Discovery responder tidak bisa start: {exc}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data.decode(errors="ignore").strip() == DISCOVERY_REQUEST:
                payload = json.dumps({
                    "name": "Cetakin Print Server",
                    "base_url": f"http://{get_ip()}:5000/",
                })
                sock.sendto(payload.encode("utf-8"), addr)
        except Exception as exc:
            print(f"Discovery error: {exc}")


threading.Thread(target=discovery_responder, daemon=True).start()


def get_file_info(filepath):
    filepath = Path(filepath)
    info = {
        "nama_file": filepath.name,
        "ukuran_file_kb": round(filepath.stat().st_size / 1024, 2),
        "jenis_file": filepath.suffix.lower().replace(".", ""),
        "jumlah_halaman": "-",
        "ukuran_kertas": "-",
    }

    if filepath.suffix.lower() == ".pdf":
        reader = PdfReader(str(filepath))
        info["jumlah_halaman"] = len(reader.pages)

        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        w = min(width, height)
        h = max(width, height)

        if 580 <= w <= 610 and 820 <= h <= 860:
            info["ukuran_kertas"] = "A4"
        elif 600 <= w <= 630 and 770 <= h <= 810:
            info["ukuran_kertas"] = "Letter"
        elif 600 <= w <= 630 and 990 <= h <= 1030:
            info["ukuran_kertas"] = "Legal"
        else:
            info["ukuran_kertas"] = f"{round(width)} x {round(height)} pt"

    return info


def get_printers():
    if win32print is None:
        return []

    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [printer[2] for printer in win32print.EnumPrinters(flags)]
    except Exception:
        return []


def default_printer():
    if win32print is None:
        return ""

    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        printers = get_printers()
        return printers[0] if printers else ""


def printer_is_ready(printer_name):
    if win32print is None or not printer_name:
        return False, "Driver printer Windows belum tersedia."

    try:
        handle = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(handle, 2)
        finally:
            win32print.ClosePrinter(handle)

        attributes = int(info.get("Attributes", 0) or 0)
        status = int(info.get("Status", 0) or 0)

        offline_bits = [
            0x00000001,  # paused
            0x00000002,  # error
            0x00000004,  # pending deletion
            0x00000008,  # paper jam
            0x00000010,  # paper out
            0x00000020,  # manual feed
            0x00000040,  # paper problem
            0x00000080,  # offline
            0x00000800,  # output bin full
            0x00001000,  # not available
            0x00040000,  # no toner
            0x00100000,  # user intervention
            0x00200000,  # out of memory
            0x00400000,  # door open
        ]
        work_offline = bool(attributes & 0x00000400)
        has_blocking_status = any(status & bit for bit in offline_bits)

        if work_offline:
            return False, "Printer terdaftar, tetapi sedang Work Offline."
        if has_blocking_status:
            return False, f"Printer terdaftar, tetapi status Windows belum siap ({status})."
        return True, "Printer siap digunakan."
    except Exception as exc:
        return False, f"Printer tidak bisa dibuka oleh Windows: {exc}"


def get_ready_printers():
    ready = []
    for printer_name in get_printers():
        is_ready, _ = printer_is_ready(printer_name)
        if is_ready:
            ready.append(printer_name)
    return ready


def is_pdf_printer_name(printer_name):
    normalized = normalize_message(printer_name)
    return any(marker in normalized for marker in [
        "print to pdf", "save to pdf", "save as pdf", "microsoft print to pdf", "pdfcreator", "pdf writer"
    ])


def get_pdf_printers():
    return [printer for printer in get_printers() if is_pdf_printer_name(printer)]


def printer_connection_status():
    printers = get_printers()
    ready_printers = get_ready_printers()
    pdf_printers = get_pdf_printers()
    usable_printers = list(dict.fromkeys(ready_printers + pdf_printers))
    selected = default_printer()
    if selected and selected not in usable_printers:
        selected = ""
    if not selected and usable_printers:
        selected = usable_printers[0]

    connected = bool(usable_printers)
    message = (
        f"Printer siap digunakan: {selected or usable_printers[0]}"
        if connected else
        "Printer sedang tidak tersambung, mohon segera kontak kepada operator."
    )
    return {
        "printers": printers,
        "ready_printers": ready_printers,
        "pdf_printers": pdf_printers,
        "usable_printers": usable_printers,
        "selected_printer": selected,
        "connected": connected,
        "message": message,
    }


def append_chat_log(user_id, sender, message):
    session = get_user_session(user_id)
    session["messages"].append({
        "sender": sender,
        "message": str(message or ""),
        "time": now_text(),
    })
    # Keep only last 100 messages per user
    if len(session["messages"]) > 100:
        session["messages"] = session["messages"][-100:]
    session["last_active"] = now_text()


def chat_reply(user_id, user_message, payload):
    session = get_user_session(user_id)
    session["bot_typing"] = False
    messages = session["messages"]
    if not messages or messages[-1]["sender"] != "user" or messages[-1]["message"] != str(user_message or ""):
        append_chat_log(user_id, "user", user_message)
    append_chat_log(user_id, "bot", payload.get("response", ""))
    return jsonify(payload)


def normalize_message(text):
    text = str(text or "").strip().lower()
    # Collapse repeating letters (e.g., "hiii" -> "hi", "hayyy" -> "hay")
    text = re.sub(r'([a-zA-Z])\1+', r'\1', text)
    # Common variations of greetings normalized to standard
    text = re.sub(r'\b(hay|hey|hei|he|hlo|halo|helo|hello)\b', 'hai', text)
    return " ".join(text.split())


def contains_bad_words(text):
    normalized = normalize_message(text)
    # Remove punctuation for better match
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = " ".join(normalized.split())
    
    # List of bad words patterns
    bad_words_patterns = [
        r'\bngnt[o0][tdf]\w*\b', 
        r'\bng[e3]nt[o0]t\w*\b',
        r'\bk[o0]nt[o0]l\w*\b',
        r'\bkntl\w*\b',
        r'\bkontl\w*\b',
        r'\bm[e3]m[e3]k\w*\b',
        r'\bmemk\w*\b',
        r'\bmmk\w*\b',
        r'\banj[iy]ng\w*\b',
        r'\banjg\w*\b',
        r'\bajg\w*\b',
        r'\bbngst\w*\b',
        r'\bbgst\w*\b',
        r'\bbangsat\w*\b',
        r'\bbaj[iy]ngan\w*\b',
        r'\bbjgn\w*\b',
        r'\bc[iy]ba[iy]\w*\b',
        r'\bcby\w*\b',
        r'\bsh[iy]bal\w*\b',
        r'\bs[iy]bal\w*\b',
        r'\bs[e3]kk[iy]\w*\b',
        r'\bs[e3]k[iy]\w*\b',
        r'\bta[iy]k\w*\b',
        r'\bta[e3]\w*\b',
        r'\bg[o0]bl[o0]k\w*\b',
        r'\bg[o0]bl[o0]g\w*\b',
        r'\bgbl[o0]k\w*\b',
        r'\bt[o0]l[o0]l\w*\b',
        r'\basu\w*\b',
        r'\basw\w*\b',
        r'\bbab[iy]\w*\b',
        r'\bp[e3]l[e3]r\w*\b',
        r'\bng[e3]w[e3]\w*\b',
    ]
    for pattern in bad_words_patterns:
        if re.search(pattern, normalized):
            return True
    return False



def is_confirmation(text):
    normalized = normalize_message(re.sub(r"[^\w\s]", " ", text))
    tokens = [
        token for token in normalized.split()
        if token not in {"kak", "min", "mas", "mbak", "bang", "admin", "ya", "dong", "nih"}
    ]
    cleaned = " ".join(tokens) if tokens else normalized
    confirmation_words = {
        "iya", "iy", "y", "ya", "yes", "benar", "bener", "bnr", "betul", "oke", "ok",
        "sip", "setuju", "sesuai", "lanjut", "gas", "gass", "print", "cetak",
        "eksekusi", "acc", "approve", "pas", "cocok", "yo", "yoi", "yoii", "gaspol",
        "gaskeun", "okeii"
    }
    confirmation_phrases = {
        "sudah benar", "udah benar", "sudah sesuai", "udah sesuai", "langsung print",
        "lanjut print", "lanjut cetak", "cetak sekarang", "print sekarang",
        "iya lanjut", "iya cetak", "iya print", "oke lanjut", "oke print",
        "sip lanjut", "sip print", "sip cetak", "sip langsung print",
        "langsung cetak", "langsung print", "gas cetak", "gas print",
        "sudah pas", "udah pas", "oke gas print", "oke gass print",
        "oke gas cetak", "oke gass cetak", "oke gas", "oke gass",
        "yoi print", "yoi cetak", "lanjut gas", "lanjut gass",
        "gaskeun print", "gaskeun cetak", "gaspol print", "gaspol cetak",
        "yoi langsung print", "yoi langsung cetak", "oke langsung print",
        "oke langsung cetak", "oke gaskeun", "oke gaspol"
    }
    return cleaned in confirmation_words or cleaned in confirmation_phrases


def is_rejection(text):
    return normalize_message(text) in {
        "ga", "gak", "gk", "nggak", "enggak", "tidak", "tdk", "no", "bukan",
        "salah", "belum", "jangan", "cancel", "batal",
    }


def is_short_acknowledgement(text):
    normalized = normalize_message(re.sub(r"[^\w\s]", " ", text))
    short_messages = {
        "hmm", "hm", "oh", "ohh", "oke", "ok", "sip", "baik", "bentar", "bntar", "bntr", "sebentar",
        "tunggu", "nanti", "nanti kak", "bentar ya", "bentar ya kak", "sebentar ya",
        "bntar ya", "bntar ya kak", "bntr ya", "bntr ya kak", "sebentar ya kak",
        "saya cek dulu", "tunggu dulu", "ntar dulu",
    }
    return normalized in short_messages


def is_general_service_question(text):
    normalized = normalize_message(text)
    service_words = ["ada apa aja", "layanan", "melayani", "bisa apa", "fotokopi", "fotocopy", "atk", "selain print"]
    return any(word in normalized for word in service_words)


def wants_printer_list(text):
    normalized = normalize_message(text)
    cleaned = re.sub(r"[^\w\s]", " ", normalized).strip()
    words = cleaned.split()
    if not words:
        return False
    
    exact_matches = {
        "printer", "ganti", "iya ganti", "ya ganti", "ok ganti", "oke ganti", "ganti dong", 
        "ganti printer", "ganti printernya", "ubah printer", "pilih printer", "daftar printer", 
        "list printer", "lihat printer", "pilih printer lain", "ganti jenis printer", 
        "mau ganti printer", "ganti ke printer lain", "pengen ganti printer", "pilihan printer",
        "printer apa", "pakai printer mana", "printer tersedia", "pilih jenis printer",
    }
    if cleaned in exact_matches:
        return True
        
    phrases = [
        "ganti printer", "ubah printer", "pilih printer", "daftar printer", "list printer",
        "iya ganti", "ya ganti", "ganti jenis printer", "printer lain", "ganti printernya"
    ]
    if any(p in cleaned for p in phrases):
        return True
        
    return False


def is_direct_printer_choice(text, pending_print):
    normalized = normalize_message(text)
    if not pending_print.get("awaiting_printer_choice", False):
        return False
    
    instruction_terms = ["halaman", "hal", "page", "rangkap", "rngkap", "rngkp", "rgkap", "rgkp", "copy", "kopi", "warna", "grayscale", "bw", "hitam", "putih", "bolak", "duplex", "kertas"]
    if any(term in normalized for term in instruction_terms):
        return False
        
    return bool(re.fullmatch(r"(?:printer|nomor|no|pilih)?\s*\d+", normalized))


def has_printer_choice_intent(text, pending_print=None):
    normalized = normalize_message(text)
    return is_direct_printer_choice(text, pending_print or {}) or any(phrase in normalized for phrase in [
        "printer ", "pilih printer", "ganti printer", "pakai printer", "gunakan printer",
        "nomor printer", "printer nomor", "printer no",
    ])


def wants_save_to_pdf(text):
    normalized = normalize_message(text)
    return any(phrase in normalized for phrase in [
        "save to pdf", "print to pdf", "simpan pdf", "simpan ke pdf", "jadikan pdf",
        "buat pdf", "kirim pdf", "export pdf", "ekspor pdf",
    ])


def format_printer_options():
    status = printer_connection_status()
    printers = status["usable_printers"] or status["printers"]
    if not printers:
        return "Belum ada printer yang terdeteksi di PC."

    lines = ["Printer yang tersedia di PC:"]
    for index, printer_name in enumerate(printers, start=1):
        suffix = " (Save/Print to PDF)" if is_pdf_printer_name(printer_name) else ""
        lines.append(f"{index}. {printer_name}{suffix}")
    lines.append("\nBalas dengan nomor printer atau nama printernya. Contoh: printer 1")
    return "\n".join(lines)


def match_printer_choice(text, pending_print=None):
    normalized = normalize_message(text)
    instruction_terms = ["halaman", "hal", "page", "rangkap", "rngkap", "rngkp", "rgkap", "rgkp", "copy", "kopi", "warna", "grayscale", "bw", "hitam", "putih", "bolak", "duplex", "kertas"]
    has_explicit_printer_keyword = any(kw in normalized for kw in ["printer", "print ke", "cetak ke"])
    
    status = printer_connection_status()
    printers = status["usable_printers"] or status["printers"]
    if not printers:
        return ""

    number_match = None
    if has_printer_choice_intent(text, pending_print):
        if any(term in normalized for term in instruction_terms) and not has_explicit_printer_keyword:
            pass
        else:
            number_match = re.search(r"(?:printer|nomor|no|pilih)?\s*(\d+)", normalized)
            
    if number_match:
        index = int(number_match.group(1)) - 1
        if 0 <= index < len(printers):
            return printers[index]

    for printer_name in printers:
        printer_key = normalize_message(printer_name)
        if printer_key and (printer_key in normalized or (not any(term in normalized for term in instruction_terms) and normalized in printer_key)):
            return printer_name

    if wants_save_to_pdf(text):
        pdf_printers = status.get("pdf_printers", [])
        if pdf_printers:
            return pdf_printers[0]
    return ""


def set_selected_printer(user_id, printer_name):
    if not printer_name:
        return
    session = get_user_session(user_id)
    session["remote_state"]["printer_name"] = printer_name
    pending_print = session["pending_print"]
    pending_print["instructions"].setdefault("color_mode", "Grayscale")
    pending_print["instructions"].setdefault("pages", "Semua halaman")
    pending_print["instructions"].setdefault("copies", 1)
    pending_print["instructions"].setdefault("duplex", "Tidak")
    pending_print["instructions"].setdefault("paper", "Sesuai dokumen")
    pending_print["instructions"].setdefault("quality", "Standar")
    pending_print["instructions"]["printer_name"] = printer_name
    pending_print["awaiting_printer_choice"] = False


def merge_print_instructions(current, updates):
    merged = dict(current or {})
    for key, value in updates.items():
        if key == "pages" and value == "Semua halaman" and merged.get("pages"):
            continue
        merged[key] = value
    return merged


def resolve_page_bounds(page_text, file_info):
    try:
        total_pages = int(file_info.get("jumlah_halaman", 1)) if file_info else 1
    except Exception:
        total_pages = 1

    if page_text == "Semua halaman":
        return 0, max(total_pages - 1, 0)
    if "," in str(page_text) or ";" in str(page_text):
        indices = resolve_page_indices(page_text, file_info)
        if indices:
            return min(indices), max(indices)
        return 0, max(total_pages - 1, 0)
    if "-" in page_text:
        start, end = page_text.split("-", 1)
        page_start = max(int(start) - 1, 0)
        page_end = min(max(int(end) - 1, page_start), max(total_pages - 1, 0))
        return page_start, page_end
    page_start = max(int(page_text) - 1, 0)
    return page_start, min(page_start, max(total_pages - 1, 0))


def resolve_page_indices(page_text, file_info):
    try:
        total_pages = int(file_info.get("jumlah_halaman", 1)) if file_info else 1
    except Exception:
        total_pages = 1

    max_index = max(total_pages - 1, 0)
    normalized = normalize_message(page_text)
    if normalized == "semua halaman":
        return list(range(0, max_index + 1))

    selected = []
    for part in re.split(r"[,;]", normalized):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = max(int(start_text) - 1, 0)
            end = min(max(int(end_text) - 1, start), max_index)
            selected.extend(range(start, end + 1))
        else:
            index = min(max(int(part) - 1, 0), max_index)
            selected.append(index)

    return sorted(list(dict.fromkeys(selected))) or list(range(0, max_index + 1))


def sync_instructions_to_state(user_id, instructions, file_info):
    session = get_user_session(user_id)
    remote_state = session["remote_state"]
    
    page_text = instructions.get("pages", "Semua halaman")
    page_start, page_end = resolve_page_bounds(page_text, file_info)
    indices = resolve_page_indices(page_text, file_info)
    
    remote_state["nama_file"] = file_info["nama_file"] if file_info else ""
    remote_state["page_start"] = page_start
    remote_state["page_end"] = page_end
    remote_state["page_indices"] = indices
    remote_state["pages"] = page_text
    remote_state["printer_name"] = instructions.get("printer_name", "") or remote_state.get("printer_name", "") or default_printer()
    remote_state["color_mode"] = instructions.get("color_mode", "Grayscale")
    remote_state["copies"] = int(instructions.get("copies", 1))
    remote_state["command_id"] += 1


def build_pdf_download(file_info, instructions):
    if not file_info:
        raise ValueError("File belum tersedia.")
    if str(file_info.get("jenis_file", "")).lower() != "pdf":
        raise ValueError("Save to PDF hanya tersedia untuk file PDF.")

    source_path = UPLOAD_FOLDER / file_info["nama_file"]
    if not source_path.exists():
        raise ValueError("File sumber tidak ditemukan di server.")

    reader = PdfReader(str(source_path))
    page_indices = [
        index for index in resolve_page_indices(instructions.get("pages", "Semua halaman"), file_info)
        if 0 <= index < len(reader.pages)
    ]
    if not page_indices:
        raise ValueError("Nomor halaman tidak ditemukan di file PDF.")

    writer = PdfWriter()
    for index in page_indices:
        writer.add_page(reader.pages[index])

    stem = source_path.stem
    all_pages = page_indices == list(range(0, len(reader.pages)))
    if all_pages:
        suffix = "semua_halaman"
    elif len(page_indices) == 1:
        suffix = f"halaman_{page_indices[0] + 1}"
    else:
        labels = [str(index + 1) for index in page_indices]
        suffix = f"halaman_{'-'.join(labels[:6])}"
        if len(labels) > 6:
            suffix += "_dst"
    output_name = f"{stem}_{suffix}_PrintBot.pdf"
    output_path = DOWNLOAD_FOLDER / output_name
    with output_path.open("wb") as file:
        writer.write(file)
    return output_name


def parse_print_instructions(text, user_id):
    session = get_user_session(user_id)
    remote_state = session["remote_state"]
    pending_print = session["pending_print"]
    
    message = normalize_message(text)
    message = re.sub(r'(\d)[\s,;]*(?:sama|sma|sm|dengan|dan\s+juga|dan|dngn|dgn|with|and|serta|&|atau|or|terus|trus|plus|juga|lalu|kemudian)\s*(?=\d)', r'\1 , ', message)
    instructions = {
        "color_mode": "Grayscale",
        "pages": "Semua halaman",
        "copies": 1,
        "duplex": "Tidak",
        "paper": "Sesuai dokumen",
        "quality": "Standar",
        "printer_name": remote_state.get("printer_name") or default_printer(),
    }

    existing = pending_print.get("instructions") or {}
    if existing:
        instructions.update(existing)

    printer_choice = match_printer_choice(text, pending_print) if has_printer_choice_intent(text, pending_print) else ""
    if printer_choice:
        instructions["printer_name"] = printer_choice

    if any(word in message for word in ["warna", "color", "colour", "full color", "berwarna"]):
        instructions["color_mode"] = "Color"
    if any(word in message for word in ["hitam putih", "hitam", "putih", "item", "bw", "grayscale", "abu abu", "black white", "gray", "grey", "abu"]):
        instructions["color_mode"] = "Grayscale"


    # 1. Parse copies first and remove matched substring from message to avoid page number conflict
    copies_match_1 = re.search(r"(\d+)\s*(?:rangkap|rngkap|rngkp|rgkap|rgkp|rangkapan|rngkapan|rgkapan|copy|kopi|x|lembar|cetak)\s*(?:nya)?", message)
    copies_match_2 = re.search(r"(?:rangkap|rngkap|rngkp|rgkap|rgkp|rangkapan|rngkapan|rgkapan|copy|kopi|x|jumlah)\s*(?:nya)?[\s,:=]*(?:jadi|menjadi|dijadikan|sebanyak|yaitu|ke)?[\s,:=]*(\d+)", message)
    
    message_for_pages = message
    if copies_match_1:
        instructions["copies"] = max(1, int(copies_match_1.group(1)))
        message_for_pages = message_for_pages.replace(copies_match_1.group(0), " ")
    elif copies_match_2:
        instructions["copies"] = max(1, int(copies_match_2.group(1)))
        message_for_pages = message_for_pages.replace(copies_match_2.group(0), " ")

    # 2. Parse pages from message_for_pages
    # Search for page keyword (halaman, hal, page, range, no, nomor, dll)
    page_keyword_match = re.search(r"\b(?:halaman|hal|page|range|nomor|no)(?:nya)?\b", message_for_pages)
    if page_keyword_match:
        start_idx = page_keyword_match.end()
        subtext = message_for_pages[start_idx:]
        # Extract all numbers/ranges after the page keyword
        page_items = re.findall(r"\b\d+-\d+\b|\b\d+\b", subtext)
        if page_items:
            try:
                def get_sort_key(part):
                    part = part.strip()
                    if not part: return 0
                    if '-' in part:
                        val = part.split('-')[0].strip()
                        return int(val) if val.isdigit() else 0
                    return int(part) if part.isdigit() else 0
                page_items = [p.strip() for p in page_items if p.strip()]
                page_items.sort(key=get_sort_key)
                instructions["pages"] = ",".join(page_items)
            except Exception:
                instructions["pages"] = ",".join(page_items)
    elif "semua" in message_for_pages:
        instructions["pages"] = "Semua halaman"

    if any(word in message for word in ["bolak balik", "dua sisi", "double side", "duplex"]):
        instructions["duplex"] = "Ya"
    if any(word in message for word in ["satu muka", "1 muka", "jangan bolak balik"]):
        instructions["duplex"] = "Tidak"

    for paper in ["a4", "f4", "legal", "letter", "a3"]:
        if paper in message:
            instructions["paper"] = paper.upper()
            break

    if any(word in message for word in ["high", "bagus", "foto", "tajam"]):
        instructions["quality"] = "High Quality"
    if any(word in message for word in ["draft", "hemat", "standar"]):
        instructions["quality"] = "Standar"

    if wants_save_to_pdf(text):
        pdf_printers = get_pdf_printers()
        instructions["printer_name"] = pdf_printers[0] if pdf_printers else "Save to PDF"

    return instructions


def build_instruction_summary(instructions, pending_print):
    printer_name = instructions.get("printer_name") or "Belum dipilih"
    pages_display = instructions['pages']
    
    if pages_display != "Semua halaman":
        try:
            file_info = pending_print.get("file") or latest_file_document()
            indices = resolve_page_indices(pages_display, file_info)
            pages_display = f"{instructions['pages']} (Total: {len(indices)} halaman)"
        except Exception:
            pass

    return (
        "Instruksi Print:\n"
        f"1. Pilihan Warna: {instructions['color_mode']}\n"
        f"2. Pilihan Halaman: {pages_display}\n"
        f"3. Jumlah Rangkap: {instructions['copies']}\n"
        f"4. Bolak-balik: {instructions['duplex']}\n"
        f"5. Ukuran Kertas: {instructions['paper']}\n"
        f"6. Kualitas: {instructions['quality']}\n"
        f"7. Printer: {printer_name}\n\n"
        "Apakah ingin mengganti jenis printer lagi? Atau file ini sudah siap diprint pada printer yang terpilih?"
    )


def fallback_chat_response(user_message):
    if bot_model is None or bot_tokenizer is None:
        return "Model chatbot belum siap. Jalankan train_chatbot.py terlebih dahulu."

    try:
        max_len = int(bot_model.input_shape[1] or 35)
    except Exception:
        max_len = 35
    sequence = bot_tokenizer.texts_to_sequences([user_message])
    padded = pad_sequences(sequence, truncating="post", padding="post", maxlen=max_len)
    prediction = bot_model.predict(padded, verbose=0)[0]
    max_index = int(np.argmax(prediction))

    if float(prediction[max_index]) < 0.5:
        return "Maaf, Cetakin Dong belum mengerti maksud kakak. Bisa diulangi?"

    tag = bot_classes[max_index]
    for intent in bot_data["intents"]:
        if intent["tag"] == tag:
            return random.choice(intent["responses"])

    return "Ada kesalahan pada sistem."


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template_string("""
    <h2>Upload File Percetakan</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <br><br>
        <button type="submit">Upload</button>
    </form>
    <br>
    <a href="/data">Lihat Data</a>
    """)


@app.route("/ping")
def ping():
    return jsonify({
        "status": "ok",
        "base_url": f"http://{get_ip()}:5000/",
        "storage": "json_nosql",
    })


@app.route("/model_info")
def model_info():
    return jsonify({
        "model_loaded": bot_model is not None,
        "classes": bot_classes,
        "class_count": len(bot_classes),
        "model_file": "chatbot_rnn_model.h5",
    })


@app.route("/printers")
def printers():
    return jsonify(printer_connection_status())


# =========================
# USER REGISTRATION & SESSIONS
# =========================

@app.route("/register_user", methods=["POST"])
def register_user():
    data = request.json or {}
    user_id = data.get("user_id", "")
    user_name = data.get("user_name", "")
    
    if not user_id:
        return jsonify({"status": "error", "message": "user_id is required"}), 400
    
    session = get_user_session(user_id)
    if user_name:
        session["user_name"] = user_name
    session["last_active"] = now_text()
    
    return jsonify({"status": "success", "user_id": user_id, "user_name": session["user_name"]})


@app.route("/disconnect", methods=["POST"])
def disconnect_user():
    user_id = request.args.get("user_id")
    if not user_id and request.is_json:
        try:
            req_json = request.json
            if isinstance(req_json, dict):
                user_id = req_json.get("user_id")
        except Exception:
            pass
    if not user_id and request.form:
        user_id = request.form.get("user_id")
        
    if user_id and user_id != "__anonymous__":
        with user_sessions_lock:
            if user_id in user_sessions:
                session = user_sessions[user_id]
                if session.get("online", True):
                    session["online"] = False
                    user_name = session.get("user_name", user_id)
                    session["messages"].append({
                        "sender": "system",
                        "message": f"{user_name} telah offline",
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    delete_user_files_and_reset(user_id)
                    return jsonify({"status": "success", "message": "User disconnected"})
    return jsonify({"status": "ignored"})


@app.route("/user_sessions")
def list_user_sessions():
    """Return list of all user sessions for the desktop sidebar."""
    result = []
    with user_sessions_lock:
        for uid, session in user_sessions.items():
            if uid == "__anonymous__":
                continue
            messages = session.get("messages", [])
            last_message = ""
            last_time = session.get("last_active", "")
            if messages:
                last_msg = messages[-1]
                last_message = last_msg.get("message", "")[:80]
                last_time = last_msg.get("time", last_time)
            
            result.append({
                "user_id": uid,
                "user_name": session.get("user_name", uid),
                "last_message": last_message,
                "last_time": last_time,
                "message_count": len(messages),
                "has_file": bool(session.get("pending_print", {}).get("file")),
                "bot_typing": session.get("bot_typing", False),
                "online": session.get("online", True),
            })
    
    # Sort by last_time descending (most recent first)
    result.sort(key=lambda x: x.get("last_time", ""), reverse=True)
    return jsonify(result)


# =========================
# FILE UPLOAD (PER-USER)
# =========================

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]
    user_id = request.form.get("user_id", "") or request.args.get("user_id", "")
    original_filename = file.filename or "dokumen.pdf"
    filepath = UPLOAD_FOLDER / original_filename
    file.save(filepath)

    info = get_file_info(filepath)
    info["nama_file"] = original_filename
    info["user_id"] = user_id
    document = insert_file_document(info)

    if user_id:
        session = get_user_session(user_id)
        pending_print = session["pending_print"]
        remote_state = session["remote_state"]
        
        pending_print["file"] = document
        pending_print["awaiting_confirmation"] = False
        pending_print["instructions"] = {
            "color_mode": "Grayscale",
            "pages": "Semua halaman",
            "copies": 1,
            "duplex": "Tidak",
            "paper": "Sesuai dokumen",
            "quality": "Standar",
            "printer_name": remote_state.get("printer_name") or default_printer(),
        }
        pending_print["summary"] = ""
        pending_print["awaiting_printer_choice"] = False

        sync_instructions_to_state(user_id, pending_print["instructions"], document)

    return jsonify({
        "status": "success",
        "nama_file": document["nama_file"],
        "jenis_file": document["jenis_file"],
        "ukuran_kb": document["ukuran_file_kb"],
        "jumlah_halaman": document["jumlah_halaman"],
        "ukuran_kertas": document["ukuran_kertas"],
        "printer_connected": printer_connection_status()["connected"],
    })


@app.route("/data")
def lihat_data():
    rows = sorted(load_database()["files"], key=lambda item: item.get("id", 0), reverse=True)

    html = "<h2>Data Upload</h2><table border=1 cellpadding=5>"
    html += "<tr><th>ID</th><th>Nama</th><th>Jenis</th><th>Ukuran</th><th>Halaman</th><th>Kertas</th><th>Waktu</th><th>User</th></tr>"

    for row in rows:
        html += (
            f"<tr><td>{row['id']}</td><td>{row['nama_file']}</td>"
            f"<td>{row['jenis_file']}</td><td>{row['ukuran_file_kb']}</td>"
            f"<td>{row['jumlah_halaman']}</td><td>{row['ukuran_kertas']}</td>"
            f"<td>{row['waktu_upload']}</td><td>{row.get('user_id', '-')}</td></tr>"
        )

    html += "</table><br><a href='/'>Kembali</a>"
    return html


@app.route("/data_json")
def data_json():
    filename = request.args.get("filename")
    user_id = request.args.get("user_id", "")
    
    if user_id:
        session = get_user_session(user_id)
        remote_state = session["remote_state"]
        if not filename:
            filename = remote_state.get("nama_file")
    
    files = load_database()["files"]
    if filename:
        # If user_id specified, prefer that user's file
        if user_id:
            for f in reversed(files):
                if f.get("nama_file") == filename and f.get("user_id", "") == user_id:
                    return jsonify(f)
        for f in reversed(files):
            if f.get("nama_file") == filename:
                return jsonify(f)
    
    latest = latest_file_document(user_id=user_id if user_id else None)
    return jsonify(latest if latest else {})


@app.route("/downloads/<path:filename>")
def download_generated_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


@app.route("/uploads/<path:filename>")
def download_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


# =========================
# STATE MANAGEMENT (PER-USER)
# =========================

@app.route("/update_state", methods=["POST"])
def update_state():
    data = request.json or {}
    user_id = data.get("user_id", "")
    session = get_user_session(user_id)
    remote_state = session["remote_state"]

    remote_state["nama_file"] = data.get("nama_file", remote_state["nama_file"])
    remote_state["page_start"] = int(data.get("page_start", remote_state["page_start"]))
    remote_state["page_end"] = int(data.get("page_end", remote_state["page_end"]))
    remote_state["execute_print"] = bool(data.get("execute_print", False))
    remote_state["printer_name"] = data.get("printer_name", remote_state["printer_name"])
    remote_state["color_mode"] = data.get("color_mode", remote_state["color_mode"])
    remote_state["copies"] = int(data.get("copies", remote_state["copies"]))
    
    if "page_indices" in data:
        remote_state["page_indices"] = data["page_indices"]
    else:
        remote_state["page_indices"] = list(range(remote_state["page_start"], remote_state["page_end"] + 1))
        
    if "pages" in data:
        remote_state["pages"] = data["pages"]
    else:
        if remote_state["page_start"] == remote_state["page_end"]:
            remote_state["pages"] = str(remote_state["page_start"] + 1)
        else:
            remote_state["pages"] = f"{remote_state['page_start'] + 1}-{remote_state['page_end'] + 1}"
            
    remote_state["command_id"] += 1

    if remote_state["execute_print"]:
        session["print_status"].update({
            "status": "printing",
            "message": "Perintah cetak dikirim ke PC.",
            "printer_name": remote_state["printer_name"],
            "command_id": remote_state["command_id"],
            "updated_at": now_text(),
        })

    return jsonify({"status": "success", "state": remote_state})


@app.route("/reset_state", methods=["POST"])
def reset_state():
    data = request.json or {}
    user_id = data.get("user_id", "")
    
    if user_id:
        # Reset only this user's session
        session = get_user_session(user_id)
        session["messages"].clear()
        session["bot_typing"] = False
        session["remote_state"] = default_remote_state()
        session["pending_print"] = default_pending_print()
        session["print_status"] = default_print_status()
    else:
        # Reset all sessions and database (legacy behavior)
        save_database(default_database())
        for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
            if folder.exists():
                for item in folder.iterdir():
                    if item.is_file():
                        try:
                            item.unlink()
                        except Exception as e:
                            print(f"Error deleting file {item}: {e}")
                    elif item.is_dir():
                        try:
                            import shutil
                            shutil.rmtree(item)
                        except Exception as e:
                            print(f"Error deleting dir {item}: {e}")
        with user_sessions_lock:
            user_sessions.clear()

    return jsonify({"status": "success"})


@app.route("/get_state")
def get_state():
    user_id = request.args.get("user_id", "")
    session = get_user_session(user_id)
    return jsonify(session["remote_state"])


@app.route("/print_finished", methods=["POST"])
def print_finished():
    data = request.json or {}
    user_id = data.get("user_id", "")
    status_value = data.get("status", "done")
    printer_name = data.get("printer_name", "")

    session = get_user_session(user_id)
    session["print_status"].update({
        "status": status_value,
        "message": data.get("message", ""),
        "printer_name": printer_name,
        "command_id": int(data.get("command_id", session["remote_state"].get("command_id", 0))),
        "updated_at": now_text(),
    })
    return jsonify({"status": "success", "print_status": session["print_status"]})


@app.route("/print_status")
def get_print_status():
    user_id = request.args.get("user_id", "")
    session = get_user_session(user_id)
    return jsonify(session["print_status"])


# =========================
# CHAT (PER-USER)
# =========================

@app.route("/append_chat", methods=["POST"])
def append_chat():
    data = request.json or {}
    sender = data.get("sender", "bot")
    message = data.get("message", "")
    user_id = data.get("user_id", "")
    
    session = get_user_session(user_id)
    messages = session["messages"]
    if not messages or messages[-1]["sender"] != sender or messages[-1]["message"] != str(message or ""):
        append_chat_log(user_id, sender, message)
    return jsonify({"status": "success"})


@app.route("/chat_log")
def get_chat_log():
    user_id = request.args.get("user_id", "")
    session = get_user_session(user_id)
    return jsonify({
        "messages": session["messages"][-100:],
        "bot_typing": session["bot_typing"],
        "user_name": session.get("user_name", user_id),
    })


@app.route("/chat", methods=["POST"])
def chat():
    req_data = request.json or {}
    user_message = req_data.get("message", "")
    user_id = req_data.get("user_id", "")
    
    session = get_user_session(user_id)
    pending_print = session["pending_print"]
    remote_state = session["remote_state"]
    
    # Restore pending_print["file"] if it was cleared but exists in database
    if not pending_print.get("file"):
        db_file = latest_file_document(user_id=user_id)
        if db_file:
            pending_print["file"] = db_file
            if not pending_print.get("instructions"):
                pending_print["instructions"] = {
                    "color_mode": "Grayscale",
                    "pages": "Semua halaman",
                    "copies": 1,
                    "duplex": "Tidak",
                    "paper": "Sesuai dokumen",
                    "quality": "Standar",
                    "printer_name": remote_state.get("printer_name") or default_printer(),
                }
    
    # Check duplicate user message to avoid double logging
    messages = session["messages"]
    if not messages or messages[-1]["sender"] != "user" or messages[-1]["message"] != str(user_message or ""):
        append_chat_log(user_id, "user", user_message)
    
    session["bot_typing"] = True
    
    # Simulate a small delay for typing effect
    import time
    time.sleep(1.2)
    
    normalized = normalize_message(user_message)

    if contains_bad_words(user_message):
        return chat_reply(user_id, user_message, {
            "response": "Harap gunakan bahasa yang sopan agar kami dapat melayani Anda dengan baik."
        })

    if wants_printer_list(user_message):

        pending_print["awaiting_printer_choice"] = True
        return chat_reply(user_id, user_message, {
            "response": format_printer_options(),
            "action": "printer_list",
        })

    selected_printer = match_printer_choice(user_message, pending_print)
    if selected_printer and (
        has_printer_choice_intent(user_message, pending_print) or
        selected_printer.lower() in user_message.lower()
    ):
        set_selected_printer(user_id, selected_printer)
        if pending_print["file"]:
            pending_print["summary"] = build_instruction_summary(pending_print["instructions"], pending_print)
            pending_print["awaiting_confirmation"] = True
            
            file_info = pending_print["file"] or latest_file_document(user_id=user_id)
            sync_instructions_to_state(user_id, pending_print["instructions"], file_info)
            
            return chat_reply(user_id, user_message, {
                "response": f"Baik kak, printer dipilih: {selected_printer}\n\n{pending_print['summary']}",
                "action": "printer_selected",
                "printer_name": selected_printer,
            })

        return chat_reply(user_id, user_message, {
            "response": f"Baik kak, printer dipilih: {selected_printer}. Silakan lampirkan file PDF yang ingin diproses.",
            "action": "printer_selected",
            "printer_name": selected_printer,
        })

    if any(phrase in normalized for phrase in ["coba cek lagi", "cek lagi", "cek ulang", "printer sudah", "printer siap"]):
        printer_status = printer_connection_status()
        if not printer_status["connected"]:
            return chat_reply(user_id, user_message, {
                "response": "Printer sedang tidak tersambung, mohon segera kontak kepada operator. Setelah operator menyambungkan printer, kakak bisa balas \"coba cek lagi\"."
            })

        file_info = pending_print["file"] or latest_file_document(user_id=user_id)
        if file_info:
            return chat_reply(user_id, user_message, {
                "response": (
                    "Printer sudah terhubung kak. Ini detail file terakhir:\n"
                    f"- Nama: {file_info['nama_file']}\n"
                    f"- Besar File: {file_info['ukuran_file_kb']} KB\n"
                    f"- Jumlah Halaman: {file_info['jumlah_halaman']}\n"
                    f"- Ukuran Kertas: {file_info['ukuran_kertas']}\n"
                    f"- Jenis File: {str(file_info['jenis_file']).upper()}\n\n"
                    "Sekarang tuliskan instruksi cetaknya ya kak."
                )
            })

        return chat_reply(user_id, user_message, {"response": "Printer sudah terhubung kak. Silakan lampirkan file PDF yang ingin dicetak."})

    if not pending_print["awaiting_confirmation"] and is_short_acknowledgement(user_message):
        return chat_reply(user_id, user_message, {
            "response": "Baik kak, saya tunggu. Kalau sudah siap, kirim file PDF atau tulis instruksi cetaknya ya."
        })

    if not pending_print["awaiting_confirmation"] and is_general_service_question(user_message):
        return chat_reply(user_id, user_message, {
            "response": (
                "Di sini kakak bisa print dokumen dari HP, cek detail PDF, memberi instruksi warna/halaman/rangkap, "
                "serta menanyakan fotokopi, scan, laminating, jilid, dan produk ATK yang tersedia."
            )
        })

    if pending_print["awaiting_confirmation"]:
        if is_confirmation(normalized):
            instructions = pending_print["instructions"]
            file_info = pending_print["file"] or latest_file_document(user_id=user_id)
            page_text = instructions.get("pages", "Semua halaman")
            printer_name = instructions.get("printer_name", "") or remote_state.get("printer_name", "")

            if is_pdf_printer_name(printer_name) or wants_save_to_pdf(printer_name):
                try:
                    output_name = build_pdf_download(file_info, instructions)
                except Exception as exc:
                    return chat_reply(user_id, user_message, {
                        "response": f"Maaf kak, file PDF baru belum bisa dibuat: {exc}"
                    })

                pending_print["awaiting_confirmation"] = False
                file_url = request.host_url.rstrip("/") + f"/downloads/{output_name}"
                return chat_reply(user_id, user_message, {
                    "response": "Baik kak, file sudah saya pilah dan simpan kembali sebagai PDF. Silakan download file di bawah ini.",
                    "action": "pdf_ready",
                    "file_name": output_name,
                    "file_url": file_url,
                })

            printer_status = printer_connection_status()
            if not printer_status["connected"]:
                return chat_reply(user_id, user_message, {
                    "response": "Printer sedang tidak tersambung, mohon segera kontak kepada operator. Saya belum bisa mulai mencetak sebelum printer PC terdeteksi."
                })

            page_start, page_end = resolve_page_bounds(page_text, file_info)
            indices = resolve_page_indices(page_text, file_info)

            remote_state["nama_file"] = file_info["nama_file"] if file_info else ""
            remote_state["page_start"] = page_start
            remote_state["page_end"] = page_end
            remote_state["page_indices"] = indices
            remote_state["execute_print"] = True
            remote_state["printer_name"] = printer_name or printer_status.get("selected_printer", "") or default_printer()
            remote_state["color_mode"] = instructions.get("color_mode", "Grayscale")
            remote_state["copies"] = int(instructions.get("copies", 1))
            remote_state["command_id"] += 1

            session["print_status"].update({
                "status": "printing",
                "message": "Perintah cetak dikirim ke PC.",
                "printer_name": remote_state["printer_name"],
                "command_id": remote_state["command_id"],
                "updated_at": now_text(),
            })

            pending_print["awaiting_confirmation"] = False

            return chat_reply(user_id, user_message, {
                "response": "Baiklah kak mohon tunggu yaa, akan segera kami lakukan pencetakan",
                "action": "print_started",
                "printer_name": remote_state["printer_name"],
            })

        if is_rejection(normalized):
            pending_print["awaiting_confirmation"] = False
            pending_print["instructions"] = {}
            pending_print["summary"] = ""
            return chat_reply(user_id, user_message, {
                "response": "Baik kak, silakan kirimkan filenya ke mari. Pastikan filenya jelas ya, mau dicetak hitam putih atau warna? Dan berapa rangkap?"
            })

        if pending_print["file"] and any(word in normalized for word in [
            "print", "cetak", "warna", "grayscale", "bw", "halaman", "rangkap",
            "rngkap", "rngkp", "rgkap", "rgkp", "rangkapan", "rngkapan", "rgkapan",
            "copy", "bolak", "a4", "f4", "legal", "letter", "draft", "quality",
            "printer", "pdf", "simpan", "save", "hitam", "putih", "item", "puth",
            "colour", "color", "full", "abu", "grey", "gray", "hal", "hlm", "halamn",
            "halamann", "kopi", "copi", "double", "sisi", "duplex", "ubah", "ganti",
            "set", "koreksi", "edit", "revisi", "gnt"
        ]):
            instructions = parse_print_instructions(user_message, user_id)
            pending_print["instructions"] = merge_print_instructions(pending_print.get("instructions"), instructions)
            pending_print["summary"] = build_instruction_summary(pending_print["instructions"], pending_print)
            pending_print["awaiting_confirmation"] = True
            
            file_info = pending_print["file"] or latest_file_document(user_id=user_id)
            sync_instructions_to_state(user_id, pending_print["instructions"], file_info)
            
            return chat_reply(user_id, user_message, {"response": pending_print["summary"]})

        return chat_reply(user_id, user_message, {
            "response": "Saya sedang menunggu konfirmasi dari rangkuman instruksi tadi. Balas \"iya\" kalau sudah sesuai, atau tulis koreksinya seperti halaman, warna, atau jumlah rangkap."
        })

    if pending_print["file"] and any(word in normalized for word in [
        "print", "cetak", "warna", "grayscale", "bw", "halaman", "rangkap",
        "rngkap", "rngkp", "rgkap", "rgkp", "rangkapan", "rngkapan", "rgkapan",
        "copy", "bolak", "a4", "f4", "legal", "letter", "draft", "quality",
        "printer", "pdf", "simpan", "save", "hitam", "putih", "item", "puth",
        "colour", "color", "full", "abu", "grey", "gray", "hal", "hlm", "halamn",
        "halamann", "kopi", "copi", "double", "sisi", "duplex", "ubah", "ganti",
        "set", "koreksi", "edit", "revisi", "gnt"
    ]):
        instructions = parse_print_instructions(user_message, user_id)
        pending_print["instructions"] = merge_print_instructions(pending_print.get("instructions"), instructions)
        pending_print["summary"] = build_instruction_summary(pending_print["instructions"], pending_print)
        pending_print["awaiting_confirmation"] = True
        
        file_info = pending_print["file"] or latest_file_document(user_id=user_id)
        sync_instructions_to_state(user_id, pending_print["instructions"], file_info)
        
        return chat_reply(user_id, user_message, {"response": pending_print["summary"]})

    if pending_print["file"] and is_confirmation(normalized):
        return chat_reply(user_id, user_message, {
            "response": "File sudah saya terima kak, tapi instruksi cetaknya belum lengkap. Mau dicetak warna atau hitam putih, halaman berapa, dan berapa rangkap?"
        })

    return chat_reply(user_id, user_message, {"response": fallback_chat_response(user_message)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
