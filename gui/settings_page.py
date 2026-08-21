import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QCheckBox, QPushButton, QFileDialog,
                             QApplication, QSpinBox, QFontComboBox, QFrame,
                             QScrollArea, QStackedWidget, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt
from utils.settings import app_config, save_settings
from gui.theme import styled, apply_theme, Theme
from utils import strings 

class SettingsWidget(QWidget):
    def __init__(self, parent=None, go_back_callback=None):
        super().__init__(parent)
        self.setWindowTitle(strings.APP_SET_TITLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # --- 1. الهيدر العلوي: العنوان وأزرار الأقسام الأفقية (Segmented Bar) ---
        header_layout = QHBoxLayout()
        
        self.header_title = QLabel(strings.APP_SET_TITLE)
        self.header_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #f3f4f6;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()

        self.restart_btn = QPushButton(strings.BTN_SET_RESTART)
        self.restart_btn.setObjectName("primary")
        self.restart_btn.setStyleSheet("background-color: #f59e0b; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        self.restart_btn.clicked.connect(self.save_and_restart)
        self.restart_btn.hide()
        header_layout.addWidget(self.restart_btn)

        main_layout.addLayout(header_layout)

        # شريط الأقسام الأفقي (Pill Tabs)
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)
        
        self.tab_btn_gen = QPushButton("🎨 " + ("عام والمظهر" if strings.is_ar else "General & Appearance"))
        self.tab_btn_gen.setObjectName("SettingsSegmentBtn")
        self.tab_btn_gen.setProperty("active", "true")
        self.tab_btn_gen.clicked.connect(lambda: self.switch_page(0))

        self.tab_btn_dl = QPushButton("📥 " + ("التحميلات والترجمة" if strings.is_ar else "Downloads & Subtitles"))
        self.tab_btn_dl.setObjectName("SettingsSegmentBtn")
        self.tab_btn_dl.clicked.connect(lambda: self.switch_page(1))

        self.tab_btn_adv = QPushButton("🛠️ " + ("خيارات متقدمة" if strings.is_ar else "Advanced"))
        self.tab_btn_adv.setObjectName("SettingsSegmentBtn")
        self.tab_btn_adv.clicked.connect(lambda: self.switch_page(2))

        nav_bar.addWidget(self.tab_btn_gen)
        nav_bar.addWidget(self.tab_btn_dl)
        nav_bar.addWidget(self.tab_btn_adv)
        nav_bar.addStretch()

        main_layout.addLayout(nav_bar)

        # --- 2. مساحة المحتوى القابلة للتمرير (Scroll Area) ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 8, 0, 0)
        scroll_layout.setSpacing(16)

        self.stacked_widget = QStackedWidget()
        self.setup_pages()
        scroll_layout.addWidget(self.stacked_widget)
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        self.load_data()
        self.connect_signals()

    def switch_page(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        
        self.tab_btn_gen.setProperty("active", "true" if index == 0 else "false")
        self.tab_btn_dl.setProperty("active", "true" if index == 1 else "false")
        self.tab_btn_adv.setProperty("active", "true" if index == 2 else "false")

        for btn in [self.tab_btn_gen, self.tab_btn_dl, self.tab_btn_adv]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def setup_pages(self):
        # ═════════════════════════════════════════════════════════════
        # الصفحة 1: عام والمظهر (General & Appearance)
        # ═════════════════════════════════════════════════════════════
        self.page_gen = QWidget()
        page_gen_layout = QVBoxLayout(self.page_gen)
        page_gen_layout.setContentsMargins(0, 0, 0, 0)
        page_gen_layout.setSpacing(14)

        card_appearance = QFrame()
        card_appearance.setObjectName("OptionsCard")
        card_app_layout = QVBoxLayout(card_appearance)
        card_app_layout.setContentsMargins(18, 18, 18, 18)
        card_app_layout.setSpacing(14)

        title_app = QLabel("🎨 " + ("المظهر والتخصيص" if strings.is_ar else "Appearance & Customization"))
        title_app.setStyleSheet("font-size: 14px; font-weight: 700; color: #f3f4f6;")
        card_app_layout.addWidget(title_app)

        grid_app = QGridLayout()
        grid_app.setHorizontalSpacing(16)
        grid_app.setVerticalSpacing(12)

        # اللغة
        lbl_lang = QLabel(strings.LBL_SET_LANG)
        lbl_lang.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(strings.OPT_SET_LANG_SYS, "system")
        self.lang_combo.addItem(strings.OPT_SET_LANG_EN, "en")
        self.lang_combo.addItem(strings.OPT_SET_LANG_AR, "ar")
        grid_app.addWidget(lbl_lang, 0, 0)
        grid_app.addWidget(self.lang_combo, 0, 1)

        # الثيم
        lbl_theme = QLabel(strings.LBL_SET_THEME)
        lbl_theme.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(strings.OPT_SET_THEME_AUTO, "auto")
        self.theme_combo.addItem(strings.OPT_SET_THEME_LIGHT, "light")
        self.theme_combo.addItem(strings.OPT_SET_THEME_DARK, "dark")
        grid_app.addWidget(lbl_theme, 1, 0)
        grid_app.addWidget(self.theme_combo, 1, 1)

        # نوع الخط
        lbl_font = QLabel(strings.LBL_SET_FONT_FAMILY)
        lbl_font.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.font_combo = QFontComboBox()
        grid_app.addWidget(lbl_font, 2, 0)
        grid_app.addWidget(self.font_combo, 2, 1)

        # حجم الخط
        lbl_size = QLabel(strings.LBL_SET_FONT_SIZE)
        lbl_size.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 30)
        grid_app.addWidget(lbl_size, 3, 0)
        grid_app.addWidget(self.font_size_spin, 3, 1)

        card_app_layout.addLayout(grid_app)

        card_app_layout.addSpacing(6)
        self.notify_check = QCheckBox(strings.CHK_SET_NOTIFY)
        self.thumb_check = QCheckBox(strings.CHK_SET_THUMB)
        card_app_layout.addWidget(self.notify_check)
        card_app_layout.addWidget(self.thumb_check)

        page_gen_layout.addWidget(card_appearance)
        page_gen_layout.addStretch()
        self.stacked_widget.addWidget(self.page_gen)

        # ═════════════════════════════════════════════════════════════
        # الصفحة 2: التحميلات والترجمة (Downloads & Subtitles)
        # ═════════════════════════════════════════════════════════════
        self.page_dl = QWidget()
        page_dl_layout = QVBoxLayout(self.page_dl)
        page_dl_layout.setContentsMargins(0, 0, 0, 0)
        page_dl_layout.setSpacing(14)

        # كارت المسار والسرعة
        card_loc = QFrame()
        card_loc.setObjectName("OptionsCard")
        card_loc_layout = QVBoxLayout(card_loc)
        card_loc_layout.setContentsMargins(18, 18, 18, 18)
        card_loc_layout.setSpacing(14)

        title_loc = QLabel("📁 " + ("مسار وسرعة التحميل" if strings.is_ar else "Download Path & Speed"))
        title_loc.setStyleSheet("font-size: 14px; font-weight: 700; color: #f3f4f6;")
        card_loc_layout.addWidget(title_loc)

        grid_loc = QGridLayout()
        grid_loc.setHorizontalSpacing(16)
        grid_loc.setVerticalSpacing(12)

        lbl_loc = QLabel(strings.LBL_SET_DL_LOC)
        lbl_loc.setStyleSheet("font-weight: 600; color: #9ca3af;")
        loc_h = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItem(strings.OPT_SET_LOC_ASK, "ask")
        self.location_combo.addItem(strings.OPT_SET_LOC_AUTO, "auto")
        self.location_combo.addItem(strings.OPT_SET_LOC_CUSTOM, "custom")
        loc_h.addWidget(self.location_combo, stretch=1)

        self.custom_loc_btn = QPushButton(strings.BTN_SET_BROWSE)
        self.custom_loc_btn.setObjectName("ghost")
        self.custom_loc_btn.hide()
        loc_h.addWidget(self.custom_loc_btn)
        grid_loc.addWidget(lbl_loc, 0, 0)
        grid_loc.addLayout(loc_h, 0, 1)

        lbl_speed = QLabel(strings.LBL_SET_SPEED)
        lbl_speed.setStyleSheet("font-weight: 600; color: #9ca3af;")
        speed_h = QHBoxLayout()
        self.speed_combo = QComboBox()
        self.speed_combo.addItem(strings.OPT_SET_SPEED_NONE, "0")
        self.speed_combo.addItem("500 KB/s", "500K")
        self.speed_combo.addItem("1 MB/s", "1M")
        self.speed_combo.addItem("2 MB/s", "2M")
        self.speed_combo.addItem(strings.OPT_SET_LOC_CUSTOM, "custom")
        speed_h.addWidget(self.speed_combo, stretch=1)

        self.custom_speed_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_speed_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(4)
        self.custom_speed_spin = QSpinBox()
        self.custom_speed_spin.setRange(1, 50000)
        self.custom_speed_unit = QComboBox()
        self.custom_speed_unit.addItems(["KB/s", "MB/s"])
        custom_layout.addWidget(self.custom_speed_spin)
        custom_layout.addWidget(self.custom_speed_unit)
        self.custom_speed_widget.hide()
        speed_h.addWidget(self.custom_speed_widget)

        grid_loc.addWidget(lbl_speed, 1, 0)
        grid_loc.addLayout(speed_h, 1, 1)

        lbl_conc = QLabel(strings.LBL_SET_CONCURRENT)
        lbl_conc.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        grid_loc.addWidget(lbl_conc, 2, 0)
        grid_loc.addWidget(self.concurrent_spin, 2, 1)

        card_loc_layout.addLayout(grid_loc)
        self.data_saver_check = QCheckBox(strings.CHK_SET_DATA_SAVER)
        card_loc_layout.addWidget(self.data_saver_check)
        page_dl_layout.addWidget(card_loc)

        # كارت الترجمة والجودة
        card_subs = QFrame()
        card_subs.setObjectName("OptionsCard")
        card_subs_layout = QVBoxLayout(card_subs)
        card_subs_layout.setContentsMargins(18, 18, 18, 18)
        card_subs_layout.setSpacing(14)

        title_subs = QLabel("🌐 " + ("الترجمة والجودة" if strings.is_ar else "Subtitles & Quality"))
        title_subs.setStyleSheet("font-size: 14px; font-weight: 700; color: #f3f4f6;")
        card_subs_layout.addWidget(title_subs)

        grid_subs = QGridLayout()
        grid_subs.setHorizontalSpacing(16)
        grid_subs.setVerticalSpacing(12)

        lbl_p_sub = QLabel(strings.LBL_SET_PRIM_SUB)
        lbl_p_sub.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.prim_sub_combo = QComboBox()
        self.prim_sub_combo.addItem("العربية (Arabic)" if strings.is_ar else "Arabic", "ar")
        self.prim_sub_combo.addItem("English", "en")
        self.prim_sub_combo.addItem("Français (French)" if strings.is_ar else "French", "fr")
        self.prim_sub_combo.addItem("Español (Spanish)" if strings.is_ar else "Spanish", "es")
        grid_subs.addWidget(lbl_p_sub, 0, 0)
        grid_subs.addWidget(self.prim_sub_combo, 0, 1)

        lbl_s_sub = QLabel(strings.LBL_SET_SEC_SUB)
        lbl_s_sub.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.sec_sub_combo = QComboBox()
        self.sec_sub_combo.addItem("English", "en")
        self.sec_sub_combo.addItem("العربية (Arabic)" if strings.is_ar else "Arabic", "ar")
        self.sec_sub_combo.addItem("Français (French)" if strings.is_ar else "French", "fr")
        self.sec_sub_combo.addItem("Español (Spanish)" if strings.is_ar else "Spanish", "es")
        grid_subs.addWidget(lbl_s_sub, 1, 0)
        grid_subs.addWidget(self.sec_sub_combo, 1, 1)

        card_subs_layout.addLayout(grid_subs)

        self.embed_subs_check = QCheckBox(strings.CHK_EMBED_SUBS)
        card_subs_layout.addWidget(self.embed_subs_check)

        downgrade_layout = QHBoxLayout()
        self.downgrade_check = QCheckBox(strings.CHK_SET_DOWNGRADE)
        downgrade_info_lbl = QLabel("ℹ️")
        downgrade_info_lbl.setToolTip(strings.TOOLTIP_DOWNGRADE_INFO)
        downgrade_info_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        downgrade_layout.addWidget(self.downgrade_check)
        downgrade_layout.addWidget(downgrade_info_lbl)
        downgrade_layout.addStretch()
        card_subs_layout.addLayout(downgrade_layout)

        page_dl_layout.addWidget(card_subs)
        page_dl_layout.addStretch()
        self.stacked_widget.addWidget(self.page_dl)

        # ═════════════════════════════════════════════════════════════
        # الصفحة 3: خيارات متقدمة (Advanced Options)
        # ═════════════════════════════════════════════════════════════
        self.page_adv = QWidget()
        page_adv_layout = QVBoxLayout(self.page_adv)
        page_adv_layout.setContentsMargins(0, 0, 0, 0)
        page_adv_layout.setSpacing(14)

        card_cookies = QFrame()
        card_cookies.setObjectName("OptionsCard")
        card_cook_layout = QVBoxLayout(card_cookies)
        card_cook_layout.setContentsMargins(18, 18, 18, 18)
        card_cook_layout.setSpacing(12)

        title_cook = QLabel("🍪 " + ("ملفات تعريف الارتباط (Cookies)" if strings.is_ar else "Browser Cookies"))
        title_cook.setStyleSheet("font-size: 14px; font-weight: 700; color: #f3f4f6;")
        card_cook_layout.addWidget(title_cook)

        lbl_cook_desc = QLabel("يساعد استيراد ملفات تعريف الارتباط في تحميل مقاطع الفيديو المحمية أو الخاصة من المتصفح مباشرة." if strings.is_ar else "Import cookies to download private or restricted videos directly from your browser.")
        lbl_cook_desc.setStyleSheet("font-size: 12px; color: #9ca3af;")
        lbl_cook_desc.setWordWrap(True)
        card_cook_layout.addWidget(lbl_cook_desc)

        lbl_cookies = QLabel(strings.LBL_SET_COOKIES)
        lbl_cookies.setStyleSheet("font-weight: 600; color: #9ca3af;")
        self.cookie_combo = QComboBox()
        self.cookie_combo.addItem(strings.OPT_SET_COOKIE_NONE, "none")
        self.cookie_combo.addItem("Google Chrome", "chrome")
        self.cookie_combo.addItem("Mozilla Firefox", "firefox")
        self.cookie_combo.addItem("Microsoft Edge", "edge")
        self.cookie_combo.addItem("Brave", "brave")
        self.cookie_combo.addItem(strings.OPT_SET_COOKIE_CUSTOM, "custom")
        card_cook_layout.addWidget(self.cookie_combo)

        page_adv_layout.addWidget(card_cookies)

        card_reset = QFrame()
        card_reset.setObjectName("OptionsCard")
        card_reset_layout = QVBoxLayout(card_reset)
        card_reset_layout.setContentsMargins(18, 18, 18, 18)
        card_reset_layout.setSpacing(12)

        title_reset = QLabel("⚠️ " + ("إعادة ضبط المصنع" if strings.is_ar else "Factory Reset"))
        title_reset.setStyleSheet("font-size: 14px; font-weight: 700; color: #ef4444;")
        card_reset_layout.addWidget(title_reset)

        lbl_reset_desc = QLabel("إعادة تعيين كافة إعدادات التطبيق إلى حالتها الافتراضية الأولية." if strings.is_ar else "Reset all application settings and preferences to default.")
        lbl_reset_desc.setStyleSheet("font-size: 12px; color: #9ca3af;")
        card_reset_layout.addWidget(lbl_reset_desc)

        self.reset_all_btn = styled.danger_button(strings.BTN_FACTORY_RESET)
        self.reset_all_btn.setFixedHeight(36)
        card_reset_layout.addWidget(self.reset_all_btn)

        page_adv_layout.addWidget(card_reset)
        page_adv_layout.addStretch()
        self.stacked_widget.addWidget(self.page_adv)

        # ربط الأحداث المباشرة
        self.location_combo.currentIndexChanged.connect(self.toggle_custom_location)
        self.custom_loc_btn.clicked.connect(self.browse_folder)
        self.speed_combo.currentIndexChanged.connect(self.toggle_custom_speed)
        self.custom_speed_unit.currentTextChanged.connect(self.on_speed_unit_changed)
        self.reset_all_btn.clicked.connect(self.factory_reset)

    def on_speed_unit_changed(self, text):
        if text == "KB/s": self.custom_speed_spin.setValue(100)
        else: self.custom_speed_spin.setValue(1)

    def toggle_custom_speed(self):
        if self.speed_combo.currentData() == "custom":
            self.custom_speed_widget.show()
            if self.custom_speed_unit.currentText() == "KB/s": self.custom_speed_spin.setValue(100)
            else: self.custom_speed_spin.setValue(1)
        else:
            self.custom_speed_widget.hide()

    def toggle_custom_location(self):
        if self.location_combo.currentData() == "custom": self.custom_loc_btn.show()
        else: self.custom_loc_btn.hide()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.custom_loc_btn.setProperty("path", folder)
            folder_name = folder.split('/')[-1] if '/' in folder else folder
            self.custom_loc_btn.setText(f"📁 {folder_name}")
            self.save_data()

    def load_data(self):
        idx = self.theme_combo.findData(app_config.get("theme", "auto"))
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)
        
        self.initial_lang = app_config.get("language", "system")
        idx = self.lang_combo.findData(self.initial_lang)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        
        idx = self.location_combo.findData(app_config.get("save_mode", "auto"))
        if idx >= 0: self.location_combo.setCurrentIndex(idx)

        self.initial_font_family = app_config.get("font_family", "system")
        if self.initial_font_family != "system":
            self.font_combo.setCurrentText(self.initial_font_family)
        
        self.initial_font_size = app_config.get("font_size", 12)
        self.font_size_spin.setValue(self.initial_font_size)

        if app_config.get("custom_path"):
            self.custom_loc_btn.setProperty("path", app_config.get("custom_path"))
            folder_name = app_config["custom_path"].split('/')[-1]
            self.custom_loc_btn.setText(f"📁 {folder_name}")
            if app_config.get("save_mode") == "custom":
                self.custom_loc_btn.show()

        self.notify_check.setChecked(app_config.get("notifications", True))
        self.data_saver_check.setChecked(app_config.get("data_saver", False))
        self.concurrent_spin.setValue(app_config.get("concurrent_downloads", 1))

        speed_val = app_config.get("speed_limit", "0")
        idx = self.speed_combo.findData(speed_val)
        if idx >= 0:
            self.speed_combo.setCurrentIndex(idx)
            self.custom_speed_widget.hide()
        else:
            self.speed_combo.setCurrentIndex(self.speed_combo.findData("custom"))
            self.custom_speed_widget.show()
            if "M" in speed_val:
                self.custom_speed_spin.setValue(int(speed_val.replace("M", "")))
                self.custom_speed_unit.setCurrentText("MB/s")
            elif "K" in speed_val:
                self.custom_speed_spin.setValue(int(speed_val.replace("K", "")))
                self.custom_speed_unit.setCurrentText("KB/s")

        self.thumb_check.setChecked(app_config.get("show_thumbnails", True))
        self.downgrade_check.setChecked(app_config.get("allow_downgrade", True))

        self.embed_subs_check.setChecked(app_config.get("embed_subs_default", True))
        p_idx = self.prim_sub_combo.findData(app_config.get("primary_sub_lang", "ar"))
        if p_idx >= 0: self.prim_sub_combo.setCurrentIndex(p_idx)
        s_idx = self.sec_sub_combo.findData(app_config.get("secondary_sub_lang", "en"))
        if s_idx >= 0: self.sec_sub_combo.setCurrentIndex(s_idx)
        
        c_idx = self.cookie_combo.findData(app_config.get("browser_cookies", "none"))
        if c_idx >= 0: self.cookie_combo.setCurrentIndex(c_idx)

        self.check_restart_needed()

    def check_restart_needed(self):
        lang_changed = (self.lang_combo.currentData() != getattr(self, 'initial_lang', None))
        font_f_changed = (self.font_combo.currentText() != getattr(self, 'initial_font_family', None))
        font_s_changed = (self.font_size_spin.value() != getattr(self, 'initial_font_size', None))
        
        if lang_changed or font_f_changed or font_s_changed:
            self.restart_btn.show()
        else:
            self.restart_btn.hide()

    def save_data(self):
        app_config["theme"] = self.theme_combo.currentData()
        app_config["language"] = self.lang_combo.currentData()
        app_config["save_mode"] = self.location_combo.currentData()
        custom_path = self.custom_loc_btn.property("path")
        if custom_path: app_config["custom_path"] = custom_path
        app_config["notifications"] = self.notify_check.isChecked()
        app_config["data_saver"] = self.data_saver_check.isChecked()
        app_config["concurrent_downloads"] = self.concurrent_spin.value()
        app_config["show_thumbnails"] = self.thumb_check.isChecked()
        app_config["browser_cookies"] = self.cookie_combo.currentData()
        app_config["font_family"] = self.font_combo.currentText()
        app_config["font_size"] = self.font_size_spin.value()

        if self.speed_combo.currentData() == "custom":
            unit = "M" if self.custom_speed_unit.currentText() == "MB/s" else "K"
            app_config["speed_limit"] = f"{self.custom_speed_spin.value()}{unit}"
        else:
            app_config["speed_limit"] = self.speed_combo.currentData()

        app_config["allow_downgrade"] = self.downgrade_check.isChecked()
        app_config["embed_subs_default"] = self.embed_subs_check.isChecked()
        app_config["primary_sub_lang"] = self.prim_sub_combo.currentData()
        app_config["secondary_sub_lang"] = self.sec_sub_combo.currentData()
        save_settings(app_config)

    def on_restart_setting_changed(self):
        self.save_data()
        self.check_restart_needed()

    def connect_signals(self):
        self.theme_combo.currentIndexChanged.connect(self.save_and_apply_theme)
        self.lang_combo.currentIndexChanged.connect(self.on_restart_setting_changed)
        self.font_combo.currentFontChanged.connect(self.on_restart_setting_changed)
        self.font_size_spin.valueChanged.connect(self.on_restart_setting_changed)

        self.location_combo.currentIndexChanged.connect(self.save_data)
        self.speed_combo.currentIndexChanged.connect(self.save_data)
        self.custom_speed_spin.valueChanged.connect(self.save_data)
        self.custom_speed_unit.currentTextChanged.connect(self.save_data)
        self.concurrent_spin.valueChanged.connect(self.save_data)
        self.notify_check.stateChanged.connect(self.save_data)
        self.data_saver_check.stateChanged.connect(self.save_data)
        self.thumb_check.stateChanged.connect(self.save_data)
        self.cookie_combo.currentIndexChanged.connect(self.on_cookie_changed)

        self.downgrade_check.stateChanged.connect(self.save_data)
        self.embed_subs_check.stateChanged.connect(self.save_data)
        self.prim_sub_combo.currentIndexChanged.connect(self.save_data)
        self.sec_sub_combo.currentIndexChanged.connect(self.save_data)

    def save_and_apply_theme(self):
        self.save_data()
        app = QApplication.instance()
        apply_theme(app, app_config.get("theme", "auto"))

    def save_and_restart(self):
        self.save_data()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def factory_reset(self):
        from PyQt6.QtWidgets import QMessageBox
        import sys
        import os
        from utils.settings import default_config, save_settings

        reply = QMessageBox.question(self, "تأكيد" if strings.is_ar else "Confirm", 
                                     strings.MSG_RESET_CONFIRM, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            app_config.clear()
            app_config.update(default_config)

            app_config["font_family"] = "system"
            app_config["font_size"] = 12
            
            save_settings(app_config)

            os.execl(sys.executable, sys.executable, *sys.argv)

    def on_cookie_changed(self, index):
        selected_mode = self.cookie_combo.currentData()
        
        if selected_mode == "custom":
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                strings.MSG_SELECT_COOKIE_FILE, 
                "", 
                "Text Files (*.txt);;All Files (*)"
            )
            if file_path:
                app_config["browser_cookies"] = "custom"
                app_config["cookie_file"] = file_path
                self.save_data()
            else:
                self.cookie_combo.setCurrentIndex(0) 
        else:
            self.save_data()