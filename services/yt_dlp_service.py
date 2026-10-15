import os
import json
import time
import shutil
import urllib.request
import urllib.parse
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QObject, QMutex, QMutexLocker, QThreadPool
from utils.locales import tr
from utils.logger import logger
from managers.binary_manager import BinaryManager


def get_ytdlp_cli_args():
    """Generates standard CLI flags for cookies, JS runtimes, and extractor arguments."""
    from core.ffmpeg_handler import get_binary_path
    from managers.settings_manager import SettingsManager

    args = ["--no-colors", "--no-warnings"]
    mgr = SettingsManager()
    cookies_type = mgr.get("cookies_type", "none")
    if cookies_type in ["chrome", "firefox", "edge", "brave", "opera", "safari", "vivaldi"]:
        args += ["--cookies-from-browser", cookies_type]
    elif cookies_type == "custom":
        custom_path = mgr.get("custom_cookies_path", "")
        if custom_path and os.path.exists(custom_path):
            args += ["--cookies", custom_path]

    # Auto-detect available JS runtime (Deno, Node, Bun, QuickJS)
    for rt in ["deno", "node", "bun", "quickjs"]:
        rt_path = get_binary_path(rt) or shutil.which(rt)
        if rt_path:
            args += ["--js-runtimes", f"{rt}:{rt_path}"]

    # YouTube client arguments to prevent 403 Forbidden
    args += ["--extractor-args", "youtube:player_client=default,ios,web_creator"]
    return args


def load_cookies_opts():
    """Backwards-compatible helper returning a dictionary for legacy callers."""
    return {}


def run_ytdlp_json(extra_args: list, cancel_check=None) -> dict:
    """
    Executes yt-dlp.exe with --dump-single-json and parses the stdout JSON dict.
    Supports cancellation polling and hides console window on Windows.
    """
    ytdlp_path = BinaryManager.get_binary_path("yt-dlp")
    if not ytdlp_path:
        raise Exception(tr("error_ytdlp_missing", "yt-dlp executable not found. Please ensure yt-dlp.exe is in PATH or bin/ folder."))

    cmd = [ytdlp_path] + get_ytdlp_cli_args() + extra_args + ["--dump-single-json"]

    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        startupinfo=startupinfo,
        creationflags=creationflags
    )

    try:
        if cancel_check:
            while True:
                if cancel_check():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    raise Exception("CANCELLED")
                try:
                    stdout, stderr = proc.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    continue
        else:
            stdout, stderr = proc.communicate()
    except Exception as e:
        try:
            proc.terminate()
        except Exception:
            pass
        raise e

    if proc.returncode != 0:
        err_msg = stderr.strip() if stderr else f"yt-dlp process returned code {proc.returncode}"
        raise Exception(err_msg)

    idx_start = stdout.find('{')
    idx_end = stdout.rfind('}')
    if idx_start != -1 and idx_end != -1:
        return json.loads(stdout[idx_start:idx_end + 1])
    return json.loads(stdout)


class SafeYoutubeDL:
    """Stub class preserved for backwards compatibility."""
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def extract_info(self, url, download=False):
        return run_ytdlp_json(["--flat-playlist", url])


class ThumbnailRunnableSignals(QObject):
    thumb_loaded = pyqtSignal(int, bytes)


class ThumbnailRunnable(QRunnable):
    def __init__(self, index, thumbnail_url):
        super().__init__()
        self.index = index
        self.thumbnail_url = thumbnail_url
        self.signals = ThumbnailRunnableSignals()

    def run(self):
        if not self.thumbnail_url:
            return
        url = self.thumbnail_url
        if url.startswith("//"):
            url = f"https:{url}"
        elif not url.startswith("http"):
            url = f"https://img.youtube.com/vi/{self.thumbnail_url}/hqdefault.jpg"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.signals.thumb_loaded.emit(self.index, data)
        except Exception as e:
            logger.warning(f"Thumbnail error for {url}: {e}")


class SearchWorker(QThread):
    results_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, query, video_offset=1, playlist_offset=1):
        super().__init__()
        self.query = query
        self.video_offset = video_offset
        self.playlist_offset = playlist_offset

    def run(self):
        try:
            # 1. Fetch videos
            video_query = f"ytsearch500:{self.query}"
            v_items = f"{self.video_offset}:{self.video_offset + 9}"
            v_args = ["--flat-playlist", "--playlist-items", v_items, video_query]
            info = run_ytdlp_json(v_args)
            videos = []
            for entry in info.get('entries', []):
                if entry:
                    title = entry.get('title', '')
                    bad_titles = ['[private video]', '[deleted video]', '[unavailable video]']
                    if not title or title.lower() in bad_titles:
                        continue
                    thumb = entry.get('thumbnail')
                    if not thumb and entry.get('thumbnails'):
                        thumb = entry.get('thumbnails')[0].get('url')
                    videos.append({
                        'id': entry.get('id'),
                        'title': title,
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        'thumbnail': thumb,
                        'uploader': entry.get('uploader') or entry.get('channel', 'Unknown Channel'),
                        'duration': entry.get('duration'),
                        'view_count': entry.get('view_count'),
                        'is_playlist': False
                    })

            # 2. Fetch playlists
            encoded_query = urllib.parse.quote_plus(self.query)
            playlist_query = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAw%253D%253D"
            p_items = f"{self.playlist_offset}:{self.playlist_offset + 4}"
            p_args = ["--flat-playlist", "--playlist-items", p_items, playlist_query]
            info_p = run_ytdlp_json(p_args)
            playlists = []
            for entry in info_p.get('entries', []):
                if entry:
                    title = entry.get('title', '')
                    if not title:
                        continue
                    thumb = entry.get('thumbnail')
                    if not thumb and entry.get('thumbnails'):
                        thumb = entry.get('thumbnails')[0].get('url')
                    playlists.append({
                        'id': entry.get('id'),
                        'title': title,
                        'url': entry.get('url') or f"https://www.youtube.com/playlist?list={entry.get('id')}",
                        'thumbnail': thumb,
                        'uploader': entry.get('uploader') or entry.get('channel', 'Unknown Channel'),
                        'duration': None,
                        'view_count': entry.get('video_count') or entry.get('playlist_count'),
                        'is_playlist': True
                    })

            # 3. Interleave and merge results (e.g. 2 videos, 1 playlist)
            merged = []
            v_idx = 0
            p_idx = 0
            while v_idx < len(videos) or p_idx < len(playlists):
                for _ in range(2):
                    if v_idx < len(videos):
                        merged.append(videos[v_idx])
                        v_idx += 1
                if p_idx < len(playlists):
                    merged.append(playlists[p_idx])
                    p_idx += 1

            self.results_signal.emit(merged)
        except Exception as e:
            self.error_signal.emit(str(e))


class SingleInspectRunnable(QRunnable):
    def __init__(self, index, url, callback):
        super().__init__()
        self.index = index
        self.url = url
        self.callback = callback

    def run(self):
        clean_url = self.url.strip()
        if clean_url.lower().startswith("dl:"):
            clean_url = clean_url[3:].strip()
        try:
            info = run_ytdlp_json(["--flat-playlist", clean_url])
            video_title = info.get('title', clean_url)
            video_id = info.get('id')
            duration = info.get('duration')
            self.callback(self.index, video_id, video_title, clean_url, duration)
        except Exception as e:
            logger.warning(f"Error inspecting url {clean_url}: {e}")
            self.callback(self.index, None, clean_url, clean_url, None)


class InspectWorker(QThread):
    result_signal = pyqtSignal(str, int, bytes, list, dict, dict)
    playlist_signal = pyqtSignal(str, bytes, list)
    thumbnail_signal = pyqtSignal(bytes)
    error_signal = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def format_size(self, bytes_size):
        if not bytes_size:
            return "(Size Unknown)"
        mb = bytes_size / (1024 * 1024)
        if mb < 1:
            return f"{bytes_size / 1024:.1f} KB"
        return f"{mb:.1f} MB"

    def get_video_label(self, h):
        if h <= 144:
            return "Very Low"
        elif h <= 240:
            return "Low"
        elif h <= 360:
            return "Medium"
        elif h <= 480:
            return "Standard (SD)"
        elif h <= 720:
            return "High (HD)"
        elif h <= 1080:
            return "Full HD"
        elif h <= 1440:
            return "2K"
        elif h <= 2160:
            return "4K"
        else:
            return "8K"

    def calc_audio_size(self, bitrate_kbps, duration_sec):
        if not duration_sec:
            return "(Size Unknown)"
        mb = (bitrate_kbps * duration_sec) / 8000
        return f"{mb:.1f} MB"

    def run(self):
        from managers.settings_manager import SettingsManager
        mgr = SettingsManager()
        show_thumbnails = mgr.get("show_thumbnails", True)

        if isinstance(self.url, list):
            title = tr("packages_title", "Collected Links Box")
            total = len(self.url)
            if total == 0:
                self.playlist_signal.emit(title, b'', [])
                return
            results = [None] * total
            completed = 0
            mutex = QMutex()

            def on_inspect_complete(index, video_id, video_title, clean_url, duration=None):
                nonlocal completed
                with QMutexLocker(mutex):
                    results[index] = {
                        'id': video_id,
                        'title': video_title,
                        'url': clean_url,
                        'duration': duration
                    }
                    completed += 1
                if completed == total:
                    self.playlist_signal.emit(title, b'', [r for r in results if r is not None])

            pool = QThreadPool()
            pool.setMaxThreadCount(8)
            for i, item_url in enumerate(self.url):
                runnable = SingleInspectRunnable(i, item_url, on_inspect_complete)
                pool.start(runnable)
            pool.waitForDone()
            return

        limit = mgr.get("mix_playlist_limit", 50)
        is_auto_playlist = False
        if isinstance(self.url, str):
            url_upper = self.url.upper()
            if "LIST=RD" in url_upper or "LIST=UL" in url_upper or "LIST=LL" in url_upper or "LIST=LM" in url_upper or "LIST=WL" in url_upper:
                is_auto_playlist = True

        extra_args = ["--flat-playlist"]
        if is_auto_playlist and limit > 0:
            extra_args += ["--playlist-end", str(limit)]
        extra_args.append(self.url)

        subtitles_dict = {}
        try:
            info = run_ytdlp_json(extra_args)
            if info.get('is_live'):
                raise Exception("Live streams are not supported for downloading.")

            if 'entries' in info:
                title = info.get('title', 'Unknown Playlist')
                playlist_uploader = info.get('uploader') or info.get('channel') or ''
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
                            'url': entry.get('url', f"https://www.youtube.com/watch?v={entry.get('id')}"),
                            'thumbnail': entry.get('thumbnail'),
                            'duration': entry.get('duration'),
                            'view_count': entry.get('view_count'),
                            'upload_date': entry.get('upload_date') or entry.get('release_date'),
                            'uploader': entry.get('uploader') or entry.get('channel') or playlist_uploader
                        })
                thumbnail_url = info.get('thumbnail')
                self.playlist_signal.emit(title, b'', entries)
                if thumbnail_url and show_thumbnails:
                    try:
                        req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        image_data = urllib.request.urlopen(req, timeout=5).read()
                        if image_data:
                            self.thumbnail_signal.emit(image_data)
                    except Exception as e:
                        logger.error(f"Failed to download playlist thumbnail: {e}")
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

                audio_formats = {}
                for f in formats:
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        abr = f.get('abr') or 0
                        ext = f.get('ext') or ''
                        abr_int = int(round(abr)) if abr > 0 else 0
                        if abr_int > 0:
                            key = (ext, abr_int)
                            size = f.get('filesize') or f.get('filesize_approx') or 0
                            if key not in audio_formats or size > audio_formats[key]['size']:
                                audio_formats[key] = {
                                    'format_id': f.get('format_id'),
                                    'ext': ext,
                                    'abr': abr_int,
                                    'size': size
                                }
                sorted_audio = sorted(audio_formats.values(), key=lambda x: x['abr'], reverse=True)
                for f_info in sorted_audio:
                    abr = f_info['abr']
                    ext = f_info['ext'].upper()
                    size_str = self.format_size(f_info['size'])
                    display_text = f"🎵 {ext} ({abr}kbps) - {size_str}"
                    format_code = f"audio:{f_info['format_id']}:{f_info['ext']}:{abr}"
                    format_list.append({'type': 'audio', 'label': display_text, 'format_code': format_code})

                subs = info.get('subtitles')
                if isinstance(subs, dict):
                    for lang in subs.keys():
                        subtitles_dict[lang] = {'type': 'Manual', 'code': lang}
                auto_subs = info.get('automatic_captions')
                if isinstance(auto_subs, dict):
                    for lang in auto_subs.keys():
                        if lang not in subtitles_dict:
                            subtitles_dict[lang] = {'type': 'Auto', 'code': lang}

                thumbnail_url = info.get('thumbnail')
                extra_info = {
                    'uploader': info.get('uploader') or info.get('channel') or '',
                    'view_count': info.get('view_count'),
                    'upload_date': info.get('upload_date') or info.get('release_date') or ''
                }
                self.result_signal.emit(title, duration, b'', format_list, subtitles_dict, extra_info)
                if thumbnail_url and show_thumbnails:
                    try:
                        req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        image_data = urllib.request.urlopen(req, timeout=5).read()
                        if image_data:
                            self.thumbnail_signal.emit(image_data)
                    except Exception as e:
                        logger.error(f"Failed to download video thumbnail: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(f"❌ Error: {str(e)}")