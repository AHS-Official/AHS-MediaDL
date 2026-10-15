import os
import json
import sys
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QMessageBox, QLabel, QDialog, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QSize
from gui.components.cards import HistoryCard
from utils.locales import tr
from utils.helpers import get_colored_icon, get_current_theme_color
from utils.theme import get_accent_hex, hex_to_rgb


class DeleteConfirmDialog(QDialog):
    """نافذة تأكيد مخصصة للاختيار بين حذف السجل فقط أو حذف السجل مع الملف الأصلي من القرص."""
    def __init__(self, count=1, parent=None):
        super().__init__(parent)
        self.count = count
        self.delete_files = False
        self.confirmed = False
        self.setWindowTitle(tr("delete_dialog_title", "Confirm Delete"))
        self.setFixedWidth(420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        acc = get_accent_hex()
        rgb = hex_to_rgb(acc)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }}
            QLabel {{
                color: #f8fafc;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Icon + Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_colored_icon("assets/icons/trash.svg", "#ef4444").pixmap(28, 28))
        header_layout.addWidget(icon_lbl)


        title_lbl = QLabel(tr("delete_dialog_title", "Confirm Delete"))
        t_font = title_lbl.font()
        t_font.setBold(True)
        t_font.setPointSize(t_font.pointSize() + 2)
        title_lbl.setFont(t_font)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Message Body
        msg_text = tr("delete_dialog_msg", "How would you like to delete the selected items ({count})?").format(count=count)
        body_lbl = QLabel(msg_text)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(body_lbl)

        # Action Buttons
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(10)

        # Option 1: Delete history only
        self.btn_hist_only = QPushButton(tr("btn_delete_history_only", "Delete from History Only"))
        self.btn_hist_only.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
        """)
        self.btn_hist_only.clicked.connect(self._on_hist_only)
        btns_layout.addWidget(self.btn_hist_only)

        # Option 2: Delete history and file
        self.btn_hist_and_file = QPushButton(tr("btn_delete_history_and_file", "Delete from History & Disk"))
        self.btn_hist_and_file.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.btn_hist_and_file.clicked.connect(self._on_hist_and_file)
        btns_layout.addWidget(self.btn_hist_and_file)

        # Option 3: Cancel
        self.btn_cancel = QPushButton(tr("btn_cancel_selection", "Cancel"))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid transparent;
            }
            QPushButton:hover {
                color: #f8fafc;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)

    def _on_hist_only(self):
        self.confirmed = True
        self.delete_files = False
        self.accept()

    def _on_hist_and_file(self):
        self.confirmed = True
        self.delete_files = True
        self.accept()


class DetailsDialog(QDialog):
    """نافذة أنيقة تعرض كافة تفاصيل العنصر المحمّل (الصورة، العنوان، الحجم، الرابط، المسار)."""
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setWindowTitle(tr("details_dialog_title", "Item Details"))
        self.setFixedWidth(540)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        acc = get_accent_hex()
        rgb = hex_to_rgb(acc)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }}
            QLabel {{
                color: #f8fafc;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Area (Info Icon + Title + Media Badge)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        info_icon_lbl = QLabel()
        info_icon_lbl.setPixmap(get_colored_icon("assets/icons/info.svg", acc).pixmap(24, 24))
        top_layout.addWidget(info_icon_lbl)

        title_lbl = QLabel(tr("details_dialog_title", "Item Details"))
        t_font = title_lbl.font()
        t_font.setBold(True)
        t_font.setPointSize(t_font.pointSize() + 3)
        title_lbl.setFont(t_font)
        title_lbl.setStyleSheet(f"color: {acc}; border: none; background: transparent;")
        top_layout.addWidget(title_lbl)

        top_layout.addStretch()

        # Media Type Badge
        media_type = item_data.get('type', 'video')
        type_str = tr("badge_video", "Video") if media_type == 'video' else tr("badge_audio", "Audio")
        badge_lbl = QLabel(type_str)
        badge_color = acc if media_type == 'video' else "#3b82f6"
        b_rgb = hex_to_rgb(badge_color)
        badge_lbl.setStyleSheet(f"""
            background-color: rgba({b_rgb[0]}, {b_rgb[1]}, {b_rgb[2]}, 0.15);
            color: {badge_color};
            border: 1px solid rgba({b_rgb[0]}, {b_rgb[1]}, {b_rgb[2]}, 0.3);
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        top_layout.addWidget(badge_lbl)
        layout.addLayout(top_layout)

        # Thumbnail Preview Box
        thumb_path = item_data.get('thumb_path', '')
        preview_frame = QFrame()
        preview_frame.setObjectName("PreviewFrame")
        preview_frame.setStyleSheet("""
            QFrame#PreviewFrame {
                background-color: #1e293b;
                border-radius: 10px;
                border: none;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        p_layout = QHBoxLayout(preview_frame)
        p_layout.setContentsMargins(12, 12, 12, 12)
        p_layout.setSpacing(14)

        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(120, 68)
        thumb_lbl.setStyleSheet("border-radius: 6px; background-color: #0f172a; border: none;")
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from PyQt6.QtGui import QPixmap, QPainter, QColor
        icon_file = "assets/icons/video.svg" if media_type == "video" else "assets/icons/music.svg"
        if thumb_path and os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(120, 68, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                final_pix = QPixmap(120, 68)
                final_pix.fill(Qt.GlobalColor.transparent)
                painter = QPainter(final_pix)
                painter.drawPixmap(0, 0, scaled_pix)
                painter.fillRect(0, 0, 120, 68, QColor(0, 0, 0, 80))
                icon_pixmap = get_colored_icon(icon_file, "#ffffff").pixmap(24, 24)
                painter.drawPixmap((120 - 24) // 2, (68 - 24) // 2, icon_pixmap)
                painter.end()
                thumb_lbl.setPixmap(final_pix)
            else:
                thumb_lbl.setPixmap(get_colored_icon(icon_file, get_current_theme_color()).pixmap(28, 28))
        else:
            thumb_lbl.setPixmap(get_colored_icon(icon_file, get_current_theme_color()).pixmap(28, 28))

        p_layout.addWidget(thumb_lbl)

        # Title inside preview box
        from gui.components.common import MultiLineElidedLabel
        title_box = MultiLineElidedLabel(item_data.get('title', tr("unknown_title")))
        tb_font = title_box.font()
        tb_font.setBold(True)
        tb_font.setPointSize(tb_font.pointSize() + 1)
        title_box.setFont(tb_font)
        title_box.setStyleSheet("color: #f8fafc; border: none; background: transparent;")
        p_layout.addWidget(title_box, 1)

        layout.addWidget(preview_frame)

        # Detail Rows Container
        details_container = QFrame()
        details_container.setObjectName("DetailsContainer")
        details_container.setStyleSheet("""
            QFrame#DetailsContainer {
                background-color: #1e293b;
                border-radius: 10px;
                border: none;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        dc_layout = QVBoxLayout(details_container)
        dc_layout.setContentsMargins(16, 16, 16, 16)
        dc_layout.setSpacing(12)

        # Row helper
        def add_row(label_text, value_text, copy_btn=False, open_btn=False, action_fn=None):
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(f"<b>{label_text}:</b>")
            lbl.setStyleSheet("color: #94a3b8; font-size: 12px; border: none; background: transparent;")
            lbl.setFixedWidth(110)
            row.addWidget(lbl)

            val = QLabel(value_text)
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setStyleSheet("color: #e2e8f0; font-size: 12px; border: none; background: transparent;")
            row.addWidget(val, 1)

            if copy_btn:
                btn_c = QPushButton(tr("details_copy_link", "Copy Link"))
                btn_c.setIcon(get_colored_icon("assets/icons/clipboard.svg", acc))
                btn_c.setIconSize(QSize(15, 15))
                btn_c.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.2);
                        color: {acc}; border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.4);
                    }}
                    QPushButton:hover {{
                        background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.35);
                    }}
                """)
                if action_fn:
                    btn_c.clicked.connect(action_fn)
                row.addWidget(btn_c)

            if open_btn:
                btn_o = QPushButton(tr("details_open_folder", "Open Folder"))
                btn_o.setIcon(get_colored_icon("assets/icons/folder-open.svg", "#ffffff"))
                btn_o.setIconSize(QSize(15, 15))
                btn_o.setStyleSheet("""
                    QPushButton {
                        background-color: #334155; color: #f8fafc; border: 1px solid #475569;
                    }
                    QPushButton:hover { background-color: #475569; }
                """)
                if action_fn:
                    btn_o.clicked.connect(action_fn)
                row.addWidget(btn_o)

            dc_layout.addLayout(row)

        if item_data.get('date'):
            add_row(tr("details_date", "Download Date"), item_data.get('date'))
        if item_data.get('size'):
            add_row(tr("details_size", "File Size"), item_data.get('size'))
        if item_data.get('duration'):
            add_row(tr("details_duration", "Duration"), item_data.get('duration'))

        # Source URL
        url = item_data.get('url', '')
        if url:
            add_row(tr("details_source_link", "Source Link"), url, copy_btn=True, action_fn=self._copy_link)

        # Save Path
        save_path = item_data.get('save_path', '')
        if save_path:
            add_row(tr("details_save_path", "Save Path"), save_path, open_btn=True, action_fn=self._open_folder)

        layout.addWidget(details_container)

        # Footer Area (Single Cancel / Close Button)
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        btn_cancel = QPushButton(tr("btn_cancel_selection", "Cancel"))
        btn_cancel.setFixedSize(110, 36)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        layout.addLayout(footer_layout)


    def _copy_link(self):
        url = self.item_data.get('url', '')
        if url:
            QApplication.clipboard().setText(url)
            if hasattr(self.parent(), 'main_app') and hasattr(self.parent().main_app, 'show_notification'):
                self.parent().main_app.show_notification(
                    tr("details_copy_link", "Copy Link"),
                    tr("details_link_copied", "Link copied to clipboard!")
                )

    def _open_folder(self):
        save_path = self.item_data.get('save_path', '')
        if save_path and os.path.exists(save_path):
            folder_path = os.path.dirname(os.path.normpath(save_path))
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'linux':
                subprocess.Popen(['xdg-open', folder_path])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder_path])



class HistoryPage(QWidget):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.selection_mode = False
        self.cards = []
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Selection Action Bar (Shown only in Selection Mode)
        self.selection_bar = QFrame()
        self.selection_bar.setObjectName("SelectionBar")
        acc = get_accent_hex()
        rgb = hex_to_rgb(acc)
        self.selection_bar.setStyleSheet(f"""
            QFrame#SelectionBar {{
                background-color: #1e293b;
                border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.3);
                border-radius: 8px;
            }}
            QLabel {{
                color: #f8fafc;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        
        bar_layout = QHBoxLayout(self.selection_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(10)

        # Buttons on the Left
        self.btn_select_all = QPushButton(tr("btn_select_all", "Select All"))
        self.btn_select_all.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: #f8fafc; border: 1px solid #475569;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        bar_layout.addWidget(self.btn_select_all)

        self.btn_delete_selected = QPushButton(tr("btn_delete_selected", "Delete Selected ({count})").format(count=0))
        self.btn_delete_selected.setStyleSheet("""
            QPushButton {
                background-color: #ef4444; color: #ffffff; border: none;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
        """)
        self.btn_delete_selected.clicked.connect(self.delete_selected_items)
        bar_layout.addWidget(self.btn_delete_selected)

        self.btn_cancel_selection = QPushButton(tr("btn_cancel_selection", "Cancel"))
        self.btn_cancel_selection.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #94a3b8; border: 1px solid #334155;
            }
            QPushButton:hover { color: #f8fafc; background-color: rgba(255, 255, 255, 0.05); }
        """)
        self.btn_cancel_selection.clicked.connect(self.exit_selection_mode)
        bar_layout.addWidget(self.btn_cancel_selection)

        bar_layout.addStretch()

        # Selection Count Text on the Right
        self.lbl_selection_count = QLabel(tr("sel_mode_count", "{count} of {total} selected").format(count=0, total=0))
        bar_layout.addWidget(self.lbl_selection_count)

        self.selection_bar.hide()
        main_layout.addWidget(self.selection_bar)


        # Empty state widget
        from gui.components.common import EmptyStateWidget
        self.empty_state_widget = EmptyStateWidget(
            "assets/icons/inbox.svg",
            tr("empty_history_title", "No Download History"),
            tr("empty_history_sub", "Completed downloads will be recorded here."),
            self,
            image_path="assets/images/history_empty.png"
        )
        self.empty_state_widget.set_action(
            tr("btn_start_download", "Start Downloading"),
            self._go_to_search,
            tr("empty_history_hint", "Head to Search and paste a URL to begin")
        )
        main_layout.addWidget(self.empty_state_widget)

        # Scroll area for history cards
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

        self.load_history_ui()

    def _go_to_search(self):
        """ينقل لصفحة البحث لبدء تحميل جديد."""
        if hasattr(self.main_app, 'ui_manager'):
            self.main_app.ui_manager.change_page(0)

    def _create_history_card(self, item):
        card = HistoryCard(
            title=item.get('title', tr("unknown_title")),
            url=item.get('url', ''),
            media_type=item.get('type', 'video'),
            date_str=item.get('date', ''),
            thumb_path=item.get('thumb_path', ''),
            save_path=item.get('save_path', ''),
            duration=item.get('duration', ''),
            size=item.get('size', ''),
            main_app=self.main_app
        )
        if 'id' in item:
            card.item_data['id'] = item['id']
        card.selection_changed.connect(self.update_selection_bar_ui)
        card.request_selection_mode.connect(self.enter_selection_mode)
        card.request_delete.connect(self.delete_single_card)
        card.request_details.connect(self.show_details_dialog)
        return card

    def load_history_ui(self):
        self.exit_selection_mode()
        self.cards.clear()

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        history_data = self.main_app.history_manager.load_history()
        has_items = bool(history_data)

        if has_items:
            for item in history_data:
                card = self._create_history_card(item)
                self.cards.append(card)
                self.cards_layout.addWidget(card)

        self.empty_state_widget.setVisible(not has_items)
        self.scroll_area.setVisible(has_items)

    def add_to_history(self, title, duration, size, url, media_type, thumb_path="", save_path=""):
        from datetime import datetime
        row_id = self.main_app.history_manager.add_to_history(title, duration, size, url, media_type, thumb_path, save_path)
        
        # Remove existing card with same (url, media_type) if replaced
        for existing_card in list(self.cards):
            if existing_card.url == url and existing_card.media_type == media_type:
                self.cards.remove(existing_card)
                self.cards_layout.removeWidget(existing_card)
                existing_card.deleteLater()
                break

        new_item = {
            'id': row_id,
            'title': title,
            'url': url,
            'type': media_type,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'thumb_path': thumb_path,
            'save_path': save_path,
            'duration': duration,
            'size': size
        }
        new_card = self._create_history_card(new_item)
        if self.selection_mode:
            new_card.set_selection_mode(True)
        self.cards.insert(0, new_card)
        self.cards_layout.insertWidget(0, new_card)

        self.empty_state_widget.setVisible(False)
        self.scroll_area.setVisible(True)
    
    def enter_selection_mode(self, target_card=None):
        self.selection_mode = True
        self.selection_bar.show()

        for card in self.cards:
            card.set_selection_mode(True)

        if target_card and isinstance(target_card, HistoryCard):
            target_card.set_selected(True)

        self.update_selection_bar_ui()

    def exit_selection_mode(self):
        self.selection_mode = False
        self.selection_bar.hide()

        for card in self.cards:
            card.set_selection_mode(False)

    def update_selection_bar_ui(self):
        if not self.selection_mode:
            return

        selected_count = sum(1 for card in self.cards if card.is_selected())
        total_count = len(self.cards)

        self.lbl_selection_count.setText(
            tr("sel_mode_count", "{count} of {total} selected").format(count=selected_count, total=total_count)
        )
        self.btn_delete_selected.setText(
            tr("btn_delete_selected", "Delete Selected ({count})").format(count=selected_count)
        )
        self.btn_delete_selected.setEnabled(selected_count > 0)

        if selected_count == total_count and total_count > 0:
            self.btn_select_all.setText(tr("btn_deselect_all", "Deselect All"))
        else:
            self.btn_select_all.setText(tr("btn_select_all", "Select All"))

    def toggle_select_all(self):
        selected_count = sum(1 for card in self.cards if card.is_selected())
        total_count = len(self.cards)
        
        target_state = not (selected_count == total_count and total_count > 0)
        for card in self.cards:
            card.set_selected(target_state)

    def delete_selected_items(self):
        selected_cards = [card for card in self.cards if card.is_selected()]
        if not selected_cards:
            return

        dlg = DeleteConfirmDialog(count=len(selected_cards), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.confirmed:
            entries_to_delete = [card.item_data for card in selected_cards]
            self.main_app.history_manager.remove_entries(
                entries_to_delete, 
                delete_files=dlg.delete_files,
                is_active_cb=self.main_app.download_manager.is_path_active
            )
            self.load_history_ui()

    def delete_single_card(self, card):
        dlg = DeleteConfirmDialog(count=1, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.confirmed:
            self.main_app.history_manager.remove_entries(
                [card.item_data], 
                delete_files=dlg.delete_files,
                is_active_cb=self.main_app.download_manager.is_path_active
            )
            self.load_history_ui()

    def show_details_dialog(self, card):
        dlg = DetailsDialog(card.item_data, parent=self)
        dlg.exec()

    def update_icon_colors(self, icon_color):
        self.empty_state_widget.update_icon_color("assets/icons/inbox.svg", icon_color)
        for card in self.cards:
            card.update_icon_colors(icon_color)

    def update_accent_colors(self):
        if hasattr(self, 'empty_state_widget') and self.empty_state_widget:
            self.empty_state_widget.update_accent_color()
        acc = get_accent_hex()
        rgb = hex_to_rgb(acc)
        if hasattr(self, 'selection_bar'):
            self.selection_bar.setStyleSheet(f"""
                QFrame#SelectionBar {{
                    background-color: #1e293b;
                    border: 1px solid rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.3);
                    border-radius: 8px;
                }}
                QLabel {{ color: #f8fafc; font-weight: bold; font-size: 13px; }}
                QPushButton {{ border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: bold; }}
            """)
