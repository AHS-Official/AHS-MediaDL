"""
media_panels.py
───────────────
يجمع مكونات معاينة الوسائط المشتركة:
  1. SingleVideoPanel — معاينة الفيديو الواحد وخياراته
  2. PlaylistPanel    — معاينة قوائم التشغيل وخياراتها
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QCheckBox, QFrame,
    QScrollArea, QPushButton, QLineEdit, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QThreadPool, pyqtSignal, QRect, QTimer
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter

from gui.components.common import (
    ResponsiveImage, MultiLineElidedLabel, ElidedLabel,
    get_relative_time, format_views, FormatPreferencesMixin
)
from gui.components.quality_tiles import QualityGridWidget
from utils.helpers import (
    get_colored_icon, get_current_theme_color,
    get_full_language_name, clean_and_shorten_title
)
from utils.theme import get_accent_hex
from utils.locales import tr


# قائمة الجودات الثابتة للـ playlist (مكان واحد للتعديل)
PLAYLIST_FORMATS = [
    ("4K (2160p) - Ultra HD",               "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"),
    ("2K (1440p) - Quad HD",                "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"),
    ("Full HD (1080p)",                      "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"),
    ("High (720p)",                          "bestvideo[height<=720]+bestaudio/best[height<=720]/best"),
    ("Standard (480p)",                      "bestvideo[height<=480]+bestaudio/best[height<=480]/best"),
    ("Medium (360p)",                        "bestvideo[height<=360]+bestaudio/best[height<=360]/best"),
    ("Low (240p)",                           "bestvideo[height<=240]+bestaudio/best[height<=240]/best"),
    ("Very Low (144p)",                      "bestvideo[height<=144]+bestaudio/best[height<=144]/best"),
    ("separator",                            ""),
    ("M4A (128kbps) - Original Best Audio",  "audio:bestaudio:m4a:128"),
]


class SingleVideoPanel(QWidget, FormatPreferencesMixin):
    """
    البطاقة الشاملة العصرية لمعاينة الفيديو الواحد وخيارات التنزيل (Modern Video Hero Card).
    تجمع تفاصيل الفيديو، أزرار التبديل بين الفيديو والموسيقى، شبكة كروت الجودات،
    خيارات الترجمة، مسار الحفظ، وأزرار الإجراءات في إطار أنيق وموحد.
    """
    download_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, main_app, parent=None, is_dialog=False):
        super().__init__(parent)
        self.main_app = main_app
        self.is_dialog = is_dialog
        self.clean_title = "video"
        self._format_list = []
        self._current_selected_format = None
        self._initUI()
        self._load_remember_state()

    def _initUI(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── The Unified Hero Card Frame ───────────────────────────────────────
        self.hero_card = QFrame(self)
        self.hero_card.setObjectName("MediaHeroCard")
        self.hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.info_card = self.hero_card  # For backward-compatibility
        self.settings_card = self.hero_card  # For backward-compatibility
        card_layout = QVBoxLayout(self.hero_card)
        card_layout.setContentsMargins(22, 16, 22, 16)
        card_layout.setSpacing(12)

        # ── 1. Top Header: Thumbnail (Left) + Video Information (Right) ───────
        header_widget = QWidget(self.hero_card)
        header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        # Thumbnail with duration overlay on the LEFT (200x112, 16:9 ratio)
        self.thumb_label = ResponsiveImage(min_height=112)
        self.thumb_label.setFixedSize(200, 112)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.thumb_label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Video info on the RIGHT
        info_side_layout = QVBoxLayout()
        info_side_layout.setContentsMargins(0, 0, 0, 0)
        info_side_layout.setSpacing(4)

        # Title: standard QLabel with wordWrap, max 2 lines
        self.title_label = QLabel('', self.hero_card)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setMaximumHeight(44)
        info_side_layout.addWidget(self.title_label)

        # Meta row: Uploader, views, upload date
        self.meta_row = QHBoxLayout()
        self.meta_row.setContentsMargins(0, 0, 0, 0)
        self.meta_row.setSpacing(6)

        meta_font = QFont()
        meta_font.setPointSize(9)

        self.channel_icon_lbl = QLabel(self.hero_card)
        self.channel_icon_lbl.setFixedSize(14, 14)
        self.channel_label = QLabel('', self.hero_card)
        self.channel_label.setFont(meta_font)
        self.meta_row.addWidget(self.channel_icon_lbl)
        self.meta_row.addWidget(self.channel_label)

        self.views_sep_lbl = QLabel('•', self.hero_card)
        self.views_sep_lbl.setFont(meta_font)
        self.views_icon_lbl = QLabel(self.hero_card)
        self.views_icon_lbl.setFixedSize(14, 14)
        self.views_label = QLabel('', self.hero_card)
        self.views_label.setFont(meta_font)
        self.meta_row.addWidget(self.views_sep_lbl)
        self.meta_row.addWidget(self.views_icon_lbl)
        self.meta_row.addWidget(self.views_label)

        self.date_sep_lbl = QLabel('•', self.hero_card)
        self.date_sep_lbl.setFont(meta_font)
        self.date_icon_lbl = QLabel(self.hero_card)
        self.date_icon_lbl.setFixedSize(14, 14)
        self.date_label = QLabel('', self.hero_card)
        self.date_label.setFont(meta_font)
        self.meta_row.addWidget(self.date_sep_lbl)
        self.meta_row.addWidget(self.date_icon_lbl)
        self.meta_row.addWidget(self.date_label)

        # Dummy hidden label for backwards compatibility
        self.meta_label = QLabel('', self.hero_card)
        self.meta_label.hide()

        self.meta_row.addStretch()
        info_side_layout.addLayout(self.meta_row)
        info_side_layout.addStretch()

        # Selected Quality Summary Badge (Compact pill shape)
        self.badge_frame = QFrame(self.hero_card)
        self.badge_frame.setObjectName("QualitySummaryBadge")
        self.badge_frame.setFixedHeight(28)
        badge_layout = QHBoxLayout(self.badge_frame)
        badge_layout.setContentsMargins(10, 0, 12, 0)
        badge_layout.setSpacing(6)

        self.badge_icon_lbl = QLabel(self.badge_frame)
        self.badge_icon_lbl.setFixedSize(14, 14)
        badge_layout.addWidget(self.badge_icon_lbl)

        self.quality_badge_lbl = QLabel(self.badge_frame)
        self.quality_badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_font = QFont()
        badge_font.setPointSize(9)
        badge_font.setBold(True)
        self.quality_badge_lbl.setFont(badge_font)
        badge_layout.addWidget(self.quality_badge_lbl)

        badge_hlayout = QHBoxLayout()
        badge_hlayout.setContentsMargins(0, 0, 0, 0)
        badge_hlayout.addWidget(self.badge_frame)
        badge_hlayout.addStretch()
        info_side_layout.addLayout(badge_hlayout)

        header_layout.addLayout(info_side_layout, stretch=1)

        self.duration_label = QLabel('', self.hero_card)
        self.duration_label.hide()

        card_layout.addWidget(header_widget)

        # ── Top Divider ───────────────────────────────────────────────────────
        self.divider_top = QFrame(self.hero_card)
        self.divider_top.setFrameShape(QFrame.Shape.HLine)
        self.divider_top.setFrameShadow(QFrame.Shadow.Plain)
        self.divider_top.setFixedHeight(1)
        card_layout.addWidget(self.divider_top)

        # ── 2. Segmented Switcher (Video vs Music) ───────────────────────────
        self.tab_container = QFrame(self.hero_card)
        self.tab_container.setObjectName("SegmentedTabContainer")
        self.tab_container.setFixedHeight(38)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(3, 3, 3, 3)
        tab_layout.setSpacing(6)

        self.tab_video_btn = QPushButton(tr('tab_video', 'Video'), self.tab_container)
        self.tab_video_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_video_btn.setCheckable(True)
        self.tab_video_btn.setChecked(True)
        self.tab_video_btn.setFixedHeight(30)
        self.tab_video_btn.setIconSize(QSize(16, 16))
        self.tab_video_btn.clicked.connect(lambda: self._on_tab_changed("video"))
        tab_layout.addWidget(self.tab_video_btn)

        self.tab_audio_btn = QPushButton(tr('tab_music', 'Music'), self.tab_container)
        self.tab_audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_audio_btn.setCheckable(True)
        self.tab_audio_btn.setFixedHeight(30)
        self.tab_audio_btn.setIconSize(QSize(16, 16))
        self.tab_audio_btn.clicked.connect(lambda: self._on_tab_changed("audio"))
        tab_layout.addWidget(self.tab_audio_btn)

        card_layout.addWidget(self.tab_container)

        # ── 3. Quality Tiles Section ──────────────────────────────────────────
        quality_header_layout = QHBoxLayout()
        quality_header_layout.setContentsMargins(0, 0, 0, 0)
        quality_header_layout.setSpacing(8)

        self.quality_header_icon = QLabel(self.hero_card)
        self.quality_header_icon.setFixedSize(16, 16)
        quality_header_layout.addWidget(self.quality_header_icon)

        self.quality_section_header = QLabel(tr('choose_video_quality', 'Choose quality:'), self.hero_card)
        q_hdr_font = QFont()
        q_hdr_font.setPointSize(10)
        q_hdr_font.setBold(True)
        self.quality_section_header.setFont(q_hdr_font)
        quality_header_layout.addWidget(self.quality_section_header)
        quality_header_layout.addStretch()

        card_layout.addLayout(quality_header_layout)

        self.quality_grid = QualityGridWidget(self.hero_card)
        self.quality_grid.quality_selected.connect(self._on_quality_tile_selected)
        card_layout.addWidget(self.quality_grid)

        # Hidden underlying QComboBox for backwards compatibility (NEVER shown)
        self.format_combo = QComboBox(self.hero_card)
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.format_combo.hide()
        self.format_combo.currentIndexChanged.connect(self._on_format_combo_index_changed)
        card_layout.addWidget(self.format_combo)

        # ── 4. Subtitle Section (Clean Header + Full width Combobox) ──────────
        self.sub_section = QFrame(self.hero_card)
        self.sub_section.setObjectName("SubtitleSection")
        sub_layout = QVBoxLayout(self.sub_section)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(6)

        sub_header_layout = QHBoxLayout()
        sub_header_layout.setContentsMargins(0, 0, 0, 0)
        sub_header_layout.setSpacing(8)

        self.sub_header_icon = QLabel(self.sub_section)
        self.sub_header_icon.setFixedSize(16, 16)
        sub_header_layout.addWidget(self.sub_header_icon)

        self.sub_header_lbl = QLabel(tr('subtitles_header', 'Subtitles:'), self.sub_section)
        sub_hdr_font = QFont()
        sub_hdr_font.setPointSize(10)
        sub_hdr_font.setBold(True)
        self.sub_header_lbl.setFont(sub_hdr_font)
        sub_header_layout.addWidget(self.sub_header_lbl)
        sub_header_layout.addStretch()

        sub_layout.addLayout(sub_header_layout)

        self.sub_combo = QComboBox(self.sub_section)
        self.sub_combo.setFixedHeight(34)
        self.sub_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.sub_combo.setIconSize(QSize(16, 16))
        self.sub_combo.currentIndexChanged.connect(self._on_sub_combo_changed)
        sub_layout.addWidget(self.sub_combo)

        # Backward compatibility dummy checkbox
        self.sub_cb = QCheckBox(self.sub_section)
        self.sub_cb.hide()

        card_layout.addWidget(self.sub_section)

        # ── 5. Download Folder Section (Two Rows: Header row + Path Input & Button)
        self.folder_section = QFrame(self.hero_card)
        self.folder_section.setObjectName("FolderSection")
        folder_layout = QVBoxLayout(self.folder_section)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(6)

        folder_header_layout = QHBoxLayout()
        folder_header_layout.setContentsMargins(0, 0, 0, 0)
        folder_header_layout.setSpacing(8)

        self.folder_header_icon = QLabel(self.folder_section)
        self.folder_header_icon.setFixedSize(16, 16)
        folder_header_layout.addWidget(self.folder_header_icon)

        self.folder_header_lbl = QLabel(tr('save_directory_label', 'Save Directory:'), self.folder_section)
        f_hdr_font = QFont()
        f_hdr_font.setPointSize(10)
        f_hdr_font.setBold(True)
        self.folder_header_lbl.setFont(f_hdr_font)
        folder_header_layout.addWidget(self.folder_header_lbl)
        folder_header_layout.addStretch()

        folder_layout.addLayout(folder_header_layout)

        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        folder_row.setSpacing(10)

        self.folder_path_input = QLineEdit(self.folder_section)
        self.folder_path_input.setReadOnly(True)
        self.folder_path_input.setFixedHeight(34)
        folder_row.addWidget(self.folder_path_input, stretch=1)

        self.folder_change_btn = QPushButton(tr('btn_change_folder', 'Change'), self.folder_section)
        self.folder_change_btn.setObjectName("FolderChangeBtn")
        self.folder_change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_change_btn.setFixedHeight(34)
        self.folder_change_btn.setIconSize(QSize(16, 16))
        self.folder_change_btn.clicked.connect(self._on_change_folder_clicked)
        folder_row.addWidget(self.folder_change_btn)

        folder_layout.addLayout(folder_row)
        card_layout.addWidget(self.folder_section)

        # ── Bottom Divider ────────────────────────────────────────────────────
        self.divider_bottom = QFrame(self.hero_card)
        self.divider_bottom.setFrameShape(QFrame.Shape.HLine)
        self.divider_bottom.setFrameShadow(QFrame.Shadow.Plain)
        self.divider_bottom.setFixedHeight(1)
        card_layout.addWidget(self.divider_bottom)

        # ── 6. Bottom Controls: Remember Choice + Cancel + Download Now ───────
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 4, 0, 0)
        controls_layout.setSpacing(14)

        self.remember_choice_cb = QCheckBox(tr("remember_my_choice", "Always remember my format choice"), self.hero_card)
        self.remember_choice_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remember_choice_cb.toggled.connect(self.on_remember_choice_toggled)
        controls_layout.addWidget(self.remember_choice_cb)

        controls_layout.addStretch()

        self.cancel_btn = QPushButton(tr('btn_cancel', 'Cancel'), self.hero_card)
        self.cancel_btn.setObjectName("btn_cancel_hero")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setIconSize(QSize(16, 16))
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        controls_layout.addWidget(self.cancel_btn)

        self.download_btn = QPushButton(tr('start_download', 'Download Now'), self.hero_card)
        self.download_btn.setObjectName("btn_download_hero")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setFixedHeight(38)
        self.download_btn.setIconSize(QSize(18, 18))
        self.download_btn.clicked.connect(self._on_download_clicked)
        controls_layout.addWidget(self.download_btn)

        card_layout.addLayout(controls_layout)
        root_layout.addWidget(self.hero_card)

        self.update_theme()

    def _load_remember_state(self):
        remember_checked = self.main_app.settings_manager.get("remember_format_choice", False)
        self.remember_choice_cb.setChecked(remember_checked)

    def _on_tab_changed(self, mode: str):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        if mode == "video":
            self.tab_video_btn.setChecked(True)
            self.tab_audio_btn.setChecked(False)
            self.quality_section_header.setText(tr('choose_video_quality', 'اختر الجودة:'))
            self.quality_header_icon.setPixmap(get_colored_icon("assets/icons/clapperboard.svg", text_primary).pixmap(16, 16))
        else:
            self.tab_video_btn.setChecked(False)
            self.tab_audio_btn.setChecked(True)
            self.quality_section_header.setText(tr('choose_audio_quality', 'اختر جودة الصوت:'))
            self.quality_header_icon.setPixmap(get_colored_icon("assets/icons/music.svg", text_primary).pixmap(16, 16))
        self.quality_grid.set_mode(mode)
        self._apply_tab_styles()

    def _on_quality_tile_selected(self, global_idx, fmt_info):
        self._current_selected_format = fmt_info
        from gui.components.quality_tiles import QualityTileWidget
        tile_helper = QualityTileWidget(0, fmt_info)
        title_name = tile_helper._parse_clean_title()
        size_str = tile_helper._parse_clean_size()
        badge_prefix = tr('selected_quality_badge', 'Selected Quality:')
        accent = get_accent_hex()
        self.badge_icon_lbl.setPixmap(get_colored_icon("assets/icons/sparkles.svg", accent).pixmap(14, 14))
        self.badge_icon_lbl.show()
        if size_str and size_str != tr("size_unknown", "Unknown") and "Unknown" not in size_str:
            badge_text = f"{badge_prefix} {title_name} (~{size_str})"
        else:
            badge_text = f"{badge_prefix} {title_name}"
        self.quality_badge_lbl.setText(badge_text)

        # Sync underlying format_combo
        if 0 <= global_idx < self.format_combo.count():
            if self.format_combo.currentIndex() != global_idx:
                self.format_combo.blockSignals(True)
                self.format_combo.setCurrentIndex(global_idx)
                self.format_combo.blockSignals(False)
                self.save_format_preference()

    def _on_format_combo_index_changed(self, idx):
        if idx >= 0:
            code = self.format_combo.itemData(idx)
            if code:
                self.quality_grid.select_by_format_code(str(code))
                self.save_format_preference()

    def _on_change_folder_clicked(self):
        current_dir = self.main_app.last_save_dir or os.path.join(os.path.expanduser("~"), "Downloads")
        new_dir = QFileDialog.getExistingDirectory(self, tr("dialog_save_media_as", "Select Save Folder"), current_dir)
        if new_dir:
            self.main_app.last_save_dir = new_dir
            self.folder_path_input.setText(new_dir)
            self.folder_path_input.setToolTip(new_dir)
            if hasattr(self.main_app, 'save_settings'):
                self.main_app.save_settings(new_dir)

    def _on_download_clicked(self):
        self.download_requested.emit()

    def _on_cancel_clicked(self):
        self.cancel_requested.emit()

    def populate(self, title, duration_secs, image_data, format_list, subtitles_dict, extra_info=None):
        self.clean_title = clean_and_shorten_title(title)
        self._format_list = format_list

        self.title_label.setText(title)
        self.title_label.setToolTip(title)

        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        sec_color = "#94a3b8" if is_dark else "#64748b"

        if extra_info:
            uploader = extra_info.get('uploader', '')
            view_count = extra_info.get('view_count')
            upload_date = extra_info.get('upload_date', '')

            if uploader:
                self.channel_icon_lbl.setPixmap(get_colored_icon("assets/icons/user.svg", sec_color).pixmap(14, 14))
                self.channel_label.setText(uploader)
                self.channel_icon_lbl.show()
                self.channel_label.show()
            else:
                self.channel_icon_lbl.hide()
                self.channel_label.hide()

            views_str = format_views(view_count)
            date_str = get_relative_time(upload_date)

            if views_str:
                self.views_sep_lbl.setVisible(bool(uploader))
                self.views_icon_lbl.setPixmap(get_colored_icon("assets/icons/eye.svg", sec_color).pixmap(14, 14))
                self.views_label.setText(views_str)
                self.views_icon_lbl.show()
                self.views_label.show()
            else:
                self.views_sep_lbl.hide()
                self.views_icon_lbl.hide()
                self.views_label.hide()

            if date_str:
                self.date_sep_lbl.setVisible(bool(uploader or views_str))
                self.date_icon_lbl.setPixmap(get_colored_icon("assets/icons/calendar.svg", sec_color).pixmap(14, 14))
                self.date_label.setText(date_str)
                self.date_icon_lbl.show()
                self.date_label.show()
            else:
                self.date_sep_lbl.hide()
                self.date_icon_lbl.hide()
                self.date_label.hide()
        else:
            self.channel_icon_lbl.hide()
            self.channel_label.hide()
            self.views_sep_lbl.hide()
            self.views_icon_lbl.hide()
            self.views_label.hide()
            self.date_sep_lbl.hide()
            self.date_icon_lbl.hide()
            self.date_label.hide()

        m, s = divmod(duration_secs or 0, 60)
        h, m = divmod(m, 60)
        self.duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self.thumb_label.set_duration_text(self.duration_str)

        if image_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.thumb_label.setPixmap(pixmap)
                self.thumb_label._pixmap = pixmap
                self.thumb_label.show()

        # Populate underlying combo for backwards compatibility
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for item in format_list:
            if item.get('type') == 'separator':
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(item.get('label', ''), item.get('format_code', ''))
        self.format_combo.hide()
        self.format_combo.setEnabled(True)
        self.format_combo.blockSignals(False)

        # Populate quality grid
        self.quality_grid.set_formats(format_list)

        # Populate subtitles
        self._populate_subtitles(subtitles_dict)

        # Update download path section
        mgr = self.main_app.settings_manager
        dl_type = mgr.get("download_path_type", "downloads")
        if dl_type == "always_ask":
            self.folder_section.hide()
        else:
            self.folder_section.show()
            current_dir = self.main_app.last_save_dir or mgr.get("custom_path") or os.path.join(os.path.expanduser("~"), "Downloads")
            self.folder_path_input.setText(current_dir)
            self.folder_path_input.setToolTip(current_dir)

        # Auto select saved format preference
        self.auto_select_saved_format()

        # Reset tab to video
        self._on_tab_changed("video")

        self.download_btn.setEnabled(True)
        self.sub_section.show()
        self.hero_card.show()
        self.show()
        self.update_theme()

    def show_placeholder(self, title="", pixmap=None, extra_info=None):
        if title:
            self.clean_title = clean_and_shorten_title(title)
            self.title_label.setText(title)
            self.title_label.setToolTip(title)

        if pixmap and not pixmap.isNull():
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label._pixmap = pixmap
            self.thumb_label.show()
        else:
            self.thumb_label.show_loading()

        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        sec_color = "#94a3b8" if is_dark else "#64748b"

        if extra_info:
            uploader = extra_info.get('uploader', '')
            if uploader:
                self.channel_icon_lbl.setPixmap(get_colored_icon("assets/icons/user.svg", sec_color).pixmap(14, 14))
                self.channel_label.setText(uploader)
                self.channel_icon_lbl.show()
                self.channel_label.show()
            views_str = extra_info.get('view_count', '')
            if views_str:
                self.views_sep_lbl.setVisible(bool(uploader))
                self.views_icon_lbl.setPixmap(get_colored_icon("assets/icons/eye.svg", sec_color).pixmap(14, 14))
                self.views_label.setText(str(views_str))
                self.views_icon_lbl.show()
                self.views_label.show()
            dur = extra_info.get('duration')
            if dur:
                m, s = divmod(dur or 0, 60)
                h, m = divmod(m, 60)
                self.duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                self.thumb_label.set_duration_text(self.duration_str)

        accent = get_accent_hex()
        self.badge_icon_lbl.setPixmap(get_colored_icon("assets/icons/hourglass.svg", accent).pixmap(14, 14))
        self.badge_icon_lbl.show()
        self.quality_badge_lbl.setText(tr("search_loading_formats", "Fetching formats... please wait."))
        self.download_btn.setEnabled(False)

        # Subtitles placeholder state
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()
        hour_icon = get_colored_icon("assets/icons/hourglass.svg", "#94a3b8")
        self.sub_combo.addItem(hour_icon, tr("fetching_subtitles", "Fetching subtitles..."), "")
        self.sub_combo.setEnabled(False)
        self.sub_cb.setEnabled(False)
        self.sub_cb.setChecked(False)
        self.sub_combo.blockSignals(False)
        self.sub_section.show()

        # Update download path section
        mgr = self.main_app.settings_manager
        dl_type = mgr.get("download_path_type", "downloads")
        if dl_type == "always_ask":
            self.folder_section.hide()
        else:
            self.folder_section.show()
            current_dir = self.main_app.last_save_dir or mgr.get("custom_path") or os.path.join(os.path.expanduser("~"), "Downloads")
            self.folder_path_input.setText(current_dir)
            self.folder_path_input.setToolTip(current_dir)

        self._on_tab_changed("video")
        self.quality_grid.show_skeleton(4)
        self.quality_grid.show()
        self.hero_card.show()
        self.show()
        self.update_theme()

    def _populate_subtitles(self, subtitles_dict):
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()

        if not subtitles_dict:
            self._disable_subs()
            self.sub_combo.blockSignals(False)
            return

        filtered = {
            lang: info for lang, info in subtitles_dict.items()
            if "live_chat" not in lang.lower() and "chat" not in lang.lower()
        }
        if not filtered:
            self._disable_subs()
            self.sub_combo.blockSignals(False)
            return

        primary_lang = self.main_app.settings_manager.get("primary_sub_lang", "ar")
        secondary_lang = self.main_app.settings_manager.get("secondary_sub_lang", "en")

        def get_lang_priority(lang_code):
            base = lang_code.split('-')[0].lower()
            if base == primary_lang.lower():
                return 0
            elif base == secondary_lang.lower():
                return 1
            return 2

        manual_subs, original_auto_subs, other_auto_subs = [], [], []
        for lang_code, s_info in filtered.items():
            is_orig = "-orig" in lang_code.lower() or "-original" in lang_code.lower()
            stype = s_info.get('type', 'Manual') if isinstance(s_info, dict) else 'Manual'
            if stype == 'Manual':
                manual_subs.append((lang_code, s_info))
            elif stype == 'Auto' and is_orig:
                original_auto_subs.append((lang_code, s_info))
            else:
                other_auto_subs.append((lang_code, s_info))

        top_group = manual_subs if manual_subs else original_auto_subs
        bottom_group = (original_auto_subs + other_auto_subs) if manual_subs else other_auto_subs
        top_group.sort(key=lambda x: get_lang_priority(x[0]))
        bottom_group.sort(key=lambda x: get_lang_priority(x[0]))

        # First option: None
        cancel_icon = get_colored_icon("assets/icons/cancel.svg", "#ef4444")
        self.sub_combo.addItem(cancel_icon, tr('none_subtitle', 'None'), "")

        globe_icon = get_colored_icon("assets/icons/globe.svg", "#3b82f6")
        best_match_idx = -1
        all_subs = top_group + bottom_group
        for idx, (lang_code, s_info) in enumerate(all_subs, start=1):
            is_orig = "-orig" in lang_code.lower() or "-original" in lang_code.lower()
            type_val = s_info.get('type', 'Manual') if isinstance(s_info, dict) else 'Manual'
            code_val = s_info.get('code', lang_code) if isinstance(s_info, dict) else lang_code
            type_tag = tr("manual_tag", "manual") if type_val == 'Manual' else tr("auto_tag", "auto")
            if is_orig:
                type_str = f"{tr('original_tag', 'original')} - {type_tag}"
            else:
                type_str = type_tag
            lang_name = get_full_language_name(lang_code)
            label = f"{lang_name} ({type_str})"
            self.sub_combo.addItem(globe_icon, label, code_val)

            base = lang_code.split('-')[0].lower()
            if best_match_idx == -1 and base == primary_lang.lower():
                best_match_idx = idx

        # Auto select preferred language or top item
        if best_match_idx != -1:
            self.sub_combo.setCurrentIndex(best_match_idx)
            self.sub_cb.setChecked(True)
        elif self.sub_combo.count() > 1:
            self.sub_combo.setCurrentIndex(1)
            self.sub_cb.setChecked(True)
        else:
            self.sub_combo.setCurrentIndex(0)
            self.sub_cb.setChecked(False)

        self.sub_combo.setEnabled(True)
        self.sub_combo.show()
        self.sub_combo.blockSignals(False)

    def _disable_subs(self):
        self.sub_combo.blockSignals(True)
        self.sub_combo.clear()
        cancel_icon = get_colored_icon("assets/icons/cancel.svg", "#ef4444")
        self.sub_combo.addItem(cancel_icon, tr('no_subtitles_found', 'No subtitles available'), "")
        self.sub_combo.setEnabled(False)
        self.sub_cb.setChecked(False)
        self.sub_combo.blockSignals(False)

    def _on_sub_combo_changed(self, idx):
        if idx >= 0:
            data = self.sub_combo.itemData(idx)
            has_sub = bool(data)
            self.sub_cb.setChecked(has_sub)

    def toggle_sub_combo(self, checked):
        pass

    def _apply_tab_styles(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        bg_container = "#080e1b" if is_dark else "#f1f5f9"
        border_container = "#1e293b" if is_dark else "#e2e8f0"
        self.tab_container.setStyleSheet(f"""
            QFrame#SegmentedTabContainer {{
                background-color: {bg_container};
                border: 1px solid {border_container};
                border-radius: 12px;
            }}
        """)
        active_style = f"""
            QPushButton {{
                background-color: {'#152238' if is_dark else '#ffffff'};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border: 1px solid {'#334155' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                font-weight: bold;
                padding: 4px 14px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background: transparent;
                color: {'#94a3b8' if is_dark else '#64748b'};
                border: none;
                border-radius: 8px;
                font-weight: 500;
                padding: 4px 14px;
            }}
            QPushButton:hover {{
                color: {'#ffffff' if is_dark else '#0f172a'};
            }}
        """
        self.tab_video_btn.setStyleSheet(active_style if self.tab_video_btn.isChecked() else inactive_style)
        self.tab_audio_btn.setStyleSheet(active_style if self.tab_audio_btn.isChecked() else inactive_style)

        text_active = "#ffffff" if is_dark else "#0f172a"
        text_inactive = "#94a3b8" if is_dark else "#64748b"
        self.tab_video_btn.setIcon(get_colored_icon("assets/icons/video.svg", text_active if self.tab_video_btn.isChecked() else text_inactive))
        self.tab_audio_btn.setIcon(get_colored_icon("assets/icons/music.svg", text_active if self.tab_audio_btn.isChecked() else text_inactive))

    def update_theme(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        accent = get_accent_hex()

        bg_card = "#0d1527" if is_dark else "#ffffff"
        border_card = "rgba(51, 65, 85, 0.6)" if is_dark else "#cbd5e1"
        if getattr(self, 'is_dialog', False):
            self.hero_card.setStyleSheet("""
                QFrame#MediaHeroCard {
                    background-color: transparent;
                    border: none;
                }
            """)
        else:
            self.hero_card.setStyleSheet(f"""
                QFrame#MediaHeroCard {{
                    background-color: {bg_card};
                    border: 1.5px solid {border_card};
                    border-radius: 16px;
                }}
            """)

        self.badge_frame.setStyleSheet(f"""
            QFrame#QualitySummaryBadge {{
                background-color: rgba(249, 115, 22, 0.12);
                border: 1px solid {accent};
                border-radius: 14px;
            }}
        """)
        self.quality_badge_lbl.setStyleSheet(f"color: {accent}; font-weight: bold;")

        divider_color = "#243249" if is_dark else "#e2e8f0"
        divider_style = f"background-color: {divider_color}; border: none;"
        self.divider_top.setStyleSheet(divider_style)
        self.divider_bottom.setStyleSheet(divider_style)

        self._apply_tab_styles()

        self.sub_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {'#080e1b' if is_dark else '#f8fafc'};
                color: {'#f1f5f9' if is_dark else '#0f172a'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {'#334155' if is_dark else '#94a3b8'};
            }}
            QComboBox:disabled {{
                background-color: {'#060a14' if is_dark else '#f1f5f9'};
                color: {'#475569' if is_dark else '#94a3b8'};
                border-color: {'#151f30' if is_dark else '#e2e8f0'};
            }}
            QComboBox QAbstractItemView {{
                background-color: {'#0d1527' if is_dark else '#ffffff'};
                color: {'#f1f5f9' if is_dark else '#0f172a'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                selection-background-color: {'#1e293b' if is_dark else '#e2e8f0'};
                selection-color: {'#ffffff' if is_dark else '#0f172a'};
            }}
        """)

        self.folder_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {'#080e1b' if is_dark else '#f8fafc'};
                color: {'#94a3b8' if is_dark else '#475569'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
            }}
        """)
        self.folder_change_btn.setStyleSheet(f"""
            QPushButton#FolderChangeBtn {{
                background-color: {'#152238' if is_dark else '#e2e8f0'};
                color: {'#f8fafc' if is_dark else '#1e293b'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#FolderChangeBtn:hover {{
                background-color: {'#1e293b' if is_dark else '#cbd5e1'};
                border-color: {'#334155' if is_dark else '#94a3b8'};
            }}
        """)

        self.cancel_btn.setStyleSheet(f"""
            QPushButton#btn_cancel_hero {{
                background: transparent;
                color: {'#94a3b8' if is_dark else '#64748b'};
                border: 1.5px solid {'#334155' if is_dark else '#cbd5e1'};
                border-radius: 19px;
                padding: 6px 24px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_cancel_hero:hover {{
                background: {'rgba(51, 65, 85, 0.3)' if is_dark else '#f1f5f9'};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border-color: {'#64748b' if is_dark else '#94a3b8'};
            }}
        """)

        self.download_btn.setStyleSheet(f"""
            QPushButton#btn_download_hero {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.4 #6366f1, stop:1 #e11d48);
                color: #ffffff;
                border: 1px solid transparent;
                border-radius: 19px;
                padding: 6px 28px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#btn_download_hero:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:0.4 #4f46e5, stop:1 #be123c);
            }}
            QPushButton#btn_download_hero:disabled {{
                background: {'#334155' if is_dark else '#cbd5e1'};
                color: {'#64748b' if is_dark else '#94a3b8'};
            }}
        """)

        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        text_secondary = "#94a3b8" if is_dark else "#64748b"
        self.title_label.setStyleSheet(f"color: {text_primary};")
        self.channel_label.setStyleSheet(f"color: {text_secondary}; font-weight: bold; font-size: 12px;")
        self.views_sep_lbl.setStyleSheet(f"color: {text_secondary}; font-weight: bold;")
        self.views_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
        self.date_sep_lbl.setStyleSheet(f"color: {text_secondary}; font-weight: bold;")
        self.date_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
        self.meta_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
        self.quality_section_header.setStyleSheet(f"color: {text_primary};")
        self.sub_header_lbl.setStyleSheet(f"color: {text_primary};")
        self.folder_header_lbl.setStyleSheet(f"color: {text_primary};")
        self.remember_choice_cb.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")

        # Tint icons
        self.sub_header_icon.setPixmap(get_colored_icon("assets/icons/subtitles.svg", text_primary).pixmap(16, 16))
        self.folder_header_icon.setPixmap(get_colored_icon("assets/icons/folder.svg", text_primary).pixmap(16, 16))
        self.folder_change_btn.setIcon(get_colored_icon("assets/icons/folder-open.svg", text_primary))
        self.cancel_btn.setIcon(get_colored_icon("assets/icons/cancel.svg", text_secondary))
        self.download_btn.setIcon(get_colored_icon("assets/icons/download.svg", "#ffffff"))

        mode = getattr(self.quality_grid, 'mode', 'video')
        q_icon = "assets/icons/clapperboard.svg" if mode == "video" else "assets/icons/music.svg"
        self.quality_header_icon.setPixmap(get_colored_icon(q_icon, text_primary).pixmap(16, 16))

        if hasattr(self, 'quality_grid') and hasattr(self.quality_grid, 'update_theme'):
            self.quality_grid.update_theme()

        if self.channel_label.isVisible():
            self.channel_icon_lbl.setPixmap(get_colored_icon("assets/icons/user.svg", text_secondary).pixmap(14, 14))
        if self.views_label.isVisible():
            self.views_icon_lbl.setPixmap(get_colored_icon("assets/icons/eye.svg", text_secondary).pixmap(14, 14))
        if self.date_label.isVisible():
            self.date_icon_lbl.setPixmap(get_colored_icon("assets/icons/calendar.svg", text_secondary).pixmap(14, 14))

    def get_selected_sub_lang(self):
        if hasattr(self, 'sub_combo') and self.sub_combo.isEnabled():
            code = self.sub_combo.currentData()
            if code:
                return code
        if hasattr(self, 'sub_cb') and self.sub_cb.isChecked():
            return self.sub_combo.currentData()
        return None

    def reset(self):
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.channel_icon_lbl.hide()
        self.channel_label.setText("")
        self.channel_label.hide()
        self.views_sep_lbl.hide()
        self.views_icon_lbl.hide()
        self.views_label.setText("")
        self.views_label.hide()
        self.date_sep_lbl.hide()
        self.date_icon_lbl.hide()
        self.date_label.setText("")
        self.date_label.hide()
        self.meta_label.setText("")
        self.meta_label.hide()
        self.duration_label.setText("")
        self.thumb_label.hide()
        self.thumb_label.clear()
        self.badge_icon_lbl.clear()
        self.quality_badge_lbl.setText("")
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.sub_cb.hide()
        self.sub_combo.hide()
        self.hero_card.hide()
        self.hide()


class PlaylistItemSkeleton(QFrame):
    """
    كارت فيديو هيكلي نابض (Pulse Shimmer) يظهر داخل قائمة التشغيل أثناء جلب العناصر.
    يحاكي تصميم كارت الفيديو الحقيقي (مؤشر التحديد، رقم الترتيب، الصورة المصغرة، سطر العنوان والمدة).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlaylistItemSkeleton")
        self.setFixedHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._alpha = 90
        self._direction = 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse_tick)

        self._initUI()
        self._apply_style()

    def _initUI(self):
        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(14, 8, 16, 8)
        row_layout.setSpacing(14)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 1. Circular check indicator placeholder
        self.check_box = QFrame(self)
        self.check_box.setFixedSize(18, 18)
        row_layout.addWidget(self.check_box)

        # 2. Number placeholder
        self.num_box = QFrame(self)
        self.num_box.setFixedSize(18, 14)
        row_layout.addWidget(self.num_box)

        # 3. Video thumbnail placeholder (80x45)
        self.thumb_box = QFrame(self)
        self.thumb_box.setFixedSize(80, 45)
        row_layout.addWidget(self.thumb_box)

        # 4. Details lines placeholder
        details_layout = QVBoxLayout()
        details_layout.setSpacing(6)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_bar = QFrame(self)
        self.title_bar.setFixedHeight(14)
        self.title_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.title_bar.setMaximumWidth(280)
        details_layout.addWidget(self.title_bar)

        self.meta_bar = QFrame(self)
        self.meta_bar.setFixedHeight(10)
        self.meta_bar.setFixedWidth(130)
        details_layout.addWidget(self.meta_bar)

        row_layout.addLayout(details_layout, stretch=1)

    def _pulse_tick(self):
        self._alpha += 4 * self._direction
        if self._alpha >= 170:
            self._direction = -1
        elif self._alpha <= 70:
            self._direction = 1
        self._apply_style()

    def _get_is_dark(self):
        p = self.parent()
        while p:
            if hasattr(p, 'main_app') and hasattr(p.main_app, 'theme_manager'):
                return p.main_app.theme_manager.get_actual_theme() == "dark"
            p = p.parent()
        return get_current_theme_color() == "#f1f5f9"

    def _apply_style(self):
        is_dark = self._get_is_dark()
        a_frac = self._alpha / 255.0

        if is_dark:
            bg_row = f"rgba(13, 21, 39, {0.6 + a_frac * 0.3:.2f})"
            border_row = f"rgba(51, 65, 85, {0.4 + a_frac * 0.4:.2f})"
            inner_fill = f"rgba(71, 85, 105, {a_frac:.2f})"
        else:
            bg_row = f"rgba(241, 245, 249, {0.6 + a_frac * 0.3:.2f})"
            border_row = f"rgba(203, 213, 225, {0.5 + a_frac * 0.4:.2f})"
            inner_fill = f"rgba(148, 163, 184, {a_frac * 0.8:.2f})"

        self.setStyleSheet(f"""
            QFrame#PlaylistItemSkeleton {{
                background-color: {bg_row};
                border: 1.5px solid {border_row};
                border-radius: 10px;
            }}
        """)
        self.check_box.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 9px;")
        self.num_box.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 3px;")
        self.thumb_box.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 6px;")
        self.title_bar.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 4px;")
        self.meta_bar.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 3px;")

    def showEvent(self, event):
        self._alpha = 90
        self._direction = 1
        self._apply_style()
        self.timer.start(35)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)


class PlaylistItemRow(QFrame):
    """
    بطاقة عصرية فردية لكل فيديو داخل قائمة التشغيل.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, index, entry, show_thumbnails=True, parent=None):
        super().__init__(parent)
        self.index = index
        self.entry = entry
        self.show_thumbnails = show_thumbnails
        self.setObjectName("PlaylistItemRow")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._initUI()

    def _initUI(self):
        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(14, 8, 16, 8)
        row_layout.setSpacing(14)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 1. Circular check indicator
        self.cb = QCheckBox(self)
        self.cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cb.setChecked(True)
        self.cb.toggled.connect(self._on_toggled)
        row_layout.addWidget(self.cb)

        # 2. Number index: 1. , 2. , etc.
        self.num_lbl = QLabel(f"{self.index + 1}.", self)
        num_font = QFont()
        num_font.setPointSize(10)
        num_font.setBold(True)
        self.num_lbl.setFont(num_font)
        self.num_lbl.setFixedWidth(24)
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(self.num_lbl)

        # 3. Video thumbnail (16:9 ratio, 80x45)
        self.thumb_lbl = ResponsiveImage(min_height=45, spinner_size=16)
        self.thumb_lbl.setFixedSize(80, 45)
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.show_thumbnails:
            self.thumb_lbl.show_loading()
            row_layout.addWidget(self.thumb_lbl)
        else:
            self.thumb_lbl.hide()

        # Duration parsing
        dur_raw = self.entry.get('duration')
        self.dur_str = ""
        if dur_raw:
            if isinstance(dur_raw, (int, float)):
                sec = int(dur_raw)
                m, s = divmod(sec, 60)
                h, m = divmod(m, 60)
                self.dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            elif isinstance(dur_raw, str):
                if ":" in dur_raw:
                    self.dur_str = dur_raw
                else:
                    try:
                        sec = int(float(dur_raw))
                        m, s = divmod(sec, 60)
                        h, m = divmod(m, 60)
                        self.dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    except Exception:
                        self.dur_str = dur_raw

        # 4. Details layout
        details_layout = QVBoxLayout()
        details_layout.setSpacing(3)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = ElidedLabel(self.entry.get('title', ''), self)
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self.title_lbl.setFont(title_font)
        details_layout.addWidget(self.title_lbl)

        # Meta row: duration + channel/uploader
        uploader = self.entry.get('uploader') or self.entry.get('channel') or ""

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        meta_row.setContentsMargins(0, 0, 0, 0)

        meta_font = QFont()
        meta_font.setPointSize(9)

        if self.dur_str:
            self.clock_icon = QLabel(self)
            self.clock_icon.setFixedSize(12, 12)
            meta_row.addWidget(self.clock_icon)

            self.dur_lbl = QLabel(self.dur_str, self)
            self.dur_lbl.setFont(meta_font)
            meta_row.addWidget(self.dur_lbl)

            if uploader:
                self.bullet_lbl = QLabel("•", self)
                self.bullet_lbl.setFont(meta_font)
                meta_row.addWidget(self.bullet_lbl)

        if uploader:
            self.uploader_lbl = QLabel(uploader, self)
            self.uploader_lbl.setFont(meta_font)
            meta_row.addWidget(self.uploader_lbl)

        meta_row.addStretch()
        details_layout.addLayout(meta_row)

        # Backward compatibility dummy
        meta_parts = []
        if self.dur_str:
            meta_parts.append(self.dur_str)
        if uploader:
            meta_parts.append(uploader)
        self.meta_lbl = QLabel("  •  ".join(meta_parts), self)
        self.meta_lbl.hide()

        row_layout.addLayout(details_layout, stretch=1)

        # Properties for backward compatibility with external code
        self.cb.setProperty("img_label", self.thumb_lbl)
        self.cb.setProperty("title_lbl", self.title_lbl)
        self.cb.setProperty("channel_lbl", self.meta_lbl)
        self.cb.setProperty("meta_lbl", self.meta_lbl)

    def _on_toggled(self, checked):
        self.update_style()
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.cb.setChecked(not self.cb.isChecked())
        super().mousePressEvent(event)

    def update_style(self, is_dark=None):
        if is_dark is None:
            main_app = getattr(self.parent(), 'main_app', None)
            if not main_app:
                p = self.parent()
                while p:
                    if hasattr(p, 'main_app'):
                        main_app = p.main_app
                        break
                    p = p.parent()
            if main_app and hasattr(main_app, 'theme_manager'):
                is_dark = (main_app.theme_manager.get_actual_theme() == "dark")
            else:
                is_dark = True

        accent = get_accent_hex()
        is_checked = self.cb.isChecked()
        bg_card = "#0b1424" if is_dark else "#f8fafc"
        border_card = accent if is_checked else ("#1e293b" if is_dark else "#e2e8f0")
        self.setStyleSheet(f"""
            QFrame#PlaylistItemRow {{
                background-color: {bg_card};
                border: 1.5px solid {border_card};
                border-radius: 10px;
            }}
            QFrame#PlaylistItemRow:hover {{
                border-color: {accent if is_checked else ('#334155' if is_dark else '#cbd5e1')};
            }}
            QCheckBox {{
                background: transparent;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {'#152238' if is_dark else '#e2e8f0'};
                border: 1.5px solid {'#475569' if is_dark else '#94a3b8'};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border: 1.5px solid {accent};
                image: url(assets/icons/check.svg);
            }}
        """)
        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        text_secondary = "#94a3b8" if is_dark else "#64748b"
        self.num_lbl.setStyleSheet(f"color: {text_secondary}; font-weight: bold; background: transparent; border: none;")
        self.title_lbl.setStyleSheet(f"color: {text_primary}; background: transparent; border: none;")
        self.meta_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 11px; background: transparent; border: none;")

        if hasattr(self, 'clock_icon'):
            self.clock_icon.setPixmap(get_colored_icon("assets/icons/clock.svg", text_secondary).pixmap(12, 12))
        if hasattr(self, 'dur_lbl'):
            self.dur_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 11px; background: transparent; border: none;")
        if hasattr(self, 'bullet_lbl'):
            self.bullet_lbl.setStyleSheet(f"color: {text_secondary}; font-weight: bold; background: transparent; border: none;")
        if hasattr(self, 'uploader_lbl'):
            self.uploader_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 11px; background: transparent; border: none;")


class PlaylistPanel(QWidget, FormatPreferencesMixin):
    """
    البطاقة الشاملة العصرية لمعاينة قائمة التشغيل وخيارات التنزيل (Modern Playlist Hero Card).
    تجمع تفاصيل القائمة، التبديل بين الفيديو والموسيقى، أزرار الجودات السريعة،
    خيارات الترجمة، كروت الفيديوهات، مسار الحفظ، وأزرار الإجراءات في إطار أنيق وموحد.
    """
    download_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, main_app, parent=None, is_dialog=False):
        super().__init__(parent)
        self.main_app = main_app
        self.is_dialog = is_dialog
        self.pl_checkboxes = []
        self.has_custom_pl_thumb = False
        self.loaded_pixmap = None
        self.clean_title = "playlist"
        self.current_mode = "video"  # "video" | "audio"
        self.quality_pills = []
        self._initUI()
        self._load_remember_state()

    def _initUI(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── The Unified Hero Card Frame ───────────────────────────────────────
        self.hero_card = QFrame(self)
        self.hero_card.setObjectName("MediaHeroCard")
        self.playlist_card = self.hero_card  # For backward-compatibility
        self.settings_card = self.hero_card  # For backward-compatibility
        card_layout = QVBoxLayout(self.hero_card)
        card_layout.setContentsMargins(22, 16, 22, 16)
        card_layout.setSpacing(12)

        # ── 1. Top Header: Thumbnail (Left) + Playlist Information (Right) ────
        header_widget = QWidget(self.hero_card)
        header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        # Thumbnail with Playlist badge overlay on the LEFT (200x112, 16:9 ratio)
        self.thumb_container = QWidget(self.hero_card)
        self.thumb_container.setFixedSize(200, 112)
        thumb_box = QVBoxLayout(self.thumb_container)
        thumb_box.setContentsMargins(0, 0, 0, 0)

        self.thumb_label = ResponsiveImage(min_height=112)
        self.thumb_label.setFixedSize(200, 112)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_box.addWidget(self.thumb_label)

        self.badge_playlist = QFrame(self.thumb_label)
        self.badge_playlist.setObjectName("BadgePlaylist")
        pl_badge_layout = QHBoxLayout(self.badge_playlist)
        pl_badge_layout.setContentsMargins(6, 2, 8, 2)
        pl_badge_layout.setSpacing(4)
        self.badge_pl_icon = QLabel(self.badge_playlist)
        self.badge_pl_icon.setFixedSize(12, 12)
        self.badge_pl_icon.setPixmap(get_colored_icon("assets/icons/playlist.svg", "#ffffff").pixmap(12, 12))
        pl_badge_layout.addWidget(self.badge_pl_icon)
        self.badge_pl_text = QLabel(tr('playlist_badge_text', 'Playlist'), self.badge_playlist)
        self.badge_pl_text.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 10px; border: none; background: transparent;")
        pl_badge_layout.addWidget(self.badge_pl_text)
        self.badge_playlist.setStyleSheet("""
            QFrame#BadgePlaylist {
                background-color: #ea580c;
                border-radius: 6px;
                border: none;
            }
        """)
        self.badge_playlist.adjustSize()
        self.badge_playlist.move(
            self.thumb_label.width() - self.badge_playlist.width() - 8,
            self.thumb_label.height() - self.badge_playlist.height() - 8
        )

        header_layout.addWidget(self.thumb_container, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Playlist Info on the RIGHT
        info_side_layout = QVBoxLayout()
        info_side_layout.setContentsMargins(0, 0, 0, 0)
        info_side_layout.setSpacing(4)

        self.title_label = QLabel('', self.hero_card)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setMaximumHeight(44)
        info_side_layout.addWidget(self.title_label)

        # Meta row: Count of videos
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)

        self.count_icon = QLabel(self.hero_card)
        self.count_icon.setFixedSize(14, 14)
        meta_row.addWidget(self.count_icon)

        self.count_label = QLabel('', self.hero_card)
        count_font = QFont()
        count_font.setPointSize(9)
        self.count_label.setFont(count_font)
        meta_row.addWidget(self.count_label)
        meta_row.addStretch()
        info_side_layout.addLayout(meta_row)
        info_side_layout.addStretch()

        # Selected Counter Badge (pill shape)
        badge_hlayout = QHBoxLayout()
        badge_hlayout.setContentsMargins(0, 0, 0, 0)

        self.badge_frame = QFrame(self.hero_card)
        self.badge_frame.setObjectName("QualitySummaryBadge")
        self.badge_frame.setFixedHeight(28)
        badge_box = QHBoxLayout(self.badge_frame)
        badge_box.setContentsMargins(10, 0, 12, 0)
        badge_box.setSpacing(6)

        self.badge_icon_lbl = QLabel(self.badge_frame)
        self.badge_icon_lbl.setFixedSize(14, 14)
        badge_box.addWidget(self.badge_icon_lbl)

        self.pl_counter_lbl = QLabel(self.badge_frame)
        self.pl_counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_font = QFont()
        b_font.setPointSize(9)
        b_font.setBold(True)
        self.pl_counter_lbl.setFont(b_font)
        badge_box.addWidget(self.pl_counter_lbl)

        badge_hlayout.addWidget(self.badge_frame)
        badge_hlayout.addStretch()
        info_side_layout.addLayout(badge_hlayout)

        header_layout.addLayout(info_side_layout, stretch=1)
        card_layout.addWidget(header_widget)

        # ── Top Divider ───────────────────────────────────────────────────────
        self.divider_top = QFrame(self.hero_card)
        self.divider_top.setFrameShape(QFrame.Shape.HLine)
        self.divider_top.setFrameShadow(QFrame.Shadow.Plain)
        self.divider_top.setFixedHeight(1)
        card_layout.addWidget(self.divider_top)

        # ── 2. Type Switcher & Quality Pills Row ─────────────────────────────
        quality_row = QHBoxLayout()
        quality_row.setContentsMargins(0, 0, 0, 0)
        quality_row.setSpacing(14)

        # Segmented Video vs Music Switcher
        self.tab_container = QFrame(self.hero_card)
        self.tab_container.setObjectName("SegmentedTabContainer")
        self.tab_container.setFixedHeight(36)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(3, 3, 3, 3)
        tab_layout.setSpacing(4)

        self.tab_video_btn = QPushButton(tr('tab_video', 'Video'), self.tab_container)
        self.tab_video_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_video_btn.setCheckable(True)
        self.tab_video_btn.setChecked(True)
        self.tab_video_btn.setFixedHeight(30)
        self.tab_video_btn.setIconSize(QSize(16, 16))
        self.tab_video_btn.clicked.connect(lambda: self._on_mode_changed("video"))
        tab_layout.addWidget(self.tab_video_btn)

        self.tab_audio_btn = QPushButton(tr('tab_music', 'Music'), self.tab_container)
        self.tab_audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_audio_btn.setCheckable(True)
        self.tab_audio_btn.setFixedHeight(30)
        self.tab_audio_btn.setIconSize(QSize(16, 16))
        self.tab_audio_btn.clicked.connect(lambda: self._on_mode_changed("audio"))
        tab_layout.addWidget(self.tab_audio_btn)

        quality_row.addWidget(self.tab_container)

        # Quality Pills Container
        self.quality_pills_container = QWidget(self.hero_card)
        self.pills_layout = QHBoxLayout(self.quality_pills_container)
        self.pills_layout.setContentsMargins(0, 0, 0, 0)
        self.pills_layout.setSpacing(8)
        quality_row.addWidget(self.quality_pills_container)
        quality_row.addStretch()

        card_layout.addLayout(quality_row)

        # Hidden underlying QComboBox for backwards compatibility
        self.format_combo = QComboBox(self.hero_card)
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.format_combo.hide()
        self.format_combo.currentIndexChanged.connect(self._on_format_combo_index_changed)
        card_layout.addWidget(self.format_combo)

        # ── Middle Divider ────────────────────────────────────────────────────
        self.divider_middle = QFrame(self.hero_card)
        self.divider_middle.setFrameShape(QFrame.Shape.HLine)
        self.divider_middle.setFrameShadow(QFrame.Shadow.Plain)
        self.divider_middle.setFixedHeight(1)
        card_layout.addWidget(self.divider_middle)

        # ── 3. Subtitles Checkbox Row ─────────────────────────────────────────
        sub_row_layout = QHBoxLayout()
        sub_row_layout.setContentsMargins(0, 0, 0, 0)
        sub_row_layout.setSpacing(8)

        self.sub_frame = QFrame(self.hero_card)
        self.sub_frame.setObjectName("PlaylistSubFrame")
        sub_layout = QHBoxLayout(self.sub_frame)
        sub_layout.setContentsMargins(14, 6, 14, 6)
        sub_layout.setSpacing(8)

        self.sub_cb = QCheckBox(tr('set_subtitles', 'Subtitles'), self.sub_frame)
        self.sub_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sub_cb.setIconSize(QSize(16, 16))
        self.sub_cb.setChecked(False)
        sub_layout.addWidget(self.sub_cb)

        self.sub_info_icon = QLabel(self.sub_frame)
        self.sub_info_icon.setFixedSize(16, 16)
        self.sub_info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.sub_info_icon.setToolTip(tr("sub_info_tooltip", "Subtitles will be downloaded if available"))
        sub_layout.addWidget(self.sub_info_icon)

        sub_row_layout.addWidget(self.sub_frame)
        sub_row_layout.addStretch()
        card_layout.addLayout(sub_row_layout)

        # ── 4. Videos List Section ────────────────────────────────────────────
        videos_header = QHBoxLayout()
        videos_header.setContentsMargins(0, 2, 0, 2)
        videos_header.setSpacing(8)

        self.videos_list_icon = QLabel(self.hero_card)
        self.videos_list_icon.setFixedSize(16, 16)
        videos_header.addWidget(self.videos_list_icon)

        self.videos_list_title = QLabel(tr('videos_list_header', 'Videos List:'), self.hero_card)
        v_title_font = QFont()
        v_title_font.setPointSize(10)
        v_title_font.setBold(True)
        self.videos_list_title.setFont(v_title_font)
        videos_header.addWidget(self.videos_list_title)

        videos_header.addStretch()

        self.btn_select_all = QPushButton(tr('select_all', 'Select All'), self.hero_card)
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.clicked.connect(self.select_all_items)
        videos_header.addWidget(self.btn_select_all)

        pipe_lbl = QLabel("|", self.hero_card)
        pipe_lbl.setStyleSheet("color: #475569; font-weight: bold;")
        videos_header.addWidget(pipe_lbl)

        self.btn_deselect_all = QPushButton(tr('deselect_all', 'Deselect All'), self.hero_card)
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        videos_header.addWidget(self.btn_deselect_all)

        card_layout.addLayout(videos_header)

        # Videos ScrollArea
        self.pl_scroll = QScrollArea(self.hero_card)
        self.pl_scroll.setWidgetResizable(True)
        pl_height = 200 if getattr(self, 'is_dialog', False) else 292
        self.pl_scroll.setFixedHeight(pl_height)
        self.pl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pl_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.pl_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._pl_container = QWidget()
        self._pl_container.setStyleSheet("background: transparent;")
        self.pl_items_layout = QVBoxLayout(self._pl_container)
        self.pl_items_layout.setContentsMargins(2, 4, 14, 4)
        self.pl_items_layout.setSpacing(8)
        self.pl_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.pl_scroll.setWidget(self._pl_container)
        card_layout.addWidget(self.pl_scroll)

        # Backward compatibility dummy
        self.pl_select_all_cb = QCheckBox(self.hero_card)
        self.pl_select_all_cb.hide()

        # ── 5. Save Directory Section ─────────────────────────────────────────
        self.folder_section = QFrame(self.hero_card)
        self.folder_section.setObjectName("FolderSection")
        folder_layout = QVBoxLayout(self.folder_section)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(6)

        folder_header_layout = QHBoxLayout()
        folder_header_layout.setContentsMargins(0, 0, 0, 0)
        folder_header_layout.setSpacing(8)

        self.folder_header_icon = QLabel(self.folder_section)
        self.folder_header_icon.setFixedSize(16, 16)
        folder_header_layout.addWidget(self.folder_header_icon)

        self.folder_header_lbl = QLabel(tr('save_directory_label', 'Save Directory:'), self.folder_section)
        f_hdr_font = QFont()
        f_hdr_font.setPointSize(10)
        f_hdr_font.setBold(True)
        self.folder_header_lbl.setFont(f_hdr_font)
        folder_header_layout.addWidget(self.folder_header_lbl)
        folder_header_layout.addStretch()

        folder_layout.addLayout(folder_header_layout)

        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        folder_row.setSpacing(10)

        self.folder_path_input = QLineEdit(self.folder_section)
        self.folder_path_input.setReadOnly(True)
        self.folder_path_input.setFixedHeight(34)
        folder_row.addWidget(self.folder_path_input, stretch=1)

        self.folder_change_btn = QPushButton(tr('btn_change_folder', 'Change'), self.folder_section)
        self.folder_change_btn.setObjectName("FolderChangeBtn")
        self.folder_change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_change_btn.setFixedHeight(34)
        self.folder_change_btn.setIconSize(QSize(16, 16))
        self.folder_change_btn.clicked.connect(self._on_change_folder_clicked)
        folder_row.addWidget(self.folder_change_btn)

        folder_layout.addLayout(folder_row)
        card_layout.addWidget(self.folder_section)

        # ── Bottom Divider ────────────────────────────────────────────────────
        self.divider_bottom = QFrame(self.hero_card)
        self.divider_bottom.setFrameShape(QFrame.Shape.HLine)
        self.divider_bottom.setFrameShadow(QFrame.Shadow.Plain)
        self.divider_bottom.setFixedHeight(1)
        card_layout.addWidget(self.divider_bottom)

        # ── 6. Bottom Controls: Remember Choice + Cancel + Download Now ───────
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 4, 0, 0)
        controls_layout.setSpacing(14)

        self.remember_choice_cb = QCheckBox(tr("remember_my_choice", "Always remember my format choice"), self.hero_card)
        self.remember_choice_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remember_choice_cb.toggled.connect(self.on_remember_choice_toggled)
        controls_layout.addWidget(self.remember_choice_cb)

        controls_layout.addStretch()

        self.cancel_btn = QPushButton(tr('btn_cancel', 'Cancel'), self.hero_card)
        self.cancel_btn.setObjectName("btn_cancel_hero")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setIconSize(QSize(16, 16))
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        controls_layout.addWidget(self.cancel_btn)

        self.download_btn = QPushButton(tr('start_download', 'Download Now'), self.hero_card)
        self.download_btn.setObjectName("btn_download_hero")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setFixedHeight(38)
        self.download_btn.setIconSize(QSize(18, 18))
        self.download_btn.clicked.connect(self._on_download_clicked)
        controls_layout.addWidget(self.download_btn)

        card_layout.addLayout(controls_layout)
        root_layout.addWidget(self.hero_card)

        self.update_theme()

    def _load_remember_state(self):
        remember_checked = self.main_app.settings_manager.get("remember_format_choice", False)
        self.remember_choice_cb.setChecked(remember_checked)

    def _on_cancel_clicked(self):
        self.cancel_requested.emit()

    def _on_download_clicked(self):
        self.download_requested.emit()

    def _on_change_folder_clicked(self):
        curr = self.folder_path_input.text() or self.main_app.last_save_dir
        folder = QFileDialog.getExistingDirectory(self, tr("dialog_select_playlist", "Select Folder for Playlist"), curr)
        if folder:
            self.folder_path_input.setText(folder)
            self.main_app.last_save_dir = folder
            self.main_app.save_settings(folder)

    def set_playlist_thumbnail(self, pixmap):
        if pixmap and not pixmap.isNull():
            self.loaded_pixmap = pixmap
            scaled = pixmap.scaled(
                200, 112,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumb_label.setPixmap(scaled)
            self.has_custom_pl_thumb = True
            self.badge_playlist.adjustSize()
            self.badge_playlist.move(
                self.thumb_label.width() - self.badge_playlist.width() - 8,
                self.thumb_label.height() - self.badge_playlist.height() - 8
            )
            self.badge_playlist.raise_()

    def populate(self, title, image_data, entries):
        self.clean_title = clean_and_shorten_title(title)
        self.title_label.setText(title)
        self.title_label.setToolTip(title)

        total_videos = len(entries)
        count_str = tr('playlist_videos_count', '{} videos').format(total_videos)
        self.count_label.setText(count_str)
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        sec_color = "#94a3b8" if is_dark else "#64748b"
        self.count_icon.setPixmap(get_colored_icon("assets/icons/playlist.svg", sec_color).pixmap(14, 14))
        self.count_icon.show()

        self.has_custom_pl_thumb = False
        if image_data:
            pix = QPixmap()
            if pix.loadFromData(image_data):
                self.set_playlist_thumbnail(pix)
        if not self.has_custom_pl_thumb:
            placeholder = QPixmap(200, 112)
            placeholder.fill(QColor("#080e1b"))
            p = QPainter(placeholder)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            icon = get_colored_icon("assets/icons/playlist.svg", "#f97316")
            if not icon.isNull():
                icon.paint(p, QRect(76, 32, 48, 48))
            p.end()
            self.thumb_label.setPixmap(placeholder)
            self.badge_playlist.adjustSize()
            self.badge_playlist.move(
                self.thumb_label.width() - self.badge_playlist.width() - 8,
                self.thumb_label.height() - self.badge_playlist.height() - 8
            )
            self.badge_playlist.raise_()

        self._clear_items()
        self.pl_checkboxes = []

        show_thumbnails = self._read_show_thumbnails_setting()

        for i, entry in enumerate(entries):
            entry['original_index'] = i + 1
            self._add_item_row(i, entry, show_thumbnails)

        # Populate underlying combo for backwards compatibility
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for label, code in PLAYLIST_FORMATS:
            if label == "separator":
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(label, code)
        # Default combo index to 1080p for playlists if available
        idx_1080 = -1
        for i in range(self.format_combo.count()):
            code = str(self.format_combo.itemData(i) or '')
            if "height<=1080" in code:
                idx_1080 = i
                break
        if idx_1080 != -1:
            self.format_combo.blockSignals(True)
            self.format_combo.setCurrentIndex(idx_1080)
            self.format_combo.blockSignals(False)

        # Build quality pill buttons
        self._build_quality_pills()

        self.sub_cb.setEnabled(True)
        self.sub_cb.setChecked(False)

        # Update download path section
        mgr = self.main_app.settings_manager
        dl_type = mgr.get("download_path_type", "downloads")
        if dl_type == "always_ask":
            self.folder_section.hide()
        else:
            current_dir = self.main_app.last_save_dir or (mgr.get_current_download_dir() if hasattr(mgr, 'get_current_download_dir') else mgr.get("custom_path")) or os.path.join(os.path.expanduser("~"), "Downloads")
            self.folder_path_input.setText(current_dir)
            self.folder_path_input.setToolTip(current_dir)
            self.folder_section.show()

        self.auto_select_saved_format()
        self.update_selection_counter()
        self.download_btn.setEnabled(True)
        self.btn_select_all.setEnabled(True)
        self.btn_deselect_all.setEnabled(True)
        self.sub_cb.setEnabled(True)
        self.hero_card.show()
        self.show()
        self.update_theme()

    def show_placeholder(self, title="", pixmap=None, entries_count=None, extra_info=None):
        if title:
            self.clean_title = clean_and_shorten_title(title)
            self.title_label.setText(title)
            self.title_label.setToolTip(title)

        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        sec_color = "#94a3b8" if is_dark else "#64748b"

        if not entries_count and extra_info:
            entries_count = extra_info.get('entries_count') or extra_info.get('view_count')

        if entries_count and str(entries_count).strip().lower() not in ('none', '', '0'):
            count_str = tr('playlist_videos_count', '{} videos').format(entries_count)
            self.count_label.setText(count_str)
        else:
            self.count_label.setText(tr('playlist_calculating', 'Calculating...'))
        self.count_icon.setPixmap(get_colored_icon("assets/icons/playlist.svg", sec_color).pixmap(14, 14))
        self.count_icon.show()

        if pixmap and not pixmap.isNull():
            self.set_playlist_thumbnail(pixmap)
        else:
            self.thumb_label.show_loading()

        accent = get_accent_hex()
        self.badge_icon_lbl.setPixmap(get_colored_icon("assets/icons/hourglass.svg", accent).pixmap(14, 14))
        self.badge_icon_lbl.show()
        self.pl_counter_lbl.setText(tr("search_loading_playlist", "Fetching playlist items... please wait."))
        self.download_btn.setEnabled(False)
        self.btn_select_all.setEnabled(False)
        self.btn_deselect_all.setEnabled(False)
        self.sub_cb.setEnabled(False)

        # Show 3 animated pulsing skeleton items in playlist items layout
        self._clear_items()
        for _ in range(3):
            skel = PlaylistItemSkeleton(parent=self._pl_container)
            self.pl_items_layout.addWidget(skel)

        # Update download path section
        mgr = self.main_app.settings_manager
        dl_type = mgr.get("download_path_type", "downloads")
        if dl_type == "always_ask":
            self.folder_section.hide()
        else:
            current_dir = self.main_app.last_save_dir or (mgr.get_current_download_dir() if hasattr(mgr, 'get_current_download_dir') else mgr.get("custom_path")) or os.path.join(os.path.expanduser("~"), "Downloads")
            self.folder_path_input.setText(current_dir)
            self.folder_path_input.setToolTip(current_dir)
            self.folder_section.show()

        self.hero_card.show()
        self.show()
        self.update_theme()

    def _build_quality_pills(self):
        # Clear existing pills
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.quality_pills.clear()

        # Video quality definitions
        video_pills_spec = [
            ("4K", "bestvideo[height<=2160]"),
            ("2K", "bestvideo[height<=1440]"),
            ("1080p", "bestvideo[height<=1080]"),
            ("720p", "bestvideo[height<=720]"),
            ("480p", "bestvideo[height<=480]"),
            ("360p", "bestvideo[height<=360]"),
        ]

        # Audio quality definitions
        audio_pills_spec = [
            ("M4A (128kbps)", "audio:bestaudio:m4a:128"),
        ]

        active_spec = video_pills_spec if self.current_mode == "video" else audio_pills_spec
        accent = get_accent_hex()

        for label_text, code_prefix in active_spec:
            btn = QPushButton(label_text, self.quality_pills_container)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setProperty("code_prefix", code_prefix)
            if self.current_mode == "audio":
                btn.setIcon(get_colored_icon("assets/icons/music.svg", accent))
                btn.setIconSize(QSize(14, 14))
            btn.clicked.connect(lambda checked=False, cp=code_prefix, b=btn: self._on_quality_pill_clicked(cp, b))
            self.pills_layout.addWidget(btn)
            self.quality_pills.append(btn)

        self._sync_pills_with_combo()

    def _on_mode_changed(self, mode: str):
        if mode in ["video", "audio"] and mode != self.current_mode:
            self.current_mode = mode
            self.tab_video_btn.setChecked(mode == "video")
            self.tab_audio_btn.setChecked(mode == "audio")
            self._apply_tab_styles()
            self._build_quality_pills()
            # Select default pill in new mode
            if self.quality_pills:
                target_pill = None
                if mode == "video":
                    for p in self.quality_pills:
                        if p.text() == "1080p":
                            target_pill = p
                            break
                if not target_pill:
                    target_pill = self.quality_pills[0]
                prefix = target_pill.property("code_prefix")
                self._on_quality_pill_clicked(prefix, target_pill)

    def _on_quality_pill_clicked(self, code_prefix: str, clicked_btn: QPushButton):
        for btn in self.quality_pills:
            btn.setChecked(btn == clicked_btn)
        self._apply_pill_styles()

        # Sync underlying format_combo
        target_idx = -1
        for i in range(self.format_combo.count()):
            code = str(self.format_combo.itemData(i) or '')
            if code.startswith(code_prefix) or code_prefix in code:
                target_idx = i
                break
        if target_idx != -1 and self.format_combo.currentIndex() != target_idx:
            self.format_combo.blockSignals(True)
            self.format_combo.setCurrentIndex(target_idx)
            self.format_combo.blockSignals(False)
            self.save_format_preference()

    def _sync_pills_with_combo(self):
        curr_code = str(self.format_combo.currentData() or '')
        matched = False
        for btn in self.quality_pills:
            prefix = btn.property("code_prefix")
            is_match = (curr_code.startswith(prefix) or prefix in curr_code)
            btn.setChecked(is_match)
            if is_match:
                matched = True
        if not matched and self.quality_pills:
            # Default to 1080p if video, or first item
            idx = 2 if (self.current_mode == "video" and len(self.quality_pills) > 2) else 0
            for b in self.quality_pills:
                b.setChecked(False)
            self.quality_pills[idx].setChecked(True)
            prefix = self.quality_pills[idx].property("code_prefix")
            # Sync back
            for i in range(self.format_combo.count()):
                code = str(self.format_combo.itemData(i) or '')
                if code.startswith(prefix) or prefix in code:
                    self.format_combo.blockSignals(True)
                    self.format_combo.setCurrentIndex(i)
                    self.format_combo.blockSignals(False)
                    break
        self._apply_pill_styles()

    def _on_format_combo_index_changed(self, idx):
        if idx >= 0:
            code = str(self.format_combo.itemData(idx) or '')
            desired_mode = "audio" if code.startswith("audio:") else "video"
            if desired_mode != self.current_mode:
                self._on_mode_changed(desired_mode)
            else:
                self._sync_pills_with_combo()
            self.save_format_preference()

    def _add_item_row(self, index, entry, show_thumbnails):
        from services.yt_dlp_service import ThumbnailRunnable

        row = PlaylistItemRow(index, entry, show_thumbnails=show_thumbnails, parent=self._pl_container)
        row.toggled.connect(lambda _: self.update_selection_counter())
        self.pl_items_layout.addWidget(row)
        self.pl_checkboxes.append((row.cb, entry))

        if show_thumbnails:
            thumb_param = entry.get('thumbnail') or entry.get('id')
            if thumb_param:
                runnable = ThumbnailRunnable(index, thumb_param)
                runnable.signals.thumb_loaded.connect(self.update_playlist_thumb)
                QThreadPool.globalInstance().start(runnable)

    def update_playlist_thumb(self, index, data):
        if data and index < len(self.pl_checkboxes):
            cb, entry = self.pl_checkboxes[index]
            label = cb.property("img_label")
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled = pixmap.scaled(
                    80, 45,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                if label:
                    label.setPixmap(scaled)
                entry['thumb_pixmap'] = pixmap
                if index == 0 and not self.has_custom_pl_thumb:
                    self.set_playlist_thumbnail(pixmap)
            else:
                if label:
                    label.hide_loading()

    def _clear_items(self):
        while self.pl_items_layout.count():
            item = self.pl_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _read_show_thumbnails_setting(self):
        return self.main_app.settings_manager.get("show_thumbnails", True)

    def select_all_items(self):
        for cb, _ in self.pl_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
            parent_row = cb.parent()
            if hasattr(parent_row, 'update_style'):
                parent_row.update_style()
        self.update_selection_counter()

    def deselect_all_items(self):
        for cb, _ in self.pl_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
            parent_row = cb.parent()
            if hasattr(parent_row, 'update_style'):
                parent_row.update_style()
        self.update_selection_counter()

    def toggle_all_playlist_items(self):
        # Kept for backward compatibility
        state = self.pl_select_all_cb.isChecked()
        if state:
            self.select_all_items()
        else:
            self.deselect_all_items()

    def get_selected_entries(self):
        return [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]

    def update_selection_counter(self):
        total = len(self.pl_checkboxes)
        selected = sum(1 for cb, _ in self.pl_checkboxes if cb.isChecked())
        count_text = tr("playlist_selected_count", "Selected: {} of {} videos").format(selected, total)
        accent = get_accent_hex()
        self.badge_icon_lbl.setPixmap(get_colored_icon("assets/icons/sparkles.svg", accent).pixmap(14, 14))
        self.badge_icon_lbl.show()
        self.pl_counter_lbl.setText(count_text)

        self.pl_select_all_cb.blockSignals(True)
        self.pl_select_all_cb.setChecked(selected == total and total > 0)
        self.pl_select_all_cb.blockSignals(False)

    def reset(self):
        self._clear_items()
        self.pl_checkboxes.clear()
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.sub_cb.setChecked(False)
        self.badge_icon_lbl.clear()
        self.pl_counter_lbl.setText("")
        self.count_icon.clear()
        self.count_icon.hide()
        self.count_label.setText("")
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.thumb_label.clear()
        self.has_custom_pl_thumb = False
        self.hero_card.hide()
        self.hide()

    def _apply_tab_styles(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        bg_container = "#080e1b" if is_dark else "#f1f5f9"
        border_container = "#1e293b" if is_dark else "#e2e8f0"
        self.tab_container.setStyleSheet(f"""
            QFrame#SegmentedTabContainer {{
                background-color: {bg_container};
                border: 1px solid {border_container};
                border-radius: 12px;
            }}
        """)
        active_style = f"""
            QPushButton {{
                background-color: {'#152238' if is_dark else '#ffffff'};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border: 1px solid {'#334155' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                font-weight: bold;
                padding: 4px 14px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background: transparent;
                color: {'#94a3b8' if is_dark else '#64748b'};
                border: none;
                border-radius: 8px;
                font-weight: 500;
                padding: 4px 14px;
            }}
            QPushButton:hover {{
                color: {'#ffffff' if is_dark else '#0f172a'};
            }}
        """
        self.tab_video_btn.setStyleSheet(active_style if self.tab_video_btn.isChecked() else inactive_style)
        self.tab_audio_btn.setStyleSheet(active_style if self.tab_audio_btn.isChecked() else inactive_style)

        text_active = "#ffffff" if is_dark else "#0f172a"
        text_inactive = "#94a3b8" if is_dark else "#64748b"
        self.tab_video_btn.setIcon(get_colored_icon("assets/icons/video.svg", text_active if self.tab_video_btn.isChecked() else text_inactive))
        self.tab_audio_btn.setIcon(get_colored_icon("assets/icons/music.svg", text_active if self.tab_audio_btn.isChecked() else text_inactive))

    def _apply_pill_styles(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        accent = get_accent_hex()
        if "#" in accent and len(accent) == 7:
            r = int(accent[1:3], 16)
            g = int(accent[3:5], 16)
            b = int(accent[5:7], 16)
            bg_checked = f"rgba({r}, {g}, {b}, {0.18 if is_dark else 0.12})"
        else:
            bg_checked = "rgba(59, 130, 246, 0.12)"

        for btn in self.quality_pills:
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_checked};
                        color: {'#ffffff' if is_dark else accent};
                        border: 1.5px solid {accent};
                        border-radius: 14px;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 4px 16px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {'#0b1325' if is_dark else '#ffffff'};
                        color: {'#94a3b8' if is_dark else '#475569'};
                        border: 1px solid {'#1e293b' if is_dark else '#e2e8f0'};
                        border-radius: 14px;
                        font-weight: 500;
                        font-size: 12px;
                        padding: 4px 16px;
                    }}
                    QPushButton:hover {{
                        background-color: {'#162235' if is_dark else '#f1f5f9'};
                        border-color: {'#475569' if is_dark else '#cbd5e1'};
                        color: {'#ffffff' if is_dark else '#0f172a'};
                    }}
                """)

    def update_theme(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        accent = get_accent_hex()

        bg_card = "#0d1527" if is_dark else "#ffffff"
        border_card = "rgba(51, 65, 85, 0.6)" if is_dark else "#cbd5e1"
        if getattr(self, 'is_dialog', False):
            self.hero_card.setStyleSheet("""
                QFrame#MediaHeroCard {
                    background-color: transparent;
                    border: none;
                }
            """)
        else:
            self.hero_card.setStyleSheet(f"""
                QFrame#MediaHeroCard {{
                    background-color: {bg_card};
                    border: 1.5px solid {border_card};
                    border-radius: 16px;
                }}
            """)

        self.badge_frame.setStyleSheet(f"""
            QFrame#QualitySummaryBadge {{
                background-color: rgba(249, 115, 22, 0.12);
                border: 1px solid {accent};
                border-radius: 14px;
            }}
        """)
        self.pl_counter_lbl.setStyleSheet(f"color: {accent}; font-weight: bold;")

        divider_color = "#243249" if is_dark else "#e2e8f0"
        divider_style = f"background-color: {divider_color}; border: none;"
        self.divider_top.setStyleSheet(divider_style)
        self.divider_middle.setStyleSheet(divider_style)
        self.divider_bottom.setStyleSheet(divider_style)

        self._apply_tab_styles()
        self._apply_pill_styles()

        self.pl_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 7px;
                margin: 2px 0px 2px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {'#334155' if is_dark else '#cbd5e1'};
                min-height: 28px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {'#64748b' if is_dark else '#94a3b8'};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # Links style
        self.btn_select_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {accent};
                font-weight: bold;
                font-size: 11px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        self.btn_deselect_all.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {'#94a3b8' if is_dark else '#64748b'};
                font-weight: 500;
                font-size: 11px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                color: {'#ffffff' if is_dark else '#0f172a'};
                text-decoration: underline;
            }}
        """)

        self.sub_frame.setStyleSheet(f"""
            QFrame#PlaylistSubFrame {{
                background-color: {'#080e1b' if is_dark else '#f8fafc'};
                border: 1px solid {'#1e293b' if is_dark else '#e2e8f0'};
                border-radius: 12px;
            }}
        """)

        info_icon_color = '#94a3b8' if is_dark else '#64748b'
        self.sub_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", info_icon_color).pixmap(16, 16))
        self.sub_info_icon.show()

        self.sub_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {'#f1f5f9' if is_dark else '#0f172a'};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                background-color: {'#152238' if is_dark else '#e2e8f0'};
                border: 1.5px solid {'#334155' if is_dark else '#cbd5e1'};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border: 1.5px solid {accent};
                image: url(assets/icons/check.svg);
            }}
        """)

        self.folder_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {'#080e1b' if is_dark else '#f8fafc'};
                color: {'#94a3b8' if is_dark else '#475569'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
            }}
        """)
        self.folder_change_btn.setStyleSheet(f"""
            QPushButton#FolderChangeBtn {{
                background-color: {'#152238' if is_dark else '#e2e8f0'};
                color: {'#f8fafc' if is_dark else '#1e293b'};
                border: 1px solid {'#1e293b' if is_dark else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#FolderChangeBtn:hover {{
                background-color: {'#1e293b' if is_dark else '#cbd5e1'};
                border-color: {'#334155' if is_dark else '#94a3b8'};
            }}
        """)

        self.cancel_btn.setStyleSheet(f"""
            QPushButton#btn_cancel_hero {{
                background: transparent;
                color: {'#94a3b8' if is_dark else '#64748b'};
                border: 1.5px solid {'#334155' if is_dark else '#cbd5e1'};
                border-radius: 19px;
                padding: 6px 24px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_cancel_hero:hover {{
                background: {'rgba(51, 65, 85, 0.3)' if is_dark else '#f1f5f9'};
                color: {'#ffffff' if is_dark else '#0f172a'};
                border-color: {'#64748b' if is_dark else '#94a3b8'};
            }}
        """)

        self.download_btn.setStyleSheet(f"""
            QPushButton#btn_download_hero {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.4 #6366f1, stop:1 #e11d48);
                color: #ffffff;
                border: 1px solid transparent;
                border-radius: 19px;
                padding: 6px 28px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton#btn_download_hero:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:0.4 #4f46e5, stop:1 #be123c);
            }}
            QPushButton#btn_download_hero:disabled {{
                background: {'#334155' if is_dark else '#cbd5e1'};
                color: {'#64748b' if is_dark else '#94a3b8'};
            }}
        """)

        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        text_secondary = "#94a3b8" if is_dark else "#64748b"
        self.title_label.setStyleSheet(f"color: {text_primary};")
        self.count_label.setStyleSheet(f"color: {text_secondary}; font-weight: bold; font-size: 12px;")
        self.videos_list_title.setStyleSheet(f"color: {text_primary};")
        self.folder_header_lbl.setStyleSheet(f"color: {text_primary};")
        self.remember_choice_cb.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")

        # Tint icons
        self.videos_list_icon.setPixmap(get_colored_icon("assets/icons/clapperboard.svg", text_primary).pixmap(16, 16))
        self.folder_header_icon.setPixmap(get_colored_icon("assets/icons/folder.svg", text_primary).pixmap(16, 16))
        self.folder_change_btn.setIcon(get_colored_icon("assets/icons/folder-open.svg", text_primary))
        self.cancel_btn.setIcon(get_colored_icon("assets/icons/cancel.svg", text_secondary))
        self.download_btn.setIcon(get_colored_icon("assets/icons/download.svg", "#ffffff"))
        self.count_icon.setPixmap(get_colored_icon("assets/icons/playlist.svg", text_secondary).pixmap(14, 14))
        self.sub_cb.setIcon(get_colored_icon("assets/icons/subtitles.svg", accent))

        for cb, _ in self.pl_checkboxes:
            parent_row = cb.parent()
            if hasattr(parent_row, 'update_style'):
                parent_row.update_style(is_dark)