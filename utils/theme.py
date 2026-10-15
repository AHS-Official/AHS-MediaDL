"""
╔══════════════════════════════════════════════════════════════╗
║           AHS-MediaDL — Dynamic Design System                ║
║      Generates QSS dynamically with Font & Mode injection     ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

ACCENTS = {
    "orange": {
        "accent": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5e3a, stop:1 #ff2a5f)",
        "accent_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff7e5a, stop:1 #ff4a7f)",
        "accent_pressed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e04a2a, stop:1 #e01a4f)",
        "accent_hex": "#ff5e3a",
        "accent_hover_hex": "#ff7e5a",
        "glow_color": "rgba(255, 94, 58, 0.35)",
        "badge_bg_dark": "rgba(255, 94, 58, 0.08)",
        "badge_border_dark": "rgba(255, 94, 58, 0.15)",
        "badge_bg_light": "rgba(255, 94, 58, 0.06)",
        "badge_border_light": "rgba(255, 94, 58, 0.12)"
    },
    "blue": {
        "accent": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #1d4ed8)",
        "accent_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6)",
        "accent_pressed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #1e3a8a)",
        "accent_hex": "#3b82f6",
        "accent_hover_hex": "#60a5fa",
        "glow_color": "rgba(59, 130, 246, 0.40)",
        "badge_bg_dark": "rgba(59, 130, 246, 0.10)",
        "badge_border_dark": "rgba(59, 130, 246, 0.20)",
        "badge_bg_light": "rgba(59, 130, 246, 0.08)",
        "badge_border_light": "rgba(59, 130, 246, 0.16)"
    },
    "purple": {
        "accent": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #6d28d9)",
        "accent_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a78bfa, stop:1 #8b5cf6)",
        "accent_pressed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6d28d9, stop:1 #4c1d95)",
        "accent_hex": "#8b5cf6",
        "accent_hover_hex": "#a78bfa",
        "glow_color": "rgba(139, 92, 246, 0.35)",
        "badge_bg_dark": "rgba(139, 92, 246, 0.08)",
        "badge_border_dark": "rgba(139, 92, 246, 0.15)",
        "badge_bg_light": "rgba(139, 92, 246, 0.06)",
        "badge_border_light": "rgba(139, 92, 246, 0.12)"
    },
    "green": {
        "accent": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #047857)",
        "accent_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981)",
        "accent_pressed": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #064e3b)",
        "accent_hex": "#10b981",
        "accent_hover_hex": "#34d399",
        "glow_color": "rgba(16, 185, 129, 0.35)",
        "badge_bg_dark": "rgba(16, 185, 129, 0.08)",
        "badge_border_dark": "rgba(16, 185, 129, 0.15)",
        "badge_bg_light": "rgba(16, 185, 129, 0.06)",
        "badge_border_light": "rgba(16, 185, 129, 0.12)"
    }
}

# ── Dark palette (Dark Slate base - Minimal macOS Style) ─────────
DARK = {
    "bg_base":          "#0f172a",
    "bg_card":          "#1e293b",
    "bg_input":         "#0f172a",
    "bg_selected":      "#334155",
    "text_selected":    "#ffffff",
    "text_primary":     "#f8fafc",
    "text_secondary":   "#94a3b8",
    "border":           "#334155",
    "border_focus":     "#3b82f6",
    "accent":           ACCENTS["blue"]["accent"],
    "accent_hover":     ACCENTS["blue"]["accent_hover"],
    "accent_pressed":   ACCENTS["blue"]["accent_pressed"],
    "accent_hex":       ACCENTS["blue"]["accent_hex"],
    "glow_color":       ACCENTS["blue"]["glow_color"],
    "scrollbar_handle": "#334155",
    "scrollbar_hover":  "#475569",
    "empty_state_badge_bg": ACCENTS["blue"]["badge_bg_dark"],
    "empty_state_badge_border": ACCENTS["blue"]["badge_border_dark"]
}

# ── Light palette (Soft macOS & GNOME Style - Eyestrain-Free) ────
LIGHT = {
    "bg_base":          "#e2e8f0",  # خلفية رمادية ناعمة تمنع التوهج وإجهاد العين
    "bg_card":          "#ffffff",  # بطاقات بيضاء هادئة
    "bg_input":         "#f8fafc",  # حقول إدخال مريحة وبسيطة
    "bg_selected":      "#dbeafe",  # تحديد أزرق ثلجي ناعم
    "text_selected":    "#1e40af",  # نصوص محددة بكحلي أنيق
    "text_primary":     "#1e293b",  # نصوص داكنة مريحة للقراءة بدلاً من الأسود الحاد
    "text_secondary":   "#64748b",  # نصوص فرعية هادئة
    "border":           "#cbd5e1",  # حدود ناعمة ومحددة
    "border_focus":     "#2563eb",  # لون تركيز مريح
    "accent":           ACCENTS["blue"]["accent"],
    "accent_hover":     ACCENTS["blue"]["accent_hover"],
    "accent_pressed":   ACCENTS["blue"]["accent_pressed"],
    "accent_hex":       ACCENTS["blue"]["accent_hex"],
    "glow_color":       ACCENTS["blue"]["glow_color"],
    "scrollbar_handle": "#cbd5e1",
    "scrollbar_hover":  "#94a3b8",
    "empty_state_badge_bg": ACCENTS["blue"]["badge_bg_light"],
    "empty_state_badge_border": ACCENTS["blue"]["badge_border_light"]
}

def load_accent_theme():
    try:
        from managers.settings_manager import SettingsManager
        return SettingsManager().get("accent_theme", "orange")
    except Exception:
        return "orange"

def get_accent_hex():
    accent_name = load_accent_theme()
    return ACCENTS.get(accent_name, ACCENTS["blue"])["accent_hex"]

def get_accent_hover_hex():
    accent_name = load_accent_theme()
    return ACCENTS.get(accent_name, ACCENTS["blue"])["accent_hover_hex"]

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def get_style_sheet(theme_mode, font_family="System Default", font_size=12, is_rtl=False):
    if theme_mode == "auto":
        from utils.helpers import detect_system_theme
        theme_mode = detect_system_theme()

    accent_name = load_accent_theme()
    acc = ACCENTS.get(accent_name, ACCENTS["blue"])

    # Inject dynamic accent colors
    if theme_mode == "dark":
        DARK["accent"]           = acc["accent"]
        DARK["accent_hover"]     = acc["accent_hover"]
        DARK["accent_pressed"]   = acc["accent_pressed"]
        DARK["accent_hex"]       = acc["accent_hex"]
        DARK["glow_color"]       = acc["glow_color"]
        DARK["empty_state_badge_bg"]     = acc["badge_bg_dark"]
        DARK["empty_state_badge_border"] = acc["badge_border_dark"]
        c = DARK
    else:
        LIGHT["accent"]           = acc["accent"]
        LIGHT["accent_hover"]     = acc["accent_hover"]
        LIGHT["accent_pressed"]   = acc["accent_pressed"]
        LIGHT["accent_hex"]       = acc["accent_hex"]
        LIGHT["glow_color"]       = acc["glow_color"]
        LIGHT["empty_state_badge_bg"]     = acc["badge_bg_light"]
        LIGHT["empty_state_badge_border"] = acc["badge_border_light"]
        c = LIGHT

    font_css = f"font-size: {font_size}pt;"
    if font_family != "System Default":
        font_css += f" font-family: '{font_family}';"

    sidebar_border     = "border-left"  if is_rtl else "border-right"
    sidebar_no_border  = "border-right" if is_rtl else "border-left"
    btn_checked_border = "border-right" if is_rtl else "border-left"
    btn_unchecked_border = "border-left" if is_rtl else "border-right"
    sidebar_align = "left"

    # ── card shadow/glow for dark vs light ──
    if theme_mode == "dark":
        card_shadow = f"rgba(0, 0, 0, 0.55)"
        card_hover_border = acc["accent_hex"]
    else:
        card_shadow = f"rgba(0, 0, 0, 0.08)"
        card_hover_border = acc["accent_hex"]

    return f"""
    /* ═══════════════════════════════════════════
       BASE
    ═══════════════════════════════════════════ */
    QWidget {{
        background-color: {c['bg_base']};
        color: {c['text_primary']};
        {font_css}
        border: none;
        outline: none;
    }}

    QLabel, QCheckBox, QRadioButton, QGroupBox {{
        background-color: transparent;
    }}

    QMainWindow, QDialog {{
        background-color: {c['bg_base']};
    }}

    /* ═══════════════════════════════════════════
       INPUTS
    ═══════════════════════════════════════════ */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1.5px solid {c['border']};
        border-radius: 10px;
        padding: 7px 14px;
        font-weight: 500;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1.5px solid {c['border_focus']};
    }}

    QLineEdit QToolButton {{
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='{c['text_secondary'].replace('#', '%23')}'><path d='M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z'/></svg>");
        background: transparent;
        border: none;
        width: 16px;
        height: 16px;
        padding: 0px;
        margin-right: 4px;
        margin-left: 4px;
    }}
    QLineEdit QToolButton:hover {{
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='{c['text_primary'].replace('#', '%23')}'><path d='M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z'/></svg>");
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        border: 1.5px solid {c['border']};
        border-radius: 10px;
        selection-background-color: {c['bg_selected']};
        selection-color: {c['text_selected']};
        padding: 4px;
        outline: none;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}

    /* ═══════════════════════════════════════════
       LIST WIDGET
    ═══════════════════════════════════════════ */
    QListWidget {{
        background-color: transparent;
        {sidebar_border}: 1.5px solid {c['border']};
        {sidebar_no_border}: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 4px;
        color: {c['text_primary']};
    }}
    QListWidget::item:hover {{
        background-color: {c['bg_input']};
    }}
    QListWidget::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_selected']};
        font-weight: bold;
    }}
    QListWidget::item:selected:hover {{
        background-color: {c['bg_selected']};
    }}

    /* ═══════════════════════════════════════════
       CARDS
    ═══════════════════════════════════════════ */
    DownloadCard, HistoryCard, QFrame#MediaInfoCard, QFrame#DownloadSettingsCard, QFrame#GroupBox {{
        background-color: {c['bg_card']};
        border: 1.5px solid {c['border']};
        border-radius: 14px;
        margin: 5px 2px;
        padding: 4px;
    }}
    DownloadCard:hover, HistoryCard:hover, QFrame#MediaInfoCard:hover, QFrame#DownloadSettingsCard:hover {{
        border: 1.5px solid rgba(59, 130, 246, 0.5);
    }}

    /* ═══════════════════════════════════════════
       POPUPS
    ═══════════════════════════════════════════ */
    QFrame#NotifPopup, QFrame#DlPopup {{
        background-color: {c['bg_card']};
        border: 1.5px solid {c['border']};
        border-radius: 14px;
    }}
    QFrame#NotifPopup QLabel, QFrame#DlPopup QLabel {{
        background-color: transparent;
        color: {c['text_primary']};
    }}
    QFrame#NotifPopup QLabel#NotifMessage {{
        color: {c['text_secondary']};
    }}

    /* ═══════════════════════════════════════════
       TOOLTIP
    ═══════════════════════════════════════════ */
    QToolTip {{
        background-color: #1e2d45;
        color: #e2e8f0;
        border: 1px solid #2d4266;
        border-radius: 8px;
        padding: 5px 10px;
        font-weight: 500;
    }}

    /* ═══════════════════════════════════════════
       CARD LABELS
    ═══════════════════════════════════════════ */
    DownloadCard QLabel, HistoryCard QLabel, QFrame#MediaInfoCard QLabel, QFrame#DownloadSettingsCard QLabel {{
        background-color: transparent;
    }}

    /* ═══════════════════════════════════════════
       BUTTONS — PRIMARY
    ═══════════════════════════════════════════ */
    QPushButton {{
        background-color: {c['accent']};
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
        font-size: {font_size + 1}pt;
    }}
    QPushButton:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent_pressed']};
    }}
    QPushButton:disabled {{
        background-color: {c['border']};
        color: {c['text_secondary']};
    }}

    /* Speed unit button */
    QPushButton#btn_speed_unit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1.5px solid {c['border']};
        border-radius: 8px;
        padding: 4px 8px;
        font-weight: 600;
    }}
    QPushButton#btn_speed_unit:hover {{
        background-color: {c['bg_selected']};
        border-color: {c['border_focus']};
    }}

    /* ═══════════════════════════════════════════
       SIDEBAR (Icon-only, 60px)
    ═══════════════════════════════════════════ */
    QWidget#Sidebar {{
        background-color: {c['bg_card']};
        {sidebar_border}: 1px solid {c['border']};
        {sidebar_no_border}: none;
    }}
    QWidget#Sidebar QWidget {{
        background: transparent;
        border: none;
    }}

    QWidget#Sidebar QPushButton {{
        background-color: transparent;
        color: {c['text_secondary']};
        border-radius: 12px;
        border: none;
        padding: 10px;
        text-align: {sidebar_align};
        font-weight: 500;
    }}
    QWidget#Sidebar QPushButton:hover {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
    }}
    QWidget#Sidebar QPushButton:checked {{
        background-color: {c['bg_selected']};
        color: {c['accent_hex']};
        font-weight: 700;
        {btn_checked_border}: 3px solid {c['accent_hex']};
        {btn_unchecked_border}: none;
    }}
    QWidget#Sidebar QPushButton#btn_menu,
    QWidget#Sidebar QPushButton:checked#btn_menu {{
        background-color: transparent;
        border: none;
        color: {c['text_secondary']};
        text-align: center;
    }}

    /* ═══════════════════════════════════════════
       PROGRESS BAR
    ═══════════════════════════════════════════ */
    QProgressBar {{
        background-color: {c['bg_input']};
        color: transparent;
        border: none;
        border-radius: 5px;
        text-align: center;
        height: 8px;
        max-height: 8px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #60a5fa);
        border-radius: 5px;
    }}

    /* Status labels in download cards */
    QLabel#StatusLabelDone {{
        color: #34d399;
        font-weight: 600;
    }}
    QLabel#StatusLabelError {{
        color: #f87171;
        font-weight: 600;
    }}
    QLabel#StatusLabelActive {{
        color: {c['accent_hex']};
        font-weight: 600;
    }}

    /* ═══════════════════════════════════════════
       CHECKBOX
    ═══════════════════════════════════════════ */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
        font-weight: 500;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1.5px solid {c['border']};
        border-radius: 5px;
        background-color: {c['bg_input']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['border_focus']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent_hex']};
        border-color: {c['accent_hex']};
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><path d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/></svg>");
    }}

    /* ═══════════════════════════════════════════
       SCROLLBAR
    ═══════════════════════════════════════════ */

    QSlider {{
        background: transparent;
    }}
    QSlider::groove:horizontal {{
        border: 1px solid {c['border']};
        height: 6px;
        background: {c['bg_input']};
        margin: 2px 0;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent_hex']};
        border: 2px solid {c['bg_card']};
        width: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['text_primary']};
    }}
    QSlider::sub-page:horizontal {{
        background: {c['accent_hex']};
        border-radius: 3px;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar_handle']};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: transparent;
        height: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar_handle']};
        border-radius: 3px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
        width: 0px;
    }}

    /* ═══════════════════════════════════════════
       SPLITTER
    ═══════════════════════════════════════════ */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 3px;
    }}
    QSplitter::handle:hover {{
        background-color: {c['border_focus']};
    }}

    /* ═══════════════════════════════════════════
       EMPTY STATE
    ═══════════════════════════════════════════ */
    QFrame#EmptyStateContainer {{
        background-color: transparent;
        border: none;
        min-width: 380px;
        max-width: 480px;
    }}
    QFrame#EmptyStateContainer QLabel {{
        color: {c['text_secondary']};
    }}
    QLabel#EmptyStateIcon {{
        background-color: {c['empty_state_badge_bg']};
        border: 1px solid {c['empty_state_badge_border']};
        border-radius: 48px;
    }}"""

class ThemeManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def get_theme_mode(self):
        return self.settings.get("theme", "auto")

    def get_actual_theme(self):
        theme = self.get_theme_mode()
        if theme == "auto":
            from utils.helpers import detect_system_theme
            return detect_system_theme()
        return theme

    def get_theme_color(self):
        actual = self.get_actual_theme()
        return "#f1f5f9" if actual == "dark" else "#0f172a"

    def get_accent_theme_name(self):
        return self.settings.get("accent_theme", "orange")

    def get_accent_hex(self):
        name = self.get_accent_theme_name()
        return ACCENTS.get(name, ACCENTS["orange"])["accent_hex"]

    def get_accent_hover_hex(self):
        name = self.get_accent_theme_name()
        return ACCENTS.get(name, ACCENTS["orange"])["accent_hover_hex"]

    def get_style(self, font_family="System Default", font_size=12, is_rtl=False):
        theme = self.get_theme_mode()
        return get_style_sheet(theme, font_family, font_size, is_rtl)
