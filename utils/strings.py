from utils.settings import app_config

_lang = app_config.get("language", "en")
if _lang == "system":
    _lang = "en" 

is_ar = (_lang == "ar")

# ==========================================
# 1. نصوص التطبيق والتبويبات (App & Tabs)
# ==========================================
APP_TITLE = "AHS-MediaDL" # ⬅️ الاسم بقى ثابت في اللغتين
APP_TAB_ADD = "الرئيسية" if is_ar else "Home"
APP_TAB_QUEUE = "التنزيلات" if is_ar else "Downloads"
APP_BATCH_TITLE = "📦 مجموعة روابط" if is_ar else "📦 Batch Links"
APP_SET_TITLE = "⚙️ الإعدادات" if is_ar else "⚙️ Settings"

# ⬅️ ضفنا تبويبات الإعدادات هنا عشان الترجمة
SET_TAB_GENERAL = "⚙️ عام" if is_ar else "⚙️ General"
# ضيف دي تحت SET_TAB_GENERAL
SET_TAB_APPEARANCE = "🎨 المظهر" if is_ar else "🎨 Appearance"

# ضيف دول تحت نصوص الإعدادات (LBL_SET_...)
LBL_SET_FONT_FAMILY = "نوع الخط:" if is_ar else "Font Family:"
LBL_SET_FONT_SIZE = "حجم الخط:" if is_ar else "Font Size:"
LBL_SET_WIN_WIDTH = "عرض النافذة الافتراضي:" if is_ar else "Default Window Width:"
LBL_SET_WIN_HEIGHT = "طول النافذة الافتراضي:" if is_ar else "Default Window Height:"
SET_TAB_DOWNLOADS = "📥 التحميلات" if is_ar else "📥 Downloads"
SET_TAB_QUALITY = "📝 الجودة والترجمة" if is_ar else "📝 Quality & Subs"
SET_TAB_ADVANCED = "🛠️ إعدادات متقدمة" if is_ar else "🛠️ Advanced"

# ==========================================
# 2. الأزرار (Buttons)
# ==========================================
BTN_SETTINGS = "⚙️ الإعدادات" if is_ar else "⚙️ Settings"
BTN_CHECK_LINK = "🔍 فحص الرابط" if is_ar else "🔍 Check Link"
BTN_BATCH = "📦 مجموعة روابط" if is_ar else "📦 Batch"
BTN_BATCH_PROCESS = "تحميل كقائمة تشغيل" if is_ar else "Load as Playlist"
BTN_DOWNLOAD = "⬇️ تحميل الآن" if is_ar else "⬇️ Download Now"
BTN_DOWNLOAD_SIZE = "⬇️ تحميل الآن ({})" if is_ar else "⬇️ Download Now ({})"
BTN_DOWNLOAD_SUB = "⬇️ تحميل ترجمة فقط" if is_ar else "⬇️ Download Subtitles Only"
BTN_PAUSE_ALL = "⏸️ إيقاف الكل" if is_ar else "⏸️ Pause All"
BTN_RESUME_ALL = "▶️ استئناف الكل" if is_ar else "▶️ Resume All"
BTN_CANCEL_ALL = "🚫 إلغاء الكل" if is_ar else "🚫 Cancel All"
BTN_CLEAR_COMPLETED = "🧹 مسح المكتمل" if is_ar else "🧹 Clear Completed"
BTN_START = "بدء ▶" if is_ar else "Start ▶"
BTN_CANCEL = "إلغاء" if is_ar else "Cancel"
BTN_PAUSE = "⏸️ إيقاف" if is_ar else "⏸️ Pause"
BTN_RESUME = "▶️ استئناف" if is_ar else "▶️ Resume"
BTN_OPEN_FOLDER = "📂 فتح المجلد" if is_ar else "📂 Open Folder"
BTN_FORCE = "فرض التحميل" if is_ar else "Force Download"
BTN_SET_BROWSE = "📁 تصفح..." if is_ar else "📁 Browse..."
BTN_SET_RESTART = "🔄 إعادة تشغيل" if is_ar else "🔄 Restart"
BTN_SET_DONE = "تم" if is_ar else "Done"
BTN_FACTORY_RESET = "⚠️ إعادة ضبط المصنع" if is_ar else "⚠️ Factory Reset"
MSG_RESET_CONFIRM = "هل أنت متأكد من مسح كل الإعدادات والعودة للوضع الافتراضي؟ (سيتم إعادة تشغيل التطبيق فوراً)" if is_ar else "Are you sure you want to reset all settings? (App will restart immediately)"

# ==========================================
# 3. النصوص الوصفية (Labels)
# ==========================================
LBL_FETCHING = "⏳ جاري جلب البيانات... يرجى الانتظار." if is_ar else "⏳ Fetching details... Please wait."
LBL_TYPE = "النوع:" if is_ar else "Type:"
LBL_QUALITY = "الجودة:" if is_ar else "Quality:"
LBL_TOTAL_SPEED = "🚀 السرعة الكلية: " if is_ar else "🚀 Total Speed: "
LBL_BATCH_DESC = "📋 ضع روابطك هنا (رابط واحد في كل سطر):" if is_ar else "📋 Paste your links here (One link per line):"
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
CHK_SUB_AVAILABLE = "📝 ترجمة (متاحة)" if is_ar else "📝 Subtitles (Available)"
CHK_SUBS_BEST_EFFORT = "📝 ترجمة (إن وُجدت)" if is_ar else "📝 Subs (Best Effort)"
CHK_NO_SUBS = "🚫 لا توجد ترجمة" if is_ar else "🚫 No Subtitles"
CHK_EMBED_SUBS = "📌 دمج في الفيديو" if is_ar else "📌 Embed in Video"
CHK_SUBS_ONLY = "📄 تحميل الترجمة فقط" if is_ar else "📄 Download Subs Only"
CHK_SET_NOTIFY = "الإشعارات عند الانتهاء" if is_ar else "Notifications when finished"
CHK_SET_THUMB = "🖼️ عرض الصور المصغرة" if is_ar else "🖼️ Show Thumbnails"
CHK_SET_DATA_SAVER = "توفير البيانات (بدء يدوي)" if is_ar else "Data Saver (Manual Start)"
CHK_SET_ALLOW_DOWNGRADE = "السماح بخفض الجودة تلقائياً" if is_ar else "Allow automatic quality downgrade"

# ==========================================
# 5. خيارات القوائم (ComboBox Options)
# ==========================================
OPT_TYPE_VIDEO = "🎬 فيديو" if is_ar else "🎬 Video"
OPT_TYPE_AUDIO = "🎵 صوت" if is_ar else "🎵 Audio"
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
QUAL_4K = "🎬 جودة فائقة ({}) - 4K" if is_ar else "🎬 Ultra HD ({}) - 4K"
QUAL_2K = "🎬 جودة عالية جداً ({}) - 2K" if is_ar else "🎬 Quad HD ({}) - 2K"
QUAL_1080 = "🎬 دقة كاملة ({}) - 1080p" if is_ar else "🎬 Full HD ({}) - 1080p"
QUAL_720 = "🎬 عالية الدقة ({}) - 720p" if is_ar else "🎬 HD ({}) - 720p"
QUAL_480 = "🎬 جودة عادية ({}) - 480p" if is_ar else "🎬 Standard ({}) - 480p"
QUAL_360 = "🎬 جودة موبايل ({}) - 360p" if is_ar else "🎬 Mobile ({}) - 360p"
QUAL_240 = "🎬 جودة منخفضة ({}) - 240p" if is_ar else "🎬 Low ({}) - 240p"
QUAL_144 = "🎬 توفير بيانات ({}) - 144p" if is_ar else "🎬 Data Saver ({}) - 144p"

AUDIO_M4A = "🎵 صوت M4A سريع (128K)" if is_ar else "🎵 Fast M4A (128K)"
AUDIO_MP3_70 = "🎵 صوت MP3 صغير (70K)" if is_ar else "🎵 Mini MP3 (70K)"
AUDIO_MP3_128 = "🎵 صوت MP3 قياسي (128K)" if is_ar else "🎵 Standard MP3 (128K)"
AUDIO_MP3_160 = "🎵 صوت MP3 بجودة (160K)" if is_ar else "🎵 HQ MP3 (160K)"
AUDIO_MP3_320 = "🎵 صوت MP3 احترافي (320K)" if is_ar else "🎵 Premium MP3 (320K)"

# ==========================================
# 7. حالات الطابور (Queue Status)
# ==========================================
STATUS_WAITING = "في انتظار التحميل..." if is_ar else "Waiting in queue..."
STATUS_PAUSED_DATA = "متوقف (توفير البيانات)" if is_ar else "Paused (Data Saver)"
STATUS_COMPLETED = "اكتمل بنجاح! 🎉" if is_ar else "Completed! 🎉"
STATUS_PAUSED = "متوقف مؤقتاً ⏸️" if is_ar else "Paused ⏸️"
STATUS_CANCELLED = "تم الإلغاء 🚫" if is_ar else "Cancelled 🚫"

# ==========================================
# 8. الرسائل والتبيهات (Messages)
# ==========================================
MSG_PLACEHOLDER_URL = "ضع الرابط هنا..." if is_ar else "Paste link here..."
MSG_SAVED = "📌 تم الحفظ! (أعد وضع الرابط)" if is_ar else "📌 Saved! (Repaste link)"
MSG_DURATION = "المدة: {}" if is_ar else "Duration: {}"
MSG_LANG_SELECTED = "✅ تم اختيار {}!" if is_ar else "✅ {} Selected!"
MSG_BATCH_COLLECTION_TITLE = "مجموعة مخصصة ({} روابط)" if is_ar else "Batch Collection ({} Links)"

# في ملف strings.py
APP_TAB_HISTORY = "السجل" if is_ar else "History"
BTN_CLEAR_HISTORY = "🗑️ مسح السجل بالكامل" if is_ar else "🗑️ Clear All History"
LBL_HISTORY_EMPTY = "لا يوجد سجل للتحميلات حتى الآن." if is_ar else "No download history yet."
MSG_HISTORY_CLEARED = "تم مسح السجل بنجاح!" if is_ar else "History cleared successfully!"
# أعمدة الجدول
COL_THUMB = "الصورة" if is_ar else "Thumb"
COL_TITLE = "العنوان" if is_ar else "Title"
COL_DATE = "التاريخ" if is_ar else "Date"
COL_ACTION = "إجراء" if is_ar else "Action"

# ضيف دول في strings.py
BTN_METADATA = "✏️ تعديل البيانات" if is_ar else "✏️ Edit Metadata"
LBL_META_TITLE = "عنوان الأغنية (Title):" if is_ar else "Song Title:"
LBL_META_ARTIST = "اسم الفنان (Artist):" if is_ar else "Artist:"
LBL_META_ALBUM = "اسم الألبوم (Album):" if is_ar else "Album:"
BTN_SAVE_DOWNLOAD = "💾 حفظ وبدء التحميل" if is_ar else "💾 Save & Download"

# تلميحات الرموز
TOOLTIP_START = "بدء التحميل" if is_ar else "Start Download"
TOOLTIP_PAUSE = "إيقاف مؤقت" if is_ar else "Pause"
TOOLTIP_STOP = "إيقاف واستئناف لاحقاً" if is_ar else "Stop & Resume Later"
TOOLTIP_CANCEL = "إلغاء وحذف" if is_ar else "Cancel & Remove"
TOOLTIP_FOLDER = "فتح المجلد" if is_ar else "Open Folder"