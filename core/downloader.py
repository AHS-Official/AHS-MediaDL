from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import re
from data.settings import app_config, DEFAULT_DOWNLOAD_PATH

class UserCancelledError(BaseException):
    pass

class DownloadThread(QThread):
    progress_update = pyqtSignal(int, int, int, str, str) # percent, downloaded, total, speed, eta
    status_update = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, format_id, sub_langs=None, subs_only=False, embed_subs=False, save_dir=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.sub_langs = sub_langs or []
        self.subs_only = subs_only 
        self.embed_subs = embed_subs
        self.save_dir = save_dir 
        self.is_cancelled = False
        self.current_speed_bytes = 0

    def progress_hook(self, d):
        if self.is_cancelled:
            raise UserCancelledError("Download Cancelled by User")

        if d['status'] == 'downloading':
            self.current_speed_bytes = d.get('speed', 0) or 0
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0) or 0
            
            percent = 0
            if total > 0:
                percent = int(downloaded / total * 100)
                
            speed = d.get('_speed_str', '0 KB/s')
            speed = re.sub(r'\x1b\[[0-9;]*[mK]', '', speed).strip()
            eta = d.get('_eta_str', '--:--')
            eta = re.sub(r'\x1b\[[0-9;]*[mK]', '', eta).strip()

            self.progress_update.emit(percent, downloaded, total, speed, eta)
            
        elif d['status'] == 'finished':
            self.current_speed_bytes = 0
            self.progress_update.emit(100, 0, 0, "Done", "--:--")
            self.status_update.emit("Processing... Please wait.")

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
                'socket_timeout': 30,
                'retries': 10,
                'postprocessors': [],
                'prefer_ffmpeg': True,
            }
            
            if not self.embed_subs:
                ydl_opts['merge_output_format'] = app_config.get("output_format", "mp4")
            
            if limit_bytes:
                ydl_opts['ratelimit'] = limit_bytes
                ydl_opts['concurrent_fragment_downloads'] = 1 
            
            browser = app_config.get("browser_cookies", "none")
            if browser != "none": ydl_opts['cookiesfrombrowser'] = (browser,)

            if self.subs_only: 
                ydl_opts['skip_download'] = True
            else:
                if self.format_id.startswith("mp3-"):
                    bitrate = self.format_id.split("-")[1]
                    ydl_opts.update({'format': 'bestaudio/best'})
                    ydl_opts['postprocessors'].append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate})
                elif self.format_id == "m4a-128":
                    ydl_opts.update({'format': 'bestaudio[ext=m4a]/bestaudio/best'})
                    ydl_opts['postprocessors'].append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'})
                else:
                    ydl_opts['format'] = f"{self.format_id}+bestaudio[ext=m4a]/best"

                ydl_opts['writethumbnail'] = True 
                ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            if self.sub_langs:
                lang = self.sub_langs[0]
                ydl_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': [lang],
                })
                
                ydl_opts['subtitlesformat'] = 'vtt'
                
                is_audio = self.format_id.startswith("mp3-") or self.format_id.startswith("m4a-")
                
                if is_audio and not self.subs_only:
                    if app_config.get("embed_lyrics", False):
                        ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': 'lrc'})
                        ydl_opts['embedmetadata'] = True
                    else:
                        sub_format = app_config.get("subtitle_output_format", "srt")
                        ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': sub_format})
                else:
                    sub_format = app_config.get("subtitle_output_format", "srt")
                    ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': sub_format})
                    
                    if not self.subs_only and self.embed_subs:
                        ydl_opts['embedsubtitles'] = True
                        ydl_opts['merge_output_format'] = app_config.get("video_container", "mkv")
                        ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle', 'already_have_subtitle': False})

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            if not self.is_cancelled:
                self.finished.emit()
                
        except UserCancelledError:
            self.error.emit("Cancelled")
        except Exception as e:
            error_msg = str(e)
            error_msg = re.sub(r'\x1b\[[0-9;]*[mK]', '', error_msg).strip()
            if "Download Cancelled" in error_msg: self.error.emit("Cancelled")
            else: self.error.emit(error_msg)

    def cancel_download(self):
        self.is_cancelled = True
