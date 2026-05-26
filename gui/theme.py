from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# ──────────────────────────────────────────────
#  Color Tokens
# ──────────────────────────────────────────────

class DarkColors:
    BG_PRIMARY    = "#1e1e2e"
    BG_SECONDARY  = "#252535"
    BG_TERTIARY   = "#2a2a3e"
    SURFACE       = "#313145"
    SURFACE_2     = "#3a3a52"
    BORDER        = "#4a4a6a"
    BORDER_FOCUS  = "#7c6af7"
    ACCENT        = "#7c6af7"
    ACCENT_LIGHT  = "#9d8ff9"
    ACCENT_DIM    = "rgba(124,106,247,0.15)"
    TEXT_PRIMARY  = "#e2e2f0"
    TEXT_SECONDARY= "#a0a0c0"
    TEXT_HINT     = "#6060a0"
    SUCCESS       = "#4ec9a0"
    WARNING       = "#e5c07b"
    DANGER        = "#e06c75"
    INFO          = "#61afef"
    SUCCESS_BG    = "rgba(78,201,160,0.12)"
    WARNING_BG    = "rgba(229,192,123,0.12)"
    DANGER_BG     = "rgba(224,108,117,0.12)"
    INFO_BG       = "rgba(97,175,239,0.12)"


class LightColors:
    BG_PRIMARY    = "#f5f5fa"
    BG_SECONDARY  = "#eeeeF7"
    BG_TERTIARY   = "#e8e8f4"
    SURFACE       = "#ffffff"
    SURFACE_2     = "#f0f0f8"
    BORDER        = "#d0d0e8"
    BORDER_FOCUS  = "#6c5ce7"
    ACCENT        = "#6c5ce7"
    ACCENT_LIGHT  = "#8577ef"
    ACCENT_DIM    = "rgba(108,92,231,0.10)"
    TEXT_PRIMARY  = "#1a1a2e"
    TEXT_SECONDARY= "#555580"
    TEXT_HINT     = "#9090b0"
    SUCCESS       = "#27ae60"
    WARNING       = "#c07a00"
    DANGER        = "#c0392b"
    INFO          = "#2980b9"
    SUCCESS_BG    = "rgba(39,174,96,0.10)"
    WARNING_BG    = "rgba(192,122,0,0.10)"
    DANGER_BG     = "rgba(192,57,43,0.10)"
    INFO_BG       = "rgba(41,128,185,0.10)"


# ──────────────────────────────────────────────
#  Typography
# ──────────────────────────────────────────────

class Typography:
    FONT_FAMILY = "Cairo"
    FONT_MONO   = "JetBrains Mono"
    SIZE_XS  = 10
    SIZE_SM  = 11
    SIZE_BASE= 12
    SIZE_MD  = 13
    SIZE_LG  = 15
    SIZE_XL  = 18

    @staticmethod
    def base() -> QFont:
        return QFont(Typography.FONT_FAMILY, Typography.SIZE_BASE)

    @staticmethod
    def heading(size: int = 15) -> QFont:
        f = QFont(Typography.FONT_FAMILY, size)
        f.setWeight(QFont.Weight.DemiBold)
        return f

    @staticmethod
    def mono(size: int = 12) -> QFont:
        return QFont(Typography.FONT_MONO, size)


# ──────────────────────────────────────────────
#  Spacing & Radius
# ──────────────────────────────────────────────

class Spacing:
    XS = 4; SM = 6; MD = 8; LG = 12; XL = 16; XXL = 24

class Radius:
    SM = 4; MD = 6; LG = 10; XL = 14; XXL = 18


# ──────────────────────────────────────────────
#  Stylesheet Generator
# ──────────────────────────────────────────────

def _build_stylesheet(c) -> str:
    return f"""
QWidget {{
    background-color: {c.BG_PRIMARY};
    color: {c.TEXT_PRIMARY};
    font-family: "{Typography.FONT_FAMILY}";
    font-size: {Typography.SIZE_BASE}pt;
    border: none;
    outline: none;
}}
QMainWindow {{ background-color: {c.BG_PRIMARY}; }}

/* ── Sidebar Navigation ── */
QFrame#Sidebar {{
    background-color: {c.BG_SECONDARY};
    border-right: 1px solid {c.BORDER};
}}
QPushButton#SidebarButton {{
    background-color: transparent;
    color: {c.TEXT_SECONDARY};
    text-align: left;
    padding: 14px 22px;
    border-radius: {Radius.MD}px;
    font-weight: 600;
    font-size: {Typography.SIZE_MD}pt;
    border: none;
}}
QPushButton#SidebarButton:hover {{
    background-color: {c.SURFACE};
    color: {c.TEXT_PRIMARY};
}}
QPushButton#SidebarButton:checked {{
    background-color: {c.ACCENT_DIM};
    color: {c.ACCENT_LIGHT};
    border-left: 4px solid {c.ACCENT};
}}

/* ── Modern Glow Card ── */
QFrame#GlowCard {{
    background-color: {c.SURFACE};
    border: 1px solid {c.BORDER};
    border-radius: {Radius.XL}px;
}}
QFrame#GlowCard:hover {{
    border-color: {c.BORDER_FOCUS};
}}

/* ── Queue Item Card ── */
QFrame#QueueItem {{
    background-color: {c.SURFACE};
    border: 1px solid {c.BORDER};
    border-radius: {Radius.LG}px;
}}
QFrame#QueueItem:hover {{
    border-color: {c.ACCENT};
    background-color: {c.BG_SECONDARY};
}}

/* ── Modern URL Bar Input ── */
QLineEdit#UrlInput {{
    background-color: {c.SURFACE};
    color: {c.TEXT_PRIMARY};
    border: 2px solid {c.BORDER};
    border-radius: {Radius.LG}px;
    padding: 8px 14px;
    font-size: {Typography.SIZE_MD}pt;
}}
QLineEdit#UrlInput:focus {{
    border-color: {c.ACCENT};
}}

/* ── Menu Bar ── */
QMenuBar {{
    background-color: {c.BG_SECONDARY};
    color: {c.TEXT_SECONDARY};
    padding: 2px 8px;
    border-bottom: 1px solid {c.BORDER};
}}
QMenuBar::item {{ padding: 4px 10px; border-radius: {Radius.SM}px; }}
QMenuBar::item:selected {{ background-color: {c.SURFACE}; color: {c.TEXT_PRIMARY}; }}
QMenu {{
    background-color: {c.SURFACE}; border: 1px solid {c.BORDER};
    border-radius: {Radius.MD}px; padding: 4px;
}}
QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: {Radius.SM}px; }}
QMenu::item:selected {{ background-color: {c.ACCENT_DIM}; color: {c.ACCENT_LIGHT}; }}
QMenu::separator {{ height: 1px; background: {c.BORDER}; margin: 4px 8px; }}

/* ── Tool Bar ── */
QToolBar {{
    background-color: {c.BG_TERTIARY};
    border-bottom: 1px solid {c.BORDER};
    padding: 4px 8px; spacing: 4px;
}}
QToolButton {{
    background: transparent; color: {c.TEXT_SECONDARY};
    border: 1px solid transparent; border-radius: {Radius.SM}px; padding: 4px 10px;
}}
QToolButton:hover {{ background: {c.SURFACE}; border-color: {c.BORDER}; color: {c.TEXT_PRIMARY}; }}
QToolButton:pressed, QToolButton:checked {{
    background: {c.ACCENT_DIM}; border-color: {c.ACCENT}; color: {c.ACCENT_LIGHT};
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {c.BG_SECONDARY}; color: {c.TEXT_HINT};
    border-top: 1px solid {c.BORDER}; font-size: {Typography.SIZE_SM}pt;
}}

/* ── Push Button ── */
QPushButton {{
    background-color: {c.SURFACE}; color: {c.TEXT_SECONDARY};
    border: 1px solid {c.BORDER}; border-radius: {Radius.MD}px;
    padding: 8px 18px; font-weight: bold;
}}
QPushButton:hover {{ background: {c.SURFACE_2}; border-color: {c.ACCENT}; color: {c.TEXT_PRIMARY}; }}
QPushButton:pressed {{ background: {c.ACCENT_DIM}; border-color: {c.ACCENT}; color: {c.ACCENT_LIGHT}; }}
QPushButton:disabled {{ color: {c.TEXT_HINT}; border-color: {c.BORDER}; background: transparent; }}
QPushButton#primary {{ background: {c.ACCENT}; color: #fff; border-color: {c.ACCENT}; }}
QPushButton#primary:hover {{ background: {c.ACCENT_LIGHT}; border-color: {c.ACCENT_LIGHT}; }}
QPushButton#danger {{ background: transparent; color: {c.DANGER}; border-color: {c.DANGER}; }}
QPushButton#danger:hover {{ background: {c.DANGER_BG}; }}

/* ── Line Edit ── */
QLineEdit {{
    background: {c.BG_PRIMARY}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER}; border-radius: {Radius.MD}px; padding: 6px 10px;
}}
QLineEdit:focus {{ border-color: {c.ACCENT}; }}
QLineEdit:disabled {{ color: {c.TEXT_HINT}; }}
QLineEdit[readOnly="true"] {{ color: {c.TEXT_HINT}; background: {c.BG_SECONDARY}; }}

/* ── Text Edit ── */
QTextEdit, QPlainTextEdit {{
    background: {c.BG_PRIMARY}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER}; border-radius: {Radius.MD}px; padding: 8px;
}}
QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {c.ACCENT}; }}

/* ── Combo Box ── */
QComboBox {{
    background-color: {c.SURFACE_2};
    color: {c.TEXT_PRIMARY};
    border: 1.5px solid {c.BORDER};
    border-radius: {Radius.MD}px;
    padding: 6px 12px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {c.ACCENT};
    background-color: {c.SURFACE};
}}
QComboBox:focus {{
    border-color: {c.BORDER_FOCUS};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {c.BG_SECONDARY};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {Radius.MD}px;
    padding: 4px;
    selection-background-color: {c.ACCENT_DIM};
    selection-color: {c.ACCENT_LIGHT};
}}
QComboBox QAbstractItemView::item {{
    background-color: {c.BG_SECONDARY};
    color: {c.TEXT_PRIMARY};
    padding: 6px 10px;
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {c.ACCENT_DIM};
    color: {c.ACCENT_LIGHT};
}}

/* ── Spin Box ── */
QSpinBox, QDoubleSpinBox {{
    background: {c.BG_PRIMARY}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER}; border-radius: {Radius.MD}px; padding: 5px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {c.ACCENT}; }}

/* ── Check Box ── */
QCheckBox {{ color: {c.TEXT_SECONDARY}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c.BORDER}; border-radius: {Radius.SM}px; background: {c.BG_PRIMARY};
}}
QCheckBox::indicator:hover {{ border-color: {c.ACCENT}; }}
QCheckBox::indicator:checked {{ background: {c.ACCENT}; border-color: {c.ACCENT}; }}
QCheckBox:hover {{ color: {c.TEXT_PRIMARY}; }}

/* ── Radio Button ── */
QRadioButton {{ color: {c.TEXT_SECONDARY}; spacing: 8px; }}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c.BORDER}; border-radius: 8px; background: {c.BG_PRIMARY};
}}
QRadioButton::indicator:checked {{ background: {c.ACCENT}; border-color: {c.ACCENT}; }}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 4px; background: {c.BORDER}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {c.ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -6px 0;
    border-radius: 8px; background: {c.ACCENT_LIGHT}; border: 2px solid {c.BG_PRIMARY};
}}
QSlider::handle:horizontal:hover {{ background: #ffffff; }}

/* ── Progress Bar ── */
QProgressBar {{
    background: {c.BORDER}; border: none; border-radius: 4px;
    height: 6px; color: transparent;
}}
QProgressBar::chunk {{ background: {c.ACCENT}; border-radius: 4px; }}

/* ── Scroll Bar ── */
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c.BORDER}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{
    background: {c.BORDER}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c.ACCENT}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: 1px solid {c.BORDER}; border-radius: {Radius.MD}px;
    background: {c.SURFACE}; top: -1px;
}}
QTabBar::tab {{
    background: transparent; color: {c.TEXT_HINT};
    padding: 7px 18px; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {c.ACCENT_LIGHT}; border-bottom-color: {c.ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: {c.TEXT_SECONDARY}; }}

/* ── Tree / List / Table ── */
QTreeView, QListView, QListWidget, QTreeWidget {{
    background: {c.BG_PRIMARY}; border: 1px solid {c.BORDER};
    border-radius: {Radius.MD}px; outline: none;
    alternate-background-color: {c.BG_SECONDARY};
}}
QTreeView::item, QListView::item, QListWidget::item, QTreeWidget::item {{
    padding: 5px 8px; border-radius: {Radius.SM}px;
}}
QTreeView::item:selected, QListView::item:selected,
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {c.ACCENT_DIM}; color: {c.ACCENT_LIGHT};
}}
QTreeView::item:hover, QListView::item:hover,
QListWidget::item:hover, QTreeWidget::item:hover {{ background: {c.SURFACE}; }}

QTableWidget, QTableView {{
    background: {c.BG_PRIMARY}; border: 1px solid {c.BORDER};
    border-radius: {Radius.MD}px; gridline-color: {c.BG_SECONDARY};
}}
QHeaderView::section {{
    background: {c.BG_TERTIARY}; color: {c.TEXT_HINT};
    border: none; border-bottom: 1px solid {c.BORDER};
    padding: 6px 10px; font-size: {Typography.SIZE_SM}pt; font-weight: 600;
}}
QTableView::item, QTableWidget::item {{ padding: 5px 10px; color: {c.TEXT_SECONDARY}; }}
QTableView::item:selected, QTableWidget::item:selected {{
    background: {c.ACCENT_DIM}; color: {c.TEXT_PRIMARY};
}}

/* ── Group Box ── */
QGroupBox {{
    border: 1px solid {c.BORDER}; border-radius: {Radius.LG}px;
    margin-top: 18px; padding: 12px 8px 8px;
    color: {c.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}pt; font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 12px; padding: 0 6px; background: {c.BG_PRIMARY};
}}

/* ── Labels ── */
QLabel {{ color: {c.TEXT_SECONDARY}; background: transparent; }}
QLabel#heading {{ color: {c.TEXT_PRIMARY}; font-size: {Typography.SIZE_LG}pt; font-weight: 600; }}
QLabel#hint {{ color: {c.TEXT_HINT}; font-size: {Typography.SIZE_SM}pt; }}

/* ── Splitter ── */
QSplitter::handle {{ background: {c.BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ── Dialog / MessageBox ── */
QDialog, QMessageBox {{ background: {c.BG_PRIMARY}; }}

/* ── Tool Tip ── */
QToolTip {{
    background: {c.SURFACE}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER}; border-radius: {Radius.SM}px; padding: 4px 8px;
    font-size: {Typography.SIZE_SM}pt;
}}

/* ── Dock Widget ── */
QDockWidget {{ color: {c.TEXT_SECONDARY}; }}
QDockWidget::title {{
    background: {c.BG_SECONDARY}; padding: 6px 10px;
    border-bottom: 1px solid {c.BORDER};
    font-size: {Typography.SIZE_SM}pt; font-weight: 600;
}}
"""


# ──────────────────────────────────────────────
#  AppTheme
# ──────────────────────────────────────────────

class AppTheme:
    DARK  = "dark"
    LIGHT = "light"
    AUTO  = "auto"
    _current_mode: str = DARK
    _user_choice: str = AUTO

    @classmethod
    def apply(cls, app: QApplication, mode: str = AUTO):
        cls._user_choice = mode
        
        try:
            app.styleHints().colorSchemeChanged.disconnect()
        except: pass
        
        if mode == cls.AUTO:
            app.styleHints().colorSchemeChanged.connect(lambda: cls._auto_update(app))
            cls._auto_update(app)
        else:
            cls._apply_specific(app, mode)

    @classmethod
    def _auto_update(cls, app: QApplication):
        """Monitor OS color scheme"""
        from PyQt6.QtCore import Qt
        scheme = app.styleHints().colorScheme()
        
        if scheme == Qt.ColorScheme.Dark:
            cls._apply_specific(app, cls.DARK)
        else:
            cls._apply_specific(app, cls.LIGHT)

    @classmethod
    def _apply_specific(cls, app: QApplication, mode: str):
        """Apply target theme"""
        cls._current_mode = mode
        c = DarkColors if mode == cls.DARK else LightColors
        app.setStyleSheet(_build_stylesheet(c))
        app.setFont(Typography.base())

    @classmethod
    def toggle(cls, app: QApplication):
        new_mode = cls.LIGHT if cls._current_mode == cls.DARK else cls.DARK
        cls.apply(app, new_mode)
        return new_mode

    @classmethod
    def current(cls) -> str:
        return cls._current_mode

    @classmethod
    def colors(cls):
        return DarkColors if cls._current_mode == cls.DARK else LightColors


def apply_theme(app: QApplication, mode: str = AppTheme.DARK):
    # Load custom font family and font size from app_config dynamically
    try:
        from data.settings import app_config
        font_family = app_config.get("font_family", "System Default")
        if font_family == "System Default":
            font_family = "Cairo"
        Typography.FONT_FAMILY = font_family

        try:
            Typography.SIZE_BASE = int(app_config.get("font_size", 12))
        except (ValueError, TypeError):
            Typography.SIZE_BASE = 12

        # Dynamically recalculate relative sizes
        Typography.SIZE_XS = max(8, Typography.SIZE_BASE - 2)
        Typography.SIZE_SM = max(9, Typography.SIZE_BASE - 1)
        Typography.SIZE_MD = Typography.SIZE_BASE + 1
        Typography.SIZE_LG = Typography.SIZE_BASE + 3
        Typography.SIZE_XL = Typography.SIZE_BASE + 6
    except Exception as e:
        print(f"Error loading startup font settings: {e}")

    AppTheme.apply(app, mode)
