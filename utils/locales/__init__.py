import sys
import os
import json
from utils.helpers import get_data_path

settings_path = get_data_path(os.path.join('data', 'settings.json'))

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

lang = resolve_lang(lang)

from utils.locales.strings_en import STRINGS as EN_STRINGS

def set_current_language(lang_setting):
    global lang, STRINGS
    actual_lang = resolve_lang(lang_setting)
    lang = actual_lang
    if actual_lang == "ar":
        try:
            from utils.locales.strings_ar import STRINGS as AR_STRINGS
            STRINGS = EN_STRINGS.copy()
            STRINGS.update(AR_STRINGS)
        except ImportError:
            STRINGS = EN_STRINGS
    else:
        STRINGS = EN_STRINGS

set_current_language(lang)

def tr(key, default=""):
    return STRINGS.get(key, default or key)