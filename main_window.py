import os
import re
import json
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QComboBox,
                             QFileDialog, QTabWidget, QScrollArea, QApplication, QMessageBox,
                             QStackedWidget, QCheckBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from widgets import ResponsiveImage, ElidedLabel, DownloadCard, PlaylistThumbnail
from workers import InspectWorker, DownloadWorker, ThumbnailWorker

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
    
def clean_and_shorten_title(title, limit=150):
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    if len(clean) > limit:
        return clean[:limit-3] + "..."
    return clean

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.last_save_dir = self.load_settings()
        self.clean_title = "video"
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AHS-MediaDL')
        self.setWindowIcon(QIcon(resource_path('icon.ico')))
        self.resize(650, 450) 
        self.setMinimumSize(550, 400)
        
        self.max_concurrent = 3
        self.active_workers = []
        self.waiting_workers = []

        app_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab_main = QWidget()
        self.tab_queue = QWidget()
        self.tabs.addTab(self.tab_main, "🏠 Home")
        self.tabs.addTab(self.tab_queue, "⬇️ Downloads")
        
        app_layout.addWidget(self.tabs)

        # --- Tab 1: Home ---
        main_layout = QVBoxLayout(self.tab_main)

        url_layout = QHBoxLayout()
        self.paste_btn = QPushButton('📋', self)
        self.paste_btn.setFixedWidth(40)
        self.paste_btn.clicked.connect(self.paste_text)
        url_layout.addWidget(self.paste_btn)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter video URL here...')
        self.url_input.setClearButtonEnabled(True)
        self.url_input.textChanged.connect(self.on_text_changed)
        self.url_input.returnPressed.connect(self.inspect_url) 
        url_layout.addWidget(self.url_input)

        self.inspect_btn = QPushButton('🔍', self)
        self.inspect_btn.setFixedWidth(40)
        self.inspect_btn.clicked.connect(self.inspect_url)
        url_layout.addWidget(self.inspect_btn)
        main_layout.addLayout(url_layout)
        self.result_stack = QStackedWidget()
        main_layout.addWidget(self.result_stack)

        self.page_single = QWidget()
        page_single_layout = QVBoxLayout(self.page_single)
        page_single_layout.setContentsMargins(0, 0, 0, 0)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        self.thumb_label = PlaylistThumbnail()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.hide()
        info_layout.addWidget(self.thumb_label)

        self.title_label = ElidedLabel('', self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        self.title_label.setFont(title_font) 
        info_layout.addWidget(self.title_label)

        self.duration_label = QLabel('', self)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.duration_label)

        page_single_layout.addLayout(info_layout)

        self.format_combo = QComboBox(self)
        self.format_combo.hide()
        self.format_combo.addItem("Waiting for URL...", "")
        self.format_combo.setEnabled(False)
        page_single_layout.addWidget(self.format_combo)
        page_single_layout.addStretch()

        self.result_stack.addWidget(self.page_single)

        self.page_playlist = QWidget()
        page_pl_layout = QVBoxLayout(self.page_playlist)
        page_pl_layout.setContentsMargins(0, 0, 0, 0)

        self.pl_select_all_cb = QCheckBox("Select All")
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
        self.btn_pl_cancel = QPushButton("❌ Cancel")
        self.btn_pl_cancel.setFixedHeight(35)
        btn_c_font = self.btn_pl_cancel.font()
        btn_c_font.setBold(True)
        self.btn_pl_cancel.setFont(btn_c_font)
        self.btn_pl_cancel.clicked.connect(self.reset_ui_state)
        
        self.btn_pl_next = QPushButton("Next ➡️")
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

        home_controls_layout = QHBoxLayout()
        
        self.download_btn = QPushButton('🚀 Start Download', self)
        self.download_btn.setFixedHeight(40)
        self.download_btn.hide()
        self.download_btn.setEnabled(False) 
        self.download_btn.clicked.connect(self.start_download)
        
        home_controls_layout.addWidget(self.download_btn)
        main_layout.addLayout(home_controls_layout)

        # --- Tab 2: Downloads ---
        queue_layout = QVBoxLayout(self.tab_queue)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }") 
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop) 
        
        self.scroll_area.setWidget(self.cards_container)
        queue_layout.addWidget(self.scroll_area)

        global_controls_layout = QHBoxLayout()
        
        self.btn_pause_all = QPushButton("⏸️ Pause All")
        self.btn_pause_all.setToolTip("Pause or Resume all active downloads")
        
        self.btn_cancel_all = QPushButton("❌ Cancel All")
        self.btn_cancel_all.setToolTip("Cancel all active downloads")
        
        self.btn_clear_all = QPushButton("🧹 Clear")
        self.btn_clear_all.setToolTip("Remove finished or canceled items from the list")

        global_controls_layout.addWidget(self.btn_clear_all)
        global_controls_layout.addStretch()
        global_controls_layout.addWidget(self.btn_pause_all)
        global_controls_layout.addWidget(self.btn_cancel_all)
        
        queue_layout.addLayout(global_controls_layout)

        self.btn_pause_all.clicked.connect(self.action_pause_resume_all)
        self.btn_cancel_all.clicked.connect(self.action_cancel_all)
        self.btn_clear_all.clicked.connect(self.action_clear_all)

    def load_settings(self):
        default_dir = os.path.expanduser('~/Downloads')
        user_home = os.path.expanduser('~')
        app_dir = os.path.join(user_home, '.AHS-MediaDL')
        if not os.path.exists(app_dir):
            try:
                os.makedirs(app_dir)
            except:
                pass

        self.settings_file = os.path.join(app_dir, 'settings.json')
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('last_save_dir', default_dir)
        except:
            pass 
            
        return default_dir

    def save_settings(self, directory):
        try:
            data = {'last_save_dir': directory}
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except:
            pass

    def reset_ui_state(self):
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.duration_label.setText("")
        self.thumb_label.hide()
        self.thumb_label.clear()
        self.clean_title = "video"
        self.format_combo.clear()
        self.format_combo.addItem("Waiting for URL...", "")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.format_combo.hide()
        self.download_btn.hide()

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

    def get_download_cards(self):
        cards = []
        for i in range(self.cards_layout.count()):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, DownloadCard):
                cards.append(widget)
        return cards

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def on_text_changed(self, text):
        if not text: 
            self.reset_ui_state()

    def inspect_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.title_label.setText("⚠️ Please enter a URL first!")
            return

        if "start_radio=" in url or "list=RD" in url:
            url = re.sub(r'&list=[^&]+', '', url)
            url = re.sub(r'&start_radio=[^&]+', '', url)
            url = url.split("&")[0]

        if "watch?v=" in url and "list=" in url:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Playlist Detected")
            msg_box.setText("This video is part of a playlist.\nWould you like to process the entire playlist or just this specific video?")
            
            btn_playlist = msg_box.addButton("All playlist", QMessageBox.ButtonRole.ActionRole)
            btn_video = msg_box.addButton("Just This Video", QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
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
        self.title_label.setText("🔍 Searching...")
        self.duration_label.setText("")
        self.title_label.setToolTip("")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.inspect_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        
        self.inspect_worker = InspectWorker(url)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.playlist_signal.connect(self.on_playlist_success)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    def on_inspect_success(self, title, duration_secs, image_data, format_list):
        self.clean_title = clean_and_shorten_title(title)
        self.title_label.setToolTip(title)
        self.title_label.setText(title)
        m, s = divmod(duration_secs, 60)
        h, m = divmod(m, 60)
        if h > 0:
            duration_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            duration_str = f"{m:02d}:{s:02d}"
        self.duration_label.setText(f"⏱ Duration: {duration_str}")
        
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.show()
            
        self.format_combo.clear()
        for item in format_list:
            if item['type'] == 'separator':
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(item['label'], item['format_code'])

        self.format_combo.show() 
        self.format_combo.setEnabled(True)
        
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
            cb = QCheckBox()
            cb.setChecked(True)

            thumb_lbl = QLabel()
            thumb_lbl.setFixedSize(60, 34)
            thumb_lbl.setStyleSheet("background-color: #222;")
            cb.setProperty("img_label", thumb_lbl)
            
            title_lbl = ElidedLabel(f"{i+1}. {entry['title']}")
            
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
                    scaled_pixmap = pixmap.scaled(60, 34, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled_pixmap)
                    entry['thumb_pixmap'] = pixmap

    def toggle_all_playlist_items(self):
        state = self.pl_select_all_cb.isChecked()
        for cb, _ in self.pl_checkboxes:
            cb.setChecked(state)

    def process_selected_playlist(self):
        selected = [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]
        if not selected:
            return
            
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
        self.download_btn.show()
        self.download_btn.setEnabled(True)
        
        self.result_stack.setCurrentIndex(0)

    def on_inspect_error(self, error_msg):
        self.reset_ui_state()
        self.title_label.setText(error_msg)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def start_download(self):
        url = self.url_input.text()
        if not url and not hasattr(self, 'is_playlist_mode'): return

        format_code = self.format_combo.currentData()
        if format_code.startswith("audio:"):
            _, codec, _ = format_code.split(":")
            filter_str = f"Audio Files (*.{codec})"
        else:
            filter_str = "MP4 Video (*.mp4);;MKV Video (*.mkv)"

        default_path = os.path.join(self.last_save_dir, self.clean_title)
        
        if getattr(self, 'is_playlist_mode', False):
            save_dir = QFileDialog.getExistingDirectory(self, "Select Folder for Playlist", self.last_save_dir)
            if not save_dir: return
            self.last_save_dir = save_dir
            self.save_settings(save_dir)
            is_audio = format_code.startswith("audio:")
            if is_audio:
                target_dir = save_dir
            else:
                target_dir = os.path.join(save_dir, self.clean_title)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

            for entry in self.selected_playlist_entries:
                vid_url = entry['url']
                clean_vid_title = clean_and_shorten_title(entry['title'])

                if is_audio:
                    _, codec, _ = format_code.split(":")
                    ext = f".{codec}"
                    final_title = clean_vid_title
                else:
                    ext = ".mp4"
                    original_index = entry.get('original_index', 1)
                    final_title = f"{original_index}. {clean_vid_title}"

                save_path = os.path.join(target_dir, f"{final_title}{ext}")
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
                self.cards_layout.insertWidget(0, new_card) 
                
                worker = DownloadWorker(vid_url, format_code, save_path)
                worker.progress_signal.connect(new_card.update_progress)
                worker.status_signal.connect(new_card.update_status)

                new_card.set_worker(worker)
                new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=vid_url, f=format_code, s=save_path: self.reload_download(c, u, f, s))
                
                self.waiting_workers.append(worker)
                new_card.update_status("⏳ Waiting in queue...") 
                
            self.is_playlist_mode = False
            self.selected_playlist_entries.clear()

        else:
            save_path, selected_filter = QFileDialog.getSaveFileName(self, "Save Media As", default_path, filter_str)

            if not save_path: return 

            if "mkv" in selected_filter.lower() and not save_path.lower().endswith(".mkv"):
                save_path += ".mkv"
            elif "mp4" in selected_filter.lower() and not save_path.lower().endswith(".mp4"):
                save_path += ".mp4"
            elif format_code.startswith("audio:") and not save_path.lower().endswith(f".{codec}"):
                save_path += f".{codec}"

            self.last_save_dir = os.path.dirname(save_path)
            self.save_settings(self.last_save_dir)

            new_card = DownloadCard(self.title_label.toolTip(), self.thumb_label._pixmap, save_path)
            self.cards_layout.insertWidget(0, new_card) 
            
            worker = DownloadWorker(url, format_code, save_path)
            worker.progress_signal.connect(new_card.update_progress)
            worker.status_signal.connect(new_card.update_status)

            new_card.set_worker(worker)
            new_card.btn_reload.clicked.connect(lambda checked=False, c=new_card, u=url, f=format_code, s=save_path: self.reload_download(c, u, f, s))
            
            self.waiting_workers.append(worker)
            new_card.update_status("⏳ Waiting in queue...") 

        self.tabs.setCurrentIndex(1)
        self.on_text_changed("") 
        self.url_input.clear()
        
        self.process_queue()

    def reload_download(self, card, url, format_code, save_path):
        if hasattr(card, 'worker') and card.worker:
            old_worker = card.worker
            try:
                old_worker.cancel()
                old_worker.quit()
                old_worker.wait(1000)
            except:
                pass
            try:
                old_worker.progress_signal.disconnect()
                old_worker.status_signal.disconnect()
                old_worker.finished.disconnect()
            except:
                pass
            if old_worker in self.active_workers:
                self.active_workers.remove(old_worker)
            if old_worker in self.waiting_workers:
                self.waiting_workers.remove(old_worker)
                
            old_worker.deleteLater()

        card.status_label.setText("⏳ Waiting in queue...")
        card.p_bar.setValue(0)
        card.btn_reload.hide()
        card.btn_open.hide()
        try:
            icon = card.style().standardIcon(card.style().StandardPixmap.SP_MediaPause)
            card.btn_pause.setIcon(icon)
        except AttributeError:
            pass
        card.btn_pause.setToolTip("Pause")
        card.btn_pause.show()
        card.btn_cancel.show()

        worker = DownloadWorker(url, format_code, save_path)
        worker.progress_signal.connect(card.update_progress)
        worker.status_signal.connect(card.update_status)
        card.set_worker(worker)

        self.waiting_workers.append(worker)
        self.process_queue()

    def process_queue(self):
        while len(self.active_workers) < self.max_concurrent and self.waiting_workers:
            worker = self.waiting_workers.pop(0) 
            self.active_workers.append(worker)   
            worker.finished.connect(self.on_worker_finished)
            worker.start() 

    def action_pause_resume_all(self):
        is_pausing = "Pause" in self.btn_pause_all.text()
        self.btn_pause_all.setText("▶️ Resume All" if is_pausing else "⏸️ Pause All")
        
        for widget in self.get_download_cards():
            if widget.btn_pause.isVisible():
                if is_pausing and widget.btn_pause.toolTip() == "Pause":
                    widget.btn_pause.click()
                elif not is_pausing and widget.btn_pause.toolTip() == "Resume":
                    widget.btn_pause.click()

    def action_cancel_all(self):
        self.waiting_workers.clear() 
        for widget in self.get_download_cards():
            if widget.btn_cancel.isVisible():
                widget.btn_cancel.click()

    def action_clear_all(self):
        for widget in reversed(self.get_download_cards()):
            status = widget.status_label.text()
            if "✅" in status or "❌" in status:
                
                if hasattr(widget, 'worker') and widget.worker:
                    widget.worker.deleteLater()
            
                widget.setParent(None)
                widget.deleteLater()

    def on_worker_finished(self):
        worker = self.sender() 
        if worker in self.active_workers:
            self.active_workers.remove(worker) 
        worker.deleteLater()
        self.process_queue()