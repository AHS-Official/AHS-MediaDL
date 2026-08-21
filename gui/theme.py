"""
╔══════════════════════════════════════════════════════════════╗
║           PyQt6 Modern Design System                         ║
║           Deep Charcoal & Indigo/Blue  |  Sleek & Rounded    ║
╚══════════════════════════════════════════════════════════════╝
"""

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel
from PyQt6.QtGui import QFont, QFontDatabase, QPalette, QColor
from PyQt6.QtCore import QObject, pyqtSignal
from utils.settings import app_config

# ─────────────────────────────────────────────
#  COLOR TOKENS
# ─────────────────────────────────────────────

DARK = {
    "bg_base":        "#131417",
    "bg_sidebar":     "#181a1f",
    "bg_card":        "#1e2026",
    "bg_elevated":    "#242730",
    "bg_float":       "#2b2e38",
    "bg_input":       "#181a1f",
    "bg_hover":       "#2a2d36",
    "bg_selected":    "#2b344e",
    "border":         "#2a2d36",
    "border_subtle":  "rgba(255, 255, 255, 0.07)",
    "border_focus":   "#4c75f2",
    "text_primary":   "#f3f4f6",
    "text_secondary": "#9ca3af",
    "text_muted":     "#6b7280",
    "text_disabled":  "#4b5563",
    "text_link":      "#60a5fa",
    "accent":         "#4c75f2",
    "accent_hover":   "#5b82ff",
    "accent_pressed": "#3c62dc",
    "accent_text":    "#ffffff",
    "accent_subtle":  "rgba(76, 117, 242, 0.15)",
    "success":        "#10b981",
    "success_subtle": "rgba(16, 185, 129, 0.15)",
    "warning":        "#f59e0b",
    "warning_subtle": "rgba(245, 158, 11, 0.15)",
    "error":          "#ef4444",
    "error_subtle":   "rgba(239, 68, 68, 0.15)",
    "info":           "#3b82f6",
    "scrollbar_bg":   "transparent",
    "scrollbar_handle": "#374151",
    "scrollbar_hover":  "#4b5563",
}

LIGHT = {
    "bg_base":        "#f8fafc",
    "bg_sidebar":     "#f1f5f9",
    "bg_card":        "#ffffff",
    "bg_elevated":    "#ffffff",
    "bg_float":       "#f8fafc",
    "bg_input":       "#ffffff",
    "bg_hover":       "#e2e8f0",
    "bg_selected":    "#e0e7ff",
    "border":         "#e2e8f0",
    "border_subtle":  "rgba(0, 0, 0, 0.06)",
    "border_focus":   "#4c75f2",
    "text_primary":   "#0f172a",
    "text_secondary": "#64748b",
    "text_muted":     "#94a3b8",
    "text_disabled":  "#cbd5e1",
    "text_link":      "#2563eb",
    "accent":         "#4c75f2",
    "accent_hover":   "#3b62dc",
    "accent_pressed": "#2d4ec2",
    "accent_text":    "#ffffff",
    "accent_subtle":  "rgba(76, 117, 242, 0.12)",
    "success":        "#10b981",
    "success_subtle": "rgba(16, 185, 129, 0.12)",
    "warning":        "#d97706",
    "warning_subtle": "rgba(217, 119, 6, 0.12)",
    "error":          "#dc2626",
    "error_subtle":   "rgba(220, 38, 38, 0.12)",
    "info":           "#2563eb",
    "scrollbar_bg":   "transparent",
    "scrollbar_handle": "#cbd5e1",
    "scrollbar_hover":  "#94a3b8",
}

# ─────────────────────────────────────────────
#  TYPOGRAPHY & RADIUS TOKENS
# ─────────────────────────────────────────────

FONTS = {
    "family_ui":   "Segoe UI, Noto Sans Arabic, Inter, Ubuntu, sans-serif",
    "family_mono": "Consolas, JetBrains Mono, Ubuntu Mono, monospace",
    "size_xs":   10,
    "size_sm":   11,
    "size_base":  12,
    "size_md":   13,
    "size_lg":   15,
    "size_xl":   18,
    "size_h1":   24,
    "size_h2":   20,
    "size_h3":   16,
}

RADIUS = {
    "sm":   6,
    "md":   8,
    "lg":  12,
    "xl":  16,
    "full": 999,
}

# ─────────────────────────────────────────────
#  THEME MANAGER (Singleton)
# ─────────────────────────────────────────────

class Theme(QObject):
    changed = pyqtSignal()
    _inst = None

    def __init__(self):
        super().__init__()
        self._mode = "dark"

    @classmethod
    def instance(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        if mode not in ("dark", "light"):
            mode = "dark"
        if self._mode != mode:
            self._mode = mode
            self.changed.emit()

    def toggle(self):
        self.set_mode("light" if self._mode == "dark" else "dark")

    def is_dark(self) -> bool:
        return self._mode == "dark"

    @property
    def palette(self) -> dict:
        return DARK if self._mode == "dark" else LIGHT

    def color(self, key: str) -> str:
        return self.palette.get(key, "#4c75f2")

    def qcolor(self, key: str) -> QColor:
        return QColor(self.color(key))

    @staticmethod
    def font(size_key: str = "size_base", bold: bool = False, mono: bool = False) -> QFont:
        family = app_config.get("font_family", "system")
        if family == "system":
            family = FONTS["family_mono"] if mono else FONTS["family_ui"]
        
        if size_key == "size_base":
            size = app_config.get("font_size", FONTS["size_base"])
        else:
            size = FONTS.get(size_key, FONTS["size_base"])
            
        f = QFont(family, size)
        f.setBold(bold)
        return f

# ─────────────────────────────────────────────
#  STYLESHEET GENERATOR
# ─────────────────────────────────────────────

def _css(theme: Theme) -> str:
    c = theme.palette
    r = RADIUS
    f = FONTS

    custom_font = app_config.get("font_family", "system")
    ui_font = f['family_ui'] if custom_font == "system" else custom_font
    base_size = app_config.get("font_size", f['size_base'])

    return f"""
QWidget {{
    background-color: {c['bg_base']};
    color: {c['text_primary']};
    font-family: {ui_font};
    font-size: {base_size}pt;
    border: none;
    outline: none;
}}

QLabel {{
    background-color: transparent;
    color: {c['text_primary']};
}}

QCheckBox, QRadioButton {{
    background-color: transparent;
    color: {c['text_primary']};
}}

QToolTip {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    padding: 6px 10px;
    border-radius: {r['md']}px;
    font-size: {f['size_sm']}pt;
}}

QMainWindow, QDialog {{
    background-color: {c['bg_base']};
}}

/* ═════════════════════════════════════════════
   SIDEBAR & NAVIGATION
   ═════════════════════════════════════════════ */

QWidget#Sidebar {{
    background-color: {c['bg_sidebar']};
    border-right: 1px solid {c['border_subtle']};
}}

QLabel#SidebarBrand {{
    font-size: 15pt;
    font-weight: 800;
    color: {c['text_primary']};
    padding: 6px 4px;
}}

QPushButton#SidebarNavBtn {{
    background-color: transparent;
    color: {c['text_secondary']};
    border: 1px solid transparent;
    border-radius: {r['md']}px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#SidebarNavBtn:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
}}

QPushButton#SidebarNavBtn[active="true"] {{
    background-color: {c['accent_subtle']};
    color: {c['accent']};
    border: 1px solid rgba(76, 117, 242, 0.35);
    font-weight: bold;
}}

QPushButton#ThemeToggleBtn {{
    background-color: {c['bg_card']};
    color: {c['text_secondary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 8px 12px;
    font-weight: bold;
    font-size: 12px;
}}

QPushButton#ThemeToggleBtn:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
    border-color: {c['border_focus']};
}}

QLabel#NavBadge {{
    background-color: {c['accent']};
    color: #ffffff;
    font-size: 10px;
    font-weight: bold;
    border-radius: 9px;
    padding: 2px 6px;
    min-width: 12px;
    text-align: center;
}}

QPushButton#SettingsSegmentBtn {{
    background-color: transparent;
    color: {c['text_secondary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#SettingsSegmentBtn:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
}}

QPushButton#SettingsSegmentBtn[active="true"] {{
    background-color: {c['accent_subtle']};
    color: {c['accent']};
    border: 1px solid {c['accent']};
    font-weight: bold;
}}

/* ═════════════════════════════════════════════
   BUTTONS
   ═════════════════════════════════════════════ */

QPushButton {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 6px 16px;
    font-size: {f['size_base']}pt;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
}}

QPushButton:pressed {{
    background-color: {c['bg_float']};
}}

QPushButton:disabled {{
    color: {c['text_disabled']};
    border-color: {c['border_subtle']};
    background-color: transparent;
}}

QPushButton#primary {{
    background-color: {c['accent']};
    color: {c['accent_text']};
    border: 1px solid {c['accent']};
    font-weight: bold;
}}

QPushButton#primary:hover {{
    background-color: {c['accent_hover']};
    border-color: {c['accent_hover']};
}}

QPushButton#primary:pressed {{
    background-color: {c['accent_pressed']};
}}

QPushButton#primary:disabled {{
    background-color: {c['bg_card']};
    color: {c['text_disabled']};
    border-color: {c['border_subtle']};
}}

QPushButton#danger {{
    background-color: {c['error_subtle']};
    color: {c['error']};
    border: 1px solid rgba(239, 68, 68, 0.2);
    font-weight: 600;
}}

QPushButton#danger:hover {{
    background-color: {c['error']};
    color: #ffffff;
    border-color: {c['error']};
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {c['border']}; 
    color: {c['text_secondary']};
}}

QPushButton#ghost:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
    border-color: {c['text_muted']};
}}

QPushButton#icon_btn {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 0px;
    font-size: 14px;
}}

QPushButton#icon_btn:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
}}

/* ═════════════════════════════════════════════
   INPUTS & COMBOBOX
   ═════════════════════════════════════════════ */

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 6px 12px;
    selection-background-color: {c['accent_subtle']};
    selection-color: {c['text_primary']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {c['border_focus']};
    background-color: {c['bg_card']};
}}

QLineEdit::placeholder {{
    color: {c['text_muted']};
}}

QComboBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 6px 12px;
    min-height: 26px;
}}

QComboBox:focus {{
    border-color: {c['border_focus']};
}}

QComboBox:hover {{
    background-color: {c['bg_hover']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    selection-background-color: {c['accent_subtle']};
    selection-color: {c['accent']};
    padding: 6px;
    outline: none;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 6px 10px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {c['border_focus']};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 18px;
}}

/* ═════════════════════════════════════════════
   CHECKBOXES & PROGRESS BARS
   ═════════════════════════════════════════════ */

QCheckBox, QRadioButton {{
    spacing: 8px;
    color: {c['text_primary']};
    font-weight: 500;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {c['border']};
    border-radius: {r['sm']}px;
    background-color: {c['bg_input']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}

QCheckBox::indicator:hover {{
    border-color: {c['border_focus']};
}}

QProgressBar {{
    background-color: {c['bg_float']};
    border: none;
    border-radius: {r['sm']}px;
    text-align: center;
    color: {c['text_secondary']};
    font-size: {f['size_xs']}pt;
    min-height: 8px;
    max-height: 8px;
}}

QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: {r['sm']}px;
}}

/* ═════════════════════════════════════════════
   CARDS & FRAMES
   ═════════════════════════════════════════════ */

QFrame#PreviewCard, QFrame#OptionsCard, QFrame#UnifiedMediaCard {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: {r['lg']}px;
}}

QFrame#PreviewCard:hover, QFrame#OptionsCard:hover, QFrame#UnifiedMediaCard:hover {{
    border-color: rgba(76, 117, 242, 0.4);
}}

QWidget#QueueCard {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: {r['lg']}px;
    margin-bottom: 8px;
}}

QWidget#QueueCard:hover {{
    border-color: rgba(76, 117, 242, 0.5);
    background-color: {c['bg_elevated']};
}}

QWidget#PlaylistItem {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    margin-bottom: 6px;
}}

QWidget#PlaylistItem:hover {{
    background-color: {c['bg_hover']};
    border-color: rgba(76, 117, 242, 0.4);
}}

QLabel#Thumbnail {{
    background-color: {c['bg_float']};
    border-radius: {r['md']}px;
}}

QLabel#DurationBadge {{
    background-color: rgba(0, 0, 0, 0.75);
    color: #ffffff;
    font-size: 10px;
    font-weight: bold;
    border-radius: 4px;
    padding: 2px 6px;
}}

/* ═════════════════════════════════════════════
   SCROLLBARS
   ═════════════════════════════════════════════ */

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {c['scrollbar_handle']};
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    height: 0px;
}}
"""

def apply_theme(app: QApplication, mode: str = "dark"):
    if mode == "auto":
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import Qt
        
        mode = "dark"
        try:
            scheme = QGuiApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                mode = "light"
        except Exception:
            mode = "dark"

    theme = Theme.instance()
    theme.set_mode(mode)
    app.setStyleSheet(_css(theme))
    app.setFont(Theme.font("size_base"))

def refresh_theme(app: QApplication):
    app.setStyleSheet(_css(Theme.instance()))

# ─────────────────────────────────────────────
#  WIDGET HELPERS
# ─────────────────────────────────────────────

class styled:
    @staticmethod
    def primary_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("primary")
        return btn

    @staticmethod
    def danger_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("danger")
        return btn

    @staticmethod
    def ghost_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("ghost")
        return btn

    @staticmethod
    def title_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("title")
        lbl.setFont(Theme.font("size_h3", bold=True))
        return lbl

    @staticmethod
    def secondary_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("secondary")
        return lbl