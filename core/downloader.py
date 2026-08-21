from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import re
from utils.settings import app_config, DEFAULT_DOWNLOAD_PATH
from utils import strings

class UserCancelledError(BaseException):
    pass

class DownloadThread(QThread):

    progress_update = pyqtSignal(int, str, str, str)
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, format_id, title, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None, thumb_data=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.title = title
        self.sub_langs = sub_langs or []
        self.subs_only = subs_only 
        self.embed_subs = embed_subs
        self.save_dir = save_dir 
        self.thumb_data = thumb_data
        self.is_cancelled = False
        self.current_speed_bytes = 0

    def progress_hook(self, d):
        if self.is_cancelled:
            raise UserCancelledError("Download Cancelled by User")

        if d['status'] == 'downloading':
            self.current_speed_bytes = d.get('speed', 0) or 0
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0) or 0
            if total > 0:
                percent = int(downloaded / total * 100)
                speed = d.get('_speed_str', '0 KB/s') or '0 KB/s'
                speed = re.sub(r'\x1b\[[0-9;]*[mK]', '', str(speed)).strip()
                eta = d.get('_eta_str', '--:--') or '--:--'
                eta = re.sub(r'\x1b\[[0-9;]*[mK]', '', str(eta)).strip()

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
                
            os.makedirs(save_dir, exist_ok=True)
            out_tmpl = os.path.join(save_dir, '%(title)s.%(ext)s')
            
            speed_limit_str = app_config.get("speed_limit", "0")
            limit_bytes = None
            if speed_limit_str and str(speed_limit_str).strip() != "0":
                try:
                    s_str = str(speed_limit_str).strip()
                    if "M" in s_str:
                        limit_bytes = int(float(s_str.replace("M", "").strip()) * 1024 * 1024)
                    elif "K" in s_str:
                        limit_bytes = int(float(s_str.replace("K", "").strip()) * 1024)
                    else:
                        limit_bytes = int(float(s_str))
                except Exception:
                    limit_bytes = None

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
            elif self.format_id.startswith("audio-direct:"):
                raw_fid = self.format_id.replace("audio-direct:", "")
                ydl_opts['format'] = raw_fid
            else:
                ydl_opts['format'] = self.format_id

            if self.subs_only:
                ydl_opts['writethumbnail'] = False
            else:
                ydl_opts['writethumbnail'] = True 
                if 'postprocessors' not in ydl_opts: ydl_opts['postprocessors'] = []
                ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
                ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            if self.sub_langs:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True 
                ydl_opts['subtitleslangs'] = self.sub_langs
                
                is_audio = (
                    self.format_id.startswith("mp3-") or 
                    self.format_id.startswith("m4a-") or 
                    self.format_id.startswith("audio-direct:") or
                    self.format_id.startswith("audio:")
                )
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

            if not self.is_cancelled:
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
            if getattr(self, 'save_dir', None):
                save_dir = self.save_dir
            elif app_config.get("save_mode") == "custom" and app_config.get("custom_path"):
                save_dir = app_config["custom_path"]
            else:
                save_dir = DEFAULT_DOWNLOAD_PATH

            try:
                from yt_dlp.utils import sanitize_filename
                safe_title = sanitize_filename(getattr(self, 'title', ''), restricted=False)
            except Exception:
                safe_title = re.sub(r'[\\/*?:"<>|]', "", getattr(self, 'title', ''))
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