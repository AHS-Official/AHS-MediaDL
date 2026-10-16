"""
download_dialogs.py
───────────────────
QualitySelectionDialog  — dialog اختيار جودة تنزيل الفيديو (من نتائج البحث)
PlaylistSelectionDialog — dialog اختيار مقاطع البلايليست للتنزيل
"""
import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QWidget,
                             QFrame, QScrollArea, QProgressBar, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QThreadPool
from PyQt6.QtGui import QPixmap
from gui.components.media_panels import SingleVideoPanel, PlaylistPanel
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.locales import tr


class QualitySelectionDialog(QDialog):

    def __init__(self, main_app, url, placeholder_title="", placeholder_pixmap=None, extra_info=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.url = url
        self.placeholder_title = placeholder_title
        self.placeholder_pixmap = placeholder_pixmap
        self.extra_info = extra_info or {}
        self.clean_title = "video"
        self.duration_str = "00:00"
        self.image_data = b''
        self.loaded_pixmap = None
        self.settings_file = main_app.settings_file

        self.setObjectName("QualitySelectionDialog")
        self.setWindowTitle(tr("search_download_opts", "Video Download Options"))
        self.setMinimumSize(740, 520)
        self.resize(760, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.initUI()
        self.start_inspection()
        self.center_on_parent()

    def initUI(self):
        is_dark = get_current_theme_color() == "#f1f5f9"
        bg_card = "#0d1527" if is_dark else "#ffffff"
        border_color = "#1e293b" if is_dark else "#e2e8f0"
        text_color = "#f1f5f9" if is_dark else "#0f172a"

        self.setLayoutDirection(self.main_app.layoutDirection())

        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {bg_card};
            }} 
            QPushButton {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 16px;
                color: {text_color};
                font-weight: bold;
                font-size: 12px;
            }} 
            QPushButton:hover {{ 
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #3b82f6;
            }} 
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Loading Widget
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setContentsMargins(20, 60, 20, 60)
        loading_layout.setSpacing(12)
        self.loading_lbl = QLabel(tr("search_loading_formats", "Fetching formats..."))
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setStyleSheet(f"color: {text_color}; font-size: 13px; font-weight: bold;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedSize(200, 8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {border_color};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: #3b82f6;
                border-radius: 4px;
            }}
        """)
        loading_layout.addWidget(self.loading_lbl)
        loading_layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.loading_widget)

        # Error Widget
        self.error_widget = QWidget()
        self.error_widget.hide()
        error_layout = QVBoxLayout(self.error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 60, 20, 60)
        error_layout.setSpacing(12)
        self.error_lbl = QLabel()
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
        error_layout.addWidget(self.error_lbl)
        self.btn_err_close = QPushButton(tr("btn_cancel", "Close"))
        self.btn_err_close.clicked.connect(self.reject)
        error_layout.addWidget(self.btn_err_close)
        self.layout.addWidget(self.error_widget)

        # Scroll Area for Content
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {'#334155' if is_dark else '#cbd5e1'};
                min-height: 28px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {'#64748b' if is_dark else '#94a3b8'};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # Content Widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # ── Shared Single-Video Panel ──────────────────────────────────────
        self.preview_widget = SingleVideoPanel(self.main_app, is_dialog=True)
        self.preview_widget.cancel_requested.connect(self.reject)
        self.preview_widget.download_requested.connect(self.start_download)
        self.content_layout.addWidget(self.preview_widget)

        # Aliases — للتوافق مع الكود في start_download()
        self.thumb_label = self.preview_widget.thumb_label
        self.title_label = self.preview_widget.title_label
        self.duration_label = self.preview_widget.duration_label
        self.format_combo = self.preview_widget.format_combo
        self.sub_cb = self.preview_widget.sub_cb
        self.sub_combo = self.preview_widget.sub_combo
        self.btn_cancel = self.preview_widget.cancel_btn
        self.btn_dl = self.preview_widget.download_btn

        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)

        # عرض الكارت فوراً بالبيانات المتوفرة وحالة التحميل المسبقة
        if self.placeholder_title or (self.placeholder_pixmap and not self.placeholder_pixmap.isNull()):
            self.preview_widget.show_placeholder(self.placeholder_title, self.placeholder_pixmap, self.extra_info)
            self.loading_widget.hide()
            self.scroll_area.show()
        else:
            self.scroll_area.hide()
            self.loading_widget.show()

    def start_inspection(self):
        from services.yt_dlp_service import InspectWorker
        self.inspect_worker = InspectWorker(self.url)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.playlist_signal.connect(self.on_playlist_detected)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.thumbnail_signal.connect(self.on_inspect_thumbnail_loaded)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    def on_playlist_detected(self, title, image_data, entries):
        if entries and len(entries) > 0:
            first_url = entries[0].get('url')
            if first_url and first_url != self.url:
                self.url = first_url
                self.start_inspection()
                return
        self.on_inspect_error(tr("playlist_detected_in_single", "This link is a playlist. Please use the playlist downloader."))

    def on_inspect_success(self, title, duration_secs, image_data, format_list, subtitles_dict=None, extra_info=None):
        merged_extra = dict(self.extra_info)
        if extra_info:
            merged_extra.update(extra_info)
        self.preview_widget.populate(title, duration_secs, image_data, format_list, subtitles_dict, merged_extra)
        self.clean_title = self.preview_widget.clean_title
        self.duration_str = self.preview_widget.duration_str
        self.loaded_pixmap = self.preview_widget.thumb_label._pixmap if hasattr(self.preview_widget.thumb_label, '_pixmap') else None
        self.loading_widget.hide()
        self.scroll_area.show()
        self.center_on_parent()

    def on_inspect_thumbnail_loaded(self, data):
        if data:
            self.image_data = data
            self.loaded_pixmap = QPixmap()
            if self.loaded_pixmap.loadFromData(data):
                self.thumb_label.setPixmap(self.loaded_pixmap)
                self.thumb_label._pixmap = self.loaded_pixmap
                self.thumb_label.show()
                self.preview_widget.hero_card.show()

    def on_inspect_error(self, error_msg):
        self.loading_widget.hide()
        self.scroll_area.hide()
        self.error_lbl.setText(error_msg)
        self.error_widget.show()
        self.center_on_parent()

    def center_on_parent(self):
        top_level = self.window()
        if self.parentWidget():
            top_level = self.parentWidget().window()
        if top_level:
            parent_geo = top_level.geometry()
            dialog_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)

    def reject(self):
        worker = getattr(self, 'inspect_worker', None)
        if worker is not None:
            try:
                if worker.isRunning():
                    for sig_name in ['result_signal', 'playlist_signal', 'error_signal', 'thumbnail_signal']:
                        sig = getattr(worker, sig_name, None)
                        if sig:
                            try:
                                sig.disconnect()
                            except Exception:
                                pass
            except (RuntimeError, ReferenceError):
                pass
            except Exception:
                pass
            self.inspect_worker = None
        super().reject()

    # toggle_sub_combo و auto_select_saved_format انتقلا إلى SingleVideoPanel

    def start_download(self):
        self.btn_dl.setEnabled(False)
        from gui.components.cards import DownloadCard
        from core.downloader import DownloadWorker
        from managers.settings_manager import SettingsManager
        mgr = SettingsManager()
        video_container = mgr.get("video_container", "mp4")
        audio_container = mgr.get("audio_container", "mp3")
        download_path_type = mgr.get("download_path_type", "always_ask")
        custom_path = mgr.get("custom_path", "")
        if download_path_type == "downloads":
            target_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        elif download_path_type == "custom" and custom_path:
            try:
                os.makedirs(custom_path, exist_ok=True)
                target_dir = custom_path
            except OSError as e:
                QMessageBox.warning(self, tr("warning", "Warning"), f"Could not create custom folder:\n{e}\n\nFalling back to manual selection.")
                target_dir = self.main_app.last_save_dir
                download_path_type = "always_ask"
        else:
            target_dir = self.main_app.last_save_dir
        format_code = self.format_combo.currentData()
        if not format_code:
            self.btn_dl.setEnabled(True)
            return
        if format_code.startswith("audio:"):
            codec = audio_container
            filter_str = f"Audio Files (*.{codec})"
        else:
            all_filters = {
                "mp4": "MP4 Video (*.mp4)",
                "mkv": "MKV Video (*.mkv)",
                "mov": "MOV Video (*.mov)",
                "webm": "WebM Video (*.webm)"
            }
            pref_filter = all_filters.get(video_container, "MP4 Video (*.mp4)")
            other_filters = [f for k, f in all_filters.items() if k != video_container]
            filter_str = f"{pref_filter};;{';;'.join(other_filters)}"
        if download_path_type == "always_ask":
            save_path, selected_filter = QFileDialog.getSaveFileName(self, tr("dialog_save_media_as", "Save Media As"), os.path.join(target_dir, self.clean_title), filter_str)
            if not save_path:
                self.btn_dl.setEnabled(True)
                return
            if format_code.startswith("audio:"):
                if not save_path.lower().endswith(f".{codec}"):
                    save_path += f".{codec}"
            else:
                for ext in ["mp4", "mkv", "mov", "webm"]:
                    if ext in selected_filter.lower():
                        if not save_path.lower().endswith(f".{ext}"):
                            save_path += f".{ext}"
                        break
        else:
            ext = f".{codec}" if format_code.startswith("audio:") else f".{video_container}"
            save_path = os.path.join(target_dir, f"{self.clean_title}{ext}")
            counter = 1
            base, ext_orig = os.path.splitext(save_path)
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext_orig}"
                counter += 1
        self.main_app.last_save_dir = os.path.dirname(save_path)
        self.main_app.save_settings(self.main_app.last_save_dir)
        sub_lang = None
        if self.sub_cb.isVisible() and self.sub_cb.isChecked():
            sub_lang = self.sub_combo.currentData()
        thumb_pix = self.loaded_pixmap if self.loaded_pixmap else None
        new_card = DownloadCard(self.title_label.toolTip(), thumb_pix, save_path)
        new_card.url = self.url
        new_card.format_code = format_code
        new_card.sub_lang = sub_lang
        new_card.is_playlist_sub = False
        new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
        new_card.duration = self.duration_str
        self.main_app.cards_layout.insertWidget(0, new_card)
        worker = DownloadWorker(self.url, format_code, save_path, sub_lang=sub_lang)
        worker.progress_signal.connect(new_card.update_progress)
        worker.status_signal.connect(new_card.update_status)
        worker.finished_signal.connect(new_card.set_save_path)
        new_card.set_worker(worker)
        new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=self.url, f=format_code, s=save_path, sb=sub_lang, app=self.main_app: app.download_manager.reload_download(c, u, f, s, sb))
        self.main_app.download_manager.add_worker(worker)
        new_card.update_status(tr("status_waiting_queue", "⏳ Waiting in queue..."))
        self.main_app.page_downloads.check_empty_state()
        self.main_app.download_manager.process_queue()
        self.accept()
class PlaylistSelectionDialog(QDialog):
    def __init__(self, main_app, url, placeholder_title="", placeholder_pixmap=None, extra_info=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.url = url
        self.placeholder_title = placeholder_title
        self.placeholder_pixmap = placeholder_pixmap
        self.extra_info = extra_info or {}
        self.settings_file = getattr(main_app, 'settings_file', '')

        self.pl_checkboxes = []
        self.loaded_pixmap = None

        self.setObjectName("PlaylistSelectionDialog")
        self.setWindowTitle(tr("search_playlist_opts", "Playlist Download Options"))
        self.setMinimumSize(740, 520)
        self.resize(760, 680)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.initUI()
        self.start_inspection()
        self.center_on_parent()

    def initUI(self):
        is_dark = get_current_theme_color() == "#f1f5f9"
        self.bg_color = "#0d1527" if is_dark else "#ffffff"
        self.bg_card  = "#0d1527" if is_dark else "#ffffff"
        self.border_color = "#1e293b" if is_dark else "#e2e8f0"
        self.text_color = "#f1f5f9" if is_dark else "#0f172a"

        self.setLayoutDirection(self.main_app.layoutDirection())
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.bg_color};
            }}
            QPushButton {{
                background-color: {self.bg_card};
                border: 1px solid {self.border_color};
                border-radius: 8px;
                padding: 8px 16px;
                color: {self.text_color};
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #3b82f6;
            }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Loading Widget
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.setContentsMargins(20, 60, 20, 60)
        loading_layout.setSpacing(12)
        self.loading_lbl = QLabel(tr("search_loading_playlist", "Fetching playlist items... please wait."))
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setStyleSheet(f"color: {self.text_color}; font-size: 13px; font-weight: bold;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedSize(200, 8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.border_color};
                border-radius: 4px; border: none;
            }}
            QProgressBar::chunk {{
                background-color: #3b82f6;
                border-radius: 4px;
            }}
        """)
        loading_layout.addWidget(self.loading_lbl)
        loading_layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.loading_widget)

        # Error Widget
        self.error_widget = QWidget()
        self.error_widget.hide()
        error_layout = QVBoxLayout(self.error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(20, 60, 20, 60)
        error_layout.setSpacing(12)
        self.error_lbl = QLabel()
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 12px;")
        error_layout.addWidget(self.error_lbl)
        self.btn_err_close = QPushButton(tr("btn_cancel", "Close"))
        self.btn_err_close.clicked.connect(self.reject)
        error_layout.addWidget(self.btn_err_close)
        self.layout.addWidget(self.error_widget)

        # Scroll Area for Content
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {'#334155' if is_dark else '#cbd5e1'};
                min-height: 28px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {'#64748b' if is_dark else '#94a3b8'};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # Content Widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # ── Shared Playlist Panel ──────────────────────────────────────
        self.playlist_widget = PlaylistPanel(self.main_app, is_dialog=True)
        self.playlist_widget.cancel_requested.connect(self.reject)
        self.playlist_widget.download_requested.connect(self.start_download)
        self.content_layout.addWidget(self.playlist_widget)

        # Aliases — للتوافق مع start_download()
        self.format_combo = self.playlist_widget.format_combo
        self.sub_cb       = self.playlist_widget.sub_cb
        self.btn_cancel   = self.playlist_widget.cancel_btn
        self.btn_dl       = self.playlist_widget.download_btn

        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)

        # عرض الكارت فوراً بالبيانات المتوفرة وحالة التحميل المسبقة
        if self.placeholder_title or (self.placeholder_pixmap and not self.placeholder_pixmap.isNull()):
            self.playlist_widget.show_placeholder(self.placeholder_title, self.placeholder_pixmap, extra_info=self.extra_info)
            self.loading_widget.hide()
            self.scroll_area.show()
        else:
            self.scroll_area.hide()
            self.loading_widget.show()

    def start_inspection(self):
        from services.yt_dlp_service import InspectWorker
        self.inspect_worker = InspectWorker(self.url)
        self.inspect_worker.playlist_signal.connect(self.on_inspect_success)
        self.inspect_worker.result_signal.connect(self.on_single_video_detected)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.thumbnail_signal.connect(self.on_inspect_thumbnail_loaded)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    def on_single_video_detected(self, title, duration_secs, image_data, format_list, subtitles_dict=None, extra_info=None):
        entries = [{
            'title': title,
            'duration': duration_secs,
            'url': self.url,
            'id': ''
        }]
        self.on_inspect_success(title, image_data, entries)

    def on_inspect_success(self, title, image_data, entries):
        if len(entries) >= 200:
            reply = QMessageBox.warning(
                self, 
                tr("warning", "Warning"), 
                f"This playlist contains {len(entries)} items.\nProcessing a playlist this large may impact performance or take a long time.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.reject()
                return

        # تفويض كل منطق التعبئة للـ PlaylistPanel — مكان واحد للتعديل
        self.playlist_widget.populate(title, image_data, entries)
        self.clean_title   = self.playlist_widget.clean_title
        self.loaded_pixmap = getattr(self.playlist_widget, 'loaded_pixmap', None)
        self.pl_checkboxes = self.playlist_widget.pl_checkboxes
        self.loading_widget.hide()
        self.scroll_area.show()
        self.center_on_parent()

    def on_inspect_thumbnail_loaded(self, data):
        if data:
            pix = QPixmap()
            if pix.loadFromData(data):
                self.loaded_pixmap = pix
                if self.playlist_widget:
                    self.playlist_widget.loaded_pixmap = pix

    def update_playlist_thumb(self, index, data):
        """delegate للـ PlaylistPanel."""
        self.playlist_widget.update_playlist_thumb(index, data)

    def toggle_select_all(self, checked):
        """delegate للـ PlaylistPanel."""
        self.playlist_widget.pl_select_all_cb.setChecked(checked)
        self.playlist_widget.toggle_all_playlist_items()

    def on_inspect_error(self, error_msg):
        self.loading_widget.hide()
        self.scroll_area.hide()
        self.error_lbl.setText(error_msg)
        self.error_widget.show()
        self.center_on_parent()

    def center_on_parent(self):
        top_level = self.window()
        if self.parentWidget():
            top_level = self.parentWidget().window()
        if top_level:
            parent_geo = top_level.geometry()
            dialog_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)

    def reject(self):
        worker = getattr(self, 'inspect_worker', None)
        if worker is not None:
            try:
                if worker.isRunning():
                    for sig_name in ['playlist_signal', 'result_signal', 'error_signal', 'thumbnail_signal']:
                        sig = getattr(worker, sig_name, None)
                        if sig:
                            try:
                                sig.disconnect()
                            except Exception:
                                pass
            except (RuntimeError, ReferenceError):
                pass
            except Exception:
                pass
            self.inspect_worker = None
        super().reject()

    def start_download(self):
        self.btn_dl.setEnabled(False)
        from gui.components.cards import DownloadCard
        from core.downloader import DownloadWorker
        from utils.helpers import clean_and_shorten_title
        from managers.settings_manager import SettingsManager
        mgr = SettingsManager()
        video_container = mgr.get("video_container", "mp4")
        audio_container = mgr.get("audio_container", "mp3")
        download_path_type = mgr.get("download_path_type", "always_ask")
        custom_path = mgr.get("custom_path", "")
        if download_path_type == "downloads":
            target_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        elif download_path_type == "custom" and custom_path:
            try:
                os.makedirs(custom_path, exist_ok=True)
                target_dir = custom_path
            except OSError as e:
                QMessageBox.warning(self, tr("warning", "Warning"), f"Could not create custom folder:\n{e}\n\nFalling back to manual selection.")
                target_dir = self.main_app.last_save_dir
                download_path_type = "always_ask"
        else:
            target_dir = self.main_app.last_save_dir
        format_code = self.format_combo.currentData()
        selected = [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, tr("warning", "Warning"), tr("select_at_least_one", "Please select at least one video to download."))
            self.btn_dl.setEnabled(True)
            return
        if download_path_type == "always_ask":
            save_dir = QFileDialog.getExistingDirectory(self, tr("dialog_select_playlist", "Select Folder for Playlist"), target_dir)
            if not save_dir:
                self.btn_dl.setEnabled(True)
                return
        else:
            save_dir = target_dir
        self.main_app.last_save_dir = save_dir
        self.main_app.save_settings(save_dir)
        is_audio = format_code.startswith("audio:")
        playlist_target_dir = save_dir if is_audio else os.path.join(save_dir, self.clean_title)
        if not is_audio and not os.path.exists(playlist_target_dir):
            try:
                os.makedirs(playlist_target_dir)
            except OSError as e:
                QMessageBox.critical(self, tr("error", "Error"), f"Failed to create playlist folder:\n{playlist_target_dir}\nError: {e}")
                self.btn_dl.setEnabled(True)
                return
        for entry in selected:
            vid_url = entry['url']
            clean_vid_title = clean_and_shorten_title(entry['title'])
            if is_audio:
                ext = f".{audio_container}"
                final_title = clean_vid_title
            else:
                ext = f".{video_container}"
                original_index = entry.get('original_index', 1)
                final_title = f"{original_index}. {clean_vid_title}"
            save_path = os.path.join(playlist_target_dir, f"{final_title}{ext}")
            counter = 1
            base, ext_orig = os.path.splitext(save_path)
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext_orig}"
                counter += 1
            thumb_pixmap = entry.get('thumb_pixmap')
            if not thumb_pixmap:
                if self.loaded_pixmap:
                    thumb_pixmap = self.loaded_pixmap
                else:
                    thumb_pixmap = None
            is_playlist_sub = self.sub_cb.isChecked()
            new_card = DownloadCard(final_title, thumb_pixmap, save_path)
            new_card.url = vid_url
            new_card.format_code = format_code
            if is_playlist_sub:
                from managers.settings_manager import SettingsManager
                mgr = SettingsManager()
                new_card.sub_lang = mgr.get("primary_sub_lang", "ar")
            else:
                new_card.sub_lang = None
            new_card.is_playlist_sub = is_playlist_sub
            new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
            new_card.duration = tr("playlist_item_duration")
            self.main_app.cards_layout.insertWidget(0, new_card)
            worker = DownloadWorker(vid_url, format_code, save_path, sub_lang=new_card.sub_lang, is_playlist_sub=is_playlist_sub)
            worker.progress_signal.connect(new_card.update_progress)
            worker.status_signal.connect(new_card.update_status)
            worker.finished_signal.connect(new_card.set_save_path)
            worker.sub_notification_signal.connect(self.main_app.handle_subtitle_notification)
            new_card.set_worker(worker)
            new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=vid_url, f=format_code, s=save_path, sb=new_card.sub_lang, ips=is_playlist_sub, app=self.main_app: app.download_manager.reload_download(c, u, f, s, sb, ips))
            self.main_app.download_manager.add_worker(worker)
            new_card.update_status(tr("status_waiting_queue", "⏳ Waiting in queue..."))
        self.main_app.page_downloads.check_empty_state()
        self.main_app.download_manager.process_queue()
        self.accept()
