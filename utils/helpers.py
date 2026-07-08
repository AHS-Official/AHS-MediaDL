import os
import sys
import re

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
    
def clean_and_shorten_title(title, limit=150):
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    if len(clean) > limit:
        return clean[:limit-3] + "..."
    return clean

def get_app_dir():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv else __file__))

def is_ffmpeg_available():
    import shutil
    # Check if ffmpeg is in PATH
    if shutil.which("ffmpeg"):
        return True
    # Check if ffmpeg is in local folders
    app_dir = get_app_dir()
    local_dirs = [
        os.path.join(app_dir, "ffmpeg", "bin"),
        os.path.join(app_dir, "bin"),
        app_dir
    ]
    exts = [".exe", ""] if os.name == "nt" else [""]
    for l_dir in local_dirs:
        for ext in exts:
            p = os.path.join(l_dir, f"ffmpeg{ext}")
            if os.path.isfile(p):
                return True
    return False

def resource_path(relative_path):
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)