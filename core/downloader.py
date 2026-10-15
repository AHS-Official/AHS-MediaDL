import os
import re
import time
import subprocess
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal
from core.ffmpeg_handler import get_ffmpeg_path, process_download_post_processing
from utils.locales import tr
from utils.helpers import get_data_path
from utils.logger import logger
from managers.binary_manager import BinaryManager
from services.yt_dlp_service import run_ytdlp_json, get_ytdlp_cli_args, load_cookies_opts


class DownloadWorker(QThread):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    sub_notification_signal = pyqtSignal(str, str, str)
    finished_signal = pyqtSignal(str)
    thumb_loaded_signal = pyqtSignal(bytes)

    NETWORK_ERRORS = [
        "connection broken", "connection aborted", "connection reset", "connreset", "timeout",
        "getaddrinfo", "unreachable", "temporary failure", "http error 50", "http error 403", "403: forbidden",
        "handshake", "remote end closed", "connectionpool", "connection pool", "max retries",
        "failed to establish", "urllib", "socket", "dns", "httpconnection", "httpsconnection", "ssl"
    ]

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
        self.download_phase = 1
        self.last_raw_percent = -1
        self.video_size = 0
        self.audio_size = 0
        self.total_combined_size = 0
        self.finished_files_count = 0
        is_two_parts_init = (
            not str(format_code).startswith("audio:") and
            ("+" in str(format_code) or "bestvideo" in str(format_code))
        )
        self.expected_files_count = 2 if is_two_parts_init else 1
        self.needs_thumbnail = False
        self.subtitle_status = None
        self.downloaded_sub_lang = ""
        self.proc = None

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True
        self.is_paused = False
        self._kill_proc()

    def update_rate_limit(self, new_limit):
        self.current_limit = new_limit

    def clean_ansi(self, text):
        return re.sub(r'\x1b\[[0-9;]*m', '', str(text)).strip()

    def cleanup_files(self):
        time.sleep(0.5)
        base_path = os.path.splitext(self.save_path)[0]
        folder, base_name = os.path.split(base_path)
        target_prefix = base_name + "."
        if os.path.exists(folder):
            try:
                for entry in os.listdir(folder):
                    if entry == os.path.basename(self.save_path) or entry.startswith(target_prefix):
                        f = os.path.join(folder, entry)
                        if f.endswith('.part') or f.endswith('.ytdl') or f == self.save_path:
                            try:
                                os.remove(f)
                            except OSError:
                                pass
            except Exception:
                pass

    def _suspend_proc(self):
        if self.proc and self.proc.poll() is None and os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                ntdll = ctypes.windll.ntdll
                h = kernel32.OpenProcess(0x1F0FFF, False, self.proc.pid)
                ntdll.NtSuspendProcess(h)
                kernel32.CloseHandle(h)
            except Exception as e:
                logger.warning(f"Failed to suspend process: {e}")

    def _resume_proc(self):
        if self.proc and self.proc.poll() is None and os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                ntdll = ctypes.windll.ntdll
                h = kernel32.OpenProcess(0x1F0FFF, False, self.proc.pid)
                ntdll.NtResumeProcess(h)
                kernel32.CloseHandle(h)
            except Exception as e:
                logger.warning(f"Failed to resume process: {e}")

    def _kill_proc(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

    def _resolve_subtitles(self, video_title):
        if not getattr(self, 'is_playlist_sub', False):
            return

        self.subtitle_status = "unavailable"
        self.status_signal.emit(tr("status_inspecting_subs", "🔍 Inspecting subtitles..."))
        from managers.settings_manager import SettingsManager
        mgr = SettingsManager()
        primary_sub_lang = mgr.get("primary_sub_lang", "ar")
        secondary_sub_lang = mgr.get("secondary_sub_lang", "en")
        fallback_enabled = mgr.get("download_any_sub_fallback", False)
        subtitles_dict = {}

        try:
            info = run_ytdlp_json(["--flat-playlist", self.url])
            if info.get('_type') == 'playlist':
                entries = info.get('entries')
                if entries and len(entries) > 0:
                    info = entries[0]
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
            self.subtitle_status = "downloaded"
            self.downloaded_sub_lang = lang_name
            if chosen_sub_type in ["secondary_manual", "secondary_auto_orig"]:
                self.sub_notification_signal.emit("secondary", video_title, lang_name)
            elif chosen_sub_type in ["fallback_manual", "fallback_auto_orig"]:
                self.sub_notification_signal.emit("fallback", video_title, lang_name)
        else:
            self.sub_lang = None
            if subtitles_dict:
                self.sub_notification_signal.emit("none", video_title, "")

    def _build_cli_args(self, base_path, format_override=None, skip_subs=False):
        args = get_ytdlp_cli_args()
        args += [
            "-o", f"{base_path}.%(ext)s",
            "--no-colors",
            "--no-warnings",
            "--newline",
            "-c",
            "-R", "5",
            "--fragment-retries", "5",
            "--retry-sleep", "http:1",
            "--socket-timeout", "20",
        ]

        if hasattr(self, 'current_limit') and self.current_limit:
            args += ["-r", str(self.current_limit)]

        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise Exception(tr("error_ffmpeg_missing", "FFmpeg is missing. Please ensure ffmpeg.exe and ffprobe.exe are in the 'bin' folder next to the application."))
        args += ["--ffmpeg-location", os.path.dirname(ffmpeg_path)]

        if self.sub_lang and not skip_subs:
            args += [
                "--write-sub",
                "--write-auto-sub",
                "--sub-langs", self.sub_lang,
                "--sub-format", "srt",
            ]

        fmt = format_override or self.format_code
        if fmt.startswith("audio:"):
            parts = fmt.split(":")
            from managers.settings_manager import SettingsManager
            mgr = SettingsManager()
            audio_container = mgr.get("audio_container", "mp3")
            if len(parts) == 4:
                _, format_id, orig_ext, bitrate = parts
            elif len(parts) == 3:
                _, codec, bitrate = parts
                format_id = "bestaudio/best"
            else:
                bitrate = "128"
                format_id = "bestaudio/best"
            extract_codec = audio_container
            if audio_container == "mp4":
                extract_codec = "m4a"
            elif audio_container == "mkv":
                extract_codec = "mka"
            args += [
                "-f", format_id,
                "-x",
                "--audio-format", extract_codec,
                "--audio-quality", str(bitrate),
            ]
        else:
            from managers.settings_manager import SettingsManager
            mgr = SettingsManager()
            quality_fallback = mgr.get("quality_fallback", True)
            if not quality_fallback and "<=" in fmt:
                strict_format = fmt.replace('<=', '=')
                if strict_format.endswith('/best'):
                    strict_format = strict_format[:-5]
                args += ["-f", strict_format]
            else:
                args += ["-f", fmt]

            chosen_ext = os.path.splitext(self.save_path)[1].lower().replace('.', '')
            if chosen_ext in ['mp4', 'mkv', 'mov', 'webm']:
                merge_ext = 'mp4' if chosen_ext == 'mov' else chosen_ext
                args += ["--merge-output-format", merge_ext]
                if chosen_ext in ['mp4', 'mov']:
                    args += ["--postprocessor-args", "Merger:-c:a aac"]

        args += [
            "--add-metadata",
            "--convert-thumbnails", "jpg",
            "--embed-thumbnail",
            "--parse-metadata", "%(upload_date>%Y)s:%(meta_date)s",
            "--progress-template",
            "download-progress:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|%(progress.status)s|%(progress.filename)s"
        ]

        args.append(self.url)
        return args

    def _parse_progress_line(self, line_str):
        raw = line_str[len("download-progress:"):].strip()
        parts = raw.split("|")
        if len(parts) < 6:
            return

        percent_str = parts[0]
        speed_clean = self.clean_ansi(parts[1]) if parts[1] != "NA" else "N/A"
        eta_clean = self.clean_ansi(parts[2]) if parts[2] != "NA" else "N/A"
        downloaded_clean = self.clean_ansi(parts[3]) if parts[3] != "NA" else "0B"
        total_clean = self.clean_ansi(parts[4]) if parts[4] != "NA" else "Unknown"
        status_clean = parts[5]

        p_clean = self.clean_ansi(percent_str).replace('%', '')
        try:
            percent_raw = float(p_clean)
        except ValueError:
            percent_raw = 0.0
        percent_raw = max(0.0, min(100.0, percent_raw))

        filename_clean = parts[6] if len(parts) > 6 else ""
        fn_lower = filename_clean.lower()
        is_sub = any(ext in fn_lower for ext in ['.srt', '.vtt', '.ass', '.lrc'])

        if is_sub:
            sub_percent = min(1, max(0, int(percent_raw * 0.01)))
            if sub_percent > self.last_percent:
                self.last_percent = sub_percent
                self.progress_signal.emit(sub_percent)
            self.status_signal.emit(tr("status_downloading_subs", "⏳ Downloading subtitles..."))
            return

        if status_clean == "finished":
            expected_files = getattr(self, 'expected_files_count', 1)
            if expected_files >= 2:
                self.finished_files_count += 1
                if self.finished_files_count < expected_files:
                    self.download_phase = 2
                    self.last_percent = max(self.last_percent, 85)
                    return
            self.last_percent = 99
            self.progress_signal.emit(99)
            self.status_signal.emit(tr("status_processing", "⚙️ Processing... please wait."))
            return

        format_code_str = str(getattr(self, 'format_code', ''))
        is_audio = format_code_str.startswith("audio:")
        is_two_parts = not is_audio and (
            getattr(self, 'expected_files_count', 1) >= 2 or
            ("+" in format_code_str) or
            ("bestvideo" in format_code_str)
        )

        if is_two_parts:
            if getattr(self, 'finished_files_count', 0) >= 1:
                self.download_phase = 2
            elif self.download_phase == 1 and getattr(self, 'last_raw_percent', -1) > 70 and percent_raw < 30:
                self.download_phase = 2

        if is_audio:
            display_percent = 1 + int((percent_raw / 100.0) * 98.0)
            phase_label = tr("status_downloading_audio", "⏳ Downloading audio...")
        elif is_two_parts:
            if self.download_phase == 1:
                display_percent = 1 + int((percent_raw / 100.0) * 84.0)
                phase_label = tr("status_downloading_video", "⏳ Downloading video...")
            else:
                display_percent = 86 + int((percent_raw / 100.0) * 13.0)
                phase_label = tr("status_downloading_audio", "⏳ Downloading audio...")
        else:
            display_percent = 1 + int((percent_raw / 100.0) * 98.0)
            phase_label = tr("status_downloading_video", "⏳ Downloading video...")

        display_percent = max(self.last_percent, display_percent)
        display_percent = min(99, max(1, display_percent))

        current_time = time.time()
        if (current_time - self.last_update_time > 0.5) or (display_percent != self.last_percent):
            self.progress_signal.emit(display_percent)
            speed_lbl = tr("status_speed", "Speed")
            eta_lbl = tr("status_eta", "ETA")
            status_text = f"{phase_label} {downloaded_clean} / {total_clean} | {speed_lbl}: {speed_clean} | {eta_lbl}: {eta_clean}"
            self.status_signal.emit(status_text)
            self.last_update_time = current_time
            self.last_percent = display_percent
            self.last_raw_percent = percent_raw

    def _run_download_process(self, cli_args):
        ytdlp_path = BinaryManager.get_binary_path("yt-dlp")
        if not ytdlp_path:
            raise Exception(tr("error_ytdlp_missing", "yt-dlp executable not found. Please ensure yt-dlp.exe is in PATH or bin/ folder."))

        full_cmd = [ytdlp_path] + cli_args

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        self.proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        error_lines = []

        while True:
            if self.is_cancelled:
                self._kill_proc()
                raise Exception("DOWNLOAD_CANCELLED")

            if self.is_paused:
                self._suspend_proc()
                while self.is_paused:
                    if self.is_cancelled:
                        self._resume_proc()
                        self._kill_proc()
                        raise Exception("DOWNLOAD_CANCELLED")
                    time.sleep(0.2)
                self._resume_proc()

            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    break
                continue

            line_str = line.strip()
            if not line_str:
                continue

            if "ERROR:" in line_str or "Error:" in line_str:
                error_lines.append(line_str)

            if line_str.startswith("download-progress:"):
                self._parse_progress_line(line_str)
            elif any(marker in line_str for marker in ["[Merger]", "[FFmpeg]", "[Metadata]", "[EmbedThumbnail]", "Deleting original file"]):
                if self.last_percent < 99:
                    self.last_percent = 99
                    self.progress_signal.emit(99)
                    self.status_signal.emit(tr("status_processing", "⚙️ Processing... please wait."))

        rc = self.proc.wait()
        if self.is_cancelled:
            raise Exception("DOWNLOAD_CANCELLED")
        if rc != 0:
            err_summary = "\n".join(error_lines) if error_lines else f"Download failed with exit code {rc}"
            raise Exception(err_summary)

    def _execute_download(self, cli_args, video_title):
        try:
            if getattr(self, 'needs_thumbnail', False):
                try:
                    info = run_ytdlp_json(["--flat-playlist", self.url])
                    thumbnail_url = info.get('thumbnail')
                    if thumbnail_url:
                        if thumbnail_url.startswith("//"):
                            thumbnail_url = f"https:{thumbnail_url}"
                        elif not thumbnail_url.startswith("http") and info.get('id'):
                            thumbnail_url = f"https://img.youtube.com/vi/{info.get('id')}/hqdefault.jpg"
                        req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        image_data = urllib.request.urlopen(req, timeout=5).read()
                        self.thumb_loaded_signal.emit(image_data)
                except Exception as e:
                    logger.warning(f"Lazy thumbnail download failed: {e}")

            self.status_signal.emit(tr("status_starting", "⏳ Starting download..."))

            max_retries = 3
            retry_count = 0
            success = False
            last_error = None
            while retry_count < max_retries and not self.is_cancelled and not success:
                try:
                    self._run_download_process(cli_args)
                    success = True
                except Exception as e:
                    last_error = e
                    raw_err = str(e)
                    if self.is_cancelled or "DOWNLOAD_CANCELLED" in raw_err:
                        raise e

                    is_network = any(k in raw_err.lower() for k in self.NETWORK_ERRORS)
                    if is_network:
                        retry_count += 1
                        if retry_count < max_retries:
                            self.status_signal.emit(tr("status_retrying", f"⚠️ Network error. Retrying {retry_count}/{max_retries}..."))
                            for _ in range(30):
                                if self.is_cancelled:
                                    raise Exception("DOWNLOAD_CANCELLED")
                                time.sleep(0.1)
                            continue
                        else:
                            raise e
                    else:
                        raise e

            if not success and last_error:
                raise last_error

            if not self.is_cancelled:
                self.save_path = process_download_post_processing(
                    self, self.save_path, self.sub_lang, self.format_code,
                    cancel_check=lambda: getattr(self, 'is_cancelled', False)
                )

            if not self.is_cancelled:
                self.finished_signal.emit(self.save_path)
                self.emit_done_status()

        except Exception as e:
            raw_err = str(e)
            err_msg = self.clean_ansi(raw_err)
            if raw_err == "DOWNLOAD_CANCELLED" or err_msg == "DOWNLOAD_CANCELLED":
                self.status_signal.emit(tr("status_cancelled", "❌ Canceled"))
                self.cleanup_files()
            elif self.sub_lang and ("subtitle" in err_msg.lower() or "subtitles" in err_msg.lower()):
                logger.warning(f"Subtitle download failed: {err_msg}. Retrying without subtitles...")
                self.subtitle_status = "failed"
                self.sub_lang = None
                self.status_signal.emit(tr("status_sub_failed_retrying", "⚠️ Subtitle failed, downloading video..."))
                self.sub_notification_signal.emit("failed_fallback", video_title, "")

                base_path, _ = os.path.splitext(self.save_path)
                fallback_args = self._build_cli_args(base_path, skip_subs=True)
                try:
                    self._run_download_process(fallback_args)
                    if not self.is_cancelled:
                        self.save_path = process_download_post_processing(
                            self, self.save_path, self.sub_lang, self.format_code,
                            cancel_check=lambda: getattr(self, 'is_cancelled', False)
                        )
                    if not self.is_cancelled:
                        self.finished_signal.emit(self.save_path)
                        self.emit_done_status()
                except Exception as retry_e:
                    retry_raw_err = str(retry_e)
                    retry_err_msg = self.clean_ansi(retry_raw_err)
                    self._handle_download_error(retry_raw_err, retry_err_msg)

            elif not getattr(self, 'already_tried_fallback', False):
                err_lower = err_msg.lower()
                format_keywords = ["unsupported format", "requested format", "format is not available", "format code", "video format", "audio format"]
                is_network = any(k in err_lower for k in self.NETWORK_ERRORS)
                is_format_err = any(k in err_lower for k in format_keywords)
                if is_network or not is_format_err:
                    self._handle_download_error(raw_err, err_msg)
                else:
                    self.already_tried_fallback = True
                    logger.warning(f"Download or postprocessing failed: {err_msg}. Retrying with safe fallback format...")

                    base, _ = os.path.splitext(self.save_path)
                    if self.format_code.startswith("audio:"):
                        new_ext = ".mp3"
                        status_lbl = tr("status_fallback_audio", "⚠️ Failed, retrying with standard MP3...")
                        fallback_fmt = "audio:ba:mp3:192"
                    else:
                        new_ext = ".mp4"
                        status_lbl = tr("status_fallback_video", "⚠️ Failed, retrying with standard MP4...")
                        fallback_fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

                    self.save_path = base + new_ext
                    self.status_signal.emit(status_lbl)

                    try:
                        self.finished_files_count = 0
                        fallback_args = self._build_cli_args(base, format_override=fallback_fmt)
                        self._run_download_process(fallback_args)
                        if not self.is_cancelled:
                            self.save_path = process_download_post_processing(
                                self, self.save_path, self.sub_lang, self.format_code,
                                cancel_check=lambda: getattr(self, 'is_cancelled', False)
                            )
                        if not self.is_cancelled:
                            self.finished_signal.emit(self.save_path)
                            self.emit_done_status()
                    except Exception as retry_e:
                        retry_raw_err = str(retry_e)
                        retry_err_msg = self.clean_ansi(retry_raw_err)
                        self._handle_download_error(retry_raw_err, retry_err_msg)
            else:
                self._handle_download_error(raw_err, err_msg)

    def run(self):
        video_title = os.path.splitext(os.path.basename(self.save_path))[0]
        try:
            self._resolve_subtitles(video_title)
            base_path, _ = os.path.splitext(self.save_path)
            cli_args = self._build_cli_args(base_path)
        except Exception as e:
            raw_err = str(e)
            err_msg = self.clean_ansi(raw_err)
            self._handle_download_error(raw_err, err_msg)
            return
        self._execute_download(cli_args, video_title)

    def emit_done_status(self):
        self.last_percent = 100
        self.progress_signal.emit(100)
        status_str = tr("status_done", "✅ Done!")
        sub_status = getattr(self, 'subtitle_status', None)

        if getattr(self, 'sub_lang', None) and sub_status != "failed":
            sub_status = "downloaded"
            from utils.helpers import get_full_language_name
            self.downloaded_sub_lang = get_full_language_name(self.sub_lang)

        if sub_status == "downloaded":
            lang_lbl = getattr(self, 'downloaded_sub_lang', '')
            status_str += f" | {tr('status_sub_downloaded_prefix', 'Subtitle: ')}{lang_lbl}"
        elif sub_status == "failed":
            status_str += f" | {tr('status_sub_failed_suffix', 'Subtitle failed')}"
        elif sub_status == "unavailable" and getattr(self, 'is_playlist_sub', False):
            status_str += f" | {tr('status_sub_unavailable_suffix', 'Subtitle unavailable')}"
        self.status_signal.emit(status_str)

    def _handle_download_error(self, raw_err, err_msg):
        err_lower = err_msg.lower()
        if os.path.exists(self.save_path):
            self.status_signal.emit(tr("status_cover_failed", "✅ Downloaded (Warning: Cover failed)"))
        elif any(k in err_lower for k in self.NETWORK_ERRORS):
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
