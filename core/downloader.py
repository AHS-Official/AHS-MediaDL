import os
import re
import time
import urllib.request
import yt_dlp
import glob
import concurrent.futures
from PyQt6.QtCore import QThread, pyqtSignal
from core.ffmpeg_handler import get_ffmpeg_path

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

                    # --- استخراج الترجمات المتوفرة للفيديو المفرد فقط ---
                    subs = info.get('subtitles')
                    if isinstance(subs, dict):
                        for lang in subs.keys():
                            subtitles_dict[lang] = {'type': 'Manual', 'code': lang}
                            
                    auto_subs = info.get('automatic_captions')
                    if isinstance(auto_subs, dict):
                        for lang in auto_subs.keys():
                            if lang not in subtitles_dict:  # تفضيل الترجمة اليدوية أولاً
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
            traceback.print_exc()  # سيطبع الخطأ بالتفصيل في الـ Terminal عندك لتراه
            self.error_signal.emit(f"❌ Error: {str(e)}")  # سيعرض سبب الخطأ الفعلي على واجهة التطبيق

class DownloadWorker(QThread):
    status_signal = pyqtSignal(str) 
    progress_signal = pyqtSignal(int)
    sub_notification_signal = pyqtSignal(str, str, str) # (type, title, lang_name)
    finished_signal = pyqtSignal(str)

    def __init__(self, url, format_code, save_path, sub_lang=None, is_playlist_sub=False): # أضفنا sub_lang هنا
        super().__init__()
        self.url = url
        self.format_code = format_code 
        self.save_path = save_path
        self.sub_lang = sub_lang # احفظ المتغير هنا
        self.is_playlist_sub = is_playlist_sub # احفظ المتغير هنا

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
        # 1. إذا كان التنزيل من قائمة تشغيل وتم تفعيل خيار الترجمة، نقوم بجلب اللغات المتاحة وتحديد الأفضل تلقائياً
        if getattr(self, 'is_playlist_sub', False):
            self.status_signal.emit("🔍 Inspecting subtitles...")
            
            # جلب مسار ملف الإعدادات
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
            primary_sub_lang = "ar"
            secondary_sub_lang = "en"
            fallback_enabled = False
            
            if os.path.exists(settings_file):
                try:
                    import json
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        primary_sub_lang = data.get("primary_sub_lang", "ar")
                        secondary_sub_lang = data.get("secondary_sub_lang", "en")
                        fallback_enabled = data.get("download_any_sub_fallback", False)
                except Exception:
                    pass

            # جلب البيانات من يوتيوب للفيديو المخصص
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

            # الآن نبدأ الفحص بناءً على الأولويات:
            chosen_sub_lang = None
            chosen_sub_type = None
            
            # دالة مساعدة لمطابقة اللغات
            def match_lang_code(target_lang, dict_lang_code):
                return dict_lang_code.split('-')[0].lower() == target_lang.lower()

            # 1. ترجمة يدوية باللغة الأولى
            for lang, s_info in subtitles_dict.items():
                if s_info['type'] == 'Manual' and match_lang_code(primary_sub_lang, lang):
                    chosen_sub_lang = lang
                    chosen_sub_type = "primary_manual"
                    break

            # 2. ترجمة يدوية باللغة الثانية
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    if s_info['type'] == 'Manual' and match_lang_code(secondary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "secondary_manual"
                        break

            # 3. ترجمة تلقائية أصلية (org) باللغة الأولى
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    is_original = "-orig" in lang.lower() or "-original" in lang.lower()
                    if s_info['type'] == 'Auto' and is_original and match_lang_code(primary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "primary_auto_orig"
                        break

            # 4. ترجمة تلقائية أصلية (org) باللغة الثانية
            if not chosen_sub_lang:
                for lang, s_info in subtitles_dict.items():
                    is_original = "-orig" in lang.lower() or "-original" in lang.lower()
                    if s_info['type'] == 'Auto' and is_original and match_lang_code(secondary_sub_lang, lang):
                        chosen_sub_lang = lang
                        chosen_sub_type = "secondary_auto_orig"
                        break

            # 5. تنزيل أي ترجمة تلقائية أصلية أو يدوية كخيار احتياطي (Fallback) إذا كان مفعلاً
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

            # إطلاق الإشعارات بناءً على ما تم اختياره
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

        ydl_opts = {
            'outtmpl': self.save_path,
            'quiet': True,
            'nocolor': True,
            'writethumbnail': True,
            'progress_hooks': [self.my_hook],
            'postprocessors': [],
            'overwrites': True,
            'socket_timeout': 20, # منع التجمد اللانهائي عند تقطع الشبكة
            'ratelimit': getattr(self, 'current_limit', None)
        }

        # التحقق من وجود مسار محلي أو نظامي لـ FFmpeg وإضافته لـ yt-dlp
        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)

        # إذا اختار المستخدم تحميل ترجمة، نفعّلها في yt-dlp
        if self.sub_lang:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True # لدعم التلقائي واليدوي معاً
            ydl_opts['subtitleslangs'] = [self.sub_lang]
            ydl_opts['subtitlesformat'] = 'srt'

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
            if chosen_ext in ['mp4', 'mkv', 'mov', 'webm']:
                ydl_opts['merge_output_format'] = chosen_ext

        ydl_opts['postprocessors'].append({'key': 'FFmpegMetadata', 'add_metadata': True})
        ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
        ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

        try:
            self.status_signal.emit("⏳ Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.ydl = ydl
                # تطبيق حد السرعة الموزع فورا لمنع تداخل السباق
                if hasattr(self, 'current_limit') and self.current_limit is not None:
                    ydl.params['ratelimit'] = self.current_limit
                ydl.download([self.url])

            # --- إعادة تسمية ملف الترجمة ليكون بنفس اسم الفيديو تماماً ---
            if self.sub_lang and not self.is_cancelled:
                base_path, _ = os.path.splitext(self.save_path)
                target_sub_path = f"{base_path}.srt"
                
                # البحث عن أي ملف ترجمة مكتمل بصيغة srt أو vtt أو ass
                found_sub = None
                for ext in ['.srt', '.vtt', '.ass']:
                    pattern = f"{base_path}*{ext}"
                    matches = glob.glob(pattern)
                    matches = [m for m in matches if m != target_sub_path]
                    if matches:
                        found_sub = matches[0]
                        break
                        
                if found_sub:
                    try:
                        if found_sub != target_sub_path:
                            if os.path.exists(target_sub_path):
                                os.remove(target_sub_path)
                            if found_sub.endswith('.srt'):
                                os.rename(found_sub, target_sub_path)
                            else:
                                # تحويل الصيغ vtt/ass إلى srt لتوحيد عملية الدمج
                                import subprocess
                                ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
                                cmd = [ffmpeg_path, "-y", "-i", found_sub, target_sub_path]
                                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                if res.returncode == 0 and os.path.exists(target_sub_path):
                                    os.remove(found_sub)
                    except Exception:
                        pass

            # --- Subtitle & Audio/Video Post-Processing ---
            if not self.is_cancelled:
                self.status_signal.emit("⚙️ Post-processing subtitles...")
                # 1. Load settings
                settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
                video_container = "mp4"
                embed_subtitles = False
                autoplay_subtitles = False
                external_sub_format = "srt"
                audio_sub_format = "lrc"
                embed_audio_sub = False
                audio_container = "m4a"
                
                if os.path.exists(settings_file):
                    try:
                        import json
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            video_container = data.get("video_container", "mp4")
                            embed_subtitles = data.get("embed_subtitles", False)
                            autoplay_subtitles = data.get("autoplay_subtitles", False)
                            external_sub_format = data.get("external_sub_format", "srt")
                            audio_sub_format = data.get("audio_sub_format", "lrc")
                            embed_audio_sub = data.get("embed_audio_sub", False)
                            audio_container = data.get("audio_container", "m4a")
                    except Exception:
                        pass

                base_path, _ = os.path.splitext(self.save_path)
                target_sub_path = f"{base_path}.srt"
                
                # Check if subtitle file was successfully downloaded
                if self.sub_lang and os.path.exists(target_sub_path):
                    import subprocess
                    ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
                    
                    if self.format_code.startswith("audio:"):
                        # Audio post-processing
                        if embed_audio_sub:
                            self.status_signal.emit("⚙️ Embedding subtitles into audio container...")
                            target_ext = f".{audio_container}"
                            if base_path.lower().endswith(target_ext.lower()):
                                final_audio_path = base_path
                            else:
                                final_audio_path = base_path + target_ext
                            
                            # Try copy first
                            cmd = [
                                ffmpeg_path, "-y",
                                "-i", self.save_path,
                                "-i", target_sub_path,
                                "-map", "0:a", "-map", "1:s?",
                                "-c:a", "copy"
                            ]
                            if audio_container in ['m4a', 'mp4']:
                                cmd += ["-c:s", "mov_text"]
                            else:
                                cmd += ["-c:s", "srt"]
                            cmd.append(final_audio_path)
                            
                            try:
                                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                if res.returncode != 0:
                                    # Fallback if copying fails (e.g. container mismatch), transcode audio to aac
                                    self.status_signal.emit("⚙️ Retrying audio embedding with transcoding...")
                                    cmd = [
                                        ffmpeg_path, "-y",
                                        "-i", self.save_path,
                                        "-i", target_sub_path,
                                        "-map", "0:a", "-map", "1:s?",
                                        "-c:a", "aac"
                                    ]
                                    if audio_container in ['m4a', 'mp4']:
                                        cmd += ["-c:s", "mov_text"]
                                    else:
                                        cmd += ["-c:s", "srt"]
                                    cmd.append(final_audio_path)
                                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                
                                if res.returncode == 0 and os.path.exists(final_audio_path):
                                    if self.save_path != final_audio_path and os.path.exists(self.save_path):
                                        os.remove(self.save_path)
                                    self.save_path = final_audio_path
                                    # Remove subtitle file since it's embedded
                                    if os.path.exists(target_sub_path):
                                        os.remove(target_sub_path)
                            except Exception as e:
                                print(f"Audio subtitle embedding failed: {e}")
                        else:
                            # External lyrics/subtitles next to audio
                            if audio_sub_format == "lrc":
                                self.status_signal.emit("⚙️ Converting subtitles to LRC lyrics...")
                                from utils.helpers import convert_to_lrc
                                convert_to_lrc(target_sub_path, base_path + ".lrc")
                                if os.path.exists(target_sub_path):
                                    os.remove(target_sub_path)
                            elif audio_sub_format in ["vtt", "ass"]:
                                self.status_signal.emit(f"⚙️ Converting subtitles to {audio_sub_format.upper()}...")
                                preferred_sub_path = base_path + f".{audio_sub_format}"
                                cmd = [ffmpeg_path, "-y", "-i", target_sub_path, preferred_sub_path]
                                try:
                                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                    if res.returncode == 0 and os.path.exists(preferred_sub_path):
                                        if os.path.exists(target_sub_path):
                                            os.remove(target_sub_path)
                                except Exception as e:
                                    print(f"Audio subtitle conversion failed: {e}")
                    else:
                        # Video post-processing
                        if embed_subtitles:
                            self.status_signal.emit("⚙️ Embedding subtitles into video container...")
                            ext = os.path.splitext(self.save_path)[1].lower().replace('.', '')
                            temp_output = self.save_path + ".temp" + os.path.splitext(self.save_path)[1]
                            
                            cmd = [
                                ffmpeg_path, "-y",
                                "-i", self.save_path,
                                "-i", target_sub_path,
                                "-map", "0", "-map", "1:s?",
                                "-c", "copy"
                            ]
                            if ext in ['mp4', 'mov']:
                                cmd += ["-c:s", "mov_text"]
                            elif ext == 'webm':
                                cmd += ["-c:s", "webvtt"]
                            else:
                                cmd += ["-c:s", "srt"]
                                
                            if autoplay_subtitles:
                                cmd += ["-disposition:s:0", "default"]
                                
                            cmd.append(temp_output)
                            
                            try:
                                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                if res.returncode == 0 and os.path.exists(temp_output):
                                    if os.path.exists(self.save_path):
                                        os.remove(self.save_path)
                                    os.rename(temp_output, self.save_path)
                                    # Remove subtitle file since it's embedded
                                    if os.path.exists(target_sub_path):
                                        os.remove(target_sub_path)
                                else:
                                    # If embedding failed, clean up temp file if created
                                    if os.path.exists(temp_output):
                                        os.remove(temp_output)
                                    print(f"Video subtitle embedding failed with exit code {res.returncode}")
                            except Exception as e:
                                print(f"Video subtitle embedding exception: {e}")
                        else:
                            # External subtitles next to video
                            if external_sub_format in ["vtt", "ass"]:
                                self.status_signal.emit(f"⚙️ Converting subtitles to {external_sub_format.upper()}...")
                                preferred_sub_path = base_path + f".{external_sub_format}"
                                cmd = [ffmpeg_path, "-y", "-i", target_sub_path, preferred_sub_path]
                                try:
                                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                    if res.returncode == 0 and os.path.exists(preferred_sub_path):
                                        if os.path.exists(target_sub_path):
                                            os.remove(target_sub_path)
                                except Exception as e:
                                    print(f"Video subtitle conversion failed: {e}")

            if not self.is_cancelled:
                self.finished_signal.emit(self.save_path)
                self.status_signal.emit("✅ Done!")
        except Exception as e:
            err_msg = str(e)
            if err_msg == "DOWNLOAD_CANCELLED":
                self.status_signal.emit("❌ Canceled")
                self.cleanup_files()
            else:
                if os.path.exists(self.save_path):
                    self.status_signal.emit("✅ Downloaded (Warning: Cover failed)")
                else:
                    # تفقد تفاصيل الخطأ لتنبيه المستخدم بشكل دقيق
                    if "ffmpeg" in err_msg.lower() or "ffprobe" in err_msg.lower():
                        self.status_signal.emit("❌ Error: FFmpeg is missing! Please install FFmpeg to support this format.")
                    else:
                        # تنظيف الخطأ ليكون مختصراً ومفهوماً
                        clean_err = err_msg.replace("ERROR:", "").replace("Error:", "").strip()
                        if "\n" in clean_err:
                            clean_err = clean_err.split("\n")[0]
                        if len(clean_err) > 80:
                            clean_err = clean_err[:77] + "..."
                        self.status_signal.emit(f"❌ Error: {clean_err}")

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
