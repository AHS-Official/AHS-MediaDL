import os
import shutil

def get_ffmpeg_path():
    """
    يبحث عن مسار ملف التشغيل لـ ffmpeg.
    يبحث أولاً في PATH الخاص بنظام التشغيل، ثم في المجلدات المحلية للبرنامج.
    """
    # 1. التحقق من مسار النظام (System PATH)
    sys_path = shutil.which("ffmpeg")
    if sys_path:
        return sys_path
        
    # 2. التحقق من المجلدات المحلية (مفيد للنسخ المحمولة Portable)
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
