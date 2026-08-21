import os
import re
import urllib.request
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QComboBox, QScrollArea, 
                             QCheckBox, QApplication, QStackedLayout, 
                             QMessageBox, QSizePolicy, QFileDialog, QFrame)
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon

from utils import strings
from core.workers import InfoFetcher, ThumbnailWorker
from utils.settings import app_config
from utils.helpers import format_views, format_upload_date
from gui.theme import styled, Theme
from gui.widgets import SmartTitleLabel

# --- كلاس الصورة التفاعلية ذات الحواف الناعمة والنسبة الثابتة ---
class ResponsiveImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(260, 146)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: transparent; border-radius: 10px;")

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()

    def update_image(self):
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            super().setPixmap(scaled)
        else:
            super().setPixmap(QPixmap())

    def clear(self):
        self._pixmap = None
        super().clear()


# --- الكلاس الأساسي لتابة الرئيسية Home ---
class HomeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.single_thumb_data = None
        self.current_url = ""
        self.current_title = ""
        self.video_language = None
        self.entries_checkboxes = []
        self.playlist_thumbs_data = {}
        
        self.initUI()

    def initUI(self):
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(20, 20, 20, 20)
        tab_layout.setSpacing(16)
        
        # --- 1. بار إدخال الرابط العصري ---
        url_card = QFrame()
        url_card.setObjectName("OptionsCard")
        url_card_layout = QHBoxLayout(url_card)
        url_card_layout.setContentsMargins(8, 8, 8, 8)
        url_card_layout.setSpacing(8)
        
        self.paste_btn = QPushButton("📋") 
        self.paste_btn.setObjectName("icon_btn")
        self.paste_btn.setFixedSize(38, 38) 
        self.paste_btn.setToolTip("لصق الرابط من الحافظة" if strings.is_ar else "Paste from Clipboard")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(strings.MSG_PLACEHOLDER_URL)
        self.url_input.setClearButtonEnabled(True) 
        self.url_input.setFixedHeight(38)
        self.url_input.returnPressed.connect(self.fetch_video_info)
        self.url_input.textChanged.connect(self.on_url_changed) 
        
        self.fetch_btn = styled.primary_button("🔍 " + ("فحص" if strings.is_ar else "Check"))
        self.fetch_btn.setFixedHeight(38)
        self.fetch_btn.setToolTip("فحص الرابط" if strings.is_ar else "Check Link")
        self.fetch_btn.clicked.connect(self.fetch_video_info)

        url_card_layout.addWidget(self.paste_btn)
        url_card_layout.addWidget(self.url_input, stretch=1)
        url_card_layout.addWidget(self.fetch_btn)
        tab_layout.addWidget(url_card)

        # --- 2. منطقة العرض المكدسة (Placeholder / Two-Card View / Playlist) ---
        self.content_stacked = QWidget()
        self.content_layout = QStackedLayout(self.content_stacked)
        
        # أ) الشاشة الافتراضية (Placeholder)
        self.placeholder_widget = QWidget()
        placeholder_vbox = QVBoxLayout(self.placeholder_widget)
        placeholder_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_vbox.setSpacing(12)
        
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel("جاهز للتحميل" if strings.is_ar else "Ready to Download")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #9ca3af; background: transparent;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub_lbl = QLabel("ضع رابط الفيديو أو قائمة التشغيل لبدء الفحص والتحميل فوراً" if strings.is_ar else "Paste any video or playlist URL above to start downloading")
        sub_lbl.setStyleSheet("font-size: 13px; color: #6b7280; background: transparent;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        placeholder_vbox.addStretch()
        placeholder_vbox.addWidget(icon_lbl)
        placeholder_vbox.addWidget(title_lbl)
        placeholder_vbox.addWidget(sub_lbl)
        placeholder_vbox.addStretch()
        
        self.content_layout.addWidget(self.placeholder_widget)

        # ب) واجهة الكارتين رأسياً (Two-Card Flexible Vertical Stack Layout)
        self.single_preview_w = QWidget()
        single_v_layout = QVBoxLayout(self.single_preview_w)
        single_v_layout.setContentsMargins(0, 0, 0, 0)
        single_v_layout.setSpacing(12)
        
        # ═════════════════════════════════════════════════════════════
        # الكارت الأول (العلوي): بطاقة معاينة الفيديو (Media Preview Card)
        # ═════════════════════════════════════════════════════════════
        self.preview_card = QFrame()
        self.preview_card.setObjectName("PreviewCard")
        preview_card_layout = QVBoxLayout(self.preview_card)
        preview_card_layout.setContentsMargins(16, 14, 16, 14)
        preview_card_layout.setSpacing(8)
        
        # حاوية الصورة وبادج المدة في المنتصف (16:9) تأخذ المساحة المتمددة بالكامل
        thumb_wrapper = QWidget()
        thumb_wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        thumb_wrapper_layout = QVBoxLayout(thumb_wrapper)
        thumb_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        thumb_wrapper_layout.setSpacing(0)
        
        self.thumbnail_label = ResponsiveImageLabel()
        self.thumbnail_label.setObjectName("Thumbnail")
        self.thumbnail_label.setMinimumSize(260, 146)
        self.thumbnail_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        badge_layout = QHBoxLayout()
        badge_layout.setContentsMargins(6, 0, 6, 6)
        badge_layout.addStretch()
        self.video_duration_label = QLabel()
        self.video_duration_label.setObjectName("DurationBadge")
        self.video_duration_label.hide()
        badge_layout.addWidget(self.video_duration_label)
        
        thumb_wrapper_layout.addWidget(self.thumbnail_label, stretch=1)
        thumb_wrapper_layout.addLayout(badge_layout)
        preview_card_layout.addWidget(thumb_wrapper, stretch=1)
        
        # بيانات الفيديو أسفل الصورة ملمومة بإحكام بدون أي مسافات زائدة
        meta_vbox = QVBoxLayout()
        meta_vbox.setSpacing(2)
        meta_vbox.setContentsMargins(4, 4, 4, 2)
        
        self.video_title_label = SmartTitleLabel()
        self.video_title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f3f4f6; background: transparent;")
        self.video_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_vbox.addWidget(self.video_title_label)
        
        self.video_channel_label = QLabel()
        self.video_channel_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #9ca3af; background: transparent;")
        self.video_channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_vbox.addWidget(self.video_channel_label)
        
        self.video_stats_label = QLabel()
        self.video_stats_label.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        self.video_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_vbox.addWidget(self.video_stats_label)
        
        preview_card_layout.addLayout(meta_vbox, stretch=0)
        self.preview_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        single_v_layout.addWidget(self.preview_card, stretch=1)
        
        # ═════════════════════════════════════════════════════════════
        # الكارت الثاني (السفلي): بطاقة خيارات التحميل (Download Options Card)
        # ═════════════════════════════════════════════════════════════
        self.options_card = QFrame()
        self.options_card.setObjectName("OptionsCard")
        self.options_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        options_card_layout = QVBoxLayout(self.options_card)
        options_card_layout.setContentsMargins(16, 12, 16, 14)
        options_card_layout.setSpacing(10)
        
        title_opt = QLabel("⚙️ " + ("خيارات التحميل" if strings.is_ar else "Download Options"))
        title_opt.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6; background: transparent; padding: 0px; margin: 0px;")
        options_card_layout.addWidget(title_opt)
        
        # قائمة الجودات الشاملة (فيديو + صوت حقيقي)
        self.quality_combo = QComboBox()
        self.quality_combo.setFixedHeight(38)
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        options_card_layout.addWidget(self.quality_combo)
        
        # خيارات الترجمة
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(10)
        
        self.sub_check = QCheckBox(strings.CHK_SUBTITLES)
        self.sub_check.setEnabled(False)
        self.sub_check.stateChanged.connect(self.toggle_sub_options)
        
        self.sub_combo = QComboBox()
        self.sub_combo.setFixedHeight(34)
        self.sub_combo.hide()
        
        sub_layout.addWidget(self.sub_check)
        sub_layout.addWidget(self.sub_combo, stretch=1)
        options_card_layout.addLayout(sub_layout)
        
        # زر التحميل المباشر
        self.master_add_btn = styled.primary_button(strings.BTN_DOWNLOAD)
        self.master_add_btn.setFixedHeight(42)
        self.master_add_btn.setEnabled(False)
        self.master_add_btn.clicked.connect(self.add_to_queue)
        options_card_layout.addWidget(self.master_add_btn)
        
        single_v_layout.addWidget(self.options_card, stretch=0)
        
        self.content_layout.addWidget(self.single_preview_w)
        
        # ج) واجهة معاينة قائمة التشغيل (Playlist)
        self.playlist_layout_w = QWidget()
        playlist_main_vbox = QVBoxLayout(self.playlist_layout_w)
        playlist_main_vbox.setContentsMargins(0, 0, 0, 0)
        playlist_main_vbox.setSpacing(12)
        
        playlist_bar = QHBoxLayout()
        self.master_checkbox = QCheckBox(strings.CHK_SELECT_ALL)
        self.master_checkbox.setChecked(True)
        self.master_checkbox.clicked.connect(lambda: [c.setChecked(self.master_checkbox.isChecked()) for c in getattr(self, 'entries_checkboxes', [])])
        
        self.playlist_count_label = QLabel()
        self.playlist_count_label.setStyleSheet("color: #9ca3af; font-weight: bold;")
        
        playlist_bar.addWidget(self.master_checkbox)
        playlist_bar.addStretch()
        playlist_bar.addWidget(self.playlist_count_label)
        playlist_main_vbox.addLayout(playlist_bar)
        
        self.playlist_list_w = QScrollArea()
        self.playlist_list_w.setWidgetResizable(True)
        self.playlist_content_w = QWidget()
        self.playlist_v_layout = QVBoxLayout(self.playlist_content_w)
        self.playlist_v_layout.setContentsMargins(0, 0, 0, 0)
        self.playlist_v_layout.setSpacing(6)
        self.playlist_list_w.setWidget(self.playlist_content_w)
        playlist_main_vbox.addWidget(self.playlist_list_w, stretch=1)
        
        # بطاقة خيارات قائمة التشغيل السفلية
        self.playlist_options_card = QFrame()
        self.playlist_options_card.setObjectName("OptionsCard")
        pl_opt_layout = QHBoxLayout(self.playlist_options_card)
        pl_opt_layout.setContentsMargins(12, 12, 12, 12)
        pl_opt_layout.setSpacing(12)
        
        self.pl_quality_combo = QComboBox()
        self.pl_quality_combo.setFixedHeight(38)
        self.pl_quality_combo.currentIndexChanged.connect(self.on_pl_quality_changed)
        
        self.pl_add_btn = styled.primary_button(strings.BTN_DOWNLOAD)
        self.pl_add_btn.setFixedHeight(38)
        self.pl_add_btn.clicked.connect(self.add_to_queue)
        
        pl_opt_layout.addWidget(self.pl_quality_combo, stretch=1)
        pl_opt_layout.addWidget(self.pl_add_btn)
        playlist_main_vbox.addWidget(self.playlist_options_card)
        
        self.content_layout.addWidget(self.playlist_layout_w)
        
        tab_layout.addWidget(self.content_stacked, stretch=1)

        self.video_options = []
        self.audio_options = []

    def paste_from_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_input.setText(text)
            self.fetch_video_info()

    def toggle_sub_options(self):
        if self.sub_check.isChecked():
            if self.sub_combo.count() > 0:
                self.sub_combo.show()
        else:
            self.sub_combo.hide()
        self.update_button_text()

    def on_url_changed(self, text):
        self.fetch_btn.setEnabled(True) 
        if not text.strip():
            self.content_layout.setCurrentWidget(self.placeholder_widget)
            self.master_add_btn.setEnabled(False)
            self.quality_combo.clear()
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)

    def fetch_video_info(self):
        url = self.url_input.text().strip()
        if url.startswith("ahs-dl://"): url = url.replace("ahs-dl://", "")
        elif url.startswith("ahs-dl:"): url = url.replace("ahs-dl:", "")
        import urllib.parse
        url = urllib.parse.unquote(url)
            
        if "list=RD" in url and "v=" in url:
            match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
            if match: url = f"https://www.youtube.com/watch?v={match.group(1)}"
                
        self.url_input.setText(url)
        if not url: return

        self.fetch_btn.setEnabled(False)

        is_playlist = "list=" in url
        if is_playlist:
            self.content_layout.setCurrentWidget(self.playlist_layout_w)
            while self.playlist_v_layout.count():
                item = self.playlist_v_layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
            
            self.entries_checkboxes = [] 
            loading_label = styled.secondary_label(strings.LBL_FETCHING)
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.playlist_v_layout.addWidget(loading_label)
        else:
            self.content_layout.setCurrentWidget(self.single_preview_w)
            self.single_thumb_data = None
            if app_config.get("show_thumbnails", True):
                self.thumbnail_label.show()
                self.thumbnail_label.clear()
                self.thumbnail_label.setText("⌛ ...")
            else:
                self.thumbnail_label.hide() 
            self.video_title_label.setText("جاري الفحص..." if strings.is_ar else "Fetching info...")
            self.video_channel_label.setText("")
            self.video_stats_label.setText("")
            self.video_duration_label.hide()

        if hasattr(self, 'fetch_thread') and self.fetch_thread.isRunning():
            self.fetch_thread.cancel_fetch()
            self.fetch_thread.wait(1500)

        self.fetch_thread = InfoFetcher(url, fetch_playlist=is_playlist)
        self.fetch_thread.info_received.connect(self.on_info_loaded)
        self.fetch_thread.error_received.connect(self.on_fetch_error) 
        self.fetch_thread.start()

    def on_fetch_error(self, error_msg):
        self.content_layout.setCurrentWidget(self.single_preview_w)
        self.thumbnail_label.setText("❌")
        self.video_title_label.setText("فشل في جلب البيانات" if strings.is_ar else "Error Fetching Info")
        self.video_channel_label.setText("")
        self.video_stats_label.setText("")
        self.video_duration_label.hide()
        self.fetch_btn.setEnabled(True)
        clean_error = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(error_msg))
        QMessageBox.critical(self, "Error", clean_error)

    def on_info_loaded(self, info, thumb_bytes):
        if not info or not isinstance(info, dict):
            self.on_fetch_error("Failed to extract media information." if not strings.is_ar else "فشل في جلب معلومات الوسائط.")
            return

        if info.get('_type') in ['playlist', 'multi_video'] or 'entries' in info:
            self.content_layout.setCurrentWidget(self.playlist_layout_w)
            while self.playlist_v_layout.count():
                item = self.playlist_v_layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
                
            self.entries_checkboxes = []
            self.playlist_thumbs_data = {}
            
            valid_index = 1 
            entries_list = info.get('entries')
            if not isinstance(entries_list, list):
                entries_list = []

            for entry in entries_list:
                if not entry or not isinstance(entry, dict): continue
                title = entry.get('title', '')
                if not title or "[Private video]" in title or "[Deleted video]" in title: continue

                item_widget = QWidget()
                item_widget.setObjectName("PlaylistItem")
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(10, 10, 10, 10) 
                item_layout.setSpacing(12)
                
                url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                video_id = entry.get('id')
                thumb_url = entry.get('thumbnail')
                if not thumb_url and entry.get('thumbnails'):
                    last_thumb = entry['thumbnails'][-1]
                    thumb_url = last_thumb.get('url') if isinstance(last_thumb, dict) else str(last_thumb)
                
                chk = QCheckBox(f"{valid_index}. {title}")
                chk.setChecked(True)
                chk.setProperty("url", url)
                chk.setProperty("title", title)
                
                if app_config.get("show_thumbnails", True):
                    img_label = QLabel()
                    img_label.setFixedSize(60, 36)
                    img_label.setObjectName("Thumbnail")
                    item_layout.addWidget(img_label)
                    chk.setProperty("img_label", img_label)
                    
                    if thumb_url or video_id:
                        worker = ThumbnailWorker(len(self.entries_checkboxes), thumb_url=thumb_url, video_id=video_id)
                        worker.thumb_loaded.connect(self.update_playlist_thumb)
                        worker.start()
                        if not hasattr(self, 'thumb_workers'): self.thumb_workers = []
                        self.thumb_workers.append(worker)

                item_layout.addWidget(chk, stretch=1)
                self.playlist_v_layout.addWidget(item_widget)
                self.entries_checkboxes.append(chk)
                valid_index += 1 
            
            self.playlist_count_label.setText(f"{len(self.entries_checkboxes)} " + ("فيديو" if strings.is_ar else "videos"))
            op = "<=" if app_config.get("allow_downgrade", True) else "="
            
            self.video_options = [
                (strings.QUAL_4K, f"bestvideo[height{op}2160]+bestaudio/best"),
                (strings.QUAL_2K, f"bestvideo[height{op}1440]+bestaudio/best"),
                (strings.QUAL_1080, f"bestvideo[height{op}1080]+bestaudio/best"),
                (strings.QUAL_720, f"bestvideo[height{op}720]+bestaudio/best"),
                (strings.QUAL_480, f"bestvideo[height{op}480]+bestaudio/best"),
                (strings.QUAL_360, f"bestvideo[height{op}360]+bestaudio/best"),
                (strings.QUAL_240, f"bestvideo[height{op}240]+bestaudio/best"),
                (strings.QUAL_144, f"bestvideo[height{op}144]+bestaudio/best")
            ]
            self.audio_options = [
                ("🎵 M4A (128kbps)", "m4a-128"),
                ("🎵 MP3 (320kbps)", "mp3-320"),
                ("🎵 MP3 (160kbps)", "mp3-160"),
                ("🎵 MP3 (128kbps)", "mp3-128"),
                ("🎵 MP3 (70kbps)", "mp3-70")
            ]
            self.update_quality_options()
            self.current_subtitles = {'available': True}
            self.current_auto_subs = {}
            self.build_subtitle_menu() 
            
            self.fetch_btn.setEnabled(True) 
            self.update_button_text()

            last_video = app_config.get("last_video_format")
            idx = self.quality_combo.findData(last_video)
            if idx < 0:
                last_audio = app_config.get("last_audio_format")
                idx = self.quality_combo.findData(last_audio)
            if idx >= 0:
                self.quality_combo.setCurrentIndex(idx)
                self.pl_quality_combo.setCurrentIndex(idx)

            return 
        
        # --- عرض بطاقة الفيديو المفرد (Single Video View) ---
        self.content_layout.setCurrentWidget(self.single_preview_w)
        self.current_url = info.get('webpage_url', self.url_input.text())
        self.current_title = info.get('title', 'Unknown Video')
        self.video_language = info.get('language')
        self.fetch_btn.setEnabled(True)
        
        # 1. العنوان واسم القناة والمشاهدات والتاريخ
        self.video_title_label.setText(self.current_title)
        
        uploader = info.get('uploader') or info.get('channel') or ''
        if uploader:
            self.video_channel_label.setText(f"📺 {uploader}")
            self.video_channel_label.show()
        else:
            self.video_channel_label.hide()
            
        views_count = info.get('view_count')
        upload_date = info.get('upload_date')
        timestamp = info.get('timestamp')
        
        views_str = format_views(views_count, strings.is_ar)
        date_str = format_upload_date(upload_date, timestamp, strings.is_ar)
        
        stats_parts = [p for p in [views_str, date_str] if p]
        if stats_parts:
            self.video_stats_label.setText(" • ".join(stats_parts))
            self.video_stats_label.show()
        else:
            self.video_stats_label.hide()

        # 2. بادج مدة الفيديو
        raw_duration = info.get('duration')
        duration_sec = None
        if raw_duration is not None:
            try:
                duration_sec = int(float(raw_duration))
            except (ValueError, TypeError):
                duration_sec = None

        if duration_sec is None or duration_sec <= 0:
            if info.get('is_live') or duration_sec is None:
                self.video_duration_label.setText("🔴 بث مباشر (Live)" if strings.is_ar else "🔴 Live Stream")
                self.video_duration_label.show()
            else:
                self.video_duration_label.hide()
        else:
            mins, secs = divmod(duration_sec, 60)
            hours, mins = divmod(mins, 60)
            dur_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
            self.video_duration_label.setText(f"⏱️ {dur_str}")
            self.video_duration_label.show()
            
        # 3. جلب الصورة المصغرة في الخلفية بشكل متوازي
        if app_config.get("show_thumbnails", True):
            self.thumbnail_label.show() 
            thumb_url = info.get('thumbnail')
            if not thumb_url and info.get('thumbnails'):
                last_thumb = info['thumbnails'][-1]
                thumb_url = last_thumb.get('url') if isinstance(last_thumb, dict) else str(last_thumb)
            video_id = info.get('id')
            if thumb_url or video_id:
                self.single_thumb_worker = ThumbnailWorker(0, thumb_url=thumb_url, video_id=video_id)
                self.single_thumb_worker.thumb_loaded.connect(self.update_single_thumb)
                self.single_thumb_worker.start()
        else:
            self.thumbnail_label.hide() 
            
        self.video_options = []
        self.audio_options = []

        self.current_subtitles = info.get('subtitles', {})
        self.current_auto_subs = info.get('automatic_captions', {})
        self.build_subtitle_menu() 

        formats_list = info.get('formats', [])
        if not isinstance(formats_list, list):
            formats_list = []

        # 4. استخراج حجم أفضل صوت متاح لدمجه بحجم الفيديو
        raw_audio_formats = [f for f in formats_list if isinstance(f, dict) and f.get('vcodec') == 'none' and f.get('acodec') != 'none']
        best_audio_size = 0
        if raw_audio_formats:
            best_audio = raw_audio_formats[-1]
            raw_audio_size = best_audio.get('filesize', 0) or best_audio.get('filesize_approx', 0) or 0
            try:
                best_audio_size = float(raw_audio_size)
            except (ValueError, TypeError):
                best_audio_size = 0

        # 5. استخراج وترتيب خيارات الفيديو (Video Streams)
        resolutions = {}
        op = "<=" if app_config.get("allow_downgrade", True) else "=" 
        
        for f in formats_list:
            if not isinstance(f, dict):
                continue
            if f.get('vcodec') != 'none':
                height = f.get('height')
                if not height: continue
                try:
                    height = int(height)
                except (ValueError, TypeError):
                    continue
                res = f"{height}p"
                v_size = f.get('filesize', 0) or f.get('filesize_approx', 0) or 0
                try:
                    v_size = float(v_size)
                except (ValueError, TypeError):
                    v_size = 0
                total_size = v_size + best_audio_size if f.get('acodec') == 'none' and v_size > 0 else v_size
                if res not in resolutions or total_size > resolutions[res]['size']:
                    resolutions[res] = {'format_id': f"bestvideo[height{op}{height}]+bestaudio/best", 'size': total_size, 'ext': 'mp4'}

        sorted_res = sorted(resolutions.items(), key=lambda x: int(x[0].replace('p', '')), reverse=True)

        def get_video_desc(res):
            try:
                h = int(res.replace('p', ''))
                if h >= 2160: return "🎬 2160p (4K UHD)"
                elif h >= 1440: return "🎬 1440p (2K QHD)"
                elif h >= 1080: return "🎬 1080p - Full HD"
                elif h >= 720: return "🎬 720p - High (HD)"
                elif h >= 480: return "🎬 480p - Standard (SD)"
                elif h >= 360: return "🎬 360p - Medium"
                elif h >= 240: return "🎬 240p - Low"
                elif h >= 144: return "🎬 144p - Very Low"
                else: return f"🎬 {res}"
            except Exception:
                return f"🎬 {res}"

        for res, data in sorted_res:
            size_mb = data['size'] / (1024 * 1024)
            size_txt = f"{size_mb:.1f} MB" if size_mb > 0 else ""
            desc = get_video_desc(res)
            label = f"{desc} - {size_txt}" if size_txt else desc
            self.video_options.append((label, data['format_id']))

        if not self.video_options and (info.get('vcodec') != 'none' or not formats_list):
            self.video_options.append(("🎬 " + ("أفضل جودة فيديو" if strings.is_ar else "Best Video Quality"), "best"))

        # 6. استخراج وترتيب خيارات الصوت الحقيقي (Native Audio Streams) كما في الصورة 3
        self.audio_options = []
        seen_audio_keys = set()
        extracted_audio = []

        for f in raw_audio_formats:
            ext = (f.get('ext') or 'm4a').upper()
            abr = int(f.get('abr') or f.get('tbr') or 0)
            if abr == 0:
                continue
            key = (ext, abr)
            if key in seen_audio_keys:
                continue
            seen_audio_keys.add(key)
            
            size_bytes = f.get('filesize', 0) or f.get('filesize_approx', 0) or 0
            if not size_bytes and duration_sec and duration_sec > 0:
                size_bytes = (abr * 1000 * duration_sec) / 8
            
            try:
                size_mb = float(size_bytes) / (1024 * 1024)
            except Exception:
                size_mb = 0
                
            size_txt = f"{size_mb:.1f} MB" if size_mb > 0 else ""
            label = f"🎵 {ext} ({abr}kbps)" + (f" - {size_txt}" if size_txt else "")
            fid = f"audio-direct:{f.get('format_id')}"
            extracted_audio.append((label, fid, abr))

        # ترتيب الصوت تنازلياً حسب البت ريت (Bitrate)
        extracted_audio.sort(key=lambda x: x[2], reverse=True)
        for label, fid, _ in extracted_audio:
            self.audio_options.append((label, fid))

        if not self.audio_options and raw_audio_formats:
            self.audio_options.append(("🎵 " + ("أفضل جودة صوت متاحة" if strings.is_ar else "Best Audio Quality"), "bestaudio/best"))
        
        self.update_quality_options() 
        self.master_add_btn.setEnabled(True)
        self.update_button_text()

    def update_playlist_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            if index < len(getattr(self, 'entries_checkboxes', [])):
                chk = self.entries_checkboxes[index]
                label = chk.property("img_label")
                if label:
                    label.setPixmap(pixmap.scaled(60, 36, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        if not hasattr(self, 'playlist_thumbs_data'): self.playlist_thumbs_data = {}
        self.playlist_thumbs_data[index] = data 

    def update_single_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data): 
            self.thumbnail_label.setPixmap(pixmap)
        self.single_thumb_data = data

    def update_quality_options(self):
        for combo in [self.quality_combo, self.pl_quality_combo]:
            combo.blockSignals(True)
            combo.clear()
            
            # Add video options
            for label, data in self.video_options:
                combo.addItem(label, data)
                
            # Add separator if both exist
            if self.video_options and self.audio_options:
                combo.insertSeparator(combo.count())
                
            # Add audio options
            for label, data in self.audio_options:
                combo.addItem(label, data)
                
            combo.blockSignals(False)
            
        self.on_quality_changed()
    
    def on_pl_quality_changed(self):
        idx = self.pl_quality_combo.currentIndex()
        if idx >= 0:
            self.quality_combo.blockSignals(True)
            self.quality_combo.setCurrentIndex(idx)
            self.quality_combo.blockSignals(False)

    def update_button_text(self):
        if self.quality_combo.currentIndex() >= 0:
            self.master_add_btn.setEnabled(True)
            self.pl_add_btn.setEnabled(True)
            self.master_add_btn.setText(strings.BTN_DOWNLOAD)
            self.pl_add_btn.setText(strings.BTN_DOWNLOAD)
        else:
            self.master_add_btn.setEnabled(False)
            self.pl_add_btn.setEnabled(False)

    def add_to_queue(self):
        subs_only = False
        is_playlist = (self.content_layout.currentWidget() == self.playlist_layout_w)
        active_combo = self.pl_quality_combo if is_playlist else self.quality_combo
        format_id = active_combo.currentData()
        if not format_id:
            return

        if format_id != "best":
            is_audio = isinstance(format_id, str) and (
                format_id.startswith("audio:") or 
                format_id.startswith("audio-direct:") or 
                format_id.startswith("m4a-") or 
                format_id.startswith("mp3-")
            )
            if is_audio:
                app_config["last_audio_format"] = format_id
            else:
                app_config["last_video_format"] = format_id
                
        app_config["last_sub_state"] = self.sub_check.isChecked()
        from utils.settings import save_settings
        save_settings(app_config)

        if self.sub_check.isChecked():
            lang_code = self.sub_combo.currentData()
            sub_langs = [lang_code] if lang_code else ["en", "ar"]
        else:
            sub_langs = []

        embed_subs = app_config.get("embed_subs_default", True)

        custom_save_dir = None
        if app_config.get("save_mode") == "ask":
            custom_save_dir = QFileDialog.getExistingDirectory(self, "Select Download Folder")
            if not custom_save_dir: return 

        if self.main_app and hasattr(self.main_app, 'tab_queue'):
            if is_playlist:
                for i, chk in enumerate(getattr(self, 'entries_checkboxes', [])):
                    if chk.isChecked():
                        url = chk.property("url")
                        title = chk.property("title")
                        thumb_data = self.playlist_thumbs_data.get(i) if hasattr(self, 'playlist_thumbs_data') else None
                        self.main_app.tab_queue._create_and_insert_queue_item(url, title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir)
            else:
                if not self.current_url: return
                thumb_data = getattr(self, 'single_thumb_data', None)
                self.main_app.tab_queue._create_and_insert_queue_item(self.current_url, self.current_title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir)
                self.single_thumb_data = None

        self.url_input.clear()                   
        self.content_layout.setCurrentWidget(self.placeholder_widget)
        self.master_add_btn.setEnabled(False)    
        if self.main_app and hasattr(self.main_app, 'switch_tab'):
            self.main_app.switch_tab(1)
        
    def build_subtitle_menu(self):
        self.sub_combo.clear()
        if not (self.current_subtitles or self.current_auto_subs):
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)
            self.sub_combo.hide()
            return
            
        self.sub_check.setEnabled(True)
        
        manual_langs = sorted(list(self.current_subtitles.keys())) if self.current_subtitles else []
        auto_langs = sorted(list(self.current_auto_subs.keys())) if self.current_auto_subs else []
        
        def get_lang_name(code):
            names = {
                "ar": "العربية (Arabic)" if strings.is_ar else "Arabic",
                "en": "English",
                "fr": "Français (French)" if strings.is_ar else "French",
                "es": "Español (Spanish)" if strings.is_ar else "Spanish",
                "de": "Deutsch (German)" if strings.is_ar else "German",
                "tr": "Türkçe (Turkish)" if strings.is_ar else "Turkish",
                "ru": "Русский (Russian)" if strings.is_ar else "Russian"
            }
            base = code.split("-")[0].lower()
            return names.get(base, code.upper())
            
        for lang in manual_langs:
            name = get_lang_name(lang)
            self.sub_combo.addItem(f"🌐 {name} (Manual)", lang)
            
        if manual_langs and auto_langs:
            self.sub_combo.insertSeparator(self.sub_combo.count())
            
        for lang in auto_langs:
            if lang in manual_langs: continue
            name = get_lang_name(lang)
            self.sub_combo.addItem(f"🌐 {name} (Auto)", lang)
            
        primary = app_config.get("primary_sub_lang", "ar")
        secondary = app_config.get("secondary_sub_lang", "en")
        
        found_idx = -1
        for i in range(self.sub_combo.count()):
            code = self.sub_combo.itemData(i)
            if code == primary:
                found_idx = i
                break
                
        if found_idx == -1:
            for i in range(self.sub_combo.count()):
                code = self.sub_combo.itemData(i)
                if code == secondary:
                    found_idx = i
                    break
                    
        if found_idx == -1 and self.sub_combo.count() > 0:
            found_idx = 0
            
        if found_idx >= 0:
            self.sub_combo.setCurrentIndex(found_idx)
            
        self.toggle_sub_options()

    def on_quality_changed(self):
        self.update_button_text()
