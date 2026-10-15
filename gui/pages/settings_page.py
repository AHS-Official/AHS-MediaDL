from utils.logger import logger
import os
import sys
import json
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QLabel, QComboBox, QCheckBox, QSpinBox, QFontDialog, QMessageBox, QDoubleSpinBox, QFrame, QSplitter, QScrollArea, QFileDialog, QSlider
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFontDatabase, QIcon                                                 
from utils.locales import tr                          
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color
from gui.components.buttons import ToggleSwitch

class EngineUpdateWorker(QThread):
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        import urllib.request
        import json
        import subprocess
        import sys
        
        self.status_signal.emit(tr("engine_checking", "Checking..."))
        from managers.binary_manager import BinaryManager
        latest_version = BinaryManager.get_latest_yt_dlp_version()
        if latest_version and latest_version.lstrip('v') == str(self.current_version).lstrip('v'):
            self.finished_signal.emit(True, "up_to_date")
            return

        self.status_signal.emit(tr("engine_updating", "Updating engine..."))
        success, res = BinaryManager.update_yt_dlp_binary()
        self.finished_signal.emit(success, res)

class SettingsPage(QWidget):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.initUI()

    def create_group_box(self, title_text):
        box = QFrame()
        box.setObjectName("GroupBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(15, 15, 15, 15)
        box_layout.setSpacing(12)
        title = QLabel(title_text)
        from utils.theme import get_accent_hex
        title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {get_accent_hex()}; margin-bottom: 5px; background: transparent; border: none;")
        if not hasattr(self, 'group_box_titles'):
            self.group_box_titles = []
        self.group_box_titles.append(title)
        box_layout.addWidget(title)
        return box, box_layout

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setIcon(get_colored_icon("assets/icons/arrow-left.svg", get_current_theme_color()))
        self.btn_back.setIconSize(QSize(20, 20))
        self.btn_back.setFixedSize(35, 35)
        self.btn_back.clicked.connect(lambda: self.main_app.ui_manager.change_page(0))
        top_bar.addWidget(self.btn_back)
        self.title_lbl = QLabel(tr("settings_title"))
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_bar.addWidget(self.title_lbl)
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet("color: #e3a32e; font-weight: bold; margin-left: 15px;")
        top_bar.addWidget(self.toast_label)
        top_bar.addStretch()
        self.btn_restart = QPushButton(tr("btn_restart", "Restart Now"))
        self.btn_restart.setIcon(get_colored_icon("assets/icons/restart.svg", get_current_theme_color()))
        self.btn_restart.setIconSize(QSize(16, 16))
        self.btn_restart.setMinimumWidth(140)
        self.btn_restart.setStyleSheet("background-color: #e3a32e; color: #1e1f22; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_restart.hide()
        self.btn_restart.clicked.connect(self.restart_application)
        top_bar.addWidget(self.btn_restart)
        main_layout.addLayout(top_bar)
        self.settings_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.settings_splitter.setHandleWidth(4)
        self.categories_list = QListWidget()
        self.categories_list.setMinimumWidth(150)
        self.categories_list.setMaximumWidth(300)
        self.categories_list.setStyleSheet("""
            QListWidget { border-right: none; background: transparent; }
            QListWidget::item { padding: 8px 12px; border-radius: 5px; font-size: 13px; }
        """)
        self.item_general = QListWidgetItem(get_colored_icon("assets/icons/settings.svg", get_current_theme_color()), tr("set_general"))
        self.item_appearance = QListWidgetItem(get_colored_icon("assets/icons/palette.svg", get_current_theme_color()), tr("set_appearance"))
        self.item_downloads = QListWidgetItem(get_colored_icon("assets/icons/download.svg", get_current_theme_color()), tr("set_downloads"))
        self.item_subtitles = QListWidgetItem(get_colored_icon("assets/icons/globe.svg", get_current_theme_color()), tr("set_subtitles"))
        self.item_output = QListWidgetItem(get_colored_icon("assets/icons/package.svg", get_current_theme_color()), tr("set_output_format"))
        self.categories_list.addItem(self.item_general)
        self.categories_list.addItem(self.item_appearance)
        self.categories_list.addItem(self.item_downloads)
        self.categories_list.addItem(self.item_subtitles)
        self.categories_list.addItem(self.item_output)
        self.categories_list.setIconSize(QSize(18, 18))
        self.categories_list.currentRowChanged.connect(self.change_section)
        self.settings_splitter.addWidget(self.categories_list)
        self.sections_stack = QStackedWidget()
        self.settings_splitter.addWidget(self.sections_stack)
        self.settings_splitter.setSizes([180, 500])

        def make_scroll_section():
            """ينشئ QWidget داخل QScrollArea بحيث المحتوى لا يتقوص."""
            inner = QWidget()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(inner)
            return inner, scroll

        self.section_general,   self._scroll_general    = make_scroll_section()
        self.section_appearance, self._scroll_appearance = make_scroll_section()
        self.section_downloads, self._scroll_downloads   = make_scroll_section()
        self.section_subtitles, self._scroll_subtitles   = make_scroll_section()
        self.section_output,    self._scroll_output      = make_scroll_section()
        general_layout = QVBoxLayout(self.section_general)
        general_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        general_layout.setSpacing(15)
        general_layout.setContentsMargins(0, 0, 0, 0)
        box_gen, box_gen_layout = self.create_group_box(tr("set_general"))
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
        box_gen_layout.addLayout(lang_layout)
        # Notifications Row
        noti_layout = QHBoxLayout()
        noti_layout.setContentsMargins(0, 0, 0, 0)
        noti_layout.setSpacing(8)
        self.noti_cb = ToggleSwitch()
        self.noti_cb.setChecked(True)
        self.noti_lbl = QLabel(tr("enable_notifications", "Enable Notifications"))
        self.noti_lbl.setStyleSheet("background: transparent;")
        noti_layout.addWidget(self.noti_cb)
        noti_layout.addWidget(self.noti_lbl)
        noti_layout.addStretch()
        box_gen_layout.addLayout(noti_layout)

        # Show thumbnails Row
        show_thumbnails_layout = QHBoxLayout()
        show_thumbnails_layout.setContentsMargins(0, 0, 0, 0)
        show_thumbnails_layout.setSpacing(8)
        self.show_thumbnails_cb = ToggleSwitch()
        self.show_thumbnails_cb.setChecked(True)
        self.show_thumbnails_lbl = QLabel(tr("show_thumbnails_inspect", "Show video thumbnails while searching/inspecting"))
        self.show_thumbnails_lbl.setStyleSheet("background: transparent;")
        show_thumbnails_layout.addWidget(self.show_thumbnails_cb)
        show_thumbnails_layout.addWidget(self.show_thumbnails_lbl)
        show_thumbnails_layout.addStretch()
        box_gen_layout.addLayout(show_thumbnails_layout)
        general_layout.addWidget(box_gen)

        box_bg, box_bg_layout = self.create_group_box(tr("set_background", "Background Settings"))

        # 1. Clipboard Monitor Row (on top)
        clipboard_monitor_layout = QHBoxLayout()
        clipboard_monitor_layout.setContentsMargins(0, 0, 0, 0)
        clipboard_monitor_layout.setSpacing(8)

        self.clipboard_monitor_cb = ToggleSwitch()
        tooltip_txt = tr("clipboard_monitor_tooltip", "To monitor the clipboard when the application is closed, \"Run in background\" must be enabled.")
        self.clipboard_monitor_cb.setToolTip(tooltip_txt)
        self.clipboard_monitor_cb.toggled.connect(self.save_general_settings)

        self.clipboard_monitor_lbl = QLabel(tr("clipboard_monitor_label", "Monitor clipboard"))
        self.clipboard_monitor_lbl.setStyleSheet("background: transparent;")

        self.info_lbl = QLabel("🛈")
        self.info_lbl.setStyleSheet("color: #888888; font-size: 14px; font-weight: bold; background: transparent;")
        self.info_lbl.setToolTip(tooltip_txt)

        clipboard_monitor_layout.addWidget(self.clipboard_monitor_cb)
        clipboard_monitor_layout.addWidget(self.clipboard_monitor_lbl)
        clipboard_monitor_layout.addWidget(self.info_lbl)
        clipboard_monitor_layout.addStretch()
        box_bg_layout.addLayout(clipboard_monitor_layout)

        # 2. Auto-collect copied links Row (middle)
        auto_collect_layout = QHBoxLayout()
        auto_collect_layout.setContentsMargins(0, 0, 0, 0)
        auto_collect_layout.setSpacing(8)

        self.auto_collect_cb = ToggleSwitch()
        self.auto_collect_cb.setToolTip(tr("auto_collect_links_tooltip"))
        self.auto_collect_cb.toggled.connect(self.save_general_settings)

        self.auto_collect_lbl = QLabel(tr("auto_collect_links_label", "Auto-collect copied links"))
        self.auto_collect_lbl.setStyleSheet("background: transparent;")

        auto_collect_layout.addWidget(self.auto_collect_cb)
        auto_collect_layout.addWidget(self.auto_collect_lbl)
        auto_collect_layout.addStretch()
        box_bg_layout.addLayout(auto_collect_layout)

        # 3. Run in background Row (on bottom)
        run_bg_layout = QHBoxLayout()
        run_bg_layout.setContentsMargins(0, 0, 0, 0)
        run_bg_layout.setSpacing(8)

        self.run_bg_cb = ToggleSwitch()
        self.run_bg_lbl = QLabel(tr("run_in_background_label", "Run in background"))
        self.run_bg_lbl.setStyleSheet("background: transparent;")

        run_bg_layout.addWidget(self.run_bg_cb)
        run_bg_layout.addWidget(self.run_bg_lbl)
        run_bg_layout.addStretch()
        box_bg_layout.addLayout(run_bg_layout)

        general_layout.addWidget(box_bg)

        # 3. Download Engines & Tools Management Group Box
        box_engine, box_engine_layout = self.create_group_box(tr("set_engine_title", "Download Engines & Tools"))
        
        # --- yt-dlp Section ---
        ytdlp_title = QLabel(tr("tools_ytdlp_title", "yt-dlp Engine"), self)
        ytdlp_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        box_engine_layout.addWidget(ytdlp_title)

        from managers.binary_manager import BinaryManager
        ytdlp_ver = BinaryManager.get_local_version("yt-dlp")
        if ytdlp_ver == "Not Installed":
            ytdlp_ver = tr("tools_status_missing", "Missing")
        ytdlp_loc = BinaryManager.get_binary_path("yt-dlp") or tr("tools_status_missing", "Missing")

        ytdlp_info_layout = QHBoxLayout()
        self.lbl_ytdlp_ver = QLabel(tr("tools_current_version").format(ytdlp_ver), self)
        self.lbl_ytdlp_ver.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_ytdlp_loc = QLabel(f"({ytdlp_loc})", self)
        self.lbl_ytdlp_loc.setStyleSheet("color: #64748b; font-size: 11px;")
        ytdlp_info_layout.addWidget(self.lbl_ytdlp_ver)
        ytdlp_info_layout.addWidget(self.lbl_ytdlp_loc)
        ytdlp_info_layout.addStretch()
        box_engine_layout.addLayout(ytdlp_info_layout)

        ytdlp_action_layout = QHBoxLayout()
        self.btn_update_ytdlp = QPushButton(tr("tools_btn_check_update", "Check & Update"), self)
        self.btn_update_ytdlp.setFixedWidth(140)
        self.btn_update_ytdlp.clicked.connect(self.check_and_update_ytdlp)
        self.lbl_ytdlp_status = QLabel("", self)
        self.lbl_ytdlp_status.setStyleSheet("color: gray; font-size: 11px;")
        ytdlp_action_layout.addWidget(self.btn_update_ytdlp)
        ytdlp_action_layout.addWidget(self.lbl_ytdlp_status)
        ytdlp_action_layout.addStretch()
        box_engine_layout.addLayout(ytdlp_action_layout)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(128, 128, 128, 0.2); margin: 6px 0;")
        box_engine_layout.addWidget(sep)

        # --- FFmpeg Section ---
        ffmpeg_title = QLabel(tr("tools_ffmpeg_title", "FFmpeg & Processing Tools"), self)
        ffmpeg_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        box_engine_layout.addWidget(ffmpeg_title)

        ffmpeg_ver = BinaryManager.get_local_version("ffmpeg")
        ffmpeg_loc = BinaryManager.get_binary_path("ffmpeg") or tr("tools_status_missing", "Missing")

        ffmpeg_info_layout = QHBoxLayout()
        self.lbl_ffmpeg_ver = QLabel(tr("tools_current_version").format(ffmpeg_ver), self)
        self.lbl_ffmpeg_ver.setStyleSheet("color: gray; font-size: 11px;")
        self.lbl_ffmpeg_loc = QLabel(f"({ffmpeg_loc})", self)
        self.lbl_ffmpeg_loc.setStyleSheet("color: #64748b; font-size: 11px;")
        ffmpeg_info_layout.addWidget(self.lbl_ffmpeg_ver)
        ffmpeg_info_layout.addWidget(self.lbl_ffmpeg_loc)
        ffmpeg_info_layout.addStretch()
        box_engine_layout.addLayout(ffmpeg_info_layout)

        ffmpeg_action_layout = QHBoxLayout()
        self.btn_update_ffmpeg = QPushButton(tr("tools_btn_check_update", "Check & Update"), self)
        self.btn_update_ffmpeg.setFixedWidth(140)
        self.btn_update_ffmpeg.clicked.connect(self.check_and_update_ffmpeg)
        self.lbl_ffmpeg_status = QLabel("", self)
        self.lbl_ffmpeg_status.setStyleSheet("color: gray; font-size: 11px;")
        ffmpeg_action_layout.addWidget(self.btn_update_ffmpeg)
        ffmpeg_action_layout.addWidget(self.lbl_ffmpeg_status)
        ffmpeg_action_layout.addStretch()
        box_engine_layout.addLayout(ffmpeg_action_layout)

        general_layout.addWidget(box_engine)

        box_reset, box_reset_layout = self.create_group_box(tr("danger_zone", "Danger Zone"))
        self.btn_reset_defaults = QPushButton(tr("btn_reset_defaults", "Reset to Defaults"))
        self.btn_reset_defaults.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.btn_reset_defaults.clicked.connect(self.reset_settings_to_defaults)
        box_reset_layout.addWidget(self.btn_reset_defaults)
        general_layout.addWidget(box_reset)
        appearance_layout = QVBoxLayout(self.section_appearance)
        appearance_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        appearance_layout.setSpacing(15)
        appearance_layout.setContentsMargins(0, 0, 0, 0)
        box_theme, box_theme_layout = self.create_group_box(tr("set_appearance"))
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
        box_theme_layout.addLayout(theme_layout)
        
        accent_layout = QHBoxLayout()
        self.accent_label = QLabel(tr("accent_label", "Accent Color:"))
        self.accent_combo = QComboBox()
        self.accent_combo.setFixedWidth(180)
        self.accent_combo.addItem(tr("accent_orange", "Orange (Default)"), "orange")
        self.accent_combo.addItem(tr("accent_blue", "Blue"), "blue")
        self.accent_combo.addItem(tr("accent_purple", "Purple"), "purple")
        self.accent_combo.addItem(tr("accent_green", "Green"), "green")
        accent_layout.addWidget(self.accent_label)
        accent_layout.addWidget(self.accent_combo)
        accent_layout.addStretch()
        box_theme_layout.addLayout(accent_layout)
        font_layout = QHBoxLayout()
        self.font_label = QLabel(tr("font_label", "App Font:"))
        self.font_combo = QComboBox()
        self.font_combo.setFixedWidth(180)
        self.font_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.font_combo.setMinimumContentsLength(10)
        self.font_combo.view().setMinimumWidth(300)
        self.font_combo.addItem("System Default", "System Default")
        system_fonts = sorted(QFontDatabase.families())
        for f_name in system_fonts:
            if not f_name.startswith("@"):
                self.font_combo.addItem(f_name, f_name)
        font_layout.addWidget(self.font_label)
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        box_theme_layout.addLayout(font_layout)
        appearance_layout.addWidget(box_theme)
        box_scale, box_scale_layout = self.create_group_box(tr("scale_and_size", "Layout & Scaling"))
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
        box_scale_layout.addLayout(scale_layout)
        size_layout = QHBoxLayout()
        self.size_label = QLabel(tr("size_label", "Font Size:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(8, 30)
        self.size_slider.setFixedWidth(130)
        self.size_val_label = QLabel("12 px")
        self.size_val_label.setFixedWidth(45)
        self.size_slider.valueChanged.connect(lambda v: self.size_val_label.setText(f"{v} px"))
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_val_label)
        size_layout.addStretch()
        box_scale_layout.addLayout(size_layout)
        appearance_layout.addWidget(box_scale)
        downloads_layout = QVBoxLayout(self.section_downloads)
        downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        downloads_layout.setSpacing(18)
        downloads_layout.setContentsMargins(0, 0, 0, 0)
        box_dl_path, box_dl_path_layout = self.create_group_box(tr("set_downloads"))
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
        box_dl_path_layout.addLayout(path_layout)
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
        box_dl_path_layout.addLayout(concurrent_layout)
        downloads_layout.addWidget(box_dl_path)
        box_speed, box_speed_layout = self.create_group_box(tr("bandwidth_and_quality", "Bandwidth & Quality"))
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
        box_speed_layout.addLayout(speed_layout)
        fallback_quality_layout = QHBoxLayout()
        self.quality_fallback_cb = ToggleSwitch()
        self.quality_fallback_lbl = QLabel(tr("quality_fallback_label", "Allow lower quality fallback"))
        self.quality_fallback_lbl.setStyleSheet("background: transparent;")
        self.quality_fallback_info_icon = QLabel()
        self.quality_fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.quality_fallback_info_icon.setToolTip(tr("quality_fallback_tooltip", "If requested quality is unavailable, download next best available resolution instead of failing."))
        fallback_quality_layout.addWidget(self.quality_fallback_cb)
        fallback_quality_layout.addWidget(self.quality_fallback_lbl)
        fallback_quality_layout.addWidget(self.quality_fallback_info_icon)
        fallback_quality_layout.addStretch()
        box_speed_layout.addLayout(fallback_quality_layout)
        
        mix_limit_layout = QHBoxLayout()
        self.mix_label = QLabel(tr("mix_limit_lbl", "Maximum videos to fetch from Mix/Auto Playlists:"))
        self.mix_combo = QComboBox()
        self.mix_combo.addItems(["25", "50", "100", "200", "400", tr("mix_custom", "Custom")])
        self.mix_combo.setFixedWidth(110)
        self.mix_custom_spin = QSpinBox()
        self.mix_custom_spin.setRange(1, 500)
        self.mix_custom_spin.setFixedWidth(80)
        self.mix_custom_spin.hide()
        
        def on_mix_combo_changed():
            if self.mix_combo.currentText() == tr("mix_custom", "Custom"):
                self.mix_custom_spin.show()
            else:
                self.mix_custom_spin.hide()
            self.save_downloads_settings()
            
        self.mix_combo.currentIndexChanged.connect(on_mix_combo_changed)
        self.mix_custom_spin.valueChanged.connect(self.save_downloads_settings)
        
        mix_limit_layout.addWidget(self.mix_label)
        mix_limit_layout.addWidget(self.mix_combo)
        mix_limit_layout.addWidget(self.mix_custom_spin)
        mix_limit_layout.addStretch()
        box_speed_layout.addLayout(mix_limit_layout)
        downloads_layout.addWidget(box_speed)
        
        box_cookies, box_cookies_layout = self.create_group_box(tr("set_cookies", "Cookies"))
        cookies_src_layout = QHBoxLayout()
        self.cookies_src_label = QLabel(tr("cookies_source_label", "Cookies Source:"))
        self.cookies_src_combo = QComboBox()
        self.cookies_src_combo.addItem(tr("cookies_none", "None"), "none")
        self.cookies_src_combo.addItem("Chrome", "chrome")
        self.cookies_src_combo.addItem("Firefox", "firefox")
        self.cookies_src_combo.addItem("Edge", "edge")
        self.cookies_src_combo.addItem("Brave", "brave")
        self.cookies_src_combo.addItem("Opera", "opera")
        self.cookies_src_combo.addItem("Safari", "safari")
        self.cookies_src_combo.addItem("Vivaldi", "vivaldi")
        self.cookies_src_combo.addItem(tr("cookies_custom", "Custom Cookies File (.txt)"), "custom")
        self.cookies_src_combo.setFixedWidth(180)
        self.cookies_src_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.cookies_src_combo.currentIndexChanged.connect(self.toggle_cookies_widgets_visibility)
        
        cookies_src_layout.addWidget(self.cookies_src_label)
        cookies_src_layout.addWidget(self.cookies_src_combo)
        cookies_src_layout.addStretch()
        box_cookies_layout.addLayout(cookies_src_layout)
        
        self.cookies_path_layout = QHBoxLayout()
        self.cookies_path_label = QLabel(tr("cookies_file_label", "Cookies File:"))
        self.btn_browse_cookies = QPushButton(tr("btn_browse_cookies", "Browse"))
        self.btn_browse_cookies.setFixedWidth(150)
        self.btn_browse_cookies.clicked.connect(self.choose_cookies_file_dialog_action)
        
        self.cookies_path_layout.addWidget(self.cookies_path_label)
        self.cookies_path_layout.addWidget(self.btn_browse_cookies)
        self.cookies_path_layout.addStretch()
        box_cookies_layout.addLayout(self.cookies_path_layout)
        
        downloads_layout.addWidget(box_cookies)
        
        subtitles_layout = QVBoxLayout(self.section_subtitles)
        subtitles_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        subtitles_layout.setSpacing(18)
        subtitles_layout.setContentsMargins(0, 0, 0, 0)
        box_pref, box_pref_layout = self.create_group_box(tr("subtitle_preferences", "Subtitle Language Preferences"))
        sub_primary_layout = QHBoxLayout()
        self.sub_primary_label = QLabel(tr("sub_primary_label", "Primary Subtitle Language:"))
        self.sub_primary_combo = QComboBox()
        self.sub_primary_combo.setFixedWidth(180)
        sub_primary_layout.addWidget(self.sub_primary_label)
        sub_primary_layout.addWidget(self.sub_primary_combo)
        sub_primary_layout.addStretch()
        box_pref_layout.addLayout(sub_primary_layout)
        sub_secondary_layout = QHBoxLayout()
        self.sub_secondary_label = QLabel(tr("sub_secondary_label", "Secondary Subtitle Language:"))
        self.sub_secondary_combo = QComboBox()
        self.sub_secondary_combo.setFixedWidth(180)
        sub_secondary_layout.addWidget(self.sub_secondary_label)
        sub_secondary_layout.addWidget(self.sub_secondary_combo)
        sub_secondary_layout.addStretch()
        box_pref_layout.addLayout(sub_secondary_layout)
        subtitles_layout.addWidget(box_pref)
        box_sub_fallback, box_sub_fallback_layout = self.create_group_box(tr("subtitle_fallback_policy", "Subtitle Fallback Policy"))
        fallback_layout = QHBoxLayout()
        self.fallback_cb = ToggleSwitch()
        self.fallback_lbl = QLabel(tr("sub_fallback_label", "Download any original auto subtitle as fallback"))
        self.fallback_lbl.setStyleSheet("background: transparent;")
        self.fallback_info_icon = QLabel()
        self.fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.fallback_info_icon.setToolTip(tr("sub_fallback_info_tooltip", "In playlist mode, allows downloading any language as long as it is original (org) if preferred languages are not available"))
        fallback_layout.addWidget(self.fallback_cb)
        fallback_layout.addWidget(self.fallback_lbl)
        fallback_layout.addWidget(self.fallback_info_icon)
        fallback_layout.addStretch()
        box_sub_fallback_layout.addLayout(fallback_layout)
        subtitles_layout.addWidget(box_sub_fallback)
        output_layout = QVBoxLayout(self.section_output)
        output_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        output_layout.setSpacing(15)
        output_layout.setContentsMargins(0, 0, 0, 0)
        box_vid_out, box_vid_out_layout = self.create_group_box(tr("video_subtitle_integration", "Video & Subtitles Integration"))
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
        box_vid_out_layout.addLayout(video_container_layout)
        embed_layout = QHBoxLayout()
        self.embed_subtitles_cb = ToggleSwitch()
        self.embed_subtitles_lbl = QLabel(tr("embed_subtitles_label", "Embed"))
        self.embed_subtitles_lbl.setStyleSheet("background: transparent;")
        self.embed_subtitles_info_icon = QLabel()
        self.embed_subtitles_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.embed_subtitles_info_icon.setToolTip(tr("embed_subtitles_tooltip", "Embed subtitle track directly into the video container file."))
        
        self.autoplay_subtitles_cb = ToggleSwitch()
        self.autoplay_subtitles_lbl = QLabel(tr("autoplay_subtitles_label", "Auto-play"))
        self.autoplay_subtitles_lbl.setStyleSheet("background: transparent;")
        self.autoplay_info_icon = QLabel()
        self.autoplay_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.autoplay_info_icon.setToolTip(tr("autoplay_subtitles_tooltip", "Configure subtitle track to play automatically when opening the video."))
        
        embed_layout.addWidget(self.embed_subtitles_cb)
        embed_layout.addWidget(self.embed_subtitles_lbl)
        embed_layout.addWidget(self.embed_subtitles_info_icon)
        embed_layout.addSpacing(20)
        embed_layout.addWidget(self.autoplay_subtitles_cb)
        embed_layout.addWidget(self.autoplay_subtitles_lbl)
        embed_layout.addWidget(self.autoplay_info_icon)
        embed_layout.addStretch()
        box_vid_out_layout.addLayout(embed_layout)
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
        box_vid_out_layout.addLayout(external_sub_layout)
        output_layout.addWidget(box_vid_out)
        box_aud_out, box_aud_out_layout = self.create_group_box(tr("audio_subtitle_integration", "Audio & Subtitles Integration"))
        audio_container_layout = QHBoxLayout()
        self.audio_container_lbl = QLabel(tr("audio_container_label", "Audio Container Format:"))
        self.audio_container_combo = QComboBox()
        self.audio_container_combo.setFixedWidth(180)
        self.audio_container_combo.addItem("MP3", "mp3")
        self.audio_container_combo.addItem("M4A", "m4a")
        self.audio_container_combo.addItem("MP4", "mp4")
        self.audio_container_combo.addItem("MKV", "mkv")
        audio_container_layout.addWidget(self.audio_container_lbl)
        audio_container_layout.addWidget(self.audio_container_combo)
        audio_container_layout.addStretch()
        box_aud_out_layout.addLayout(audio_container_layout)
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
        box_aud_out_layout.addLayout(audio_sub_layout)
        output_layout.addWidget(box_aud_out)
        self.sections_stack.addWidget(self._scroll_general)
        self.sections_stack.addWidget(self._scroll_appearance)
        self.sections_stack.addWidget(self._scroll_downloads)
        self.sections_stack.addWidget(self._scroll_subtitles)
        self.sections_stack.addWidget(self._scroll_output)
        self.path_combo.currentIndexChanged.connect(self.toggle_path_widgets_visibility)
        self.speed_combo.currentIndexChanged.connect(self.toggle_speed_widgets_visibility)
        self.concurrent_combo.currentIndexChanged.connect(self.toggle_concurrent_widgets_visibility)
        self.speed_spin.valueChanged.connect(self.smart_speed_conversion_check)
        self.lang_combo.currentIndexChanged.connect(self.save_general_settings)
        self.noti_cb.toggled.connect(self.save_general_settings)
        self.show_thumbnails_cb.toggled.connect(self.save_general_settings)
        self.run_bg_cb.toggled.connect(self.save_general_settings)
        self.theme_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.accent_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.font_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.scale_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.size_slider.valueChanged.connect(self.save_appearance_settings)
        self.path_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.speed_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.speed_spin.valueChanged.connect(self.save_downloads_settings)
        self.concurrent_combo.currentIndexChanged.connect(self.save_downloads_settings)
        self.concurrent_spin.valueChanged.connect(self.save_downloads_settings)
        self.quality_fallback_cb.toggled.connect(self.save_downloads_settings)
        self.sub_primary_combo.currentIndexChanged.connect(self.save_subtitles_settings)
        self.sub_secondary_combo.currentIndexChanged.connect(self.save_subtitles_settings)
        self.fallback_cb.toggled.connect(self.save_subtitles_settings)
        self.embed_subtitles_cb.toggled.connect(self.toggle_video_sub_widgets)
        self.video_container_combo.currentIndexChanged.connect(self.save_output_settings)
        self.embed_subtitles_cb.toggled.connect(self.save_output_settings)
        self.autoplay_subtitles_cb.toggled.connect(self.save_output_settings)
        self.external_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.audio_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.audio_container_combo.currentIndexChanged.connect(self.save_output_settings)
        self.load_general_settings()
        self.load_appearance_settings()
        self.load_downloads_settings()
        self.load_subtitles_settings()
        self.load_output_settings()
        main_layout.addWidget(self.settings_splitter, 1)
        self.categories_list.setCurrentRow(0)

    def change_section(self, index):
        """ التنقل بين الأقسام الداخلية للإعدادات """
        self.sections_stack.setCurrentIndex(index)

    def load_general_settings(self):
        """ قراءة الإعدادات المحفوظة من الـ JSON وتطبيقها على الواجهة """
        self.lang_combo.blockSignals(True)
        self.noti_cb.blockSignals(True)
        self.show_thumbnails_cb.blockSignals(True)
        self.run_bg_cb.blockSignals(True)
        self.clipboard_monitor_cb.blockSignals(True)
        if hasattr(self, 'auto_collect_cb'):
            self.auto_collect_cb.blockSignals(True)
        
        mgr = self.main_app.settings_manager
        if not hasattr(self, '_setting_signal_connected'):
            mgr.setting_changed.connect(self._on_setting_changed_externally)
            self._setting_signal_connected = True

        lang = mgr.get("language", "system")
        self.initial_lang = lang                              
        idx = self.lang_combo.findData(lang)
        if idx != -1:
            self.lang_combo.setCurrentIndex(idx)
        self.noti_cb.setChecked(mgr.get("notifications", True))
        self.show_thumbnails_cb.setChecked(mgr.get("show_thumbnails", True))
        self.run_bg_cb.setChecked(mgr.get("run_in_background", False))
        self.clipboard_monitor_cb.setChecked(mgr.get("clipboard_monitor", True))
        if hasattr(self, 'auto_collect_cb'):
            self.auto_collect_cb.setChecked(mgr.get("auto_collect_links", True))
        
        self.lang_combo.blockSignals(False)
        self.noti_cb.blockSignals(False)
        self.show_thumbnails_cb.blockSignals(False)
        self.run_bg_cb.blockSignals(False)
        self.clipboard_monitor_cb.blockSignals(False)
        if hasattr(self, 'auto_collect_cb'):
            self.auto_collect_cb.blockSignals(False)

    def _on_setting_changed_externally(self, key, value):
        if key == "clipboard_monitor" and hasattr(self, 'clipboard_monitor_cb'):
            self.clipboard_monitor_cb.blockSignals(True)
            self.clipboard_monitor_cb.setChecked(bool(value))
            self.clipboard_monitor_cb.blockSignals(False)
        elif key == "auto_collect_links" and hasattr(self, 'auto_collect_cb'):
            self.auto_collect_cb.blockSignals(True)
            self.auto_collect_cb.setChecked(bool(value))
            self.auto_collect_cb.blockSignals(False)

    def save_general_settings(self):
        """ حفظ قيم اللغة والإشعارات دفعة واحدة وتحديث اختصار بدء التشغيل فقط عند تغير حالة العمل في الخلفية """
        mgr = self.main_app.settings_manager
        old_run_bg = mgr.get("run_in_background", False)
        run_bg = self.run_bg_cb.isChecked()
        
        updates = {
            "language": self.lang_combo.currentData(),
            "notifications": self.noti_cb.isChecked(),
            "show_thumbnails": self.show_thumbnails_cb.isChecked(),
            "run_in_background": run_bg,
            "clipboard_monitor": self.clipboard_monitor_cb.isChecked()
        }
        if hasattr(self, 'auto_collect_cb'):
            updates["auto_collect_links"] = self.auto_collect_cb.isChecked()
            
        mgr.set_many(updates)
        self.check_restart_required()
        if old_run_bg != run_bg:
            self.main_app.system_manager.update_startup_shortcut(run_bg)

    def choose_font_dialog(self):
        """ فتح صندوق اختيار الخطوط الخاص بالويندوز """
        current_font = self.font()
        ok, font = QFontDialog.getFont(current_font, self, tr("btn_select_font"))
        if ok:
            self.selected_font_family = font.family()
            self.btn_select_font.setText(self.selected_font_family)
            self.save_appearance_settings()                        

    def load_appearance_settings(self):
        """ قراءة الثيم، الخط، السكيل، والحجم من الـ JSON وتطبيقهم على الواجهة """
        self.theme_combo.blockSignals(True)
        self.accent_combo.blockSignals(True)
        self.font_combo.blockSignals(True)
        self.scale_combo.blockSignals(True)
        self.size_slider.blockSignals(True)
        
        mgr = self.main_app.settings_manager
        theme = mgr.get("theme", "auto")
        idx_theme = self.theme_combo.findData(theme)
        if idx_theme != -1: self.theme_combo.setCurrentIndex(idx_theme)
        
        accent = mgr.get("accent_theme", "orange")
        idx_accent = self.accent_combo.findData(accent)
        if idx_accent != -1: self.accent_combo.setCurrentIndex(idx_accent)
        
        font_family = mgr.get("font_family", "System Default")
        idx_font = self.font_combo.findData(font_family)
        if idx_font != -1: self.font_combo.setCurrentIndex(idx_font)
        
        scale = mgr.get("scaling", "auto")
        self.initial_scale = scale                                   
        idx_scale = self.scale_combo.findData(scale)
        if idx_scale != -1: self.scale_combo.setCurrentIndex(idx_scale)
        
        font_size = mgr.get("font_size", 12)
        self.size_slider.setValue(font_size)
        
        self.theme_combo.blockSignals(False)
        self.accent_combo.blockSignals(False)
        self.font_combo.blockSignals(False)
        self.scale_combo.blockSignals(False)
        self.size_slider.blockSignals(False)

    def save_appearance_settings(self):
        """ حفظ إعدادات المظهر دفعة واحدة وتطبيقها فوراً """
        mgr = self.main_app.settings_manager
        mgr.set_many({
            "theme": self.theme_combo.currentData(),
            "accent_theme": self.accent_combo.currentData(),
            "font_family": self.font_combo.currentData(),
            "scaling": self.scale_combo.currentData(),
            "font_size": self.size_slider.value()
        })
        self.check_restart_required()
        self.main_app.apply_appearance(mgr.get("theme"), mgr.get("font_family"), mgr.get("font_size"))

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
            folder_name = os.path.basename(folder) if os.path.basename(folder) else folder
            self.btn_browse_path.setText(f"📁 {folder_name}")
            self.custom_selected_path = folder                    
            self.save_downloads_settings()                          

    def toggle_speed_unit_action(self):
        """ التبديل اللحظي لعنوان زرار الوحدة بين KB و MB عند الضغط عليه """
        current_unit = self.btn_speed_unit.text()
        self.btn_speed_unit.setText("MB" if current_unit == "KB" else "KB")
        self.smart_speed_conversion_check(self.speed_spin.value())

    def smart_speed_conversion_check(self, value):
        """ 🧠 ذكاء الـ SpinBox: إذا كتب المستخدم 1024 والوحدة KB تتحول تلقائياً إلى 1 MB """
        if self.btn_speed_unit.text() == "KB" and value >= 1024:
            self.speed_spin.blockSignals(True)                                      
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
        self.quality_fallback_cb.blockSignals(True)
        self.mix_combo.blockSignals(True)
        self.mix_custom_spin.blockSignals(True)
        self.cookies_src_combo.blockSignals(True)
        
        mgr = self.main_app.settings_manager
        path_type = mgr.get("download_path_type", "downloads")
        idx = self.path_combo.findData(path_type)
        if idx != -1: self.path_combo.setCurrentIndex(idx)
        self.custom_selected_path = mgr.get("custom_path", "")
        if self.custom_selected_path:
            folder_name = os.path.basename(self.custom_selected_path) or self.custom_selected_path
            self.btn_browse_path.setText(f"📁 {folder_name}")
        speed_type = mgr.get("speed_limit_type", "unlimited")
        idx = self.speed_combo.findData(speed_type)
        if idx != -1: self.speed_combo.setCurrentIndex(idx)
        self.speed_spin.setValue(mgr.get("custom_speed_value", 100))
        self.btn_speed_unit.setText(mgr.get("custom_speed_unit", "KB"))
        concurrent_type = mgr.get("concurrent_type", "3")
        idx = self.concurrent_combo.findData(concurrent_type)
        if idx != -1: self.concurrent_combo.setCurrentIndex(idx)
        self.concurrent_spin.setValue(mgr.get("custom_concurrent_value", 3))
        self.quality_fallback_cb.setChecked(mgr.get("quality_fallback", True))
        limit_val = mgr.get("mix_playlist_limit", 50)
        str_val = str(limit_val)
        std_opts = ["25", "50", "100", "200", "400"]
        if str_val in std_opts:
            self.mix_combo.setCurrentText(str_val)
            self.mix_custom_spin.hide()
        else:
            self.mix_combo.setCurrentText(tr("mix_custom", "Custom"))
            self.mix_custom_spin.setValue(limit_val)
            self.mix_custom_spin.show()
        
        cookies_type = mgr.get("cookies_type", "none")
        idx = self.cookies_src_combo.findData(cookies_type)
        if idx != -1: self.cookies_src_combo.setCurrentIndex(idx)
        self.custom_cookies_selected_path = mgr.get("custom_cookies_path", "")
        if self.custom_cookies_selected_path:
            file_name = os.path.basename(self.custom_cookies_selected_path)
            self.btn_browse_cookies.setText(f"📄 {file_name}")
        else:
            self.btn_browse_cookies.setText(tr("btn_browse_cookies", "Browse"))
            
        self.path_combo.blockSignals(False)
        self.speed_combo.blockSignals(False)
        self.speed_spin.blockSignals(False)
        self.concurrent_combo.blockSignals(False)
        self.concurrent_spin.blockSignals(False)
        self.quality_fallback_cb.blockSignals(False)
        self.mix_combo.blockSignals(False)
        self.mix_custom_spin.blockSignals(False)
        self.cookies_src_combo.blockSignals(False)
        self.toggle_path_widgets_visibility()
        self.toggle_speed_widgets_visibility()
        self.toggle_concurrent_widgets_visibility()
        self.toggle_cookies_widgets_visibility()

    def save_downloads_settings(self):
        """ حفظ إعدادات التنزيلات دفعة واحدة في عملية كتابة واحدة """
        mgr = self.main_app.settings_manager
        mix_limit = (
            self.mix_custom_spin.value()
            if self.mix_combo.currentText() == tr("mix_custom", "Custom")
            else int(self.mix_combo.currentText())
        )
        mgr.set_many({
            "download_path_type": self.path_combo.currentData(),
            "custom_path": getattr(self, 'custom_selected_path', ''),
            "speed_limit_type": self.speed_combo.currentData(),
            "custom_speed_value": self.speed_spin.value(),
            "custom_speed_unit": self.btn_speed_unit.text(),
            "concurrent_type": self.concurrent_combo.currentData(),
            "custom_concurrent_value": self.concurrent_spin.value(),
            "quality_fallback": self.quality_fallback_cb.isChecked(),
            "mix_playlist_limit": mix_limit,
            "cookies_type": self.cookies_src_combo.currentData(),
            "custom_cookies_path": getattr(self, 'custom_cookies_selected_path', '')
        })
        self.main_app.update_app_download_rules(mgr.get_all())

    def toggle_cookies_widgets_visibility(self):
        is_custom = self.cookies_src_combo.currentData() == "custom"
        self.cookies_path_label.setVisible(is_custom)
        self.btn_browse_cookies.setVisible(is_custom)

    def choose_cookies_file_dialog_action(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("select_cookies_file", "Select Cookies File"), "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.custom_cookies_selected_path = file_path
            file_name = os.path.basename(file_path)
            self.btn_browse_cookies.setText(f"📄 {file_name}")
            self.save_downloads_settings()

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
                self.show_toast(tr("toast_restart_required", "⚠️ Restart required to apply changes!"))
        else:
            self.btn_restart.hide()
            self.toast_label.setText("")

    def show_toast(self, message):
        """ 💬 عرض توست تنبيهي مؤقت يختفي تلقائياً بعد 4 ثوانٍ من الواجهة """
        self.toast_label.setText(message)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(4000, lambda: self.toast_label.setText("") if not self.btn_restart.isHidden() else None)

    def restart_application(self):
        """ Delegate to SystemManager """
        self.main_app.system_manager.restart_application()

    def retranslate_ui(self):
        """ Dynamically retranslate all labels, buttons, and titles in SettingsPage """
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setText(tr("settings_title", "Settings"))
        if hasattr(self, 'btn_restart'):
            self.btn_restart.setText(tr("btn_restart", "Restart Now"))
            
        if hasattr(self, 'item_general'):
            self.item_general.setText(tr("set_general", "General"))
        if hasattr(self, 'item_appearance'):
            self.item_appearance.setText(tr("set_appearance", "Appearance"))
        if hasattr(self, 'item_downloads'):
            self.item_downloads.setText(tr("set_downloads", "Downloads"))
        if hasattr(self, 'item_subtitles'):
            self.item_subtitles.setText(tr("set_subtitles", "Subtitles"))
        if hasattr(self, 'item_output'):
            self.item_output.setText(tr("set_output_format", "Output Format"))

        if hasattr(self, 'lang_label'):
            self.lang_label.setText(tr("lang_label", "Language:"))
        if hasattr(self, 'noti_lbl'):
            self.noti_lbl.setText(tr("enable_notifications", "Enable Notifications"))
        if hasattr(self, 'show_thumbnails_lbl'):
            self.show_thumbnails_lbl.setText(tr("show_thumbnails_inspect", "Show video thumbnails while searching/inspecting"))
        if hasattr(self, 'clipboard_monitor_lbl'):
            self.clipboard_monitor_lbl.setText(tr("clipboard_monitor_label", "Monitor clipboard"))
        if hasattr(self, 'run_bg_lbl'):
            self.run_bg_lbl.setText(tr("run_in_background_label", "Run in background"))
        if hasattr(self, 'auto_collect_lbl'):
            self.auto_collect_lbl.setText(tr("auto_collect_links_label", "Auto-collect copied links"))

        if hasattr(self, 'theme_label'):
            self.theme_label.setText(tr("theme_label", "Theme Mode:"))
        if hasattr(self, 'accent_label'):
            self.accent_label.setText(tr("accent_label", "Accent Color:"))
        if hasattr(self, 'font_label'):
            self.font_label.setText(tr("font_label", "App Font:"))
        if hasattr(self, 'size_label'):
            self.size_label.setText(tr("size_label", "Font Size:"))
        if hasattr(self, 'scale_label'):
            self.scale_label.setText(tr("scale_label", "Scaling:"))

        if hasattr(self, 'path_label'):
            self.path_label.setText(tr("path_label", "Save Path:"))
        if hasattr(self, 'speed_label'):
            self.speed_label.setText(tr("speed_label", "Download Speed:"))
        if hasattr(self, 'concurrent_label'):
            self.concurrent_label.setText(tr("concurrent_label", "Concurrent Downloads:"))
        if hasattr(self, 'quality_fallback_lbl'):
            self.quality_fallback_lbl.setText(tr("quality_fallback_label", "Allow lower quality fallback"))

        if hasattr(self, 'sub_primary_label'):
            self.sub_primary_label.setText(tr("sub_primary_label", "Primary Subtitle Language:"))
        if hasattr(self, 'sub_secondary_label'):
            self.sub_secondary_label.setText(tr("sub_secondary_label", "Secondary Subtitle Language:"))
        if hasattr(self, 'external_sub_lbl'):
            self.external_sub_lbl.setText(tr("external_sub_format_label", "External Subtitle Format:"))

        if hasattr(self, 'video_container_lbl'):
            self.video_container_lbl.setText(tr("video_container_label", "Video Container Format:"))
        if hasattr(self, 'audio_container_lbl'):
            self.audio_container_lbl.setText(tr("audio_container_label", "Audio Container Format:"))

    def update_icon_colors(self, icon_color):
        self.btn_back.setIcon(get_colored_icon("assets/icons/arrow-left.svg", icon_color))
        self.btn_restart.setIcon(get_colored_icon("assets/icons/restart.svg", icon_color))
        self.item_general.setIcon(get_colored_icon("assets/icons/settings.svg", icon_color))
        self.item_appearance.setIcon(get_colored_icon("assets/icons/palette.svg", icon_color))
        self.item_downloads.setIcon(get_colored_icon("assets/icons/download.svg", icon_color))
        self.item_subtitles.setIcon(get_colored_icon("assets/icons/globe.svg", icon_color))
        self.item_output.setIcon(get_colored_icon("assets/icons/package.svg", icon_color))
        self.fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))
        if hasattr(self, 'quality_fallback_info_icon') and self.quality_fallback_info_icon:
            self.quality_fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))
        if hasattr(self, 'embed_subtitles_info_icon') and self.embed_subtitles_info_icon:
            self.embed_subtitles_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))

    def update_accent_colors(self):
        from utils.theme import get_accent_hex
        acc = get_accent_hex()
        if hasattr(self, 'group_box_titles'):
            for title in self.group_box_titles:
                title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {acc}; margin-bottom: 5px; background: transparent; border: none;")

    def load_subtitles_settings(self):
        """ قراءة إعدادات الترجمة وتطبيقها على الواجهة """
        mgr = self.main_app.settings_manager
        primary = mgr.get("primary_sub_lang", "ar")
        secondary = mgr.get("secondary_sub_lang", "en")
        fallback = mgr.get("download_any_sub_fallback", False)
        
        self.sub_primary_combo.blockSignals(True)
        self.sub_secondary_combo.blockSignals(True)
        self.fallback_cb.blockSignals(True)
        self.sub_primary_combo.clear()
        self.sub_secondary_combo.clear()
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
        self.fallback_cb.blockSignals(False)
        self.adjust_subtitle_combos()

    def save_subtitles_settings(self):
        """ حفظ إعدادات الترجمة دفعة واحدة """
        mgr = self.main_app.settings_manager
        mgr.set_many({
            "primary_sub_lang": self.sub_primary_combo.currentData(),
            "secondary_sub_lang": self.sub_secondary_combo.currentData(),
            "download_any_sub_fallback": self.fallback_cb.isChecked()
        })
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
        self.sub_primary_combo.clear()
        for name, code in languages:
            if code != secondary_current:
                self.sub_primary_combo.addItem(name, code)
        idx = self.sub_primary_combo.findData(primary_current)
        if idx != -1:
            self.sub_primary_combo.setCurrentIndex(idx)
        else:
            self.sub_primary_combo.setCurrentIndex(0)
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
        """ 👁️ Hide/show external format widgets and enable/disable autoplay """
        is_embedded = self.embed_subtitles_cb.isChecked()
        self.autoplay_subtitles_cb.setEnabled(is_embedded)
        self.autoplay_info_icon.setEnabled(is_embedded)
        self.external_sub_lbl.setVisible(not is_embedded)
        self.external_sub_combo.setVisible(not is_embedded)

    def toggle_audio_sub_widgets(self):
        """ دالة باقية للتوافق — الـ audio sub widgets دائماً ظاهرة الآن """
        pass

    def load_output_settings(self):
        """ قراءة تفضيلات صيغة الملف الخارج والترجمات المتقدمة """
        mgr = self.main_app.settings_manager
        video_container = mgr.get("video_container", "mp4")
        embed_subtitles = mgr.get("embed_subtitles", False)
        autoplay_subtitles = mgr.get("autoplay_subtitles", False)
        external_sub_format = mgr.get("external_sub_format", "srt")
        audio_sub_format = mgr.get("audio_sub_format", "lrc")
        audio_container = mgr.get("audio_container", "mp3")
        
        self.video_container_combo.blockSignals(True)
        self.embed_subtitles_cb.blockSignals(True)
        self.autoplay_subtitles_cb.blockSignals(True)
        self.external_sub_combo.blockSignals(True)
        self.audio_sub_combo.blockSignals(True)
        self.audio_container_combo.blockSignals(True)
        idx = self.video_container_combo.findData(video_container)
        if idx != -1: self.video_container_combo.setCurrentIndex(idx)
        self.embed_subtitles_cb.setChecked(embed_subtitles)
        self.autoplay_subtitles_cb.setChecked(autoplay_subtitles)
        idx = self.external_sub_combo.findData(external_sub_format)
        if idx != -1: self.external_sub_combo.setCurrentIndex(idx)
        idx = self.audio_sub_combo.findData(audio_sub_format)
        if idx != -1: self.audio_sub_combo.setCurrentIndex(idx)
        idx = self.audio_container_combo.findData(audio_container)
        if idx != -1: self.audio_container_combo.setCurrentIndex(idx)
        self.video_container_combo.blockSignals(False)
        self.embed_subtitles_cb.blockSignals(False)
        self.autoplay_subtitles_cb.blockSignals(False)
        self.external_sub_combo.blockSignals(False)
        self.audio_sub_combo.blockSignals(False)
        self.audio_container_combo.blockSignals(False)
        self.toggle_video_sub_widgets()

    def save_output_settings(self):
        """ حفظ تفضيلات صيغة الملف الخارج والترجمات المتقدمة دفعة واحدة """
        mgr = self.main_app.settings_manager
        mgr.set_many({
            "video_container": self.video_container_combo.currentData(),
            "embed_subtitles": self.embed_subtitles_cb.isChecked(),
            "autoplay_subtitles": self.autoplay_subtitles_cb.isChecked(),
            "external_sub_format": self.external_sub_combo.currentData(),
            "audio_sub_format": self.audio_sub_combo.currentData(),
            "audio_container": self.audio_container_combo.currentData()
        })

    def reset_settings_to_defaults(self):
        confirm = QMessageBox.question(
            self,
            tr("confirm_reset_defaults_title", "Reset Settings"),
            tr("confirm_reset_defaults_msg", "Are you sure you want to reset all settings to their default values?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.main_app.settings_manager.reset_to_defaults()
            default_data = self.main_app.settings_manager.get_all()
            
            self.load_general_settings()
            self.load_appearance_settings()
            self.load_downloads_settings()
            self.load_subtitles_settings()
            self.load_output_settings()
            
            self.main_app.apply_appearance(default_data["theme"], default_data["font_family"], default_data["font_size"])
            self.main_app.update_app_download_rules(default_data)
            QMessageBox.information(self, tr("settings_title"), tr("toast_restart_required", "⚠️ Restart required to apply some changes!"))
            self.check_restart_required()

    def _guard_active_downloads(self) -> bool:
        """Returns True if safe to proceed, False if active downloads prevent updating."""
        if hasattr(self.main_app, 'download_manager'):
            active = getattr(self.main_app.download_manager, 'active_workers', [])
            if active and len(active) > 0:
                QMessageBox.warning(
                    self,
                    tr("settings_title"),
                    tr("tools_active_downloads_warn", "Active downloads running! Please pause or wait.")
                )
                return False
        return True

    def check_and_update_engine(self):
        self.check_and_update_ytdlp()

    def check_and_update_ytdlp(self):
        if not self._guard_active_downloads():
            return
        self.btn_update_ytdlp.setEnabled(False)
        self.lbl_ytdlp_status.setText(tr("engine_checking", "Checking..."))
        self.lbl_ytdlp_status.setStyleSheet("color: gray;")
        
        from managers.binary_manager import BinaryDownloaderWorker
        self.ytdlp_worker = BinaryDownloaderWorker(download_yt_dlp=True, download_ffmpeg=False, parent=self)
        self.ytdlp_worker.progress_signal.connect(lambda pct, s: self.lbl_ytdlp_status.setText(f"{s} ({pct}%)"))
        self.ytdlp_worker.finished_signal.connect(self.on_ytdlp_update_finished)
        self.ytdlp_worker.start()

    def on_ytdlp_update_finished(self, success, result):
        self.btn_update_ytdlp.setEnabled(True)
        from managers.binary_manager import BinaryManager
        if success:
            ver = BinaryManager.get_local_version("yt-dlp")
            self.lbl_ytdlp_ver.setText(tr("tools_current_version").format(ver))
            loc = BinaryManager.get_binary_path("yt-dlp") or "bin"
            self.lbl_ytdlp_loc.setText(f"({loc})")
            self.lbl_ytdlp_status.setText(tr("engine_update_success", "Successfully updated to version {}!").format(ver))
            self.lbl_ytdlp_status.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lbl_ytdlp_status.setText(tr("engine_update_fail", "Update failed: {}").format(result[:50]))
            self.lbl_ytdlp_status.setStyleSheet("color: #ef4444;")

    def check_and_update_ffmpeg(self):
        if not self._guard_active_downloads():
            return
        self.btn_update_ffmpeg.setEnabled(False)
        self.lbl_ffmpeg_status.setText(tr("engine_checking", "Checking..."))
        self.lbl_ffmpeg_status.setStyleSheet("color: gray;")

        from managers.binary_manager import BinaryDownloaderWorker
        self.ffmpeg_worker = BinaryDownloaderWorker(download_yt_dlp=False, download_ffmpeg=True, parent=self)
        self.ffmpeg_worker.progress_signal.connect(lambda pct, s: self.lbl_ffmpeg_status.setText(f"{s} ({pct}%)"))
        self.ffmpeg_worker.finished_signal.connect(self.on_ffmpeg_update_finished)
        self.ffmpeg_worker.start()

    def on_ffmpeg_update_finished(self, success, result):
        self.btn_update_ffmpeg.setEnabled(True)
        from managers.binary_manager import BinaryManager
        if success:
            ver = BinaryManager.get_local_version("ffmpeg")
            self.lbl_ffmpeg_ver.setText(tr("tools_current_version").format(ver))
            loc = BinaryManager.get_binary_path("ffmpeg") or "bin"
            self.lbl_ffmpeg_loc.setText(f"({loc})")
            self.lbl_ffmpeg_status.setText(tr("engine_update_success", "Successfully updated to version {}!").format(ver))
            self.lbl_ffmpeg_status.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lbl_ffmpeg_status.setText(tr("engine_update_fail", "Update failed: {}").format(result[:50]))
            self.lbl_ffmpeg_status.setStyleSheet("color: #ef4444;")
