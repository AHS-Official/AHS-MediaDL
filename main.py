import sys
import os
import re
import urllib.request
import yt_dlp
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QProgressBar, QComboBox,
                             QFileDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

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
                    format_code = f"audio:{opt['codec']}:{opt['br']}"
                    format_list.append({'type': 'audio', 'label': display_text, 'format_code': format_code})

                thumbnail_url = info.get('thumbnail')
                image_data = b''
                if thumbnail_url:
                    try:
                        req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        image_data = urllib.request.urlopen(req).read()
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

    def my_hook(self, d):
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%')
            p_clean = re.sub(r'\x1b\[[0-9;]*m', '', p_str).replace('%', '').strip()
            
            speed_raw = d.get('_speed_str', 'N/A')
            eta_raw = d.get('_eta_str', 'N/A')
            
            downloaded_raw = d.get('_downloaded_bytes_str', '0B')
            total_raw = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', 'Unknown')
            
            speed_clean = re.sub(r'\x1b\[[0-9;]*m', '', speed_raw).strip()
            eta_clean = re.sub(r'\x1b\[[0-9;]*m', '', eta_raw).strip()
            downloaded_clean = re.sub(r'\x1b\[[0-9;]*m', '', downloaded_raw).strip()
            total_clean = re.sub(r'\x1b\[[0-9;]*m', '', total_raw).strip()
            
            try:
                percent_val = int(float(p_clean))
                self.progress_signal.emit(percent_val)
                
                status_text = f"⏳ Downloading... {downloaded_clean} / {total_clean} | Speed: {speed_clean} | ETA: {eta_clean}"
                self.status_signal.emit(status_text)
            except ValueError:
                pass
                
        elif d['status'] == 'finished':
            self.progress_signal.emit(100)
            self.status_signal.emit("✅ Processing/Converting... please wait.")

    def run(self):
        ydl_opts = {
            'outtmpl': self.save_path,
            'quiet': True,
            'nocolor': True,
            'writethumbnail': True,
            'progress_hooks': [self.my_hook],
            'postprocessors': []
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

        ydl_opts['postprocessors'].append({
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        })
        ydl_opts['postprocessors'].append({
            'key': 'EmbedThumbnail',
            'already_have_thumbnail': False,
        })

        try:
            self.status_signal.emit("⏳ Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.status_signal.emit("✅ Download & Embedding Complete!")
        except Exception as e:
            self.status_signal.emit("❌ Error: Check your connection or FFmpeg.")

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.last_save_dir = os.path.expanduser('~/Downloads')
        self.clean_title = "video"
        self.initUI()

    def initUI(self):
        self.setWindowTitle('AHS-MediaDL V1')
        self.setGeometry(300, 300, 550, 400)

        main_layout = QVBoxLayout()

        url_layout = QHBoxLayout()

        self.paste_btn = QPushButton('📋', self)
        self.paste_btn.setToolTip('Paste')
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
        self.inspect_btn.setToolTip('Inspect URL')
        self.inspect_btn.setFixedWidth(40)
        self.inspect_btn.clicked.connect(self.inspect_url)
        url_layout.addWidget(self.inspect_btn)

        main_layout.addLayout(url_layout)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        self.thumb_label = QLabel(self)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.hide()
        info_layout.addWidget(self.thumb_label)

        self.title_label = QLabel('', self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #222;") 
        info_layout.addWidget(self.title_label)

        self.duration_label = QLabel('', self)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet("color: #555; font-size: 11px;")
        info_layout.addWidget(self.duration_label)

        main_layout.addLayout(info_layout)

        self.format_combo = QComboBox(self)
        self.format_combo.addItem("Waiting for URL...", "")
        self.format_combo.setEnabled(False)
        main_layout.addWidget(self.format_combo)

        self.download_btn = QPushButton('Start Download', self)
        self.download_btn.setEnabled(False) 
        self.download_btn.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_btn)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel('Status: Ready', self)
        main_layout.addWidget(self.status_label)
        
        main_layout.addStretch() 
        self.setLayout(main_layout)

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def on_text_changed(self, text):
        if not text: 
            self.title_label.setText("")
            self.title_label.setToolTip("")
            self.duration_label.setText("")
            self.thumb_label.hide()
            self.thumb_label.clear()
            self.progress_bar.setValue(0)
            self.status_label.setText("Status: Ready")
            self.clean_title = "video"
            self.format_combo.clear()
            self.format_combo.addItem("Waiting for URL...", "")
            self.format_combo.setEnabled(False)
            self.download_btn.setEnabled(False)

    def inspect_url(self):
        url = self.url_input.text()
        if not url:
            self.status_label.setText("⚠️ Please enter a URL first!")
            return

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

        display_title = title if len(title) <= 60 else title[:57] + "..."
        self.title_label.setToolTip(title)
        self.title_label.setText(display_title)

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
            scaled_pixmap = pixmap.scaled(200, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumb_label.setPixmap(scaled_pixmap)
            self.thumb_label.show()
            
        self.format_combo.clear()
        for item in format_list:
            if item['type'] == 'separator':
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(item['label'], item['format_code'])
        
        self.format_combo.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.status_label.setText("Status: Ready to download")

    def on_inspect_error(self, error_msg):
        self.title_label.setText(error_msg)
        self.duration_label.setText("")
        self.thumb_label.hide()
        self.status_label.setText("Status: Error")

    def start_download(self):
        url = self.url_input.text()
        if not url: return

        format_code = self.format_combo.currentData()
        
        if format_code.startswith("audio:"):
            _, codec, _ = format_code.split(":")
            ext = f".{codec}" # mp3 or m4a
        else:
            ext = ".mp4"

        default_path = os.path.join(self.last_save_dir, self.clean_title + ext)
        file_filter = f"Media Files (*{ext});;All Files (*)"
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video As", default_path, file_filter)

        if not save_path: return 

        self.last_save_dir = os.path.dirname(save_path)
        self.download_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.url_input.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.worker = DownloadWorker(url, format_code, save_path)
        self.worker.status_signal.connect(self.update_status)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.start()

    def update_status(self, message):
        self.status_label.setText(message)
        if "✅" in message or "❌" in message:
            self.download_btn.setEnabled(True)
            self.format_combo.setEnabled(True)
            self.url_input.setEnabled(True)

    def update_progress(self, percent):
        self.progress_bar.setValue(percent)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoDownloader()
    ex.show()
    sys.exit(app.exec())