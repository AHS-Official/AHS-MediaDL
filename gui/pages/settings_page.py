import os
import json
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QLabel, QComboBox, QCheckBox, QSpinBox, QFontDialog, QMessageBox, QDoubleSpinBox
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFontDatabase, QIcon  # 💡 أضف هذا السطر لقراءة خطوط النظام ديناميكياً
from utils.locales import tr  # 💡 استيراد محرك الترجمة
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color

class SettingsPage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # --- 1️⃣ الشريط العلوي (زر الرجوع + العنوان + التوست + زر الريستارت) ---
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setIcon(get_colored_icon("assets/icons/arrow-left.svg", get_current_theme_color()))
        self.btn_back.setIconSize(QSize(20, 20))
        self.btn_back.setFixedSize(35, 35)
        self.btn_back.clicked.connect(lambda: self.main_app.change_page(0))
        top_bar.addWidget(self.btn_back)
        
        title_lbl = QLabel(tr("settings_title"))
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_bar.addWidget(title_lbl)
        
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet("color: #e3a32e; font-weight: bold; margin-left: 15px;")
        top_bar.addWidget(self.toast_label)
        
        top_bar.addStretch()
        
        self.btn_restart = QPushButton(tr("btn_restart", "Restart Now"))
        self.btn_restart.setIcon(get_colored_icon("assets/icons/restart.svg", get_current_theme_color()))
        self.btn_restart.setIconSize(QSize(16, 16))
        self.btn_restart.setFixedWidth(140)
        self.btn_restart.setStyleSheet("background-color: #e3a32e; color: #1e1f22; font-weight: bold;")
        self.btn_restart.hide()
        self.btn_restart.clicked.connect(self.restart_application)
        top_bar.addWidget(self.btn_restart)
        
        main_layout.addLayout(top_bar)
        
        # --- 2️⃣ منطقة الـ Split View الرئيسية ---
        split_layout = QHBoxLayout()
        split_layout.setSpacing(15)
        
        # الجزء الأيسر: قائمة الأقسام
        self.categories_list = QListWidget()
        self.categories_list.setFixedWidth(160)
        self.categories_list.setStyleSheet("""
            QListWidget { border-right: 1px solid rgba(128, 128, 128, 0.2); background: transparent; }
            QListWidget::item { padding: 8px 12px; border-radius: 5px; font-size: 13px; }
        """)
        
        self.item_general = QListWidgetItem(get_colored_icon("assets/icons/package.svg", get_current_theme_color()), tr("set_general"))
        self.item_appearance = QListWidgetItem(get_colored_icon("assets/icons/palette.svg", get_current_theme_color()), tr("set_appearance"))
        self.item_downloads = QListWidgetItem(get_colored_icon("assets/icons/save.svg", get_current_theme_color()), tr("set_downloads"))
        self.item_subtitles = QListWidgetItem(get_colored_icon("assets/icons/clapperboard.svg", get_current_theme_color()), tr("set_subtitles"))
        self.item_output = QListWidgetItem(get_colored_icon("assets/icons/video.svg", get_current_theme_color()), tr("set_output_format"))
        
        self.categories_list.addItem(self.item_general)
        self.categories_list.addItem(self.item_appearance)
        self.categories_list.addItem(self.item_downloads)
        self.categories_list.addItem(self.item_subtitles)
        self.categories_list.addItem(self.item_output)
        self.categories_list.setIconSize(QSize(18, 18))
        
        self.categories_list.currentRowChanged.connect(self.change_section)
        split_layout.addWidget(self.categories_list)
        
        # الجزء الأيمن: الـ StackedWidget لحمل حاويات الأقسام
        self.sections_stack = QStackedWidget()
        split_layout.addWidget(self.sections_stack, 1)
        
        # إنشاء حاويات الأقسام الخمسة
        self.section_general = QWidget()
        self.section_appearance = QWidget()
        self.section_downloads = QWidget()
        self.section_subtitles = QWidget()
        self.section_output = QWidget()
        
        # ─────────────────────────────────────────────
        # 🛠️ تصميم قسم General (العام)
        # ─────────────────────────────────────────────
        general_layout = QVBoxLayout(self.section_general)
        general_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        general_layout.setSpacing(15)
        
        lang_layout = QHBoxLayout()
        self.lang_label = QLabel(tr("lang_label", "Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(180)
        self.lang_combo.addItem(tr("lang_system", "System (Default)"), "system")
        self.lang_combo.addItem(tr("lang_en", "English"), "en")
        self.lang_combo.addItem(tr("lang_ar", "العربية"), "ar")
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        general_layout.addLayout(lang_layout)
        
        self.noti_cb = QCheckBox(tr("enable_notifications", "Enable Notifications"))
        self.noti_cb.setChecked(True)
        general_layout.addWidget(self.noti_cb)
        
        # ─────────────────────────────────────────────
        # 🛠️ تصميم قسم Appearance (المظهر المرن الموحد)
        # ─────────────────────────────────────────────
        appearance_layout = QVBoxLayout(self.section_appearance)
        appearance_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        appearance_layout.setSpacing(15)
        
        # 1. المود
        theme_layout = QHBoxLayout()
        self.theme_label = QLabel(tr("theme_label", "Theme Mode:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(180)
        self.theme_combo.addItem(tr("theme_system", "System"), "auto")
        self.theme_combo.addItem(tr("theme_light", "Light"), "light")
        self.theme_combo.addItem(tr("theme_dark", "Dark"), "dark")
        theme_layout.addWidget(self.theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        appearance_layout.addLayout(theme_layout)
        
        # 2. نوع الخط الديناميكي
        font_layout = QHBoxLayout()
        self.font_label = QLabel(tr("font_label", "App Font:"))
        self.font_combo = QComboBox()
        self.font_combo.setFixedWidth(180)
        self.font_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.font_combo.setMinimumContentsLength(10)
        self.font_combo.addItem("System Default", "System Default")
        
        system_fonts = sorted(QFontDatabase.families())
        for f_name in system_fonts:
            if not f_name.startswith("@"):
                self.font_combo.addItem(f_name, f_name)
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        appearance_layout.addLayout(font_layout)
        
        # 3. الـ Scaling
        scale_layout = QHBoxLayout()
        self.scale_label = QLabel(tr("scale_label", "Scaling:"))
        self.scale_combo = QComboBox()
        self.scale_combo.setFixedWidth(180)
        self.scale_combo.addItem(tr("scale_auto", "Auto"), "auto")
        self.scale_combo.addItem("100%", "1.0")
        self.scale_combo.addItem("125%", "1.25")
        self.scale_combo.addItem("150%", "1.5")
        self.scale_combo.addItem("175%", "1.75")
        self.scale_combo.addItem("200%", "2.0")
        scale_layout.addWidget(self.scale_label)
        scale_layout.addWidget(self.scale_combo)
        scale_layout.addStretch()
        appearance_layout.addLayout(scale_layout)
        
        # 4. حجم الخط
        size_layout = QHBoxLayout()
        self.size_label = QLabel(tr("size_label", "Font Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setFixedWidth(180)
        self.size_spin.setRange(8, 30)
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        appearance_layout.addLayout(size_layout)
        
        # ─────────────────────────────────────────────
        # 🛠️ تصميم قسم Downloads (التنزيلات)
        # ─────────────────────────────────────────────
        downloads_layout = QVBoxLayout(self.section_downloads)
        downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        downloads_layout.setSpacing(18)
        
        # 1. مسار الحفظ
        path_layout = QHBoxLayout()
        self.path_label = QLabel(tr("path_label", "Save Path:"))
        self.path_combo = QComboBox()
        self.path_combo.addItem(tr("path_downloads", "Save in Downloads"), "downloads")
        self.path_combo.addItem(tr("path_always_ask", "Always Ask"), "always_ask")
        self.path_combo.addItem(tr("path_custom", "Custom"), "custom")
        self.btn_browse_path = QPushButton(tr("btn_browse", "Browse"))
        self.btn_browse_path.setFixedWidth(150)
        self.btn_browse_path.hide()
        self.btn_browse_path.clicked.connect(self.choose_folder_dialog_action)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_combo)
        path_layout.addWidget(self.btn_browse_path)
        path_layout.addStretch()
        downloads_layout.addLayout(path_layout)
        
        # 2. حد السرعة
        speed_layout = QHBoxLayout()
        self.speed_label = QLabel(tr("speed_label", "Download Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItem(tr("speed_unlimited", "Unlimited"), "unlimited")
        self.speed_combo.addItem("2 MB/s", "2M")
        self.speed_combo.addItem("1 MB/s", "1M")
        self.speed_combo.addItem("500 KB/s", "500K")
        self.speed_combo.addItem(tr("speed_custom", "Custom"), "custom")
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(1, 99999)
        self.speed_spin.setValue(100)
        self.speed_spin.setFixedWidth(100)
        self.speed_spin.hide()
        self.btn_speed_unit = QPushButton("KB")
        self.btn_speed_unit.setObjectName("btn_speed_unit")
        self.btn_speed_unit.setFixedWidth(50)
        self.btn_speed_unit.hide()
        self.btn_speed_unit.clicked.connect(self.toggle_speed_unit_action)
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_combo)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addWidget(self.btn_speed_unit)
        speed_layout.addStretch()
        downloads_layout.addLayout(speed_layout)
        
        # 3. التحميلات المتزامنة
        concurrent_layout = QHBoxLayout()
        self.concurrent_label = QLabel(tr("concurrent_label", "Concurrent Downloads:"))
        self.concurrent_combo = QComboBox()
        self.concurrent_combo.addItem("1", "1")
        self.concurrent_combo.addItem("3", "3")
        self.concurrent_combo.addItem("5", "5")
        self.concurrent_combo.addItem(tr("concurrent_custom", "Custom"), "custom")
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 20)
        self.concurrent_spin.setValue(3)
        self.concurrent_spin.setFixedWidth(70)
        self.concurrent_spin.hide()
        concurrent_layout.addWidget(self.concurrent_label)
        concurrent_layout.addWidget(self.concurrent_combo)
        concurrent_layout.addWidget(self.concurrent_spin)
        concurrent_layout.addStretch()
        downloads_layout.addLayout(concurrent_layout)
        
        # ─────────────────────────────────────────────
        # 🛠️ تصميم قسم Subtitles (الترجمة)
        # ─────────────────────────────────────────────
        subtitles_layout = QVBoxLayout(self.section_subtitles)
        subtitles_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        subtitles_layout.setSpacing(18)
        
        # 1. لغة الترجمة الأساسية
        sub_primary_layout = QHBoxLayout()
        self.sub_primary_label = QLabel(tr("sub_primary_label", "Primary Subtitle Language:"))
        self.sub_primary_combo = QComboBox()
        self.sub_primary_combo.setFixedWidth(180)
        sub_primary_layout.addWidget(self.sub_primary_label)
        sub_primary_layout.addWidget(self.sub_primary_combo)
        sub_primary_layout.addStretch()
        subtitles_layout.addLayout(sub_primary_layout)
        
        # 2. لغة الترجمة الثانوية
        sub_secondary_layout = QHBoxLayout()
        self.sub_secondary_label = QLabel(tr("sub_secondary_label", "Secondary Subtitle Language:"))
        self.sub_secondary_combo = QComboBox()
        self.sub_secondary_combo.setFixedWidth(180)
        sub_secondary_layout.addWidget(self.sub_secondary_label)
        sub_secondary_layout.addWidget(self.sub_secondary_combo)
        sub_secondary_layout.addStretch()
        subtitles_layout.addLayout(sub_secondary_layout)
        
        # 3. التحميل الاحتياطي لأي ترجمة تلقائية أصلية
        fallback_layout = QHBoxLayout()
        self.fallback_cb = QCheckBox(tr("sub_fallback_label", "Download any original auto subtitle as fallback"))
        self.fallback_info_icon = QLabel()
        self.fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.fallback_info_icon.setToolTip(tr("sub_fallback_info_tooltip", "In playlist mode, allows downloading any language as long as it is original (org) if preferred languages are not available"))
        fallback_layout.addWidget(self.fallback_cb)
        fallback_layout.addWidget(self.fallback_info_icon)
        fallback_layout.addStretch()
        subtitles_layout.addLayout(fallback_layout)

        # ─────────────────────────────────────────────
        # 🛠️ تصميم قسم Output Format (صيغة الملف الخارج)
        # ─────────────────────────────────────────────
        output_layout = QVBoxLayout(self.section_output)
        output_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        output_layout.setSpacing(15)
        
        # 1. حاوية الفيديو الخارج
        video_container_layout = QHBoxLayout()
        self.video_container_lbl = QLabel(tr("video_container_label", "Video Container Format:"))
        self.video_container_combo = QComboBox()
        self.video_container_combo.setFixedWidth(180)
        self.video_container_combo.addItem("MP4", "mp4")
        self.video_container_combo.addItem("MKV", "mkv")
        self.video_container_combo.addItem("MOV", "mov")
        self.video_container_combo.addItem("WebM", "webm")
        video_container_layout.addWidget(self.video_container_lbl)
        video_container_layout.addWidget(self.video_container_combo)
        video_container_layout.addStretch()
        output_layout.addLayout(video_container_layout)
        
        # 2. دمج الترجمة والتشغيل التلقائي وحاوية الترجمة الخارجية
        self.embed_subtitles_cb = QCheckBox(tr("embed_subtitles_label", "Embed subtitles inside video container"))
        output_layout.addWidget(self.embed_subtitles_cb)
        
        self.autoplay_subtitles_cb = QCheckBox(tr("autoplay_subtitles_label", "Enable auto-play for embedded subtitles"))
        self.autoplay_subtitles_cb.setStyleSheet("margin-left: 20px;")
        self.autoplay_subtitles_cb.hide()
        output_layout.addWidget(self.autoplay_subtitles_cb)
        
        # صيغة الترجمة الخارجية للفيديو
        external_sub_layout = QHBoxLayout()
        self.external_sub_lbl = QLabel(tr("external_sub_format_label", "External Subtitle Format:"))
        self.external_sub_combo = QComboBox()
        self.external_sub_combo.setFixedWidth(180)
        self.external_sub_combo.addItem("SRT", "srt")
        self.external_sub_combo.addItem("ASS", "ass")
        self.external_sub_combo.addItem("VTT", "vtt")
        external_sub_layout.addWidget(self.external_sub_lbl)
        external_sub_layout.addWidget(self.external_sub_combo)
        external_sub_layout.addStretch()
        
        self.external_sub_widget = QWidget()
        external_sub_widget_layout = QHBoxLayout(self.external_sub_widget)
        external_sub_widget_layout.setContentsMargins(0, 0, 0, 0)
        external_sub_widget_layout.addLayout(external_sub_layout)
        output_layout.addWidget(self.external_sub_widget)
        
        # خط فاصل رفيع وجميل
        from PyQt6.QtWidgets import QFrame
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        separator_line.setStyleSheet("background-color: rgba(128, 128, 128, 0.1); margin-top: 10px; margin-bottom: 10px;")
        output_layout.addWidget(separator_line)
        
        # 3. صيغة الترجمة/الكلمات للصوت
        audio_sub_layout = QHBoxLayout()
        self.audio_sub_lbl = QLabel(tr("audio_sub_format_label", "Audio Subtitle/Lyrics Format:"))
        self.audio_sub_combo = QComboBox()
        self.audio_sub_combo.setFixedWidth(180)
        self.audio_sub_combo.addItem("LRC (Lyrics)", "lrc")
        self.audio_sub_combo.addItem("SRT", "srt")
        self.audio_sub_combo.addItem("VTT", "vtt")
        self.audio_sub_combo.addItem("ASS", "ass")
        audio_sub_layout.addWidget(self.audio_sub_lbl)
        audio_sub_layout.addWidget(self.audio_sub_combo)
        audio_sub_layout.addStretch()
        
        self.audio_sub_widget = QWidget()
        audio_sub_widget_layout = QHBoxLayout(self.audio_sub_widget)
        audio_sub_widget_layout.setContentsMargins(0, 0, 0, 0)
        audio_sub_widget_layout.addLayout(audio_sub_layout)
        output_layout.addWidget(self.audio_sub_widget)
        
        # دمج الترجمة بالصوت
        self.embed_audio_sub_cb = QCheckBox(tr("embed_audio_sub_label", "Embed subtitles inside audio file"))
        output_layout.addWidget(self.embed_audio_sub_cb)
        
        # حاوية ملف الصوت للدمج
        audio_container_layout = QHBoxLayout()
        self.audio_container_lbl = QLabel(tr("audio_container_label", "Audio Container Format:"))
        self.audio_container_combo = QComboBox()
        self.audio_container_combo.setFixedWidth(180)
        self.audio_container_combo.addItem("M4A (Default)", "m4a")
        self.audio_container_combo.addItem("MP4", "mp4")
        self.audio_container_combo.addItem("MKV", "mkv")
        audio_container_layout.addWidget(self.audio_container_lbl)
        audio_container_layout.addWidget(self.audio_container_combo)
        audio_container_layout.addStretch()
        
        self.audio_container_widget = QWidget()
        audio_container_widget_layout = QHBoxLayout(self.audio_container_widget)
        audio_container_widget_layout.setContentsMargins(20, 0, 0, 0)
        audio_container_widget_layout.addLayout(audio_container_layout)
        self.audio_container_widget.hide()
        output_layout.addWidget(self.audio_container_widget)

        # --- 3️⃣ إضافة الحاويات المكتملة إلى الـ Stack الداخلي ---
        self.sections_stack.addWidget(self.section_general)
        self.sections_stack.addWidget(self.section_appearance)
        self.sections_stack.addWidget(self.section_downloads)
        self.sections_stack.addWidget(self.section_subtitles)
        self.sections_stack.addWidget(self.section_output)
        
        # --- 4️⃣ ربط أحداث الإخفاء والظهور اللحظي للقوائم المنسدلة ---
        self.path_combo.currentIndexChanged.connect(self.toggle_path_widgets_visibility)
        self.speed_combo.currentIndexChanged.connect(self.toggle_speed_widgets_visibility)
        self.concurrent_combo.currentIndexChanged.connect(self.toggle_concurrent_widgets_visibility)
        self.speed_spin.valueChanged.connect(self.smart_speed_conversion_check)
        
        # --- 5️⃣ ربط أحداث التغيير بالحفظ التلقائي الفوري (تم وضعه هنا بعد التأكد من خلق كل العناصر) ---
        self.lang_combo.currentIndexChanged.connect(self.save_general_settings)
        self.noti_cb.toggled.connect(self.save_general_settings)
        
        self.theme_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.font_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.scale_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.size_spin.valueChanged.connect(self.save_appearance_settings)
        
        self.path_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.speed_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.speed_spin.valueChanged.connect(self.save_downloads_settings)
        self.concurrent_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.concurrent_spin.valueChanged.connect(self.save_downloads_settings)

        self.sub_primary_combo.currentIndexChanged.connect(self.save_subtitles_settings)
        self.sub_secondary_combo.currentIndexChanged.connect(self.save_subtitles_settings)
        self.fallback_cb.toggled.connect(self.save_subtitles_settings)

        self.embed_subtitles_cb.toggled.connect(self.toggle_video_sub_widgets)
        self.embed_audio_sub_cb.toggled.connect(self.toggle_audio_sub_widgets)
        
        self.video_container_combo.currentIndexChanged.connect(self.save_output_settings)
        self.embed_subtitles_cb.toggled.connect(self.save_output_settings)
        self.autoplay_subtitles_cb.toggled.connect(self.save_output_settings)
        self.external_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.audio_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.embed_audio_sub_cb.toggled.connect(self.save_output_settings)
        self.audio_container_combo.currentIndexChanged.connect(self.save_output_settings)
        
        # --- 6️⃣ استدعاء دوال قراءة الإعدادات المحفوظة عند فتح الشاشة ---
        self.load_general_settings()
        self.load_appearance_settings()
        self.load_downloads_settings()
        self.load_subtitles_settings()
        self.load_output_settings()
        
        # إظهار وتثبيت محاذاة الشاشة
        main_layout.addLayout(split_layout)
        self.categories_list.setCurrentRow(0)
        
    def change_section(self, index):
        """ التنقل بين الأقسام الداخلية للإعدادات """
        self.sections_stack.setCurrentIndex(index)

    def load_general_settings(self):
        """ قراءة الإعدادات المحفوظة من الـ JSON وتطبيقها على الواجهة """
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # قراءة وضبط اللغة
                    lang = data.get("language", "system")
                    self.initial_lang = lang # حفظ اللغة الابتدائية للجلسة
                    idx = self.lang_combo.findData(lang)
                    if idx != -1:
                        self.lang_combo.setCurrentIndex(idx)
                        
                    # قراءة وضبط حالة الإشعارات
                    self.noti_cb.setChecked(data.get("notifications", True))
            except Exception:
                pass

    def save_general_settings(self):
        """ حفظ قيم اللغة والإشعارات فوراً داخل ملف settings.json دون مسح البيانات القديمة """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
                
        # تحديث المفاتيح الخاصة بالقسم الحالي
        data["language"] = self.lang_combo.currentData()
        data["notifications"] = self.noti_cb.isChecked()
        
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # فحص هل اللغة الحالية تختلف عن لغة الإقلاع لإظهار الزرار والتوست
            self.check_restart_required()
        except Exception:
            pass

    def choose_font_dialog(self):
        """ فتح صندوق اختيار الخطوط الخاص بالويندوز """
        current_font = self.font()
        ok, font = QFontDialog.getFont(current_font, self, tr("btn_select_font"))
        if ok:
            self.selected_font_family = font.family()
            self.btn_select_font.setText(self.selected_font_family)
            self.save_appearance_settings() # حفظ فورى عند الاختيار

    def load_appearance_settings(self):
        """ قراءة الثيم، الخط، السكيل، والحجم من الـ JSON وتطبيقهم على الواجهة """
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 1. المود
                    theme = data.get("theme", "auto")
                    idx_theme = self.theme_combo.findData(theme)
                    if idx_theme != -1: self.theme_combo.setCurrentIndex(idx_theme)
                        
                    # 2. نوع الخط
                    font_family = data.get("font_family", "System Default")
                    idx_font = self.font_combo.findData(font_family)
                    if idx_font != -1: self.font_combo.setCurrentIndex(idx_font)
                    
                    # 3. الـ Scaling
                    scale = data.get("scaling", "auto")
                    self.initial_scale = scale # حفظ الـ Scaling الابتدائي للجلسة
                    idx_scale = self.scale_combo.findData(scale)
                    if idx_scale != -1: self.scale_combo.setCurrentIndex(idx_scale)
                        
                    # 4. حجم الخط
                    font_size = data.get("font_size", 12)
                    self.size_spin.setValue(font_size)
            except Exception:
                pass

    def save_appearance_settings(self):
        """ حفظ الإعدادات الأربعة فوراً داخل ملف settings.json وتطبيقها بلحظتها """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["theme"] = self.theme_combo.currentData()
        data["font_family"] = self.font_combo.currentData()
        data["scaling"] = self.scale_combo.currentData()
        data["font_size"] = self.size_spin.value()
        
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # فحص هل الـ Scaling الحالي يختلف عن سكيل الإقلاع لإظهار الزرار والتوست
            self.check_restart_required()
            # استدعاء دالة التطبيق الشاملة والمحدثة في الملف الرئيسي
            self.main_app.apply_appearance(data["theme"], data["font_family"], data["font_size"])
        except Exception:
            pass

    def toggle_path_widgets_visibility(self):
        """ إظهار زر التصفح فقط لو تم اختيار مخصص """
        is_custom = self.path_combo.currentData() == "custom"
        self.btn_browse_path.setVisible(is_custom)

    def toggle_speed_widgets_visibility(self):
        """ إظهار الـ SpinBox وزر الوحدة فقط لو تم اختيار مخصص للسرعة """
        is_custom = self.speed_combo.currentData() == "custom"
        self.speed_spin.setVisible(is_custom)
        self.btn_speed_unit.setVisible(is_custom)

    def toggle_concurrent_widgets_visibility(self):
        """ إظهار الـ SpinBox المخصص للتحميلات المتزامنة """
        is_custom = self.concurrent_combo.currentData() == "custom"
        self.concurrent_spin.setVisible(is_custom)

    def choose_folder_dialog_action(self):
        """ دالة فتح الفايل دايلاوج وتحديث اسم الزرار (مبدئية للجزء الأول) """
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, tr("path_custom", "Select Folder"), self.main_app.last_save_dir)
        if folder:
            # تقصير شكل المسار ليظهر شيك جوه الزرار نفسه (الحركة الديناميكية اللى سألت عليها)
            folder_name = os.path.basename(folder) if os.path.basename(folder) else folder
            self.btn_browse_path.setText(f"📁 {folder_name}")
            self.custom_selected_path = folder # حفظ المسار مؤقتاً
            self.save_downloads_settings() # حفظ فورى للمسار المختار

    def toggle_speed_unit_action(self):
        """ التبديل اللحظي لعنوان زرار الوحدة بين KB و MB عند الضغط عليه """
        current_unit = self.btn_speed_unit.text()
        self.btn_speed_unit.setText("MB" if current_unit == "KB" else "KB")
        self.smart_speed_conversion_check(self.speed_spin.value())

    def smart_speed_conversion_check(self, value):
        """ 🧠 ذكاء الـ SpinBox: إذا كتب المستخدم 1024 والوحدة KB تتحول تلقائياً إلى 1 MB """
        if self.btn_speed_unit.text() == "KB" and value >= 1024:
            self.speed_spin.blockSignals(True) # منع الحلقة اللانهائية أثناء التغيير
            self.speed_spin.setValue(value / 1024)
            self.btn_speed_unit.setText("MB")
            self.speed_spin.blockSignals(False)

    def load_downloads_settings(self):
        """ قراءة إعدادات التنزيلات المحفوظة وتطبيقها على عناصر الواجهة بدقة """
        self.path_combo.blockSignals(True)
        self.speed_combo.blockSignals(True)
        self.speed_spin.blockSignals(True)
        self.concurrent_combo.blockSignals(True)
        self.concurrent_spin.blockSignals(True)

        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 1. مسار الحفظ
                    path_type = data.get("download_path_type", "downloads")
                    idx = self.path_combo.findData(path_type)
                    if idx != -1: self.path_combo.setCurrentIndex(idx)
                    self.custom_selected_path = data.get("custom_path", "")
                    if self.custom_selected_path:
                        folder_name = os.path.basename(self.custom_selected_path) or self.custom_selected_path
                        self.btn_browse_path.setText(f"📁 {folder_name}")
                    
                    # 2. حد السرعة
                    speed_type = data.get("speed_limit_type", "unlimited")
                    idx = self.speed_combo.findData(speed_type)
                    if idx != -1: self.speed_combo.setCurrentIndex(idx)
                    self.speed_spin.setValue(data.get("custom_speed_value", 100))
                    self.btn_speed_unit.setText(data.get("custom_speed_unit", "KB"))
                    
                    # 3. التحميلات المتزامنة
                    concurrent_type = data.get("concurrent_type", "3")
                    idx = self.concurrent_combo.findData(concurrent_type)
                    if idx != -1: self.concurrent_combo.setCurrentIndex(idx)
                    self.concurrent_spin.setValue(data.get("custom_concurrent_value", 3))
            except Exception:
                pass

        self.path_combo.blockSignals(False)
        self.speed_combo.blockSignals(False)
        self.speed_spin.blockSignals(False)
        self.concurrent_combo.blockSignals(False)
        self.concurrent_spin.blockSignals(False)

        # تحديث ظهور العناصر بناءً على القيم اللى اتقرأت
        self.toggle_path_widgets_visibility()
        self.toggle_speed_widgets_visibility()
        self.toggle_concurrent_widgets_visibility()

    def save_downloads_settings(self):
        """ حفظ قيم التنزيلات الثلاثة داخل ملف settings.json وتحديث متغيرات التطبيق فورا """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["download_path_type"] = self.path_combo.currentData()
        data["custom_path"] = getattr(self, 'custom_selected_path', '')
        data["speed_limit_type"] = self.speed_combo.currentData()
        data["custom_speed_value"] = self.speed_spin.value()
        data["custom_speed_unit"] = self.btn_speed_unit.text()
        data["concurrent_type"] = self.concurrent_combo.currentData()
        data["custom_concurrent_value"] = self.concurrent_spin.value()
        
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            # إرسال الإعدادات المحدثة للتطبيق الرئيسي لتطبيقها فوراً على طابور التحميل
            self.main_app.update_app_download_rules(data)
        except Exception:
            pass

    def check_restart_required(self):
        """ 🧠 الفحص الذكي: مقارنة القيم الحالية بالابتدائية للتحكم في زرار الـ Restart والتوست """
        current_lang = self.lang_combo.currentData()
        current_scale = self.scale_combo.currentData()
        
        from utils.locales import resolve_lang
        effective_initial = resolve_lang(getattr(self, 'initial_lang', 'system'))
        effective_current = resolve_lang(current_lang)
        
        lang_changed = effective_current != effective_initial
        scale_changed = current_scale != getattr(self, 'initial_scale', 'auto')
        
        if lang_changed or scale_changed:
            if self.btn_restart.isHidden():
                self.btn_restart.show()
                self.show_toast("⚠️ Restart required to apply changes!")
        else:
            self.btn_restart.hide()
            self.toast_label.setText("")

    def show_toast(self, message):
        """ 💬 عرض توست تنبيهي مؤقت يختفي تلقائياً بعد 4 ثوانٍ من الواجهة """
        self.toast_label.setText(message)
        from PyQt6.QtCore import QTimer
        # إخفاء التوست تلقائياً بعد 4 ثوانٍ مع الحفاظ على زرار الريستارت طالما التغيير قائماً
        QTimer.singleShot(4000, lambda: self.toast_label.setText("") if not self.btn_restart.isHidden() else None)

    def restart_application(self):
        """ ⚡️ الدالة السحرية لإعادة تشغيل البرنامج بالكامل فوراً بنظافة وبدون مشاكل """
        import sys
        import os
        os.execl(sys.executable, sys.executable, *sys.argv)

    def update_icon_colors(self, icon_color):
        self.btn_back.setIcon(get_colored_icon("assets/icons/arrow-left.svg", icon_color))
        self.btn_restart.setIcon(get_colored_icon("assets/icons/restart.svg", icon_color))
        self.item_general.setIcon(get_colored_icon("assets/icons/package.svg", icon_color))
        self.item_appearance.setIcon(get_colored_icon("assets/icons/palette.svg", icon_color))
        self.item_downloads.setIcon(get_colored_icon("assets/icons/save.svg", icon_color))
        self.item_subtitles.setIcon(get_colored_icon("assets/icons/clapperboard.svg", icon_color))
        self.item_output.setIcon(get_colored_icon("assets/icons/video.svg", icon_color))
        self.fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))

    def load_subtitles_settings(self):
        """ قراءة إعدادات الترجمة وتطبيقها على الواجهة """
        primary = "ar"
        secondary = "en"
        fallback = False
        
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    primary = data.get("primary_sub_lang", "ar")
                    secondary = data.get("secondary_sub_lang", "en")
                    fallback = data.get("download_any_sub_fallback", False)
            except Exception:
                pass
        
        # بناء العناصر أولاً لمنع الفقدان
        self.sub_primary_combo.blockSignals(True)
        self.sub_secondary_combo.blockSignals(True)
        
        # نضع العناصر الافتراضية
        languages = [
            (tr("lang_ar_name", "Arabic"), "ar"),
            (tr("lang_en_name", "English"), "en"),
            (tr("lang_fr_name", "French"), "fr"),
            (tr("lang_es_name", "Spanish"), "es"),
            (tr("lang_de_name", "German"), "de"),
            (tr("lang_ru_name", "Russian"), "ru"),
            (tr("lang_zh_name", "Chinese"), "zh")
        ]
        for name, code in languages:
            self.sub_primary_combo.addItem(name, code)
            self.sub_secondary_combo.addItem(name, code)
            
        idx_p = self.sub_primary_combo.findData(primary)
        if idx_p != -1:
            self.sub_primary_combo.setCurrentIndex(idx_p)
        else:
            self.sub_primary_combo.setCurrentIndex(0)
            
        idx_s = self.sub_secondary_combo.findData(secondary)
        if idx_s != -1:
            self.sub_secondary_combo.setCurrentIndex(idx_s)
        else:
            self.sub_secondary_combo.setCurrentIndex(1)
            
        self.fallback_cb.setChecked(fallback)
        
        self.sub_primary_combo.blockSignals(False)
        self.sub_secondary_combo.blockSignals(False)
        
        # تطبيق التصفية التبادلية الذكية
        self.adjust_subtitle_combos()

    def save_subtitles_settings(self):
        """ حفظ إعدادات الترجمة فوراً داخل ملف settings.json """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["primary_sub_lang"] = self.sub_primary_combo.currentData()
        data["secondary_sub_lang"] = self.sub_secondary_combo.currentData()
        data["download_any_sub_fallback"] = self.fallback_cb.isChecked()
        
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
            
        # تطبيق تعديلات الاستبعاد التبادلي
        self.adjust_subtitle_combos()

    def adjust_subtitle_combos(self):
        """ 🧠 ذكاء التفضيلات: لغة الترجمة الأساسية والثانوية لا يمكن أن تكونا متماثلتين """
        self.sub_primary_combo.blockSignals(True)
        self.sub_secondary_combo.blockSignals(True)
        
        primary_current = self.sub_primary_combo.currentData()
        secondary_current = self.sub_secondary_combo.currentData()
        
        languages = [
            (tr("lang_ar_name", "Arabic"), "ar"),
            (tr("lang_en_name", "English"), "en"),
            (tr("lang_fr_name", "French"), "fr"),
            (tr("lang_es_name", "Spanish"), "es"),
            (tr("lang_de_name", "German"), "de"),
            (tr("lang_ru_name", "Russian"), "ru"),
            (tr("lang_zh_name", "Chinese"), "zh")
        ]
        
        # ضبط Primary Combo
        self.sub_primary_combo.clear()
        for name, code in languages:
            if code != secondary_current:
                self.sub_primary_combo.addItem(name, code)
        idx = self.sub_primary_combo.findData(primary_current)
        if idx != -1:
            self.sub_primary_combo.setCurrentIndex(idx)
        else:
            self.sub_primary_combo.setCurrentIndex(0)
            
        # ضبط Secondary Combo
        self.sub_secondary_combo.clear()
        for name, code in languages:
            if code != primary_current:
                self.sub_secondary_combo.addItem(name, code)
        idx = self.sub_secondary_combo.findData(secondary_current)
        if idx != -1:
            self.sub_secondary_combo.setCurrentIndex(idx)
        else:
            self.sub_secondary_combo.setCurrentIndex(0)
            
        self.sub_primary_combo.blockSignals(False)
        self.sub_secondary_combo.blockSignals(False)

    def toggle_video_sub_widgets(self):
        """ 👁️ إخفاء وإظهار ويدجت الترجمة للفيديو تفاعلياً حسب رغبة الدمج """
        is_embedded = self.embed_subtitles_cb.isChecked()
        self.autoplay_subtitles_cb.setVisible(is_embedded)
        self.external_sub_widget.setVisible(not is_embedded)

    def toggle_audio_sub_widgets(self):
        """ 👁️ إخفاء وإظهار قائمة حاويات الصوت عند اختيار دمج الترجمة """
        is_embedded = self.embed_audio_sub_cb.isChecked()
        self.audio_container_widget.setVisible(is_embedded)
        self.audio_sub_widget.setVisible(not is_embedded)

    def load_output_settings(self):
        """ قراءة تفضيلات صيغة الملف الخارج والترجمات المتقدمة """
        video_container = "mp4"
        embed_subtitles = False
        autoplay_subtitles = False
        external_sub_format = "srt"
        audio_sub_format = "lrc"
        embed_audio_sub = False
        audio_container = "m4a"
        
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    video_container = data.get("video_container", "mp4")
                    embed_subtitles = data.get("embed_subtitles", False)
                    autoplay_subtitles = data.get("autoplay_subtitles", False)
                    external_sub_format = data.get("external_sub_format", "srt")
                    audio_sub_format = data.get("audio_sub_format", "lrc")
                    embed_audio_sub = data.get("embed_audio_sub", False)
                    audio_container = data.get("audio_container", "m4a")
            except Exception:
                pass
                
        # تطبيق على الواجهة مع حظر الإشارات لتفادي الحفظ اللانهائي
        self.video_container_combo.blockSignals(True)
        self.embed_subtitles_cb.blockSignals(True)
        self.autoplay_subtitles_cb.blockSignals(True)
        self.external_sub_combo.blockSignals(True)
        self.audio_sub_combo.blockSignals(True)
        self.embed_audio_sub_cb.blockSignals(True)
        self.audio_container_combo.blockSignals(True)
        
        idx = self.video_container_combo.findData(video_container)
        if idx != -1: self.video_container_combo.setCurrentIndex(idx)
        
        self.embed_subtitles_cb.setChecked(embed_subtitles)
        self.autoplay_subtitles_cb.setChecked(autoplay_subtitles)
        
        idx = self.external_sub_combo.findData(external_sub_format)
        if idx != -1: self.external_sub_combo.setCurrentIndex(idx)
        
        idx = self.audio_sub_combo.findData(audio_sub_format)
        if idx != -1: self.audio_sub_combo.setCurrentIndex(idx)
        
        self.embed_audio_sub_cb.setChecked(embed_audio_sub)
        
        idx = self.audio_container_combo.findData(audio_container)
        if idx != -1: self.audio_container_combo.setCurrentIndex(idx)
        
        self.video_container_combo.blockSignals(False)
        self.embed_subtitles_cb.blockSignals(False)
        self.autoplay_subtitles_cb.blockSignals(False)
        self.external_sub_combo.blockSignals(False)
        self.audio_sub_combo.blockSignals(False)
        self.embed_audio_sub_cb.blockSignals(False)
        self.audio_container_combo.blockSignals(False)
        
        # تهيئة حالة الظهور/الإخفاء التفاعلية
        self.toggle_video_sub_widgets()
        self.toggle_audio_sub_widgets()

    def save_output_settings(self):
        """ حفظ تفضيلات صيغة الملف الخارج والترجمات المتقدمة فوراً """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["video_container"] = self.video_container_combo.currentData()
        data["embed_subtitles"] = self.embed_subtitles_cb.isChecked()
        data["autoplay_subtitles"] = self.autoplay_subtitles_cb.isChecked()
        data["external_sub_format"] = self.external_sub_combo.currentData()
        data["audio_sub_format"] = self.audio_sub_combo.currentData()
        data["embed_audio_sub"] = self.embed_audio_sub_cb.isChecked()
        data["audio_container"] = self.audio_container_combo.currentData()
        
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass