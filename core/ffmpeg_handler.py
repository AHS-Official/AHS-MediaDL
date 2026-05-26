from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import urllib.request
import json
import re

class InfoFetcher(QThread):
    info_received = pyqtSignal(dict, bytes) 
    error_received = pyqtSignal(str)

    def __init__(self, url, fetch_playlist=False): 
        super().__init__()
        self.url = url
        self.fetch_playlist = fetch_playlist

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
            
            if not self.fetch_playlist:
                ydl_opts['extractor_args'] = {'youtube': ['player_client=web']}

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                self.info_received.emit(info, b'')
        except Exception as e:
            self.error_received.emit(str(e))


class ThumbnailWorker(QThread):
    thumb_loaded = pyqtSignal(int, bytes)

    def __init__(self, index, video_id): 
        super().__init__()
        self.index = index
        self.video_id = video_id

    def run(self):
        if not self.video_id:
            return
        # Build thumbnail URL manually from YouTube (faster and reliable)
        # Use mqdefault.jpg for 16:9 ratio and without black bars
        url = f"https://i.ytimg.com/vi/{self.video_id}/mqdefault.jpg"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read()
                self.thumb_loaded.emit(self.index, data)
        except Exception as e:
            pass


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
