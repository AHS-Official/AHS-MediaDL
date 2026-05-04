import os
import re
import time
import urllib.request
import yt_dlp
import glob
import concurrent.futures
from PyQt6.QtCore import QThread, pyqtSignal

class InspectWorker(QThread):
    result_signal = pyqtSignal(str, int, bytes, list)
    playlist_signal = pyqtSignal(str, bytes, list) 
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
        mb = (bitrate_kbps * duration_sec) / 8000
        return f"{mb:.1f} MB"

    def run(self):
        ydl_opts = {'quiet': True, 'nocolor': True, 'extract_flat': 'in_playlist'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                
                if 'entries' in info:
                    title = info.get('title', 'Unknown Playlist')
                    entries = []
                    
                    for entry in info.get('entries', []):
                        if entry:
                            video_title = entry.get('title', '')
                            bad_titles = ['[private video]', '[deleted video]', '[unavailable video]']
                            if not video_title or video_title.lower() in bad_titles:
                                continue
                                
                            entries.append({
                                'id': entry.get('id'),
                                'title': video_title,
                                'url': entry.get('url', f"https://www.youtube.com/watch?v={entry.get('id')}")
                            })
                    
                    thumbnail_url = info.get('thumbnail')
                    image_data = b''
                    if thumbnail_url:
                        try:
                            req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                            image_data = urllib.request.urlopen(req, timeout=5).read()
                        except Exception:
                            pass
                            
                    self.playlist_signal.emit(title, image_data, entries)

                else:
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
        except Exception:
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

        self.last_update_time = 0
        self.last_percent = -1

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
        base_name = os.path.splitext(self.save_path)[0]
        possible_files = glob.glob(f"{base_name}*")
        for f in possible_files:
            if f.endswith('.part') or f.endswith('.ytdl') or f == self.save_path:
                try:
                    os.remove(f)
                except OSError:
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
                current_time = time.time()

                if (current_time - self.last_update_time > 0.5) or (percent_val != self.last_percent):
                    self.progress_signal.emit(percent_val)
                    status_text = f"⏳ Downloading... {downloaded_clean} / {total_clean} | Speed: {speed_clean} | ETA: {eta_clean}"
                    self.status_signal.emit(status_text)
                    self.last_update_time = current_time
                    self.last_percent = percent_val
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
            parts = self.format_code.split(":")
            if len(parts) == 3:
                _, codec, bitrate = parts
            else:
                codec = "mp3"
                bitrate = "128"
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
        ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
        ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

        try:
            self.status_signal.emit("⏳ Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if not self.is_cancelled:
                self.status_signal.emit("✅ Done!")
        except Exception as e:
            if str(e) == "DOWNLOAD_CANCELLED":
                self.status_signal.emit("❌ Canceled")
                self.cleanup_files()
            else:
                if os.path.exists(self.save_path):
                    self.status_signal.emit("✅ Downloaded (Warning: Cover failed)")
                else:
                    self.status_signal.emit("❌ Error: Check connection.")

class ThumbnailWorker(QThread):
    thumb_loaded = pyqtSignal(int, bytes)

    def __init__(self, index, video_id):
        super().__init__()
        self.index = index
        self.video_id = video_id

    def run(self):
        url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"
        try:
            import urllib.request
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.thumb_loaded.emit(self.index, data)
        except Exception as e:
            print(f"Thumbnail error for {self.video_id}: {e}")