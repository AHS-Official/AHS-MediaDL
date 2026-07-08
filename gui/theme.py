"""
╔══════════════════════════════════════════════════════════════╗
║           PyQt6 Design System — JetBrains-inspired          ║
║           Dark / Light  |  Modern & Minimal                  ║
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
    "bg_base":        "#1e1f22",
    "bg_elevated":    "#2b2d30",
    "bg_float":       "#3c3f41",
    "bg_input":       "#2b2d30",
    "bg_hover":       "#383b40",
    "bg_selected":    "#214283",
    "border":         "#3c3f41",
    "border_focus":   "#4d78cc",
    "text_primary":   "#dfe1e5",
    "text_secondary": "#8c8fa3",
    "text_disabled":  "#4a4d5a",
    "text_link":      "#6b9fe4",
    "accent":         "#4d78cc",
    "accent_hover":   "#5a88e0",
    "accent_pressed": "#3d6ab8",
    "accent_text":    "#ffffff",
    "success":        "#5fb760",
    "warning":        "#e3a32e",
    "error":          "#e06c75",
    "info":           "#6b9fe4",
    "scrollbar_bg":   "#1e1f22",
    "scrollbar_handle": "#4a4d5a",
    "scrollbar_hover":  "#6b6e7a",
}

LIGHT = {
    "bg_base":        "#f7f8fa",
    "bg_elevated":    "#ffffff",
    "bg_float":       "#f0f1f3",
    "bg_input":       "#ffffff",
    "bg_hover":       "#e8eaed",
    "bg_selected":    "#d4e3fc",
    "border":         "#d1d3db",
    "border_focus":   "#4d78cc",
    "text_primary":   "#1a1b1e",
    "text_secondary": "#6c6f7a",
    "text_disabled":  "#b0b3be",
    "text_link":      "#3b6eb5",
    "accent":         "#4d78cc",
    "accent_hover":   "#3d6ab8",
    "accent_pressed": "#2d5aa0",
    "accent_text":    "#ffffff",
    "success":        "#3d8b40",
    "warning":        "#b07d1a",
    "error":          "#c0392b",
    "info":           "#3b6eb5",
    "scrollbar_bg":   "#f7f8fa",
    "scrollbar_handle": "#c4c7d0",
    "scrollbar_hover":  "#a0a3b0",
}

# ─────────────────────────────────────────────
#  TYPOGRAPHY & RADIUS TOKENS
# ─────────────────────────────────────────────

FONTS = {
    "family_ui":   "Noto Sans Arabic, Inter, Ubuntu, sans-serif",
    "family_mono": "JetBrains Mono, Ubuntu Mono, monospace",
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

SPACING = {
    "xs":   4,
    "sm":   8,
    "md":  12,
    "lg":  16,
    "xl":  24,
    "xxl": 32,
}
RADIUS = {
    "sm":   4,
    "md":   6,
    "lg":  10,
    "full": 999,
}

# ─────────────────────────────────────────────
#  THEME MANAGER (Fixed Singleton)
# ─────────────────────────────────────────────

class Theme(QObject):
    """
    Singleton theme manager.
    """
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
        assert mode in ("dark", "light"), "mode must be 'dark' or 'light'"
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
        return self.palette.get(key, "#ff00ff")

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

    @staticmethod
    def sp(key: str) -> int:
        return SPACING.get(key, 8)

    @staticmethod
    def r(key: str) -> int:
        return RADIUS.get(key, 6)

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

QToolTip {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_focus']};
    padding: 6px;
    border-radius: {r['md']}px;
    font-size: {f['size_sm']}pt;
}}

QMainWindow, QDialog {{ background-color: {c['bg_base']}; }}

QPushButton {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 5px 14px;
    font-size: {f['size_base']}pt;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
}}
QPushButton:pressed {{ background-color: {c['bg_float']}; }}
QPushButton:disabled {{
    color: {c['text_disabled']};
    border-color: {c['border']};
    background-color: {c['bg_base']};
}}

QPushButton#primary {{
    background-color: {c['accent']};
    color: {c['accent_text']};
    border: none;
    font-weight: bold;
}}
QPushButton#primary:hover {{ background-color: {c['accent_hover']}; }}
QPushButton#primary:pressed {{ background-color: {c['accent_pressed']}; }}

QPushButton#danger {{
    background-color: transparent;
    color: {c['error']};
    border: 1px solid {c['error']};
}}
QPushButton#danger:hover {{
    background-color: {c['error']};
    color: #ffffff;
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {c['border']}; 
    color: {c['text_secondary']};
}}
QPushButton#ghost:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 4px 8px;
    selection-background-color: {c['bg_selected']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {c['border_focus']}; }}
QLineEdit::placeholder {{ color: {c['text_disabled']}; }}

QComboBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 4px 8px;
    min-height: 24px;
}}
QComboBox:focus {{ border-color: {c['border_focus']}; }}
QComboBox:hover {{ background-color: {c['bg_hover']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg_float']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    selection-background-color: {c['bg_selected']};
    padding: 4px;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    padding: 4px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {c['border_focus']}; }}
QSpinBox::up-button, QSpinBox::down-button {{ background-color: transparent; border: none; width: 16px; }}

QCheckBox, QRadioButton {{ spacing: 6px; color: {c['text_primary']}; }}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c['border']};
    border-radius: {r['sm']}px;
    background-color: {c['bg_input']};
}}
QCheckBox::indicator:checked {{ background-color: {c['accent']}; border-color: {c['accent']}; }}
QCheckBox::indicator:hover {{ border-color: {c['border_focus']}; }}

QProgressBar {{
    background-color: {c['bg_float']};
    border: none;
    border-radius: {r['sm']}px;
    text-align: center;
    color: {c['text_secondary']};
    font-size: {f['size_sm']}pt;
    min-height: 6px;
    max-height: 10px;
}}
QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: {r['sm']}px;
}}

QLabel {{ color: {c['text_primary']}; background: transparent; }}
QLabel#secondary {{ color: {c['text_secondary']}; font-size: {f['size_sm']}pt; }}
QLabel#title {{ font-size: {f['size_h3']}pt; font-weight: bold; }}
QLabel#Thumbnail {{ background-color: {c['bg_elevated']}; border-radius: {r['md']}px; }}
QWidget#PlaylistItem {{ border-bottom: 1px solid {c['border']}; margin-bottom: 2px; }}
QFrame#PreviewCard {{ background-color: {c['bg_elevated']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QFrame#OptionsCard {{ background-color: {c['bg_elevated']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QWidget#PlaylistItem:hover {{ background-color: {c['bg_hover']}; }}
QWidget#QueueItem {{ margin-bottom: 5px; }}

QTabWidget::pane {{
    border: 1px solid {c['border']};
    border-radius: {r['md']}px;
    background-color: {c['bg_elevated']};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c['text_secondary']};
    padding: 6px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: {f['size_base']}pt;
}}
QTabBar::tab:selected {{
    color: {c['text_primary']};
    border-bottom: 2px solid {c['accent']};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    color: {c['text_primary']};
    background-color: {c['bg_hover']};
    border-radius: {r['sm']}px {r['sm']}px 0 0;
}}

QScrollArea {{ border: none; background-color: transparent; }}
QScrollArea > QWidget > QWidget {{ background-color: transparent; }}

QScrollBar:vertical {{
    background-color: {c['scrollbar_bg']};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{ background-color: {c['scrollbar_handle']}; min-height: 30px; border-radius: 5px; }}
QScrollBar::handle:vertical:hover {{ background-color: {c['scrollbar_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

def apply_theme(app: QApplication, mode: str = "dark"):
    if mode == "auto":
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import Qt
        
        # الوضع الافتراضي في حال لم نتمكن من قراءة النظام
        mode = "light"
        
        # قراءة ثيم النظام مباشرة عبر Qt (ممتازة ومثالية لويندوز)
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
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