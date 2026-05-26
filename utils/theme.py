"""
╔══════════════════════════════════════════════════════════════╗
║           AHS-MediaDL — Dynamic Design System                ║
║      Generates QSS dynamically with Font & Mode injection     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

# 🎨 لوحة ألوان الوضع الداكن الاحترافي (Cyber Midnight Mode)
DARK = {
    "bg_base":          "#0b0f19",       # خلفية التطبيق الكلية (أزرق ليلي عميق)
    "bg_card":          "#131926",       # خلفية الكروت واللوحات المرفوعة
    "bg_input":         "#1a2035",       # خلفية حقول الإدخال والكومبوبوكس
    "bg_selected":      "#24304f",       # لون تحديد القوائم
    "text_selected":    "#ffffff",       # لون الخط عند التحديد
    "text_primary":     "#f1f5f9",       # الخط الأساسي (سليت فاتح جداً)
    "text_secondary":   "#94a3b8",       # الخط الثانوي (رمادي هادئ)
    "border":           "#1e293b",       # الحدود الافتراضية الهادئة
    "border_focus":     "#3b82f6",       # حدود التركيز (أزرق نيون هادئ)
    
    # تدرجات الأزرار الملونة الفاخرة
    "accent":           "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed)", # أزرق إلى بنفسجي
    "accent_hover":     "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6)",
    "accent_pressed":   "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9)",
    
    "scrollbar_handle": "#1e293b",
    "scrollbar_hover":  "#334155"
}

# ☀️ لوحة ألوان الوضع الفاتح الاحترافي (Premium Slate Light Mode)
LIGHT = {
    "bg_base":          "#f8fafc",       # خلفية فاتحة باردة وهادئة (سليت 50)
    "bg_card":          "#ffffff",       # خلفية الكروت (أبيض ناصع مع تباين رائع)
    "bg_input":         "#ffffff",       # خلفية حقول الإدخال
    "bg_selected":      "#f1f5f9",       # لون تحديد القوائم
    "text_selected":    "#0f172a",       # لون الخط عند التحديد
    "text_primary":     "#0f172a",       # الخط الأساسي (سليت غامق جداً)
    "text_secondary":   "#64748b",       # الخط الثانوي (رمادي معتدل)
    "border":           "#e2e8f0",       # الحدود الافتراضية
    "border_focus":     "#3b82f6",       # حدود التركيز
    
    # تدرجات الأزرار الملونة الفاتحة
    "accent":           "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5)", # أزرق ملكي إلى نيلي
    "accent_hover":     "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #6366f1)",
    "accent_pressed":   "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #4338ca)",
    
    "scrollbar_handle": "#cbd5e1",
    "scrollbar_hover":  "#94a3b8"
}

def get_style_sheet(theme_mode, font_family="System Default", font_size=12, is_rtl=False):
    """
    دالة توليد كود الـ QSS ديناميكياً.
    تقوم بحقن نوع الخط، الحجم، ولون المود المختار، مع مراعاة اتجاه الكتابة RTL/LTR.
    """
    # 1. معالجة وضع النظام التلقائي (Auto)
    if theme_mode == "auto":
        scheme = QGuiApplication.styleHints().colorScheme()
        theme_mode = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        
    # اختيار لوحة الألوان بناءً على المود الفعلي
    c = DARK if theme_mode == "dark" else LIGHT
    
    # 2. بناء سطر الخط والحجم ديناميكياً ليفرش على كل الوجت
    font_css = f"font-size: {font_size}pt;"
    if font_family != "System Default":
        font_css += f" font-family: '{font_family}';"

    # 3. إعداد خطوط محاذاة شريط التنقل بناء على الاتجاه
    sidebar_border = "border-left" if is_rtl else "border-right"
    sidebar_no_border = "border-right" if is_rtl else "border-left"
    
    btn_checked_border = "border-right" if is_rtl else "border-left"
    btn_unchecked_border = "border-left" if is_rtl else "border-right"
    
    # ملحوظة: في محرك Qt، يتم عكس محاذاة النص تلقائياً بناءً على اتجاه الواجهة (RTL).
    # ولذلك، فإن استخدام "left" سيحاذي العناصر لليسار في الإنجليزية ولليمين في العربية تلقائياً.
    sidebar_align = "left"

    # 4. إرجاع نص الـ QSS المولد بالكامل
    return f"""
    QWidget {{
        background-color: {c['bg_base']};
        color: {c['text_primary']};
        {font_css}
        border: none;
        outline: none;
    }}

    QMainWindow, QDialog {{ 
        background-color: {c['bg_base']}; 
    }}

    /* 🛡️ تنسيق الحقول والقوائم المنسدلة بتأثير التركيز المضاد للتوهج */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 6px 12px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ 
        border: 1px solid {c['border_focus']}; 
    }}

    /* 🔍 زر مسح النص داخل حقول الإدخال */
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


    /* 🎨 تنسيق قائمة الكومبوبوكس المنسدلة - القائمة الداخلية */
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        selection-background-color: {c['bg_selected']};
        selection-color: {c['text_selected']};
        padding: 4px;
        outline: none;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    
    /* 📋 القائمة الجانبية لإعدادات التبويبات */
    QListWidget {{
        background-color: transparent;
        {sidebar_border}: 1px solid {c['border']};
        {sidebar_no_border}: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 4px;
        color: {c['text_primary']};
    }}
    QListWidget::item:selected {{
        background-color: {c['bg_selected']};
        color: {c['text_selected']};
        font-weight: bold;
    }}
    QListWidget::item:hover {{
        background-color: {c['bg_input']};
    }}

    /* 💎 تصميم كروت التنزيل والسجل (Glassmorphism Cards) */
    DownloadCard, HistoryCard, QFrame#MediaInfoCard, QFrame#DownloadSettingsCard {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin: 6px 2px;
    }}
    DownloadCard:hover, HistoryCard:hover, QFrame#MediaInfoCard:hover, QFrame#DownloadSettingsCard:hover {{
        border: 1px solid {c['border_focus']};
    }}

    /* 🛠️ تنسيق عناصر التفاصيل داخل الكروت لتجنب وراثة خلفية الكارت بالكامل */
    DownloadCard QLabel, HistoryCard QLabel, QFrame#MediaInfoCard QLabel, QFrame#DownloadSettingsCard QLabel {{
        background-color: transparent;
    }}

    /* 🔵 نظام أزرار الأكشن الرئيسية الفاخرة (Gradients) 🔵 */
    QPushButton {{
        background-color: {c['accent']};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 7px 16px;
        font-weight: bold;
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

    /* 🏷️ زرار وحدة السرعة المخصص داخل الإعدادات */
    QPushButton#btn_speed_unit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
        font-weight: bold;
    }}
    QPushButton#btn_speed_unit:hover {{
        background-color: {c['bg_selected']};
        border-color: {c['border_focus']};
    }}

    QWidget#Sidebar {{
        background-color: {c['bg_card']};
        {sidebar_border}: 1px solid {c['border']};
        {sidebar_no_border}: none;
    }}

    /* 🧭 تخصيص أزرار شريط التنقل الجانبي (Sidebar Navigation Buttons) */
    QWidget#Sidebar QPushButton {{
        background-color: transparent;
        color: {c['text_primary']};
        border-radius: 8px;
        border: none;
        padding: 10px 14px;
        text-align: {sidebar_align};
    }}
    QWidget#Sidebar QPushButton:hover {{
        background-color: {c['bg_input']};
    }}
    QWidget#Sidebar QPushButton:checked {{
        background-color: {c['bg_selected']};
        color: {c['text_selected']};
        font-weight: bold;
        {btn_checked_border}: 4px solid #3b82f6;
        {btn_unchecked_border}: none;
    }}
    /* زر الهامبرغر الصغير في شريط التنقل */
    QWidget#Sidebar QPushButton#btn_menu, QWidget#Sidebar QPushButton:checked#btn_menu {{
        background-color: transparent;
        border: none;
        text-align: center;
    }}

    /* 📊 شريط التحميل المخصص والمحاذاة الرائعة (Progress Bar) */
    QProgressBar {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: none;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        height: 16px;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 6px;
    }}

    /* ⚡️ تنسيق خانة الاختيار (QCheckBox) */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {c['border']};
        border-radius: 4px;
        background-color: {c['bg_input']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['border_focus']};
    }}
    QCheckBox::indicator:checked {{
        background-color: #3b82f6;
        border-color: #3b82f6;
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><path d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/></svg>");
    }}

    /* 📜 شريط التمرير الأنيق (Scrollbar) */
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar_handle']};
        border-radius: 4px;
        min-height: 25px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}
    """