"""
packages_dialog.py
──────────────────
PackagesDialog — صندوق جمع الروابط المطور (Collected Links Box)
"""
import os
import json
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit,
                             QCheckBox, QWidget, QMenu, QApplication)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QDesktopServices, QAction
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.theme import get_accent_hex
from utils.locales import tr


class LinkItemWidget(QWidget):
    """عنصر مخصص لعرض الرابط مع أيقونة المنصة وزر الحذف المباشر."""
    def __init__(self, url, on_delete_fn, parent=None):
        super().__init__(parent)
        self.url = url
        self.on_delete_fn = on_delete_fn

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Platform Icon Detection
        icon_file = "assets/icons/globe.svg"
        if "youtube.com" in url or "youtu.be" in url:
            icon_file = "assets/icons/video.svg"
        elif "soundcloud.com" in url or "music" in url:
            icon_file = "assets/icons/music.svg"
        elif "tiktok.com" in url or "facebook.com" in url or "instagram.com" in url:
            icon_file = "assets/icons/video.svg"

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_colored_icon(icon_file, get_accent_hex()).pixmap(18, 18))
        layout.addWidget(icon_lbl)

        # URL Label
        url_lbl = QLabel(url)
        url_lbl.setStyleSheet(f"color: {get_current_theme_color()}; font-size: 12px; background: transparent; border: none;")
        url_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(url_lbl, 1)

        # Delete Button (Trash Icon)
        btn_del = QPushButton()
        btn_del.setFixedSize(26, 26)
        btn_del.setIcon(get_colored_icon("assets/icons/trash.svg", "#ef4444"))
        btn_del.setIconSize(QSize(14, 14))
        btn_del.setToolTip(tr("ctx_delete_link", "Delete Link"))
        btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
            }
        """)
        btn_del.clicked.connect(lambda: self.on_delete_fn(self.url))
        layout.addWidget(btn_del)


class PackagesDialog(QDialog):

    def __init__(self, parent_page=None):
        super().__init__(parent_page)
        self.parent_page = parent_page
        self.settings_file = parent_page.main_app.settings_file
        self.setObjectName("PackagesDialog")
        self.setWindowTitle(tr("packages_title", "Collected Links Box"))
        self.setFixedWidth(580)
        self.setMinimumHeight(480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

        self.initUI()
        self.load_links()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def initUI(self):
        acc = get_accent_hex()
        is_dark = get_current_theme_color() == "#f1f5f9"
        bg_color = "#0b0f19" if is_dark else "#f8fafc"
        bg_card = "#131926" if is_dark else "#ffffff"
        border_color = "#1e293b" if is_dark else "#e2e8f0"
        text_color = "#f1f5f9" if is_dark else "#0f172a"

        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }} 
            QLineEdit {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 12px;
                color: {text_color};
            }} 
            QLineEdit:focus {{ 
                border: 1px solid {acc};
            }} 
            QListWidget {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 10px;
                color: {text_color};
                padding: 5px;
            }} 
            QListWidget::item {{ 
                padding: 2px;
                border-bottom: 1px solid {border_color}33;
            }} 
            QPushButton {{ 
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 6px 12px;
                color: {text_color};
                font-weight: bold;
                font-size: 12px;
            }} 
            QPushButton:hover {{ 
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid {acc};
            }} 
            QPushButton#btn_download_all {{ 
                background-color: {acc};
                color: white;
                border: none;
            }} 
            QPushButton#btn_download_all:hover {{ 
                background-color: #3b82f6;
            }} 
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header Area (Title + Link Count + Auto-collect Switch)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        pkg_icon = QLabel()
        pkg_icon.setPixmap(get_colored_icon("assets/icons/package.svg", acc).pixmap(22, 22))
        top_layout.addWidget(pkg_icon)

        self.title_lbl = QLabel(tr("packages_title", "Collected Links Box"))
        self.title_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {acc}; background: transparent; border: none;")
        top_layout.addWidget(self.title_lbl)

        top_layout.addStretch()

        # Auto-collect Checkbox Switch
        is_auto_collect = False
        if hasattr(self.parent_page.main_app, 'settings_manager'):
            mgr = self.parent_page.main_app.settings_manager
            is_auto_collect = mgr.get("auto_collect_links", True)
            mgr.setting_changed.connect(self._on_setting_changed_externally)
        
        self.auto_collect_sw = QCheckBox(tr("auto_collect_links_label", "Auto-collect copied links"))
        self.auto_collect_sw.setToolTip(tr("auto_collect_links_tooltip"))
        self.auto_collect_sw.setChecked(is_auto_collect)
        self.auto_collect_sw.setStyleSheet("""
            QCheckBox {
                color: #94a3b8;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.auto_collect_sw.toggled.connect(self._on_auto_collect_toggled)
        top_layout.addWidget(self.auto_collect_sw)

        layout.addLayout(top_layout)

        # Add Link Input Row
        add_layout = QHBoxLayout()
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText(tr("url_placeholder", "Enter URL..."))
        self.input_url.returnPressed.connect(self.add_link)

        self.btn_add = QPushButton()
        self.btn_add.setIcon(get_colored_icon("assets/icons/save.svg", get_current_theme_color()))
        self.btn_add.setIconSize(QSize(16, 16))
        self.btn_add.setFixedWidth(40)
        self.btn_add.clicked.connect(self.add_link)

        add_layout.addWidget(self.input_url)
        add_layout.addWidget(self.btn_add)
        layout.addLayout(add_layout)

        # Action Toolbar (Paste Clipboard Links + Copy All Links)
        action_bar = QHBoxLayout()
        
        self.btn_paste_clip = QPushButton(tr("btn_paste_clipboard_links", "Paste Clipboard"))
        self.btn_paste_clip.setIcon(get_colored_icon("assets/icons/clipboard.svg", get_current_theme_color()))
        self.btn_paste_clip.setIconSize(QSize(14, 14))
        self.btn_paste_clip.clicked.connect(self.paste_clipboard_links)
        action_bar.addWidget(self.btn_paste_clip)

        self.btn_copy_all = QPushButton(tr("btn_copy_all_links", "Copy All Links"))
        self.btn_copy_all.setIcon(get_colored_icon("assets/icons/clipboard.svg", get_current_theme_color()))
        self.btn_copy_all.setIconSize(QSize(14, 14))
        self.btn_copy_all.clicked.connect(self.copy_all_links)
        action_bar.addWidget(self.btn_copy_all)

        action_bar.addStretch()
        layout.addLayout(action_bar)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setToolTip(tr("packages_tooltip"))
        layout.addWidget(self.list_widget)

        # Bottom Footer (Clear All + Cancel + Download All)
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton(tr("btn_clear_all", "Clear All"))
        self.btn_clear.setIcon(get_colored_icon("assets/icons/trash.svg", get_current_theme_color()))
        self.btn_clear.setIconSize(QSize(14, 14))
        self.btn_clear.clicked.connect(self.clear_all)

        self.btn_cancel = QPushButton(tr("btn_cancel", "Cancel"))
        self.btn_cancel.setIcon(get_colored_icon("assets/icons/cancel.svg", get_current_theme_color()))
        self.btn_cancel.setIconSize(QSize(14, 14))
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_dl_all = QPushButton(tr("btn_download_all", "Download All"))
        self.btn_dl_all.setObjectName("btn_download_all")
        self.btn_dl_all.setIcon(get_colored_icon("assets/icons/download.svg", "#ffffff"))
        self.btn_dl_all.setIconSize(QSize(14, 14))
        self.btn_dl_all.clicked.connect(self.download_all)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_dl_all)
        layout.addLayout(btn_layout)

    def contextMenuEvent(self, event):
        item = self.list_widget.itemAt(self.list_widget.mapFromGlobal(event.globalPosition().toPoint()))
        if not item:
            return
        widget = self.list_widget.itemWidget(item)
        if not widget or not hasattr(widget, 'url'):
            return

        url = widget.url
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
        """)

        copy_act = QAction(get_colored_icon("assets/icons/clipboard.svg", "#ffffff"), tr("ctx_copy_link", "Copy Link"), self)
        copy_act.triggered.connect(lambda: QApplication.clipboard().setText(url))
        menu.addAction(copy_act)

        open_act = QAction(get_colored_icon("assets/icons/globe.svg", "#ffffff"), tr("ctx_open_in_browser", "Open in Browser"), self)
        open_act.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        menu.addAction(open_act)

        menu.addSeparator()

        del_act = QAction(get_colored_icon("assets/icons/trash.svg", "#ef4444"), tr("ctx_delete_link", "Delete Link"), self)
        del_act.triggered.connect(lambda: self.remove_url(url))
        menu.addAction(del_act)

        menu.exec(event.globalPosition().toPoint())

    def _on_setting_changed_externally(self, key, value):
        if key == "auto_collect_links" and hasattr(self, 'auto_collect_sw'):
            self.auto_collect_sw.blockSignals(True)
            self.auto_collect_sw.setChecked(bool(value))
            self.auto_collect_sw.blockSignals(False)

    def _on_auto_collect_toggled(self, checked):
        if hasattr(self.parent_page.main_app, 'settings_manager'):
            self.parent_page.main_app.settings_manager.set("auto_collect_links", checked)

    def _get_saved_links(self):
        return list(self.parent_page.main_app.settings_manager.get("collected_links", []))

    def load_links(self):
        self.list_widget.clear()
        links = self._get_saved_links()

        count = len(links)
        self.title_lbl.setText(tr("packages_count_title", "Collected Links Box ({count})").format(count=count))

        if not links:
            item = QListWidgetItem(tr("packages_empty", "No collected links yet."))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            self.btn_dl_all.setEnabled(False)
            self.btn_clear.setEnabled(False)
            self.btn_copy_all.setEnabled(False)
        else:
            self.btn_dl_all.setEnabled(True)
            self.btn_clear.setEnabled(True)
            self.btn_copy_all.setEnabled(True)

            for url in links:
                item = QListWidgetItem(self.list_widget)
                widget = LinkItemWidget(url, on_delete_fn=self.remove_url, parent=self)
                item.setSizeHint(widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)

    def _add_url_to_settings(self, url):
        url = url.strip()
        if not url:
            return
        mgr = self.parent_page.main_app.settings_manager
        links = list(mgr.get("collected_links", []))
        if url not in links:
            links.append(url)
            mgr.set("collected_links", links)

    def add_link(self):
        url = self.input_url.text().strip()
        if url:
            self._add_url_to_settings(url)
            self.input_url.clear()
            self.load_links()

    def paste_clipboard_links(self):
        clip_text = QApplication.clipboard().text().strip()
        if not clip_text:
            return
        urls = re.findall(r'https?://[^\s"\']+', clip_text)
        if not urls and clip_text.startswith(('http://', 'https://')):
            urls = [clip_text]

        if urls:
            mgr = self.parent_page.main_app.settings_manager
            links = list(mgr.get("collected_links", []))
            changed = False
            for u in urls:
                u = u.strip()
                if u and u not in links:
                    links.append(u)
                    changed = True
            if changed:
                mgr.set("collected_links", links)
            self.load_links()

    def copy_all_links(self):
        links = self._get_saved_links()
        if links:
            QApplication.clipboard().setText("\n".join(links))
            if hasattr(self.parent_page.main_app, 'show_notification'):
                self.parent_page.main_app.show_notification(
                    tr("btn_copy_all_links", "Copy All Links"),
                    tr("details_link_copied", "Link copied to clipboard!")
                )

    def remove_url(self, url):
        mgr = self.parent_page.main_app.settings_manager
        links = list(mgr.get("collected_links", []))
        if url in links:
            links.remove(url)
            mgr.set("collected_links", links)
        self.load_links()

    def clear_all(self):
        self.parent_page.main_app.settings_manager.set("collected_links", [])
        self.load_links()

    def download_all(self):
        collected_urls = self._get_saved_links()
        if collected_urls:
            self.clear_all()
            self.close()
            self.parent_page.inspect_custom_links(collected_urls)
        else:
            self.close()