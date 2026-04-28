import sys
import os
import re
import urllib.request
import yt_dlp
import time
import subprocess
import glob
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QProgressBar, QComboBox,
                             QFileDialog, QTabWidget, QScrollArea, QFrame)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon, QPainter

def resource_path(relative_path):
    import sys, os
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ResponsiveImage(QLabel):
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Expanding)
        self.setMinimumHeight(120)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update_image()

    def resizeEvent(self, event):
        if self._pixmap:
            self.update_image()
        super().resizeEvent(event)

    def update_image(self):
        if self._pixmap and not self.size().isEmpty():
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            super().setPixmap(scaled)

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Preferred)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)

    def sizeHint(self):
        metrics = self.fontMetrics()
        return metrics.size(Qt.TextFlag.TextSingleLine, self._full_text)

    def minimumSizeHint(self):
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance("..."), metrics.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)

class InspectWorker(QThread):
    result_signal = pyqtSignal(str, int, bytes, list) 
    error_signal = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def format_size(self, bytes_size):
        if not bytes_size: return "(Size Unknown)"
        mb = bytes_size / (1024 * 1024)
        if mb < 1: return f"{bytes_size / 1024:.1f} KB"
        return f"{mb:.1f} MB"

    def get_video_label(self, h):
        if h <= 144: return "Very Low"
        elif h <= 240: return "Low"
        elif h <= 360: return "Medium"
        elif h <= 480: return "Standard (SD)"
        elif h <= 720: return "High (HD)"
        elif h <= 1080: return "Full HD"
        elif h <= 1440: return "2K"
        else: return "4K"

    def calc_audio_size(self, bitrate_kbps, duration_sec):
        if not duration_sec: return "(Size Unknown)"
        mb = (bitrate_kbps * duration_sec) / 8192
        return f"{mb:.1f} MB"

    def run(self):
        ydl_opts = {'quiet': True, 'nocolor': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                
                formats = info.get('formats', [])
                video_formats = {} 
                
                for f in formats:
                    size = f.get('filesize') or f.get('filesize_approx') or 0
                    h = f.get('height')
                    if f.get('vcodec') != 'none' and h and h >= 144:
                        if h not in video_formats or size > video_formats[h]:
                            video_formats[h] = size

                format_list = []
                
                for h in sorted(video_formats.keys(), reverse=True):
                    size_str = self.format_size(video_formats[h])
                    label = self.get_video_label(h)
                    display_text = f"🎬 {h}p - {label} - {size_str}"
                    format_code = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                    format_list.append({'type': 'video', 'label': display_text, 'format_code': format_code})
                
                if video_formats:
                    format_list.append({'type': 'separator'})
                
                audio_options = [
                    {'label': "🎵 M4A (128K) - Mobile Optimized (Fast)", 'codec': 'm4a', 'br': '128'},
                    {'label': "🎵 MP3 (70K) - Low Quality (Space Saver)", 'codec': 'mp3', 'br': '70'},
                    {'label': "🎵 MP3 (128K) - Standard (Classic)", 'codec': 'mp3', 'br': '128'},
                    {'label': "🎵 MP3 (160K) - High Quality (Headphones)", 'codec': 'mp3', 'br': '160'},
                    {'label': "🎵 MP3 (320K) - Ultra Quality (Amplifiers)", 'codec': 'mp3', 'br': '320'},
                ]
                
                for opt in audio_options:
                    size_str = self.calc_audio_size(int(opt['br']), duration)
                    display_text = f"{opt['label']} - {size_str}"
                    format_code = f"audio:{opt['codec']}:{opt['br']}"
                    format_list.append({'type': 'audio', 'label': display_text, 'format_code': format_code})

                thumbnail_url = info.get('thumbnail')
                image_data = b''
                if thumbnail_url:
                    try:
                        req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        image_data = urllib.request.urlopen(req, timeout=5).read()
                    except Exception:
                        pass
                        
                self.result_signal.emit(title, duration, image_data, format_list)
        except Exception as e:
            self.error_signal.emit("❌ Error: Please check the URL")

class DownloadWorker(QThread):
    status_signal = pyqtSignal(str) 
    progress_signal = pyqtSignal(int)

    def __init__(self, url, format_code, save_path):
        super().__init__()
        self.url = url
        self.format_code = format_code 
        self.save_path = save_path

        self.is_paused = False
        self.is_cancelled = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True
        self.is_paused = False

    def clean_ansi(self, text):
        return re.sub(r'\x1b\[[0-9;]*m', '', str(text)).strip()

    def cleanup_files(self):
        time.sleep(1) 
        import os
        import glob
        base_name = os.path.splitext(self.save_path)[0]
        possible_files = glob.glob(f"{base_name}*")
        for f in possible_files:
            try:
                os.remove(f)
            except:
                pass

    def my_hook(self, d):
        if self.is_cancelled:
            raise Exception("DOWNLOAD_CANCELLED")

        while self.is_paused:
            if self.is_cancelled:
                raise Exception("DOWNLOAD_CANCELLED")
            time.sleep(0.5)

        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%')
            p_clean = self.clean_ansi(p_str).replace('%', '')
            
            speed_clean = self.clean_ansi(d.get('_speed_str', 'N/A'))
            eta_clean = self.clean_ansi(d.get('_eta_str', 'N/A'))
            downloaded_clean = self.clean_ansi(d.get('_downloaded_bytes_str', '0B'))
            total_clean = self.clean_ansi(d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', 'Unknown'))
            
            try:
                percent_val = int(float(p_clean))
                self.progress_signal.emit(percent_val)
                status_text = f"⏳ Downloading... {downloaded_clean} / {total_clean} | Speed: {speed_clean} | ETA: {eta_clean}"
                self.status_signal.emit(status_text)
            except ValueError:
                pass
                
        elif d['status'] == 'finished':
            self.progress_signal.emit(100)
            self.status_signal.emit("⚙️ Processing... please wait.")

    def run(self):
        ydl_opts = {
            'outtmpl': self.save_path,
            'quiet': True,
            'nocolor': True,
            'writethumbnail': True, 
            'progress_hooks': [self.my_hook],
            'postprocessors': [],
            'overwrites': True   
        }

        if self.format_code.startswith("audio:"):
            _, codec, bitrate = self.format_code.split(":")
            ydl_opts['format'] = 'bestaudio/best' 
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,     
                'preferredquality': bitrate, 
            })
        else:
            ydl_opts['format'] = self.format_code

            chosen_ext = os.path.splitext(self.save_path)[1].lower().replace('.', '')

            if chosen_ext in ['mp4', 'mkv']:
                ydl_opts['merge_output_format'] = chosen_ext

        ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
        ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

        try:
            self.status_signal.emit("⏳ Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if not self.is_cancelled:
                self.status_signal.emit("✅ Download!")
        except Exception as e:
            if str(e) == "DOWNLOAD_CANCELLED":
                self.status_signal.emit("❌ Canceled")
                self.cleanup_files()
            else:
                self.status_signal.emit("❌ Error: Check connection.")

class DownloadCard(QFrame):
    def __init__(self, title, thumbnail_pixmap, save_path=""):
        super().__init__()
        self.save_path = save_path
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.setStyleSheet("""
            QFrame {
                border: 1px solid gray;
                border-radius: 10px;
                margin: 2px;
            }
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 5px;
            }
        """)
        self.setMinimumHeight(110)

        layout = QHBoxLayout(self)

        self.thumb_label = QLabel()
        if thumbnail_pixmap:
            scaled_thumb = thumbnail_pixmap.scaled(140, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumb_label.setPixmap(scaled_thumb)
        self.thumb_label.setFixedWidth(140)
        layout.addWidget(self.thumb_label)

        details_layout = QVBoxLayout()

        top_row_layout = QHBoxLayout()
 
        self.title_label = ElidedLabel(title) 
        self.title_label.setToolTip(title) 
        self.title_label.setStyleSheet("font-weight: bold; border: none;")
        card_font = self.title_label.font()
        card_font.setPointSize(card_font.pointSize() + 1)
        self.title_label.setFont(card_font)
        top_row_layout.addWidget(self.title_label)
        
        top_row_layout.addStretch()

        self.btn_pause = QPushButton("⏸️")
        self.btn_pause.setToolTip("Pause")
        self.btn_pause.setFixedSize(30, 30)
        
        self.btn_cancel = QPushButton("❌")
        self.btn_cancel.setToolTip("Cancel")
        self.btn_cancel.setFixedSize(30, 30)
        
        self.btn_reload = QPushButton("🔄")
        self.btn_reload.setToolTip("Reload")
        self.btn_reload.setFixedSize(30, 30)
        self.btn_reload.hide()
        
        self.btn_open = QPushButton("📁")
        self.btn_open.setToolTip("Open Folder")
        self.btn_open.setFixedSize(30, 30)
        self.btn_open.hide()

        top_row_layout.addWidget(self.btn_pause)
        top_row_layout.addWidget(self.btn_cancel)
        top_row_layout.addWidget(self.btn_reload)
        top_row_layout.addWidget(self.btn_open)

        details_layout.addLayout(top_row_layout)

        self.p_bar = QProgressBar()
        self.p_bar.setMinimumHeight(20)
        self.p_bar.setStyleSheet("""
            QProgressBar {
                text-align: center; 
                font-size: 10pt; 
                font-weight: bold;
                border: 1px solid #888888;
                border-radius: 9px;
                background-color: rgba(0, 0, 0, 0.05);
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 8px;
            }
        """)
        self.p_bar.setValue(0)
        details_layout.addWidget(self.p_bar)

        self.status_label = QLabel("Waiting...")
        self.status_label.setStyleSheet("border: none; font-size: 9pt;")
        details_layout.addWidget(self.status_label)

        layout.addLayout(details_layout)

        self.btn_cancel.clicked.connect(self.action_cancel)
        self.btn_pause.clicked.connect(self.action_pause_resume)
        self.btn_open.clicked.connect(self.action_open_folder)

    def update_progress(self, val):
        self.p_bar.setValue(val)

    def update_status(self, msg):
        self.status_label.setText(msg)
        if "✅" in msg:
            self.btn_pause.hide()
            self.btn_cancel.hide()
            self.btn_reload.hide()
            self.btn_open.show()

    def action_cancel(self):
        self.status_label.setText("❌ Canceled")
        self.p_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_reload.show()
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()

    def action_pause_resume(self):
        if self.btn_pause.text() == "⏸️":
            self.btn_pause.setText("▶️")
            self.btn_pause.setToolTip("Resume")
            self.status_label.setText("⏸️ Paused")
            if hasattr(self, 'worker') and self.worker:
                self.worker.pause()
        else:
            self.btn_pause.setText("⏸️")
            self.btn_pause.setToolTip("Pause")
            self.status_label.setText("⏳ Resuming...")
            if hasattr(self, 'worker') and self.worker:
                self.worker.resume()

    def action_open_folder(self):
        path = os.path.normpath(self.save_path)
        folder_path = os.path.dirname(path)
        base_name = os.path.splitext(path)[0]

        possible_files = glob.glob(f"{base_name}.*")
        
        if possible_files:
            subprocess.Popen(f'explorer /select,"{possible_files[0]}"')
        elif os.path.exists(folder_path):
            os.startfile(folder_path)
        else:
            self.status_label.setText("❌ File deleted or moved!")

    def set_worker(self, worker):
        self.worker = worker

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
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

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        self.thumb_label = ResponsiveImage()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.hide()
        info_layout.addWidget(self.thumb_label)

        self.title_label = ElidedLabel('', self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold;") 

        title_font = self.title_label.font()
        title_font.setPointSize(title_font.pointSize() + 2)
        self.title_label.setFont(title_font) 
        info_layout.addWidget(self.title_label)

        self.duration_label = QLabel('', self)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet("")
        info_layout.addWidget(self.duration_label)

        main_layout.addLayout(info_layout)

        self.format_combo = QComboBox(self)
        self.format_combo.hide()
        self.format_combo.addItem("Waiting for URL...", "")
        self.format_combo.setEnabled(False)
        main_layout.addWidget(self.format_combo)

        main_layout.addStretch() 

        home_controls_layout = QHBoxLayout()
        self.download_btn = QPushButton('🚀 Start Download', self)
        self.download_btn.setFixedHeight(40)
        self.download_btn.hide()
        self.download_btn.setEnabled(False) 
        self.download_btn.clicked.connect(self.start_download)
        
        home_controls_layout.addWidget(self.download_btn)
        main_layout.addLayout(home_controls_layout)

        queue_layout = QVBoxLayout(self.tab_queue)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }") 
        
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
        url = self.url_input.text()
        if not url:
            self.title_label.setText("⚠️ Please enter a URL first!")
            return

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
        
        self.inspect_worker = InspectWorker(url)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.start()

    def on_inspect_success(self, title, duration_secs, image_data, format_list):
        self.clean_title = re.sub(r'[\\/*?:"<>|]', "", title)

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

    def on_inspect_error(self, error_msg):
        self.reset_ui_state()
        self.title_label.setText(error_msg)

    def start_download(self):
        url = self.url_input.text()
        if not url: return

        format_code = self.format_combo.currentData()
        if format_code.startswith("audio:"):
            _, codec, _ = format_code.split(":")
            filter_str = f"Audio Files (*.{codec})"
        else:
            filter_str = "MP4 Video (*.mp4);;MKV Video (*.mkv)"

        default_path = os.path.join(self.last_save_dir, self.clean_title)
        
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

        new_card = DownloadCard(self.title_label.toolTip(), self.thumb_label.pixmap(), save_path)
        self.cards_layout.insertWidget(0, new_card) 
        
        self.tabs.setCurrentIndex(1)
        
        self.on_text_changed("") 
        self.url_input.clear()

        worker = DownloadWorker(url, format_code, save_path)
        worker.progress_signal.connect(new_card.update_progress)
        worker.status_signal.connect(new_card.update_status)

        new_card.set_worker(worker)
        new_card.btn_reload.clicked.connect(lambda: self.reload_download(new_card, url, format_code, save_path))
        
        self.waiting_workers.append(worker)
        new_card.update_status("⏳ Waiting in queue...") 
        
        self.process_queue()

    def reload_download(self, card, url, format_code, save_path):
        card.status_label.setText("⏳ Waiting in queue...")
        card.p_bar.setValue(0)
        
        card.p_bar.setStyleSheet("text-align: center; font-size: 10pt; font-weight: bold;")

        card.btn_reload.hide()
        card.btn_pause.setText("⏸️")
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
                if is_pausing and widget.btn_pause.text() == "⏸️":
                    widget.btn_pause.click()
                elif not is_pausing and widget.btn_pause.text() == "▶️":
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
                widget.setParent(None)
                widget.deleteLater()

    def on_worker_finished(self):
        worker = self.sender() 
        if worker in self.active_workers:
            self.active_workers.remove(worker) 
        
        self.process_queue()

if __name__ == '__main__':
    import ctypes
    try:
        myappid = 'ahs.mediadl.pro.version1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

    app = QApplication(sys.argv)
    ex = VideoDownloader()
    ex.show()
    sys.exit(app.exec())