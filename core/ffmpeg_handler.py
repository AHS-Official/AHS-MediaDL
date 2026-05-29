import os
import shutil
from utils.locales import tr

def get_ffmpeg_path():
    """
    يبحث عن مسار ملف التشغيل لـ ffmpeg.
    يبحث أولاً في PATH الخاص بنظام التشغيل، ثم في المجلدات المحلية للبرنامج.
    """
    sys_path = shutil.which("ffmpeg")
    if sys_path:
        return sys_path
    local_dirs = [
        os.path.join(os.getcwd(), "ffmpeg", "bin"),
        os.path.join(os.getcwd(), "bin"),
        os.getcwd()
    ]
    exts = [".exe", ""] if os.name == "nt" else [""]
    for l_dir in local_dirs:
        for ext in exts:
            p = os.path.join(l_dir, f"ffmpeg{ext}")
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None

def get_ffprobe_path():
    """
    يبحث عن مسار ملف التشغيل لـ ffprobe.
    """
    sys_path = shutil.which("ffprobe")
    if sys_path:
        return sys_path
    local_dirs = [
        os.path.join(os.getcwd(), "ffmpeg", "bin"),
        os.path.join(os.getcwd(), "bin"),
        os.getcwd()
    ]
    exts = [".exe", ""] if os.name == "nt" else [""]
    for l_dir in local_dirs:
        for ext in exts:
            p = os.path.join(l_dir, f"ffprobe{ext}")
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None

def is_ffmpeg_available():
    """
    ترجع True إذا كان كل من ffmpeg و ffprobe متوفرين.
    """
    return get_ffmpeg_path() is not None and get_ffprobe_path() is not None

def process_download_post_processing(worker, save_path, sub_lang, format_code):
    """
    يقوم بمعالجة ودمج ملفات الترجمة وتحويل الصيغ للصوت والفيديو باستخدام FFmpeg بعد اكتمال التنزيل.
    يقوم بتحديث واجهة المستخدم عبر إرسال إشارات الحالة من خلال الـ worker الممرر.
    """
    import json
    import subprocess
    import glob
    from utils.helpers import convert_to_lrc
    if worker:
        worker.status_signal.emit(tr("status_post_processing_subs", "⚙️ Post-processing subtitles..."))
    base_path, original_ext = os.path.splitext(save_path)
    target_sub_path = f"{base_path}.srt"
    if sub_lang:
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
                        ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
                        cmd = [ffmpeg_path, "-y", "-i", found_sub, target_sub_path]
                        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if res.returncode == 0 and os.path.exists(target_sub_path):
                            os.remove(found_sub)
            except Exception as e:
                print(f"Subtitle renaming/converting failed: {e}")
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
    if format_code.startswith("audio:"):
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
                        print(f"Direct move failed, falling back to FFmpeg copy: {e}")
                        ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
                        cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                        try:
                            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            if res.returncode == 0 and os.path.exists(final_audio_path):
                                if os.path.exists(actual_downloaded_file):
                                    os.remove(actual_downloaded_file)
                                save_path = final_audio_path
                        except Exception as ex:
                            print(f"Fallback FFmpeg copy failed: {ex}")
                else:
                    if worker:
                        worker.status_signal.emit(tr("status_processing", "⚙️ Converting..."))
                    ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
                    if audio_container == "mp3":
                        cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "libmp3lame", "-q:a", "2", final_audio_path]
                    elif audio_container == "m4a":
                        cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "aac", final_audio_path]
                    else:
                        cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                    try:
                        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if res.returncode == 0 and os.path.exists(final_audio_path):
                            if os.path.exists(actual_downloaded_file):
                                os.remove(actual_downloaded_file)
                            save_path = final_audio_path
                        else:
                            cmd = [ffmpeg_path, "-y", "-i", actual_downloaded_file, "-c:a", "copy", final_audio_path]
                            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            if res.returncode == 0 and os.path.exists(final_audio_path):
                                if os.path.exists(actual_downloaded_file):
                                    os.remove(actual_downloaded_file)
                                save_path = final_audio_path
                    except Exception as e:
                        print(f"Audio container wrapping failed: {e}")
    if sub_lang and os.path.exists(target_sub_path):
        ffmpeg_path = get_ffmpeg_path() or "ffmpeg"
        if format_code.startswith("audio:"):
            if embed_audio_sub:
                if worker:
                    worker.status_signal.emit(tr("status_embedding_audio_subs", "⚙️ Embedding subtitles into audio container..."))
                target_ext = f".{audio_container}"
                if base_path.lower().endswith(target_ext.lower()):
                    final_audio_path = base_path
                else:
                    final_audio_path = base_path + target_ext
                cmd = [
                    ffmpeg_path, "-y",
                    "-i", save_path,
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
                        if worker:
                            worker.status_signal.emit(tr("status_retrying_audio_embedding", "⚙️ Retrying audio embedding with transcoding..."))
                        cmd = [
                            ffmpeg_path, "-y",
                            "-i", save_path,
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
                        if save_path != final_audio_path and os.path.exists(save_path):
                            os.remove(save_path)
                        save_path = final_audio_path
                        if os.path.exists(target_sub_path):
                            os.remove(target_sub_path)
                except Exception as e:
                    print(f"Audio subtitle embedding failed: {e}")
            else:
                if audio_sub_format == "lrc":
                    if worker:
                        worker.status_signal.emit(tr("status_converting_lrc", "⚙️ Converting subtitles to LRC lyrics..."))
                    convert_to_lrc(target_sub_path, base_path + ".lrc")
                    if os.path.exists(target_sub_path):
                        os.remove(target_sub_path)
                elif audio_sub_format in ["vtt", "ass"]:
                    if worker:
                        worker.status_signal.emit(tr("status_converting_subs_format", "⚙️ Converting subtitles to {format}...").format(format=audio_sub_format.upper()))
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
            if embed_subtitles:
                if worker:
                    worker.status_signal.emit(tr("status_embedding_video_subs", "⚙️ Embedding subtitles into video container..."))
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
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res.returncode == 0 and os.path.exists(temp_output):
                        if os.path.exists(save_path):
                            os.remove(save_path)
                        os.rename(temp_output, save_path)
                        if os.path.exists(target_sub_path):
                            os.remove(target_sub_path)
                    else:
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                        print(f"Video subtitle embedding failed with exit code {res.returncode}")
                except Exception as e:
                    print(f"Video subtitle embedding exception: {e}")
            else:
                if external_sub_format in ["vtt", "ass"]:
                    if worker:
                        worker.status_signal.emit(tr("status_converting_subs_format", "⚙️ Converting subtitles to {format}...").format(format=external_sub_format.upper()))
                    preferred_sub_path = base_path + f".{external_sub_format}"
                    cmd = [ffmpeg_path, "-y", "-i", target_sub_path, preferred_sub_path]
                    try:
                        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if res.returncode == 0 and os.path.exists(preferred_sub_path):
                            if os.path.exists(target_sub_path):
                                os.remove(target_sub_path)
                    except Exception as e:
                        print(f"Video subtitle conversion failed: {e}")
    return save_path
