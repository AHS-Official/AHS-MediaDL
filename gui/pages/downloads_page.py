from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QLabel
from PyQt6.QtCore import Qt, QSize
from gui.widgets import DownloadCard
from utils.locales import tr
from utils.helpers import get_colored_icon, get_current_theme_color

class DownloadsPage(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.initUI()
        
    def initUI(self):
        queue_layout = QVBoxLayout(self)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        
        # شاشة الانتظار (Empty State) لصفحة التنزيلات
        from gui.widgets import EmptyStateWidget
        self.empty_state_widget = EmptyStateWidget(
            "assets/icons/download.svg",
            tr("empty_downloads_title", "No Active Downloads"),
            tr("empty_downloads_sub", "Your active downloads will appear here."),
            self
        )
        queue_layout.addWidget(self.empty_state_widget)
        
        # منطقة التمرير لكروت التحميل
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }") 
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop) 
        
        self.scroll_area.setWidget(self.cards_container)
        queue_layout.addWidget(self.scroll_area)

        global_controls_layout = QHBoxLayout()
        
        self.btn_pause_all = QPushButton(tr("btn_pause_all"))
        self.btn_pause_all.setToolTip("Pause or Resume all active downloads")
        
        self.btn_cancel_all = QPushButton(tr("btn_cancel_all"))
        self.btn_cancel_all.setToolTip("Cancel all active downloads")
        
        self.btn_clear_all = QPushButton(tr("btn_clear"))
        self.btn_clear_all.setToolTip("Remove finished or canceled items from the list")

        global_controls_layout.addWidget(self.btn_clear_all)
        global_controls_layout.addStretch()
        global_controls_layout.addWidget(self.btn_pause_all)
        global_controls_layout.addWidget(self.btn_cancel_all)
        
        queue_layout.addLayout(global_controls_layout)

        self.btn_pause_all.clicked.connect(self.action_pause_resume_all)
        self.btn_cancel_all.clicked.connect(self.action_cancel_all)
        self.btn_clear_all.clicked.connect(self.action_clear_all)

        # التحقق من الحالة الابتدائية
        self.check_empty_state()

    def check_empty_state(self):
        has_cards = len(self.get_download_cards()) > 0
        self.empty_state_widget.setVisible(not has_cards)
        self.scroll_area.setVisible(has_cards)
        
        # إخفاء/إظهار أزرار التحكم الكلية
        self.btn_pause_all.setVisible(has_cards)
        self.btn_cancel_all.setVisible(has_cards)
        self.btn_clear_all.setVisible(has_cards)

    def get_download_cards(self):
        cards = []
        for i in range(self.cards_layout.count()):
            widget = self.cards_layout.itemAt(i).widget()
            if isinstance(widget, DownloadCard):
                cards.append(widget)
        return cards

    def action_pause_resume_all(self):
        is_pausing = "Pause" in self.btn_pause_all.text()
        self.btn_pause_all.setText(tr("btn_resume_all") if is_pausing else tr("btn_pause_all"))
        
        for widget in self.get_download_cards():
            if widget.btn_pause.isVisible():
                if is_pausing and widget.btn_pause.toolTip() == "Pause":
                    widget.btn_pause.click()
                elif not is_pausing and widget.btn_pause.toolTip() == "Resume":
                    widget.btn_pause.click()

    def action_cancel_all(self):
        self.main_app.waiting_workers.clear() 
        for widget in self.get_download_cards():
            if widget.btn_cancel.isVisible():
                widget.btn_cancel.click()
        self.check_empty_state()

    def action_clear_all(self):
        for widget in reversed(self.get_download_cards()):
            status = widget.status_label.text()
            if "✅" in status or "❌" in status:
                if hasattr(widget, 'worker') and widget.worker:
                    worker = widget.worker
                    from PyQt6 import sip
                    if not sip.isdeleted(worker):
                        try:
                            worker.progress_signal.disconnect()
                            worker.status_signal.disconnect()
                            worker.finished_signal.disconnect()
                        except:
                            pass
                        try:
                            if worker.isRunning():
                                worker.cancel()
                                worker.quit()
                                worker.finished.connect(worker.deleteLater)
                            else:
                                worker.deleteLater()
                        except RuntimeError:
                            pass
                widget.setParent(None)
                widget.deleteLater()
        self.check_empty_state()

    def update_icon_colors(self, icon_color):
        self.empty_state_widget.update_icon_color("assets/icons/download.svg", icon_color)