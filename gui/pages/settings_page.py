"""
Settings Page — Restructured settings with TreeView navigation, auto-save, live styling, and tooltips.
"""
import os
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame, 
                              QLabel, QComboBox, QCheckBox, QSpinBox, 
                              QTreeWidget, QTreeWidgetItem, QStackedWidget, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontDatabase, QIcon
from data.settings import app_config, save_settings, DEFAULT_DOWNLOAD_PATH
from utils import helpers


class SettingsPage(QWidget):
    restart_required_signal = pyqtSignal(str) # Emits the message when restart is needed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.startup_values = {}
        self.is_loading = True
        
        self.init_ui()
        self.load_settings_data()
        self.capture_startup_values()
        self.is_loading = False
        
        # Connect change signals for Auto-Save after loading
        self.connect_signals()

    def init_ui(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        
        # Horizontal Split: [ Left TreeView Category Select | Right Settings Stack ]
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # 1. LEFT TREEVIEW CATEGORY SELECT
        self.tree_frame = QFrame()
        self.tree_frame.setObjectName("GlowCard")
        self.tree_frame.setFixedWidth(220)
        tree_layout = QVBoxLayout(self.tree_frame)
        tree_layout.setContentsMargins(10, 15, 10, 15)
        
        tree_header = QFrame()
        tree_header_layout = QHBoxLayout(tree_header)
        tree_header_layout.setContentsMargins(0, 0, 0, 0)
        tree_header_layout.setSpacing(8)
        
        self.header_icon = QLabel()
        self.header_icon.setPixmap(helpers.get_theme_icon("folder.svg", 18).pixmap(18, 18))
        
        header_text = QLabel(helpers.BTN_SETTINGS)
        header_text.setObjectName("heading")
        header_text.setStyleSheet("font-size: 12pt; font-weight: 700; color: #7c6af7;")
        
        tree_header_layout.addWidget(self.header_icon)
        tree_header_layout.addWidget(header_text)
        tree_header_layout.addStretch()
        
        tree_layout.addWidget(tree_header)
        
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setIndentation(15)
        self.category_tree.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                font-size: 11pt;
            }
            QTreeWidget::item {
                padding: 10px 6px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QTreeWidget::item:selected {
                background-color: rgba(124, 106, 247, 0.15);
                color: #9d8ff9;
                font-weight: bold;
            }
        """)
        
        # Populate Category Tree with SVG Icons (Restructured into 3 panels)
        self.item_appearance = QTreeWidgetItem(self.category_tree, [helpers.SET_TAB_APPEARANCE])
        self.item_appearance.setIcon(0, helpers.get_theme_icon("palette.svg"))
        
        self.item_downloads  = QTreeWidgetItem(self.category_tree, [helpers.SET_TAB_DL])
        self.item_downloads.setIcon(0, helpers.get_theme_icon("inbox.svg"))
        
        self.item_subtitles  = QTreeWidgetItem(self.category_tree, [helpers.SET_TAB_SUBTITLES])
        self.item_subtitles.setIcon(0, helpers.get_theme_icon("clapperboard.svg"))
        
        self.category_tree.addTopLevelItem(self.item_appearance)
        self.category_tree.addTopLevelItem(self.item_downloads)
        self.category_tree.addTopLevelItem(self.item_subtitles)
        
        self.category_tree.currentItemChanged.connect(self.on_category_changed)
        tree_layout.addWidget(self.category_tree)
        
        main_layout.addWidget(self.tree_frame)
        
        # 2. RIGHT SETTINGS PANELS (Stacked Widget inside Scroll Area)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        # Fix horizontal scrollbar bug
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")
        
        # Build 3 Redesigned Settings Panels
        self.create_appearance_panel()
        self.create_downloads_panel()
        self.create_subtitles_panel()
        
        self.scroll_area.setWidget(self.stacked_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)
        
        # Default selection
        self.category_tree.setCurrentItem(self.item_appearance)

    def on_category_changed(self, current, previous):
        if not current:
            return
        if current == self.item_appearance:
            self.stacked_widget.setCurrentIndex(0)
        elif current == self.item_downloads:
            self.stacked_widget.setCurrentIndex(1)
        elif current == self.item_subtitles:
            self.stacked_widget.setCurrentIndex(2)

    def create_section_header(self, icon_name, text):
        header = QFrame()
        header.setObjectName("SectionHeaderFrame")
        header.setStyleSheet("border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 5px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 8)
        h_layout.setSpacing(10)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(helpers.get_theme_icon(icon_name, 20).pixmap(20, 20))
        
        text_lbl = QLabel(text)
        text_lbl.setObjectName("heading")
        text_lbl.setStyleSheet("font-size: 14pt; font-weight: 700; background: transparent; border: none;")
        
        h_layout.addWidget(icon_lbl)
        h_layout.addWidget(text_lbl)
        h_layout.addStretch()
        
        # Save attributes for dynamic live-theme refreshes
        header.icon_lbl = icon_lbl
        header.icon_name = icon_name
        if not hasattr(self, 'section_headers'):
            self.section_headers = []
        self.section_headers.append(header)
        
        return header

    # ──────────────────────────────────────────────
    #  PANEL CREATION
    # ──────────────────────────────────────────────

    def create_appearance_panel(self):
        panel = QFrame()
        panel.setObjectName("GlowCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = self.create_section_header("palette.svg", helpers.SET_TAB_APPEARANCE)
        layout.addWidget(title)
        
        # 1. Theme
        layout.addWidget(QLabel(helpers.LBL_THEME))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(helpers.THEME_AUTO, "auto")
        self.theme_combo.addItem(helpers.THEME_LIGHT, "light")
        self.theme_combo.addItem(helpers.THEME_DARK, "dark")
        layout.addWidget(self.theme_combo)
        
        # 2. Language
        layout.addWidget(QLabel(helpers.LBL_LANG))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(helpers.LANG_SYS, "system")
        self.lang_combo.addItem(helpers.LANG_EN, "en")
        self.lang_combo.addItem(helpers.LANG_AR, "ar")
        layout.addWidget(self.lang_combo)
        
        # 3. Dynamic Font Family Listing
        layout.addWidget(QLabel(helpers.SET_FONT_LABEL))
        self.font_combo = QComboBox()
        self.font_combo.addItem("System Default", "System Default")
        
        # Load all installed system fonts
        installed_fonts = QFontDatabase.families()
        for font in installed_fonts:
            self.font_combo.addItem(font, font)
        layout.addWidget(self.font_combo)
        
        # 4. Text Size Control (New!)
        layout.addWidget(QLabel(helpers.LBL_FONT_SIZE))
        self.font_size_combo = QComboBox()
        for size in range(10, 19):
            self.font_size_combo.addItem(f"{size} pt", size)
        layout.addWidget(self.font_size_combo)
        
        # 5. UI Scaling Options
        layout.addWidget(QLabel(helpers.SET_SCALE_LABEL))
        self.scale_combo = QComboBox()
        self.scale_combo.addItem("System Default (Auto)", "System Default (Auto)")
        self.scale_combo.addItem("100%", "100%")
        self.scale_combo.addItem("125%", "125%")
        self.scale_combo.addItem("150%", "150%")
        self.scale_combo.addItem("200%", "200%")
        layout.addWidget(self.scale_combo)
        
        # 6. Checkboxes
        self.notify_check = QCheckBox(helpers.CHK_NOTIFY)
        self.thumb_check = QCheckBox(helpers.CHK_THUMB)
        layout.addWidget(self.notify_check)
        layout.addWidget(self.thumb_check)
        
        layout.addStretch()
        self.stacked_widget.addWidget(panel)

    def create_downloads_panel(self):
        panel = QFrame()
        panel.setObjectName("GlowCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = self.create_section_header("inbox.svg", helpers.SET_TAB_DL)
        layout.addWidget(title)
        
        # Save mode
        layout.addWidget(QLabel(helpers.LBL_DL_LOC))
        loc_layout = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItem(helpers.LOC_ASK, "ask")
        self.location_combo.addItem(helpers.LOC_AUTO, "auto")
        self.location_combo.addItem(helpers.LOC_CUSTOM, "custom")
        loc_layout.addWidget(self.location_combo)

        from PyQt6.QtWidgets import QPushButton
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        self.custom_loc_btn = QPushButton("  " + helpers.BTN_BROWSE)
        self.custom_loc_btn.setIcon(QIcon(os.path.join(assets_dir, "icons", "folder.svg")))
        self.custom_loc_btn.setStyleSheet("background-color: #34495e; color: white; border-radius: 6px; padding: 6px 12px;")
        self.custom_loc_btn.hide()
        self.custom_loc_btn.clicked.connect(self.browse_folder)
        loc_layout.addWidget(self.custom_loc_btn)
        layout.addLayout(loc_layout)
        self.location_combo.currentIndexChanged.connect(self.toggle_custom_location)

        # Speed limits
        layout.addWidget(QLabel(helpers.LBL_SPEED))
        speed_layout = QHBoxLayout()
        self.speed_combo = QComboBox()
        self.speed_combo.addItem(helpers.SPEED_NO_LIMIT, "0")
        self.speed_combo.addItem("500 KB/s", "500K")
        self.speed_combo.addItem("1 MB/s", "1M")
        self.speed_combo.addItem("2 MB/s", "2M")
        self.speed_combo.addItem(helpers.LOC_CUSTOM, "custom")

        self.custom_speed_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_speed_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_speed_spin = QSpinBox()
        self.custom_speed_spin.setRange(1, 50000)
        self.custom_speed_unit = QComboBox()
        self.custom_speed_unit.addItems(["KB/s", "MB/s"])
        self.custom_speed_unit.currentTextChanged.connect(self.on_speed_unit_changed)
        custom_layout.addWidget(self.custom_speed_spin)
        custom_layout.addWidget(self.custom_speed_unit)
        self.custom_speed_widget.hide()

        speed_layout.addWidget(self.speed_combo)
        speed_layout.addWidget(self.custom_speed_widget)
        layout.addLayout(speed_layout)
        self.speed_combo.currentIndexChanged.connect(self.toggle_custom_speed)

        # Concurrent downloads
        layout.addWidget(QLabel(helpers.LBL_CONCURRENT))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        layout.addWidget(self.concurrent_spin)

        self.data_saver_check = QCheckBox(helpers.CHK_DATA_SAVER)
        layout.addWidget(self.data_saver_check)
        
        # Account Cookies
        layout.addWidget(QLabel(helpers.LBL_COOKIES))
        self.cookie_combo = QComboBox()
        self.cookie_combo.addItem(helpers.COOKIE_NONE, "none")
        self.cookie_combo.addItem("Google Chrome", "chrome")
        self.cookie_combo.addItem("Mozilla Firefox", "firefox")
        self.cookie_combo.addItem("Microsoft Edge", "edge")
        self.cookie_combo.addItem("Brave", "brave")
        layout.addWidget(self.cookie_combo)

        # Auto-Downgrade Option (Moved here from subtitles with info tooltip)
        downgrade_layout = QHBoxLayout()
        downgrade_layout.setContentsMargins(0, 5, 0, 0)
        self.downgrade_check = QCheckBox(helpers.CHK_ALLOW_DOWNGRADE)
        downgrade_layout.addWidget(self.downgrade_check)
        
        self.info_icon = QLabel()
        self.info_icon.setPixmap(helpers.get_theme_icon("info.svg", 16).pixmap(16, 16))
        self.info_icon.setToolTip(helpers.LBL_DOWNGRADE_INFO)
        self.info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        downgrade_layout.addWidget(self.info_icon)
        downgrade_layout.addStretch()
        layout.addLayout(downgrade_layout)

        layout.addStretch()
        self.stacked_widget.addWidget(panel)

    def create_subtitles_panel(self):
        panel = QFrame()
        panel.setObjectName("GlowCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = self.create_section_header("clapperboard.svg", helpers.SET_TAB_SUBTITLES)
        layout.addWidget(title)

        # 1. Primary and Secondary Languages (Smart Filters)
        layout.addWidget(QLabel(helpers.LBL_PRIM_SUB))
        self.primary_sub_combo = QComboBox()
        self.primary_sub_combo.addItem("العربية" if helpers.is_ar else "Arabic", "ar")
        self.primary_sub_combo.addItem("الإنجليزية" if helpers.is_ar else "English", "en")
        self.primary_sub_combo.addItem("الفرنسية" if helpers.is_ar else "French", "fr")
        self.primary_sub_combo.addItem("الألمانية" if helpers.is_ar else "German", "de")
        layout.addWidget(self.primary_sub_combo)

        layout.addWidget(QLabel(helpers.LBL_SEC_SUB))
        self.secondary_sub_combo = QComboBox()
        layout.addWidget(self.secondary_sub_combo)

        # Connect smart dynamic filters on primary language changed
        self.primary_sub_combo.currentIndexChanged.connect(self.update_secondary_languages)
        
        # 2. Video Subtitles Options
        # Checkbox "Merge subtitle tracks directly inside Video file"
        self.embed_subs_check = QCheckBox(helpers.SET_EMBED_SUBS)
        layout.addWidget(self.embed_subs_check)

        # Subtitle formats conditional layout widgets
        # Group/Widget 1: Final Video Container (shown only when merging subtitles)
        self.container_widget = QWidget()
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(QLabel(helpers.LBL_FINAL_CONTAINER))
        self.video_container_combo = QComboBox()
        self.video_container_combo.addItem(".mp4", "mp4")
        self.video_container_combo.addItem(".mkv", "mkv")
        container_layout.addWidget(self.video_container_combo)
        layout.addWidget(self.container_widget)

        # Group/Widget 2: Subtitle Output Format (shown only when separate/not merged)
        self.sub_format_widget = QWidget()
        sub_format_layout = QVBoxLayout(self.sub_format_widget)
        sub_format_layout.setContentsMargins(0, 0, 0, 0)
        sub_format_layout.addWidget(QLabel(helpers.SET_SUB_FORMAT))
        self.sub_format_combo = QComboBox()
        self.sub_format_combo.addItem("SRT Subtitles (.srt)", "srt")
        self.sub_format_combo.addItem("WebVTT Subtitles (.vtt)", "vtt")
        self.sub_format_combo.addItem("SubStation Alpha (.ass)", "ass")
        sub_format_layout.addWidget(self.sub_format_combo)
        layout.addWidget(self.sub_format_widget)

        # Connect merge subtitles checkbox to toggle visibility of formats
        self.embed_subs_check.stateChanged.connect(self.toggle_subtitle_output_visibility)

        # 3. Audio Subtitles/Lyrics Options
        # Checkbox: "Embed lyrics inside audio file"
        self.embed_lyrics_check = QCheckBox(helpers.LBL_EMBED_LYRICS)
        layout.addWidget(self.embed_lyrics_check)

        # Widget displaying sync format LRC
        self.lyrics_format_widget = QWidget()
        lyrics_layout = QHBoxLayout(self.lyrics_format_widget)
        lyrics_layout.setContentsMargins(0, 0, 0, 0)
        lyrics_layout.addWidget(QLabel(helpers.LBL_LYRICS_FORMAT))
        
        self.lyrics_format_val = QLabel("LRC (.lrc)")
        self.lyrics_format_val.setStyleSheet("font-weight: bold; color: #7c6af7;")
        lyrics_layout.addWidget(self.lyrics_format_val)
        lyrics_layout.addStretch()
        layout.addWidget(self.lyrics_format_widget)

        # Connect lyrics checkbox to toggle visibility
        self.embed_lyrics_check.stateChanged.connect(self.toggle_lyrics_visibility)

        layout.addStretch()
        self.stacked_widget.addWidget(panel)

    # ──────────────────────────────────────────────
    #  LOGIC AND AUTO-SAVE HELPERS
    # ──────────────────────────────────────────────

    def update_secondary_languages(self):
        """Smart filter secondary language list to exclude the primary language choice"""
        if self.primary_sub_combo.currentIndex() < 0:
            return
            
        self.secondary_sub_combo.blockSignals(True)
        
        # Save previous selection
        current_sec = self.secondary_sub_combo.currentData() or app_config.get("secondary_sub_lang", "en")
        
        self.secondary_sub_combo.clear()
        
        prim_lang = self.primary_sub_combo.currentData()
        languages = [
            ("العربية" if helpers.is_ar else "Arabic", "ar"),
            ("الإنجليزية" if helpers.is_ar else "English", "en"),
            ("الفرنسية" if helpers.is_ar else "French", "fr"),
            ("الألمانية" if helpers.is_ar else "German", "de")
        ]
        
        for name, code in languages:
            if code != prim_lang:
                self.secondary_sub_combo.addItem(name, code)
                
        # Restore selection
        idx = self.secondary_sub_combo.findData(current_sec)
        if idx >= 0:
            self.secondary_sub_combo.setCurrentIndex(idx)
        else:
            self.secondary_sub_combo.setCurrentIndex(0)
            
        self.secondary_sub_combo.blockSignals(False)
        self.auto_save()

    def toggle_subtitle_output_visibility(self):
        """Show Container format and hide subtitle format when Merging subtitles, and vice versa"""
        is_merged = self.embed_subs_check.isChecked()
        self.container_widget.setVisible(is_merged)
        self.sub_format_widget.setVisible(not is_merged)
        self.auto_save()

    def toggle_lyrics_visibility(self):
        """Show synced LRC format label when lyrics embedding is enabled"""
        has_lyrics = self.embed_lyrics_check.isChecked()
        self.lyrics_format_widget.setVisible(has_lyrics)
        self.auto_save()

    def on_speed_unit_changed(self, text):
        if text == "KB/s": self.custom_speed_spin.setValue(100)
        else: self.custom_speed_spin.setValue(1)
        self.auto_save()

    def toggle_custom_speed(self):
        if self.speed_combo.currentData() == "custom":
            self.custom_speed_widget.show()
            if self.custom_speed_unit.currentText() == "KB/s": self.custom_speed_spin.setValue(100)
            else: self.custom_speed_spin.setValue(1)
        else:
            self.custom_speed_widget.hide()
        self.auto_save()

    def toggle_custom_location(self):
        if self.location_combo.currentData() == "custom": self.custom_loc_btn.show()
        else: self.custom_loc_btn.hide()
        self.auto_save()

    def browse_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.custom_loc_btn.setProperty("path", folder)
            folder_name = folder.split('/')[-1] if '/' in folder else folder
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
            self.custom_loc_btn.setIcon(QIcon(os.path.join(assets_dir, "icons", "folder.svg")))
            self.custom_loc_btn.setText(f"  {folder_name}")
            self.auto_save()

    def load_settings_data(self):
        # 1. Appearance panel
        idx = self.theme_combo.findData(app_config.get("theme", "auto"))
        if idx >= 0: self.theme_combo.setCurrentIndex(idx)
        idx = self.lang_combo.findData(app_config.get("language", "system"))
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        
        idx = self.font_combo.findData(app_config.get("font_family", "System Default"))
        if idx >= 0: self.font_combo.setCurrentIndex(idx)
        
        size_val = app_config.get("font_size", 12)
        idx = self.font_size_combo.findData(size_val)
        if idx >= 0: self.font_size_combo.setCurrentIndex(idx)
        
        idx = self.scale_combo.findData(app_config.get("ui_scaling", "System Default (Auto)"))
        if idx >= 0: self.scale_combo.setCurrentIndex(idx)
        
        self.notify_check.setChecked(app_config.get("notifications", True))
        self.thumb_check.setChecked(app_config.get("show_thumbnails", True))
        
        # 2. Downloads panel
        idx = self.location_combo.findData(app_config.get("save_mode", "auto"))
        if idx >= 0: self.location_combo.setCurrentIndex(idx)

        if app_config.get("custom_path"):
            self.custom_loc_btn.setProperty("path", app_config.get("custom_path"))
            folder_name = app_config["custom_path"].split('/')[-1]
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
            self.custom_loc_btn.setIcon(QIcon(os.path.join(assets_dir, "icons", "folder.svg")))
            self.custom_loc_btn.setText(f"  {folder_name}")
            if app_config.get("save_mode") == "custom":
                self.custom_loc_btn.show()

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

        idx = self.cookie_combo.findData(app_config.get("browser_cookies", "none"))
        if idx >= 0: self.cookie_combo.setCurrentIndex(idx)
        
        self.downgrade_check.setChecked(app_config.get("allow_downgrade", True))

        # 3. Subtitles panel
        p_idx = self.primary_sub_combo.findData(app_config.get("primary_sub_lang", "ar"))
        if p_idx >= 0: self.primary_sub_combo.setCurrentIndex(p_idx)
        self.update_secondary_languages()

        s_idx = self.secondary_sub_combo.findData(app_config.get("secondary_sub_lang", "en"))
        if s_idx >= 0: self.secondary_sub_combo.setCurrentIndex(s_idx)
        
        self.embed_subs_check.setChecked(app_config.get("embed_subs_default", False))
        
        idx = self.video_container_combo.findData(app_config.get("video_container", "mkv"))
        if idx >= 0: self.video_container_combo.setCurrentIndex(idx)

        idx = self.sub_format_combo.findData(app_config.get("subtitle_output_format", "srt"))
        if idx >= 0: self.sub_format_combo.setCurrentIndex(idx)

        self.embed_lyrics_check.setChecked(app_config.get("embed_lyrics", False))
        
        # Apply visibility toggles
        self.toggle_subtitle_output_visibility()
        self.toggle_lyrics_visibility()

    def capture_startup_values(self):
        # Capture settings at startup to check if restart is needed when modified
        self.startup_values = {
            "language": app_config.get("language", "system"),
            "ui_scaling": app_config.get("ui_scaling", "System Default (Auto)")
        }

    def connect_signals(self):
        # 1. Appearance panel
        self.theme_combo.currentIndexChanged.connect(self.on_live_style_changed)
        self.lang_combo.currentIndexChanged.connect(self.auto_save)
        self.font_combo.currentIndexChanged.connect(self.on_live_style_changed)
        self.font_size_combo.currentIndexChanged.connect(self.on_live_style_changed)
        self.scale_combo.currentIndexChanged.connect(self.auto_save)
        self.notify_check.stateChanged.connect(self.auto_save)
        self.thumb_check.stateChanged.connect(self.auto_save)
        
        # 2. Downloads panel
        self.location_combo.currentIndexChanged.connect(self.auto_save)
        self.speed_combo.currentIndexChanged.connect(self.auto_save)
        self.custom_speed_spin.valueChanged.connect(self.auto_save)
        self.custom_speed_unit.currentIndexChanged.connect(self.auto_save)
        self.concurrent_spin.valueChanged.connect(self.auto_save)
        self.data_saver_check.stateChanged.connect(self.auto_save)
        self.cookie_combo.currentIndexChanged.connect(self.auto_save)
        self.downgrade_check.stateChanged.connect(self.auto_save)
        
        # 3. Subtitles panel
        self.primary_sub_combo.currentIndexChanged.connect(self.update_secondary_languages)
        self.secondary_sub_combo.currentIndexChanged.connect(self.auto_save)
        self.embed_subs_check.stateChanged.connect(self.toggle_subtitle_output_visibility)
        self.video_container_combo.currentIndexChanged.connect(self.auto_save)
        self.sub_format_combo.currentIndexChanged.connect(self.auto_save)
        self.embed_lyrics_check.stateChanged.connect(self.toggle_lyrics_visibility)

    def on_live_style_changed(self):
        """Apply theme, font, and size instantly when selected (No restart needed!)"""
        self.auto_save()
        from gui.theme import apply_theme
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            apply_theme(app, app_config.get("theme", "auto"))
            
        # Trigger dynamic theme icon refresh on the entire application window!
        if self.parent_window and hasattr(self.parent_window, 'refresh_theme_icons'):
            self.parent_window.refresh_theme_icons()
            
        # Refresh current settings panel section headers
        self.refresh_theme_icons()

    def auto_save(self):
        if self.is_loading:
            return
            
        # 1. Appearance panel
        app_config["theme"] = self.theme_combo.currentData()
        app_config["language"] = self.lang_combo.currentData()
        app_config["font_family"] = self.font_combo.currentData()
        app_config["font_size"] = self.font_size_combo.currentData()
        app_config["ui_scaling"] = self.scale_combo.currentData()
        app_config["notifications"] = self.notify_check.isChecked()
        app_config["show_thumbnails"] = self.thumb_check.isChecked()
        
        # 2. Downloads panel
        app_config["save_mode"] = self.location_combo.currentData()
        custom_path = self.custom_loc_btn.property("path")
        if custom_path: app_config["custom_path"] = custom_path
        app_config["data_saver"] = self.data_saver_check.isChecked()
        app_config["concurrent_downloads"] = self.concurrent_spin.value()
        app_config["browser_cookies"] = self.cookie_combo.currentData()
        app_config["allow_downgrade"] = self.downgrade_check.isChecked()

        if self.speed_combo.currentData() == "custom":
            unit = "M" if self.custom_speed_unit.currentText() == "MB/s" else "K"
            app_config["speed_limit"] = f"{self.custom_speed_spin.value()}{unit}"
        else:
            app_config["speed_limit"] = self.speed_combo.currentData()

        # 3. Subtitles panel
        app_config["primary_sub_lang"] = self.primary_sub_combo.currentData()
        app_config["secondary_sub_lang"] = self.secondary_sub_combo.currentData()
        app_config["embed_subs_default"] = self.embed_subs_check.isChecked()
        app_config["video_container"] = self.video_container_combo.currentData()
        
        # Map dynamic video container selection to output_format when subtitles merging is enabled
        if self.embed_subs_check.isChecked():
            app_config["output_format"] = self.video_container_combo.currentData()
        
        app_config["subtitle_output_format"] = self.sub_format_combo.currentData()
        app_config["embed_lyrics"] = self.embed_lyrics_check.isChecked()
        
        # Write directly inside configurations file (persistence)
        save_settings(app_config)
        
        # 4. Check if restart is pending (only for language and scaling changes)
        restart_keys = ["language", "ui_scaling"]
        is_restart_needed = False
        changed_keys = []
        for key in restart_keys:
            if app_config.get(key) != self.startup_values.get(key):
                is_restart_needed = True
                changed_keys.append(key)
                
        if is_restart_needed:
            msg = "إعادة تشغيل التطبيق مطلوبة لتطبيق التغييرات الجديدة" if helpers.is_ar else "Restart required to apply new changes"
            self.restart_required_signal.emit(msg)
        else:
            self.restart_required_signal.emit("")

    def refresh_theme_icons(self):
        self.header_icon.setPixmap(helpers.get_theme_icon("folder.svg", 18).pixmap(18, 18))
        self.item_appearance.setIcon(0, helpers.get_theme_icon("palette.svg"))
        self.item_downloads.setIcon(0, helpers.get_theme_icon("inbox.svg"))
        self.item_subtitles.setIcon(0, helpers.get_theme_icon("clapperboard.svg"))
        
        # Refresh downgrade icon tooltip icon
        self.info_icon.setPixmap(helpers.get_theme_icon("info.svg", 16).pixmap(16, 16))
        
        if hasattr(self, 'section_headers'):
            for header in self.section_headers:
                header.icon_lbl.setPixmap(helpers.get_theme_icon(header.icon_name, 20).pixmap(20, 20))
