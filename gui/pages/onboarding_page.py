import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QComboBox, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from utils.helpers import get_colored_icon, get_current_theme_color, resource_path
from utils.locales import tr, set_current_language, resolve_lang
from gui.components.buttons import ToggleSwitch

class OnboardingPage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.current_step = 0
        self.initUI()
        self.apply_theme_colors()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 25, 40, 25)
        main_layout.setSpacing(20)

        # Header Bar
        header_layout = QHBoxLayout()
        self.header_title = QLabel(tr("onboarding_title", "Setup Wizard"), self)
        self.header_title.setStyleSheet("font-weight: bold; font-size: 16px; opacity: 0.8;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        
        self.btn_restart = QPushButton(tr("btn_restart", "إعادة التشغيل الآن / Restart Now"), self)
        self.btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart.setStyleSheet("background-color: #e3a32e; color: #1e1f22; font-weight: bold; padding: 6px 14px; border-radius: 6px; font-size: 12px;")
        self.btn_restart.setIcon(get_colored_icon("assets/icons/restart.svg", "#1e1f22"))
        self.btn_restart.hide()
        self.btn_restart.clicked.connect(self.restart_application)
        header_layout.addWidget(self.btn_restart)
        
        main_layout.addLayout(header_layout)

        # Stacked Widget for Slides (Full Page Area)
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack, 1)

        # Build Slide Pages
        self.create_slide_1() # Language & Welcome
        self.create_slide_2() # Theme & Accent
        self.create_slide_3() # Default Directory
        self.create_slide_4() # Features Setup

        # Bottom Bar: dots indicators + Back + Next/Finish
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 10)
        
        self.btn_back = QPushButton(tr("btn_back", "Back"), self)
        self.btn_back.setFixedSize(100, 38)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.prev_slide)
        self.btn_back.hide()
        bottom_layout.addWidget(self.btn_back)

        bottom_layout.addStretch()

        # Dot indicators
        self.dots_layout = QHBoxLayout()
        self.dots_layout.setSpacing(8)
        self.dots = []
        for i in range(4):
            dot = QFrame(self)
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("background-color: #888888; border-radius: 5px;")
            self.dots_layout.addWidget(dot)
            self.dots.append(dot)
        bottom_layout.addLayout(self.dots_layout)

        bottom_layout.addStretch()

        self.btn_next = QPushButton(tr("btn_next", "Next"), self)
        self.btn_next.setFixedSize(130, 38)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.next_slide)
        bottom_layout.addWidget(self.btn_next)

        main_layout.addLayout(bottom_layout)
        self.update_indicators()

    def apply_theme_colors(self):
        accent_hex = self.main_app.theme_manager.get_accent_hex()
        accent_hover = self.main_app.theme_manager.get_accent_hover_hex()
        is_dark = self.main_app.theme_manager.get_actual_theme() == "dark"
        
        bg_color = "#1e1e2e" if is_dark else "#ffffff"
        border_color = "#32324e" if is_dark else "#e2e8f0"
        text_color = "#f8f8f2" if is_dark else "#1a202c"
        sub_text_color = "#a0aec0" if is_dark else "#718096"
        card_bg = "#252538" if is_dark else "#f8fafc"

        style = f"""
        OnboardingPage {{
            background-color: {bg_color};
        }}
        QFrame#CardBox {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
        }}
        QLabel {{
            color: {text_color};
        }}
        QLabel#SubText {{
            color: {sub_text_color};
            font-size: 14px;
        }}
        QPushButton {{
            background-color: {card_bg};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            font-weight: 500;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {border_color};
        }}
        QComboBox {{
            background-color: {card_bg};
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 13px;
        }}
        """
        self.setStyleSheet(style)
        
        # Primary Action button style
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_hex};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
        """)
        
        # Style accent chooser buttons
        if hasattr(self, 'accent_buttons'):
            for name, btn in self.accent_buttons.items():
                active = (self.main_app.theme_manager.get_accent_theme_name() == name)
                border_style = f"3px solid {text_color}" if active else "1px solid #888888"
                btn.setStyleSheet(f"background-color: {btn.property('color')}; border-radius: 18px; border: {border_style};")

    # ───────────────────────────── SLIDE CREATION ─────────────────────────────

    def create_slide_1(self):
        slide = QWidget()
        layout = QVBoxLayout(slide)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(22)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Welcome Logo / Icon
        self.lbl_logo = QLabel(self)
        logo_path = resource_path(os.path.join('assets', 'icon.ico'))
        if os.path.exists(logo_path):
            self.lbl_logo.setPixmap(QPixmap(logo_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_logo)

        # Welcome titles
        self.slide1_title = QLabel(tr("onboarding_welcome_title", "Welcome to AHS-MediaDL"), self)
        self.slide1_title.setStyleSheet("font-size: 24px; font-weight: bold; text-align: center;")
        self.slide1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.slide1_title)

        self.slide1_sub = QLabel(tr("onboarding_welcome_sub", "Let's configure a few quick preferences to get you started."), self)
        self.slide1_sub.setObjectName("SubText")
        self.slide1_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slide1_sub.setWordWrap(True)
        layout.addWidget(self.slide1_sub)

        # Language Card Container
        lang_card = QFrame(self)
        lang_card.setObjectName("CardBox")
        lang_card.setFixedWidth(420)
        lang_card_layout = QHBoxLayout(lang_card)
        lang_card_layout.setContentsMargins(20, 15, 20, 15)

        self.lang_label = QLabel(tr("lang_label", "App Language:"), self)
        self.lang_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        lang_card_layout.addWidget(self.lang_label)
        lang_card_layout.addStretch()

        self.lang_combo = QComboBox(self)
        self.lang_combo.setFixedWidth(180)
        self.lang_combo.addItem(tr("lang_system", "System Default"), "system")
        self.lang_combo.addItem("العربية", "ar")
        self.lang_combo.addItem("English", "en")
        
        current_lang = self.main_app.settings_manager.get("language", "system")
        idx = self.lang_combo.findData(current_lang)
        if idx != -1:
            self.lang_combo.setCurrentIndex(idx)
            
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        lang_card_layout.addWidget(self.lang_combo)
        
        layout.addWidget(lang_card)
        self.stack.addWidget(slide)

    def create_slide_2(self):
        slide = QWidget()
        layout = QVBoxLayout(slide)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(22)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slide2_title = QLabel(tr("onboarding_theme_title", "Choose Appearance"), self)
        self.slide2_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.slide2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.slide2_title)

        # Theme & Accent Card
        theme_card = QFrame(self)
        theme_card.setObjectName("CardBox")
        theme_card.setFixedWidth(460)
        theme_card_layout = QVBoxLayout(theme_card)
        theme_card_layout.setContentsMargins(20, 20, 20, 20)
        theme_card_layout.setSpacing(20)

        # Theme Selector Row
        theme_row = QHBoxLayout()
        self.theme_label = QLabel(tr("theme_label", "Theme Mode:"), self)
        self.theme_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        theme_row.addWidget(self.theme_label)
        theme_row.addStretch()

        self.theme_combo = QComboBox(self)
        self.theme_combo.setFixedWidth(180)
        self.theme_combo.addItem(tr("theme_system", "System Theme"), "auto")
        self.theme_combo.addItem(tr("theme_light", "Light Mode"), "light")
        self.theme_combo.addItem(tr("theme_dark", "Dark Mode"), "dark")
        
        current_theme = self.main_app.settings_manager.get("theme", "auto")
        idx = self.theme_combo.findData(current_theme)
        if idx != -1:
            self.theme_combo.setCurrentIndex(idx)
            
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_card_layout.addLayout(theme_row)

        # Divider
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: palette(midlight); opacity: 0.5;")
        theme_card_layout.addWidget(divider)

        # Accent Selection Row
        accent_row = QHBoxLayout()
        self.accent_title = QLabel(tr("accent_label", "Accent Color:"), self)
        self.accent_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        accent_row.addWidget(self.accent_title)
        accent_row.addStretch()

        accent_btns_layout = QHBoxLayout()
        accent_btns_layout.setSpacing(15)

        self.accent_buttons = {}
        colors = {
            "orange": "#ff5e3a",
            "blue": "#3b82f6",
            "purple": "#8b5cf6",
            "green": "#10b981"
        }
        for name, hex_val in colors.items():
            btn = QPushButton(self)
            btn.setFixedSize(36, 36)
            btn.setProperty("color", hex_val)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self.on_accent_changed(n))
            accent_btns_layout.addWidget(btn)
            self.accent_buttons[name] = btn

        accent_row.addLayout(accent_btns_layout)
        theme_card_layout.addLayout(accent_row)

        layout.addWidget(theme_card)
        self.stack.addWidget(slide)

    def create_slide_3(self):
        slide = QWidget()
        layout = QVBoxLayout(slide)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(22)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slide3_title = QLabel(tr("onboarding_path_title", "Where to Save Downloads?"), self)
        self.slide3_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.slide3_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.slide3_title)

        self.slide3_sub = QLabel(tr("onboarding_path_sub", "All videos and playlists downloaded will be saved here. You can change this anytime."), self)
        self.slide3_sub.setObjectName("SubText")
        self.slide3_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slide3_sub.setWordWrap(True)
        layout.addWidget(self.slide3_sub)

        # Path Card Box
        path_card = QFrame(self)
        path_card.setObjectName("CardBox")
        path_card.setFixedWidth(520)
        path_card_layout = QVBoxLayout(path_card)
        path_card_layout.setContentsMargins(20, 20, 20, 20)
        path_card_layout.setSpacing(15)

        path_row = QHBoxLayout()
        self.path_label = QLabel(tr("path_label", "Save Path:"), self)
        self.path_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        path_row.addWidget(self.path_label)
        path_row.addStretch()

        self.path_combo = QComboBox(self)
        self.path_combo.setFixedWidth(240)
        self.path_combo.addItem(tr("path_downloads", "Save in Downloads"), "downloads")
        self.path_combo.addItem(tr("path_always_ask", "Always Ask"), "always_ask")
        self.path_combo.addItem(tr("path_custom", "Custom"), "custom")
        path_row.addWidget(self.path_combo)
        path_card_layout.addLayout(path_row)

        custom_row = QHBoxLayout()
        self.lbl_path = QLabel(self.main_app.settings_manager.get("last_save_dir"), self)
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet("font-size: 13px; color: #888888;")
        custom_row.addWidget(self.lbl_path, 1)

        self.btn_browse = QPushButton(tr("btn_browse", "Browse..."), self)
        self.btn_browse.setFixedHeight(35)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_path)
        custom_row.addWidget(self.btn_browse)
        path_card_layout.addLayout(custom_row)

        current_option = self.main_app.settings_manager.get("download_path_type", "downloads")
        idx = self.path_combo.findData(current_option)
        if idx != -1:
            self.path_combo.setCurrentIndex(idx)
        self.path_combo.currentIndexChanged.connect(self.on_path_option_changed)
        self.on_path_option_changed()
        
        layout.addWidget(path_card)
        self.stack.addWidget(slide)

    def on_path_option_changed(self):
        option = self.path_combo.currentData()
        self.main_app.settings_manager.set("download_path_type", option)
        is_custom = (option == "custom")
        self.btn_browse.setVisible(is_custom)
        self.lbl_path.setVisible(is_custom)

    def create_slide_4(self):
        slide = QWidget()
        layout = QVBoxLayout(slide)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(22)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slide4_title = QLabel(tr("onboarding_features_title", "Configure Features"), self)
        self.slide4_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.slide4_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.slide4_title)

        # Toggles Card
        toggles_card = QFrame(self)
        toggles_card.setObjectName("CardBox")
        toggles_card.setFixedWidth(480)
        toggles_layout = QVBoxLayout(toggles_card)
        toggles_layout.setSpacing(20)
        toggles_layout.setContentsMargins(20, 20, 20, 20)

        # Background listener
        bg_layout = QHBoxLayout()
        self.bg_label = QLabel(tr("run_bg_label", "Run in background on close"), self)
        self.bg_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        bg_layout.addWidget(self.bg_label)
        bg_layout.addStretch()
        self.sw_bg = ToggleSwitch(self)
        self.sw_bg.setChecked(self.main_app.settings_manager.get("run_in_background", False))
        bg_layout.addWidget(self.sw_bg)
        toggles_layout.addLayout(bg_layout)

        # Divider
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: palette(midlight); opacity: 0.5;")
        toggles_layout.addWidget(divider)

        # Clipboard monitor
        clip_layout = QHBoxLayout()
        self.clip_label = QLabel(tr("clipboard_monitor_label", "Monitor Clipboard for Links"), self)
        self.clip_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        clip_layout.addWidget(self.clip_label)
        clip_layout.addStretch()
        self.sw_clip = ToggleSwitch(self)
        self.sw_clip.setChecked(self.main_app.settings_manager.get("clipboard_monitor", False))
        clip_layout.addWidget(self.sw_clip)
        toggles_layout.addLayout(clip_layout)

        layout.addWidget(toggles_card)
        self.stack.addWidget(slide)

    # ────────────────────────────── ACTIONS ───────────────────────────────────

    def on_lang_changed(self, index):
        lang = self.lang_combo.currentData()
        self.main_app.settings_manager.set("language", lang)
        self.main_app.settings_manager.save()
        set_current_language(lang)
        self.main_app.retranslate_app()
        self.retranslate_ui()

    def restart_application(self):
        """ Delegate to SystemManager """
        self.main_app.system_manager.restart_application()

    def retranslate_ui(self):
        lang = self.main_app.settings_manager.get("language", "system")
        actual_lang = resolve_lang(lang)
        is_rtl = (actual_lang == "ar")
        
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight)
        
        if hasattr(self, 'header_title'):
            self.header_title.setText(tr("onboarding_title", "Setup Wizard"))
        if hasattr(self, 'btn_back'):
            self.btn_back.setText(tr("btn_back", "Back"))
        if hasattr(self, 'slide1_title'):
            self.slide1_title.setText(tr("onboarding_welcome_title", "Welcome to AHS-MediaDL"))
        if hasattr(self, 'slide1_sub'):
            self.slide1_sub.setText(tr("onboarding_welcome_sub", "Let's configure a few quick preferences to get you started."))
        if hasattr(self, 'lang_label'):
            self.lang_label.setText(tr("lang_label", "App Language:"))
        if hasattr(self, 'slide2_title'):
            self.slide2_title.setText(tr("onboarding_theme_title", "Choose Appearance"))
        if hasattr(self, 'theme_label'):
            self.theme_label.setText(tr("theme_label", "Theme Mode:"))
        if hasattr(self, 'accent_title'):
            self.accent_title.setText(tr("accent_label", "Accent Color:"))
        if hasattr(self, 'slide3_title'):
            self.slide3_title.setText(tr("onboarding_path_title", "Where to Save Downloads?"))
        if hasattr(self, 'slide3_sub'):
            self.slide3_sub.setText(tr("onboarding_path_sub", "All videos and playlists downloaded will be saved here. You can change this anytime."))
        if hasattr(self, 'path_label'):
            self.path_label.setText(tr("path_label", "Save Path:"))
        if hasattr(self, 'path_combo'):
            self.path_combo.setItemText(0, tr("path_downloads", "Save in Downloads"))
            self.path_combo.setItemText(1, tr("path_always_ask", "Always Ask"))
            self.path_combo.setItemText(2, tr("path_custom", "Custom"))
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setItemText(0, tr("theme_system", "System"))
            self.theme_combo.setItemText(1, tr("theme_light", "Light Mode"))
            self.theme_combo.setItemText(2, tr("theme_dark", "Dark Mode"))
        if hasattr(self, 'btn_browse'):
            self.btn_browse.setText(tr("btn_browse", "Browse..."))
        if hasattr(self, 'slide4_title'):
            self.slide4_title.setText(tr("onboarding_features_title", "Configure Features"))
        if hasattr(self, 'bg_label'):
            self.bg_label.setText(tr("run_bg_label", "Run in background on close"))
        if hasattr(self, 'clip_label'):
            self.clip_label.setText(tr("clipboard_monitor_label", "Monitor Clipboard for Links"))
            
        if self.current_step == 3:
            self.btn_next.setText(tr("btn_start", "Get Started"))
        else:
            self.btn_next.setText(tr("btn_next", "Next"))

    def on_theme_changed(self, index):
        theme = self.theme_combo.currentData()
        self.main_app.settings_manager.set("theme", theme)
        self.main_app.apply_appearance(
            theme,
            self.main_app.settings_manager.get("font_family", "System Default"),
            self.main_app.settings_manager.get("font_size", 12)
        )
        self.apply_theme_colors()

    def on_accent_changed(self, name):
        self.main_app.settings_manager.set("accent_theme", name)
        self.main_app.apply_appearance(
            self.main_app.settings_manager.get("theme", "auto"),
            self.main_app.settings_manager.get("font_family", "System Default"),
            self.main_app.settings_manager.get("font_size", 12)
        )
        self.apply_theme_colors()

    def browse_path(self):
        current = self.lbl_path.text()
        folder = QFileDialog.getExistingDirectory(self, tr("select_folder", "Select Download Folder"), current)
        if folder:
            self.lbl_path.setText(folder)
            self.main_app.settings_manager.set_many({
                "last_save_dir": folder,
                "custom_path": folder
            })

    # ───────────────────────────── NAVIGATION ─────────────────────────────────

    def prev_slide(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_indicators()

    def next_slide(self):
        if self.current_step < 3:
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_indicators()
        else:
            # Finish onboarding page
            self.main_app.settings_manager.set("run_in_background", self.sw_bg.isChecked())
            self.main_app.settings_manager.set("clipboard_monitor", self.sw_clip.isChecked())
            self.main_app.settings_manager.set("first_launch", False)
            self.main_app.settings_manager.save()
            self.main_app.finish_onboarding()

    def update_indicators(self):
        accent_hex = self.main_app.theme_manager.get_accent_hex()
        for i, dot in enumerate(self.dots):
            if i == self.current_step:
                dot.setFixedSize(20, 8)
                dot.setStyleSheet(f"background-color: {accent_hex}; border-radius: 4px;")
            else:
                dot.setFixedSize(8, 8)
                dot.setStyleSheet("background-color: #888888; border-radius: 4px;")
        
        self.btn_back.setVisible(self.current_step > 0)
        
        if self.current_step == 3:
            self.btn_next.setText(tr("btn_start", "Get Started"))
        else:
            self.btn_next.setText(tr("btn_next", "Next"))
