import locale
import os
from utils.settings import app_config

_lang = app_config.get("language", "system")
if _lang == "system":
    sys_lang = ""
    try:
        from PyQt6.QtCore import QLocale
        sys_lang = QLocale.system().name()
    except Exception:
        pass
    if not sys_lang:
        try:
            sys_lang = locale.getdefaultlocale()[0] or ""
        except Exception:
            pass
    if not sys_lang:
        sys_lang = os.environ.get("LANG", "") or os.environ.get("LANGUAGE", "")
    
    _lang = "ar" if sys_lang.lower().startswith("ar") else "en"

is_ar = (_lang == "ar")

# ==========================================
# 1. نصوص التطبيق والتبويبات (App & Tabs)
# ==========================================
APP_TITLE = "AHS-MediaDL"
APP_TAB_ADD = "الرئيسية" if is_ar else "Home"
APP_TAB_QUEUE = "التنزيلات" if is_ar else "Downloads"

APP_SET_TITLE = "⚙️ الإعدادات" if is_ar else "⚙️ Settings"

# تبويبات الإعدادات
SET_TAB_GENERAL_APPEARANCE = "⚙️ عام والمظهر" if is_ar else "⚙️ General & Appearance"
SET_TAB_DOWNLOADS_SUBS = "📥 التحميلات والترجمة" if is_ar else "📥 Downloads & Subtitles"
SET_TAB_ADVANCED = "🛠️ خيارات متقدمة" if is_ar else "🛠️ Advanced Options"

LBL_SET_FONT_FAMILY = "نوع الخط:" if is_ar else "Font Family:"
LBL_SET_FONT_SIZE = "حجم الخط:" if is_ar else "Font Size:"
TOOLTIP_DOWNGRADE_INFO = "السماح بتقليل الجودة في حالة قوائم التشغيل عندما تكون الجودة المحددة غير متوفرة" if is_ar else "Allow quality downgrade for playlists when selected resolution is unavailable"

# ==========================================
# 2. الأزرار (Buttons)
# ==========================================
BTN_SETTINGS = "⚙️ الإعدادات" if is_ar else "⚙️ Settings"

BTN_DOWNLOAD = "⬇️ تحميل الآن" if is_ar else "⬇️ Download Now"
BTN_DOWNLOAD_SIZE = "⬇️ تحميل الآن ({})" if is_ar else "⬇️ Download Now ({})"
BTN_PAUSE_ALL = "⏸️ إيقاف الكل" if is_ar else "⏸️ Pause All"
BTN_RESUME_ALL = "▶️ استئناف الكل" if is_ar else "▶️ Resume All"
BTN_CANCEL_ALL = "🚫 إلغاء الكل" if is_ar else "🚫 Cancel All"
BTN_CLEAR_COMPLETED = "🧹 مسح المكتمل" if is_ar else "🧹 Clear Completed"
BTN_SET_BROWSE = "📁 تصفح..." if is_ar else "📁 Browse..."
BTN_SET_RESTART = "🔄 إعادة تشغيل" if is_ar else "🔄 Restart"
BTN_FACTORY_RESET = "⚠️ إعادة ضبط المصنع" if is_ar else "⚠️ Factory Reset"
MSG_RESET_CONFIRM = "هل أنت متأكد من مسح كل الإعدادات والعودة للوضع الافتراضي؟ (سيتم إعادة تشغيل التطبيق فوراً)" if is_ar else "Are you sure you want to reset all settings? (App will restart immediately)"

# ==========================================
# 3. النصوص الوصفية (Labels)
# ==========================================
LBL_FETCHING = "⏳ جاري جلب البيانات... يرجى الانتظار." if is_ar else "⏳ Fetching details... Please wait."
LBL_TOTAL_SPEED = "🚀 السرعة الكلية: " if is_ar else "🚀 Total Speed: "
LBL_SET_THEME = "المظهر (السمة):" if is_ar else "Theme (Appearance):"
LBL_SET_LANG = "اللغة (تتطلب إعادة تشغيل):" if is_ar else "Language (Requires Restart):"
LBL_SET_DL_LOC = "مسار الحفظ:" if is_ar else "Download Location:"
LBL_SET_SPEED = "تحديد السرعة:" if is_ar else "Speed Limit:"
LBL_SET_CONCURRENT = "التحميلات المتزامنة:" if is_ar else "Concurrent Downloads:"
LBL_SET_COOKIES = "متصفح الكوكيز:" if is_ar else "Browser for Cookies:"
LBL_SET_PRIM_SUB = "الترجمة الأساسية:" if is_ar else "Default Primary Subtitle:"
LBL_SET_SEC_SUB = "الترجمة الثانوية:" if is_ar else "Default Secondary Subtitle:"

# ==========================================
# 4. مربعات التحديد (Checkboxes)
# ==========================================
CHK_SELECT_ALL = "✅ تحديد الكل" if is_ar else "✅ Select All"
CHK_SUBTITLES = "📝 الشرح والترجمة (CC)" if is_ar else "📝 Sub/CC"
CHK_EMBED_SUBS = "📌 دمج في الفيديو" if is_ar else "📌 Embed in Video"
CHK_SET_NOTIFY = "الإشعارات عند الانتهاء" if is_ar else "Notifications when finished"
CHK_SET_THUMB = "🖼️ عرض الصور المصغرة" if is_ar else "🖼️ Show Thumbnails"
CHK_SET_DATA_SAVER = "توفير البيانات (بدء يدوي)" if is_ar else "Data Saver (Manual Start)"
CHK_SET_DOWNGRADE = "السماح بخفض الجودة تلقائياً" if is_ar else "Allow automatic quality downgrade"

# ==========================================
# 5. خيارات القوائم (ComboBox Options)
# ==========================================
OPT_SET_THEME_AUTO = "النظام الافتراضي" if is_ar else "System Default"
OPT_SET_THEME_LIGHT = "الوضع الفاتح" if is_ar else "Light Mode"
OPT_SET_THEME_DARK = "الوضع الداكن" if is_ar else "Dark Mode"
OPT_SET_LANG_SYS = "لغة النظام" if is_ar else "System Default"
OPT_SET_LANG_EN = "English" if is_ar else "English"
OPT_SET_LANG_AR = "العربية" if is_ar else "Arabic"
OPT_SET_LOC_ASK = "اسألني كل مرة" if is_ar else "Ask me every time"
OPT_SET_LOC_AUTO = "مجلد التنزيلات" if is_ar else "Downloads Folder"
OPT_SET_LOC_CUSTOM = "مخصص..." if is_ar else "Custom..."
OPT_SET_COOKIE_NONE = "معطل" if is_ar else "Disabled"
OPT_SET_COOKIE_CUSTOM = "ملف مخصص (cookies.txt)..." if is_ar else "Custom File (cookies.txt)..."
MSG_SELECT_COOKIE_FILE = "اختر ملف الكوكيز" if is_ar else "Select Cookies File"
OPT_SET_SPEED_NONE = "بدون حدود" if is_ar else "No Limit"

# ==========================================
# 6. جودات الفيديو والصوت (Qualities)
# ==========================================
QUAL_4K = "🎬 جودة فائقة - 4K" if is_ar else "🎬 Ultra HD - 4K"
QUAL_2K = "🎬 جودة عالية جداً - 2K" if is_ar else "🎬 Quad HD - 2K"
QUAL_1080 = "🎬 دقة كاملة - 1080p" if is_ar else "🎬 Full HD - 1080p"
QUAL_720 = "🎬 عالية الدقة - 720p" if is_ar else "🎬 HD - 720p"
QUAL_480 = "🎬 جودة عادية - 480p" if is_ar else "🎬 Standard - 480p"
QUAL_360 = "🎬 جودة موبايل - 360p" if is_ar else "🎬 Mobile - 360p"
QUAL_240 = "🎬 جودة منخفضة - 240p" if is_ar else "🎬 Low - 240p"
QUAL_144 = "🎬 توفير بيانات - 144p" if is_ar else "🎬 Data Saver - 144p"

AUDIO_M4A = "🎵 صوت M4A سريع (128K)" if is_ar else "🎵 Fast M4A (128K)"
AUDIO_MP3_70 = "🎵 صوت MP3 صغير (70K)" if is_ar else "🎵 Mini MP3 (70K)"
AUDIO_MP3_128 = "🎵 صوت MP3 قياسي (128K)" if is_ar else "🎵 Standard MP3 (128K)"
AUDIO_MP3_160 = "🎵 صوت MP3 بجودة (160K)" if is_ar else "🎵 HQ MP3 (160K)"
AUDIO_MP3_320 = "🎵 صوت MP3 احترافي (320K)" if is_ar else "🎵 Premium MP3 (320K)"

# ==========================================
# 7. حالات الطابور (Queue Status)
# ==========================================
STATUS_WAITING = "في انتظار التحميل..." if is_ar else "Waiting in queue..."
STATUS_CANCELLED = "تم الإلغاء 🚫" if is_ar else "Cancelled 🚫"

# ==========================================
# 8. الرسائل والتبيهات (Messages)
# ==========================================
MSG_PLACEHOLDER_URL = "ضع الرابط هنا..." if is_ar else "Paste link here..."
MSG_DURATION = "المدة: {}" if is_ar else "Duration: {}"

# تلميحات الرموز
TOOLTIP_START = "بدء التحميل" if is_ar else "Start Download"
TOOLTIP_PAUSE = "إيقاف مؤقت" if is_ar else "Pause"
TOOLTIP_CANCEL = "إلغاء وحذف" if is_ar else "Cancel & Remove"
TOOLTIP_FOLDER = "فتح المجلد" if is_ar else "Open Folder"