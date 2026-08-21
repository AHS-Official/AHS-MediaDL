import os
import re
import urllib.request
import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal

class ThumbnailWorker(QThread):
    thumb_loaded = pyqtSignal(int, bytes)

    def __init__(self, index, thumb_url=None, video_id=None):
        super().__init__()
        self.index = index
        self.thumb_url = thumb_url
        self.video_id = video_id

    def run(self):
        url = self.thumb_url
        if isinstance(url, list) and url:
            last = url[-1]
            url = last.get('url') if isinstance(last, dict) else last
        elif isinstance(url, dict):
            url = url.get('url')

        if not isinstance(url, str):
            url = None
        else:
            url = url.strip()

        if not url and self.video_id:
            url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"
        elif url and not (url.startswith("http://") or url.startswith("https://")):
            # If a video_id was passed as the second positional argument (thumb_url)
            self.video_id = url
            url = f"https://img.youtube.com/vi/{url}/hqdefault.jpg"

        if not url:
            return

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.thumb_loaded.emit(self.index, data)
        except Exception as e:
            # Fallback to YouTube thumbnail format if we have a video_id and primary fetch failed
            if self.video_id and url != f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg":
                try:
                    fallback_url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"
                    req = urllib.request.Request(fallback_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = response.read()
                        self.thumb_loaded.emit(self.index, data)
                except Exception as fb_e:
                    print(f"Thumbnail error for {self.video_id or url}: {fb_e}")
            else:
                print(f"Thumbnail error for {self.video_id or url}: {e}")

class InfoFetcher(QThread):
    info_received = pyqtSignal(dict, bytes)
    error_received = pyqtSignal(str)

    def __init__(self, url, fetch_playlist=False):
        super().__init__()
        self.url = url
        self.fetch_playlist = fetch_playlist
        self.is_cancelled = False

    def cancel_fetch(self):
        self.is_cancelled = True

    def run(self):
        try:
            target_url = self.url
            
            # Smart filter: if the URL contains both video and playlist, separate and force playlist
            if self.fetch_playlist and "list=" in target_url:
                match = re.search(r"list=([a-zA-Z0-9_-]+)", target_url)
                if match:
                    playlist_id = match.group(1)
                    target_url = f"https://www.youtube.com/playlist?list={playlist_id}"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': not self.fetch_playlist,
                'extract_flat': self.fetch_playlist,
                'skip_download': True,
                'socket_timeout': 15,
                'clean_infojson': False
            }
            
            from utils.settings import app_config
            browser = app_config.get("browser_cookies", "none")
            if browser == "custom":
                cookie_path = app_config.get("cookie_file", "")
                if cookie_path and os.path.exists(cookie_path):
                    ydl_opts['cookiefile'] = cookie_path
            elif browser != "none": 
                ydl_opts['cookiesfrombrowser'] = (browser,)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                if not self.is_cancelled:
                    self.info_received.emit(info, b'')
        except Exception as e:
            if not self.is_cancelled:
                self.error_received.emit(str(e))