import os
import sys
import shutil
import json
import subprocess
import time
import glob
import re
from utils.locales import tr
from utils.helpers import get_data_path, convert_to_lrc
from utils.logger import logger

def get_binary_path(binary_name):
    """
    يبحث عن مسار ملف التشغيل للأداة المحددة عبر BinaryManager:
    1. يبحث أولاً في مجلد bin المحلي بجانب التطبيق.
    2. يبحث في مجلد بيانات المستخدم (AppData/bin).
    3. إذا لم يجده، يبحث في متغيرات بيئة النظام (System PATH).
    """
    from managers.binary_manager import BinaryManager
    return BinaryManager.get_binary_path(binary_name)

def get_ffmpeg_path():
    """
    يبحث عن مسار ملف التشغيل لـ ffmpeg.
    """
    return get_binary_path("ffmpeg")

def get_ffprobe_path():
    """
    يبحث عن مسار ملف التشغيل لـ ffprobe.
    """
    return get_binary_path("ffprobe")


def get_media_duration_seconds(file_path):
    ffprobe = get_ffprobe_path()
    if not ffprobe or not file_path or not os.path.exists(file_path):
        return 0
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        run_kwargs = {}
        if sys.platform == 'win32':
            run_kwargs['creationflags'] = 0x08000000
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, **run_kwargs)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0

def run_with_cancellation(cmd, cancel_check=None, worker=None, status_prefix=None, total_duration=0, **kwargs):
    """
    Runs a subprocess command in a non-blocking way, checking for cancellation and tracking FFmpeg progress.
    """
    if 'stdout' not in kwargs:
        kwargs['stdout'] = subprocess.DEVNULL
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.PIPE
    if 'text' not in kwargs and 'universal_newlines' not in kwargs:
        kwargs['text'] = True
    if sys.platform == 'win32' and 'creationflags' not in kwargs:
        kwargs['creationflags'] = 0x08000000

    # Inject -stats_period 0.5 into ffmpeg commands so stderr.readline() never blocks for long
    if cmd and "ffmpeg" in os.path.basename(cmd[0]).lower() and "-stats_period" not in cmd:
        cmd = [cmd[0], "-stats_period", "0.5"] + cmd[1:]
        
    process = subprocess.Popen(cmd, **kwargs)
    time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+|\d+)')
    last_pct = -1

    try:
        while process.poll() is None:
            if cancel_check and cancel_check():
                try:
                    process.kill()
                    process.wait(timeout=1)
                except Exception:
                    pass
                raise Exception("DOWNLOAD_CANCELLED")

            if worker and total_duration > 0 and process.stderr:
                try:
                    line = process.stderr.readline()
                    if line:
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='ignore')
                        match = time_pattern.search(line)
                        if match:
                            h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
                            curr_sec = h * 3600 + m * 60 + s
                            pct = min(99, int((curr_sec / total_duration) * 100))
                            if pct != last_pct and pct >= 0:
                                last_pct = pct
                                if status_prefix:
                                    worker.status_signal.emit(f"{status_prefix} ({pct}%)")
                except Exception:
                    pass

            time.sleep(0.05)
    finally:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        process.wait()
        
    return process


def is_ffmpeg_available():
    """
    ترجع True إذا كان كل من ffmpeg و ffprobe متوفرين.
    """
    return get_ffmpeg_path() is not None and get_ffprobe_path() is not None


def _handle_subtitles_rename(base_path, target_sub_path, ffmpeg_path, cancel_check=None):
    found_sub = None
    folder, base_name = os.path.split(base_path)
    target_prefix = base_name + "."
    if os.path.exists(folder):
        try:
            for entry in os.listdir(folder):
                full_path = os.path.join(folder, entry)
                if full_path == target_sub_path:
                    continue
                if entry.startswith(target_prefix):
                    ext = os.path.splitext(entry)[1].lower()
                    if ext in ['.srt', '.vtt', '.ass']:
                        found_sub = full_path
                        break
        except Exception as e:
            logger.error(f"Error listing directory for subtitles: {e}")

    if found_sub:
        try:
            if found_sub != target_sub_path:
                if os.path.exists(target_sub_path):
                    os.remove(target_sub_path)
                if found_sub.endswith('.srt'):
                    os.rename(found_sub, target_sub_path)
                else:
                    cmd = [ffmpeg_path, "-y", "-i", found_sub, target_sub_path]
                    res = run_with_cancellation(cmd, cancel_check=cancel_check)
                    if res.returncode == 0 and os.path.exists(target_sub_path):
                        os.remove(found_sub)
        except Exception as e:
            logger.error(f"Subtitle renaming/converting failed: {e}")

def _convert_and_extract_audio(worker, base_path, save_path, audio_container, ffmpeg_path, cancel_check=None):
    actual_downloaded_file = None
    for ext in ['.m4a', '.mp3', '.mka', '.aac', '.webm', '.ogg', '.wav']:
        p_double = base_path + ext + ext
        if os.path.exists(p_double):
            actual_downloaded_file = p_double
            break
    if not actual_downloaded_file:
        if not os.path.exists(save_path):
            for ext in ['.m4a', '.mp3', '.mka', '.aac', '.webm', '.ogg', '.wav']:
                p = base_path + ext
                if os.path.exists(p):
                    actual_downloaded_file = p
                    break
        else:
            actual_downloaded_file = save_path
    if actual_downloaded_file:
        target_ext = f".{audio_container}"
        final_audio_path = base_path + target_ext
        actual_ext = os.path.splitext(actual_downloaded_file)[1].lower()
        is_same_format = actual_ext == target_ext or actual_downloaded_file.lower().endswith(target_ext.lower() + target_ext.lower())
        if actual_downloaded_file != final_audio_path:
            if is_same_format:
                try:
                    if os.path.exists(final_audio_path):
                        os.remove(final_audio_path)
                    shutil.move(actual_downloaded_file, final_audio_path)
                    save_path = final_audio_path
                except Exception as e:
                    logger.error(f"Direct move failed, falling back to FFmpeg copy: {e}")
                    cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                    try:
                        total_dur = get_media_duration_seconds(actual_downloaded_file)
                        status_prefix = tr("status_processing", "⚙️ Processing...")
                        res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                        if res.returncode == 0 and os.path.exists(final_audio_path):
                            if os.path.exists(actual_downloaded_file):
                                os.remove(actual_downloaded_file)
                            save_path = final_audio_path
                    except Exception as ex:
                        logger.error(f"Fallback FFmpeg copy failed: {ex}")
            else:
                total_dur = get_media_duration_seconds(actual_downloaded_file)
                status_prefix = tr("status_processing", "⚙️ Processing...")
                if worker:
                    worker.status_signal.emit(status_prefix)
                if audio_container == "mp3":
                    cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "libmp3lame", "-q:a", "2", final_audio_path]
                elif audio_container == "m4a":
                    cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "aac", final_audio_path]
                else:
                    cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                try:
                    res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                    if res.returncode == 0 and os.path.exists(final_audio_path):
                        if os.path.exists(actual_downloaded_file):
                            os.remove(actual_downloaded_file)
                        save_path = final_audio_path
                    else:
                        cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                        res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                        if res.returncode == 0 and os.path.exists(final_audio_path):
                            if os.path.exists(actual_downloaded_file):
                                os.remove(actual_downloaded_file)
                            save_path = final_audio_path
                except Exception as e:
                    logger.error(f"Audio container wrapping failed: {e}")
    return save_path

def _process_audio_subtitles(worker, base_path, save_path, target_sub_path, audio_sub_format, ffmpeg_path, cancel_check=None):
    total_dur = get_media_duration_seconds(save_path)
    status_prefix = tr("status_processing", "⚙️ Processing...")
    
    if os.path.exists(target_sub_path):
        if audio_sub_format == "lrc":
            if worker:
                worker.status_signal.emit(status_prefix)
            lrc_path = base_path + ".lrc"
            if convert_to_lrc(target_sub_path, lrc_path):
                if os.path.exists(target_sub_path):
                    os.remove(target_sub_path)
        elif audio_sub_format in ["vtt", "ass"]:
            if worker:
                worker.status_signal.emit(status_prefix)
            preferred_sub_path = base_path + f".{audio_sub_format}"
            cmd = [ffmpeg_path, "-y", "-i", target_sub_path, preferred_sub_path]
            try:
                res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                if res.returncode == 0 and os.path.exists(preferred_sub_path):
                    if os.path.exists(target_sub_path):
                        os.remove(target_sub_path)
            except Exception as e:
                logger.error(f"Audio subtitle conversion failed: {e}")
    return save_path

def _convert_video_container(worker, base_path, save_path, ffmpeg_path, cancel_check=None):
    if not os.path.exists(save_path):
        for ext in ['.mp4', '.mkv', '.webm', '.flv']:
            alt_path = base_path + ext
            if os.path.exists(alt_path):
                total_dur = get_media_duration_seconds(alt_path)
                status_prefix = tr("status_processing", "⚙️ Processing...")
                cmd = [ffmpeg_path, "-y", "-i", alt_path, "-c", "copy", save_path]
                try:
                    res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                    if res.returncode == 0 and os.path.exists(save_path):
                        os.remove(alt_path)
                        break
                except Exception as e:
                    logger.error(f"Container copy conversion failed: {e}")
                try:
                    import shutil
                    shutil.move(alt_path, save_path)
                    break
                except Exception as e:
                    logger.error(f"Failed to move {alt_path} to {save_path}: {e}")
    return save_path

def _embed_subtitles_to_video(worker, base_path, save_path, target_sub_path, embed_subtitles, autoplay_subtitles, external_sub_format, ffmpeg_path, cancel_check=None):
    total_dur = get_media_duration_seconds(save_path)
    status_prefix = tr("status_processing", "⚙️ Processing...")
    if embed_subtitles:
        if worker:
            worker.status_signal.emit(status_prefix)
        ext = os.path.splitext(save_path)[1].lower().replace('.', '')
        temp_output = save_path + ".temp" + os.path.splitext(save_path)[1]
        cmd = [
            ffmpeg_path, "-y",
            "-i", save_path,
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
            res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
            if res.returncode == 0 and os.path.exists(temp_output):
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(temp_output, save_path)
                if os.path.exists(target_sub_path):
                    os.remove(target_sub_path)
            else:
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                logger.error(f"Video subtitle embedding failed with exit code {res.returncode}")
        except Exception as e:
            logger.error(f"Video subtitle embedding exception: {e}")
    else:
        if external_sub_format in ["vtt", "ass"]:
            if worker:
                worker.status_signal.emit(status_prefix)
            preferred_sub_path = base_path + f".{external_sub_format}"
            cmd = [ffmpeg_path, "-y", "-i", target_sub_path, preferred_sub_path]
            try:
                res = run_with_cancellation(cmd, cancel_check=cancel_check, worker=worker, status_prefix=status_prefix, total_duration=total_dur)
                if res.returncode == 0 and os.path.exists(preferred_sub_path):
                    if os.path.exists(target_sub_path):
                        os.remove(target_sub_path)
            except Exception as e:
                logger.error(f"Video subtitle conversion failed: {e}")
    return save_path

def process_download_post_processing(worker, save_path, sub_lang, format_code, cancel_check=None):
    """
    يقوم بمعالجة ودمج ملفات الترجمة وتحويل الصيغ للصوت والفيديو باستخدام FFmpeg بعد اكتمال التنزيل.
    يقوم بتحديث واجهة المستخدم عبر إرسال إشارات الحالة من خلال الـ worker الممرر.
    """
    if worker:
        worker.status_signal.emit(tr("status_processing", "⚙️ Processing..."))
    
    base_path, original_ext = os.path.splitext(save_path)
    target_sub_path = f"{base_path}.srt"
    ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
    
    if sub_lang:
        _handle_subtitles_rename(base_path, target_sub_path, ffmpeg_path, cancel_check)
        if worker:
            if os.path.exists(target_sub_path):
                worker.subtitle_status = "downloaded"
                if not hasattr(worker, 'downloaded_sub_lang'):
                    from utils.helpers import get_full_language_name
                    worker.downloaded_sub_lang = get_full_language_name(sub_lang)
            else:
                worker.subtitle_status = "failed"

    from managers.settings_manager import SettingsManager
    mgr = SettingsManager()
    embed_subtitles = mgr.get("embed_subtitles", False)
    autoplay_subtitles = mgr.get("autoplay_subtitles", False)
    external_sub_format = mgr.get("external_sub_format", "srt")
    audio_sub_format = mgr.get("audio_sub_format", "lrc")
    embed_audio_sub = mgr.get("embed_audio_sub", False)
    audio_container = mgr.get("audio_container", "mp3")

    if format_code.startswith("audio:"):
        save_path = _convert_and_extract_audio(worker, base_path, save_path, audio_container, ffmpeg_path, cancel_check)
        if sub_lang and os.path.exists(target_sub_path):
            save_path = _process_audio_subtitles(worker, base_path, save_path, target_sub_path, audio_sub_format, ffmpeg_path, cancel_check)
    else:
        save_path = _convert_video_container(worker, base_path, save_path, ffmpeg_path, cancel_check)
        if sub_lang and os.path.exists(target_sub_path):
            save_path = _embed_subtitles_to_video(worker, base_path, save_path, target_sub_path, embed_subtitles, autoplay_subtitles, external_sub_format, ffmpeg_path, cancel_check)
            
    return save_path
