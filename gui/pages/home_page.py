import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QLabel, QComboBox, QCheckBox, 
                             QFrame, QScrollArea, QMessageBox, QApplication, QStackedWidget, QFileDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from gui.widgets import ElidedLabel, PlaylistThumbnail, DownloadCard
from core.downloader import InspectWorker, DownloadWorker, ThumbnailWorker
from utils.helpers import clean_and_shorten_title, resource_path, get_colored_icon, get_current_theme_color, get_full_language_name
from utils.locales import tr

class HomePage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app  # ربط الصفحة بالنافذة الرئيسية لقراءة الإعدادات والطوابير
        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.clean_title = "video"
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # حقل إدخال الرابط والأزرار
        url_layout = QHBoxLayout()
        self.paste_btn = QPushButton(self)
        self.paste_btn.setIcon(get_colored_icon("assets/icons/clipboard.svg", get_current_theme_color()))
        self.paste_btn.setIconSize(QSize(18, 18))
        self.paste_btn.setFixedWidth(40)
        self.paste_btn.clicked.connect(self.paste_text)
        url_layout.addWidget(self.paste_btn)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(tr("url_placeholder"))
        self.url_input.setClearButtonEnabled(True)
        self.url_input.textChanged.connect(self.on_text_changed)
        self.url_input.returnPressed.connect(self.inspect_url) 
        url_layout.addWidget(self.url_input)

        self.inspect_btn = QPushButton(self)
        self.inspect_btn.setIcon(get_colored_icon("assets/icons/search-lens.svg", get_current_theme_color()))
        self.inspect_btn.setIconSize(QSize(18, 18))
        self.inspect_btn.setFixedWidth(40)
        self.inspect_btn.clicked.connect(self.inspect_url)
        url_layout.addWidget(self.inspect_btn)
        main_layout.addLayout(url_layout)
        
        self.result_stack = QStackedWidget()
        main_layout.addWidget(self.result_stack)

        # --- شاشة الفيديو المفرد ---
        self.page_single = QWidget()
        page_single_layout = QVBoxLayout(self.page_single)
        page_single_layout.setContentsMargins(0, 0, 0, 0)
        page_single_layout.setSpacing(10)

        # شاشة الانتظار (Empty State) للصفحة الرئيسية
        from gui.widgets import EmptyStateWidget
        self.empty_state_widget = EmptyStateWidget(
            "assets/icons/search-lens.svg",
            tr("empty_home_title", "Ready to Download"),
            tr("empty_home_sub", "Enter a video or playlist URL above to inspect and download."),
            self
        )
        page_single_layout.addWidget(self.empty_state_widget)

        # كارت معلومات الفيديو الفاخر
        self.info_card = QFrame()
        self.info_card.setObjectName("MediaInfoCard")
        self.info_card.setSizePolicy(self.info_card.sizePolicy().Policy.Expanding, self.info_card.sizePolicy().Policy.Preferred)
        self.info_card.hide()
        info_card_layout = QVBoxLayout(self.info_card)
        info_card_layout.setContentsMargins(15, 15, 15, 15)
        info_card_layout.setSpacing(8)
        
        self.thumb_label = PlaylistThumbnail()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.hide()
        self.thumb_label.clicked.connect(self.go_back_to_playlist_selection)
        info_card_layout.addWidget(self.thumb_label)

        self.title_label = ElidedLabel('', self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        self.title_label.setFont(title_font) 
        info_card_layout.addWidget(self.title_label)

        self.duration_label = QLabel('', self)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_card_layout.addWidget(self.duration_label)

        page_single_layout.addWidget(self.info_card)

        # كارت إعدادات التحميل والترجمة الفاخر
        self.settings_card = QFrame()
        self.settings_card.setObjectName("DownloadSettingsCard")
        self.settings_card.hide()
        settings_card_layout = QVBoxLayout(self.settings_card)
        settings_card_layout.setContentsMargins(15, 15, 15, 15)
        settings_card_layout.setSpacing(12)

        self.format_combo = QComboBox(self)
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        settings_card_layout.addWidget(self.format_combo)
        
        # صندوق واختيار الترجمة (Sub/CC)
        sub_layout = QHBoxLayout()
        self.sub_cb = QCheckBox(tr("sub_cc"), self)
        self.sub_cb.setEnabled(False)
        self.sub_cb.toggled.connect(self.toggle_sub_combo)
        
        self.sub_info_icon = QLabel(self)
        self.sub_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.sub_info_icon.setToolTip(tr("sub_info_tooltip", "Subtitles will be downloaded if available"))
        self.sub_info_icon.hide()
        
        sub_layout.addWidget(self.sub_cb)
        sub_layout.addWidget(self.sub_info_icon)
        sub_layout.addStretch()
        settings_card_layout.addLayout(sub_layout)

        self.sub_combo = QComboBox(self)
        self.sub_combo.hide()
        settings_card_layout.addWidget(self.sub_combo)
        
        page_single_layout.addWidget(self.settings_card)
        
        page_single_layout.addStretch()
        self.result_stack.addWidget(self.page_single)

        # --- شاشة قوائم التشغيل (Playlist) ---
        self.page_playlist = QWidget()
        page_pl_layout = QVBoxLayout(self.page_playlist)
        page_pl_layout.setContentsMargins(0, 0, 0, 0)

        self.pl_select_all_cb = QCheckBox(tr("select_all"))
        self.pl_select_all_cb.setChecked(True)
        cb_font = self.pl_select_all_cb.font()
        cb_font.setBold(True)
        self.pl_select_all_cb.setFont(cb_font)
        self.pl_select_all_cb.clicked.connect(self.toggle_all_playlist_items)
        page_pl_layout.addWidget(self.pl_select_all_cb)

        self.pl_scroll = QScrollArea()
        self.pl_scroll.setWidgetResizable(True)
        
        self.pl_container = QWidget()
        self.pl_items_layout = QVBoxLayout(self.pl_container)
        self.pl_scroll.setWidget(self.pl_container)
        page_pl_layout.addWidget(self.pl_scroll)

        pl_btn_layout = QHBoxLayout()
        self.btn_pl_cancel = QPushButton(tr("btn_cancel"))
        self.btn_pl_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", get_current_theme_color()))
        self.btn_pl_cancel.setIconSize(QSize(16, 16))
        self.btn_pl_cancel.setFixedHeight(35)
        btn_c_font = self.btn_pl_cancel.font()
        btn_c_font.setBold(True)
        self.btn_pl_cancel.setFont(btn_c_font)
        self.btn_pl_cancel.clicked.connect(self.reset_ui_state)
        
        self.btn_pl_next = QPushButton(tr("btn_next"))
        self.btn_pl_next.setIcon(get_colored_icon("assets/icons/video.svg", get_current_theme_color()))
        self.btn_pl_next.setIconSize(QSize(16, 16))
        self.btn_pl_next.setFixedHeight(35)
        btn_n_font = self.btn_pl_next.font()
        btn_n_font.setBold(True)
        self.btn_pl_next.setFont(btn_n_font)
        self.btn_pl_next.clicked.connect(self.process_selected_playlist)
        
        pl_btn_layout.addWidget(self.btn_pl_cancel)
        pl_btn_layout.addStretch()
        pl_btn_layout.addWidget(self.btn_pl_next)
        page_pl_layout.addLayout(pl_btn_layout)

        self.result_stack.addWidget(self.page_playlist)

        # زر بدء التحميل الرئيسي
        home_controls_layout = QHBoxLayout()
        self.btn_back_to_playlist = QPushButton(tr("btn_back_to_playlist", "Back to Playlist"), self)
        self.btn_back_to_playlist.setIcon(get_colored_icon("assets/icons/arrow-left.svg", get_current_theme_color()))
        self.btn_back_to_playlist.setIconSize(QSize(20, 20))
        self.btn_back_to_playlist.setFixedHeight(40)
        self.btn_back_to_playlist.hide()
        self.btn_back_to_playlist.clicked.connect(self.go_back_to_playlist_selection)
        home_controls_layout.addWidget(self.btn_back_to_playlist)

        self.download_btn = QPushButton(tr("start_download"), self)
        self.download_btn.setIcon(get_colored_icon("assets/icons/rocket.svg", get_current_theme_color()))
        self.download_btn.setIconSize(QSize(20, 20))
        self.download_btn.setFixedHeight(40)
        self.download_btn.hide()
        self.download_btn.setEnabled(False) 
        self.download_btn.clicked.connect(self.start_download)
        
        home_controls_layout.addWidget(self.download_btn)
        main_layout.addLayout(home_controls_layout)

    def toggle_sub_combo(self, checked):
        if checked and self.sub_combo.count() > 0 and not self.is_playlist_mode:
            self.sub_combo.show()
        else:
            self.sub_combo.hide()

    def reset_ui_state(self):
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.duration_label.setText("")
        self.thumb_label.hide()
        self.thumb_label.clear()
        self.clean_title = "video"
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.format_combo.hide()
        self.download_btn.hide()
        self.btn_back_to_playlist.hide()
        self.sub_cb.hide()
        self.sub_info_icon.hide()
        self.sub_combo.hide()
        self.info_card.hide()
        self.settings_card.hide()
        self.empty_state_widget.show()

        if hasattr(self, 'thumb_workers'):
            self.thumb_workers.clear()
        if hasattr(self, 'pl_items_layout'):
            while self.pl_items_layout.count():
                item = self.pl_items_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    while item.layout().count():
                        sub_item = item.layout().takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
        if hasattr(self, 'pl_checkboxes'):
            self.pl_checkboxes.clear()
        if hasattr(self, 'result_stack'):
            self.result_stack.setCurrentIndex(0)
        self.is_playlist_mode = False

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def on_text_changed(self, text):
        if not text: 
            self.reset_ui_state()

    def inspect_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.title_label.setText(tr("err_empty_url"))
            return

        if "start_radio=" in url or "list=RD" in url:
            url = re.sub(r'&list=[^&]+', '', url)
            url = re.sub(r'&start_radio=[^&]+', '', url)
            url = url.split("&")[0]

        if "watch?v=" in url and "list=" in url:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("playlist_detected_title"))
            msg_box.setText(tr("playlist_detected_msg"))
            
            btn_playlist = msg_box.addButton(tr("btn_all_playlist"), QMessageBox.ButtonRole.ActionRole)
            btn_video = msg_box.addButton(tr("btn_just_video"), QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg_box.addButton(tr("msg_cancel"), QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_video:
                url = re.sub(r'&list=[^&]+', '', url)
                url = url.split("&")[0] 
            elif msg_box.clickedButton() == btn_playlist:
                match = re.search(r'list=([^&]+)', url)
                if match:
                    url = f"https://www.youtube.com/playlist?list={match.group(1)}"
            else:
                return 
        else:
            if "youtu.be" in url or "shorts" in url:
                url = url.split("?")[0]
            elif "watch?v=" in url:
                url = url.split("&")[0]

        self.url_input.setText(url)
        self.thumb_label.hide()
        self.title_label.setText(tr("searching"))
        self.duration_label.setText("")
        self.title_label.setToolTip("")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.inspect_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.empty_state_widget.hide()
        self.info_card.show()
        self.settings_card.hide()
        
        self.inspect_worker = InspectWorker(url)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.playlist_signal.connect(self.on_playlist_success)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    def on_inspect_success(self, title, duration_secs, image_data, format_list, subtitles_dict=None):
        self.clean_title = clean_and_shorten_title(title)
        self.title_label.setToolTip(title)
        self.title_label.setText(title)
        m, s = divmod(duration_secs, 60)
        h, m = divmod(m, 60)
        duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self.duration_label.setText(f"{tr('duration_prefix')}{duration_str}")
        
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.show()
            
        self.info_card.show()
        self.settings_card.show()
            
        self.format_combo.clear()
        for item in format_list:
            if item['type'] == 'separator':
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(item['label'], item['format_code'])

        self.format_combo.show() 
        self.format_combo.setEnabled(True)
        
        # إدارة خيارات الترجمات المتوفرة للفيديو المفرد
        self.sub_combo.clear()
        self.sub_cb.setChecked(False)
        self.sub_combo.hide()

        if subtitles_dict:
            # 1. فلترة وتصفية الترجمات لاستبعاد live_chat وأي محادثات
            filtered_subs = {}
            for lang, s_info in subtitles_dict.items():
                if "live_chat" in lang.lower() or "chat" in lang.lower():
                    continue
                filtered_subs[lang] = s_info
                
            if filtered_subs:
                self.sub_cb.setEnabled(True)
                self.sub_cb.setStyleSheet("") 
                
                # 2. تصنيف المجموعات:
                # - Manual Subtitles
                # - Original Auto Subtitles (Auto and code contains '-orig' or '-original')
                # - Other Auto Subtitles
                
                manual_subs = []
                original_auto_subs = []
                other_auto_subs = []
                
                for lang_code, s_info in filtered_subs.items():
                    is_original = "-orig" in lang_code.lower() or "-original" in lang_code.lower()
                    if s_info['type'] == 'Manual':
                        manual_subs.append((lang_code, s_info))
                    elif s_info['type'] == 'Auto' and is_original:
                        original_auto_subs.append((lang_code, s_info))
                    else:
                        other_auto_subs.append((lang_code, s_info))
                
                # 3. منطق الترتيب والخط الفاصل:
                # - الحالة الأولى: لو في ترجمة يدوي، اليدوي هو اللي فوق، وتحت الباقي (التلقائي والأصلي وغيره)
                # - الحالة الثانية: لو مفيش يدوي، التلقائي الأصلي (org) فوق، والباقي تحت
                
                top_group = []
                bottom_group = []
                
                if manual_subs:
                    top_group = manual_subs
                    bottom_group = original_auto_subs + other_auto_subs
                else:
                    top_group = original_auto_subs
                    bottom_group = other_auto_subs
                    
                # 4. بناء القائمة المنسدلة:
                for lang_code, s_info in top_group:
                    lang_name = get_full_language_name(lang_code)
                    if s_info['type'] == 'Manual':
                        label = f"🌐 {lang_name} (original) (manual)"
                    else:
                        label = f"🌐 {lang_name} (original) (auto)"
                    self.sub_combo.addItem(label, s_info['code'])
                    
                # إضافة خط فاصل إذا كان هناك عناصر في كلا المجموعتين
                if top_group and bottom_group:
                    self.sub_combo.insertSeparator(self.sub_combo.count())
                    
                for lang_code, s_info in bottom_group:
                    is_original = "-orig" in lang_code.lower() or "-original" in lang_code.lower()
                    lang_name = get_full_language_name(lang_code)
                    if is_original:
                        label = f"🌐 {lang_name} (original) (auto)"
                    elif s_info['type'] == 'Manual':
                        label = f"🌐 {lang_name} (original) (manual)"
                    else:
                        label = f"🌐 {lang_name} (auto)"
                    self.sub_combo.addItem(label, s_info['code'])
            else:
                self.sub_cb.setEnabled(False)
                self.sub_cb.setStyleSheet("color: gray; text-decoration: line-through;")
        else:
            self.sub_cb.setEnabled(False)
            self.sub_cb.setStyleSheet("color: gray; text-decoration: line-through;")
        self.sub_cb.show()
        
        self.download_btn.show()
        self.download_btn.setEnabled(True)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def on_playlist_success(self, title, image_data, entries):
        self.reset_ui_state()
        self.current_pl_title = title
        self.current_pl_image = image_data
        self.pl_checkboxes = []

        while self.pl_items_layout.count():
            item = self.pl_items_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        self.thumb_workers = []
        for i, entry in enumerate(entries):
            entry['original_index'] = i + 1
            row = QHBoxLayout()
            row.setSpacing(12)
            row.setContentsMargins(5, 5, 5, 5)

            cb = QCheckBox()
            cb.setChecked(True)

            thumb_lbl = QLabel()
            thumb_lbl.setFixedSize(100, 56)
            thumb_lbl.setStyleSheet("background-color: #1a2035; border-radius: 4px;")
            cb.setProperty("img_label", thumb_lbl)
            
            title_lbl = ElidedLabel(f"{i+1}. {entry['title']}")
            title_font = title_lbl.font()
            title_font.setBold(True)
            title_font.setPointSize(title_font.pointSize() + 1)
            title_lbl.setFont(title_font)
            
            row.addWidget(cb)
            row.addWidget(thumb_lbl)
            row.addWidget(title_lbl)
            row.setStretch(2, 1)
            self.pl_items_layout.addLayout(row)
            
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken) 
            self.pl_items_layout.addWidget(line)

            self.pl_checkboxes.append((cb, entry))

            if entry.get('id'):
                worker = ThumbnailWorker(i, entry['id'])
                worker.thumb_loaded.connect(self.update_playlist_thumb)
                worker.finished.connect(worker.deleteLater)
                self.thumb_workers.append(worker)
                worker.start()

        # إضافة تمدد بالأسفل لضغط العناصر للأعلى في حالة القوائم الصغيرة
        self.pl_items_layout.addStretch(1)

        self.pl_select_all_cb.setChecked(True)
        self.result_stack.setCurrentIndex(1) 
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def update_playlist_thumb(self, index, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            if index < len(getattr(self, 'pl_checkboxes', [])):
                cb, entry = self.pl_checkboxes[index]
                label = cb.property("img_label")
                if label:
                    scaled_pixmap = pixmap.scaled(100, 56, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled_pixmap)
                    entry['thumb_pixmap'] = pixmap

    def toggle_all_playlist_items(self):
        state = self.pl_select_all_cb.isChecked()
        for cb, _ in self.pl_checkboxes:
            cb.setChecked(state)

    def process_selected_playlist(self):
        selected = [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]
        if not selected: return
            
        self.is_playlist_mode = True
        self.selected_playlist_entries = selected
        title = self.current_pl_title
        self.clean_title = clean_and_shorten_title(title)
        
        self.title_label.setToolTip(title)
        self.title_label.setText(title)

        first_video_entry = None
        if hasattr(self, 'pl_checkboxes') and len(self.pl_checkboxes) > 0:
            _, first_video_entry = self.pl_checkboxes[0]
            
        if first_video_entry and first_video_entry.get('thumb_pixmap'):
            self.thumb_label.setPixmap(first_video_entry['thumb_pixmap'])
            self.thumb_label.set_count(len(selected)) 
            self.thumb_label.show()
        elif hasattr(self, 'current_pl_image') and self.current_pl_image:
            pixmap = QPixmap()
            pixmap.loadFromData(self.current_pl_image)
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.set_count(len(selected)) 
            self.thumb_label.show()

        self.info_card.show()
        self.settings_card.show()

        self.format_combo.clear()
        pl_formats = [
            ("🎬 4K (2160p) - Ultra HD", "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"),
            ("🎬 2K (1440p) - Quad HD", "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"),
            ("🎬 Full HD (1080p)", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"),
            ("🎬 High (720p)", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"),
            ("🎬 Standard (480p)", "bestvideo[height<=480]+bestaudio/best[height<=480]/best"),
            ("🎬 Medium (360p)", "bestvideo[height<=360]+bestaudio/best[height<=360]/best"),
            ("🎬 Low (240p)", "bestvideo[height<=240]+bestaudio/best[height<=240]/best"),
            ("🎬 Very Low (144p)", "bestvideo[height<=144]+bestaudio/best[height<=144]/best"),
            ("separator", ""),
            ("🎵 M4A (128K) - Mobile Optimized (Fast)", "audio:m4a:128"),
            ("🎵 MP3 (70K) - Low Quality (Space Saver)", "audio:mp3:70"),
            ("🎵 MP3 (128K) - Standard (Classic)", "audio:mp3:128"),
            ("🎵 MP3 (160K) - High Quality (Headphones)", "audio:mp3:160"),
            ("🎵 MP3 (320K) - Ultra Quality (Amplifiers)", "audio:mp3:320"),
        ]
        for label, code in pl_formats:
            if label == "separator":
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(label, code)

        self.format_combo.show() 
        self.format_combo.setEnabled(True)
        
        self.sub_cb.setEnabled(True)
        self.sub_cb.setStyleSheet("")
        self.sub_cb.setChecked(False)
        self.sub_cb.show()
        self.sub_info_icon.show()
        self.sub_combo.hide()

        self.empty_state_widget.hide()
        self.btn_back_to_playlist.show()
        self.download_btn.show()
        self.download_btn.setEnabled(True)
        self.result_stack.setCurrentIndex(0)

    def on_inspect_error(self, error_msg):
        self.reset_ui_state()
        self.empty_state_widget.hide()
        self.info_card.show()
        self.title_label.setText(error_msg)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def start_download(self):
        url = self.url_input.text()
        if not url and not self.is_playlist_mode: return

        # قراءة إعداد حاوية الفيديو المفضلة من الإعدادات
        video_container = "mp4"
        download_path_type = "always_ask"
        custom_path = ""
        if os.path.exists(self.main_app.settings_file):
            try:
                import json
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    video_container = data.get("video_container", "mp4")
                    download_path_type = data.get("download_path_type", "always_ask")
                    custom_path = data.get("custom_path", "")
            except Exception:
                pass

        if download_path_type == "downloads":
            target_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        elif download_path_type == "custom" and custom_path:
            try:
                os.makedirs(custom_path, exist_ok=True)
                target_dir = custom_path
            except Exception:
                target_dir = self.main_app.last_save_dir
                download_path_type = "always_ask"
        else:
            target_dir = self.main_app.last_save_dir

        format_code = self.format_combo.currentData()
        if format_code.startswith("audio:"):
            _, codec, _ = format_code.split(":")
            filter_str = f"Audio Files (*.{codec})"
        else:
            # ترتيب الفلاتر بوضع التفضيل الشخصي أولاً
            all_filters = {
                "mp4": "MP4 Video (*.mp4)",
                "mkv": "MKV Video (*.mkv)",
                "mov": "MOV Video (*.mov)",
                "webm": "WebM Video (*.webm)"
            }
            pref_filter = all_filters.get(video_container, "MP4 Video (*.mp4)")
            other_filters = [f for k, f in all_filters.items() if k != video_container]
            filter_str = f"{pref_filter};;{';;'.join(other_filters)}"

        if self.is_playlist_mode:
            if download_path_type == "always_ask":
                save_dir = QFileDialog.getExistingDirectory(self, "Select Folder for Playlist", target_dir)
                if not save_dir: return
            else:
                save_dir = target_dir

            self.main_app.last_save_dir = save_dir
            self.main_app.save_settings(save_dir)
            is_audio = format_code.startswith("audio:")
            playlist_target_dir = save_dir if is_audio else os.path.join(save_dir, self.clean_title)
            if not is_audio and not os.path.exists(playlist_target_dir):
                os.makedirs(playlist_target_dir)

            for entry in self.selected_playlist_entries:
                vid_url = entry['url']
                clean_vid_title = clean_and_shorten_title(entry['title'])

                if is_audio:
                    _, codec, _ = format_code.split(":")
                    ext = f".{codec}"
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
                if not thumb_pixmap and hasattr(self, 'current_pl_image') and self.current_pl_image:
                    pix = QPixmap()
                    pix.loadFromData(self.current_pl_image)
                    thumb_pixmap = pix

                new_card = DownloadCard(final_title, thumb_pixmap, save_path)
                new_card.url = vid_url
                new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
                new_card.duration = tr("playlist_item_duration")
                self.main_app.cards_layout.insertWidget(0, new_card) 
                
                is_playlist_sub = self.sub_cb.isVisible() and self.sub_cb.isChecked()
                worker = DownloadWorker(vid_url, format_code, save_path, is_playlist_sub=is_playlist_sub)
                worker.progress_signal.connect(new_card.update_progress)
                worker.status_signal.connect(new_card.update_status)
                worker.finished_signal.connect(new_card.set_save_path)
                worker.sub_notification_signal.connect(self.main_app.handle_subtitle_notification)

                new_card.set_worker(worker)
                new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=vid_url, f=format_code, s=save_path, sb=None, ips=is_playlist_sub: self.main_app.reload_download(c, u, f, s, sb, ips))
                
                self.main_app.waiting_workers.append(worker)
                new_card.update_status("⏳ Waiting in queue...") 
                
            self.main_app.page_downloads.check_empty_state()
            self.is_playlist_mode = False
            self.selected_playlist_entries.clear()

        else:
            # 2. تحديد ما إذا كان سيتم فتح الديالوج أم الحفظ الفوري
            if download_path_type == "always_ask":
                save_path, selected_filter = QFileDialog.getSaveFileName(self, "Save Media As", os.path.join(target_dir, self.clean_title), filter_str)
                if not save_path: return 

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
                # حفظ فوري بدون إزعاج المستخدم بدايلوج
                if format_code.startswith("audio:"):
                    ext = f".{codec}"
                else:
                    ext = f".{video_container}"
                
                save_path = os.path.join(target_dir, f"{self.clean_title}{ext}")
                
                # منع تكرار الأسماء بإضافة _1, _2 إلخ
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

            new_card = DownloadCard(self.title_label.toolTip(), self.thumb_label._pixmap, save_path)
            new_card.url = url
            new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
            new_card.duration = self.duration_label.text().replace(tr("duration_prefix"), "") if self.duration_label.text() else "00:00"
            self.main_app.cards_layout.insertWidget(0, new_card) 
            
            worker = DownloadWorker(url, format_code, save_path, sub_lang=sub_lang)
            worker.progress_signal.connect(new_card.update_progress)
            worker.status_signal.connect(new_card.update_status)
            worker.finished_signal.connect(new_card.set_save_path)

            new_card.set_worker(worker)
            new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=url, f=format_code, s=save_path, sb=sub_lang: self.main_app.reload_download(c, u, f, s, sb))
            
            self.main_app.waiting_workers.append(worker)
            new_card.update_status("⏳ Waiting in queue...") 
            self.main_app.page_downloads.check_empty_state() 

        self.main_app.change_page(1)
        self.on_text_changed("") 
        self.url_input.clear()
        self.main_app.process_queue()

    def update_icon_colors(self, icon_color):
        self.paste_btn.setIcon(get_colored_icon("assets/icons/clipboard.svg", icon_color))
        self.inspect_btn.setIcon(get_colored_icon("assets/icons/search-lens.svg", icon_color))
        self.btn_pl_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", icon_color))
        
        is_rtl = (self.layoutDirection() == Qt.LayoutDirection.RightToLeft)
        next_icon = "assets/icons/arrow-left.svg" if is_rtl else "assets/icons/arrow-right.svg"
        back_icon = "assets/icons/arrow-right.svg" if is_rtl else "assets/icons/arrow-left.svg"
        self.btn_pl_next.setIcon(get_colored_icon(next_icon, icon_color))
        self.btn_back_to_playlist.setIcon(get_colored_icon(back_icon, icon_color))

        self.download_btn.setIcon(get_colored_icon("assets/icons/rocket.svg", icon_color))
        self.empty_state_widget.update_icon_color("assets/icons/search-lens.svg", icon_color)
        self.sub_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))

    def go_back_to_playlist_selection(self):
        if hasattr(self, 'result_stack'):
            self.result_stack.setCurrentIndex(1)
            self.download_btn.hide()
            self.btn_back_to_playlist.hide()
            self.info_card.hide()
            self.settings_card.hide()