import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                             QHeaderView, QPushButton, QTableWidgetItem, QMessageBox)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from utils import strings
from utils.helpers import get_app_dir
from gui.theme import styled

class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        # إنشاء الجدول
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([strings.COL_THUMB, strings.COL_TITLE, strings.COL_DATE, strings.COL_ACTION])
        self.history_table.setColumnWidth(0, 90)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_table)
        
        # زر مسح السجل
        self.clear_history_btn = styled.danger_button(strings.BTN_CLEAR_HISTORY)
        self.clear_history_btn.clicked.connect(self.clear_all_history)
        layout.addWidget(self.clear_history_btn)

    def load_history(self):
        history_file = os.path.join(get_app_dir(), "history.json")
        if not os.path.exists(history_file):
            self.history_table.setRowCount(0)
            return
        
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
            
        self.history_table.setRowCount(len(data))
        for i, entry in enumerate(data):
            self.history_table.setRowHeight(i, 55)
            
            # Thumbnail column
            thumb_path = entry.get('thumb_path', '')
            if thumb_path and os.path.exists(thumb_path):
                try:
                    from PyQt6.QtGui import QPixmap
                    from PyQt6.QtWidgets import QLabel
                    from PyQt6.QtCore import Qt
                    pixmap = QPixmap(thumb_path)
                    if not pixmap.isNull():
                        img_label = QLabel()
                        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        img_label.setPixmap(pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        self.history_table.setCellWidget(i, 0, img_label)
                except Exception as ex:
                    print(f"Error rendering thumbnail: {ex}")
            
            self.history_table.setItem(i, 1, QTableWidgetItem(entry.get('title', 'Unknown')))
            self.history_table.setItem(i, 2, QTableWidgetItem(entry.get('date', '')))
            
            btn = styled.ghost_button("📂")
            btn.setToolTip(strings.BTN_OPEN_FOLDER)
            btn.clicked.connect(lambda ch, p=entry.get('path', ''): QDesktopServices.openUrl(QUrl.fromLocalFile(p)) if p else None)
            self.history_table.setCellWidget(i, 3, btn)

    def clear_all_history(self):
        history_file = os.path.join(get_app_dir(), "history.json")
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
            except OSError:
                pass
            # Clean up cached thumbnails too
            cache_dir = os.path.join(get_app_dir(), "cache", "thumbnails")
            if os.path.exists(cache_dir):
                import shutil
                try:
                    shutil.rmtree(cache_dir)
                except OSError:
                    pass
            self.history_table.setRowCount(0)
            QMessageBox.information(self, "Success" if not strings.is_ar else "نجاح", strings.MSG_HISTORY_CLEARED)
