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

def get_app_icon_path():
    for name in ['icon_1.png', 'icon.ico', 'icon.png']:
        path = resource_path(os.path.join('assets', name))
        if os.path.exists(path):
            return path
    return None

def get_app_icon():
    from PyQt6.QtGui import QIcon
    p = get_app_icon_path()
    if p:
        return QIcon(p)
    return QIcon()

def format_views(count, is_ar=True):
    if count is None:
        return ""
    try:
        count = int(count)
    except (ValueError, TypeError):
        return ""
    if is_ar:
        if count >= 1_000_000_000:
            return f"{count / 1_000_000_000:.1f} مليار مشاهدة"
        elif count >= 1_000_000:
            return f"{count / 1_000_000:.1f} مليون مشاهدة"
        elif count >= 1_000:
            return f"{count / 1_000:.1f} ألف مشاهدة"
        else:
            return f"{count} مشاهدة"
    else:
        if count >= 1_000_000_000:
            return f"{count / 1_000_000_000:.1f}B views"
        elif count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        else:
            return f"{count} views"

def format_upload_date(upload_date_str, timestamp=None, is_ar=True):
    import datetime
    dt = None
    if timestamp:
        try:
            dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).date()
        except Exception:
            pass
    if not dt and upload_date_str and len(str(upload_date_str)) == 8:
        try:
            s = str(upload_date_str)
            dt = datetime.date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            pass
    if not dt:
        return ""
    
    today = datetime.datetime.now(datetime.timezone.utc).date()
    days = (today - dt).days
    if days < 0:
        days = 0
    
    years = days // 365
    months = days // 30
    weeks = days // 7

    if is_ar:
        if years >= 1:
            return f"قبل {years} سنة" if years == 1 else f"قبل {years} سنوات" if years < 11 else f"قبل {years} سنة"
        elif months >= 1:
            return f"قبل شهر" if months == 1 else f"قبل شهرين" if months == 2 else f"قبل {months} أشهر" if months < 11 else f"قبل {months} شهراً"
        elif weeks >= 1:
            return f"قبل أسبوع" if weeks == 1 else f"قبل أسبوعين" if weeks == 2 else f"قبل {weeks} أسابيع"
        elif days >= 1:
            return f"قبل يوم" if days == 1 else f"قبل يومين" if days == 2 else f"قبل {days} أيام"
        else:
            return "اليوم"
    else:
        if years >= 1:
            return f"{years} year ago" if years == 1 else f"{years} years ago"
        elif months >= 1:
            return f"{months} month ago" if months == 1 else f"{months} months ago"
        elif weeks >= 1:
            return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
        elif days >= 1:
            return f"{days} day ago" if days == 1 else f"{days} days ago"
        else:
            return "Today"