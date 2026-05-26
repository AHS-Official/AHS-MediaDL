import os
import json

# ──────────────────────────────────────────────
#  Language Loader
# ──────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LANG_DIR = os.path.join(_BASE_DIR, "utils", "languages")

def _detect_language():
    try:
        from data.settings import app_config
        lang = app_config.get("language", "en")
        if lang == "system":
            return "en"
        return lang
    except Exception:
        pass
    return "en"

def _load_strings(lang_code):
    lang_file = os.path.join(_LANG_DIR, f"{lang_code}.json")
    if not os.path.exists(lang_file):
        lang_file = os.path.join(_LANG_DIR, "en.json")
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_lang = _detect_language()
is_ar = (_lang == "ar")
_strings = _load_strings(_lang)

# Expose all string keys as module-level attributes
for _key, _value in _strings.items():
    globals()[_key] = _value


# ──────────────────────────────────────────────
#  Utility Functions
# ──────────────────────────────────────────────

def format_size(bytes_val):
    """Format bytes into human-readable size string."""
    if not bytes_val or bytes_val <= 0:
        return "0.0 MB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def get_theme_icon(icon_name, size=24):
    """Dynamically loads an SVG icon and colors it based on the active dark/light theme."""
    try:
        from gui.theme import AppTheme
        color = "#e2e2f0" if AppTheme.current() == "dark" else "#1a1a2e"
    except Exception:
        color = "#e2e2f0" # Fallback color

    icons_dir = os.path.join(_BASE_DIR, "assets", "icons")
    svg_path = os.path.join(icons_dir, icon_name)
    
    from PyQt6.QtGui import QIcon
    if not os.path.exists(svg_path):
        return QIcon()

    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Dynamically inject the theme colors into stroke/fill
        svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')

        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray, Qt

        renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
    except Exception as e:
        print(f"Error rendering dynamic SVG icon {icon_name}: {e}")
        return QIcon(svg_path)


def extract_desc(template, val):
    """Extracts description from localized template (e.g. extracts 'Excellent' from template)"""
    try:
        formatted = template.format(val)
        if " - " in formatted:
            return formatted.split(" - ", 1)[1]
    except Exception:
        pass
    return ""


def send_system_notification(title, message):
    """Sends a non-blocking system-level native notification on Linux and Windows."""
    import sys
    import subprocess
    try:
        if sys.platform.startswith('linux'):
            # Linux native notification
            subprocess.Popen(['notify-send', title, message])
        elif sys.platform.startswith('win'):
            # Windows PowerShell native notification
            powershell_cmd = (
                f'[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
                f'$n = New-Object System.Windows.Forms.NotifyIcon; '
                f'$n.Icon = [System.Drawing.SystemIcons]::Information; '
                f'$n.BalloonTipTitle = "{title.replace(chr(34), chr(92)+chr(34))}"; '
                f'$n.BalloonTipText = "{message.replace(chr(34), chr(92)+chr(34))}"; '
                f'$n.Visible = $True; '
                f'$n.ShowBalloonTip(5000); '
                f'Start-Sleep -Seconds 5'
            )
            # Use CREATE_NO_WINDOW to avoid popup terminal flashes on Windows
            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            subprocess.Popen(["powershell", "-NoProfile", "-Command", powershell_cmd], creationflags=flags)
    except Exception as e:
        print(f"Failed to send system notification: {e}")

