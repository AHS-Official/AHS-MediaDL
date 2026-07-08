from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import re
from utils.settings import app_config, DEFAULT_DOWNLOAD_PATH
from utils import strings
import json
from datetime import datetime

class UserCancelledError(BaseException):
    pass

class DownloadThread(QThread):

    progress_update = pyqtSignal(int, str, str, str)
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    history_ready = pyqtSignal(dict)

    def __init__(self, url, format_id, title, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None, thumb_data=None, custom_metadata=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.title = title
        self.sub_langs = sub_langs or []
        self.subs_only = subs_only 
        self.embed_subs = embed_subs
        self.save_dir = save_dir 
        self.thumb_data = thumb_data
        self.custom_metadata = custom_metadata
        self.is_cancelled = False
        self.current_speed_bytes = 0

    def progress_hook(self, d):
        if self.is_cancelled:
            raise UserCancelledError("Download Cancelled by User")

        if d['status'] == 'downloading':
            self.current_speed_bytes = d.get('speed', 0) or 0
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0:
                percent = int(downloaded / total * 100)
                speed = d.get('_speed_str', '0 KB/s')
                speed = re.sub(r'\x1b\[[0-9;]*[mK]', '', speed).strip()
                eta = d.get('_eta_str', '--:--')
                eta = re.sub(r'\x1b\[[0-9;]*[mK]', '', eta).strip()

                def format_size(bytes_num):
                    if not bytes_num: return "0 KB"
                    units = ["B", "KB", "MB", "GB", "TB"]
                    i = 0
                    while bytes_num >= 1024 and i < len(units) - 1:
                        bytes_num /= 1024.0
                        i += 1
                    return f"{bytes_num:.1f} {units[i]}"

                dl_str = format_size(downloaded)
                tot_str = format_size(total)
                size_str = f"{dl_str} / {tot_str}"

                self.progress_update.emit(percent, speed, eta, size_str)
                self.status_update.emit(f"Downloading... {percent}%" if not strings.is_ar else f"جاري التحميل... {percent}%")
                
        elif d['status'] == 'finished':
            self.current_speed_bytes = 0
            self.progress_update.emit(100, "", "", "") 
            self.status_update.emit("Processing... Please wait." if not strings.is_ar else "جاري المعالجة... يرجى الانتظار")

    def run(self):
        try:
            if getattr(self, 'save_dir', None):
                save_dir = self.save_dir
            elif app_config.get("save_mode") == "custom" and app_config.get("custom_path"):
                save_dir = app_config["custom_path"]
            else:
                save_dir = DEFAULT_DOWNLOAD_PATH
                
            out_tmpl = os.path.join(save_dir, '%(title)s.%(ext)s')
            
            speed_limit_str = app_config.get("speed_limit", "0")
            limit_bytes = None
            if speed_limit_str != "0":
                try:
                    if "M" in speed_limit_str:
                        limit_bytes = int(speed_limit_str.replace("M", "")) * 1024 * 1024
                    elif "K" in speed_limit_str:
                        limit_bytes = int(speed_limit_str.replace("K", "")) * 1024
            
                except: pass

            ydl_opts = {
                'outtmpl': out_tmpl,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'nocolor': True,
                'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
                'socket_timeout': 30,
                'retries': 5,
            }
            
            if limit_bytes:
                ydl_opts['ratelimit'] = limit_bytes
                ydl_opts['concurrent_fragment_downloads'] = 1
            
            browser = app_config.get("browser_cookies", "none")
            if browser == "custom":
                cookie_path = app_config.get("cookie_file", "")
                if cookie_path and os.path.exists(cookie_path):
                    ydl_opts['cookiefile'] = cookie_path
            elif browser != "none": 
                ydl_opts['cookiesfrombrowser'] = (browser,)

            if self.subs_only: ydl_opts['skip_download'] = True

            if self.format_id.startswith("mp3-"):
                bitrate = self.format_id.split("-")[1]
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}],
                })
            elif self.format_id == "m4a-128":
                ydl_opts.update({
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}],
                })
            else:
                ydl_opts['format'] = self.format_id

            if self.subs_only:
                ydl_opts['writethumbnail'] = False
            else:
                ydl_opts['writethumbnail'] = True 
                if 'postprocessors' not in ydl_opts: ydl_opts['postprocessors'] = []
                ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            if self.sub_langs:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True 
                ydl_opts['subtitleslangs'] = self.sub_langs
                
                is_audio = self.format_id.startswith("mp3-") or self.format_id.startswith("m4a-")
                embed_enabled = getattr(self, 'embed_subs', False)
                
                if not self.subs_only:
                    if is_audio:
                        ydl_opts['subtitlesformat'] = 'srt/best'
                        ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'})
                    else:
                        ydl_opts['subtitlesformat'] = 'srt/best'
                        if embed_enabled:
                            ydl_opts['embedsubtitles'] = True
                            ydl_opts['merge_output_format'] = 'mkv'
                            ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': False})

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if not self.is_cancelled and getattr(self, 'custom_metadata', None):
                try:
                    from core.workers import apply_metadata
                    import glob
                    from yt_dlp.utils import sanitize_filename
                    
                    safe_title = sanitize_filename(getattr(self, 'title', ''), restricted=False)
                    escaped_title = glob.escape(safe_title)
                    search_pattern = os.path.join(save_dir, f"{escaped_title}.*")
                    downloaded_files = glob.glob(search_pattern)
                    
                    if downloaded_files:
                        target_file = None
                        for f in downloaded_files:
                            if f.endswith(('.mp3', '.m4a')):
                                target_file = f
                                break
                        
                        if target_file:
                            apply_metadata(target_file, self.custom_metadata)
                            print(f"✅ Metadata applied successfully to: {target_file}")
                except Exception as e:
                    print(f"❌ Failed to apply metadata: {e}")

            # تم تنظيم هذا الجزء لمنع تكرار الكود والإشارات
            if not self.is_cancelled:
                from utils.helpers import get_app_dir
                thumb_path = ""
                if getattr(self, 'thumb_data', None):
                    try:
                        from yt_dlp.utils import sanitize_filename
                        safe_title = sanitize_filename(getattr(self, 'title', ''), restricted=False)
                        cache_dir = os.path.join(get_app_dir(), "cache", "thumbnails")
                        os.makedirs(cache_dir, exist_ok=True)
                        thumb_path = os.path.join(cache_dir, f"{safe_title}.jpg")
                        with open(thumb_path, "wb") as f:
                            f.write(self.thumb_data)
                    except Exception as ex:
                        print(f"Error caching thumbnail: {ex}")
                        thumb_path = ""

                history_entry = {
                    "title": getattr(self, 'title', "Unknown"),
                    "url": self.url,
                    "path": save_dir,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "format": self.format_id,
                    "thumb_path": thumb_path
                }
                
                # 1. إطلاق إشارة الواجهة أولاً لتبلغها بالبيانات
                self.history_ready.emit(history_entry)
                
                # 2. حفظ السجل في ملف JSON
                history_file = os.path.join(get_app_dir(), "history.json")
                history_data = []
                if os.path.exists(history_file):
                    try:
                        with open(history_file, "r", encoding="utf-8") as f:
                            history_data = json.load(f)
                    except: 
                        history_data = []
                
                history_data.insert(0, history_entry)
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, indent=4, ensure_ascii=False)
                
                # 3. إطلاق إشارة الانتهاء النهائية (مرة واحدة فقط)
                self.finished.emit()
                
        except UserCancelledError:
            self.error.emit("Cancelled")
            self.cleanup_temp_files()
        except Exception as e:
            error_msg = str(e)
            error_msg = re.sub(r'\x1b\[[0-9;]*[mK]', '', error_msg).strip()
            if "Download Cancelled" in error_msg or "DOWNLOAD_CANCELLED" in error_msg: 
                self.error.emit("Cancelled")
                self.cleanup_temp_files()
            else: 
                self.error.emit(error_msg)

    def cancel_download(self):
        self.is_cancelled = True

    def cleanup_temp_files(self):
        try:
            import glob
            from yt_dlp.utils import sanitize_filename
            if getattr(self, 'save_dir', None):
                save_dir = self.save_dir
            elif app_config.get("save_mode") == "custom" and app_config.get("custom_path"):
                save_dir = app_config["custom_path"]
            else:
                save_dir = DEFAULT_DOWNLOAD_PATH
                
            safe_title = sanitize_filename(getattr(self, 'title', ''), restricted=False)
            escaped_title = glob.escape(safe_title)
            search_pattern = os.path.join(save_dir, f"{escaped_title}*")
            possible_files = glob.glob(search_pattern)
            for f in possible_files:
                if f.endswith(('.part', '.ytdl')) or f == os.path.join(save_dir, f"{safe_title}.{self.format_id}"):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")