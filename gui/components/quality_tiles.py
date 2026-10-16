"""
quality_tiles.py
────────────────
مكونات بطاقات اختيار الجودة (Quality Tiles) وكارت التحميل الهيكلي (Skeleton Loading Card)
المصممة خصيصاً لواجهة الفحص الحديثة لـ AHS-MediaDL.
"""

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont

from utils.helpers import get_colored_icon, get_current_theme_color
from utils.theme import get_accent_hex
from utils.locales import tr
import re


class QualityTileWidget(QFrame):
    """
    مربع / كارت تفاعلي يمثل دقة أو جودة واحدة (فيديو أو صوت).
    يعرض: الدقة بخط عريض، حجم الملف التقريبي، وأيقونة التحديد والنوع.
    """
    clicked = pyqtSignal(int)

    def __init__(self, index, format_info, is_selected=False, parent=None):
        super().__init__(parent)
        self.index = index
        self.format_info = format_info
        self._is_selected = is_selected
        self._is_hovered = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(78)
        self.setMinimumWidth(110)

        self._initUI()
        self._apply_style()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 10)
        main_layout.setSpacing(4)

        # ── Top Row: Type Icon (left) + Checkmark (right) ─────────────────────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # Media Type Icon (video or audio) on the left
        self.type_icon_lbl = QLabel(self)
        self.type_icon_lbl.setFixedSize(16, 16)
        top_row.addWidget(self.type_icon_lbl)

        top_row.addStretch()

        # Selected Checkmark indicator (circle on top right)
        self.check_lbl = QLabel(self)
        self.check_lbl.setFixedSize(16, 16)
        self.check_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_check_icon()
        top_row.addWidget(self.check_lbl)

        main_layout.addLayout(top_row)

        # ── Quality Title (e.g. 4K Ultra, 1080p FHD, M4A 128kbps) ─────────────
        label_text = self._parse_clean_title()
        self.title_lbl = QLabel(label_text, self)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self.title_lbl.setFont(title_font)
        main_layout.addWidget(self.title_lbl)

        # ── File Size (e.g. Size: 155.7 MB) ───────────────────────────────────
        size_text = self._parse_clean_size()
        prefix = tr("size_prefix_simple", "Size:")
        if size_text and size_text != tr("size_unknown", "Unknown") and "Unknown" not in size_text:
            full_size_str = f"{prefix} {size_text}"
        else:
            full_size_str = tr("size_unknown", "Unknown")
        self.size_lbl = QLabel(full_size_str, self)
        self.size_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_font = QFont()
        size_font.setPointSize(9)
        self.size_lbl.setFont(size_font)
        main_layout.addWidget(self.size_lbl)

    _SIZE_PATTERN = re.compile(
        r'(?:[-–—~]|\s)*\(?\s*~?\s*(\d+(?:\.\d+)?\s*(?:B|KB|MB|GB|TB|KiB|MiB|GiB|Bytes))\s*\)?\s*$',
        re.IGNORECASE
    )
    _UNKNOWN_PATTERN = re.compile(
        r'(?:[-–—~]|\s)*\(?\s*(?:Size\s+)?Unknown\s*\)?\s*$',
        re.IGNORECASE
    )

    def _parse_clean_title(self):
        label = self.format_info.get('label', '')
        clean = label.replace("🎬", "").replace("🎵", "").strip()
        m = self._SIZE_PATTERN.search(clean)
        if m:
            title_raw = clean[:m.start()].rstrip(' -–—~')
        else:
            m_unk = self._UNKNOWN_PATTERN.search(clean)
            if m_unk:
                title_raw = clean[:m_unk.start()].rstrip(' -–—~')
            else:
                title_raw = clean

        # Audio formats: format & bitrate, e.g. "M4A (128kbps)" or "MP3 (320kbps)"
        is_audio = (self.format_info.get('type') == 'audio' or str(self.format_info.get('format_code', '')).startswith('audio:'))
        if is_audio:
            m_audio = re.search(r'([A-Za-z0-9]+)\s*\(([^)]+)\)', title_raw, re.IGNORECASE)
            if m_audio:
                codec = m_audio.group(1).upper()
                bitrate = m_audio.group(2).strip()
                return f"{codec} ({bitrate})"
            parts = [p.strip() for p in title_raw.split("-")]
            return parts[0] if parts else title_raw

        # Video formats: map to real actual resolutions (1080p, 720p, 480p, etc.)
        mapping = {
            "4320": "8K",
            "2160": "4K",
            "1440": "2K",
            "1080": "1080p",
            "720": "720p",
            "480": "480p",
            "360": "360p",
            "240": "240p",
            "144": "144p",
        }
        for res, clean_name in mapping.items():
            if res in title_raw:
                return clean_name

        m_res = re.search(r'(\d{3,4})p?', title_raw)
        if m_res:
            res_num = m_res.group(1)
            if res_num in mapping:
                return mapping[res_num]
            return f"{res_num}p"

        clean_fallback = title_raw.replace("-", " ").strip()
        clean_fallback = re.sub(r'\s+', ' ', clean_fallback)
        return clean_fallback if clean_fallback else label

    def _parse_clean_size(self):
        label = self.format_info.get('label', '')
        clean = label.replace("🎬", "").replace("🎵", "").strip()
        m = self._SIZE_PATTERN.search(clean)
        if m:
            return m.group(1).strip()
        m_unk = self._UNKNOWN_PATTERN.search(clean)
        if m_unk or "unknown" in clean.lower():
            return tr("size_unknown", "Unknown")
        return ""

    def _update_check_icon(self):
        accent_hex = get_accent_hex()
        if self._is_selected:
            self.check_lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {accent_hex};
                    border-radius: 8px;
                    border: none;
                }}
            """)
            self.check_lbl.setPixmap(get_colored_icon("assets/icons/check.svg", "#ffffff").pixmap(QSize(10, 10)))
            self.check_lbl.show()
        else:
            self.check_lbl.clear()
            self.check_lbl.setStyleSheet("background: transparent; border: none;")
            self.check_lbl.hide()

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._update_check_icon()
        self._apply_style()

    def is_selected(self) -> bool:
        return self._is_selected

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._is_hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._apply_style()
        super().leaveEvent(event)

    def _get_is_dark(self):
        p = self.parent()
        while p:
            if hasattr(p, 'main_app') and hasattr(p.main_app, 'theme_manager'):
                return p.main_app.theme_manager.get_actual_theme() == "dark"
            p = p.parent()
        return get_current_theme_color() == "#f1f5f9"

    def _apply_style(self):
        is_dark = self._get_is_dark()
        accent = get_accent_hex()

        if "#" in accent and len(accent) == 7:
            r = int(accent[1:3], 16)
            g = int(accent[3:5], 16)
            b = int(accent[5:7], 16)
            sel_bg = f"rgba({r}, {g}, {b}, {0.15 if is_dark else 0.12})"
        else:
            sel_bg = "rgba(59, 130, 246, 0.12)"

        if self._is_selected:
            bg_color = sel_bg
            border_color = accent
            title_color = accent if not is_dark else "#ffffff"
            size_color = "#475569" if not is_dark else "#94a3b8"
        elif self._is_hovered:
            bg_color = "#162235" if is_dark else "#f1f5f9"
            border_color = "rgba(148, 163, 184, 0.4)" if is_dark else "#cbd5e1"
            title_color = "#f8fafc" if is_dark else "#0f172a"
            size_color = "#94a3b8" if is_dark else "#64748b"
        else:
            bg_color = "#0e1626" if is_dark else "#ffffff"
            border_color = "#1e293b" if is_dark else "#e2e8f0"
            title_color = "#cbd5e1" if is_dark else "#0f172a"
            size_color = "#64748b" if is_dark else "#64748b"

        self.setStyleSheet(f"""
            QualityTileWidget {{
                background-color: {bg_color};
                border: 1.5px solid {border_color};
                border-radius: 14px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setStyleSheet(f"color: {title_color}; font-weight: bold;")
        if hasattr(self, 'size_lbl'):
            self.size_lbl.setStyleSheet(f"color: {size_color};")
        if hasattr(self, 'type_icon_lbl'):
            is_audio = self.format_info.get('type') == 'audio' or str(self.format_info.get('format_code', '')).startswith('audio:')
            icon_path = "assets/icons/music.svg" if is_audio else "assets/icons/video.svg"
            if self._is_selected:
                icon_color = accent
            elif self._is_hovered:
                icon_color = "#f8fafc" if is_dark else "#0f172a"
            else:
                icon_color = "#64748b" if is_dark else "#94a3b8"
            self.type_icon_lbl.setPixmap(get_colored_icon(icon_path, icon_color).pixmap(QSize(14, 14)))


class QualityTileSkeleton(QFrame):
    """
    مربع جودة هيكلي نابض (Pulse Shimmer) يظهر أثناء عملية جلب الصيغ.
    يحاكي شكل وتوزيع مربع الجودة الحقيقي (أيقونة، عنوان الجودة، حجم الملف).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QualityTileSkeleton")
        self.setFixedHeight(78)
        self.setMinimumWidth(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._alpha = 90
        self._direction = 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse_tick)

        self._initUI()
        self._apply_style()

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top row: icon placeholder (left) + check placeholder (right)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.icon_box = QFrame(self)
        self.icon_box.setFixedSize(14, 14)
        top_row.addWidget(self.icon_box)

        top_row.addStretch()

        self.check_box = QFrame(self)
        self.check_box.setFixedSize(14, 14)
        top_row.addWidget(self.check_box)

        layout.addLayout(top_row)

        # Title line placeholder (centered)
        title_h = QHBoxLayout()
        title_h.setContentsMargins(0, 0, 0, 0)
        title_h.addStretch()
        self.title_bar = QFrame(self)
        self.title_bar.setFixedSize(64, 12)
        title_h.addWidget(self.title_bar)
        title_h.addStretch()
        layout.addLayout(title_h)

        # Size line placeholder (centered)
        size_h = QHBoxLayout()
        size_h.setContentsMargins(0, 0, 0, 0)
        size_h.addStretch()
        self.size_bar = QFrame(self)
        self.size_bar.setFixedSize(46, 9)
        size_h.addWidget(self.size_bar)
        size_h.addStretch()
        layout.addLayout(size_h)

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
            bg_tile = f"rgba(15, 23, 42, {0.6 + a_frac * 0.3:.2f})"
            border_tile = f"rgba(51, 65, 85, {0.4 + a_frac * 0.4:.2f})"
            inner_fill = f"rgba(71, 85, 105, {a_frac:.2f})"
        else:
            bg_tile = f"rgba(248, 250, 252, {0.7 + a_frac * 0.3:.2f})"
            border_tile = f"rgba(226, 232, 240, {0.8 + a_frac * 0.2:.2f})"
            inner_fill = f"rgba(203, 213, 225, {0.6 + a_frac * 0.35:.2f})"

        self.setStyleSheet(f"""
            QFrame#QualityTileSkeleton {{
                background-color: {bg_tile};
                border: 1.5px solid {border_tile};
                border-radius: 12px;
            }}
        """)
        inner_style = f"background-color: {inner_fill}; border: none; border-radius: 4px;"
        self.icon_box.setStyleSheet(inner_style)
        self.check_box.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 7px;")
        self.title_bar.setStyleSheet(inner_style)
        self.size_bar.setStyleSheet(f"background-color: {inner_fill}; border: none; border-radius: 3px;")

    def showEvent(self, event):
        self._alpha = 90
        self._direction = 1
        self._apply_style()
        self.timer.start(35)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)


class QualityGridWidget(QWidget):
    """
    شبكة تفاعلية منظمة تحتوي على مربعات الجودة، مع دعم التبديل السلس
    بين جودات الفيديو والصوت والترتيب التلقائي في صفوف متجاوبة.
    """
    quality_selected = pyqtSignal(int, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_formats = []
        self.video_formats = []
        self.audio_formats = []
        self.current_mode = "video"  # "video" | "audio"
        self.tile_widgets = []
        self.selected_format_code = ""
        self.selected_video_code = ""
        self.selected_audio_code = ""

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(10)
        for c in range(4):
            self.grid_layout.setColumnStretch(c, 1)

    def show_skeleton(self, count=4):
        """عرض مربعات جودة هيكلية نابضة (Skeleton Tiles) أثناء جلب الصيغ."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.tile_widgets.clear()

        columns = 4
        total_rows = (count + columns - 1) // columns
        tile_height = 78
        needed_height = total_rows * tile_height + max(0, total_rows - 1) * 10 + 8
        self.setFixedHeight(needed_height)

        for i in range(count):
            row = i // columns
            col = i % columns
            skel = QualityTileSkeleton(parent=self)
            self.grid_layout.addWidget(skel, row, col)
            self.tile_widgets.append(skel)

    def set_formats(self, format_list):
        self.all_formats = format_list
        self.video_formats = [f for f in format_list if f.get('type') == 'video']
        self.audio_formats = [f for f in format_list if f.get('type') == 'audio']
        if self.video_formats and not self.selected_video_code:
            self.selected_video_code = self.video_formats[0].get('format_code', '')
        if self.audio_formats and not self.selected_audio_code:
            self.selected_audio_code = self.audio_formats[0].get('format_code', '')
        self.render_mode(self.current_mode)

    def set_mode(self, mode: str):
        if mode in ["video", "audio"] and mode != self.current_mode:
            self.current_mode = mode
            self.render_mode(mode)

    def render_mode(self, mode: str):
        # Clean up existing tiles completely from layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.tile_widgets.clear()

        formats = self.video_formats if mode == "video" else self.audio_formats
        if not formats:
            return

        # Determine target selected code for this mode
        target_code = self.selected_video_code if mode == "video" else self.selected_audio_code
        available_codes = [f.get('format_code') for f in formats]
        if target_code not in available_codes:
            target_code = formats[0].get('format_code', '')
            if mode == "video":
                self.selected_video_code = target_code
            else:
                self.selected_audio_code = target_code
        self.selected_format_code = target_code

        columns = 4
        total_rows = (len(formats) + columns - 1) // columns
        tile_height = 78
        needed_height = total_rows * tile_height + max(0, total_rows - 1) * 10 + 8
        self.setFixedHeight(needed_height)

        for i, fmt in enumerate(formats):
            row = i // columns
            col = i % columns
            global_idx = self.all_formats.index(fmt) if fmt in self.all_formats else i
            is_sel = (fmt.get('format_code') == self.selected_format_code)

            tile = QualityTileWidget(global_idx, fmt, is_selected=is_sel, parent=self)
            tile.clicked.connect(self._on_tile_clicked)
            self.grid_layout.addWidget(tile, row, col)
            self.tile_widgets.append(tile)

        # Always emit the currently selected format info so the badge and backend sync
        selected_fmt = next((f for f in formats if f.get('format_code') == self.selected_format_code), formats[0])
        global_idx = self.all_formats.index(selected_fmt) if selected_fmt in self.all_formats else 0
        self.quality_selected.emit(global_idx, selected_fmt)

    def _on_tile_clicked(self, global_idx):
        if 0 <= global_idx < len(self.all_formats):
            fmt = self.all_formats[global_idx]
            self.selected_format_code = fmt.get('format_code', '')
            if self.current_mode == "video":
                self.selected_video_code = self.selected_format_code
            else:
                self.selected_audio_code = self.selected_format_code
            for tile in self.tile_widgets:
                tile.set_selected(tile.index == global_idx)
            self.quality_selected.emit(global_idx, fmt)

    def select_by_format_code(self, format_code: str):
        self.selected_format_code = format_code
        is_audio = any(f.get('format_code') == format_code for f in self.audio_formats)
        if is_audio:
            self.selected_audio_code = format_code
        else:
            self.selected_video_code = format_code
        desired_mode = "audio" if is_audio else "video"
        if desired_mode != self.current_mode:
            self.current_mode = desired_mode
            self.render_mode(desired_mode)
        else:
            for tile in self.tile_widgets:
                is_match = (tile.format_info.get('format_code') == format_code)
                tile.set_selected(is_match)
                if is_match:
                    self.quality_selected.emit(tile.index, tile.format_info)

    def update_theme(self):
        """تحديث ثيم ومظهر كافة مربعات الجودة الحالية."""
        for tile in self.tile_widgets:
            if hasattr(tile, '_apply_style'):
                tile._apply_style()


class SkeletonVideoCard(QFrame):
    """
    كارت هيكلي عصري ونابض (Skeleton Shimmer Card) يظهر أثناء عملية فحص الرابط
    وجلب بيانات الفيديو، ليمنح المستخدم شعوراً بالحداثة والسرعة ويثبت مكان الكارت في الشاشة.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SkeletonVideoCard")
        self.setFixedHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._alpha = 100
        self._direction = 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse_tick)

        self._initUI()

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        # ── Header Shimmer: Thumbnail + Text Lines ─────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # Thumbnail placeholder on the left
        self.thumb_box = QFrame(self)
        self.thumb_box.setFixedSize(220, 124)
        header_layout.addWidget(self.thumb_box)

        # Info placeholder lines on the right
        lines_layout = QVBoxLayout()
        lines_layout.setSpacing(10)

        self.bar_title1 = QFrame(self)
        self.bar_title1.setFixedHeight(18)
        self.bar_title1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lines_layout.addWidget(self.bar_title1)

        self.bar_title2 = QFrame(self)
        self.bar_title2.setFixedHeight(14)
        self.bar_title2.setFixedWidth(260)
        lines_layout.addWidget(self.bar_title2)

        self.bar_meta = QFrame(self)
        self.bar_meta.setFixedHeight(12)
        self.bar_meta.setFixedWidth(180)
        lines_layout.addWidget(self.bar_meta)

        self.bar_badge = QFrame(self)
        self.bar_badge.setFixedHeight(24)
        self.bar_badge.setFixedWidth(200)
        lines_layout.addWidget(self.bar_badge)

        lines_layout.addStretch()
        header_layout.addLayout(lines_layout)

        layout.addLayout(header_layout)

        # ── Tab placeholder ───────────────────────────────────────────────────
        self.tab_bar_box = QFrame(self)
        self.tab_bar_box.setFixedHeight(36)
        layout.addWidget(self.tab_bar_box)

        # ── Quality Tiles Placeholder (Row of 4) ──────────────────────────────
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(10)
        self.tile_boxes = []
        for _ in range(4):
            box = QFrame(self)
            box.setFixedHeight(64)
            tiles_layout.addWidget(box)
            self.tile_boxes.append(box)
        layout.addLayout(tiles_layout)

        layout.addStretch()

    def _get_is_dark(self):
        p = self.parent()
        while p:
            if hasattr(p, 'main_app') and hasattr(p.main_app, 'theme_manager'):
                return p.main_app.theme_manager.get_actual_theme() == "dark"
            p = p.parent()
        return get_current_theme_color() == "#f1f5f9"

    def _pulse_tick(self):
        self._alpha += 4 * self._direction
        if self._alpha >= 180:
            self._direction = -1
        elif self._alpha <= 70:
            self._direction = 1
        self._apply_pulse_style()

    def _apply_pulse_style(self):
        is_dark = self._get_is_dark()
        a_frac = self._alpha / 255.0

        if is_dark:
            bg_card = "#0b1120"
            border_card = "rgba(51, 65, 85, 0.4)"
            c_fill = f"rgba(51, 65, 85, {a_frac:.2f})"
            c_border = f"rgba(71, 85, 105, {a_frac * 0.8:.2f})"
        else:
            bg_card = "#ffffff"
            border_card = "#cbd5e1"
            c_fill = f"rgba(226, 232, 240, {0.6 + a_frac * 0.35:.2f})"
            c_border = f"rgba(203, 213, 225, {0.7 + a_frac * 0.3:.2f})"

        self.setStyleSheet(f"""
            QFrame#SkeletonVideoCard {{
                background-color: {bg_card};
                border: 1.5px solid {border_card};
                border-radius: 16px;
            }}
            QFrame {{
                background-color: {c_fill};
                border: 1px solid {c_border};
                border-radius: 8px;
            }}
        """)

    def update_theme(self):
        self._apply_pulse_style()

    def showEvent(self, event):
        self._alpha = 100
        self._direction = 1
        self._apply_pulse_style()
        self.timer.start(35)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
