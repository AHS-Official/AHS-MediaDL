import os
import re
import urllib.request
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QComboBox, QScrollArea, 
                             QCheckBox, QApplication, QDialog, QStackedLayout, 
                             QMessageBox, QTextEdit, QSizePolicy, QFileDialog, QFrame)
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon

from utils import strings
from core.workers import InfoFetcher, ThumbnailWorker
from utils.settings import app_config
from gui.theme import styled, Theme

# --- كلاسات فرعية مساعدة للواجهة ---
class ResponsiveImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(150, 100)
        self.setMaximumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: transparent; border: none;")

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


class SmartTitleLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-weight: bold; margin-top: 5px;")

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self.update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elision()

    def update_elision(self):
        if not self._full_text:
            super().setText("")
            return
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width() - 10)
        super().setText(elided)


class BatchTitleFetcher(QThread):
    title_fetched = pyqtSignal(int, str)

    def __init__(self, links):
        super().__init__()
        self.links = links

    def run(self):
        for i, link in enumerate(self.links):
            match = re.search(r"(?:v=|\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})", link)
            vid_id = match.group(1) if match else None
            if vid_id:
                try:
                    api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json"
                    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        if 'title' in data:
                            self.title_fetched.emit(i, data['title'])
                except:
                    pass


class MetadataDialog(QDialog):
    def __init__(self, parent, default_title=""):
        super().__init__(parent)
        self.setWindowTitle(strings.BTN_METADATA)
        self.resize(350, 220)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(strings.LBL_META_TITLE))
        self.title_input = QLineEdit(default_title)
        layout.addWidget(self.title_input)
        
        layout.addWidget(QLabel(strings.LBL_META_ARTIST))
        self.artist_input = QLineEdit()
        layout.addWidget(self.artist_input)
        
        layout.addWidget(QLabel(strings.LBL_META_ALBUM))
        self.album_input = QLineEdit()
        layout.addWidget(self.album_input)
        
        layout.addStretch()
        save_btn = styled.primary_button(strings.BTN_SAVE_DOWNLOAD)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)
        
    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "artist": self.artist_input.text().strip(),
            "album": self.album_input.text().strip()
        }


# --- الكلاس الأساسي لتابة Home ---
class HomeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = parent  # الإشارة للملف الرئيسي main_window
        self.single_thumb_data = None
        self.custom_metadata = None
        self.current_url = ""
        self.current_title = ""
        self.video_language = None
        self.entries_checkboxes = []
        self.playlist_thumbs_data = {}
        
        self.initUI()

    def initUI(self):
        tab_add_layout = QVBoxLayout(self)
        
        # --- بار إدخال الرابط وفحصه ---
        url_hbox = QHBoxLayout()
        
        self.paste_btn = styled.primary_button("📋") 
        self.paste_btn.setFixedSize(35, 35) 
        self.paste_btn.setStyleSheet("padding: 0px; font-size: 16px;")
        self.paste_btn.setToolTip("لصق الرابط" if strings.is_ar else "Paste URL")
        self.paste_btn.clicked.connect(lambda: self.url_input.setText(QApplication.clipboard().text()))
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(strings.MSG_PLACEHOLDER_URL)
        self.url_input.setClearButtonEnabled(True) 
        self.url_input.setFixedHeight(35)
        self.url_input.returnPressed.connect(self.fetch_video_info)
        self.url_input.textChanged.connect(self.on_url_changed) 
        
        self.fetch_btn = QPushButton("🔍")
        self.fetch_btn.setFixedSize(35, 35)
        self.fetch_btn.setStyleSheet("padding: 0px; font-size: 16px;")
        self.fetch_btn.setToolTip("فحص الرابط" if strings.is_ar else "Check Link")
        self.fetch_btn.clicked.connect(self.fetch_video_info)

        self.batch_btn = styled.primary_button("📦")
        self.batch_btn.setFixedSize(35, 35)
        self.batch_btn.setStyleSheet("padding: 0px; font-size: 16px;")
        self.batch_btn.setToolTip("مجموعة روابط" if strings.is_ar else "Batch Links")
        self.batch_btn.clicked.connect(self.open_batch_dialog)
        
        url_hbox.addWidget(self.paste_btn)
        url_hbox.addWidget(self.url_input)
        url_hbox.addWidget(self.fetch_btn)
        url_hbox.addWidget(self.batch_btn) 
        tab_add_layout.addLayout(url_hbox)

        # --- منطقة المعاينة المتغيرة (Single / Playlist) ---
        self.gallery_stacked = QWidget() 
        self.gallery_layout = QStackedLayout(self.gallery_stacked)
        
        # 1. واجهة معاينة فيديو مفرد
        self.single_preview_w = QWidget()
        single_layout = QVBoxLayout(self.single_preview_w)
        single_layout.setContentsMargins(0, 5, 0, 5)
        
        self.preview_card = QFrame()
        self.preview_card.setObjectName("PreviewCard")
        self.preview_card.setFrameShape(QFrame.Shape.StyledPanel)
        
        card_layout = QVBoxLayout(self.preview_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.thumbnail_label = ResponsiveImageLabel()
        self.thumbnail_label.setObjectName("Thumbnail")
        
        self.video_title_label = SmartTitleLabel()
        self.video_duration_label = styled.secondary_label("")
        self.video_duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card_layout.addWidget(self.thumbnail_label, stretch=1) 
        card_layout.addWidget(self.video_title_label)
        card_layout.addWidget(self.video_duration_label)
        
        single_layout.addWidget(self.preview_card)
        self.gallery_layout.addWidget(self.single_preview_w)
        
        # 2. واجهة معاينة قائمة التشغيل (Playlist)
        self.playlist_list_w = QScrollArea()
        self.playlist_list_w.setWidgetResizable(True)
        self.playlist_content_w = QWidget()
        self.playlist_v_layout = QVBoxLayout(self.playlist_content_w)
        self.playlist_list_w.setWidget(self.playlist_content_w)
        
        self.playlist_layout = QVBoxLayout()
        playlist_bar = QHBoxLayout()
        
        self.master_checkbox = QCheckBox(strings.CHK_SELECT_ALL)
        self.master_checkbox.setChecked(True)
        self.master_checkbox.clicked.connect(lambda: [c.setChecked(self.master_checkbox.isChecked()) for c in getattr(self, 'entries_checkboxes', [])])
        
        playlist_bar.addWidget(self.master_checkbox)
        playlist_bar.addStretch()
        
        self.playlist_layout.addLayout(playlist_bar)
        self.playlist_layout.addWidget(self.playlist_list_w)
        
        self.playlist_layout_w = QWidget()
        self.playlist_layout_w.setLayout(self.playlist_layout)
        self.gallery_layout.addWidget(self.playlist_layout_w)

        # الـ Placeholder الافتراضي قبل وضع أي رابط
        self.placeholder_widget = QWidget()
        tab_add_layout.addWidget(self.placeholder_widget, stretch=1)
        tab_add_layout.addWidget(self.gallery_stacked, stretch=1)
        self.gallery_stacked.hide()

        # --- بطاقة خيارات التحميل والترجمة ---
        self.options_card = QFrame()
        self.options_card.setObjectName("OptionsCard")
        self.options_card.setFrameShape(QFrame.Shape.StyledPanel)
        self.options_card.hide()
        
        options_card_layout = QVBoxLayout(self.options_card)
        options_card_layout.setContentsMargins(12, 12, 12, 12)
        options_card_layout.setSpacing(10)
        
        # النوع المخفي للتوافق
        self.type_label = QLabel(strings.LBL_TYPE)
        self.type_combo = QComboBox()
        self.type_combo.addItems([strings.OPT_TYPE_VIDEO, strings.OPT_TYPE_AUDIO])
        self.type_combo.hide()
        self.type_label.hide()
        
        # حقل الجودة مباشرة بدون عنوان
        self.quality_combo = QComboBox()
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        options_card_layout.addWidget(self.quality_combo)
        
        # خيارات الترجمة
        self.sub_check = QCheckBox(strings.CHK_SUBTITLES)
        self.sub_check.setEnabled(False)
        self.sub_check.stateChanged.connect(self.toggle_sub_options)
        
        self.sub_combo = QComboBox()
        self.sub_combo.hide()
        
        self.subs_only_check = QCheckBox(strings.CHK_SUBS_ONLY)
        self.subs_only_check.hide()
        self.subs_only_check.stateChanged.connect(self.on_subs_only_changed)
        self.subs_only_check.stateChanged.connect(self.update_button_text)
        
        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.sub_check)
        sub_layout.addWidget(self.sub_combo)
        sub_layout.addWidget(self.subs_only_check)
        sub_layout.addStretch()
        options_card_layout.addLayout(sub_layout)
        
        tab_add_layout.addWidget(self.options_card)

        self.video_options = []
        self.audio_options = []

        # --- أزرار بدء التحميل والميتاداتا ---
        self.master_add_btn = styled.primary_button(strings.BTN_DOWNLOAD)
        self.master_add_btn.setFixedHeight(45)
        self.master_add_btn.setEnabled(False)
        self.master_add_btn.hide()
        self.master_add_btn.clicked.connect(self.add_to_queue)
        self.subs_only_check.stateChanged.connect(self.update_button_text)
        
        self.meta_btn = styled.ghost_button(strings.BTN_METADATA)
        self.meta_btn.setFixedHeight(45)
        self.meta_btn.hide()
        self.meta_btn.clicked.connect(self.open_metadata_dialog)

        add_btns_layout = QHBoxLayout()
        add_btns_layout.addWidget(self.meta_btn)
        add_btns_layout.addWidget(self.master_add_btn, stretch=1)
        tab_add_layout.addLayout(add_btns_layout)

    def open_batch_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(strings.APP_BATCH_TITLE)
        dialog.resize(550, 400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(strings.LBL_BATCH_DESC))
        
        from utils.helpers import get_app_dir
        save_file = os.path.join(get_app_dir(), "batch_links.txt")
        text_edit = QTextEdit()
        if os.path.exists(save_file):
            with open(save_file, "r", encoding="utf-8") as f:
                text_edit.setPlainText(f.read())
                
        def save_links_live():
            with open(save_file, "w", encoding="utf-8") as f:
                f.write(text_edit.toPlainText())
                
        text_edit.textChanged.connect(save_links_live)
        layout.addWidget(text_edit)

        process_btn = styled.primary_button(strings.BTN_BATCH_PROCESS)
        
        def process_links():
            text = text_edit.toPlainText()
            links = [line.strip() for line in text.split('\n') if line.strip().startswith('http')]
            if not links: return
            dialog.accept()

            if hasattr(self, 'placeholder_widget'): self.placeholder_widget.hide()
            self.gallery_stacked.show()
            
            fake_info = {
                '_type': 'playlist',
                'title': strings.MSG_BATCH_COLLECTION_TITLE.format(len(links)),
                'entries': []
            }
            
            for i, link in enumerate(links):
                match = re.search(r"(?:v=|\/|youtu\.be\/|shorts\/)([0-9A-Za-z_-]{11})", link)
                vid_id = match.group(1) if match else None
                fake_info['entries'].append({
                    'url': link,
                    'title': f"⏳ ({i+1})",
                    'id': vid_id 
                })
                
            self.on_info_loaded(fake_info, b'')
            self.batch_title_thread = BatchTitleFetcher(links)
            self.batch_title_thread.title_fetched.connect(self.update_batch_title)
            self.batch_title_thread.start()

        process_btn.clicked.connect(process_links)
        layout.addWidget(process_btn)
        dialog.exec()

    def toggle_sub_options(self):
        if self.sub_check.isChecked():
            if self.sub_combo.count() > 0:
                self.sub_combo.show()
            if hasattr(self, 'subs_only_check'): self.subs_only_check.show()
        else:
            self.sub_combo.hide()
            if hasattr(self, 'subs_only_check'): 
                self.subs_only_check.hide()
                self.subs_only_check.setChecked(False)
        self.update_button_text()

    def on_subs_only_changed(self):
        self.update_button_text()

    def on_url_changed(self, text):
        self.fetch_btn.setEnabled(True) 
        if not text.strip():
            self.gallery_stacked.hide()
            self.options_card.hide()
            self.master_add_btn.hide()
            self.meta_btn.hide()
            if hasattr(self, 'placeholder_widget'): self.placeholder_widget.show() 
            self.master_add_btn.setEnabled(False)
            self.master_add_btn.setText(strings.BTN_DOWNLOAD) 
            self.quality_combo.clear()
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)
            if hasattr(self, 'subs_only_check'):
                self.subs_only_check.setChecked(False)
                self.subs_only_check.hide()

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
        if hasattr(self, 'placeholder_widget'): self.placeholder_widget.hide() 
        self.gallery_stacked.show() 
        self.options_card.hide()
        self.master_add_btn.hide()
        self.meta_btn.hide() 

        is_playlist = "list=" in url
        if is_playlist:
            self.gallery_layout.setCurrentWidget(self.playlist_layout_w)
            while self.playlist_v_layout.count():
                item = self.playlist_v_layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
            
            self.entries_checkboxes = [] 
            loading_label = styled.secondary_label(strings.LBL_FETCHING)
            loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.playlist_v_layout.addWidget(loading_label)
        else:
            self.gallery_layout.setCurrentWidget(self.single_preview_w)
            self.single_thumb_data = None
            if app_config.get("show_thumbnails", True):
                self.thumbnail_label.show()
                self.thumbnail_label.clear()
                self.thumbnail_label.setText("...")
            else:
                self.thumbnail_label.hide() 
            self.video_title_label.setText("...")
            self.video_duration_label.setText("...")

        if hasattr(self, 'fetch_thread') and self.fetch_thread.isRunning():
            self.fetch_thread.cancel_fetch()
            self.fetch_thread.wait(1500)

        self.fetch_thread = InfoFetcher(url, fetch_playlist=is_playlist)
        self.fetch_thread.info_received.connect(self.on_info_loaded)
        self.fetch_thread.error_received.connect(self.on_fetch_error) 
        self.fetch_thread.start()

    def on_fetch_error(self, error_msg):
        self.gallery_stacked.show()
        self.gallery_layout.setCurrentWidget(self.single_preview_w)
        self.thumbnail_label.setText("❌ Error")
        self.video_title_label.setText("Error")
        self.options_card.hide()
        self.master_add_btn.hide()
        self.meta_btn.hide()
        self.fetch_btn.setEnabled(True)
        clean_error = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(error_msg))
        QMessageBox.critical(self, "Error", clean_error)

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
                item_widget.setObjectName("PlaylistItem")
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(5, 8, 5, 8) 
                item_layout.setSpacing(15)
                
                url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                video_id = entry.get('id')
                
                chk = QCheckBox(f"{valid_index}. {title}")
                chk.setChecked(True)
                chk.setProperty("url", url)
                chk.setProperty("title", title)
                
                if app_config.get("show_thumbnails", True):
                    img_label = QLabel()
                    img_label.setFixedSize(60, 34)
                    img_label.setObjectName("Thumbnail")
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
            
            self.type_combo.setEnabled(True) 
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
                (strings.AUDIO_M4A, "m4a-128"),
                (strings.AUDIO_MP3_70, "mp3-70"),
                (strings.AUDIO_MP3_128, "mp3-128"),
                (strings.AUDIO_MP3_160, "mp3-160"),
                (strings.AUDIO_MP3_320, "mp3-320")
            ]
            self.update_quality_options()
            self.current_subtitles = {'available': True}
            self.current_auto_subs = {}
            self.build_subtitle_menu() 
            
            self.sub_check.setEnabled(True)
            self.toggle_sub_options()
            self.options_card.show()
            self.master_add_btn.show()
            self.master_add_btn.setEnabled(True)
            self.fetch_btn.setEnabled(True) 
            self.update_button_text()

            is_video = (self.type_combo.currentText() == strings.OPT_TYPE_VIDEO)
            format_to_find = app_config.get("last_video_format") if is_video else app_config.get("last_audio_format")
            idx = self.quality_combo.findData(format_to_find)
            if idx >= 0: self.quality_combo.setCurrentIndex(idx)
            if hasattr(self, 'sub_check') and self.sub_check.isEnabled():
                self.sub_check.setChecked(app_config.get("last_sub_state", False))
            return 
        
        self.gallery_layout.setCurrentWidget(self.single_preview_w)
        self.current_url = info.get('webpage_url', self.url_input.text())
        self.current_title = info.get('title', 'Unknown Video')
        self.video_language = info.get('language')
        self.fetch_btn.setEnabled(True)
        
        self.video_title_label.setText(self.current_title)
        duration_sec = info.get('duration')
        if duration_sec is None:
            self.video_duration_label.setText("🔴 بث مباشر (Live)" if strings.is_ar else "🔴 Live Stream")
        else:
            mins, secs = divmod(duration_sec, 60)
            hours, mins = divmod(mins, 60)
            dur_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
            self.video_duration_label.setText(strings.MSG_DURATION.format(dur_str))
            
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

        def get_video_desc(res):
            try:
                h = int(res.replace('p', ''))
                if h > 1440: template = strings.QUAL_4K
                elif h > 1080: template = strings.QUAL_2K
                elif h > 720: template = strings.QUAL_1080
                elif h > 480: template = strings.QUAL_720
                elif h > 360: template = strings.QUAL_480
                elif h > 240: template = strings.QUAL_360
                elif h > 144: template = strings.QUAL_240
                else: template = strings.QUAL_144
                return template.format(res)
            except:
                return f"🎬 ({res})"

        for res, data in sorted_res:
            size_mb = data['size'] / (1024 * 1024)
            size_txt = f"{size_mb:.1f} MB" if size_mb > 0 else ""
            label = f"{get_video_desc(res)} - {size_txt}"
            self.video_options.append((label, data['format_id']))

        self.audio_options = []
        def calc_size(kbps):
            size_mb = (kbps * duration_sec) / 8 / 1024
            return f"{size_mb:.1f} MB" if size_mb > 0 else ""

        self.audio_options.append((f"{strings.AUDIO_M4A} ({calc_size(128)})", "m4a-128"))
        self.audio_options.append((f"{strings.AUDIO_MP3_70} ({calc_size(70)})", "mp3-70"))
        self.audio_options.append((f"{strings.AUDIO_MP3_128} ({calc_size(128)})", "mp3-128"))
        self.audio_options.append((f"{strings.AUDIO_MP3_160} ({calc_size(160)})", "mp3-160"))
        self.audio_options.append((f"{strings.AUDIO_MP3_320} ({calc_size(320)})", "mp3-320"))
        
        self.update_quality_options() 
        self.options_card.show()
        self.master_add_btn.show()
        self.master_add_btn.setEnabled(True)
        self.update_button_text()

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

    def update_batch_title(self, index, real_title):
        if hasattr(self, 'entries_checkboxes') and index < len(self.entries_checkboxes):
            chk = self.entries_checkboxes[index]
            chk.setText(f"{index + 1}. {real_title}")
            chk.setProperty("title", real_title)

    def update_single_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data): self.thumbnail_label.setPixmap(pixmap)
        self.single_thumb_data = data

    def update_quality_options(self):
        self.quality_combo.blockSignals(True)
        self.quality_combo.clear()
        
        # Add video options
        for label, data in self.video_options:
            self.quality_combo.addItem(label, data)
            
        # Add separator if both exist
        if self.video_options and self.audio_options:
            self.quality_combo.insertSeparator(self.quality_combo.count())
            
        # Add audio options
        for label, data in self.audio_options:
            self.quality_combo.addItem(label, data)
            
        self.quality_combo.blockSignals(False)
        self.on_quality_changed()
    
    def update_button_text(self):
        if hasattr(self, 'subs_only_check') and self.subs_only_check.isChecked():
            self.quality_combo.setEnabled(False) 
            self.master_add_btn.setEnabled(True) 
            self.master_add_btn.setText(strings.BTN_DOWNLOAD_SUB)
            return 

        self.quality_combo.setEnabled(True)
        if self.quality_combo.currentIndex() >= 0:
            self.master_add_btn.setEnabled(True)
            data = self.quality_combo.currentData()
            if data and isinstance(data, dict) and data.get('filesize'):
                size_mb = data['filesize'] / (1024 * 1024)
                self.master_add_btn.setText(strings.BTN_DOWNLOAD_SIZE.format(f"{size_mb:.1f} MB"))
            else: self.master_add_btn.setText(strings.BTN_DOWNLOAD)
        else:
            self.master_add_btn.setEnabled(False)
            self.master_add_btn.setText(strings.BTN_DOWNLOAD)

    def add_to_queue(self):
        subs_only = hasattr(self, 'subs_only_check') and self.subs_only_check.isChecked()
        format_id = "best" if subs_only else self.quality_combo.currentData()
        if format_id != "best":
            is_video = (self.type_combo.currentText() == strings.OPT_TYPE_VIDEO)
            if is_video: app_config["last_video_format"] = format_id
            else: app_config["last_audio_format"] = format_id
                
        app_config["last_sub_state"] = self.sub_check.isChecked()
        from utils.settings import save_settings
        save_settings(app_config)
        if not format_id: return

        if self.sub_check.isChecked():
            lang_code = self.sub_combo.currentData()
            sub_langs = [lang_code] if lang_code else ["en", "ar"]
        else: sub_langs = []

        embed_subs = app_config.get("embed_subs_default", True)

        custom_save_dir = None
        if app_config.get("save_mode") == "ask":
            custom_save_dir = QFileDialog.getExistingDirectory(self, "Select Download Folder")
            if not custom_save_dir: return 

        # نربط الأزرار والبيانات لترسل لتابة الـ Queue المنفصلة
        if self.gallery_layout.currentWidget() == self.playlist_layout_w:
            for i, chk in enumerate(getattr(self, 'entries_checkboxes', [])):
                if chk.isChecked():
                    url = chk.property("url")
                    title = chk.property("title")
                    thumb_data = self.playlist_thumbs_data.get(i) if hasattr(self, 'playlist_thumbs_data') else None
                    self.main_app.tab_queue._create_and_insert_queue_item(url, title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir)
        else:
            if not self.current_url: return
            thumb_data = getattr(self, 'single_thumb_data', None)
            custom_meta = getattr(self, 'custom_metadata', None)
            self.main_app.tab_queue._create_and_insert_queue_item(self.current_url, self.current_title, thumb_data, format_id, sub_langs, subs_only, embed_subs, custom_save_dir, custom_meta)
            self.single_thumb_data = None
            self.custom_metadata = None

        self.url_input.clear()                   
        self.gallery_stacked.hide()              
        self.master_add_btn.setEnabled(False)    
        self.master_add_btn.setText(strings.BTN_DOWNLOAD) 
        self.main_app.tabs.setCurrentIndex(1) # نقل المستخدم فوراً لصفحة التحميلات عند البدء
        
    def build_subtitle_menu(self):
        self.sub_combo.clear()
        if not (self.current_subtitles or self.current_auto_subs):
            self.sub_check.setChecked(False)
            self.sub_check.setEnabled(False)
            self.sub_combo.hide()
            if hasattr(self, 'subs_only_check'): self.subs_only_check.hide()
            return
            
        self.sub_check.setEnabled(True)
        
        # Populate languages
        # Manual subtitles
        manual_langs = sorted(list(self.current_subtitles.keys())) if self.current_subtitles else []
        # Auto subtitles
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
            
        # Add manual subtitles first
        for lang in manual_langs:
            name = get_lang_name(lang)
            self.sub_combo.addItem(f"🌐 {name} (Manual)", lang)
            
        # Add separator if both exist
        if manual_langs and auto_langs:
            self.sub_combo.insertSeparator(self.sub_combo.count())
            
        # Add auto subtitles
        for lang in auto_langs:
            if lang in manual_langs: continue
            name = get_lang_name(lang)
            self.sub_combo.addItem(f"🌐 {name} (Auto)", lang)
            
        # Select default language from settings
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
        format_id = self.quality_combo.currentData()
        if not format_id:
            self.update_button_text()
            return
            
        # Check if the selected format is audio
        is_audio = isinstance(format_id, str) and (format_id.startswith("audio:") or format_id.startswith("m4a-") or format_id.startswith("mp3-"))
        
        self.type_combo.blockSignals(True)
        if is_audio:
            self.type_combo.setCurrentIndex(1) # Audio
        else:
            self.type_combo.setCurrentIndex(0) # Video
        self.type_combo.blockSignals(False)
            
        is_single = (self.gallery_layout.currentWidget() == self.single_preview_w)
        if is_audio:
            if is_single:
                self.meta_btn.show()
            else:
                self.meta_btn.hide()
                
            if hasattr(self, 'subs_only_check'):
                self.subs_only_check.hide()
        else:
            self.meta_btn.hide()
            if self.sub_check.isChecked():
                if hasattr(self, 'subs_only_check'):
                    self.subs_only_check.show()
                    
        self.update_button_text()

    def open_metadata_dialog(self):
        dialog = MetadataDialog(self, self.current_title)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_metadata = dialog.get_data()
            self.add_to_queue()
