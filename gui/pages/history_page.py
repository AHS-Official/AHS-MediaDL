"""
History Page — Displays log of all past downloads as clickable cards.
"""
import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from gui.widgets import HistoryCard
from utils import helpers


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 24, 20, 20)
        self.main_layout.setSpacing(15)
        
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        
        # Header Row
        header_layout = QHBoxLayout()
        
        self.header_title = QFrame()
        self.header_title.setObjectName("HeaderTitleFrame")
        self.header_title_layout = QHBoxLayout(self.header_title)
        self.header_title_layout.setContentsMargins(0, 0, 0, 0)
        self.header_title_layout.setSpacing(8)
        
        self.header_icon_lbl = QLabel()
        self.header_icon_lbl.setPixmap(helpers.get_theme_icon("history.svg", 24).pixmap(24, 24))
        text_lbl = QLabel(helpers.HISTORY_TITLE)
        text_lbl.setObjectName("heading")
        text_lbl.setStyleSheet("font-size: 14pt; font-weight: 700;")
        
        self.header_title_layout.addWidget(self.header_icon_lbl)
        self.header_title_layout.addWidget(text_lbl)
        header_layout.addWidget(self.header_title)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("  " + helpers.HISTORY_CLEAR)
        self.clear_btn.setIcon(helpers.get_theme_icon("broom.svg"))
        self.clear_btn.setObjectName("danger")
        self.clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_btn)
        
        self.main_layout.addLayout(header_layout)
        
        # Scrolling area for list of Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        
        self.scroll_area.setWidget(self.list_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # Load history data on creation
        self.reload_history()

    def reload_history(self):
        # Clear current list
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        history_file = os.path.join("data", "history.json")
        if not os.path.exists(history_file):
            self.show_placeholder()
            return
            
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            self.show_placeholder()
            return
            
        if not history:
            self.show_placeholder()
            return
            
        self.clear_btn.setVisible(True)
        # Add history cards to layout (most recent first)
        for i, item in enumerate(history):
            card = HistoryCard(
                title=item.get("title", "Unknown"),
                date=item.get("date", "N/A"),
                url=item.get("url", ""),
                media_type=item.get("media_type", "video")
            )
            # Insert before the stretch spacer
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            
            # Insert simple visual separator (except after the very last card)
            if i < len(history) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); max-height: 1px; margin: 4px 10px;")
                self.list_layout.insertWidget(self.list_layout.count() - 1, line)

    def show_placeholder(self):
        self.clear_btn.setVisible(False)
        ph_card = QFrame()
        ph_card.setObjectName("GlowCard")
        ph_card.setMinimumHeight(200)
        ph_layout = QVBoxLayout(ph_card)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(helpers.get_theme_icon("folder-open.svg", 48).pixmap(48, 48))
        icon_lbl.setStyleSheet("margin-bottom: 8px;")
        
        lbl = QLabel(helpers.HISTORY_EMPTY)
        lbl.setObjectName("heading")
        lbl.setStyleSheet("font-size: 14pt; font-weight: 700; color: #a0a0c0;")
        
        lbl_sub = QLabel(helpers.HISTORY_EMPTY_SUB)
        lbl_sub.setObjectName("hint")
        lbl_sub.setStyleSheet("font-size: 11pt;")
        
        ph_layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(lbl_sub, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.list_layout.insertWidget(0, ph_card)

    def clear_history(self):
        history_file = os.path.join("data", "history.json")
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
            except Exception:
                pass
        self.reload_history()

    def refresh_theme_icons(self):
        self.header_icon_lbl.setPixmap(helpers.get_theme_icon("history.svg", 24).pixmap(24, 24))
        self.clear_btn.setIcon(helpers.get_theme_icon("broom.svg"))
        self.reload_history()


def add_to_history(title, url, media_type="video"):
    """Core function to append items to history log."""
    from datetime import datetime
    history_file = os.path.join("data", "history.json")
    os.makedirs("data", exist_ok=True)
    
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []
            
    item = {
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "url": url,
        "media_type": media_type
    }
    
    # Prepend to show most recent first
    history.insert(0, item)
    
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
    except Exception:
        pass
