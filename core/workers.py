import os
import re
import time
import urllib.request
import yt_dlp
import glob
import concurrent.futures
from PyQt6.QtCore import QThread, pyqtSignal



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

def apply_metadata(target_file, metadata):
    """
    Applies custom metadata (title, artist, album) to an audio file (mp3 or m4a) using ffmpeg.
    """
    import subprocess
    import tempfile
    
    if not os.path.exists(target_file):
        return
        
    ext = os.path.splitext(target_file)[1]
    dir_name = os.path.dirname(target_file)
    
    # Create temp file in the same directory to make replacement atomic
    fd, temp_file_path = tempfile.mkstemp(suffix=ext, dir=dir_name)
    os.close(fd)
    
    cmd = ['ffmpeg', '-y', '-i', target_file]
    for key, value in metadata.items():
        if value:
            cmd.extend(['-metadata', f'{key}={value}'])
            
    cmd.extend(['-codec', 'copy', temp_file_path])
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
        subprocess.run(cmd, startupinfo=startupinfo, capture_output=True, text=True, check=True)
        os.replace(temp_file_path, target_file)
    except Exception as e:
        print(f"Error applying metadata: {e}")
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass