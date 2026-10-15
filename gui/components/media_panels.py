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
    QScrollArea
)
from PyQt6.QtCore import Qt, QSize, QThreadPool
from PyQt6.QtGui import QPixmap

from gui.components.common import (
    ResponsiveImage, MultiLineElidedLabel,
    get_relative_time, format_views, FormatPreferencesMixin
)
from utils.helpers import (
    get_colored_icon, get_current_theme_color,
    get_full_language_name, clean_and_shorten_title
)
from utils.locales import tr


# قائمة الجودات الثابتة للـ playlist (مكان واحد للتعديل)
PLAYLIST_FORMATS = [
    ("🎬 4K (2160p) - Ultra HD",            "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best"),
    ("🎬 2K (1440p) - Quad HD",             "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best"),
    ("🎬 Full HD (1080p)",                   "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"),
    ("🎬 High (720p)",                       "bestvideo[height<=720]+bestaudio/best[height<=720]/best"),
    ("🎬 Standard (480p)",                   "bestvideo[height<=480]+bestaudio/best[height<=480]/best"),
    ("🎬 Medium (360p)",                     "bestvideo[height<=360]+bestaudio/best[height<=360]/best"),
    ("🎬 Low (240p)",                        "bestvideo[height<=240]+bestaudio/best[height<=240]/best"),
    ("🎬 Very Low (144p)",                   "bestvideo[height<=144]+bestaudio/best[height<=144]/best"),
    ("separator",                            ""),
    ("🎵 M4A (128kbps) - Original Best Audio", "audio:bestaudio:m4a:128"),
]


class SingleVideoPanel(QWidget, FormatPreferencesMixin):
    """
    Panel مشترك لعرض معلومات الفيديو الواحد وخيارات التنزيل.
    """

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._initUI()
        self._load_remember_state()

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Info Card (thumbnail + title + channel + views/date) ───────────────
        self.info_card = QFrame()
        self.info_card.setObjectName("MediaInfoCard")
        self.info_card.setSizePolicy(
            self.info_card.sizePolicy().Policy.Expanding,
            self.info_card.sizePolicy().Policy.Preferred
        )
        info_layout = QVBoxLayout(self.info_card)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(6)

        self.thumb_label = ResponsiveImage()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.hide()
        info_layout.addWidget(self.thumb_label)

        self.title_label = MultiLineElidedLabel('', self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        self.title_label.setFont(title_font)
        info_layout.addWidget(self.title_label)

        self.channel_label = QLabel('', self)
        self.channel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_label.hide()
        info_layout.addWidget(self.channel_label)

        self.meta_label = QLabel('', self)
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.meta_label.hide()
        info_layout.addWidget(self.meta_label)

        self.duration_label = QLabel('', self)
        self.duration_label.hide()
        layout.addWidget(self.info_card)

        # ── Settings Card (format + subtitle + remember) ──────────────────────
        self.settings_card = QFrame()
        self.settings_card.setObjectName("DownloadSettingsCard")
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(12)

        self.format_combo = QComboBox(self)
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.format_combo.currentIndexChanged.connect(self.save_format_preference)
        settings_layout.addWidget(self.format_combo)

        sub_layout = QHBoxLayout()

        self.sub_cb = QCheckBox(tr("sub_cc"), self)
        self.sub_cb.setEnabled(False)
        self.sub_cb.toggled.connect(self.toggle_sub_combo)
        sub_layout.addWidget(self.sub_cb)

        self.sub_combo = QComboBox(self)
        self.sub_combo.hide()
        sub_layout.addWidget(self.sub_combo)

        sub_layout.addStretch()

        self.remember_choice_cb = QCheckBox(tr("remember_my_choice", "Remember my choice"), self)
        self.remember_choice_cb.toggled.connect(self.on_remember_choice_toggled)
        sub_layout.addWidget(self.remember_choice_cb)

        settings_layout.addLayout(sub_layout)
        layout.addWidget(self.settings_card)
        
        self.update_theme()

    def _load_remember_state(self):
        remember_checked = self.main_app.settings_manager.get("remember_format_choice", False)
        self.remember_choice_cb.setChecked(remember_checked)

    def populate(self, title, duration_secs, image_data, format_list, subtitles_dict, extra_info=None):
        self.clean_title = clean_and_shorten_title(title)

        self.title_label.setText(title)
        self.title_label.setToolTip(title)

        if extra_info:
            uploader = extra_info.get('uploader', '')
            view_count = extra_info.get('view_count')
            upload_date = extra_info.get('upload_date', '')

            if uploader:
                self.channel_label.setText(uploader)
                self.channel_label.show()
            else:
                self.channel_label.hide()

            views_str = format_views(view_count)
            date_str = get_relative_time(upload_date)
            meta_parts = [p for p in [views_str, date_str] if p]
            if meta_parts:
                self.meta_label.setText(" • ".join(meta_parts))
                self.meta_label.show()
            else:
                self.meta_label.hide()
        else:
            self.channel_label.hide()
            self.meta_label.hide()

        m, s = divmod(duration_secs or 0, 60)
        h, m = divmod(m, 60)
        self.duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        
        self.duration_label.setText(f"{tr('duration_prefix')}{self.duration_str}")
        self.thumb_label.set_duration_text(self.duration_str)

        if image_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.thumb_label.setPixmap(pixmap)
                self.thumb_label._pixmap = pixmap
                self.thumb_label.show()

        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for item in format_list:
            if item['type'] == 'separator':
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(item['label'], item['format_code'])
        self.format_combo.show()
        self.format_combo.setEnabled(True)

        self.sub_combo.clear()
        self.sub_cb.setChecked(False)
        self.sub_combo.hide()
        self._populate_subtitles(subtitles_dict)
        self.sub_cb.show()

        self.auto_select_saved_format()
        self.format_combo.blockSignals(False)
        self.update_theme()

    def _populate_subtitles(self, subtitles_dict):
        if not subtitles_dict:
            self._disable_subs()
            return

        filtered = {
            lang: info for lang, info in subtitles_dict.items()
            if "live_chat" not in lang.lower() and "chat" not in lang.lower()
        }
        if not filtered:
            self._disable_subs()
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
            if s_info['type'] == 'Manual':
                manual_subs.append((lang_code, s_info))
            elif s_info['type'] == 'Auto' and is_orig:
                original_auto_subs.append((lang_code, s_info))
            else:
                other_auto_subs.append((lang_code, s_info))

        top_group = manual_subs if manual_subs else original_auto_subs
        bottom_group = (original_auto_subs + other_auto_subs) if manual_subs else other_auto_subs
        top_group.sort(key=lambda x: get_lang_priority(x[0]))
        bottom_group.sort(key=lambda x: get_lang_priority(x[0]))

        self.sub_cb.setEnabled(True)
        self.sub_cb.setStyleSheet("")
        font = self.sub_cb.font()
        font.setStrikeOut(False)
        self.sub_cb.setFont(font)

        for lang_code, s_info in top_group:
            lang_name = get_full_language_name(lang_code)
            label = (f"🌐 {lang_name} (original) (manual)" if s_info['type'] == 'Manual'
                     else f"🌐 {lang_name} (original) (auto)")
            self.sub_combo.addItem(label, s_info['code'])

        if top_group and bottom_group:
            self.sub_combo.insertSeparator(self.sub_combo.count())

        for lang_code, s_info in bottom_group:
            is_orig = "-orig" in lang_code.lower() or "-original" in lang_code.lower()
            lang_name = get_full_language_name(lang_code)
            if is_orig:
                label = f"🌐 {lang_name} (original) (auto)"
            elif s_info['type'] == 'Manual':
                label = f"🌐 {lang_name} (original) (manual)"
            else:
                label = f"🌐 {lang_name} (auto)"
            self.sub_combo.addItem(label, s_info['code'])

    def _disable_subs(self):
        self.sub_cb.setEnabled(False)
        self.sub_cb.setStyleSheet("color: gray;")
        font = self.sub_cb.font()
        font.setStrikeOut(True)
        self.sub_cb.setFont(font)

    def toggle_sub_combo(self, checked):
        if checked and self.sub_combo.count() > 0:
            self.sub_combo.show()
        else:
            self.sub_combo.hide()

    def update_theme(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        text_secondary = "#94a3b8" if is_dark else "#64748b"
        text_tertiary = "#64748b" if is_dark else "#94a3b8"
        
        self.title_label.setStyleSheet(f"color: {text_primary};")
        self.channel_label.setStyleSheet(f"color: {text_secondary}; font-weight: bold; font-size: 12px;")
        self.meta_label.setStyleSheet(f"color: {text_tertiary}; font-size: 11px;")

    def get_selected_sub_lang(self):
        if self.sub_cb.isVisible() and self.sub_cb.isChecked():
            return self.sub_combo.currentData()
        return None

    def reset(self):
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.channel_label.setText("")
        self.channel_label.hide()
        self.meta_label.setText("")
        self.meta_label.hide()
        self.duration_label.setText("")
        self.duration_label.hide()
        self.thumb_label.hide()
        self.thumb_label.clear()
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.format_combo.hide()
        self.sub_cb.hide()
        self.sub_combo.hide()
        self.info_card.hide()
        self.settings_card.hide()


class PlaylistPanel(QWidget, FormatPreferencesMixin):
    """
    Panel مشترك لعرض قائمة تشغيل وخيارات تنزيلها.
    """

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.pl_checkboxes = []
        self._initUI()
        self._load_remember_state()

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.playlist_card = QFrame(self)
        self.playlist_card.setObjectName("MediaInfoCard")
        card_layout = QVBoxLayout(self.playlist_card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(12)

        select_all_layout = QHBoxLayout()
        select_all_layout.setContentsMargins(0, 0, 0, 0)

        self.pl_select_all_cb = QCheckBox(tr("select_all", "Select All"), self.playlist_card)
        self.pl_select_all_cb.setChecked(True)
        cb_font = self.pl_select_all_cb.font()
        cb_font.setBold(True)
        self.pl_select_all_cb.setFont(cb_font)
        self.pl_select_all_cb.clicked.connect(self.toggle_all_playlist_items)
        select_all_layout.addWidget(self.pl_select_all_cb)

        select_all_layout.addStretch()

        self.pl_counter_lbl = QLabel("", self.playlist_card)
        self.pl_counter_lbl.setStyleSheet("color: #8a99ad; font-weight: bold; font-size: 11px;")
        select_all_layout.addWidget(self.pl_counter_lbl)

        card_layout.addLayout(select_all_layout)

        self.pl_scroll = QScrollArea(self.playlist_card)
        self.pl_scroll.setWidgetResizable(True)
        self.pl_scroll.setStyleSheet("background: transparent; border: none;")
        self._pl_container = QWidget()
        self._pl_container.setStyleSheet("background: transparent;")
        self.pl_items_layout = QVBoxLayout(self._pl_container)
        self.pl_items_layout.setContentsMargins(4, 4, 4, 4)
        self.pl_items_layout.setSpacing(4)
        self.pl_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.pl_scroll.setWidget(self._pl_container)
        card_layout.addWidget(self.pl_scroll)

        layout.addWidget(self.playlist_card)

        self.settings_card = QFrame()
        self.settings_card.setObjectName("DownloadSettingsCard")
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(8)

        self.format_combo = QComboBox(self)
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.format_combo.currentIndexChanged.connect(self.save_format_preference)
        settings_layout.addWidget(self.format_combo)

        sub_row = QHBoxLayout()
        self.sub_cb = QCheckBox(tr("sub_cc", "Subtitles"), self)
        self.sub_cb.setChecked(False)
        sub_row.addWidget(self.sub_cb)

        self.sub_info_icon = QLabel(self)
        self.sub_info_icon.setPixmap(
            get_colored_icon("assets/icons/info.svg", get_current_theme_color()).pixmap(16, 16)
        )
        self.sub_info_icon.setToolTip(tr("sub_info_tooltip", "Subtitles will be downloaded if available"))
        self.sub_info_icon.hide()
        sub_row.addWidget(self.sub_info_icon)

        sub_row.addStretch()

        self.remember_choice_cb = QCheckBox(tr("remember_my_choice", "Remember my choice"), self)
        self.remember_choice_cb.toggled.connect(self.on_remember_choice_toggled)
        sub_row.addWidget(self.remember_choice_cb)

        settings_layout.addLayout(sub_row)
        layout.addWidget(self.settings_card)

    def _load_remember_state(self):
        remember_checked = self.main_app.settings_manager.get("remember_format_choice", False)
        self.remember_choice_cb.setChecked(remember_checked)

    def populate(self, title, image_data, entries):
        self.clean_title = clean_and_shorten_title(title)

        self.loaded_pixmap = None
        if image_data:
            pix = QPixmap()
            if pix.loadFromData(image_data):
                self.loaded_pixmap = pix

        self._clear_items()
        self.pl_checkboxes = []

        show_thumbnails = self._read_show_thumbnails_setting()

        for i, entry in enumerate(entries):
            entry['original_index'] = i + 1
            self._add_item_row(i, entry, show_thumbnails)

        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for label, code in PLAYLIST_FORMATS:
            if label == "separator":
                self.format_combo.insertSeparator(self.format_combo.count())
            else:
                self.format_combo.addItem(label, code)
        self.format_combo.show()
        self.format_combo.setEnabled(True)

        self.sub_cb.setEnabled(True)
        self.sub_cb.setStyleSheet("")
        self.sub_cb.setChecked(False)
        self.sub_cb.show()
        self.sub_info_icon.show()
        self.pl_select_all_cb.setChecked(True)

        self.auto_select_saved_format()
        self.update_selection_counter()
        self.update_theme()
        self.format_combo.blockSignals(False)

    def _add_item_row(self, index, entry, show_thumbnails):
        from services.yt_dlp_service import ThumbnailRunnable

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(6, 6, 6, 6)
        row_layout.setSpacing(12)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        cb = QCheckBox()
        cb.setChecked(True)
        cb.toggled.connect(self.update_selection_counter)

        thumb_lbl = ResponsiveImage(min_height=84, spinner_size=22)
        thumb_lbl.setFixedSize(150, 84)

        cb.setProperty("img_label", thumb_lbl)
        thumb_lbl.show_loading()

        duration_secs = entry.get('duration')
        if duration_secs:
            try:
                sec = int(duration_secs)
                m, s = divmod(sec, 60)
                h, m = divmod(m, 60)
                dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                thumb_lbl.set_duration_text(dur_str)
            except Exception:
                pass

        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        details_layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = MultiLineElidedLabel(f"{index + 1}. {entry['title']}", row_widget)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
        title_font = title_lbl.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() - 1)
        title_lbl.setFont(title_font)
        details_layout.addWidget(title_lbl)

        uploader = entry.get('uploader') or entry.get('channel') or ""
        channel_lbl = QLabel(uploader, row_widget)
        channel_lbl.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
        channel_font = channel_lbl.font()
        channel_font.setPointSize(channel_font.pointSize() - 2)
        channel_lbl.setFont(channel_font)
        if uploader:
            channel_lbl.show()
        else:
            channel_lbl.hide()
        details_layout.addWidget(channel_lbl)

        views_str = format_views(entry.get('view_count'))
        date_str = get_relative_time(entry.get('upload_date'))
        meta_parts = [p for p in [views_str, date_str] if p]
        
        meta_lbl = QLabel(" • ".join(meta_parts) if meta_parts else "", row_widget)
        meta_lbl.setAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
        meta_font = meta_lbl.font()
        meta_font.setPointSize(meta_font.pointSize() - 2)
        meta_lbl.setFont(meta_font)
        if meta_parts:
            meta_lbl.show()
        else:
            meta_lbl.hide()
        details_layout.addWidget(meta_lbl)
        details_layout.addStretch()

        cb.setProperty("title_lbl", title_lbl)
        cb.setProperty("channel_lbl", channel_lbl)
        cb.setProperty("meta_lbl", meta_lbl)

        row_layout.addWidget(cb)
        if show_thumbnails:
            row_layout.addWidget(thumb_lbl)
        else:
            thumb_lbl.hide()
        row_layout.addLayout(details_layout, 1)

        self.pl_items_layout.addWidget(row_widget)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.pl_items_layout.addWidget(line)

        self.pl_checkboxes.append((cb, entry))

        if show_thumbnails:
            thumb_param = entry.get('thumbnail') or entry.get('id')
            if thumb_param:
                runnable = ThumbnailRunnable(index, thumb_param)
                runnable.signals.thumb_loaded.connect(self.update_playlist_thumb)
                QThreadPool.globalInstance().start(runnable)

    def update_playlist_thumb(self, index, data):
        pixmap = QPixmap()
        loaded = False
        if data:
            loaded = pixmap.loadFromData(data)

        if index < len(self.pl_checkboxes):
            cb, entry = self.pl_checkboxes[index]
            label = cb.property("img_label")
            if label:
                if loaded:
                    scaled = pixmap.scaled(
                        150, 84,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    label.setPixmap(scaled)
                    entry['thumb_pixmap'] = pixmap
                else:
                    label.hide_loading()
                    placeholder = get_colored_icon(
                        "assets/icons/video.svg", get_current_theme_color()
                    ).pixmap(QSize(24, 24))
                    label.setPixmap(placeholder)

    def _clear_items(self):
        while self.pl_items_layout.count():
            item = self.pl_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _read_show_thumbnails_setting(self):
        return self.main_app.settings_manager.get("show_thumbnails", True)

    def toggle_all_playlist_items(self):
        state = self.pl_select_all_cb.isChecked()
        for cb, _ in self.pl_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(state)
            cb.blockSignals(False)
        self.update_selection_counter()

    def get_selected_entries(self):
        return [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]

    def update_selection_counter(self):
        total = len(self.pl_checkboxes)
        selected = sum(1 for cb, _ in self.pl_checkboxes if cb.isChecked())
        self.pl_counter_lbl.setText(f"({selected}/{total})")

        self.pl_select_all_cb.blockSignals(True)
        if selected == total:
            self.pl_select_all_cb.setChecked(True)
        elif selected == 0:
            self.pl_select_all_cb.setChecked(False)
        else:
            self.pl_select_all_cb.setChecked(True)
        self.pl_select_all_cb.blockSignals(False)

    def reset(self):
        self._clear_items()
        self.pl_checkboxes.clear()
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.sub_cb.setChecked(False)
        self.sub_info_icon.hide()
        self.pl_counter_lbl.setText("")
        self.pl_select_all_cb.setChecked(True)

    def update_theme(self):
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        text_primary = "#f1f5f9" if is_dark else "#0f172a"
        text_secondary = "#94a3b8" if is_dark else "#64748b"
        text_tertiary = "#64748b" if is_dark else "#94a3b8"

        for cb, _ in self.pl_checkboxes:
            title_lbl = cb.property("title_lbl")
            channel_lbl = cb.property("channel_lbl")
            meta_lbl = cb.property("meta_lbl")
            if title_lbl:
                title_lbl.setStyleSheet(f"color: {text_primary};")
            if channel_lbl:
                channel_lbl.setStyleSheet(f"color: {text_secondary}; font-weight: bold; font-size: 11px;")
            if meta_lbl:
                meta_lbl.setStyleSheet(f"color: {text_tertiary}; font-size: 10px;")