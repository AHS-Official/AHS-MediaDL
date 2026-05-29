import os
import re
import time
import urllib.request
import yt_dlp
import glob
import json
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QObject
from core.ffmpeg_handler import get_ffmpeg_path, process_download_post_processing
from utils.locales import tr

class InspectWorker(QThread):
    result_signal = pyqtSignal(str, int, bytes, list, dict)
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
        if isinstance(self.url, list):
            title = tr("packages_title", "Collected Links Box")
            entries = []
            for i, item_url in enumerate(self.url):
                clean_url = item_url.strip()
                if clean_url.lower().startswith("dl:"):
                    clean_url = clean_url[3:].strip()
                try:
                    with yt_dlp.YoutubeDL({'quiet': True, 'nocolor': True, 'extract_flat': True}) as ydl:
                        info = ydl.extract_info(clean_url, download=False)
                        video_title = info.get('title', clean_url)
                        video_id = info.get('id')
                        entries.append({
                            'id': video_id,
                            'title': video_title,
                            'url': clean_url
                        })
                except Exception as e:
                    print(f"Error inspecting url {clean_url}: {e}")
                    entries.append({
                        'id': None,
                        'title': clean_url,
                        'url': clean_url
                    })
            self.playlist_signal.emit(title, b'', entries)
            return
        ydl_opts = {'quiet': True, 'nocolor': True, 'extract_flat': 'in_playlist'}
        subtitles_dict = {}
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
                    image_data = b''
                    if thumbnail_url:
                        try:
                            req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                            image_data = urllib.request.urlopen(req, timeout=5).read()
                        except Exception:
                            pass
                    self.result_signal.emit(title, duration, image_data, format_list, subtitles_dict)
        except Exception as e:
            import traceback
            traceback.print_exc()                                                   
            self.error_signal.emit(f"❌ Error: {str(e)}")                                            

class DownloadWorker(QThread):
    status_signal = pyqtSignal(str) 
    progress_signal = pyqtSignal(int)
    sub_notification_signal = pyqtSignal(str, str, str)                           
    finished_signal = pyqtSignal(str)

    def __init__(self, url, format_code, save_path, sub_lang=None, is_playlist_sub=False):                     
        super().__init__()
        self.url = url
        self.format_code = format_code 
        self.save_path = save_path
        self.sub_lang = sub_lang                   
        self.is_playlist_sub = is_playlist_sub                   
        self.is_paused = False
        self.is_cancelled = False
        self.is_connection_error = False
        self.last_update_time = 0
        self.last_percent = -1

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True
        self.is_paused = False

    def update_rate_limit(self, new_limit):
        self.current_limit = new_limit
        if hasattr(self, 'ydl') and self.ydl:
            self.ydl.params['ratelimit'] = new_limit

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
            info_dict = d.get('info_dict')
            if info_dict and not hasattr(self, 'fallback_detected'):
                self.fallback_detected = False
                downloaded_height = info_dict.get('height')
                if downloaded_height:
                    match = re.search(r'height<=(144|240|360|480|720|1080|1440|2160)', self.format_code)
                    if match:
                        req_height = int(match.group(1))
                        if downloaded_height < req_height:
                            self.fallback_detected = True
                            self.fallback_info = (info_dict.get('title', 'Video'), req_height, downloaded_height)
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
            self.status_signal.emit(tr("status_processing", "⚙️ Processing... please wait."))

    def run(self):
        if getattr(self, 'is_playlist_sub', False):
            self.status_signal.emit(tr("status_inspecting_subs", "🔍 Inspecting subtitles..."))
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
            primary_sub_lang = "ar"
            secondary_sub_lang = "en"
            fallback_enabled = False
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        primary_sub_lang = data.get("primary_sub_lang", "ar")
                        secondary_sub_lang = data.get("secondary_sub_lang", "en")
                        fallback_enabled = data.get("download_any_sub_fallback", False)
                except Exception:
                    pass
            subtitles_dict = {}
            video_title = "video"
            try:
                inspect_opts = {'quiet': True, 'nocolor': True}
                with yt_dlp.YoutubeDL(inspect_opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                    video_title = info.get('title', 'video')
                    subs = info.get('subtitles')
                    if isinstance(subs, dict):
                        for lang in subs.keys():
                            if "live_chat" not in lang.lower() and "chat" not in lang.lower():
                                subtitles_dict[lang] = {'type': 'Manual', 'code': lang}
                    auto_subs = info.get('automatic_captions')
                    if isinstance(auto_subs, dict):
                        for lang in auto_subs.keys():
                            if "live_chat" not in lang.lower() and "chat" not in lang.lower():
                                if lang not in subtitles_dict:
                                    subtitles_dict[lang] = {'type': 'Auto', 'code': lang}
            except Exception:
                pass
            chosen_sub_lang = None
            chosen_sub_type = None

            def match_lang_code(target_lang, dict_lang_code):
                return dict_lang_code.split('-')[0].lower() == target_lang.lower()
            for lang, s_info in subtitles_dict.items():
                if s_info['type'] == 'Manual' and match_lang_code(primary_sub_lang, lang):
                    chosen_sub_lang = lang
                    chosen_sub_type = "primary_manual"
                    break
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    if s_info['type'] == 'Manual' and match_lang_code(secondary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "secondary_manual"
                        break
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    is_original = "-orig" in lang.lower() or "-original" in lang.lower()
                    if s_info['type'] == 'Auto' and is_original and match_lang_code(primary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "primary_auto_orig"
                        break
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    is_original = "-orig" in lang.lower() or "-original" in lang.lower()
                    if s_info['type'] == 'Auto' and is_original and match_lang_code(secondary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "secondary_auto_orig"
                        break
            if not chosen_sub_lang and fallback_enabled:
                for lang, s_info in subtitles_dict.items():
                    if s_info['type'] == 'Manual':
                        chosen_sub_lang = lang
                        chosen_sub_type = "fallback_manual"
                        break
                if not chosen_sub_lang:
                    for lang, s_info in subtitles_dict.items():
                        is_original = "-orig" in lang.lower() or "-original" in lang.lower()
                        if s_info['type'] == 'Auto' and is_original:
                            chosen_sub_lang = lang
                            chosen_sub_type = "fallback_auto_orig"
                            break
            if chosen_sub_lang:
                self.sub_lang = chosen_sub_lang
                from utils.helpers import get_full_language_name
                lang_name = get_full_language_name(chosen_sub_lang)
                if chosen_sub_type in ["secondary_manual", "secondary_auto_orig"]:
                    self.sub_notification_signal.emit("secondary", video_title, lang_name)
                elif chosen_sub_type in ["fallback_manual", "fallback_auto_orig"]:
                    self.sub_notification_signal.emit("fallback", video_title, lang_name)
            else:
                self.sub_lang = None
                if subtitles_dict:
                    self.sub_notification_signal.emit("none", video_title, "")
        base_path, _ = os.path.splitext(self.save_path)
        ydl_opts = {
            'outtmpl': f"{base_path}.%(ext)s",
            'quiet': True,
            'nocolor': True,
            'writethumbnail': True,
            'progress_hooks': [self.my_hook],
            'postprocessors': [],
            'overwrites': True,
            'socket_timeout': 20,                                       
            'ratelimit': getattr(self, 'current_limit', None)
        }
        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        if self.sub_lang:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True                             
            ydl_opts['subtitleslangs'] = [self.sub_lang]
            ydl_opts['subtitlesformat'] = 'srt'
        if self.format_code.startswith("audio:"):
            parts = self.format_code.split(":")
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
            audio_container = "m4a"
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        audio_container = data.get("audio_container", "m4a")
                except Exception:
                    pass
            if len(parts) == 4:
                _, format_id, orig_ext, bitrate = parts
                ydl_opts['format'] = format_id
            elif len(parts) == 3:
                _, codec, bitrate = parts
                ydl_opts['format'] = 'bestaudio/best'
            else:
                bitrate = "128"
                ydl_opts['format'] = 'bestaudio/best'
            extract_codec = audio_container
            if audio_container == "mp4":
                extract_codec = "m4a"
            elif audio_container == "mkv":
                extract_codec = "mka"
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': extract_codec,     
                'preferredquality': bitrate, 
            })
        else:
            quality_fallback = True
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        quality_fallback = data.get("quality_fallback", True)
                except Exception:
                    pass
            if not quality_fallback and "<=" in self.format_code:
                strict_format = self.format_code.replace('<=', '=')
                if strict_format.endswith('/best'):
                    strict_format = strict_format[:-5]
                ydl_opts['format'] = strict_format
            else:
                ydl_opts['format'] = self.format_code
            chosen_ext = os.path.splitext(self.save_path)[1].lower().replace('.', '')
            if chosen_ext in ['mp4', 'mkv', 'mov', 'webm']:
                ydl_opts['merge_output_format'] = chosen_ext
                if chosen_ext == 'mp4':
                    ydl_opts['postprocessor_args'] = {
                        'merger': ['-c:a', 'aac']
                    }
        ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
        ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
        ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})
        try:
            self.status_signal.emit(tr("status_starting", "⏳ Starting download..."))
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.ydl = ydl
                if hasattr(self, 'current_limit') and self.current_limit is not None:
                    ydl.params['ratelimit'] = self.current_limit
                ydl.download([self.url])
            if not self.is_cancelled:
                self.save_path = process_download_post_processing(self, self.save_path, self.sub_lang, self.format_code)
            if not self.is_cancelled:
                self.finished_signal.emit(self.save_path)
                self.status_signal.emit(tr("status_done", "✅ Done!"))
        except Exception as e:
            raw_err = str(e)
            err_msg = self.clean_ansi(raw_err)
            if raw_err == "DOWNLOAD_CANCELLED" or err_msg == "DOWNLOAD_CANCELLED":
                self.status_signal.emit(tr("status_cancelled", "❌ Canceled"))
                self.cleanup_files()
            else:
                err_lower = err_msg.lower()
                network_keywords = ["connection broken", "connection aborted", "connection reset", "connreset", "timeout", 
                                    "getaddrinfo", "unreachable", "temporary failure", "http error 50", "handshake", "remote end closed",
                                    "connectionpool", "connection pool", "max retries", "failed to establish", "urllib", "socket", "dns",
                                    "httpconnection", "httpsconnection", "ssl"]
                if os.path.exists(self.save_path):
                    self.status_signal.emit(tr("status_cover_failed", "✅ Downloaded (Warning: Cover failed)"))
                elif any(k in err_lower for k in network_keywords):
                    self.is_connection_error = True
                    self.status_signal.emit(tr("status_error_conn"))
                else:
                    if "ffmpeg" in err_lower or "ffprobe" in err_lower:
                        self.status_signal.emit(tr("status_ffmpeg_missing", "❌ Error: FFmpeg is missing! Please install FFmpeg to support this format."))
                    else:
                        clean_err = err_msg.replace("ERROR:", "").replace("Error:", "").strip()
                        if "\n" in clean_err:
                            clean_err = clean_err.split("\n")[0]
                        if len(clean_err) > 80:
                            clean_err = clean_err[:77] + "..."
                        self.status_signal.emit(tr("status_error_prefix", "❌ Error: ") + clean_err)

class ThumbnailRunnableSignals(QObject):
    thumb_loaded = pyqtSignal(int, bytes)

class ThumbnailRunnable(QRunnable):

    def __init__(self, index, video_id):
        super().__init__()
        self.index = index
        self.video_id = video_id
        self.signals = ThumbnailRunnableSignals()

    def run(self):
        url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.signals.thumb_loaded.emit(self.index, data)
        except Exception as e:
            print(f"Thumbnail error for {self.video_id}: {e}")
