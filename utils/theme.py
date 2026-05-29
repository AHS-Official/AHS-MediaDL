"""
╔══════════════════════════════════════════════════════════════╗
║           AHS-MediaDL — Dynamic Design System                ║
║      Generates QSS dynamically with Font & Mode injection     ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

DARK = {
    "bg_base":          "#0b0f19",                                              
    "bg_card":          "#131926",                                       
    "bg_input":         "#1a2035",                                        
    "bg_selected":      "#24304f",                          
    "text_selected":    "#ffffff",                             
    "text_primary":     "#f1f5f9",                                      
    "text_secondary":   "#94a3b8",                                  
    "border":           "#1e293b",                                  
    "border_focus":     "#3b82f6",                                      
    "accent":           "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed)",                  
    "accent_hover":     "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6)",
    "accent_pressed":   "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9)",
    "scrollbar_handle": "#1e293b",
    "scrollbar_hover":  "#334155"
}

LIGHT = {
    "bg_base":          "#f8fafc",                                           
    "bg_card":          "#ffffff",                                               
    "bg_input":         "#ffffff",                           
    "bg_selected":      "#f1f5f9",                          
    "text_selected":    "#0f172a",                             
    "text_primary":     "#0f172a",                                      
    "text_secondary":   "#64748b",                                   
    "border":           "#e2e8f0",                          
    "border_focus":     "#3b82f6",                     
    "accent":           "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5)",                     
    "accent_hover":     "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #6366f1)",
    "accent_pressed":   "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #4338ca)",
    "scrollbar_handle": "#cbd5e1",
    "scrollbar_hover":  "#94a3b8"
}

def get_style_sheet(theme_mode, font_family="System Default", font_size=12, is_rtl=False):
    if theme_mode == "auto":
        scheme = QGuiApplication.styleHints().colorScheme()
        theme_mode = "dark" if scheme == Qt.ColorScheme.Dark else "light"
    c = DARK if theme_mode == "dark" else LIGHT
    font_css = f"font-size: {font_size}pt;"
    if font_family != "System Default":
        font_css += f" font-family: '{font_family}';"
    sidebar_border = "border-left" if is_rtl else "border-right"
    sidebar_no_border = "border-right" if is_rtl else "border-left"
    btn_checked_border = "border-right" if is_rtl else "border-left"
    btn_unchecked_border = "border-left" if is_rtl else "border-right"
    sidebar_align = "left"
    return f"""
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

    DownloadCard, HistoryCard, QFrame#MediaInfoCard, QFrame#DownloadSettingsCard, QFrame#GroupBox {{ 
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin: 6px 2px;
    }} 
    DownloadCard:hover, HistoryCard:hover, QFrame#MediaInfoCard:hover, QFrame#DownloadSettingsCard:hover {{ 
        border: 1px solid {c['border_focus']};
    }} 

    QFrame#NotifPopup, QFrame#DlPopup {{ 
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }} 
    QFrame#NotifPopup QLabel, QFrame#DlPopup QLabel {{ 
        background-color: transparent;
        color: {c['text_primary']};
    }} 
    QFrame#NotifPopup QLabel#NotifMessage {{ 
        color: {c['text_secondary']};
    }} 

    QToolTip {{ 
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {"#334155" if theme_mode == "dark" else "#cbd5e1"};
        border-radius: 6px;
        padding: 4px 8px;
    }} 

    DownloadCard QLabel, HistoryCard QLabel, QFrame#MediaInfoCard QLabel, QFrame#DownloadSettingsCard QLabel {{ 
        background-color: transparent;
    }} 

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
    QWidget#Sidebar QPushButton#btn_menu, QWidget#Sidebar QPushButton:checked#btn_menu {{ 
        background-color: transparent;
        border: none;
        text-align: center;
    }} 

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

    QSplitter::handle {{ 
        background-color: {c['border']};
    }} 
    QSplitter::handle:horizontal {{ 
        width: 4px;
    }} 
    QSplitter::handle:hover {{ 
        background-color: {c['border_focus']};
    }} 
    """
