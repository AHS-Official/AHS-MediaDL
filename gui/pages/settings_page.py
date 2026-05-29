import os
import sys
import json
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QLabel, QComboBox, QCheckBox, QSpinBox, QFontDialog, QMessageBox, QDoubleSpinBox, QFrame, QSplitter
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFontDatabase, QIcon                                                 
from utils.locales import tr                          
from utils.helpers import resource_path, get_colored_icon, get_current_theme_color
from gui.widgets import ToggleSwitch

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
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff5e3a; margin-bottom: 5px; background: transparent; border: none;")
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
        self.section_general = QWidget()
        self.section_appearance = QWidget()
        self.section_downloads = QWidget()
        self.section_subtitles = QWidget()
        self.section_output = QWidget()
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
        self.noti_cb = QCheckBox(tr("enable_notifications", "Enable Notifications"))
        self.noti_cb.setChecked(True)
        box_gen_layout.addWidget(self.noti_cb)
        self.run_bg_cb = QCheckBox(tr("run_in_background_label", "Run in background / Close to system tray"))
        self.clipboard_monitor_cb = QCheckBox(tr("clipboard_monitor_label", "Monitor clipboard for YouTube links"))
        self.clipboard_monitor_cb.setStyleSheet("margin-left: 20px;" if self.layoutDirection() != Qt.LayoutDirection.RightToLeft else "margin-right: 20px;")
        self.run_bg_cb.toggled.connect(self.toggle_clipboard_monitor_visibility)
        box_gen_layout.addWidget(self.run_bg_cb)
        box_gen_layout.addWidget(self.clipboard_monitor_cb)
        general_layout.addWidget(box_gen)
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
        self.size_spin = QSpinBox()
        self.size_spin.setFixedWidth(180)
        self.size_spin.setRange(8, 30)
        size_layout.addWidget(self.size_label)
        size_layout.addWidget(self.size_spin)
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
        self.quality_fallback_cb = QCheckBox(tr("quality_fallback_label", "Allow lower quality fallback"))
        self.quality_fallback_info_icon = QLabel()
        self.quality_fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.quality_fallback_info_icon.setToolTip(tr("quality_fallback_tooltip", "If requested quality is unavailable, download next best available resolution instead of failing."))
        fallback_quality_layout.addWidget(self.quality_fallback_cb)
        fallback_quality_layout.addWidget(self.quality_fallback_info_icon)
        fallback_quality_layout.addStretch()
        box_speed_layout.addLayout(fallback_quality_layout)
        downloads_layout.addWidget(box_speed)
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
        self.fallback_cb = QCheckBox(tr("sub_fallback_label", "Download any original auto subtitle as fallback"))
        self.fallback_info_icon = QLabel()
        self.fallback_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.fallback_info_icon.setToolTip(tr("sub_fallback_info_tooltip", "In playlist mode, allows downloading any language as long as it is original (org) if preferred languages are not available"))
        fallback_layout.addWidget(self.fallback_cb)
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
        self.embed_subtitles_cb = QCheckBox(tr("embed_subtitles_label", "Embed subtitles inside video container"))
        self.embed_subtitles_info_icon = QLabel()
        self.embed_subtitles_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16))
        self.embed_subtitles_info_icon.setToolTip(tr("embed_subtitles_tooltip", "Embed subtitle track directly into the video container file."))
        embed_layout.addWidget(self.embed_subtitles_cb)
        embed_layout.addWidget(self.embed_subtitles_info_icon)
        embed_layout.addStretch()
        box_vid_out_layout.addLayout(embed_layout)
        autoplay_layout = QHBoxLayout()
        self.autoplay_subtitles_lbl = QLabel(tr("autoplay_subtitles_label", "Enable auto-play for embedded subtitles"))
        self.autoplay_subtitles_cb = ToggleSwitch()
        autoplay_layout.addWidget(self.autoplay_subtitles_lbl)
        autoplay_layout.addWidget(self.autoplay_subtitles_cb)
        autoplay_layout.addStretch()
        box_vid_out_layout.addLayout(autoplay_layout)
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
        self.audio_container_combo.addItem("M4A (Default)", "m4a")
        self.audio_container_combo.addItem("MP3", "mp3")
        self.audio_container_combo.addItem("MP4", "mp4")
        self.audio_container_combo.addItem("MKV", "mkv")
        audio_container_layout.addWidget(self.audio_container_lbl)
        audio_container_layout.addWidget(self.audio_container_combo)
        audio_container_layout.addStretch()
        box_aud_out_layout.addLayout(audio_container_layout)
        self.embed_audio_sub_cb = QCheckBox(tr("embed_audio_sub_label", "Embed subtitles inside audio file"))
        box_aud_out_layout.addWidget(self.embed_audio_sub_cb)
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
        self.sections_stack.addWidget(self.section_general)
        self.sections_stack.addWidget(self.section_appearance)
        self.sections_stack.addWidget(self.section_downloads)
        self.sections_stack.addWidget(self.section_subtitles)
        self.sections_stack.addWidget(self.section_output)
        self.path_combo.currentIndexChanged.connect(self.toggle_path_widgets_visibility)
        self.speed_combo.currentIndexChanged.connect(self.toggle_speed_widgets_visibility)
        self.concurrent_combo.currentIndexChanged.connect(self.toggle_concurrent_widgets_visibility)
        self.speed_spin.valueChanged.connect(self.smart_speed_conversion_check)
        self.lang_combo.currentIndexChanged.connect(self.save_general_settings)
        self.noti_cb.toggled.connect(self.save_general_settings)
        self.run_bg_cb.toggled.connect(self.save_general_settings)
        self.clipboard_monitor_cb.toggled.connect(self.save_general_settings)
        self.theme_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.font_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.scale_combo.currentIndexChanged.connect(self.save_appearance_settings)
        self.size_spin.valueChanged.connect(self.save_appearance_settings)
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
        self.embed_audio_sub_cb.toggled.connect(self.toggle_audio_sub_widgets)
        self.video_container_combo.currentIndexChanged.connect(self.save_output_settings)
        self.embed_subtitles_cb.toggled.connect(self.save_output_settings)
        self.autoplay_subtitles_cb.toggled.connect(self.save_output_settings)
        self.external_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.audio_sub_combo.currentIndexChanged.connect(self.save_output_settings)
        self.embed_audio_sub_cb.toggled.connect(self.save_output_settings)
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

    def toggle_clipboard_monitor_visibility(self, checked):
        self.clipboard_monitor_cb.setVisible(checked)

    def load_general_settings(self):
        """ قراءة الإعدادات المحفوظة من الـ JSON وتطبيقها على الواجهة """
        self.lang_combo.blockSignals(True)
        self.noti_cb.blockSignals(True)
        self.run_bg_cb.blockSignals(True)
        self.clipboard_monitor_cb.blockSignals(True)
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lang = data.get("language", "system")
                    self.initial_lang = lang                              
                    idx = self.lang_combo.findData(lang)
                    if idx != -1:
                        self.lang_combo.setCurrentIndex(idx)
                    self.noti_cb.setChecked(data.get("notifications", True))
                    self.run_bg_cb.setChecked(data.get("run_in_background", False))
                    self.clipboard_monitor_cb.setChecked(data.get("clipboard_monitor", False))
            except Exception:
                pass
        self.lang_combo.blockSignals(False)
        self.noti_cb.blockSignals(False)
        self.run_bg_cb.blockSignals(False)
        self.clipboard_monitor_cb.blockSignals(False)
        self.toggle_clipboard_monitor_visibility(self.run_bg_cb.isChecked())

    def save_general_settings(self):
        """ حفظ قيم اللغة والإشعارات فوراً داخل ملف settings.json دون مسح البيانات القديمة """
        data = {}
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        data["language"] = self.lang_combo.currentData()
        data["notifications"] = self.noti_cb.isChecked()
        data["run_in_background"] = self.run_bg_cb.isChecked()
        data["clipboard_monitor"] = self.clipboard_monitor_cb.isChecked()
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.check_restart_required()
            if not data["run_in_background"]:
                from PyQt6.QtNetwork import QLocalSocket
                socket = QLocalSocket()
                socket.connectToServer("AHS_MediaDL_Listener_Server")
                if socket.waitForConnected(300):
                    socket.write(b"QUIT")
                    socket.waitForBytesWritten(500)
                    socket.disconnectFromServer()
        except Exception:
            pass

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
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    theme = data.get("theme", "auto")
                    idx_theme = self.theme_combo.findData(theme)
                    if idx_theme != -1: self.theme_combo.setCurrentIndex(idx_theme)
                    font_family = data.get("font_family", "System Default")
                    idx_font = self.font_combo.findData(font_family)
                    if idx_font != -1: self.font_combo.setCurrentIndex(idx_font)
                    scale = data.get("scaling", "auto")
                    self.initial_scale = scale                                   
                    idx_scale = self.scale_combo.findData(scale)
                    if idx_scale != -1: self.scale_combo.setCurrentIndex(idx_scale)
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
            self.check_restart_required()
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
        if os.path.exists(self.main_app.settings_file):
            try:
                with open(self.main_app.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    path_type = data.get("download_path_type", "downloads")
                    idx = self.path_combo.findData(path_type)
                    if idx != -1: self.path_combo.setCurrentIndex(idx)
                    self.custom_selected_path = data.get("custom_path", "")
                    if self.custom_selected_path:
                        folder_name = os.path.basename(self.custom_selected_path) or self.custom_selected_path
                        self.btn_browse_path.setText(f"📁 {folder_name}")
                    speed_type = data.get("speed_limit_type", "unlimited")
                    idx = self.speed_combo.findData(speed_type)
                    if idx != -1: self.speed_combo.setCurrentIndex(idx)
                    self.speed_spin.setValue(data.get("custom_speed_value", 100))
                    self.btn_speed_unit.setText(data.get("custom_speed_unit", "KB"))
                    concurrent_type = data.get("concurrent_type", "3")
                    idx = self.concurrent_combo.findData(concurrent_type)
                    if idx != -1: self.concurrent_combo.setCurrentIndex(idx)
                    self.concurrent_spin.setValue(data.get("custom_concurrent_value", 3))
                    self.quality_fallback_cb.setChecked(data.get("quality_fallback", True))
            except Exception:
                pass
        self.path_combo.blockSignals(False)
        self.speed_combo.blockSignals(False)
        self.speed_spin.blockSignals(False)
        self.concurrent_combo.blockSignals(False)
        self.concurrent_spin.blockSignals(False)
        self.quality_fallback_cb.blockSignals(False)
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
        data["quality_fallback"] = self.quality_fallback_cb.isChecked()
        try:
            with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
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
        """ ⚡️ الدالة السحرية لإعادة تشغيل البرنامج بالكامل فوراً بنظافة وبدون مشاكل """
        import sys
        import os
        import subprocess
        from PyQt6.QtWidgets import QApplication
        executable = sys.executable
        args = sys.argv
        base_exec = os.path.basename(executable).lower()
        is_python = "python" in base_exec or base_exec in ["py.exe", "py"]
        if is_python:
            cmd = [executable] + args
        else:
            cmd = [executable] + args[1:]
        try:
            subprocess.Popen(cmd)
        except Exception:
            pass
        QApplication.quit()

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
        self.sub_primary_combo.blockSignals(True)
        self.sub_secondary_combo.blockSignals(True)
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
        """ 👁️ Enable/disable external format widgets rather than hiding them, keeping layout stable """
        is_embedded = self.embed_subtitles_cb.isChecked()
        self.autoplay_subtitles_lbl.setEnabled(is_embedded)
        self.autoplay_subtitles_cb.setEnabled(is_embedded)
        self.external_sub_lbl.setEnabled(not is_embedded)
        self.external_sub_combo.setEnabled(not is_embedded)

    def toggle_audio_sub_widgets(self):
        """ 👁️ Hide/show external audio sub widgets based on embed checkbox """
        is_embedded = self.embed_audio_sub_cb.isChecked()
        self.audio_sub_lbl.setVisible(not is_embedded)
        self.audio_sub_combo.setVisible(not is_embedded)

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

    def reset_settings_to_defaults(self):
        confirm = QMessageBox.question(
            self,
            tr("confirm_reset_defaults_title", "Reset Settings"),
            tr("confirm_reset_defaults_msg", "Are you sure you want to reset all settings to their default values?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            default_data = {
                "last_save_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
                "language": "system",
                "notifications": True,
                "theme": "auto",
                "font_family": "System Default",
                "scaling": "auto",
                "font_size": 12,
                "download_path_type": "downloads",
                "custom_path": "",
                "speed_limit_type": "unlimited",
                "custom_speed_value": 100,
                "custom_speed_unit": "KB",
                "concurrent_type": "3",
                "custom_concurrent_value": 3,
                "primary_sub_lang": "ar",
                "secondary_sub_lang": "en",
                "download_any_sub_fallback": False,
                "video_container": "mp4",
                "embed_subtitles": True,
                "autoplay_subtitles": True,
                "external_sub_format": "srt",
                "audio_sub_format": "lrc",
                "embed_audio_sub": False,
                "audio_container": "m4a",
                "quality_fallback": True,
                "first_launch": True,
                "run_in_background": False,
                "clipboard_monitor": False
            }
            try:
                with open(self.main_app.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
                self.load_general_settings()
                self.load_appearance_settings()
                self.load_downloads_settings()
                self.load_subtitles_settings()
                self.load_output_settings()
                self.main_app.apply_appearance(default_data["theme"], default_data["font_family"], default_data["font_size"])
                self.main_app.update_app_download_rules(default_data)
                QMessageBox.information(self, tr("settings_title"), tr("toast_restart_required", "⚠️ Restart required to apply some changes!"))
                self.check_restart_required()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to reset settings: {e}")
