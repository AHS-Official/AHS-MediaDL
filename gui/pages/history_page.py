import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QMessageBox, QLabel
from PyQt6.QtCore import Qt, QSize
from gui.widgets import HistoryCard
from utils.locales import tr
from utils.helpers import get_colored_icon, get_current_theme_color

class HistoryPage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        # تحديد مسار ملف السجل داخل مجلد data
        self.history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'history.json')
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # شاشة الانتظار (Empty State) لصفحة السجل
        from gui.widgets import EmptyStateWidget
        self.empty_state_widget = EmptyStateWidget(
            "assets/icons/inbox.svg",
            tr("empty_history_title", "No Download History"),
            tr("empty_history_sub", "Completed downloads will be recorded here."),
            self
        )
        main_layout.addWidget(self.empty_state_widget)
        
        # شريط التمرير (Scrollbar)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(8)
        
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)
        
        # الزر الثابت بالأسفل لمسح السجل بالكامل
        bottom_layout = QHBoxLayout()
        self.btn_clear_history = QPushButton(tr("btn_clear_history"))
        self.btn_clear_history.setFixedHeight(35)
        self.btn_clear_history.clicked.connect(self.clear_history)
        
        bottom_layout.addWidget(self.btn_clear_history)
        main_layout.addLayout(bottom_layout)
        
        # تحميل البيانات وعرضها فور فتح الصفحة
        self.load_history_ui()
        
    def load_history_ui(self):
        # تنظيف الواجهة الحالية أولاً لتجنب التكرار
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        has_items = False
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    if history_data:
                        has_items = True
                        # عرض التنزيلات الجديدة في الأعلى (Reversed)
                        for item in reversed(history_data):
                            card = HistoryCard(
                                title=item.get('title', tr("unknown_title")),
                                url=item.get('url', ''),
                                media_type=item.get('type', 'video'),
                                date_str=item.get('date', '')
                            )
                            self.cards_layout.addWidget(card)
            except Exception:
                pass
                
        # إظهار/إخفاء شاشة الانتظار وزر المسح ومنطقة السجل
        self.empty_state_widget.setVisible(not has_items)
        self.scroll_area.setVisible(has_items)
        self.btn_clear_history.setVisible(has_items)
                
    def add_to_history(self, title, duration, size, url, media_type):
        history_data = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
            except Exception:
                pass
                
        from datetime import datetime
        new_entry = {
            "title": title,
            "duration": duration,
            "size": size,
            "url": url,
            "type": media_type,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        history_data.append(new_entry)
        
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
            
        self.load_history_ui()
        
    def clear_history(self):
        if self.cards_layout.count() == 0:
            return
            
        reply = QMessageBox.question(self, tr("confirm_title"), tr("confirm_clear_history_msg"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if os.path.exists(self.history_file):
                try:
                    os.remove(self.history_file)
                except Exception:
                    pass
            self.load_history_ui()

    def update_icon_colors(self, icon_color):
        self.empty_state_widget.update_icon_color("assets/icons/inbox.svg", icon_color)