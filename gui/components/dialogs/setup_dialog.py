"""
Setup Dialog for AHS-MediaDL.

Appears on first launch if FFmpeg or yt-dlp binaries are missing.
Downloads and installs tools with live progress, or allows manual local import.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFileDialog, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from managers.binary_manager import BinaryManager, BinaryDownloaderWorker
from utils.helpers import resource_path, get_current_theme_color, get_colored_icon
from utils.locales import tr
from utils.logger import logger


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setWindowTitle(tr("setup_title", "Setting up Download Tools"))
        self.setFixedSize(520, 310)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.initUI()
        self.start_download()

    def initUI(self):
        is_dark = get_current_theme_color() == "#f1f5f9"
        bg_color = "#0b0f19" if is_dark else "#f8fafc"
        bg_card = "#131926" if is_dark else "#ffffff"
        border_color = "#1e293b" if is_dark else "#e2e8f0"
        text_color = "#f1f5f9" if is_dark else "#0f172a"
        sub_text = "#94a3b8" if is_dark else "#64748b"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QFrame#Card {{
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel {{
                color: {text_color};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {'#1e293b' if is_dark else '#e2e8f0'};
                text-align: center;
                color: {text_color};
                font-weight: bold;
                font-size: 11px;
                height: 18px;
            }}
            QProgressBar::chunk {{
                background-color: #3b82f6;
                border-radius: 5px;
            }}
            QPushButton {{
                padding: 7px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                cursor: pointer;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self)
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # Header with Logo & Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            logo_lbl = QLabel(self)
            pix = QPixmap(icon_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            header_layout.addWidget(logo_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        self.lbl_title = QLabel(tr("setup_title", "Setting up Download Tools"), self)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_vbox.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(tr("setup_desc", "Configuring essential tools for video and audio downloading..."), self)
        self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {sub_text};")
        self.lbl_desc.setWordWrap(True)
        title_vbox.addWidget(self.lbl_desc)
        header_layout.addLayout(title_vbox, 1)

        card_layout.addLayout(header_layout)

        # Progress bar
        self.p_bar = QProgressBar(self)
        self.p_bar.setRange(0, 100)
        self.p_bar.setValue(0)
        card_layout.addWidget(self.p_bar)

        # Status text
        self.lbl_status = QLabel("⏳ Checking missing tools...", self)
        self.lbl_status.setStyleSheet("font-size: 11px;")
        card_layout.addWidget(self.lbl_status)

        # Action Buttons Layout (Hidden unless error or manual browse needed)
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)

        self.btn_retry = QPushButton(tr("setup_retry", "Retry"), self)
        self.btn_retry.setStyleSheet("background-color: #3b82f6; color: white; border: none;")
        self.btn_retry.clicked.connect(self.start_download)
        self.btn_retry.hide()
        self.btn_layout.addWidget(self.btn_retry)

        self.btn_browse = QPushButton(tr("setup_browse", "Browse Local Folder..."), self)
        self.btn_browse.setStyleSheet(f"background-color: {'#1e293b' if is_dark else '#e2e8f0'}; color: {text_color}; border: none;")
        self.btn_browse.clicked.connect(self.browse_folder)
        self.btn_browse.hide()
        self.btn_layout.addWidget(self.btn_browse)

        self.btn_cancel = QPushButton(tr("btn_cancel", "Cancel"), self)
        self.btn_cancel.setStyleSheet("background-color: transparent; color: #ef4444; border: 1px solid #ef4444;")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.btn_cancel)

        card_layout.addLayout(self.btn_layout)
        main_layout.addWidget(card)

    def start_download(self):
        missing = BinaryManager.get_missing_tools()
        needs_ytdlp = "yt-dlp" in missing
        needs_ffmpeg = "ffmpeg" in missing or "ffprobe" in missing

        if not needs_ytdlp and not needs_ffmpeg:
            self.lbl_status.setText(tr("setup_complete", "✅ Setup complete!"))
            self.p_bar.setValue(100)
            QTimer.singleShot(500, self.accept)
            return

        self.btn_retry.hide()
        self.btn_browse.hide()
        self.lbl_status.setText("⏳ Connecting to server...")
        self.lbl_status.setStyleSheet("font-size: 11px;")
        self.p_bar.setValue(5)

        self.worker = BinaryDownloaderWorker(download_yt_dlp=needs_ytdlp, download_ffmpeg=needs_ffmpeg, parent=self)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, pct: int, status_str: str):
        self.p_bar.setValue(pct)
        self.lbl_status.setText(status_str)

    def on_finished(self, success: bool, message: str):
        if success:
            self.p_bar.setValue(100)
            self.lbl_status.setText(tr("setup_complete", "✅ Setup completed successfully! Starting application..."))
            self.lbl_status.setStyleSheet("font-size: 11px; color: #10b981; font-weight: bold;")
            QTimer.singleShot(700, self.accept)
        else:
            self.lbl_status.setText(tr("setup_failed", "❌ Failed to download tools. Check internet connection."))
            self.lbl_status.setStyleSheet("font-size: 11px; color: #ef4444; font-weight: bold;")
            self.btn_retry.show()
            self.btn_browse.show()

    def browse_folder(self):
        """Allows selecting a local folder that already contains ffmpeg.exe or yt-dlp.exe."""
        folder = QFileDialog.getExistingDirectory(self, tr("setup_browse_desc", "Select folder containing tools"))
        if not folder:
            return

        success, copied = BinaryManager.import_binaries_from_folder(folder)
        if success:
            QMessageBox.information(
                self,
                tr("setup_title"),
                tr("setup_browse_success").format(", ".join(copied))
            )
            # Check if all tools are now available
            if BinaryManager.are_all_tools_available():
                self.accept()
            else:
                self.start_download()
        else:
            QMessageBox.warning(
                self,
                tr("setup_title"),
                tr("setup_browse_none")
            )

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        event.accept()
