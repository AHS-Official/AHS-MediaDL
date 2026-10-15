"""
Utility functions and system helpers for AHS-MediaDL.
"""

import os
import sys
import re
import json
from typing import Optional, Union, Dict, Any

def is_compiled() -> bool:
    """Returns True if the application is compiled (via Nuitka, PyInstaller, or frozen binary)."""
    return (
        getattr(sys, 'frozen', False)
        or hasattr(sys, '__compiled__')
        or '__compiled__' in globals()
    )

def get_app_root_dir() -> str:
    """
    Returns the root directory containing the application:
    - In compiled mode (Nuitka / PyInstaller), returns folder containing the .exe.
    - In development mode, returns project workspace root.
    """
    if is_compiled():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path: str) -> str:
    """
    Returns absolute path to resource, working for dev, Nuitka (.dist), and PyInstaller.
    
    :param relative_path: Path relative to application root.
    :return: Resolved absolute path.
    """
    if hasattr(sys, '_MEIPASS'):
        candidate = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(get_app_root_dir(), relative_path)

def get_data_dir() -> str:
    """
    Returns writable user data directory path.
    In compiled mode (.exe), returns OS app data location.
    In dev mode, returns workspace root.
    """
    if is_compiled():
        if sys.platform == "win32":
            base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
            data_dir = os.path.join(base_dir, "AHS-MediaDL")
        else:
            data_dir = os.path.expanduser("~/.local/share/AHS-MediaDL")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return get_app_root_dir()

def get_data_path(relative_path: str) -> str:
    """
    Returns full path to a file inside the writable user data directory.
    
    :param relative_path: Path relative to data directory.
    :return: Full path to target data file.
    """
    return os.path.join(get_data_dir(), relative_path)

def clean_and_shorten_title(title: str, limit: int = 150) -> str:
    """
    Cleans illegal OS filename characters from title and truncates if necessary.
    
    :param title: Video/audio title string.
    :param limit: Maximum allowed length.
    :return: Sanitized title string.
    """
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    if len(clean) > limit:
        return clean[:limit-3] + "..."
    return clean

def get_colored_icon(relative_path: str, color_hex: str) -> Any:
    """
    Reads an SVG icon file and dynamically recolors 'currentColor' to the given hex color.
    
    :param relative_path: Relative path to SVG icon file.
    :param color_hex: Target hex color string (e.g. "#f1f5f9").
    :return: QIcon object with colored SVG pixmap, or fallback QIcon.
    """
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtCore import QByteArray
    path = resource_path(relative_path)
    if not os.path.exists(path):
        return QIcon()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        colored_svg = svg_content.replace('currentColor', color_hex)
        ba = QByteArray(colored_svg.encode('utf-8'))
        pixmap = QPixmap()
        if pixmap.loadFromData(ba, 'SVG'):
            return QIcon(pixmap)
    except Exception as e:
        from utils.logger import logger
        logger.warning(f"Error coloring icon {relative_path}: {e}")
    return QIcon(path)

def get_masked_app_icon(size: int = 34, radius: int = 8) -> Any:
    """
    Loads application icon (icon.ico) and masks it with smooth anti-aliased rounded corners.
    
    :param size: Target display width/height in pixels.
    :param radius: Corner rounding radius in pixels.
    :return: High-DPI QPixmap with rounded corners.
    """
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath
    from PyQt6.QtCore import Qt
    ico_path = resource_path(os.path.join("assets", "icon.ico"))
    if not os.path.exists(ico_path):
        return QPixmap()
    scale_factor = 4
    render_size = size * scale_factor
    render_radius = radius * scale_factor
    
    original_pixmap = QIcon(ico_path).pixmap(render_size, render_size)
    if original_pixmap.isNull():
        return original_pixmap

    rounded = QPixmap(render_size, render_size)
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, render_size, render_size, render_radius, render_radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, original_pixmap)
    painter.end()
    
    rounded.setDevicePixelRatio(scale_factor)
    return rounded

def detect_system_theme() -> str:
    """
    Detects current OS theme preference ('dark' or 'light').
    
    :return: Theme string 'dark' or 'light'.
    """
    if sys.platform.startswith("linux"):
        is_dark = False
        try:
            import subprocess
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1
            )
            if res.returncode == 0:
                val = res.stdout.strip().strip("'").strip('"')
                if "dark" in val.lower():
                    is_dark = True
        except Exception:
            pass
            
        if not is_dark:
            try:
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1
                )
                if res.returncode == 0:
                    val = res.stdout.strip().strip("'").strip('"')
                    if "dark" in val.lower():
                        is_dark = True
            except Exception:
                pass
        return "dark" if is_dark else "light"
    else:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import Qt
        scheme = QGuiApplication.styleHints().colorScheme()
        return "dark" if scheme == Qt.ColorScheme.Dark else "light"

def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """
    Converts a HEX color string to CSS/Qt rgba() string representation.
    
    :param hex_color: Hex color string (e.g. "#ffffff" or "ffffff").
    :param alpha: Opacity value between 0.0 and 1.0.
    :return: Formatted 'rgba(r, g, b, alpha)' string.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return hex_color

def open_file_or_folder(path: str, select_file: bool = False) -> None:
    """
    Opens target file or folder in OS file manager or default player.
    
    :param path: Absolute path to target file or directory.
    :param select_file: If True, selects the file inside parent directory (Windows explorer).
    """
    import subprocess
    path = os.path.abspath(os.path.normpath(path))
    if not os.path.exists(path):
        return

    if select_file and sys.platform == 'win32':
        try:
            import ctypes
            ole32 = ctypes.oledll.ole32
            shell32 = ctypes.windll.shell32
            ole32.CoInitialize(None)
            pidl = shell32.ILCreateFromPathW(path)
            if pidl:
                shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
                shell32.ILFree(pidl)
                return
        except Exception:
            pass
        # Fallback if ctypes call fails
        subprocess.Popen(f'explorer /select,"{path}"')
        return

    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'linux':
        target = os.path.dirname(path) if select_file and os.path.isfile(path) else path
        subprocess.Popen(['xdg-open', target])
    elif sys.platform == 'darwin':
        if select_file:
            subprocess.Popen(['open', '-R', path])
        else:
            subprocess.Popen(['open', path])

def get_current_theme_color() -> str:
    """
    Returns default icon/text color hex based on active settings theme in memory.
    """
    try:
        from managers.settings_manager import SettingsManager
        theme = SettingsManager().get("theme", "auto")
    except Exception:
        theme = "auto"
    if theme == "auto":
        theme = detect_system_theme()
    return "#f1f5f9" if theme == "dark" else "#0f172a"

def get_full_language_name(code: str) -> str:
    """
    Converts 2-letter language code (e.g., 'ar', 'en') to human-readable language name.
    
    :param code: ISO language code string.
    :return: Full language name string.
    """
    from utils.locales import tr
    lang_names = {
        "ar": tr("lang_ar_name", "Arabic"),
        "en": tr("lang_en_name", "English"),
        "fr": tr("lang_fr_name", "French"),
        "es": tr("lang_es_name", "Spanish"),
        "de": tr("lang_de_name", "German"),
        "ru": tr("lang_ru_name", "Russian"),
        "zh": tr("lang_zh_name", "Chinese")
    }
    base_code = code.split('-')[0].lower()
    iso_languages = {
        "aa": "Afar", "ab": "Abkhazian", "ae": "Avestan", "af": "Afrikaans", "ak": "Akan",
        "am": "Amharic", "an": "Aragonese", "ar": "Arabic", "as": "Assamese", "av": "Avaric",
        "ay": "Aymara", "az": "Azerbaijani", "ba": "Bashkir", "be": "Belarusian", "bg": "Bulgarian",
        "bh": "Bihari", "bi": "Bislama", "bm": "Bambara", "bn": "Bengali", "bo": "Tibetan",
        "br": "Breton", "bs": "Bosnian", "ca": "Catalan", "ce": "Chechen", "ch": "Chamorro",
        "co": "Corsican", "cr": "Cree", "cs": "Czech", "cu": "Church Slavic", "cv": "Chuvash",
        "cy": "Welsh", "da": "Danish", "de": "German", "dv": "Divehi", "dz": "Dzongkha",
        "ee": "Ewe", "el": "Greek", "en": "English", "eo": "Esperanto", "es": "Spanish",
        "et": "Estonian", "eu": "Basque", "fa": "Persian", "ff": "Fulah", "fi": "Finnish",
        "fj": "Fijian", "fo": "Faroese", "fr": "French", "fy": "Western Frisian", "ga": "Irish",
        "gd": "Scottish Gaelic", "gl": "Galician", "gn": "Guarani", "gu": "Gujarati", "gv": "Manx",
        "ha": "Hausa", "he": "Hebrew", "hi": "Hindi", "ho": "Hiri Motu", "hr": "Croatian",
        "ht": "Haitian", "hu": "Hungarian", "hy": "Armenian", "hz": "Herero", "ia": "Interlingua",
        "id": "Indonesian", "ie": "Interlingue", "ig": "Igbo", "ii": "Sichuan Yi", "ik": "Inupiaq",
        "io": "Ido", "is": "Icelandic", "it": "Italian", "iu": "Inuktitut", "ja": "Japanese",
        "jv": "Javanese", "ka": "Georgian", "kg": "Kongo", "ki": "Kikuyu", "kj": "Kuanyama",
        "kk": "Kazakh", "kl": "Kalaallisut", "km": "Khmer", "kn": "Kannada", "ko": "Korean",
        "kr": "Kanuri", "ks": "Kashmiri", "ku": "Kurdish", "kv": "Komi", "kw": "Cornish",
        "ky": "Kirghiz", "la": "Latin", "lb": "Luxembourgish", "lg": "Ganda", "li": "Limburgish",
        "ln": "Lingala", "lo": "Lao", "lt": "Lithuanian", "lu": "Luba-Katanga", "lv": "Latvian",
        "mg": "Malagasy", "mh": "Marshallese", "mi": "Maori", "mk": "Macedonian", "ml": "Malayalam",
        "mn": "Mongolian", "mr": "Marathi", "ms": "Malay", "mt": "Maltese", "my": "Burmese",
        "na": "Nauru", "nb": "Norwegian Bokmål", "nd": "North Ndebele", "ne": "Nepali", "ng": "Ndonga",
        "nl": "Dutch", "nn": "Norwegian Nynorsk", "no": "Norwegian", "nr": "South Ndebele", "nv": "Navajo",
        "ny": "Chichewa", "oc": "Occitan", "oj": "Ojibwa", "om": "Oromo", "or": "Oriya",
        "os": "Ossetian", "pa": "Panjabi", "pi": "Pali", "pl": "Polish", "ps": "Pashto",
        "pt": "Portuguese", "qu": "Quechua", "rm": "Romansh", "rn": "Rundi", "ro": "Romanian",
        "ru": "Russian", "rw": "Kinyarwanda", "sa": "Sanskrit", "sc": "Sardinian", "sd": "Sindhi",
        "se": "Northern Sami", "sg": "Sango", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian",
        "sm": "Samoan", "sn": "Shona", "so": "Somali", "sq": "Albanian", "sr": "Serbian",
        "ss": "Swati", "st": "Southern Sotho", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili",
        "ta": "Tamil", "te": "Telugu", "tg": "Tajik", "th": "Thai", "ti": "Tigrinya",
        "tk": "Turkmen", "tl": "Tagalog", "tn": "Tswana", "to": "Tonga", "tr": "Turkish",
        "ts": "Tsonga", "tt": "Tatar", "tw": "Twi", "ty": "Tahitian", "ug": "Uighur",
        "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek", "ve": "Venda", "vi": "Vietnamese",
        "vo": "Volapük", "wa": "Walloon", "wo": "Wolof", "xh": "Xhosa", "yi": "Yiddish",
        "yo": "Yoruba", "za": "Zhuang", "zh": "Chinese", "zu": "Zulu"
    }
    name = lang_names.get(base_code) or iso_languages.get(base_code)
    if name:
        return name
    return base_code.upper()

def convert_to_lrc(subtitle_path: str, lrc_path: str) -> bool:
    """
    Converts a .vtt or .srt subtitle file to .lrc lyrics format.
    
    :param subtitle_path: Path to existing subtitle file (.vtt or .srt).
    :param lrc_path: Target path to save .lrc file.
    :return: True if conversion succeeded, False otherwise.
    """
    if not os.path.exists(subtitle_path):
        return False
    try:
        with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        lrc_lines = []
        timestamp_regex = re.compile(r'(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{2,3})')
        current_text = []
        current_time_str = None
        for line in lines:
            line_str = line.strip()
            if not line_str:
                if current_time_str and current_text:
                    clean_text = " ".join(current_text)
                    if clean_text:
                        lrc_lines.append(f"{current_time_str}{clean_text}")
                    current_text = []
                    current_time_str = None
                continue
            if "-->" in line_str:
                start_part = line_str.split("-->")[0].strip()
                match = timestamp_regex.search(start_part)
                if match:
                    hours = int(match.group(1)) if match.group(1) else 0
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    ms_str = match.group(4)
                    csecs = int(ms_str[:2])
                    total_minutes = hours * 60 + minutes
                    current_time_str = f"[{total_minutes:02d}:{seconds:02d}.{csecs:02d}]"
                continue
            if line_str.isdigit() or line_str.upper() == "WEBVTT" or line_str.startswith("NOTE"):
                continue
            clean_line = re.sub(r'<[^>]*>', '', line_str)
            if clean_line:
                current_text.append(clean_line)
        if current_time_str and current_text:
            clean_text = " ".join(current_text)
            if clean_text:
                lrc_lines.append(f"{current_time_str}{clean_text}")
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lrc_lines))
        return True
    except Exception as e:
        from utils.logger import logger
        logger.warning(f"Error converting to LRC: {e}")
        return False

def trim_working_set_memory() -> None:
    """
    Trims physical RAM usage (Working Set) on Windows using EmptyWorkingSet.
    Safely reduces idle/background RAM consumption down to ~4-10 MB.
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            psapi = ctypes.windll.psapi
            psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
            psapi.EmptyWorkingSet.restype = wintypes.BOOL
            psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
        except Exception:
            pass

