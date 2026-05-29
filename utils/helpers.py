import os
import sys
import re
import json

def resource_path(relative_path):
    """
    تحجيم المسارات لتعمل أثناء التطوير أو بعد تحويل التطبيق إلى ملف تنفيذي (.exe)
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def clean_and_shorten_title(title, limit=150):
    """
    تنظيف اسم الفيديو من الرموز الممنوعة في الويندوز وتقصيره
    """
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    if len(clean) > limit:
        return clean[:limit-3] + "..."
    return clean

def get_colored_icon(relative_path, color_hex):
    """
    يقوم بقراءة ملف الـ SVG وتلوينه بلون الهكس المختار ديناميكياً
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
        print(f"Error coloring icon {relative_path}: {e}")
    return QIcon(path)

def get_current_theme_color():
    """
    جلب اللون الافتراضي للأيقونات بناءً على الثيم النشط في الإعدادات
    """
    settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'settings.json')
    theme = "auto"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                theme = data.get("theme", "auto")
        except:
            pass
    if theme == "auto":
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import Qt
        scheme = QGuiApplication.styleHints().colorScheme()
        theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
    return "#f1f5f9" if theme == "dark" else "#0f172a"

def get_full_language_name(code):
    """ 🌐 يقوم بتحويل كود اللغة الثنائي إلى الاسم الكامل المترجم حسب لغة التطبيق الحالية """
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

def convert_to_lrc(subtitle_path, lrc_path):
    """
    Converts a .vtt or .srt subtitle file to .lrc lyrics format.
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
        print(f"Error converting to LRC: {e}")
        return False
