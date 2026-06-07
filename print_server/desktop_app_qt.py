import sys
import os
import socket
import requests
import win32print
import win32api
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QLineEdit, QScrollArea, QMessageBox, QStackedWidget,
                             QTextEdit, QFrame, QListWidget, QListWidgetItem,
                             QSplitter, QSizePolicy, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QColor, QBrush, QPen, QIcon
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtPrintSupport import QPrinter

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = BUNDLE_DIR


# =========================
# GET IP ADDRESS
# =========================
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

# =========================
# CUSTOM USER LIST ITEM WIDGET (WhatsApp-style)
# =========================
class UserListItemWidget(QWidget):
    def __init__(self, user_name, last_message, last_time, has_file=False, online=True, unread_count=0, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Avatar circle
        avatar = QLabel()
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignCenter)
        initials = "".join([w[0].upper() for w in user_name.split()[:2]]) if user_name else "?"
        avatar.setText(initials)
        avatar.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #215B63, stop:1 #2D737C);
                color: #FFFFFF;
                border-radius: 22px;
                font-weight: bold;
                font-size: 15px;
            }
        """)
        layout.addWidget(avatar)
        
        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 0, 0, 0)
        
        # Top row: name + status + time
        top_row = QHBoxLayout()
        top_row.setSpacing(4)
        
        name_label = QLabel(user_name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #12363B;")
        top_row.addWidget(name_label)
        
        # Online / Offline Status Badge
        status_text = "●"
        status_color = "#10B981" if online else "#9CA3AF"  # Green for online, Gray for offline
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"font-size: 10px; color: {status_color}; font-weight: bold;")
        status_label.setToolTip("Online" if online else "Offline")
        top_row.addWidget(status_label)
        
        top_row.addStretch()
        
        # Time label
        time_display = last_time
        if last_time and " " in last_time:
            time_display = last_time.split(" ")[1][:5]
        time_label = QLabel(time_display)
        time_label.setStyleSheet("font-size: 10px; color: #8A9A96;")
        top_row.addWidget(time_label)
        
        text_col.addLayout(top_row)
        
        # Bottom row: last message + file badge + unread badge
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        
        msg_text = last_message if last_message else "Belum ada pesan"
        if len(msg_text) > 40:
            msg_text = msg_text[:40] + "…"
        msg_label = QLabel(msg_text)
        msg_label.setStyleSheet("font-size: 11px; color: #6B7F78;")
        bottom_row.addWidget(msg_label)
        
        bottom_row.addStretch()
        
        if has_file:
            file_badge = QLabel("📄")
            file_badge.setStyleSheet("font-size: 13px;")
            bottom_row.addWidget(file_badge)
            
        if unread_count > 0:
            unread_badge = QLabel(str(unread_count))
            unread_badge.setFixedSize(18, 18)
            unread_badge.setAlignment(Qt.AlignCenter)
            # Creative neon violet/purple color, not green or blue!
            unread_badge.setStyleSheet("""
                QLabel {
                    background: #8B5CF6;
                    color: #FFFFFF;
                    border-radius: 9px;
                    font-size: 9px;
                    font-weight: bold;
                }
            """)
            bottom_row.addWidget(unread_badge)
        
        text_col.addLayout(bottom_row)
        
        layout.addLayout(text_col, 1)

# =========================
# MAIN APP
# =========================
class PrintServerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrintBot Studio - Operator")
        icon_path = os.path.join(BUNDLE_DIR, "app_icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BUNDLE_DIR, "app_icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(1280, 780)
        
        # State Variables
        self.last_id = None
        self.current_file = None
        self.current_data = None
        self.current_page = 0
        self.total_pages = 0

        # Variabel baru untuk pembatasan halaman
        self.page_start = 0  
        self.page_end = 0
        self.page_indices = []
        self.current_page_idx = 0
        self.remote_color_mode = "Grayscale"
        self.remote_copies = 1
        self.last_chat_count = 0
        self.last_bot_typing = False
 
        # [BARU] Untuk melacak ID perintah dari HP
        self.last_command_id = 0

        # [BARU] Multi-user state
        self.active_user_id = None
        self.user_sessions_cache = []
        self.unread_counts = {}
        self.last_read_message_counts = {}

        # Setup Stacked Widget untuk berpindah layar
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.apply_theme()

        # Inisialisasi Layar
        self.init_start_screen()
        self.init_main_menu_screen()

        # Mulai dari layar pertama
        self.stacked_widget.setCurrentIndex(0)

        # Setup Timer untuk Polling (belum dijalankan)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_data)

        self.chat_timer = QTimer(self)
        self.chat_timer.timeout.connect(self.poll_chat_log)
        self.chat_timer.start(1000)

        # Timer untuk polling user sessions (sidebar)
        self.user_sessions_timer = QTimer(self)
        self.user_sessions_timer.timeout.connect(self.poll_user_sessions)

        # System Tray setup
        self.allow_exit = False
        self.init_tray_icon()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #F6F0E4;
                color: #172E32;
                font-family: Segoe UI, Arial;
                font-size: 12px;
            }
            QLabel {
                background: transparent;
            }
            QLabel#HeroTitle {
                color: #12363B;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#SectionTitle {
                color: #12363B;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#StatusBadge {
                background: #D7EADF;
                color: #12363B;
                border: 1px solid #215B63;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QFrame#Panel {
                background: #FFFDF6;
                border: 1px solid #CDAA7D;
                border-radius: 8px;
            }
            QPushButton {
                background: #215B63;
                color: white;
                border: 0;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: #2D737C; }
            QPushButton:disabled { background: #A7B1AA; color: #F4F4F4; }
            QPushButton#AccentButton {
                background: #F59E0B;
                color: #12363B;
            }
            QPushButton#DangerButton {
                background: #A84F45;
            }
            QLineEdit, QComboBox {
                background: #FFFFFF;
                border: 1px solid #CDAA7D;
                border-radius: 6px;
                padding: 8px;
            }
            QTextEdit {
                background: #12363B;
                color: #FFF7E8;
                border: 1px solid #215B63;
                border-radius: 8px;
                padding: 10px;
            }
            QScrollArea { border: 0; }
            QScrollBar:vertical {
                border: none;
                background: #F6F0E4;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CDAA7D;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #B69367;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #F6F0E4;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #CDAA7D;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #B69367;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QListWidget {
                background: #FFFDF6;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #E6D2B5;
                padding: 0px;
            }
            QListWidget::item:selected {
                background: #E8F0ED;
            }
            QListWidget::item:hover {
                background: #F0EBE0;
            }
        """)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = os.path.join(BUNDLE_DIR, "app_icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BUNDLE_DIR, "app_icon.ico")
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("PrintBot Studio - Operator")
        
        tray_menu = QMenu()
        
        show_action = QAction("Buka Panel Operator", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Keluar/Matikan Server", self)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def exit_app(self):
        self.allow_exit = True
        self.tray_icon.hide()
        QApplication.quit()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show_window()

    def closeEvent(self, event):
        if not self.allow_exit:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "PrintBot Studio",
                "Aplikasi tetap berjalan di background.\nBuka kembali melalui icon di tray.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            event.accept()

    # =========================
    # SCREEN 1 (START)
    # =========================
    def init_start_screen(self):
        start_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel("PRINT SERVER")
        title_label.setObjectName("HeroTitle")
        title_label.setText("PrintBot Studio")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel("Dashboard operator untuk file, printer, dan alur chatbot")
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)

        layout.addSpacing(20)

        start_btn = QPushButton("Start Server")
        start_btn.setObjectName("AccentButton")
        start_btn.setFixedWidth(200)
        start_btn.clicked.connect(self.start_server)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("DangerButton")
        close_btn.setFixedWidth(200)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        start_widget.setLayout(layout)
        self.stacked_widget.addWidget(start_widget)

    def start_server(self):
        # Pindah ke layar Main Menu dan jalankan polling langsung tanpa popup IP
        self.stacked_widget.setCurrentIndex(1)
        self.poll_timer.start(3000) # Polling setiap 3 detik
        self.user_sessions_timer.start(2000) # Poll user sessions setiap 2 detik
        self.poll_chat_log()

    # =========================
    # SCREEN 2 (MAIN MENU)
    # =========================
    def init_main_menu_screen(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        # SCROLL AREA (Document Panel)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(580)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QFrame()
        scroll_content.setObjectName("Panel")
        
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(18, 18, 18, 18)
        self.scroll_layout.setSpacing(12)

        # Header Title of the Document Panel
        title = QLabel("Panel Dokumen")
        title.setObjectName("SectionTitle")
        self.scroll_layout.addWidget(title, alignment=Qt.AlignCenter)
        
        # Subtitle or Hint
        sub_title = QLabel("Detail preview file masuk dan konfigurasi pencetakan")
        sub_title.setStyleSheet("color: #8A9A96; font-size: 11px; margin-bottom: 8px;")
        self.scroll_layout.addWidget(sub_title, alignment=Qt.AlignCenter)

        # Active user indicator
        self.active_user_label = QLabel("Belum ada user aktif")
        self.active_user_label.setStyleSheet("""
            background: #215B63; color: #FFFFFF; border-radius: 6px;
            padding: 6px 14px; font-weight: bold; font-size: 12px;
        """)
        self.scroll_layout.addWidget(self.active_user_label, alignment=Qt.AlignCenter)

        # Side-by-side layout
        side_layout = QHBoxLayout()
        side_layout.setSpacing(20)
        
        # Left Side (Preview Panel)
        preview_panel = QVBoxLayout()
        preview_panel.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        preview_panel.setSpacing(10)
        
        # Preview Image Label
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(360, 460)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px dashed #CDAA7D; background: #FFFDF9; border-radius: 8px;")
        preview_panel.addWidget(self.preview_label)
        
        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignCenter)
        
        self.prev_btn = QPushButton("<<")
        self.prev_btn.setFixedWidth(50)
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page: 0/0")
        self.page_label.setStyleSheet("font-weight: bold; color: #12363B;")
        nav_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton(">>")
        self.next_btn.setFixedWidth(50)
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        
        preview_panel.addLayout(nav_layout)
        side_layout.addLayout(preview_panel)
        
        # Right Side (Controls Panel)
        controls_panel = QVBoxLayout()
        controls_panel.setAlignment(Qt.AlignTop)
        controls_panel.setSpacing(10)
        
        # Status Badge inside controls
        status_container = QHBoxLayout()
        status_container.addWidget(QLabel("Status:"), alignment=Qt.AlignVCenter)
        self.status_label = QLabel("Menunggu File...")
        self.status_label.setObjectName("StatusBadge")
        status_container.addWidget(self.status_label)
        controls_panel.addLayout(status_container)
        
        # Info Box / Metadata Card
        info_card = QFrame()
        info_card.setStyleSheet("QFrame { background: #FFFDF9; border: 1px solid #E6D2B5; border-radius: 8px; }")
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(8, 8, 8, 8)
        
        info_title = QLabel("Metadata File")
        info_title.setStyleSheet("font-weight: bold; color: #12363B; font-size: 13px;")
        info_card_layout.addWidget(info_title)
        
        self.info_label = QLabel("Belum ada file masuk")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #172E32; font-family: Consolas, monospace;")
        info_card_layout.addWidget(self.info_label)
        
        controls_panel.addWidget(info_card)
        
        # Inputs Group Card
        inputs_card = QFrame()
        inputs_card.setStyleSheet("QFrame { background: #FFFDF9; border: 1px solid #E6D2B5; border-radius: 8px; }")
        inputs_layout = QVBoxLayout(inputs_card)
        inputs_layout.setSpacing(8)
        
        inputs_layout.addWidget(QLabel("Halaman (contoh: 1 atau 1-3):"))
        self.page_entry = QLineEdit()
        self.page_entry.setPlaceholderText("Semua halaman")
        self.page_entry.editingFinished.connect(self.on_page_input)
        inputs_layout.addWidget(self.page_entry)

        inputs_layout.addWidget(QLabel("Jumlah Rangkap:"))
        self.copies_entry = QLineEdit()
        self.copies_entry.setPlaceholderText("1")
        self.copies_entry.editingFinished.connect(self.on_copies_input)
        inputs_layout.addWidget(self.copies_entry)

        inputs_layout.addWidget(QLabel("Pilihan Warna:"))
        self.color_box = QComboBox()
        self.color_box.addItems(["Grayscale", "Color"])
        self.color_box.currentIndexChanged.connect(self.on_color_changed)
        inputs_layout.addWidget(self.color_box)
        
        inputs_layout.addWidget(QLabel("Pilih Printer Target:"))
        self.printer_box = QComboBox()
        self.printer_box.addItems(self.get_printers())
        self.printer_box.currentIndexChanged.connect(self.on_printer_changed)
        inputs_layout.addWidget(self.printer_box)
        
        controls_panel.addWidget(inputs_card)
        
        # Actions Group Card
        actions_card = QFrame()
        actions_card.setStyleSheet("QFrame { background: #FFFDF9; border: 1px solid #E6D2B5; border-radius: 8px; }")
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setSpacing(6)
        
        # Top buttons row
        test_buttons_layout = QHBoxLayout()
        test_conn_btn = QPushButton("Cek Koneksi")
        test_conn_btn.clicked.connect(self.test_connection)
        test_buttons_layout.addWidget(test_conn_btn)
        
        test_print_btn = QPushButton("Test Print")
        test_print_btn.clicked.connect(self.test_print)
        test_buttons_layout.addWidget(test_print_btn)
        actions_layout.addLayout(test_buttons_layout)
        
        # Primary print button
        print_btn = QPushButton("PRINT DOKUMEN")
        print_btn.setObjectName("AccentButton")
        print_btn.setFixedHeight(38)
        print_btn.clicked.connect(self.print_file)
        actions_layout.addWidget(print_btn)
        
        # Danger / delete button
        reset_btn = QPushButton("Hapus Dokumen")
        reset_btn.setObjectName("DangerButton")
        reset_btn.clicked.connect(self.reset_file)
        actions_layout.addWidget(reset_btn)
        
        controls_panel.addWidget(actions_card)
        
        side_layout.addLayout(controls_panel)
        self.scroll_layout.addLayout(side_layout)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # ====================================
        # CHAT PANEL (Single-column layout with Stacked Widget)
        # ====================================
        chat_panel = QFrame()
        chat_panel.setObjectName("Panel")
        chat_panel.setFixedWidth(360)  # Fixed width to prevent overlapping/squeezing
        
        chat_panel_layout = QVBoxLayout(chat_panel)
        chat_panel_layout.setContentsMargins(0, 0, 0, 0)
        chat_panel_layout.setSpacing(0)

        # QStackedWidget for Chat Panel
        self.chat_stack = QStackedWidget()
        chat_panel_layout.addWidget(self.chat_stack)

        # PAGE 0: User List View (Gambar 3)
        self.user_list_page = QWidget()
        self.user_list_page.setStyleSheet("background: #FFFDF6; border: none;")
        user_list_page_layout = QVBoxLayout(self.user_list_page)
        user_list_page_layout.setContentsMargins(0, 0, 0, 0)
        user_list_page_layout.setSpacing(0)

        # Page 0 Header (similar to Gambar 1 but clean and fixed height)
        user_list_header = QFrame()
        user_list_header.setFixedHeight(48)
        user_list_header.setStyleSheet("""
            QFrame { 
                background: #215B63; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                border: none;
            }
        """)
        user_list_header_layout = QHBoxLayout(user_list_header)
        user_list_header_layout.setContentsMargins(16, 0, 16, 0)
        
        user_list_title = QLabel("💬 Daftar Chat User")
        user_list_title.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold; border: none;")
        user_list_header_layout.addWidget(user_list_title)
        
        user_list_header_layout.addStretch()
        
        self.chat_user_count_label = QLabel("0 user")
        self.chat_user_count_label.setStyleSheet("color: #A4C5BC; font-size: 11px; border: none;")
        user_list_header_layout.addWidget(self.chat_user_count_label)
        
        user_list_page_layout.addWidget(user_list_header)

        # Search bar
        self.user_search = QLineEdit()
        self.user_search.setPlaceholderText("🔍 Cari user...")
        self.user_search.setStyleSheet("""
            QLineEdit {
                background: #F6F0E4; border: none; border-bottom: 1px solid #E6D2B5;
                border-radius: 0; padding: 10px 12px; font-size: 12px;
            }
        """)
        self.user_search.textChanged.connect(self.filter_user_list)
        user_list_page_layout.addWidget(self.user_search)

        # User list
        self.user_list_widget = QListWidget()
        self.user_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.user_list_widget.itemClicked.connect(self.on_user_selected)
        user_list_page_layout.addWidget(self.user_list_widget)

        # Empty state
        self.empty_user_label = QLabel("Belum ada user yang chat.\nMenunggu koneksi dari HP...")
        self.empty_user_label.setAlignment(Qt.AlignCenter)
        self.empty_user_label.setStyleSheet("color: #8A9A96; font-size: 12px; padding: 20px; border: none;")
        user_list_page_layout.addWidget(self.empty_user_label)

        self.chat_stack.addWidget(self.user_list_page)

        # PAGE 1: Chat Detail View (Gambar 2)
        self.chat_detail_page = QWidget()
        self.chat_detail_page.setStyleSheet("background: #FFFDF6; border: none;")
        chat_detail_page_layout = QVBoxLayout(self.chat_detail_page)
        chat_detail_page_layout.setContentsMargins(0, 0, 0, 0)
        chat_detail_page_layout.setSpacing(0)

        # Page 1 Header (shows selected user name + back button)
        self.chat_detail_header = QFrame()
        self.chat_detail_header.setFixedHeight(48)
        self.chat_detail_header.setStyleSheet("""
            QFrame { 
                background: #1a4248; border: none;
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px;
                border-bottom: 1px solid #215B63;
            }
        """)
        detail_header_layout = QHBoxLayout(self.chat_detail_header)
        detail_header_layout.setContentsMargins(8, 0, 16, 0)
        detail_header_layout.setSpacing(8)
        
        # Back button
        self.back_to_list_btn = QPushButton("←")
        self.back_to_list_btn.setFixedSize(32, 32)
        self.back_to_list_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 16px;
                padding: 0;
            }
            QPushButton:hover {
                background: #215B63;
            }
        """)
        self.back_to_list_btn.clicked.connect(self.go_back_to_user_list)
        detail_header_layout.addWidget(self.back_to_list_btn)
        
        self.chat_detail_user_label = QLabel("Pilih user")
        self.chat_detail_user_label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14px; border: none;")
        detail_header_layout.addWidget(self.chat_detail_user_label)

        detail_header_layout.addStretch()
        
        self.chat_detail_status_label = QLabel("")
        self.chat_detail_status_label.setStyleSheet("color: #A4C5BC; font-size: 11px; border: none;")
        detail_header_layout.addWidget(self.chat_detail_status_label)

        chat_detail_page_layout.addWidget(self.chat_detail_header)

        # Chat messages area
        self.chat_log_text = QTextEdit()
        self.chat_log_text.setReadOnly(True)
        self.chat_log_text.setPlaceholderText("Belum ada pesan.")
        self.chat_log_text.setStyleSheet("""
            QTextEdit {
                background: #12363B;
                color: #FFF7E8;
                border: none;
                border-radius: 0;
                padding: 10px;
            }
        """)
        chat_detail_page_layout.addWidget(self.chat_log_text)

        # Refresh button
        refresh_chat_btn = QPushButton("🔄 Refresh Chat")
        refresh_chat_btn.setStyleSheet("""
            QPushButton {
                background: #1a4248; color: #A4C5BC; border: none;
                border-bottom-right-radius: 8px; border-bottom-left-radius: 8px; padding: 10px;
                font-weight: normal; font-size: 12px;
            }
            QPushButton:hover { background: #215B63; color: #FFFFFF; }
        """)
        refresh_chat_btn.clicked.connect(self.poll_chat_log)
        chat_detail_page_layout.addWidget(refresh_chat_btn)

        self.chat_stack.addWidget(self.chat_detail_page)

        main_layout.addWidget(chat_panel)
        self.stacked_widget.addWidget(main_widget)

    # =========================
    # USER SESSION POLLING
    # =========================
    def poll_user_sessions(self):
        try:
            res = requests.get("http://127.0.0.1:5000/user_sessions", timeout=1)
            if res.status_code == 200:
                sessions = res.json()
                self.user_sessions_cache = sessions
                self.update_user_list(sessions)
        except Exception:
            pass

    def update_user_list(self, sessions):
        # Update unread counts first
        for session_data in sessions:
            uid = session_data.get("user_id")
            msg_count = session_data.get("message_count", 0)
            
            if uid == self.active_user_id:
                self.unread_counts[uid] = 0
                self.last_read_message_counts[uid] = msg_count
            else:
                if uid not in self.last_read_message_counts:
                    self.last_read_message_counts[uid] = msg_count
                    self.unread_counts[uid] = 0
                elif msg_count > self.last_read_message_counts[uid]:
                    self.unread_counts[uid] = msg_count - self.last_read_message_counts[uid]

        search_text = self.user_search.text().strip().lower()
        
        # Remember current selection
        current_selected_id = self.active_user_id
        
        self.user_list_widget.clear()
        
        filtered = sessions
        if search_text:
            filtered = [s for s in sessions if search_text in s.get("user_name", "").lower()]
        
        if not filtered:
            self.empty_user_label.setVisible(True)
            self.user_list_widget.setVisible(False)
        else:
            self.empty_user_label.setVisible(False)
            self.user_list_widget.setVisible(True)
            
            for session_data in filtered:
                user_id = session_data.get("user_id", "")
                user_name = session_data.get("user_name", user_id)
                last_message = session_data.get("last_message", "")
                last_time = session_data.get("last_time", "")
                has_file = session_data.get("has_file", False)
                online = session_data.get("online", True)
                unread_count = self.unread_counts.get(user_id, 0)
                
                item_widget = UserListItemWidget(user_name, last_message, last_time, has_file, online, unread_count)
                
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(0, 72))
                list_item.setData(Qt.UserRole, user_id)
                list_item.setData(Qt.UserRole + 1, user_name)
                
                self.user_list_widget.addItem(list_item)
                self.user_list_widget.setItemWidget(list_item, item_widget)
                
                # Restore selection
                if user_id == current_selected_id:
                    list_item.setSelected(True)
                    self.user_list_widget.setCurrentItem(list_item)
                    
                    # Update detail header status dynamically
                    self.chat_detail_status_label.setText("Online" if online else "Offline")
                    if online:
                        self.chat_detail_status_label.setStyleSheet("color: #A4C5BC; font-size: 11px; border: none;")
                        self.active_user_label.setText(f"👤 User aktif: {user_name}")
                    else:
                        self.chat_detail_status_label.setStyleSheet("color: #8A9A96; font-size: 11px; border: none;")
                        self.active_user_label.setText("Belum ada user aktif")
        
        self.chat_user_count_label.setText(f"{len(sessions)} user")

    def filter_user_list(self, text):
        self.update_user_list(self.user_sessions_cache)

    def on_user_selected(self, item):
        user_id = item.data(Qt.UserRole)
        user_name = item.data(Qt.UserRole + 1)
        
        if user_id == self.active_user_id:
            self.chat_stack.setCurrentIndex(1)
            return
            
        self.active_user_id = user_id
        self.last_chat_count = 0  # Force refresh
        self.last_bot_typing = False
        self.last_command_id = 0
        self.last_id = None
        
        self.chat_detail_user_label.setText(f"💬 {user_name}")
        
        # Check online status from cache
        online = True
        if hasattr(self, 'user_sessions_cache') and self.user_sessions_cache:
            for session_data in self.user_sessions_cache:
                if session_data.get("user_id") == user_id:
                    online = session_data.get("online", True)
                    break
                    
        self.chat_detail_status_label.setText("Online" if online else "Offline")
        if online:
            self.chat_detail_status_label.setStyleSheet("color: #A4C5BC; font-size: 11px; border: none;")
            self.active_user_label.setText(f"👤 User aktif: {user_name}")
        else:
            self.chat_detail_status_label.setStyleSheet("color: #8A9A96; font-size: 11px; border: none;")
            self.active_user_label.setText("Belum ada user aktif")
        
        # Clear unread
        self.unread_counts.pop(user_id, None)
        
        # Switch chat view to Page 1 (Chat Detail)
        self.chat_stack.setCurrentIndex(1)
        
        # Immediately poll this user's chat and data
        self.poll_chat_log()
        self.poll_data()

    def go_back_to_user_list(self):
        self.user_list_widget.clearSelection()
        self.active_user_id = None
        self.active_user_label.setText("Belum ada user aktif")
        self.preview_label.clear()
        self.info_label.setText("Belum ada file masuk")
        self.status_label.setText("Menunggu File...")
        self.page_label.setText("Page: 0/0")
        self.page_entry.clear()
        self.copies_entry.clear()
        self.current_file = None
        self.current_data = None
        self.chat_stack.setCurrentIndex(0)

    # =========================
    # GET PRINTER LIST
    # =========================
    def get_printers(self):
        printers = []
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        for p in win32print.EnumPrinters(flags):
            printers.append(p[2])
        return printers

    def test_connection(self):
        printer_name = self.printer_box.currentText()
        if not printer_name:
            QMessageBox.critical(self, "Error", "Pilih printer dulu")
            return

        is_ready, reason = self.is_printer_ready(printer_name)
        if is_ready:
            QMessageBox.information(self, "Status", f"{printer_name} terhubung dan siap digunakan")
        else:
            QMessageBox.warning(self, "Status", f"Printer tidak siap:\n{reason}")

    def is_printer_ready(self, printer_name):
        try:
            handle = win32print.OpenPrinter(printer_name)
            try:
                printer_info = win32print.GetPrinter(handle, 2)
            finally:
                win32print.ClosePrinter(handle)

            attributes = int(printer_info.get("Attributes", 0) or 0)
            status = int(printer_info.get("Status", 0) or 0)
            blocking_bits = [
                0x00000001, 0x00000002, 0x00000004, 0x00000008, 0x00000010,
                0x00000020, 0x00000040, 0x00000080, 0x00001000, 0x00100000,
                0x00400000,
            ]
            if attributes & 0x00000400:
                return False, "Printer sedang Work Offline di Windows."
            if any(status & bit for bit in blocking_bits):
                return False, f"Status printer Windows belum ready ({status})."
            return True, "Printer siap."
        except Exception as e:
            return False, f"Windows tidak bisa membuka printer: {e}"

    # =========================
    # PDF PREVIEW & PAGINATION
    # =========================
    def preview_pdf(self, filepath, page_num=0):
        try:
            doc = fitz.open(filepath)
            self.total_pages = len(doc)
            self.current_page = page_num
 
            if hasattr(self, "page_indices") and self.page_indices:
                if page_num in self.page_indices:
                    self.current_page_idx = self.page_indices.index(page_num)
                else:
                    self.current_page_idx = 0
            else:
                self.page_indices = list(range(0, self.total_pages))
                self.current_page_idx = page_num
 
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
 
            fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(350, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
 
            self.preview_label.setPixmap(pixmap)
 
            # Update Label sesuai mode (Semua halaman atau Range tertentu)
            if not self.page_entry.text():
                self.page_label.setText(f"Page: {page_num+1}/{self.total_pages}")
            else:
                total_selected = len(self.page_indices)
                self.page_label.setText(f"Page: {page_num+1} ({total_selected} halaman terpilih)")
                    
            self.update_nav_buttons()

        except Exception as e:
            print(f"Error loading PDF preview: {e}")

    def update_nav_buttons(self):
        if not self.current_file or not hasattr(self, "page_indices") or not self.page_indices:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return
 
        self.prev_btn.setEnabled(self.current_page_idx > 0)
        self.next_btn.setEnabled(self.current_page_idx < len(self.page_indices) - 1)
 
    def next_page(self):
        if self.current_file and hasattr(self, "page_indices") and self.page_indices and self.current_page_idx < len(self.page_indices) - 1:
            self.current_page_idx += 1
            self.current_page = self.page_indices[self.current_page_idx]
            self.preview_pdf(self.current_file, self.current_page)
 
    def prev_page(self):
        if self.current_file and hasattr(self, "page_indices") and self.page_indices and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.current_page = self.page_indices[self.current_page_idx]
            self.preview_pdf(self.current_file, self.current_page)

    def on_page_input(self):
        if not self.current_file:
            return
 
        text = self.page_entry.text().strip()
        
        # Jika user menghapus input teks, kembalikan ke full range
        if not text:
            self.page_indices = list(range(0, self.total_pages))
            self.page_start = 0
            self.page_end = self.total_pages - 1 if self.total_pages > 0 else 0
            self.current_page = 0
            self.current_page_idx = 0
            self.preview_pdf(self.current_file, self.current_page)
            self.push_state()
            return
 
        try:
            import re
            normalized = text.lower()
            selected = []
            max_index = self.total_pages - 1
            
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
            
            self.page_indices = list(dict.fromkeys(selected))
            if not self.page_indices:
                self.page_indices = list(range(0, self.total_pages))
            
            self.page_start = min(self.page_indices)
            self.page_end = max(self.page_indices)
            
            # Langsung lompat ke halaman awal dari range yang diketik
            self.current_page_idx = 0
            self.current_page = self.page_indices[0]
            self.preview_pdf(self.current_file, self.current_page)
            self.push_state()
 
        except ValueError:
            QMessageBox.warning(self, "Error", "Format halaman salah. Contoh: 1, 3, 5 atau 1-3, 5")
            self.page_entry.clear()

    def on_copies_input(self):
        text = self.copies_entry.text().strip()
        if text.isdigit():
            self.remote_copies = max(1, int(text))
            self.push_state()
        else:
            self.copies_entry.setText(str(self.remote_copies))

    def on_printer_changed(self):
        self.push_state()

    def on_color_changed(self):
        self.remote_color_mode = self.color_box.currentText()
        self.push_state()

    def push_state(self):
        if not self.current_file or not self.active_user_id:
            return
        import os
        nama_file = os.path.basename(self.current_file)
        payload = {
            "user_id": self.active_user_id,
            "nama_file": nama_file,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "page_indices": self.page_indices,
            "printer_name": self.printer_box.currentText(),
            "color_mode": self.color_box.currentText(),
            "copies": getattr(self, "remote_copies", 1),
            "pages": self.page_entry.text().strip() or f"{self.page_start+1}-{self.page_end+1}"
        }
        try:
            requests.post("http://127.0.0.1:5000/update_state", json=payload, timeout=1)
        except Exception as e:
            print("Error pushing state to server:", e)

    # =========================
    # GET DATA & STATE FROM SERVER (PER-USER)
    # =========================
    def poll_data(self):
        if not self.active_user_id:
            return

        # 1. CEK FILE BARU untuk user aktif
        try:
            res = requests.get(f"http://127.0.0.1:5000/data_json?user_id={self.active_user_id}", timeout=1)
            if res.status_code == 200:
                data = res.json()
                if data and data.get("id") != self.last_id:
                    self.last_id = data["id"]
                    self.show_file(data)
        except Exception:
            pass

        # 2. CEK PERINTAH REMOTE DARI HP untuk user aktif
        try:
            res_state = requests.get(f"http://127.0.0.1:5000/get_state?user_id={self.active_user_id}", timeout=1)
            if res_state.status_code == 200:
                state = res_state.json()
                
                # Jika ada perintah baru dan nama filenya sama dengan yang sedang dibuka di PC
                if state["command_id"] != self.last_command_id and self.current_file and state["nama_file"] in self.current_file:
                    self.last_command_id = state["command_id"]

                    printer_from_mobile = state.get("printer_name", "")
                    if printer_from_mobile:
                        index = self.printer_box.findText(printer_from_mobile)
                        if index >= 0 and index != self.printer_box.currentIndex():
                            self.printer_box.blockSignals(True)
                            self.printer_box.setCurrentIndex(index)
                            self.printer_box.blockSignals(False)

                    self.remote_color_mode = state.get("color_mode", self.remote_color_mode)
                    color_index = self.color_box.findText(self.remote_color_mode)
                    if color_index >= 0 and color_index != self.color_box.currentIndex():
                        self.color_box.blockSignals(True)
                        self.color_box.setCurrentIndex(color_index)
                        self.color_box.blockSignals(False)

                    self.remote_copies = int(state.get("copies", self.remote_copies) or 1)
                    
                    self.copies_entry.blockSignals(True)
                    self.copies_entry.setText(str(self.remote_copies))
                    self.copies_entry.blockSignals(False)
                    
                    # Sinkronisasi Perubahan Halaman
                    state_indices = state.get("page_indices", [])
                    if not state_indices:
                        state_indices = list(range(state["page_start"], state["page_end"] + 1))
 
                    if (self.page_start != state["page_start"] or 
                        self.page_end != state["page_end"] or 
                        getattr(self, "page_indices", []) != state_indices):
                        
                        self.page_start = state["page_start"]
                        self.page_end = state["page_end"]
                        self.page_indices = state_indices
                        
                        if getattr(self, "current_page", 0) in self.page_indices:
                            self.current_page_idx = self.page_indices.index(self.current_page)
                        else:
                            self.current_page_idx = 0
                            self.current_page = self.page_indices[0] if self.page_indices else 0
                        
                        # Update teks di UI Desktop layaknya diketik manual
                        self.page_entry.blockSignals(True)
                        if len(self.page_indices) == self.total_pages and self.page_indices == list(range(0, self.total_pages)):
                            self.page_entry.setText("")
                        else:
                            is_contiguous = True
                            for idx in range(1, len(self.page_indices)):
                                if self.page_indices[idx] != self.page_indices[idx - 1] + 1:
                                    is_contiguous = False
                                    break
                            
                            if is_contiguous:
                                if len(self.page_indices) == 1:
                                    self.page_entry.setText(f"{self.page_indices[0] + 1}")
                                else:
                                    self.page_entry.setText(f"{self.page_indices[0] + 1}-{self.page_indices[-1] + 1}")
                            else:
                                self.page_entry.setText(",".join(str(idx + 1) for idx in self.page_indices))
                        self.page_entry.blockSignals(False)
                        
                        self.preview_pdf(self.current_file, self.current_page)
                    
                    # Jika HP menekan tombol Print
                    if state["execute_print"]:
                        self.print_file(command_id=state["command_id"])
                        
        except Exception:
            pass

    def show_file(self, data):
        filepath = os.path.join(BASE_DIR, "uploads", data['nama_file'])
        self.current_file = filepath
        self.current_data = data

        # Reset parameter
        self.info_label.setText("Memuat data...")
        self.page_entry.clear()
        self.copies_entry.setText(str(self.remote_copies))

        if data.get("jenis_file") == "pdf":
            # Set end page default ke total halaman dari get_file_info (di-pass dari JSON)
            total = int(data.get("jumlah_halaman", 0))
            self.page_start = 0
            self.page_end = total - 1 if total > 0 else 0
            self.page_indices = list(range(0, total))
            self.current_page_idx = 0
            self.preview_pdf(filepath, 0)
        else:
            self.page_indices = []
            self.current_page_idx = 0
            self.update_nav_buttons()

        self.status_label.setText("File Diterima")
        self.append_operator_note(f"File diterima: {data['nama_file']}")

        info_html = (
            f"<b>Nama:</b> {data['nama_file']}<br>"
            f"<b>Ukuran:</b> {data['ukuran_file_kb']} KB<br>"
            f"<b>Halaman:</b> {data['jumlah_halaman']}<br>"
            f"<b>Kertas:</b> {data['ukuran_kertas']}<br>"
            f"<b>Jenis:</b> {str(data['jenis_file']).upper()}<br>"
            f"<b>Waktu:</b> {data['waktu_upload']}"
        )
        self.info_label.setText(info_html)

    def reset_file(self):
        try:
            payload = {}
            if self.active_user_id:
                payload["user_id"] = self.active_user_id
            requests.post("http://127.0.0.1:5000/reset_state", json=payload, timeout=1)
        except Exception as e:
            print("Error resetting remote state:", e)
        self.current_file = None
        self.current_data = None
        self.page_start = 0
        self.page_end = 0
        self.page_indices = []
        self.current_page_idx = 0
        self.preview_label.clear()
        self.info_label.setText("Belum ada file masuk")
        self.status_label.setText("Menunggu File...")
        self.page_label.setText("Page: 0/0")
        self.page_entry.clear()
        self.copies_entry.clear()
        self.color_box.blockSignals(True)
        self.color_box.setCurrentIndex(0)
        self.color_box.blockSignals(False)
        self.update_nav_buttons()
        self.append_operator_note("File dihapus dari panel operator.")

    def append_operator_note(self, message):
        if hasattr(self, "chat_log_text"):
            self.chat_log_text.append(f"<span style='color:#F59E0B'>[Operator]</span> {message}")

    def poll_chat_log(self):
        if not hasattr(self, "chat_log_text") or not self.active_user_id:
            return
        try:
            res = requests.get(f"http://127.0.0.1:5000/chat_log?user_id={self.active_user_id}", timeout=1)
            if res.status_code != 200:
                return
            data = res.json()
            messages = data.get("messages", [])
            bot_typing = data.get("bot_typing", False)
            user_name = data.get("user_name", self.active_user_id)
            
            # Check if there is any update
            if len(messages) == self.last_chat_count and bot_typing == getattr(self, "last_bot_typing", False):
                return
                
            self.last_chat_count = len(messages)
            self.last_bot_typing = bot_typing
            
            html_content = """
            <html>
            <head>
            <style>
                body {
                    background-color: #12363B;
                    color: #FFF7E8;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 8px;
                    margin: 0;
                }
                .chat-container {
                    display: flex;
                    flex-direction: column;
                }
            </style>
            </head>
            <body>
            <div class="chat-container">
            """
            
            for item in messages:
                sender = item.get("sender", "")
                text = str(item.get("message", "")).replace("\n", "<br>").replace("\\n", "<br>")
                time_str = item.get("time", "")
                if time_str:
                    parts = time_str.split(" ")
                    if len(parts) > 1:
                        time_str = parts[1]
                
                if sender == "system":
                    html_content += f"""
                    <div style="text-align: center; margin: 8px 0; font-size: 11px; font-style: italic; color: #8A9A96;">
                        {text}
                    </div>
                    """
                elif sender == "user":
                    html_content += f"""
                    <table width="100%" style="margin-bottom: 6px;">
                        <tr>
                            <td width="85%" style="background-color: #E2ECE9; border-radius: 12px; padding: 10px; color: #172E32;">
                                <div style="font-weight: bold; font-size: 11px; color: #215B63; margin-bottom: 4px;">
                                    {user_name} <span style="font-size: 9px; color: #8A9A96; float: right; font-weight: normal;">{time_str}</span>
                                </div>
                                <div style="font-size: 12px;">{text}</div>
                            </td>
                            <td width="15%"></td>
                        </tr>
                    </table>
                    """
                else:
                    html_content += f"""
                    <table width="100%" style="margin-bottom: 6px;">
                        <tr>
                            <td width="15%"></td>
                            <td width="85%" style="background-color: #215B63; border-radius: 12px; padding: 10px; color: #FFFFFF; border: 1px solid #CDAA7D;">
                                <div style="font-weight: bold; font-size: 11px; color: #F59E0B; margin-bottom: 4px;">
                                    Bot (Anda) <span style="font-size: 9px; color: #A4C5BC; float: right; font-weight: normal;">{time_str}</span>
                                </div>
                                <div style="font-size: 12px;">{text}</div>
                            </td>
                        </tr>
                    </table>
                    """
            
            if bot_typing:
                html_content += """
                <table width="100%" style="margin-bottom: 6px;">
                    <tr>
                        <td width="15%"></td>
                        <td width="85%" style="background-color: #1a4248; border-radius: 12px; padding: 10px; color: #FFF7E8; border: 1px dashed #CDAA7D;">
                            <div style="font-size: 12px; font-style: italic; color: #F59E0B;">
                                <span style="font-weight: bold;">Bot</span> sedang mengetik...
                            </div>
                        </td>
                    </tr>
                </table>
                """
            
            html_content += """
            </div>
            </body>
            </html>
            """
            
            self.chat_log_text.setHtml(html_content)
            
            # Scroll to bottom
            scrollbar = self.chat_log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print("Error polling chat log:", e)

    # =========================
    # PRINTING
    # =========================
    def test_print(self):
        printer_name = self.printer_box.currentText()
        if not printer_name:
            QMessageBox.critical(self, "Error", "Pilih printer dulu")
            return
        is_ready, reason = self.is_printer_ready(printer_name)
        if not is_ready:
            QMessageBox.warning(self, "Error", f"Printer tidak siap:\n{reason}")
            return

        try:
            file_path = "test_print.txt"
            with open(file_path, "w") as f:
                f.write("Printer terhubung dengan baik\n\nTest berhasil.")

            win32print.SetDefaultPrinter(printer_name)
            win32api.ShellExecute(0, "print", file_path, None, ".", 0)
            QMessageBox.information(self, "Success", "Test print berhasil")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # =========================
    # PRINTING (DIRECT PRINT)
    # =========================
    def notify_print_finished(self, status, message, printer_name, command_id=None):
        try:
            payload = {
                "status": status,
                "message": message,
                "printer_name": printer_name,
                "command_id": command_id or self.last_command_id,
            }
            if self.active_user_id:
                payload["user_id"] = self.active_user_id
            requests.post(
                "http://127.0.0.1:5000/print_finished",
                json=payload,
                timeout=1,
            )
        except Exception as e:
            print(f"Gagal kirim status print: {e}")

    def print_file(self, command_id=None):
        import os
        
        if not self.current_file:
            QMessageBox.critical(self, "Error", "Tidak ada file")
            self.notify_print_finished("error", "Tidak ada file", self.printer_box.currentText(), command_id)
            return

        printer_name = self.printer_box.currentText()
        if not printer_name:
            QMessageBox.critical(self, "Error", "Pilih printer")
            self.notify_print_finished("error", "Printer belum dipilih", printer_name, command_id)
            return
        is_ready, reason = self.is_printer_ready(printer_name)
        if not is_ready:
            QMessageBox.warning(self, "Error", f"Printer tidak siap:\n{reason}")
            self.notify_print_finished("error", f"Printer tidak siap: {reason}", printer_name, command_id)
            return

        abs_filepath = os.path.abspath(self.current_file)
        if not os.path.exists(abs_filepath):
            QMessageBox.critical(self, "Error", f"File fisik tidak ditemukan:\n{abs_filepath}")
            self.notify_print_finished("error", "File fisik tidak ditemukan", printer_name, command_id)
            return

        try:
            # === JIKA FILE ADALAH PDF ===
            if self.current_data.get("jenis_file") == "pdf":
                
                # Inisialisasi Direct Printer dengan Resolusi Tinggi
                printer = QPrinter(QPrinter.HighResolution)
                printer.setPrinterName(printer_name)
                printer.setCopyCount(max(1, self.remote_copies))

                if str(self.remote_color_mode).lower() == "color":
                    printer.setColorMode(QPrinter.Color)
                else:
                    printer.setColorMode(QPrinter.GrayScale)
                
                # ---------------------------------------------------------
                # DETEKSI DAN ATUR UKURAN KERTAS SESUAI INFO DARI SERVER
                # ---------------------------------------------------------
                kertas = self.current_data.get("ukuran_kertas", "")
                
                if kertas == "Legal":
                    printer.setPageSize(QPrinter.Legal)
                elif kertas == "Letter":
                    printer.setPageSize(QPrinter.Letter)
                elif kertas == "A4":
                    printer.setPageSize(QPrinter.A4)
                # ---------------------------------------------------------

                # Buka dokumen
                doc = fitz.open(abs_filepath)
                
                # Gunakan QPainter untuk menggambar halaman ke printer
                painter = QPainter()
                painter.begin(printer)
                
                pages_to_print = getattr(self, "page_indices", [])
                if not pages_to_print:
                    pages_to_print = list(range(self.page_start, self.page_end + 1))
 
                for idx, i in enumerate(pages_to_print):
                    page = doc.load_page(i)
                    
                    # Zoom/Matrix tinggi agar hasil cetak teks tidak pecah/blur
                    zoom = 4
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    
                    fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
                    
                    # viewport() sekarang sudah menyesuaikan dengan ukuran kertas yang diset di atas (misal Legal)
                    rect = painter.viewport()
                    size = qimg.size()
                    size.scale(rect.size(), Qt.KeepAspectRatio)
                    
                    painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
                    painter.setWindow(qimg.rect())
                    
                    painter.drawImage(0, 0, qimg)
                    
                    if idx < len(pages_to_print) - 1:
                        printer.newPage()
                        
                painter.end()
                doc.close()
                
                pages_desc = ",".join(str(x + 1) for x in pages_to_print)
                QMessageBox.information(self, "Success", f"Halaman {pages_desc} berhasil dikirim ke printer.")
                self.notify_print_finished("done", "File berhasil dikirim ke printer", printer_name, command_id)

            # === JIKA BUKAN PDF (Misal docx) ===
            else:
                win32print.SetDefaultPrinter(printer_name)
                win32api.ShellExecute(0, "printto", abs_filepath, f'"{printer_name}"', ".", 0)
                QMessageBox.information(self, "Success", "Perintah print sedang diproses oleh sistem.")
                self.notify_print_finished("done", "File berhasil dikirim ke printer", printer_name, command_id)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mencetak:\n{str(e)}")
            self.notify_print_finished("error", f"Gagal mencetak: {e}", printer_name, command_id)
            
# =========================
# RUN
# =========================
def run_gui():
    import sys
    # Pastikan QApplication hanya dibuat jika belum ada
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
        
    app.setStyle("Fusion") 
    window = PrintServerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()
