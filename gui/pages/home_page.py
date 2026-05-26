"""
Home Page — URL input, video/playlist preview, quality selection, and download button.
"""
import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QComboBox, QScrollArea, 
                             QCheckBox, QApplication, QDialog, 
                             QStackedLayout, QMessageBox, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QTextCursor, QTextBlockFormat

from core.ffmpeg_handler import InfoFetcher, ThumbnailWorker, BatchTitleFetcher
from data.settings import app_config
from utils import helpers


class HomePage(QWidget):
    # Signals to communicate with main_window
    add_to_queue_signal = pyqtSignal(list)  # list of dicts with download info
    switch_to_downloads_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_url = ""
        self.current_title = ""
        self.video_options = []
        self.audio_options = []
        self.current_subtitles = {}
        self.current_auto_subs = {}
        self.entries_checkboxes = []
        self.playlist_thumbs_data = {}
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(15)

        # Dynamic asset paths
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        icon_path = os.path.join(assets_dir, "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(assets_dir, "logo.png")

        # URL Input Bar
        url_hbox = QHBoxLayout()
        url_hbox.setSpacing(10)
        self.paste_btn = QPushButton()
        self.paste_btn.setIcon(helpers.get_theme_icon("clipboard.svg"))
        self.paste_btn.setIconSize(QSize(18, 18))
        self.paste_btn.setFixedSize(45, 45)
        self.paste_btn.setToolTip("Paste URL")
        self.paste_btn.clicked.connect(lambda: self.url_input.setText(QApplication.clipboard().text()))
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("UrlInput")
        self.url_input.setPlaceholderText(helpers.PLACEHOLDER_URL)
        self.url_input.setClearButtonEnabled(True) 
        self.url_input.setFixedHeight(45)
        self.url_input.returnPressed.connect(self.fetch_video_info)
        self.url_input.textChanged.connect(self.on_url_changed) 
        
        self.fetch_btn = QPushButton()
        self.fetch_btn.setIcon(helpers.get_theme_icon("search-lens.svg"))
        self.fetch_btn.setIconSize(QSize(18, 18))
        self.fetch_btn.setFixedSize(45, 45)
        self.fetch_btn.setToolTip(helpers.BTN_CHECK_LINK)
        self.fetch_btn.setObjectName("primary")
        self.fetch_btn.clicked.connect(self.fetch_video_info)

        self.batch_btn = QPushButton()
        self.batch_btn.setIcon(helpers.get_theme_icon("package.svg"))
        self.batch_btn.setIconSize(QSize(18, 18))
        self.batch_btn.setFixedSize(45, 45)
        self.batch_btn.setToolTip(helpers.BTN_BATCH)
        self.batch_btn.clicked.connect(self.open_batch_dialog)
        
        url_hbox.addWidget(self.paste_btn)
        url_hbox.addWidget(self.url_input, stretch=1)
        url_hbox.addWidget(self.fetch_btn)
        url_hbox.addWidget(self.batch_btn) 
        layout.addLayout(url_hbox)

        # Preview Galleries
        self.gallery_stacked = QWidget() 
        self.gallery_layout = QStackedLayout(self.gallery_stacked)
        
        # Glow Card container for single video preview
        self.single_preview_card = QFrame()
        self.single_preview_card.setObjectName("GlowCard")
        single_card_layout = QVBoxLayout(self.single_preview_card)
        single_card_layout.setContentsMargins(15, 15, 15, 15)
        single_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(426, 240) 
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("border-radius: 12px; background-color: rgba(0,0,0,0.15);")
        
        self.video_title_label = QLabel()
        self.video_title_label.setWordWrap(True)
        self.video_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_title_label.setObjectName("heading")
        self.video_title_label.setStyleSheet("font-size: 12pt; font-weight: 700; margin-top: 10px;")
        
        self.video_duration_label = QLabel()
        self.video_duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_duration_label.setObjectName("hint")
        
        single_card_layout.addWidget(self.thumbnail_label)
        single_card_layout.addWidget(self.video_title_label)
        single_card_layout.addWidget(self.video_duration_label)
        
        self.single_preview_w = QWidget()
        single_outer_layout = QVBoxLayout(self.single_preview_w)
        single_outer_layout.setContentsMargins(0, 0, 0, 0)
        single_outer_layout.addWidget(self.single_preview_card)
        self.gallery_layout.addWidget(self.single_preview_w)
        
        # Playlist item layout
        self.playlist_list_w = QScrollArea()
        self.playlist_list_w.setWidgetResizable(True)
        self.playlist_content_w = QWidget()
        self.playlist_v_layout = QVBoxLayout(self.playlist_content_w)
        self.playlist_list_w.setWidget(self.playlist_content_w)
        
        self.playlist_layout = QVBoxLayout()
        self.playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_bar = QHBoxLayout()
        
        self.master_checkbox = QCheckBox(helpers.CHK_SELECT_ALL)
        self.master_checkbox.setChecked(True)
        self.master_checkbox.clicked.connect(lambda: [c.setChecked(self.master_checkbox.isChecked()) for c in getattr(self, 'entries_checkboxes', [])])
        
        playlist_bar.addWidget(self.master_checkbox)
        playlist_bar.addStretch()
        
        self.playlist_layout.addLayout(playlist_bar)
        self.playlist_layout.addWidget(self.playlist_list_w)
        
        self.playlist_layout_w = QWidget()
        self.playlist_layout_w.setLayout(self.playlist_layout)
        self.gallery_layout.addWidget(self.playlist_layout_w)

        # Placeholder widget when empty
        self.placeholder_card = QFrame()
        self.placeholder_card.setObjectName("GlowCard")
        placeholder_layout = QVBoxLayout(self.placeholder_card)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.ph_icon = QLabel()
        self.ph_icon.setFixedSize(80, 80)
        self.ph_icon.setPixmap(helpers.get_theme_icon("search-lens.svg", 80).pixmap(80, 80))
        
        self.ph_title = QLabel("في انتظار الرابط..." if helpers.is_ar else "Waiting for Link")
        self.ph_title.setObjectName("heading")
        self.ph_title.setStyleSheet("font-size: 16pt; font-weight: 800; color: #7c6af7;")
        
        self.ph_desc = QLabel(helpers.PLACEHOLDER_URL)
        self.ph_desc.setObjectName("hint")
        self.ph_desc.setStyleSheet("font-size: 11pt;")
        
        placeholder_layout.addWidget(self.ph_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.ph_title, alignment=Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.ph_desc, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.placeholder_widget = QWidget()
        ph_outer_layout = QVBoxLayout(self.placeholder_widget)
        ph_outer_layout.setContentsMargins(0, 0, 0, 0)
        ph_outer_layout.addWidget(self.placeholder_card)
        
        layout.addWidget(self.placeholder_widget, stretch=1)
        layout.addWidget(self.gallery_stacked, stretch=1)
        self.gallery_stacked.hide()

        # Selection Options Card
        self.options_card = QFrame()
        self.options_card.setObjectName("GlowCard")
        options_layout = QVBoxLayout(self.options_card)
        options_layout.setContentsMargins(15, 12, 15, 12)
        options_layout.setSpacing(8)
        
        combos_hbox = QHBoxLayout()
        combos_hbox.setSpacing(15)
        
        self.quality_label = QLabel(helpers.LBL_QUALITY)
        self.quality_combo = QComboBox()
        self.quality_combo.currentIndexChanged.connect(self.update_quality_desc_and_button)
        
        combos_hbox.addWidget(self.quality_label)
        combos_hbox.addWidget(self.quality_combo, stretch=1)
        options_layout.addLayout(combos_hbox)

        self.quality_desc_label = QLabel()
        self.quality_desc_label.setObjectName("hint")
        self.quality_desc_label.setStyleSheet("font-size: 9.5pt; color: #a0a0c0; padding-left: 65px;")
        options_layout.addWidget(self.quality_desc_label)

        # Simplified Subtitle Row
        self.sub_check = QCheckBox("الترجمة" if helpers.is_ar else "Sub/CC")
        self.sub_check.setEnabled(False)
        
        self.playlist_sub_info = QLabel()
        self.playlist_sub_info.setPixmap(helpers.get_theme_icon("info.svg", 16).pixmap(16, 16))
        self.playlist_sub_info.setToolTip("إذا كانت الترجمة متاحة لأي فيديو داخل قائمة التشغيل، سيتم تحميلها تلقائيًا." if helpers.is_ar else "If subtitles are available for any video within the playlist, they will be automatically loaded.")
        self.playlist_sub_info.hide()

        self.sub_lang_combo = QComboBox()
        self.sub_lang_combo.hide()

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(10)
        sub_layout.addWidget(self.sub_check)
        sub_layout.addWidget(self.playlist_sub_info)
        sub_layout.addWidget(self.sub_lang_combo)
        sub_layout.addStretch() 
        options_layout.addLayout(sub_layout) 
        
        self.sub_check.stateChanged.connect(self.toggle_sub_options)

        layout.addWidget(self.options_card)

        self.master_add_btn = QPushButton(helpers.BTN_DOWNLOAD)
        self.master_add_btn.setFixedHeight(45)
        self.master_add_btn.setEnabled(False)
        self.master_add_btn.setObjectName("primary")
        self.master_add_btn.clicked.connect(self.add_to_queue)
        layout.addWidget(self.master_add_btn)

    # ──────────────────────────────────────────────
    #  URL & Fetch Logic
    # ──────────────────────────────────────────────

    def on_url_changed(self, text):
        self.fetch_btn.setEnabled(True) 
        if not text.strip():
            self.gallery_stacked.hide()
            self.placeholder_widget.show() 
            self.master_add_btn.setEnabled(False)
            self.master_add_btn.setText(helpers.BTN_DOWNLOAD) 
            self.quality_combo.clear()
            self.quality_desc_label.clear()
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)
            self.playlist_sub_info.hide()
            self.sub_lang_combo.clear()
            self.sub_lang_combo.hide()

    def fetch_video_info(self):
        url = self.url_input.text().strip()
        if not url: return

        self.fetch_btn.setEnabled(False)
        self.placeholder_widget.hide() 
        self.gallery_stacked.show() 

        is_playlist = "list=" in url
        
        # Unlock or Lock Subtitles dropdown for Playlists
        self.sub_lang_combo.setEnabled(not is_playlist)
        if is_playlist:
            self.sub_lang_combo.setToolTip(helpers.SUB_LOCKED_TIP)
        else:
            self.sub_lang_combo.setToolTip("")

        if is_playlist:
            self.gallery_layout.setCurrentWidget(self.playlist_layout_w)
            while self.playlist_v_layout.count():
                item = self.playlist_v_layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
            
            self.entries_checkboxes = [] 
            loading_label = QLabel(helpers.LBL_FETCHING)
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_label.setObjectName("hint")
            self.playlist_v_layout.addWidget(loading_label)
        else:
            self.gallery_layout.setCurrentWidget(self.single_preview_w) 
            if app_config.get("show_thumbnails", True):
                self.thumbnail_label.show()
                self.thumbnail_label.clear()
                self.thumbnail_label.setText("...")
            else:
                self.thumbnail_label.hide() 
            self.video_title_label.setText("...")
            self.video_duration_label.setText("...")

        if hasattr(self, 'fetch_thread') and self.fetch_thread.isRunning():
            try: self.fetch_thread.info_received.disconnect()
            except: pass
            try: self.fetch_thread.error_received.disconnect()
            except: pass 

        self.fetch_thread = InfoFetcher(url, fetch_playlist=is_playlist)
        self.fetch_thread.info_received.connect(self.on_info_loaded)
        self.fetch_thread.error_received.connect(self.on_fetch_error) 
        self.fetch_thread.start()

    def on_fetch_error(self, error_msg):
        self.gallery_stacked.show()
        self.gallery_layout.setCurrentWidget(self.single_preview_w)
        self.thumbnail_label.setText("❌ Error")
        self.video_title_label.setText("Error")
        self.fetch_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", str(error_msg))

    def on_info_loaded(self, info, thumb_bytes):
        self.gallery_stacked.show()
        
        if info.get('_type') in ['playlist', 'multi_video'] or 'entries' in info:
            self.gallery_layout.setCurrentWidget(self.playlist_layout_w)

            while self.playlist_v_layout.count():
                item = self.playlist_v_layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
                
            self.entries_checkboxes = []
            self.playlist_thumbs_data = {}
            
            valid_index = 1 
            for entry in info.get('entries', []):
                if not entry: continue
                title = entry.get('title', '')
                if not title or "[Private video]" in title or "[Deleted video]" in title: continue

                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(15, 10, 15, 10) 
                item_layout.setSpacing(20)
                
                url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                video_id = entry.get('id')
                
                chk = QCheckBox(f"{valid_index}. {title}")
                chk.setChecked(True)
                chk.setProperty("url", url)
                chk.setProperty("title", title)
                
                if app_config.get("show_thumbnails", True):
                    img_label = QLabel()
                    img_label.setFixedSize(60, 34)
                    item_layout.addWidget(img_label)
                    chk.setProperty("img_label", img_label)
                    
                    if video_id:
                        worker = ThumbnailWorker(len(self.entries_checkboxes), video_id)
                        worker.thumb_loaded.connect(self.update_playlist_thumb)
                        worker.start()
                        if not hasattr(self, 'thumb_workers'): self.thumb_workers = []
                        self.thumb_workers.append(worker)

                item_layout.addWidget(chk)
                item_layout.addStretch() 
                self.playlist_v_layout.addWidget(item_widget)
                self.entries_checkboxes.append(chk)
                valid_index += 1 
            
            op = "<=" if app_config.get("allow_downgrade", True) else "="
            
            self.video_options = [
                ("2160p (4K)", f"bestvideo[height{op}2160]+bestaudio/best", helpers.extract_desc(helpers.Q_4K, "2160p")),
                ("1440p (2K)", f"bestvideo[height{op}1440]+bestaudio/best", helpers.extract_desc(helpers.Q_2K, "1440p")),
                ("1080p (Full HD)", f"bestvideo[height{op}1080]+bestaudio/best", helpers.extract_desc(helpers.Q_1080, "1080p")),
                ("720p (HD)", f"bestvideo[height{op}720]+bestaudio/best", helpers.extract_desc(helpers.Q_720, "720p")),
                ("480p", f"bestvideo[height{op}480]+bestaudio/best", helpers.extract_desc(helpers.Q_480, "480p")),
                ("360p", f"bestvideo[height{op}360]+bestaudio/best", helpers.extract_desc(helpers.Q_360, "360p")),
                ("240p", f"bestvideo[height{op}240]+bestaudio/best", helpers.extract_desc(helpers.Q_240, "240p")),
                ("144p", f"bestvideo[height{op}144]+bestaudio/best", helpers.extract_desc(helpers.Q_144, "144p"))
            ]
            self.audio_options = [
                ("M4A (128kbps)", "m4a-128", helpers.extract_desc(helpers.A_M4A, "M4A")),
                ("MP3 (70kbps)", "mp3-70", helpers.extract_desc(helpers.A_MP3_70, "70kbps")),
                ("MP3 (128kbps)", "mp3-128", helpers.extract_desc(helpers.A_MP3_128, "128kbps")),
                ("MP3 (160kbps)", "mp3-160", helpers.extract_desc(helpers.A_MP3_160, "160kbps")),
                ("MP3 (320kbps)", "mp3-320", helpers.extract_desc(helpers.A_MP3_320, "320kbps"))
            ]
            self.update_quality_options()
            
            self.original_language = info.get('language')
            self.current_subtitles = {'ar': [{'name': 'Arabic'}], 'en': [{'name': 'English'}], 'fr': [{'name': 'French'}]}
            self.current_auto_subs = {}
            self.build_subtitle_menu() 
            
            self.sub_check.setEnabled(True)
            self.playlist_sub_info.show() # Exclamation/info icon next to Sub/CC for playlists
            self.toggle_sub_options()
            
            self.master_add_btn.setEnabled(False) # Keep disabled on load (Safety Logic)
            self.fetch_btn.setEnabled(True) 
            
            self.quality_combo.setCurrentIndex(0) # Enforce "Choose Quality" default selection
            if hasattr(self, 'sub_check') and self.sub_check.isEnabled():
                self.sub_check.setChecked(app_config.get("last_sub_state", False))
            return 
        
        self.gallery_layout.setCurrentWidget(self.single_preview_w)
        self.current_url = info.get('webpage_url', self.url_input.text())
        self.current_title = info.get('title', 'Unknown Video')
        self.fetch_btn.setEnabled(True)
        
        self.video_title_label.setText(self.current_title)
        duration_sec = info.get('duration')
        if duration_sec is None:
            self.video_duration_label.setText(helpers.MSG_LIVE)
        else:
            mins, secs = divmod(duration_sec, 60)
            hours, mins = divmod(mins, 60)
            dur_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
            self.video_duration_label.setText(helpers.MSG_DURATION.format(dur_str))
            
        if app_config.get("show_thumbnails", True):
            self.thumbnail_label.show() 
            self.thumbnail_label.clear()
            video_id = info.get('id')
            if video_id:
                self.single_thumb_worker = ThumbnailWorker(0, video_id)
                self.single_thumb_worker.thumb_loaded.connect(self.update_single_thumb)
                self.single_thumb_worker.start()
        else:
            self.thumbnail_label.hide() 
            
        self.video_options = []
        self.audio_options = []

        self.original_language = info.get('language')
        self.current_subtitles = info.get('subtitles', {})
        self.current_auto_subs = info.get('automatic_captions', {})
        self.build_subtitle_menu() 

        audio_formats = [f for f in info.get('formats', []) if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
        best_audio_size = 0
        if audio_formats:
            best_audio = audio_formats[-1]
            best_audio_size = best_audio.get('filesize', 0) or best_audio.get('filesize_approx', 0) or 0

        resolutions = {}
        op = "<=" if app_config.get("allow_downgrade", True) else "=" 
        
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none':
                height = f.get('height')
                if not height: continue
                res = f"{height}p"
                v_size = f.get('filesize', 0) or f.get('filesize_approx', 0) or 0
                total_size = v_size + best_audio_size if f.get('acodec') == 'none' and v_size > 0 else v_size
                if res not in resolutions or total_size > resolutions[res]['size']:
                    resolutions[res] = {'format_id': f"bestvideo[height{op}{height}]+bestaudio/best", 'size': total_size, 'ext': 'mp4'}

        sorted_res = sorted(resolutions.items(), key=lambda x: int(x[0].replace('p', '')), reverse=True)

        def get_video_desc_template(res):
            try:
                h = int(res.replace('p', ''))
                if h > 1440: return helpers.Q_4K
                elif h > 1080: return helpers.Q_2K
                elif h > 720: return helpers.Q_1080  
                elif h > 480: return helpers.Q_720   
                elif h > 360: return helpers.Q_480   
                elif h > 240: return helpers.Q_360
                elif h > 144: return helpers.Q_240
                else: return helpers.Q_144
            except:
                return "🎬 Quality ({})"

        for res, data in sorted_res:
            size_mb = data['size'] / (1024 * 1024)
            size_txt = f"{size_mb:.1f} MB" if size_mb > 0 else ""
            desc = helpers.extract_desc(get_video_desc_template(res), res)
            self.video_options.append((res, data['format_id'], desc, size_txt))

        self.audio_options = []
        def calc_size(kbps):
            size_mb = (kbps * duration_sec) / 8 / 1024 if duration_sec else 0
            return f"{size_mb:.1f} MB" if size_mb > 0 else ""

        self.audio_options.append(("M4A (128kbps)", "m4a-128", helpers.extract_desc(helpers.A_M4A, "M4A"), calc_size(128)))
        self.audio_options.append(("MP3 (70kbps)", "mp3-70", helpers.extract_desc(helpers.A_MP3_70, "70kbps"), calc_size(70)))
        self.audio_options.append(("MP3 (128kbps)", "mp3-128", helpers.extract_desc(helpers.A_MP3_128, "128kbps"), calc_size(128)))
        self.audio_options.append(("MP3 (160kbps)", "mp3-160", helpers.extract_desc(helpers.A_MP3_160, "160kbps"), calc_size(160)))
        self.audio_options.append(("MP3 (320kbps)", "mp3-320", helpers.extract_desc(helpers.A_MP3_320, "320kbps"), calc_size(320)))
        
        self.update_quality_options()
        
    def update_playlist_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            if index < len(getattr(self, 'entries_checkboxes', [])):
                chk = self.entries_checkboxes[index]
                label = chk.property("img_label")
                if label:
                    label.setPixmap(pixmap.scaled(60, 34, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        if not hasattr(self, 'playlist_thumbs_data'): self.playlist_thumbs_data = {}
        self.playlist_thumbs_data[index] = data 

    def update_single_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.thumbnail_label.setPixmap(pixmap.scaled(426, 240, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.single_thumb_data = data

    # ──────────────────────────────────────────────
    #  Quality Options & Safety Logic
    # ──────────────────────────────────────────────

    def update_quality_options(self):
        self.quality_combo.clear()
        
        # 1. Add Default Choose Quality option at index 0 (Safety Logic)
        choose_text = "اختر الجودة..." if helpers.is_ar else "Choose Quality..."
        self.quality_combo.addItem(choose_text, None)
        
        # 2. Add Video Options (if any)
        if self.video_options:
            for item in self.video_options:
                res_text = item[0]
                format_id = item[1]
                desc = item[2]
                size_txt = item[3] if len(item) > 3 else ""
                
                display_text = f"🎬  {res_text}"
                if size_txt:
                    display_text += f" ({size_txt})"
                    
                self.quality_combo.addItem(display_text, {
                    'format_id': format_id,
                    'type': 'video',
                    'desc': desc,
                    'size_txt': size_txt
                })
                
        # 3. Add Separator (if we have both video and audio options)
        if self.video_options and self.audio_options:
            self.quality_combo.insertSeparator(self.quality_combo.count())
            
        # 4. Add Audio Options (if any)
        if self.audio_options:
            for item in self.audio_options:
                res_text = item[0]
                format_id = item[1]
                desc = item[2]
                size_txt = item[3] if len(item) > 3 else ""
                
                display_text = f"🎵  {res_text}"
                if size_txt:
                    display_text += f" ({size_txt})"
                    
                self.quality_combo.addItem(display_text, {
                    'format_id': format_id,
                    'type': 'audio',
                    'desc': desc,
                    'size_txt': size_txt
                })
                
        self.quality_combo.setCurrentIndex(0) # Choose Quality by default
        self.update_quality_desc_and_button()

    def update_quality_desc_and_button(self):
        idx = self.quality_combo.currentIndex()
        if idx <= 0: # Choose Quality or separator
            self.master_add_btn.setEnabled(False)
            self.master_add_btn.setText(helpers.BTN_DOWNLOAD)
            self.quality_desc_label.setText("")
            return
            
        data = self.quality_combo.currentData()
        if not data or not isinstance(data, dict):
            self.master_add_btn.setEnabled(False)
            self.master_add_btn.setText(helpers.BTN_DOWNLOAD)
            self.quality_desc_label.setText("")
            return
            
        self.master_add_btn.setEnabled(True)
        size_txt = data.get('size_txt', '')
        if size_txt:
            self.master_add_btn.setText(helpers.BTN_DOWNLOAD_SIZE.format(size_txt))
        else:
            self.master_add_btn.setText(helpers.BTN_DOWNLOAD)
            
        desc = data.get('desc', '')
        if desc:
            self.quality_desc_label.setText(f"ℹ️  {desc}")
        else:
            self.quality_desc_label.setText("")

    def toggle_sub_options(self):
        if self.sub_check.isChecked():
            self.sub_lang_combo.show()
        else:
            self.sub_lang_combo.hide()
        self.update_quality_desc_and_button()

    def build_subtitle_menu(self):
        self.sub_lang_combo.clear()
        
        # 1. Gather all official (manual) subtitles
        top_subs = {}
        for lang_code, lang_info in self.current_subtitles.items():
            lang_name = lang_info[0].get('name', lang_code) if lang_info else lang_code
            suffix = " (الأصلية)" if helpers.is_ar else " (Official)"
            top_subs[lang_code] = f"{lang_name}{suffix}"
            
        # 2. Gather remaining auto captions
        bottom_subs = {}
        for lang_code, lang_info in self.current_auto_subs.items():
            lang_name = lang_info[0].get('name', lang_code) if lang_info else lang_code
            suffix = " (تلقائي)" if helpers.is_ar else " (Auto)"
            bottom_subs[lang_code] = f"{lang_name}{suffix}"

        # 3. Apply elevation logic: if no official subtitles exist, look for original language in auto captions
        if not top_subs and bottom_subs:
            orig_lang = getattr(self, 'original_language', None)
            if not orig_lang and len(bottom_subs) > 0:
                # Guess original language as the first auto subtitle in the list
                orig_lang = list(bottom_subs.keys())[0]
                
            if orig_lang in bottom_subs:
                # Elevate it!
                lang_name = bottom_subs[orig_lang].split(" (")[0] # strip " (Auto)"
                suffix = " (الأصلي) (تلقائي)" if helpers.is_ar else " (Original) (Auto)"
                top_subs[orig_lang] = f"{lang_name}{suffix}"
                # Remove it from bottom list so it doesn't duplicate
                bottom_subs.pop(orig_lang, None)

        # 4. Populate the sub_lang_combo with official / elevated subtitles
        has_elements = False
        if top_subs:
            has_elements = True
            for code, name in top_subs.items():
                self.sub_lang_combo.addItem(name, code)
                
        # 5. Insert horizontal divider if we have both top and bottom items
        if top_subs and bottom_subs:
            self.sub_lang_combo.insertSeparator(self.sub_lang_combo.count())
            
        # 6. Populate bottom list of automatic translations
        if bottom_subs:
            has_elements = True
            for code, name in bottom_subs.items():
                self.sub_lang_combo.addItem(name, code)
                
        if has_elements:
            self.sub_check.setEnabled(True)
            self.sub_lang_combo.show()
            self.toggle_sub_options()
            
            # Select default primary language from config
            prim_lang = app_config.get("primary_sub_lang", "ar")
            p_idx = self.sub_lang_combo.findData(prim_lang)
            if p_idx >= 0:
                self.sub_lang_combo.setCurrentIndex(p_idx)
        else:
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)
            self.playlist_sub_info.hide()
            self.sub_lang_combo.clear()
            self.sub_lang_combo.hide()

    # ──────────────────────────────────────────────
    #  Batch Dialog
    # ──────────────────────────────────────────────

    def open_batch_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(helpers.BATCH_TITLE)
        dialog.resize(550, 400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(helpers.BATCH_DESC))
        
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False) 
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            
        save_file = os.path.join(data_dir, "batch_links.txt")
        if os.path.exists(save_file):
            with open(save_file, "r", encoding="utf-8") as f:
                text_edit.setPlainText(f.read())
                
        def on_text_changed():
            with open(save_file, "w", encoding="utf-8") as f:
                f.write(text_edit.toPlainText())
            text_edit.blockSignals(True) 
            cursor = text_edit.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            fmt = QTextBlockFormat()
            fmt.setBottomMargin(18) 
            cursor.mergeBlockFormat(fmt)
            text_edit.blockSignals(False)
            
        text_edit.textChanged.connect(on_text_changed)
        on_text_changed() 
        
        layout.addWidget(text_edit)

        process_btn = QPushButton(helpers.BATCH_BTN)
        process_btn.setObjectName("primary")
        
        def process_links():
            text = text_edit.toPlainText()
            links = [line.strip() for line in text.split('\n') if line.strip().startswith('http')]
            if not links: return
            
            text_edit.clear()
            if os.path.exists(save_file):
                try: os.remove(save_file) 
                except: pass

            dialog.accept()

            self.placeholder_widget.hide()
            self.gallery_stacked.show()
            
            fake_info = {
                '_type': 'playlist',
                'title': helpers.BATCH_FAKE_TITLE.format(len(links)),
                'entries': []
            }
            
            for i, link in enumerate(links):
                match = re.search(r"(?:v=|\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})", link)
                vid_id = match.group(1) if match else None
                
                fake_info['entries'].append({
                    'url': link,
                    'title': helpers.BATCH_FAKE_LINK.format(i+1),
                    'id': vid_id 
                })
                
            self.on_info_loaded(fake_info, b'')

            self.batch_title_thread = BatchTitleFetcher(links)
            self.batch_title_thread.title_fetched.connect(self.update_batch_title)
            self.batch_title_thread.start()

        process_btn.clicked.connect(process_links)
        layout.addWidget(process_btn)
        dialog.exec()

    def update_batch_title(self, index, real_title):
        if hasattr(self, 'entries_checkboxes') and index < len(self.entries_checkboxes):
            chk = self.entries_checkboxes[index]
            chk.setText(f"{index + 1}. {real_title}")
            chk.setProperty("title", real_title) 

    def refresh_theme_icons(self):
        self.paste_btn.setIcon(helpers.get_theme_icon("clipboard.svg"))
        self.fetch_btn.setIcon(helpers.get_theme_icon("search-lens.svg"))
        self.batch_btn.setIcon(helpers.get_theme_icon("package.svg"))
        self.ph_icon.setPixmap(helpers.get_theme_icon("search-lens.svg", 80).pixmap(80, 80))
        self.playlist_sub_info.setPixmap(helpers.get_theme_icon("info.svg", 16).pixmap(16, 16)) 

    # ──────────────────────────────────────────────
    #  Add to Queue
    # ──────────────────────────────────────────────

    def add_to_queue(self):
        data = self.quality_combo.currentData()
        if not data or not isinstance(data, dict): return
        
        format_id = data.get('format_id')
        is_video = (data.get('type') == 'video')
        if is_video:
            app_config["last_video_format"] = format_id
        else:
            app_config["last_audio_format"] = format_id
                
        app_config["last_sub_state"] = self.sub_check.isChecked()
        from data.settings import save_settings
        save_settings(app_config)

        sub_langs = []
        if self.sub_check.isChecked():
            selected_primary = self.sub_lang_combo.currentData()
            if selected_primary: sub_langs.append(selected_primary)

        # Merge subtitles directly loaded from general Appearance Settings
        embed_subs = app_config.get("embed_subs_default", True)

        from PyQt6.QtWidgets import QFileDialog
        custom_save_dir = None
        if app_config.get("save_mode") == "ask":
            custom_save_dir = QFileDialog.getExistingDirectory(self, "Select Download Folder")
            if not custom_save_dir: return 

        downloads = []
        if self.gallery_layout.currentWidget() == self.playlist_layout_w:
            for i, chk in enumerate(getattr(self, 'entries_checkboxes', [])):
                if chk.isChecked():
                    url = chk.property("url")
                    title = chk.property("title")
                    thumb_data = self.playlist_thumbs_data.get(i) if hasattr(self, 'playlist_thumbs_data') else None
                    downloads.append({
                        'url': url, 'title': title, 'thumb_data': thumb_data,
                        'format_id': format_id, 'sub_langs': sub_langs,
                        'subs_only': False, 'embed_subs': embed_subs,
                        'custom_save_dir': custom_save_dir
                    })
        else:
            if not self.current_url: return
            thumb_data = getattr(self, 'single_thumb_data', None)
            downloads.append({
                'url': self.current_url, 'title': self.current_title,
                'thumb_data': thumb_data, 'format_id': format_id,
                'sub_langs': sub_langs, 'subs_only': False,
                'embed_subs': embed_subs, 'custom_save_dir': custom_save_dir
            })
            self.single_thumb_data = None

        # Emit signal so main_window handles queue insertion
        self.add_to_queue_signal.emit(downloads)
        
        # Reset UI
        self.url_input.clear()                   
        self.gallery_stacked.hide()              
        self.master_add_btn.setEnabled(False)    
        self.master_add_btn.setText(helpers.BTN_DOWNLOAD) 
        
        # Tell main window to switch to downloads page
        self.switch_to_downloads_signal.emit()
