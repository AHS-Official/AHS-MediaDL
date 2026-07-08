import sys
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QCheckBox, QPushButton, QFileDialog,
                             QWidget, QApplication, QTabWidget, QSpinBox, QFontComboBox)
from PyQt6.QtWidgets import QListWidget, QStackedWidget
from PyQt6.QtCore import Qt
from utils.settings import app_config, save_settings
from gui.theme import apply_theme
from utils import strings 

class SettingsWidget(QWidget):
    def __init__(self, parent=None, go_back_callback=None):
        super().__init__(parent)
        self.setWindowTitle(strings.APP_SET_TITLE)
        self.resize(650, 450)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(160)
        self.sidebar.setObjectName("Sidebar")
        border_style = "border-left: 1px solid rgba(128, 128, 128, 0.2);" if strings.is_ar else "border-right: 1px solid rgba(128, 128, 128, 0.2);"
        self.sidebar.setStyleSheet(f"""
            QListWidget#Sidebar {{
                background-color: rgba(0, 0, 0, 0.05); /* لون خلفية خفيف */
                border: none;
                {border_style}
                padding-top: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QListWidget#Sidebar::item {{
                padding: 12px;
                margin: 4px 8px;
                border-radius: 6px;
            }}
            QListWidget#Sidebar::item:selected {{
                background-color: #4d78cc; /* لونك الأزرق المميز */
                color: white;
            }}
            QListWidget#Sidebar::item:hover:!selected {{
                background-color: rgba(128, 128, 128, 0.1);
            }}
        """)
        self.main_layout.addWidget(self.sidebar)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        self.stacked_widget = QStackedWidget()
        right_layout.addWidget(self.stacked_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.restart_btn = QPushButton(strings.BTN_SET_RESTART)
        self.restart_btn.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 6px 15px; border-radius: 5px;")
        self.restart_btn.clicked.connect(self.save_and_restart)
        btn_layout.addWidget(self.restart_btn)

        self.done_btn = QPushButton(strings.BTN_SET_DONE)
        if go_back_callback:
            self.done_btn.clicked.connect(go_back_callback)
        self.done_btn.setStyleSheet("background-color: #4d78cc; color: white; font-weight: bold; padding: 6px 20px; border-radius: 5px;")
        btn_layout.addWidget(self.done_btn)

        right_layout.addLayout(btn_layout)
        self.main_layout.addWidget(right_container, stretch=1)

        self.sidebar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        self.setup_pages()

        self.load_data()
        self.connect_signals()

    def setup_pages(self):
        self.tab_general = QWidget()
        layout_general = QVBoxLayout(self.tab_general)

        layout_general.addWidget(QLabel(strings.LBL_SET_LANG))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(strings.OPT_SET_LANG_SYS, "system")
        self.lang_combo.addItem(strings.OPT_SET_LANG_EN, "en")
        self.lang_combo.addItem(strings.OPT_SET_LANG_AR, "ar")
        layout_general.addWidget(self.lang_combo)

        self.notify_check = QCheckBox(strings.CHK_SET_NOTIFY)
        layout_general.addWidget(self.notify_check)

        self.close_to_tray_check = QCheckBox("التصغير للشريط العلوي عند الإغلاق (X)" if strings.is_ar else "Minimize to tray on close (X)")
        layout_general.addWidget(self.close_to_tray_check)

        layout_general.addStretch()
        self.sidebar.addItem(strings.SET_TAB_GENERAL)
        self.stacked_widget.addWidget(self.tab_general)

        self.tab_appearance = QWidget()
        layout_appearance = QVBoxLayout(self.tab_appearance)

        layout_appearance.addWidget(QLabel(strings.LBL_SET_THEME))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(strings.OPT_SET_THEME_AUTO, "auto")
        self.theme_combo.addItem(strings.OPT_SET_THEME_LIGHT, "light")
        self.theme_combo.addItem(strings.OPT_SET_THEME_DARK, "dark")
        layout_appearance.addWidget(self.theme_combo)

        layout_appearance.addWidget(QLabel(strings.LBL_SET_FONT_FAMILY))
        self.font_combo = QFontComboBox()
        layout_appearance.addWidget(self.font_combo)

        layout_appearance.addWidget(QLabel(strings.LBL_SET_FONT_SIZE))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 30)
        layout_appearance.addWidget(self.font_size_spin)

        win_size_layout = QHBoxLayout()
        self.win_width_spin = QSpinBox()
        self.win_width_spin.setRange(400, 1920)
        self.win_width_spin.setPrefix("W: ")
        self.win_height_spin = QSpinBox()
        self.win_height_spin.setRange(400, 1080)
        self.win_height_spin.setPrefix("H: ")

        win_size_layout.addWidget(QLabel(strings.LBL_SET_WIN_WIDTH))
        win_size_layout.addWidget(self.win_width_spin)
        win_size_layout.addWidget(QLabel(strings.LBL_SET_WIN_HEIGHT))
        win_size_layout.addWidget(self.win_height_spin)
        layout_appearance.addLayout(win_size_layout)

        self.thumb_check = QCheckBox(strings.CHK_SET_THUMB)
        layout_appearance.addWidget(self.thumb_check) 

        layout_appearance.addStretch()
        self.sidebar.addItem(strings.SET_TAB_APPEARANCE)
        self.stacked_widget.addWidget(self.tab_appearance)

        self.tab_downloads = QWidget()
        layout_downloads = QVBoxLayout(self.tab_downloads)

        layout_downloads.addWidget(QLabel(strings.LBL_SET_DL_LOC))
        loc_layout = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItem(strings.OPT_SET_LOC_ASK, "ask")
        self.location_combo.addItem(strings.OPT_SET_LOC_AUTO, "auto")
        self.location_combo.addItem(strings.OPT_SET_LOC_CUSTOM, "custom")
        loc_layout.addWidget(self.location_combo)

        self.custom_loc_btn = QPushButton(strings.BTN_SET_BROWSE)
        self.custom_loc_btn.setStyleSheet("background-color: #34495e; color: white; border-radius: 4px; padding: 4px;")
        self.custom_loc_btn.hide()
        loc_layout.addWidget(self.custom_loc_btn)
        layout_downloads.addLayout(loc_layout)

        layout_downloads.addWidget(QLabel(strings.LBL_SET_SPEED))
        speed_layout = QHBoxLayout()
        self.speed_combo = QComboBox()
        self.speed_combo.addItem(strings.OPT_SET_SPEED_NONE, "0")
        self.speed_combo.addItem("500 KB/s", "500K")
        self.speed_combo.addItem("1 MB/s", "1M")
        self.speed_combo.addItem("2 MB/s", "2M")
        self.speed_combo.addItem(strings.OPT_SET_LOC_CUSTOM, "custom")

        self.custom_speed_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_speed_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_speed_spin = QSpinBox()
        self.custom_speed_spin.setRange(1, 50000)
        self.custom_speed_unit = QComboBox()
        self.custom_speed_unit.addItems(["KB/s", "MB/s"])
        custom_layout.addWidget(self.custom_speed_spin)
        custom_layout.addWidget(self.custom_speed_unit)
        self.custom_speed_widget.hide()

        speed_layout.addWidget(self.speed_combo)
        speed_layout.addWidget(self.custom_speed_widget)
        layout_downloads.addLayout(speed_layout)

        layout_downloads.addWidget(QLabel(strings.LBL_SET_CONCURRENT))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        layout_downloads.addWidget(self.concurrent_spin)

        self.data_saver_check = QCheckBox(strings.CHK_SET_DATA_SAVER)
        layout_downloads.addWidget(self.data_saver_check)

        layout_downloads.addStretch()
        self.sidebar.addItem(strings.SET_TAB_DOWNLOADS)
        self.stacked_widget.addWidget(self.tab_downloads)

        self.tab_quality = QWidget()
        layout_quality = QVBoxLayout(self.tab_quality)

        self.embed_subs_check = QCheckBox(strings.CHK_EMBED_SUBS)
        layout_quality.addWidget(self.embed_subs_check)

        layout_quality.addWidget(QLabel(strings.LBL_SET_PRIM_SUB))
        self.prim_sub_combo = QComboBox()
        self.prim_sub_combo.addItem("العربية (Arabic)" if strings.is_ar else "Arabic", "ar")
        self.prim_sub_combo.addItem("English", "en")
        self.prim_sub_combo.addItem("Français (French)" if strings.is_ar else "French", "fr")
        self.prim_sub_combo.addItem("Español (Spanish)" if strings.is_ar else "Spanish", "es")
        layout_quality.addWidget(self.prim_sub_combo)

        layout_quality.addWidget(QLabel(strings.LBL_SET_SEC_SUB))
        self.sec_sub_combo = QComboBox()
        self.sec_sub_combo.addItem("English", "en")
        self.sec_sub_combo.addItem("العربية (Arabic)" if strings.is_ar else "Arabic", "ar")
        self.sec_sub_combo.addItem("Français (French)" if strings.is_ar else "French", "fr")
        self.sec_sub_combo.addItem("Español (Spanish)" if strings.is_ar else "Spanish", "es")
        layout_quality.addWidget(self.sec_sub_combo)

        layout_quality.addStretch()
        self.sidebar.addItem(strings.SET_TAB_QUALITY)
        self.stacked_widget.addWidget(self.tab_quality)

        self.tab_advanced = QWidget()
        layout_advanced = QVBoxLayout(self.tab_advanced)

        layout_advanced.addWidget(QLabel(strings.LBL_SET_COOKIES))
        self.cookie_combo = QComboBox()
        self.cookie_combo.addItem(strings.OPT_SET_COOKIE_NONE, "none")
        self.cookie_combo.addItem("Google Chrome", "chrome")
        self.cookie_combo.addItem("Mozilla Firefox", "firefox")
        self.cookie_combo.addItem("Microsoft Edge", "edge")
        self.cookie_combo.addItem("Brave", "brave")
        self.cookie_combo.addItem(strings.OPT_SET_COOKIE_CUSTOM, "custom")
        layout_advanced.addWidget(self.cookie_combo)

        self.downgrade_check = QCheckBox(strings.CHK_SET_DOWNGRADE if hasattr(strings, 'CHK_SET_DOWNGRADE') else ("السماح بخفض الجودة" if strings.is_ar else "Allow Quality Downgrade"))
        layout_advanced.addWidget(self.downgrade_check)

        layout_advanced.addStretch() 

        self.reset_all_btn = QPushButton(strings.BTN_FACTORY_RESET)
        self.reset_all_btn.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        layout_advanced.addWidget(self.reset_all_btn)
        
        self.sidebar.addItem(strings.SET_TAB_ADVANCED)
        self.stacked_widget.addWidget(self.tab_advanced)

        self.location_combo.currentIndexChanged.connect(self.toggle_custom_location)
        self.custom_loc_btn.clicked.connect(self.browse_folder)
        self.speed_combo.currentIndexChanged.connect(self.toggle_custom_speed)
        self.custom_speed_unit.currentTextChanged.connect(self.on_speed_unit_changed)
        self.reset_all_btn.clicked.connect(self.factory_reset)

        self.sidebar.setCurrentRow(0)

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
        idx = self.lang_combo.findData(app_config.get("language", "system"))
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        idx = self.location_combo.findData(app_config.get("save_mode", "auto"))
        if idx >= 0: self.location_combo.setCurrentIndex(idx)

        current_font = app_config.get("font_family", "system")
        if current_font != "system":
            self.font_combo.setCurrentText(current_font)
        
        self.font_size_spin.setValue(app_config.get("font_size", 12))
        self.win_width_spin.setValue(app_config.get("window_width", 700))
        self.win_height_spin.setValue(app_config.get("window_height", 650))

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

        self.close_to_tray_check.setChecked(app_config.get("close_to_tray", True))

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
        # حفظ الخطوط
        app_config["font_family"] = self.font_combo.currentText()
        app_config["font_size"] = self.font_size_spin.value()
        app_config["window_width"] = self.win_width_spin.value()
        app_config["window_height"] = self.win_height_spin.value()

        app_config["close_to_tray"] = self.close_to_tray_check.isChecked()

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

    def connect_signals(self):
        self.theme_combo.currentIndexChanged.connect(self.save_and_apply_theme)
        self.lang_combo.currentIndexChanged.connect(self.save_data)
        self.location_combo.currentIndexChanged.connect(self.save_data)
        self.speed_combo.currentIndexChanged.connect(self.save_data)
        self.custom_speed_spin.valueChanged.connect(self.save_data)
        self.custom_speed_unit.currentTextChanged.connect(self.save_data)
        self.concurrent_spin.valueChanged.connect(self.save_data)
        self.notify_check.stateChanged.connect(self.save_data)
        self.data_saver_check.stateChanged.connect(self.save_data)
        self.thumb_check.stateChanged.connect(self.save_data)
        self.font_size_spin.valueChanged.connect(self.save_data)
        self.cookie_combo.currentIndexChanged.connect(self.on_cookie_changed)
        self.close_to_tray_check.stateChanged.connect(self.save_data)
        self.embed_subs_check.stateChanged.connect(self.save_data)
        self.prim_sub_combo.currentIndexChanged.connect(self.save_data)
        self.sec_sub_combo.currentIndexChanged.connect(self.save_data)

    def save_and_apply_theme(self):
        self.save_data()
        app = QApplication.instance()
        apply_theme(app, app_config["theme"])

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
            app_config["window_width"] = 700
            app_config["window_height"] = 650
            
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