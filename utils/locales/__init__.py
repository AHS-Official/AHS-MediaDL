import os
import json

# تحديد مسار ملف settings.json
locales_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.dirname(locales_dir)
root_dir = os.path.dirname(utils_dir)
settings_path = os.path.join(root_dir, 'data', 'settings.json')

lang = "system"
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            lang = data.get("language", "system")
    except Exception:
        pass

def resolve_lang(lang_setting):
    if lang_setting == "system":
        try:
            import sys
            if sys.platform == 'win32':
                import ctypes
                lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                primary_lang = lcid & 0x3ff
                if primary_lang == 0x01: # LANG_ARABIC
                    return "ar"
                else:
                    return "en"
            else:
                import locale
                sys_lang, _ = locale.getlocale()
                if not sys_lang:
                    sys_lang = locale.getdefaultlocale()[0]
                if sys_lang and sys_lang.lower().startswith('ar'):
                    return "ar"
                else:
                    return "en"
        except Exception:
            return "en"
    return lang_setting

# تحديد اللغة الفعالة للتطبيق
lang = resolve_lang(lang)

# تحميل المفردات المناسبة بناءً على اللغة المحددة مع دعم آلية الاحتياط باللغة الإنجليزية (English Fallback)
from utils.locales.strings_en import STRINGS as EN_STRINGS

STRINGS = {}
if lang == "ar":
    try:
        from utils.locales.strings_ar import STRINGS as AR_STRINGS
        # دمج الكلمات: الكلمات العربية تُحدِّث الإنجليزية، وإذا غاب أي مفتاح يُعرض بالإنجليزية تلقائياً
        STRINGS = EN_STRINGS.copy()
        STRINGS.update(AR_STRINGS)
    except ImportError:
        STRINGS = EN_STRINGS
else:
    STRINGS = EN_STRINGS

def tr(key, default=""):
    """
    دالة جلب النصوص بناءً على المفتاح.
    إذا لم تجده تبحث عن القيمة الافتراضية الممررة، وإذا لم تجدها تطبع المفتاح نفسه.
    """
    return STRINGS.get(key, default or key)