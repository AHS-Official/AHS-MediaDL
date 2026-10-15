from utils.logger import logger
import os
import sys
import subprocess
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar, QCheckBox, QMenu
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QAction
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.locales import tr
from gui.components.common import ResponsiveImage, ElidedLabel

class DownloadCard(QFrame):

    def __init__(self, title, thumbnail_pixmap, save_path=""):
        super().__init__()
        self.save_path = save_path
        self.current_percent = 0
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumHeight(110)
        layout = QHBoxLayout(self)
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(120, 70)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if thumbnail_pixmap and not thumbnail_pixmap.isNull():
            self.has_real_thumbnail = True
            scaled_thumb = thumbnail_pixmap.scaled(120, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            self.thumb_label.setPixmap(scaled_thumb)
        else:
            self.has_real_thumbnail = False
            is_audio = False
            if save_path:
                ext = os.path.splitext(save_path)[1].lower()
                if ext in ['.mp3', '.m4a', '.opus', '.wav', '.flac']:
                    is_audio = True
            placeholder_file = "assets/icons/music.svg" if is_audio else "assets/icons/video.svg"
            placeholder_icon = get_colored_icon(placeholder_file, get_current_theme_color())
            self.thumb_label.setPixmap(placeholder_icon.pixmap(QSize(36, 36)))
            self.thumb_label.setStyleSheet("background-color: #111827; border-radius: 8px;")
        layout.addWidget(self.thumb_label)
        details_layout = QVBoxLayout()
        top_row_layout = QHBoxLayout()
        self.title_label = ElidedLabel(title) 
        self.title_label.setToolTip(title) 
        card_font = self.title_label.font()
        card_font.setBold(True)
        card_font.setPointSize(card_font.pointSize() + 1)
        self.title_label.setFont(card_font)
        top_row_layout.addWidget(self.title_label)
        top_row_layout.setStretch(0, 1)
        self.btn_pause = self.create_icon_button("assets/icons/pause.svg", tr("tooltip_pause", "Pause"))
        self.btn_cancel = self.create_icon_button("assets/icons/cancel.svg", tr("tooltip_cancel", "Cancel"))
        self.btn_reload = self.create_icon_button("assets/icons/restart.svg", tr("tooltip_reload", "Reload"))
        self.btn_open = self.create_icon_button("assets/icons/folder-open.svg", tr("tooltip_open_folder", "Open Folder"))
        self.btn_reload.hide()
        self.btn_open.hide()
        top_row_layout.addWidget(self.btn_pause)
        top_row_layout.addWidget(self.btn_cancel)
        top_row_layout.addWidget(self.btn_reload)
        top_row_layout.addWidget(self.btn_open)
        details_layout.addLayout(top_row_layout)
        self.p_bar = QProgressBar()
        self.p_bar.setMinimumHeight(8)
        self.p_bar.setMaximumHeight(8)
        self.p_bar.setTextVisible(False)
        self.p_bar.setValue(0)
        details_layout.addWidget(self.p_bar)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)
        self.status_icon_lbl = QLabel()
        self.status_icon_lbl.setFixedSize(16, 16)
        self.status_icon_lbl.hide()
        self.status_label = ElidedLabel(tr("status_waiting_queue", "Waiting in queue..."))
        status_font = self.status_label.font()
        status_font.setPointSize(status_font.pointSize() - 1)
        self.status_label.setFont(status_font)

        self.right_status_label = QLabel("")
        self.right_status_label.setFont(status_font)
        self.right_status_label.setStyleSheet("color: #9ca3af;")
        self.right_status_label.hide()

        status_layout.addWidget(self.status_icon_lbl)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.right_status_label)
        details_layout.addLayout(status_layout)
        layout.addLayout(details_layout)
        layout.setStretch(1, 1)
        self.btn_cancel.clicked.connect(self.action_cancel)
        self.btn_pause.clicked.connect(self.action_pause_resume)
        self.btn_open.clicked.connect(self.action_open_folder)

    def create_icon_button(self, icon_path, tooltip):
        btn = QPushButton()
        icon = get_colored_icon(icon_path, get_current_theme_color())
        btn.setIcon(icon)
        btn.setIconSize(QSize(18, 18))
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setFlat(True) 
        btn.setStyleSheet("""
            QPushButton { border-radius: 6px; border: none; background: transparent; }
            QPushButton:hover { background-color: rgba(128, 128, 128, 0.2); }
        """)
        return btn

    def update_progress(self, val):
        self.current_percent = val
        self.p_bar.setValue(val)

    def update_status(self, msg):
        icon_path = None
        clean_msg = msg
        if "⏸️" in msg or "Paused" in msg or "مؤقتاً" in msg:
            icon_path = "assets/icons/pause.svg"
            clean_msg = msg.replace("⏸️", "").strip()
        elif "⏳" in msg or "Downloading" in msg or "تحميل" in msg or "Resuming" in msg or "استئناف" in msg or "Starting" in msg or "بدء" in msg:
            if "Resuming" in msg or "استئناف" in msg:
                icon_path = "assets/icons/restart.svg"
            elif "Starting" in msg or "بدء" in msg:
                icon_path = "assets/icons/rocket.svg"
            else:
                icon_path = "assets/icons/hourglass.svg"
            clean_msg = msg.replace("⏳", "").strip()
        elif "⚙️" in msg or "Processing" in msg or "معالجة" in msg:
            icon_path = "assets/icons/settings.svg"
            clean_msg = msg.replace("⚙️", "").strip()
        elif "🔍" in msg or "Inspecting" in msg or "فحص" in msg:
            icon_path = "assets/icons/search-lens.svg"
            clean_msg = msg.replace("🔍", "").strip()
        elif ("✅" in msg or 
              "Done" in msg or 
              "اكتمل" in msg or 
              "Completed" in msg or
              msg.strip() == tr("status_done", "Download Completed").strip() or
              msg.strip() == tr("status_cover_failed", "Downloaded (Warning: Cover failed)").strip()):
            icon_path = "assets/icons/check.svg"
            clean_msg = msg.replace("✅", "").strip()
        elif "❌" in msg or "Canceled" in msg or "إلغاء" in msg or "خطأ" in msg or "Error" in msg:
            icon_path = "assets/icons/cancel.svg"
            clean_msg = msg.replace("❌", "").strip()

        left_msg = clean_msg
        right_msg = ""

        if " | Speed: " in clean_msg:
            parts = clean_msg.split(" | Speed: ")
            left_msg = parts[0]
            if len(parts) > 1:
                speed_eta_part = parts[1]
                if " | ETA: " in speed_eta_part:
                    se_parts = speed_eta_part.split(" | ETA: ")
                    speed_str = se_parts[0].strip()
                    eta_str = se_parts[1].strip()
                    right_msg = f"🚀 {speed_str}    ⌛ {eta_str}"
                else:
                    right_msg = f"🚀 {speed_eta_part.strip()}"

        if "Downloading..." in left_msg:
            left_msg = left_msg.replace("Downloading... ", f"{tr('status_downloading', 'Downloading...')} {self.current_percent}%    ")
        left_msg = left_msg.replace(" | ", "    ")

        self.current_status_icon_path = icon_path
        if icon_path:
            self.status_icon_lbl.setPixmap(get_colored_icon(icon_path, get_current_theme_color()).pixmap(14, 14))
            self.status_icon_lbl.show()
        else:
            self.status_icon_lbl.hide()

        is_done = ("✅" in msg or 
                   "Done" in msg or 
                   "اكتمل" in msg or 
                   "Completed" in msg or
                   msg.strip() == tr("status_done", "Download Completed").strip() or
                   msg.strip() == tr("status_cover_failed", "Downloaded (Warning: Cover failed)").strip())
        is_error = ("❌" in msg or "Error" in msg or "خطأ" in msg or "Canceled" in msg or "إلغاء" in msg)
        is_active = ("⏳" in msg or "Downloading" in msg or "تحميل" in msg or "Starting" in msg or "بدء" in msg
                     or "⚙️" in msg or "Processing" in msg or "معالجة" in msg
                     or "🔍" in msg or "Inspecting" in msg or "فحص" in msg)

        if is_done:
            self.status_label.setObjectName("StatusLabelDone")
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.hide()
            self.btn_open.show()
            self.right_status_label.setText("")
            self.right_status_label.hide()
            try:
                main_win = self.window()
                size_bytes = os.path.getsize(self.save_path) if os.path.exists(self.save_path) else 0
                mb = size_bytes / (1024 * 1024)
                size_str = f"{size_bytes / 1024:.1f} KB" if mb < 1 else f"{mb:.1f} MB"

                from utils.helpers import get_data_path
                thumb_dir = get_data_path(os.path.join('data', 'thumbnails'))
                os.makedirs(thumb_dir, exist_ok=True)
                import hashlib
                url = getattr(self, 'url', 'N/A')
                url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
                thumb_path = os.path.join(thumb_dir, f"{url_hash}.png")
                pixmap = self.thumb_label.pixmap()
                if pixmap and not pixmap.isNull():
                    pixmap.save(thumb_path, "PNG")

                sub_info = ""
                if "|" in msg:
                    sub_info = " |" + msg.split("|", 1)[1]
                done_msg = f"{tr('status_done', 'Download Completed')}{sub_info}"
                self.status_label.setText(done_msg)

                if hasattr(main_win, 'page_history'):
                    duration = getattr(self, 'duration', '00:00')
                    media_type = getattr(self, 'media_type', 'video')
                    main_win.page_history.add_to_history(
                        self.title_label._full_text,
                        duration,
                        size_str,
                        url,
                        media_type,
                        thumb_path=thumb_path,
                        save_path=self.save_path
                    )
                    if hasattr(main_win, 'show_notification'):
                        main_win.show_notification(
                            tr("status_done", "Download Completed"),
                            self.title_label._full_text,
                            self.thumb_label.pixmap()
                        )
            except Exception as e:
                logger.warning(f"Error handling card completion: {e}")
        elif is_error:
            self.status_label.setObjectName("StatusLabelError")
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.show()
            self.status_label.setText(left_msg)
            self.right_status_label.setText("")
            self.right_status_label.hide()
        elif is_active:
            self.status_label.setObjectName("StatusLabelActive")
            self.status_label.setText(left_msg)
            if right_msg:
                self.right_status_label.setText(right_msg)
                self.right_status_label.show()
            else:
                self.right_status_label.setText("")
                self.right_status_label.hide()
        else:
            self.status_label.setObjectName("")
            self.status_label.setText(left_msg)
            if right_msg:
                self.right_status_label.setText(right_msg)
                self.right_status_label.show()
            else:
                self.right_status_label.setText("")
                self.right_status_label.hide()
        # Force QSS re-evaluation after objectName change
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def update_icon_colors(self, icon_color):
        self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg" if self.btn_pause.toolTip() == tr("tooltip_pause", "Pause") else "assets/icons/play.svg", icon_color))
        self.btn_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", icon_color))
        self.btn_reload.setIcon(get_colored_icon("assets/icons/restart.svg", icon_color))
        self.btn_open.setIcon(get_colored_icon("assets/icons/folder-open.svg", icon_color))
        if getattr(self, 'current_status_icon_path', None):
            self.status_icon_lbl.setPixmap(get_colored_icon(self.current_status_icon_path, icon_color).pixmap(14, 14))

    def action_cancel(self):
        self.status_label.setText(tr("status_cancelled", "❌ Canceled"))
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_reload.show()
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def action_pause_resume(self):
        icon_color = get_current_theme_color()
        if self.btn_pause.toolTip() == tr("tooltip_pause", "Pause"):
            self.btn_pause.setIcon(get_colored_icon("assets/icons/play.svg", icon_color))
            self.btn_pause.setToolTip(tr("tooltip_resume", "Resume"))
            self.status_label.setText(tr("status_paused", "⏸️ Paused"))
            if hasattr(self, 'worker') and self.worker:
                self.worker.pause()
        else:
            self.btn_pause.setIcon(get_colored_icon("assets/icons/pause.svg", icon_color))
            self.btn_pause.setToolTip(tr("tooltip_pause", "Pause"))
            self.status_label.setText(tr("status_resuming", "⏳ Resuming..."))
            if hasattr(self, 'worker') and self.worker:
                self.worker.resume()

    def action_open_folder(self):
        from utils.helpers import open_file_or_folder
        path = os.path.normpath(self.save_path)
        if os.path.exists(path):
            open_file_or_folder(path, select_file=True)
            return

        folder_path = os.path.dirname(path)
        base_path = os.path.splitext(path)[0]
        folder, base_name = os.path.split(base_path)
        target_prefix = base_name + "."
        possible_files = []
        if os.path.exists(folder):
            try:
                for entry in os.listdir(folder):
                    if entry.startswith(target_prefix) and not entry.lower().endswith(('.srt', '.vtt', '.ass', '.lrc')):
                        possible_files.append(os.path.join(folder, entry))
            except Exception:
                pass
                
        if possible_files:
            open_file_or_folder(possible_files[0], select_file=True)
        elif os.path.exists(folder_path):
            open_file_or_folder(folder_path)
        else:
            self.status_label.setText("❌ File deleted or moved!")

    def set_worker(self, worker):
        self.worker = worker
        if not getattr(self, 'has_real_thumbnail', False) and hasattr(worker, 'thumb_loaded_signal'):
            worker.thumb_loaded_signal.connect(self.update_thumbnail_from_bytes)
            worker.needs_thumbnail = True

    def update_thumbnail_from_bytes(self, image_data):
        if image_data:
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled_thumb = pixmap.scaled(120, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                self.thumb_label.setPixmap(scaled_thumb)
                self.thumb_label.setStyleSheet("")  # Clear placeholder background
                self.has_real_thumbnail = True

    def set_save_path(self, path):
        self.save_path = path

class PlaylistThumbnail(ResponsiveImage):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.video_count = 0

    def set_count(self, count):
        self.video_count = count
        if count > 0:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.video_count > 0:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event) 
        if self.video_count > 0 and hasattr(self, '_pixmap') and self._pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            scaled_size = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio).size()
            x = (self.width() - scaled_size.width()) // 2
            y = (self.height() - scaled_size.height()) // 2
            box_w = 120
            box_h = 35
            painter.fillRect(x, y + scaled_size.height() - box_h, box_w, box_h, QColor(0, 0, 0, 180)) 
            painter.setPen(Qt.GlobalColor.white)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            painter.setFont(font)
            painter.drawText(x, y + scaled_size.height() - box_h, box_w, box_h, Qt.AlignmentFlag.AlignCenter, f"▶ {self.video_count} Videos")

class HistoryCard(QFrame):
    selection_changed = pyqtSignal()
    request_selection_mode = pyqtSignal(object)
    request_delete = pyqtSignal(object)
    request_details = pyqtSignal(object)

    def __init__(self, title, url, media_type, date_str="", thumb_path="", save_path="", duration="", size="", main_app=None):
        super().__init__()
        self.url = url
        self.media_type = media_type
        self.thumb_path = thumb_path
        self.save_path = save_path
        self.duration = duration
        self.size = size
        self.main_app = main_app
        self.selection_mode = False

        self._press_pos = None
        self._start_x = 0
        self._is_swiping = False
        self._current_x = 0
        self.MAX_SWIPE = 95

        self.item_data = {
            "title": title,
            "url": url,
            "type": media_type,
            "date": date_str,
            "thumb_path": thumb_path,
            "save_path": save_path,
            "duration": duration,
            "size": size
        }

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumHeight(75)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

        # 1. Background Action Frame (Holds revealed quick action buttons)
        from PyQt6.QtWidgets import QApplication
        is_rtl = QApplication.isRightToLeft()

        self.bg_frame = QFrame(self)
        self.bg_frame.setStyleSheet("background-color: #0f172a; border-radius: 8px;")
        bg_layout = QHBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(10, 8, 10, 8)
        bg_layout.setSpacing(8)

        self.btn_swipe_redownload = QPushButton()
        self.btn_swipe_redownload.setFixedSize(36, 36)
        self.btn_swipe_redownload.setToolTip(tr("ctx_redownload", "Redownload"))
        self.btn_swipe_redownload.setIcon(get_colored_icon("assets/icons/restart.svg", "#ffffff"))
        self.btn_swipe_redownload.setIconSize(QSize(18, 18))
        self.btn_swipe_redownload.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_swipe_redownload.clicked.connect(self.action_redownload)

        self.btn_swipe_delete = QPushButton()
        self.btn_swipe_delete.setFixedSize(36, 36)
        self.btn_swipe_delete.setToolTip(tr("ctx_delete", "Delete"))
        self.btn_swipe_delete.setIcon(get_colored_icon("assets/icons/trash.svg", "#ffffff"))
        self.btn_swipe_delete.setIconSize(QSize(18, 18))
        self.btn_swipe_delete.setStyleSheet("""
            QPushButton {
                background-color: #ef4444; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_swipe_delete.clicked.connect(lambda checked=False, obj=self: obj.request_delete.emit(obj))

        # Swipe logic: 
        # In LTR, stretch pushes buttons to the right. Card swipes left to reveal.
        # In RTL, stretch pushes buttons to the left. Card swipes right to reveal.
        bg_layout.addStretch()
        bg_layout.addWidget(self.btn_swipe_redownload)
        bg_layout.addWidget(self.btn_swipe_delete)

        # Hide background actions by default to prevent any bleeding
        self.bg_frame.hide()

        # 2. Foreground Content Frame (Holds main card UI)
        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("CardContentFrame")
        layout = QHBoxLayout(self.content_frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Checkbox for selection mode
        self.checkbox = QCheckBox(self.content_frame)
        self.checkbox.setFixedSize(22, 22)
        self.checkbox.hide()
        self.checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self.checkbox)

        self.thumb_lbl = QLabel()
        self.thumb_lbl.setFixedSize(96, 54)
        self.thumb_lbl.setStyleSheet("border-radius: 6px; background-color: #1a2035; border: 1px solid #1e293b;")
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from PyQt6.QtGui import QPixmap, QPainter
        icon_file = "assets/icons/video.svg" if media_type == "video" else "assets/icons/music.svg"
        icon_pixmap = get_colored_icon(icon_file, "#ffffff").pixmap(20, 20)

        if thumb_path and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(96, 54, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.FastTransformation)
                final_pix = QPixmap(96, 54)
                final_pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(final_pix)
                painter.drawPixmap(0, 0, scaled_pix)
                painter.fillRect(0, 0, 96, 54, QColor(0, 0, 0, 80))
                icon_x = (96 - 20) // 2
                icon_y = (54 - 20) // 2
                painter.drawPixmap(icon_x, icon_y, icon_pixmap)
                painter.end()
                self.thumb_lbl.setPixmap(final_pix)
            else:
                self.thumb_lbl.setPixmap(get_colored_icon(icon_file, get_current_theme_color()).pixmap(24, 24))
        else:
            self.thumb_lbl.setPixmap(get_colored_icon(icon_file, get_current_theme_color()).pixmap(24, 24))

        layout.addWidget(self.thumb_lbl)

        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        self.title_label = ElidedLabel(title)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        details_layout.addWidget(self.title_label)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(8)
        info_text = f"{tr('download_date_lbl', 'Download Date')}: {date_str}" if date_str else ""
        info_lbl = QLabel(info_text)
        info_lbl.setStyleSheet("color: gray; font-size: 11px;")
        sub_layout.addWidget(info_lbl)

        if date_str:
            bullet_lbl = QLabel("•")
            bullet_lbl.setStyleSheet("color: gray; font-size: 11px;")
            sub_layout.addWidget(bullet_lbl)

        import html
        from utils.theme import get_accent_hex
        url_lbl = QLabel()
        safe_url = html.escape(url, quote=True)
        url_lbl.setText(f'<a href="{safe_url}" style="color: {get_accent_hex()}; text-decoration: none;">{tr("source_link", "Source Link")}</a>')
        url_lbl.setOpenExternalLinks(True)
        url_lbl.setStyleSheet("font-size: 11px;")
        sub_layout.addWidget(url_lbl)

        sub_layout.addStretch()
        details_layout.addLayout(sub_layout)
        layout.addLayout(details_layout)
        layout.setStretch(2, 1)

        # Single primary Play button
        self.btn_play = QPushButton()
        self.btn_play.setToolTip(tr("ctx_play_file", "Play File"))
        self.btn_play.setFixedSize(36, 36)
        self.btn_play.setFlat(True)
        self.btn_play.setIcon(get_colored_icon("assets/icons/play.svg", get_current_theme_color()))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.clicked.connect(self.action_open_file)

        if not self.save_path or not os.path.exists(self.save_path):
            self.btn_play.setEnabled(False)
            self.btn_play.setToolTip(tr("file_deleted_or_moved", "File deleted or moved"))

        layout.addWidget(self.btn_play)
        self.update_card_style()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_frame.setGeometry(0, 0, self.width(), self.height())
        self.content_frame.setGeometry(self._current_x, 0, self.width(), self.height())

    def set_selection_mode(self, enabled):
        self.selection_mode = enabled
        if enabled:
            self.close_swipe(animated=False)
            self.checkbox.show()
        else:
            self.checkbox.setChecked(False)
            self.checkbox.hide()
        self.update_card_style()

    def is_selected(self):
        return self.checkbox.isChecked()

    def set_selected(self, selected):
        self.checkbox.setChecked(selected)
        self.update_card_style()

    def _on_check_changed(self, state):
        self.update_card_style()
        self.selection_changed.emit()

    def update_icon_colors(self, icon_color=None):
        if not icon_color:
            icon_color = get_current_theme_color()
        icon_file = "assets/icons/video.svg" if getattr(self, 'media_type', 'video') == "video" else "assets/icons/music.svg"
        if not self.thumb_path or not os.path.exists(self.thumb_path):
            self.thumb_lbl.setPixmap(get_colored_icon(icon_file, icon_color).pixmap(QSize(24, 24)))
        if hasattr(self, 'btn_play'):
            self.btn_play.setIcon(get_colored_icon("assets/icons/play.svg", icon_color))
        if hasattr(self, 'btn_swipe_redownload'):
            self.btn_swipe_redownload.setIcon(get_colored_icon("assets/icons/restart.svg", "#ffffff"))
        if hasattr(self, 'btn_swipe_delete'):
            self.btn_swipe_delete.setIcon(get_colored_icon("assets/icons/trash.svg", "#ffffff"))
        self.update_card_style()

    def update_card_style(self):
        from utils.theme import get_accent_hex, hex_to_rgb
        from utils.helpers import detect_system_theme
        acc_hex = get_accent_hex()
        rgb = hex_to_rgb(acc_hex)

        is_dark = True
        if hasattr(self, 'main_app') and self.main_app and hasattr(self.main_app, 'theme_manager'):
            is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        else:
            is_dark = (detect_system_theme() == "dark")

        if is_dark:
            bg_card = "#1e293b"
            bg_card_hover = "#26354a"
            border_color = "#334155"
            bg_card_selected = "#1c2b42"
            bg_card_selected_hover = "#233756"
            text_color = "#f8fafc"
            bg_swipe = "#0f172a"
            btn_bg = "rgba(255, 255, 255, 0.06)"
            btn_border = "rgba(255, 255, 255, 0.12)"
        else:
            bg_card = "#ffffff"
            bg_card_hover = "#f8fafc"
            border_color = "#cbd5e1"
            bg_card_selected = "#dbeafe"
            bg_card_selected_hover = "#bfdbfe"
            text_color = "#1e293b"
            bg_swipe = "#e2e8f0"
            btn_bg = "rgba(0, 0, 0, 0.04)"
            btn_border = "rgba(0, 0, 0, 0.08)"

        if hasattr(self, 'bg_frame') and self.bg_frame:
            self.bg_frame.setStyleSheet(f"background-color: {bg_swipe}; border-radius: 8px;")

        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setStyleSheet(f"color: {text_color}; font-weight: bold;")

        if hasattr(self, 'btn_play') and self.btn_play:
            self.btn_play.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 8px;
                    border: 1px solid {btn_border};
                    background-color: {btn_bg};
                }}
                QPushButton:hover {{
                    background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.25);
                    border: 1.5px solid {acc_hex};
                }}
                QPushButton:disabled {{
                    background-color: transparent;
                    border: 1px solid {border_color};
                }}
            """)

        if self.is_selected():
            self.content_frame.setStyleSheet(f"""
                QFrame#CardContentFrame {{
                    background-color: {bg_card_selected};
                    border: 2px solid {acc_hex};
                    border-radius: 10px;
                }}
                QFrame#CardContentFrame:hover {{
                    background-color: {bg_card_selected_hover};
                    border: 2px solid {acc_hex};
                }}
            """)
        else:
            self.content_frame.setStyleSheet(f"""
                QFrame#CardContentFrame {{
                    background-color: {bg_card};
                    border: 1px solid {border_color};
                    border-radius: 10px;
                }}
                QFrame#CardContentFrame:hover {{
                    background-color: {bg_card_hover};
                    border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.45);
                }}
            """)


    def animate_swipe(self, target_x):
        self._current_x = target_x
        if target_x != 0:
            self.bg_frame.show()

        anim = QPropertyAnimation(self.content_frame, b"pos", self)
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.setStartValue(self.content_frame.pos())
        anim.setEndValue(QPoint(target_x, 0))
        if target_x == 0:
            anim.finished.connect(self.bg_frame.hide)
        anim.start()
        self._current_anim = anim

    def close_swipe(self, animated=True):
        if animated:
            self.animate_swipe(0)
        else:
            self._current_x = 0
            self.content_frame.move(0, 0)
            self.bg_frame.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._start_x = self.content_frame.x()
            self._is_swiping = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos and not self.selection_mode:
            curr_pos = event.globalPosition().toPoint()
            dx = curr_pos.x() - self._press_pos.x()
            
            if abs(dx) > 6:
                self._is_swiping = True

            if self._is_swiping:
                from PyQt6.QtWidgets import QApplication
                is_rtl = QApplication.isRightToLeft()

                # Clamp swipe offset based on direction towards sidebar
                if is_rtl:
                    # Swiping right towards sidebar
                    new_x = max(0, min(self.MAX_SWIPE, self._start_x + dx))
                else:
                    # Swiping left towards sidebar
                    new_x = min(0, max(-self.MAX_SWIPE, self._start_x + dx))

                if new_x != 0:
                    self.bg_frame.show()

                self._current_x = new_x
                self.content_frame.move(new_x, 0)
                return
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        if self._press_pos and event.button() == Qt.MouseButton.LeftButton:
            if self._is_swiping:
                from PyQt6.QtWidgets import QApplication
                is_rtl = QApplication.isRightToLeft()
                
                curr_offset = abs(self.content_frame.x())
                if curr_offset > self.MAX_SWIPE / 2.5:
                    target_x = self.MAX_SWIPE if is_rtl else -self.MAX_SWIPE
                    self.animate_swipe(target_x)
                else:
                    self.animate_swipe(0)
                
                self._press_pos = None
                self._is_swiping = False
                return

            self._press_pos = None
            
            # Click handling
            if self.selection_mode:
                self.checkbox.setChecked(not self.checkbox.isChecked())
                return
            elif self.content_frame.x() != 0:
                self.animate_swipe(0)
                return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.selection_mode:
            if self.save_path and os.path.exists(self.save_path):
                self.action_open_file()
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        # 1. Play file
        play_action = QAction(get_colored_icon("assets/icons/play.svg", get_current_theme_color()), tr("ctx_play_file", "Play File"), self)
        file_exists = bool(self.save_path and os.path.exists(self.save_path))
        play_action.setEnabled(file_exists)
        play_action.triggered.connect(self.action_open_file)
        menu.addAction(play_action)

        # 2. Redownload
        redownload_action = QAction(get_colored_icon("assets/icons/restart.svg", get_current_theme_color()), tr("ctx_redownload", "Redownload"), self)
        redownload_action.triggered.connect(self.action_redownload)
        menu.addAction(redownload_action)

        # 3. Details
        details_action = QAction(get_colored_icon("assets/icons/info.svg", get_current_theme_color()), tr("ctx_details", "Details"), self)
        details_action.triggered.connect(lambda checked=False, obj=self: obj.request_details.emit(obj))
        menu.addAction(details_action)

        menu.addSeparator()

        # 4. Select
        select_action = QAction(get_colored_icon("assets/icons/check.svg", get_current_theme_color()), tr("ctx_select", "Select"), self)
        select_action.triggered.connect(lambda checked=False, obj=self: obj.request_selection_mode.emit(obj))
        menu.addAction(select_action)

        # 5. Delete
        delete_action = QAction(get_colored_icon("assets/icons/trash.svg", "#ef4444"), tr("ctx_delete", "Delete"), self)
        delete_action.triggered.connect(lambda checked=False, obj=self: obj.request_delete.emit(obj))
        menu.addAction(delete_action)

        menu.exec(event.globalPos())

    def action_open_file(self):
        if self.save_path and os.path.exists(self.save_path):
            from utils.helpers import open_file_or_folder
            open_file_or_folder(self.save_path)

    def action_redownload(self):
        if self.main_app and self.url:
            self.main_app.system_manager.handle_incoming_url(self.url)

class SearchResultCard(QFrame):
    def __init__(self, title, url, uploader, duration_sec, view_count, thumbnail_url, download_callback, is_playlist=False, parent=None):
        super().__init__(parent)
        self.url = url
        self.thumbnail_url = thumbnail_url
        self.download_callback = download_callback
        self.is_playlist = is_playlist
        self.has_real_thumbnail = False
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Thumbnail label
        from gui.components.common import ResponsiveImage
        self.thumb_lbl = ResponsiveImage(min_height=56, spinner_size=18)
        self.thumb_lbl.setFixedSize(100, 56)
        self.thumb_lbl.setStyleSheet("border-radius: 6px; background-color: #1a2035; border: 1px solid #1e293b;")
        self.thumb_lbl.show_loading()
        layout.addWidget(self.thumb_lbl)
        
        # Details layout
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        # Video title
        self.title_label = ElidedLabel(title)
        self.title_label.setToolTip(title)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        details_layout.addWidget(self.title_label)
        
        # Metadata layout
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(10)
        
        # Playlist or Video Badge
        self.badge = QLabel()
        if is_playlist:
            self.badge.setText(tr("badge_playlist", "Playlist"))
            from utils.theme import get_accent_hex, hex_to_rgb
            acc = get_accent_hex()
            rgb = hex_to_rgb(acc)
            self.badge.setStyleSheet(f"""
                background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.12);
                color: {acc};
                border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.25);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
        else:
            self.badge.setText(tr("badge_video", "Video"))
            self.badge.setStyleSheet("""
                background-color: rgba(59, 130, 246, 0.12);
                color: #3b82f6;
                border: 1px solid rgba(59, 130, 246, 0.25);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
        meta_layout.addWidget(self.badge)
        
        # Channel name
        self.uploader_lbl = QLabel(uploader)
        self.uploader_lbl.setStyleSheet("color: gray; font-size: 11px;")
        meta_layout.addWidget(self.uploader_lbl)
        
        # Duration label
        duration_str = ""
        if duration_sec and not is_playlist:
            try:
                sec = int(duration_sec)
                m, s = divmod(sec, 60)
                h, m = divmod(m, 60)
                duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            except:
                pass
        
        if duration_str:
            self.thumb_lbl.set_duration_text(duration_str)
            
        # Views/Count label
        if is_playlist:
            if view_count:
                v_text = "Videos" if tr("nav_search") == "Search" else "فيديو"
                self.thumb_lbl.set_duration_text(f"▶ {view_count} {v_text}")
            views_str = ""
        else:
            views_str = ""
            if view_count:
                try:
                    vc = int(view_count)
                    if vc >= 1_000_000:
                        views_str = f"{vc/1_000_000:.1f}M views"
                    elif vc >= 1_000:
                        views_str = f"{vc/1_000:.1f}K views"
                    else:
                        views_str = f"{vc} views"
                except:
                    views_str = str(view_count)
                    
        if views_str:
            self.views_lbl = QLabel(views_str)
            self.views_lbl.setStyleSheet("color: gray; font-size: 11px;")
            meta_layout.addWidget(self.views_lbl)
            
        meta_layout.addStretch()
        details_layout.addLayout(meta_layout)
        layout.addLayout(details_layout)
        layout.setStretch(1, 1)
        
        # Download button
        self.btn_download = QPushButton()
        self.btn_download.setToolTip(tr("start_download", "Download"))
        self.btn_download.setFixedSize(32, 32)
        self.btn_download.setFlat(True)
        self.btn_download.setStyleSheet("""
            QPushButton { border-radius: 6px; border: none; background: transparent; }
            QPushButton:hover { background-color: rgba(128, 128, 128, 0.2); }
        """)
        self.btn_download.setIcon(get_colored_icon("assets/icons/download.svg", get_current_theme_color()))
        self.btn_download.setIconSize(QSize(18, 18))
        self.btn_download.clicked.connect(self.action_download)
        layout.addWidget(self.btn_download)
        
    def action_download(self):
        if self.download_callback:
            self.download_callback(self.url, self.title_label._full_text, self.thumb_lbl.pixmap(), self.is_playlist)
            
    def update_thumbnail(self, image_data):
        if image_data:
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled_thumb = pixmap.scaled(100, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.thumb_lbl.setPixmap(scaled_thumb)
                self.thumb_lbl.setStyleSheet("border-radius: 6px; border: 1px solid #1e293b;")
                self.has_real_thumbnail = True
                return
        
        self.thumb_lbl.hide_loading()
        icon_name = "package.svg" if self.is_playlist else "video.svg"
        placeholder_icon = get_colored_icon(f"assets/icons/{icon_name}", get_current_theme_color())
        self.thumb_lbl.setPixmap(placeholder_icon.pixmap(QSize(24, 24)))
                
    def update_icon_colors(self, icon_color):
        self.btn_download.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        if not self.has_real_thumbnail and not self.thumb_lbl.spinner.isVisible():
            icon_name = "package.svg" if self.is_playlist else "video.svg"
            self.thumb_lbl.setPixmap(get_colored_icon(f"assets/icons/{icon_name}", icon_color).pixmap(QSize(24, 24)))

