# AHS-MediaDL

<p align="center">
  <img src="assets/icon.ico" width="128" height="128" alt="AHS-MediaDL Logo">
</p>

<p align="center">
  <strong>تطبيق سطح مكتب حديث لتحميل وإدارة الفيديوهات والصوتيات باستخدام Python وPyQt6 وyt-dlp وFFmpeg.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PyQt6-green?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6">
  <img src="https://img.shields.io/badge/yt--dlp-red?style=for-the-badge" alt="yt-dlp">
  <img src="https://img.shields.io/badge/Windows%20%7C%20Linux%20%7C%20macOS-orange?style=for-the-badge" alt="Platforms">
  <img src="https://img.shields.io/badge/License-MIT-blueviolet?style=for-the-badge" alt="MIT License">
</p>

---

## 📖 نبذة

**AHS-MediaDL** هو تطبيق سطح مكتب لتحميل وإدارة الفيديوهات والصوتيات، تم تطويره باستخدام **Python وPyQt6**، مع الاعتماد على **yt-dlp** كمحرك لتحميل واستخراج الوسائط و**FFmpeg** لمعالجة وتحويل الملفات.

تم تطوير المشروع ليجمع بين سهولة استخدام تطبيقات سطح المكتب والميزات المتقدمة لأدوات تحميل الوسائط، مع التركيز على تنظيم الكود، تجربة المستخدم، الأداء، وقابلية التوسع.

> **حالة المشروع:** هذه النسخة تمثل الإصدار المكتمل من نسخة Python/PyQt6 من AHS-MediaDL.

---

## ✨ المميزات

### 📥 تحميل الوسائط
- تحميل الفيديوهات والصوتيات بجودات متعددة تصل إلى 4K و8K حسب المصدر.
- استخراج الصوت بصيغ مثل MP3 وM4A.
- دمج مسارات الفيديو والصوت تلقائيًا باستخدام FFmpeg.
- دعم صيغ فيديو متعددة.
- تحميل الترجمات المتوفرة.

### 🔍 البحث والفحص
- البحث عن الفيديوهات مباشرة من داخل التطبيق.
- عرض نتائج البحث مع الصور المصغرة والعناوين والقنوات والمدد.
- فحص الروابط واستخراج الجودات والصيغ والترجمات المتاحة.
- إمكانية بدء التحميل مباشرة من نتائج البحث.
- خيار تعطيل الصور المصغرة لتقليل استهلاك البيانات.

### 📊 إدارة التحميلات
- دعم تحميلات متزامنة متعددة.
- قائمة انتظار لإدارة المهام.
- إيقاف واستئناف التحميلات.
- إلغاء وإعادة محاولة المهام الفاشلة.
- عرض السرعة والحجم ونسبة التقدم والوقت المتبقي.
- تحديد سرعة التحميل.
- التعامل تلقائيًا مع الملفات المتكررة.

### 📋 القوائم والتحميلات الجماعية
- فحص قوائم التشغيل واختيار العناصر المطلوبة.
- تحديد أو إلغاء تحديد جميع العناصر.
- تحميل عدة روابط دفعة واحدة.
- التحكم في عدد العناصر المعالجة من روابط Mix والقوائم.

### 💬 الترجمات
- دعم الترجمات اليدوية والتلقائية.
- دعم الترجمات التلقائية المترجمة.
- دعم `.vtt` و`.srt`.
- تحميل الترجمات كجزء من الوسائط أو كملفات منفصلة.

### 📜 سجل التحميلات
- البحث والتصفية.
- فتح الملفات أو المجلدات.
- إعادة تحميل العناصر السابقة.
- حذف عناصر محددة أو مسح السجل بالكامل.

### 🎨 التخصيص
- الوضع الداكن والفاتح والتلقائي.
- ألوان واجهة متعددة.
- تغيير الخط وحجمه.
- تغيير مقياس الواجهة من 100% إلى 200%.
- حركات وانتقالات سلسة.

### 🖥️ التكامل مع النظام
- العمل من خلال **System Tray**.
- التشغيل في الخلفية.
- مراقبة الحافظة واكتشاف روابط الوسائط.
- اكتشاف وإدارة FFmpeg وyt-dlp تلقائيًا.
- منع تشغيل أكثر من نسخة باستخدام IPC.
- إمكانية التشغيل مع بدء Windows.

### 🌐 تعدد اللغات
- العربية والإنجليزية.
- دعم RTL وLTR.
- تغيير اللغة من داخل الإعدادات.
- إعادة تشغيل آمنة لتطبيق تغييرات اللغة.

### 🔐 Cookies
- دعم استخدام Cookies للوصول إلى المحتوى الذي يتطلب تسجيل الدخول.
- استيراد Cookies من المتصفحات المدعومة.
- دعم ملفات `cookies.txt`.
- اختيار مصدر Cookies من إعدادات التطبيق.

---

## 🖼️ صور من التطبيق

| البحث والنتائج | قائمة التحميلات |
|:---:|:---:|
| ![Search](docs/screenshots/search_page.png) | ![Downloads](docs/screenshots/downloads_page.png) |

| الإعداد الأولي | الإعدادات |
|:---:|:---:|
| ![Onboarding](docs/screenshots/onboarding.png) | ![Settings](docs/screenshots/settings.png) |

| سجل التحميلات | الإشعارات |
|:---:|:---:|
| ![History](docs/screenshots/history.png) | ![Notifications](docs/screenshots/notifications.png) |

---

## 🔄 كيف يعمل؟

```text
Input URL / Search
       ↓
InfoFetcherThread
       ↓
Quality & Format Selection
       ↓
DownloadManager
       ↓
DownloadWorker
       ↓
FFmpeg Processing
       ↓
History & Notification
```

يتم فحص الرابط أو البحث عن المحتوى، ثم استخراج المعلومات والجودات المتاحة، وإضافة المهمة إلى قائمة التحميلات. يتولى `DownloadWorker` عملية التحميل ومتابعة التقدم، بينما يتولى `FFmpeg` الدمج والتحويل عند الحاجة.

---

## 📦 الصيغ والجودات

تعتمد الخيارات المتاحة فعليًا على المصدر وإمكانيات `yt-dlp`.

| الفئة | الدعم |
|---|---|
| جودة الفيديو | حتى 8K، 4K، 2K، 1080p، 720p، 480p، 360p وغيرها |
| الفيديو | MP4، MKV، WebM، MOV |
| الصوت | MP3، M4A، أفضل جودة أصلية |
| الترجمات | يدوية، تلقائية، تلقائية مترجمة |
| ملفات الترجمة | `.vtt`، `.srt` |

---

## 🌐 المنصات المدعومة

يعتمد دعم المنصات على **yt-dlp**، لذلك يستطيع التطبيق التعامل مع المواقع التي يدعمها إصدار yt-dlp المستخدم.

ومن أمثلتها:

- YouTube
- Vimeo
- Dailymotion
- Twitch
- Facebook
- Instagram
- TikTok
- Twitter/X
- Threads
- SoundCloud
- Bandcamp

> قد يتغير دعم المنصات بمرور الوقت وفقًا لتحديثات yt-dlp والقيود الخاصة بكل منصة.

---

## 📥 التثبيت والتشغيل

### النسخة الجاهزة — Windows

يمكن تحميل النسخة الجاهزة من:

**[GitHub Releases](https://github.com/AHS-Official/AHS-MediaDL/releases)**

### التشغيل من المصدر

#### المتطلبات

- Python 3.10+
- FFmpeg

#### Windows

```powershell
git clone https://github.com/AHS-Official/AHS-MediaDL.git
cd AHS-MediaDL

python -m venv .venv
.venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

python main.py
```

#### Linux / macOS

```bash
git clone https://github.com/AHS-Official/AHS-MediaDL.git
cd AHS-MediaDL

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python main.py
```

يمكن للتطبيق اكتشاف FFmpeg من **System PATH** أو من مجلد `bin` وفق إعدادات المشروع.

---

## 🏗️ بنية المشروع

يعتمد المشروع على بنية Modular Architecture لفصل مسؤوليات التطبيق:

```text
AHS-MediaDL/
├── core/        # التحميل ومعالجة الوسائط
├── services/    # الخدمات ومنطق yt-dlp
├── managers/    # إدارة الحالة والتحميلات والإعدادات
├── gui/         # واجهة PyQt6
├── utils/       # الأدوات المشتركة والترجمة والثيمات
├── data/        # البيانات المحلية
├── assets/      # الأيقونات والموارد
├── docs/        # الصور والوثائق
├── main.py      # نقطة تشغيل التطبيق
└── requirements.txt
```

### أهم المكونات

- **Core** — `yt-dlp`, `FFmpeg`, Workers
- **Services** — تنسيق عمليات الاستخراج والتحميل
- **Managers** — التحميلات، السجل، الإعدادات، الأدوات، الإشعارات، النظام
- **GUI** — صفحات ومكونات ونوافذ PyQt6
- **Utils** — الترجمة، الثيمات، المسارات، التسجيل والأدوات المساعدة

---

## 🛠️ التقنيات

- **Python** — لغة البرمجة
- **PyQt6** — واجهة المستخدم
- **yt-dlp** — استخراج وتحميل الوسائط
- **FFmpeg** — معالجة ودمج وتحويل الوسائط
- **SQLite3** — قاعدة بيانات سجل التحميلات
- **Nuitka** — بناء النسخة المستقلة
- **QLocalServer / QLocalSocket** — IPC ومنع تشغيل أكثر من نسخة

---

## 📜 الترخيص

يتم توزيع المشروع بموجب **MIT License**.

راجع ملف `LICENSE` لمزيد من التفاصيل.

---

## 🙏 شكر وتقدير

يعتمد المشروع على عدد من المشاريع مفتوحة المصدر الرائعة:

- **yt-dlp** — محرك استخراج وتحميل الوسائط.
- **FFmpeg** — معالجة وتحويل الوسائط.
- **PyQt6** — إطار عمل تطبيق سطح المكتب.

---

## 💡 عن المشروع

بدأ **AHS-MediaDL** كمشروع بسيط للتعلم العملي، ثم تطور تدريجيًا إلى تطبيق سطح مكتب متكامل من حيث التصميم والوظائف والبنية الداخلية.

كان المشروع تجربة عملية في:

**Python · PyQt6 · GUI Development · Multithreading · Background Processes · State Management · SQLite · FFmpeg · yt-dlp · Desktop Application Architecture**

تم استخدام أدوات الذكاء الاصطناعي كمساعد أثناء التطوير وكتابة وتنقيح أجزاء من الكود وحل المشكلات، بينما تم تحديد فكرة المشروع ومتطلباته وميزاته وتصميمه وتوجيه عملية التطوير واختبار النتائج بشكل تدريجي.

---

<p align="center">
  تم تطوير AHS-MediaDL باستخدام Python وPyQt6، مع الكثير من التعلم والتجربة.
</p>