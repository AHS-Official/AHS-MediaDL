"""
search_page.py
──────────────
الصفحة الرئيسية الموحدة: تدمج فحص الروابط (URL Inspect) والبحث في يوتيوب (YouTube Search)
في واجهة واحدة ذكية ومتكاملة.
"""
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QFrame, QScrollArea, QStackedWidget,
    QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QSize, QThreadPool, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from core.downloader import DownloadWorker
from services.yt_dlp_service import InspectWorker, SearchWorker, ThumbnailRunnable
from gui.components.common import EmptyStateWidget, LoadingSpinner
from gui.components.cards import DownloadCard, SearchResultCard
from gui.components.dialogs import PackagesDialog, QualitySelectionDialog, PlaylistSelectionDialog
from gui.components.media_panels import SingleVideoPanel, PlaylistPanel
from utils.helpers import (
    clean_and_shorten_title, get_colored_icon, get_current_theme_color
)
from utils.locales import tr


class SearchPage(QWidget):
    """
    الصفحة الرئيسية الموحدة (URL Download + YouTube Search).
    - لو المدخل URL → inspect وتنزيل
    - لو كلمات → بحث في يوتيوب
    """

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.is_playlist_mode = False
        self.selected_playlist_entries = []
        self.clean_title = "video"
        # Search state
        self.search_card_widgets = []
        self.search_worker = None
        self.inspect_worker = None
        self.video_offset = 1
        self.playlist_offset = 1
        self.current_query = ""
        self._current_mode = "idle"  # idle | url | search
        self.initUI()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Input Bar ─────────────────────────────────────────────────────────
        url_layout = QHBoxLayout()
        url_layout.setContentsMargins(10, 10, 10, 10)
        url_layout.setSpacing(8)

        self.package_btn = QPushButton(self)
        self.package_btn.setIcon(get_colored_icon("assets/icons/package.svg", get_current_theme_color()))
        self.package_btn.setIconSize(QSize(18, 18))
        self.package_btn.setFixedSize(44, 44)
        self.package_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.package_btn.setToolTip(tr("btn_packages", "Link Aggregator"))
        self.package_btn.clicked.connect(self.show_package_dialog)
        url_layout.addWidget(self.package_btn)

        self.smart_paste_btn = QPushButton(self)
        self.smart_paste_btn.setIcon(get_colored_icon("assets/icons/clipboard.svg", get_current_theme_color()))
        self.smart_paste_btn.setIconSize(QSize(18, 18))
        self.smart_paste_btn.setFixedSize(44, 44)
        self.smart_paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.smart_paste_btn.setToolTip(tr("tooltip_paste_link", "Paste from Clipboard"))
        self.smart_paste_btn.clicked.connect(self.paste_text)
        self.paste_btn = self.smart_paste_btn
        url_layout.addWidget(self.smart_paste_btn)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(tr("url_or_search_placeholder", "Enter media URL or search YouTube..."))
        self.url_input.setClearButtonEnabled(True)
        self.url_input.setFixedHeight(44)
        self.url_input.textChanged.connect(self.on_text_changed)
        self.url_input.returnPressed.connect(self.on_input_submit)
        url_layout.addWidget(self.url_input)

        self.inspect_btn = QPushButton(self)
        self.inspect_btn.setIcon(get_colored_icon("assets/icons/search-lens.svg", "#ffffff"))
        self.inspect_btn.setIconSize(QSize(18, 18))
        self.inspect_btn.setFixedHeight(44)
        self.inspect_btn.setMinimumWidth(54)
        self.inspect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.inspect_btn.setToolTip(tr("tooltip_search_inspect", "Inspect URL or Search YouTube"))
        self.inspect_btn.clicked.connect(self.on_input_submit)
        url_layout.addWidget(self.inspect_btn)

        main_layout.addLayout(url_layout)

        # ── Result Stack ──────────────────────────────────────────────────────
        self.result_stack = QStackedWidget()
        main_layout.addWidget(self.result_stack)

        # Index 0: URL mode — empty state + guide + info cards
        self.page_single = QWidget()
        page_single_layout = QVBoxLayout(self.page_single)
        page_single_layout.setContentsMargins(0, 0, 0, 0)
        page_single_layout.setSpacing(10)

        self.empty_state_widget = EmptyStateWidget(
            "assets/icons/search-lens.svg",
            tr("empty_home_title", "Ready to Download"),
            tr("empty_home_sub", "Enter a URL to download or keywords to search YouTube."),
            self,
            image_path="assets/images/home_empty.png"
        )
        self.empty_state_widget.hide()
        page_single_layout.addWidget(self.empty_state_widget)

        # ── Guide Dashboard Widget ────────────────────────────────────────────
        self.guide_dashboard = QWidget()
        guide_layout = QVBoxLayout(self.guide_dashboard)
        guide_layout.setContentsMargins(15, 20, 15, 15)
        guide_layout.setSpacing(25)
        guide_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.guide_welcome_title = QLabel(tr("guide_welcome_title", "Welcome to AHS-MediaDL"), self)
        self.guide_welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        guide_layout.addWidget(self.guide_welcome_title)

        self.guide_welcome_sub = QLabel(tr("guide_welcome_sub", "The fast and premium media downloader of your choice"), self)
        self.guide_welcome_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        guide_layout.addWidget(self.guide_welcome_sub)

        self.qactions_container = QFrame(self)
        self.qactions_container.setObjectName("QActionsContainer")
        qactions_layout = QHBoxLayout(self.qactions_container)
        qactions_layout.setSpacing(15)

        self.btn_quick_paste = QPushButton(tr("quick_action_paste", "📋 Paste & Download"), self)
        self.btn_quick_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_paste.setFixedHeight(35)
        self.btn_quick_paste.clicked.connect(self.quick_paste_action)
        qactions_layout.addWidget(self.btn_quick_paste)

        self.btn_quick_search = QPushButton(tr("quick_action_search", "🔍 Search YouTube"), self)
        self.btn_quick_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_search.setFixedHeight(35)
        self.btn_quick_search.clicked.connect(self.quick_search_action)
        qactions_layout.addWidget(self.btn_quick_search)

        self.btn_quick_settings = QPushButton(tr("quick_action_settings", "⚙️ Open Settings"), self)
        self.btn_quick_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_settings.setFixedHeight(35)
        self.btn_quick_settings.clicked.connect(self.quick_settings_action)
        qactions_layout.addWidget(self.btn_quick_settings)

        guide_layout.addWidget(self.qactions_container)

        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(15)

        steps = [
            ("assets/icons/clipboard.svg", tr("step_1_title", "1. Copy Link"), tr("step_1_sub", "Copy a video/playlist link from any supported platform")),
            ("assets/icons/search-lens.svg", tr("step_2_title", "2. Paste or Search"), tr("step_2_sub", "Paste link above or enter search query")),
            ("assets/icons/download.svg", tr("step_3_title", "3. Choose & Download"), tr("step_3_sub", "Pick format/quality and click Download"))
        ]

        self.guide_cards = []
        for icon_path, step_title, step_sub in steps:
            card = QFrame(self)
            card.setObjectName("GuideCard")
            card.setMinimumWidth(190)
            card.setMaximumWidth(230)
            card.setMinimumHeight(170)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 16, 14, 16)
            card_layout.setSpacing(8)

            lbl_icon = QLabel(card)
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_icon)

            lbl_title = QLabel(step_title, card)
            lbl_title.setWordWrap(True)
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_title)

            lbl_sub = QLabel(step_sub, card)
            lbl_sub.setWordWrap(True)
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_sub)

            steps_layout.addWidget(card)
            self.guide_cards.append((card, lbl_icon, lbl_title, lbl_sub, icon_path))

        guide_layout.addLayout(steps_layout)
        page_single_layout.addWidget(self.guide_dashboard)
        self.update_guide_theme()

        self.content_container = QWidget()
        self.content_container.hide()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)

        # ── Shared Single-Video Panel ─────────────────────────────────────────
        self.preview_widget = SingleVideoPanel(self.main_app)
        self.content_layout.addWidget(self.preview_widget)
        self.content_layout.addStretch()

        self.info_card = self.preview_widget.info_card
        self.settings_card = self.preview_widget.settings_card
        self.thumb_label = self.preview_widget.thumb_label
        self.title_label = self.preview_widget.title_label
        self.duration_label = self.preview_widget.duration_label
        self.format_combo = self.preview_widget.format_combo
        self.sub_cb = self.preview_widget.sub_cb
        self.sub_combo = self.preview_widget.sub_combo
        self.remember_choice_cb = self.preview_widget.remember_choice_cb

        page_single_layout.addWidget(self.content_container)
        self.result_stack.addWidget(self.page_single)

        # Index 1: Playlist mode — PlaylistPanel
        self.page_playlist = QWidget()
        self.page_pl_layout = QVBoxLayout(self.page_playlist)
        self.page_pl_layout.setContentsMargins(0, 0, 0, 0)
        self.page_pl_layout.setSpacing(12)

        self.playlist_widget = PlaylistPanel(self.main_app)
        self.page_pl_layout.addWidget(self.playlist_widget)

        self.pl_select_all_cb  = self.playlist_widget.pl_select_all_cb
        self.pl_scroll         = self.playlist_widget.pl_scroll
        self.pl_items_layout   = self.playlist_widget.pl_items_layout
        self.pl_checkboxes     = self.playlist_widget.pl_checkboxes

        self.result_stack.addWidget(self.page_playlist)

        # Index 2: YouTube Search results
        self.page_search_results = QWidget()
        page_search_layout = QVBoxLayout(self.page_search_results)
        page_search_layout.setContentsMargins(0, 0, 0, 0)
        page_search_layout.setSpacing(8)
        self._init_search_ui(page_search_layout)
        self.result_stack.addWidget(self.page_search_results)

        # ── Action Buttons (Download Now & Cancel) ────────────────────────────
        self.home_controls_layout = QHBoxLayout()
        self.cancel_btn = QPushButton(tr("btn_cancel", "Cancel"), self)
        self.cancel_btn.setObjectName("btn_cancel_inline")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.cancel_action)
        self.home_controls_layout.addWidget(self.cancel_btn)

        self.home_controls_layout.addStretch()

        self.download_btn = QPushButton(tr("start_download", "Download Now"), self)
        self.download_btn.setObjectName("btn_download_inline")
        self.download_btn.setFixedHeight(40)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.hide()
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        self.home_controls_layout.addWidget(self.download_btn)
        main_layout.addLayout(self.home_controls_layout)

    def _init_search_ui(self, page_search_layout):
        self.search_empty_state = EmptyStateWidget(
            "assets/icons/search-lens.svg",
            tr("search_empty_title", "Search YouTube"),
            tr("search_empty_sub", "Enter keywords or phrases to search and download videos directly."),
            self,
            image_path="assets/images/home_empty.png"
        )
        page_search_layout.addWidget(self.search_empty_state)

        self.search_scroll_area = QScrollArea(self)
        self.search_scroll_area.setWidgetResizable(True)
        self.search_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.search_scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.search_results_container = QWidget()
        self.search_results_container.setStyleSheet("background: transparent;")
        self.search_results_layout = QVBoxLayout(self.search_results_container)
        self.search_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.search_results_layout.setSpacing(8)
        self.search_results_layout.setContentsMargins(0, 0, 0, 0)
        self.search_scroll_area.setWidget(self.search_results_container)
        self.search_scroll_area.hide()
        page_search_layout.addWidget(self.search_scroll_area)

        self.load_more_btn = QPushButton(tr("search_load_more", "Load More"), self)
        self.load_more_btn.clicked.connect(self.load_more_results)
        self.load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_more_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #3b82f6;
                border: none;
                padding: 6px 12px;
                font-size: 14px;
                font-weight: bold;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #2563eb;
            }
            QPushButton:disabled {
                color: gray;
                text-decoration: none;
            }
        """)
        self.load_more_btn.hide()
        page_search_layout.addWidget(self.load_more_btn)

        self.load_more_spinner = LoadingSpinner(size=28, color="#3b82f6", parent=self)
        self.load_more_spinner.hide()

    # ──────────────────────────── Layout & State ─────────────────────────────

    def setup_single_layout(self):
        if self.settings_card.parent() != self.content_container:
            self.content_layout.insertWidget(1, self.settings_card)
        if self.download_btn.parent() != self:
            self.home_controls_layout.addWidget(self.download_btn)
        if self.cancel_btn.parent() != self:
            self.home_controls_layout.insertWidget(0, self.cancel_btn)

    def setup_playlist_layout(self):
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)
        self.download_btn.show()
        self.download_btn.setEnabled(True)

    def reset_ui_state(self):
        self.setup_single_layout()
        self.title_label.setText("")
        self.title_label.setToolTip("")
        self.duration_label.setText("")
        self.thumb_label.hide()
        self.thumb_label.clear()
        self.clean_title = "video"
        self.format_combo.clear()
        self.format_combo.addItem(tr("waiting_url"), "")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.download_btn.hide()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.hide()
        self.sub_cb.hide()
        self.sub_combo.hide()
        self.info_card.hide()
        self.settings_card.hide()
        self.content_container.hide()
        self.empty_state_widget.hide_loading()
        self.empty_state_widget.hide()
        self.guide_dashboard.show()
        if hasattr(self, 'thumb_workers'):
            self.thumb_workers.clear()
        if hasattr(self, 'playlist_widget'):
            self.playlist_widget.reset()
            self.pl_checkboxes = self.playlist_widget.pl_checkboxes
        if hasattr(self, 'result_stack'):
            self.result_stack.setCurrentIndex(0)
        self._clear_search_results()
        if hasattr(self, 'search_scroll_area'):
            self.search_scroll_area.hide()
        self._current_mode = "idle"
        self.is_playlist_mode = False

    def cancel_action(self):
        if hasattr(self, 'url_input'):
            self.url_input.clear()
        self.reset_ui_state()

    # ──────────────────────────── Input Logic ────────────────────────────────

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def quick_paste_action(self):
        self.paste_text()
        self.on_input_submit()

    def quick_search_action(self):
        self.url_input.setFocus()
        self.url_input.selectAll()

    def quick_settings_action(self):
        self.main_app.ui_manager.change_page(3)

    def cancel_active_workers(self):
        if hasattr(self, 'search_worker') and self.search_worker is not None:
            try:
                self.search_worker.results_signal.disconnect()
                self.search_worker.error_signal.disconnect()
                self.search_worker.finished.disconnect()
                self.search_worker.finished.connect(self.search_worker.deleteLater)
            except Exception:
                pass
            self.search_worker = None

        if hasattr(self, 'inspect_worker') and self.inspect_worker is not None:
            try:
                self.inspect_worker.result_signal.disconnect()
                self.inspect_worker.playlist_signal.disconnect()
                self.inspect_worker.error_signal.disconnect()
                self.inspect_worker.thumbnail_signal.disconnect()
            except Exception:
                pass
            self.inspect_worker = None

    def on_text_changed(self, text):
        if not text:
            self.cancel_active_workers()
            self.reset_ui_state()

    def _is_url(self, text):
        t = text.strip().lower()
        if t.startswith("dl:"):
            t = t[3:].strip()
        if t.startswith(("http://", "https://", "www.")):
            return True
        known_domains = (
            "youtube.com/", "youtu.be/", "facebook.com/", "fb.watch/",
            "tiktok.com/", "instagram.com/", "twitter.com/", "x.com/", "soundcloud.com/"
        )
        return any(d in t for d in known_domains)

    def on_input_submit(self):
        text = self.url_input.text().strip()
        if not text:
            return
        self.cancel_active_workers()
        if self._is_url(text):
            if text.lower().startswith("dl:"):
                text = text[3:].strip()
            if not text.lower().startswith(("http://", "https://")):
                text = "https://" + text
                self.url_input.blockSignals(True)
                self.url_input.setText(text)
                self.url_input.blockSignals(False)
            self.inspect_url()
        else:
            self.perform_search()

    # ─────────────────────────── Inspect URL ─────────────────────────────────

    def inspect_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.title_label.setText(tr("err_empty_url"))
            return
        if "watch?v=" in url and "list=" in url:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("playlist_detected_title"))
            msg_box.setText(tr("playlist_detected_msg"))
            btn_playlist = msg_box.addButton(tr("btn_all_playlist"), QMessageBox.ButtonRole.ActionRole)
            btn_video = msg_box.addButton(tr("btn_just_video"), QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(tr("msg_cancel"), QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            if msg_box.clickedButton() == btn_video:
                url = re.sub(r'&list=[^&]+', '', url)
                url = url.split("&")[0]
            elif msg_box.clickedButton() == btn_playlist:
                match = re.search(r'list=([^&]+)', url)
                if match:
                    list_id = match.group(1)
                    if list_id.startswith(("PL", "OL", "UL", "UU")):
                        url = f"https://www.youtube.com/playlist?list={list_id}"
            else:
                return
        else:
            if "youtu.be" in url or "shorts" in url:
                url = url.split("?")[0]
            elif "watch?v=" in url:
                url = url.split("&")[0]

        self.cancel_active_workers()
        self.url_input.blockSignals(True)
        self.url_input.setText(url)
        self.url_input.blockSignals(False)

        self.title_label.setText(tr("searching"))
        self.duration_label.setText("")
        self.title_label.setToolTip("")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(False)
        
        self.content_container.hide()
        self.info_card.hide()
        self.settings_card.hide()
        self.empty_state_widget.show_loading(tr("searching"))
        self.empty_state_widget.show()
        self.guide_dashboard.hide()
        self.result_stack.setCurrentIndex(0)

        self.inspect_worker = InspectWorker(url)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.playlist_signal.connect(self.on_playlist_success)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.thumbnail_signal.connect(self.on_inspect_thumbnail_loaded)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    def on_inspect_success(self, title, duration_secs, image_data, format_list, subtitles_dict=None, extra_info=None):
        self.preview_widget.populate(title, duration_secs, image_data, format_list, subtitles_dict, extra_info)
        self.clean_title = self.preview_widget.clean_title

        self.empty_state_widget.hide_loading()
        self.empty_state_widget.hide()
        self.content_container.show()
        self.info_card.show()
        self.settings_card.show()
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.show()
            self.cancel_btn.setEnabled(True)
        self.download_btn.show()
        self.download_btn.setEnabled(True)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def on_inspect_thumbnail_loaded(self, data):
        if data:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                if self.is_playlist_mode:
                    self.current_pl_image = data
                else:
                    self.thumb_label.setPixmap(pixmap)
                    self.thumb_label._pixmap = pixmap
                    self.thumb_label.show()

    def on_playlist_success(self, title, image_data, entries):
        if len(entries) >= 200:
            reply = QMessageBox.warning(
                self, 
                tr("warning", "Warning"), 
                f"This playlist contains {len(entries)} items.\nProcessing a playlist this large may impact performance or take a long time.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.empty_state_widget.hide_loading()
                self.reset_ui_state()
                self.inspect_btn.setEnabled(True)
                self.url_input.setEnabled(True)
                return

        self.empty_state_widget.hide_loading()
        self.empty_state_widget.hide()
        self.reset_ui_state()
        self.is_playlist_mode = True
        self.current_pl_title = title
        self.current_pl_image = image_data
        
        self.playlist_widget.populate(title, image_data, entries)
        self.clean_title = self.playlist_widget.clean_title
        self.pl_checkboxes = self.playlist_widget.pl_checkboxes

        self.setup_playlist_layout()
        self.result_stack.setCurrentIndex(1)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def update_playlist_thumb(self, index, data):
        self.playlist_widget.update_playlist_thumb(index, data)

    def toggle_all_playlist_items(self):
        self.playlist_widget.toggle_all_playlist_items()

    def on_inspect_error(self, error_msg):
        self.empty_state_widget.hide_loading()
        self.reset_ui_state()
        self.guide_dashboard.hide()
        self.empty_state_widget.hide()
        self.content_container.show()
        self.info_card.show()
        self.title_label.setText(error_msg)
        self.inspect_btn.setEnabled(True)
        self.url_input.setEnabled(True)

    def inspect_custom_links(self, urls):
        self.cancel_active_workers()
        
        self.title_label.setText(tr("searching"))
        self.duration_label.setText("")
        self.title_label.setToolTip("")
        self.format_combo.setEnabled(False)
        self.download_btn.setEnabled(False)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(False)
        
        self.content_container.hide()
        self.info_card.hide()
        self.settings_card.hide()
        self.empty_state_widget.show_loading(tr("searching"))
        self.empty_state_widget.show()
        self.guide_dashboard.hide()
        self.result_stack.setCurrentIndex(0)

        self.inspect_worker = InspectWorker(urls)
        self.inspect_worker.result_signal.connect(self.on_inspect_success)
        self.inspect_worker.playlist_signal.connect(self.on_playlist_success)
        self.inspect_worker.error_signal.connect(self.on_inspect_error)
        self.inspect_worker.thumbnail_signal.connect(self.on_inspect_thumbnail_loaded)
        self.inspect_worker.finished.connect(self.inspect_worker.deleteLater)
        self.inspect_worker.start()

    # ─────────────────────────── Download ────────────────────────────────────

    def start_download(self):
        url = self.url_input.text()
        if not url and not self.is_playlist_mode:
            return
        mgr = self.main_app.settings_manager
        video_container = mgr.get("video_container", "mp4")
        audio_container = mgr.get("audio_container", "mp3")
        download_path_type = mgr.get("download_path_type", "always_ask")
        custom_path = mgr.get("custom_path", "")

        if download_path_type == "downloads":
            target_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        elif download_path_type == "custom" and custom_path:
            try:
                os.makedirs(custom_path, exist_ok=True)
                target_dir = custom_path
            except Exception:
                target_dir = self.main_app.last_save_dir
                download_path_type = "always_ask"
        else:
            target_dir = self.main_app.last_save_dir

        if self.is_playlist_mode:
            format_code = self.playlist_widget.format_combo.currentData()
        else:
            format_code = self.preview_widget.format_combo.currentData()

        if format_code.startswith("audio:"):
            codec = audio_container
            filter_str = f"Audio Files (*.{codec})"
        else:
            all_filters = {
                "mp4": "MP4 Video (*.mp4)",
                "mkv": "MKV Video (*.mkv)",
                "mov": "MOV Video (*.mov)",
                "webm": "WebM Video (*.webm)"
            }
            pref_filter = all_filters.get(video_container, "MP4 Video (*.mp4)")
            other_filters = [f for k, f in all_filters.items() if k != video_container]
            filter_str = f"{pref_filter};;{';;'.join(other_filters)}"

        if self.is_playlist_mode:
            selected = [entry for cb, entry in self.pl_checkboxes if cb.isChecked()]
            if not selected:
                QMessageBox.warning(self, tr("warning", "Warning"), tr("select_at_least_one", "Please select at least one video to download."))
                return
            self.selected_playlist_entries = selected
            if download_path_type == "always_ask":
                save_dir = QFileDialog.getExistingDirectory(self, tr("dialog_select_playlist", "Select Folder for Playlist"), target_dir)
                if not save_dir:
                    return
            else:
                save_dir = target_dir
            self.main_app.last_save_dir = save_dir
            self.main_app.save_settings(save_dir)
            is_audio = format_code.startswith("audio:")
            playlist_target_dir = save_dir if is_audio else os.path.join(save_dir, self.clean_title)
            if not is_audio and not os.path.exists(playlist_target_dir):
                os.makedirs(playlist_target_dir, exist_ok=True)
            for entry in self.selected_playlist_entries:
                vid_url = entry['url']
                clean_vid_title = clean_and_shorten_title(entry['title'])
                if is_audio:
                    ext = f".{audio_container}"
                    final_title = clean_vid_title
                else:
                    ext = f".{video_container}"
                    original_index = entry.get('original_index', 1)
                    final_title = f"{original_index}. {clean_vid_title}"
                save_path = os.path.join(playlist_target_dir, f"{final_title}{ext}")
                counter = 1
                base, ext_orig = os.path.splitext(save_path)
                while os.path.exists(save_path):
                    save_path = f"{base}_{counter}{ext_orig}"
                    counter += 1
                thumb_pixmap = entry.get('thumb_pixmap')
                if not thumb_pixmap and hasattr(self, 'current_pl_image') and self.current_pl_image:
                    pix = QPixmap()
                    pix.loadFromData(self.current_pl_image)
                    thumb_pixmap = pix
                is_playlist_sub = self.playlist_widget.sub_cb.isVisible() and self.playlist_widget.sub_cb.isChecked()
                new_card = DownloadCard(final_title, thumb_pixmap, save_path)
                new_card.url = vid_url
                new_card.format_code = format_code
                new_card.sub_lang = mgr.get("primary_sub_lang", "ar") if is_playlist_sub else None
                new_card.is_playlist_sub = is_playlist_sub
                new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
                new_card.duration = tr("playlist_item_duration")
                self.main_app.cards_layout.insertWidget(0, new_card)
                worker = DownloadWorker(vid_url, format_code, save_path, sub_lang=new_card.sub_lang, is_playlist_sub=is_playlist_sub)
                worker.progress_signal.connect(new_card.update_progress)
                worker.status_signal.connect(new_card.update_status)
                worker.finished_signal.connect(new_card.set_save_path)
                worker.sub_notification_signal.connect(self.main_app.handle_subtitle_notification)
                new_card.set_worker(worker)
                new_card.btn_reload.clicked.connect(
                    lambda checked=False, c=new_card, u=vid_url, f=format_code, s=save_path, sb=new_card.sub_lang, ips=is_playlist_sub:
                    self.main_app.download_manager.reload_download(c, u, f, s, sb, ips)
                )
                self.main_app.download_manager.add_worker(worker)
                new_card.update_status(tr("status_waiting_queue", "⏳ Waiting in queue..."))
            self.main_app.page_downloads.check_empty_state()
            self.is_playlist_mode = False
            self.selected_playlist_entries.clear()
        else:
            if download_path_type == "always_ask":
                save_path, selected_filter = QFileDialog.getSaveFileName(
                    self, tr("dialog_save_media_as", "Save Media As"),
                    os.path.join(target_dir, self.clean_title), filter_str
                )
                if not save_path:
                    return
                if format_code.startswith("audio:"):
                    if not save_path.lower().endswith(f".{codec}"):
                        save_path += f".{codec}"
                else:
                    for ext in ["mp4", "mkv", "mov", "webm"]:
                        if ext in selected_filter.lower():
                            if not save_path.lower().endswith(f".{ext}"):
                                save_path += f".{ext}"
                            break
            else:
                ext = f".{codec}" if format_code.startswith("audio:") else f".{video_container}"
                save_path = os.path.join(target_dir, f"{self.clean_title}{ext}")
                counter = 1
                base, ext_orig = os.path.splitext(save_path)
                while os.path.exists(save_path):
                    save_path = f"{base}_{counter}{ext_orig}"
                    counter += 1
            self.main_app.last_save_dir = os.path.dirname(save_path)
            self.main_app.save_settings(self.main_app.last_save_dir)
            sub_lang = None
            if self.preview_widget.sub_cb.isVisible() and self.preview_widget.sub_cb.isChecked():
                sub_lang = self.preview_widget.sub_combo.currentData()
            new_card = DownloadCard(self.title_label.toolTip(), self.thumb_label._pixmap, save_path)
            new_card.url = url
            new_card.format_code = format_code
            new_card.sub_lang = sub_lang
            new_card.is_playlist_sub = False
            new_card.media_type = "audio" if format_code.startswith("audio:") else "video"
            new_card.duration = self.duration_label.text().replace(tr("duration_prefix"), "") if self.duration_label.text() else "00:00"
            self.main_app.cards_layout.insertWidget(0, new_card)
            worker = DownloadWorker(url, format_code, save_path, sub_lang=sub_lang)
            worker.progress_signal.connect(new_card.update_progress)
            worker.status_signal.connect(new_card.update_status)
            worker.finished_signal.connect(new_card.set_save_path)
            new_card.set_worker(worker)
            new_card.btn_reload.clicked.connect(
                lambda checked=False, c=new_card, u=url, f=format_code, s=save_path, sb=sub_lang:
                self.main_app.download_manager.reload_download(c, u, f, s, sb)
            )
            self.main_app.download_manager.add_worker(worker)
            new_card.update_status(tr("status_waiting_queue", "⏳ Waiting in queue..."))
            self.main_app.page_downloads.check_empty_state()

        self.on_text_changed("")
        self.url_input.clear()
        self.main_app.download_manager.process_queue()

    def toggle_sub_combo(self, checked):
        self.preview_widget.toggle_sub_combo(checked)

    def auto_select_saved_format(self):
        self.preview_widget.auto_select_saved_format()

    def save_format_preference(self):
        self.preview_widget.save_format_preference()

    def on_remember_choice_toggled(self, checked):
        self.preview_widget.on_remember_choice_toggled(checked)

    # ──────────────────────────── YouTube Search ─────────────────────────────

    def perform_search(self):
        query = self.url_input.text().strip()
        if not query:
            return
        self.current_query = query
        self.video_offset = 1
        self.playlist_offset = 1
        self._current_mode = "search"

        self.load_more_btn.hide()
        self._clear_search_results()
        self.search_scroll_area.hide()

        self.search_empty_state.show_loading(tr("search_searching", "Searching YouTube..."))
        self.search_empty_state.show()
        self.download_btn.hide()
        self.result_stack.setCurrentIndex(2)

        self.search_worker = SearchWorker(self.current_query, self.video_offset, self.playlist_offset)
        self.search_worker.results_signal.connect(self.on_search_success)
        self.search_worker.error_signal.connect(self.on_search_error)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def load_more_results(self):
        if not self.current_query:
            return
        if hasattr(self, 'search_scroll_area'):
            self._saved_scroll_val = self.search_scroll_area.verticalScrollBar().value()
        self.load_more_btn.hide()
        
        btn_idx = self.search_results_layout.indexOf(self.load_more_btn)
        if btn_idx != -1:
            self.search_results_layout.insertWidget(btn_idx, self.load_more_spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            self.search_results_layout.addWidget(self.load_more_spinner, alignment=Qt.AlignmentFlag.AlignCenter)
            
        self.load_more_spinner.show()
        self.load_more_spinner.start()
        
        self.video_offset += 10
        self.playlist_offset += 5
        self.search_worker = SearchWorker(self.current_query, self.video_offset, self.playlist_offset)
        self.search_worker.results_signal.connect(self.on_load_more_success)
        self.search_worker.error_signal.connect(self.on_search_error)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def on_search_success(self, results):
        self._clear_search_results()
        self.search_empty_state.hide_loading()
        if not results:
            self.search_empty_state.title_label.setText(tr("search_no_results", "No results found."))
            if hasattr(self.search_empty_state, 'subtitle_label'):
                self.search_empty_state.subtitle_label.setText("")
            self.search_empty_state.show()
            self.load_more_btn.hide()
            return
        self.search_empty_state.hide()
        self.search_scroll_area.show()
        self._append_search_cards(results)

    def on_load_more_success(self, results):
        if results:
            self._append_search_cards(results)

    def _append_search_cards(self, results):
        icon_color = get_current_theme_color()
        start_index = len(self.search_card_widgets)
        
        self.load_more_spinner.stop()
        self.search_results_layout.removeWidget(self.load_more_spinner)
        self.load_more_spinner.hide()
        
        btn_idx = self.search_results_layout.indexOf(self.load_more_btn)
        if btn_idx == -1:
            for i, entry in enumerate(results):
                card = SearchResultCard(
                    title=entry.get('title'),
                    url=entry.get('url'),
                    uploader=entry.get('uploader'),
                    duration_sec=entry.get('duration'),
                    view_count=entry.get('view_count'),
                    thumbnail_url=entry.get('thumbnail'),
                    download_callback=self.on_search_download_requested,
                    is_playlist=entry.get('is_playlist', False),
                    parent=self.search_results_container
                )
                card.update_icon_colors(icon_color)
                self.search_results_layout.addWidget(card)
                self.search_card_widgets.append(card)
                
                thumb_param = entry.get('thumbnail') or entry.get('id')
                if thumb_param:
                    runnable = ThumbnailRunnable(start_index + i, thumb_param)
                    runnable.signals.thumb_loaded.connect(self.update_search_card_thumbnail)
                    QThreadPool.globalInstance().start(runnable)
                    
            self.search_results_layout.addWidget(self.load_more_btn)
        else:
            for i, entry in enumerate(results):
                card = SearchResultCard(
                    title=entry.get('title'),
                    url=entry.get('url'),
                    uploader=entry.get('uploader'),
                    duration_sec=entry.get('duration'),
                    view_count=entry.get('view_count'),
                    thumbnail_url=entry.get('thumbnail'),
                    download_callback=self.on_search_download_requested,
                    is_playlist=entry.get('is_playlist', False),
                    parent=self.search_results_container
                )
                card.update_icon_colors(icon_color)
                self.search_results_layout.insertWidget(btn_idx, card)
                self.search_card_widgets.append(card)
                btn_idx += 1
                
                thumb_param = entry.get('thumbnail') or entry.get('id')
                if thumb_param:
                    runnable = ThumbnailRunnable(start_index + i, thumb_param)
                    runnable.signals.thumb_loaded.connect(self.update_search_card_thumbnail)
                    QThreadPool.globalInstance().start(runnable)
                    
        self.load_more_btn.show()
        if hasattr(self, '_saved_scroll_val'):
            QTimer.singleShot(50, lambda: self.search_scroll_area.verticalScrollBar().setValue(self._saved_scroll_val))

    def on_search_error(self, err_msg):
        self.load_more_spinner.stop()
        self.search_results_layout.removeWidget(self.load_more_spinner)
        self.load_more_spinner.hide()
        if not self.search_card_widgets:
            self.search_empty_state.hide_loading()
            self.search_empty_state.title_label.setText(
                tr("status_error_prefix", "Error: ") + tr("status_error_conn", "Check connection.")
            )
            if hasattr(self.search_empty_state, 'subtitle_label'):
                self.search_empty_state.subtitle_label.setText(err_msg)
            self.search_empty_state.show()
            self.load_more_btn.hide()
        else:
            self.load_more_btn.show()

    def on_search_finished(self):
        self.url_input.setEnabled(True)
        self.inspect_btn.setEnabled(True)
        self.search_empty_state.hide_loading()
        self.search_worker = None

    def update_search_card_thumbnail(self, index, data):
        if index < len(self.search_card_widgets):
            self.search_card_widgets[index].update_thumbnail(data)

    def on_search_download_requested(self, url, title, thumbnail_pixmap, is_playlist=False):
        if is_playlist:
            dialog = PlaylistSelectionDialog(
                main_app=self.main_app,
                url=url,
                placeholder_title=title,
                placeholder_pixmap=thumbnail_pixmap,
                parent=self
            )
            dialog.exec()
        else:
            dialog = QualitySelectionDialog(
                main_app=self.main_app,
                url=url,
                placeholder_title=title,
                placeholder_pixmap=thumbnail_pixmap,
                parent=self
            )
            dialog.exec()

    def _clear_search_results(self):
        self.search_results_layout.removeWidget(self.load_more_btn)
        self.search_results_layout.removeWidget(self.load_more_spinner)
        while self.search_results_layout.count():
            item = self.search_results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if widget not in (self.load_more_btn, self.load_more_spinner):
                    widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        if sub_item.widget() not in (self.load_more_btn, self.load_more_spinner):
                            sub_item.widget().deleteLater()
        self.search_card_widgets.clear()
        self.load_more_btn.hide()
        self.load_more_spinner.hide()

    # ──────────────────────────── Icons & Theme ──────────────────────────────

    def update_icon_colors(self, icon_color):
        self.package_btn.setIcon(get_colored_icon("assets/icons/package.svg", icon_color))
        if hasattr(self, 'smart_paste_btn') and self.smart_paste_btn:
            self.smart_paste_btn.setIcon(get_colored_icon("assets/icons/clipboard.svg", icon_color))
        elif hasattr(self, 'paste_btn') and self.paste_btn:
            self.paste_btn.setIcon(get_colored_icon("assets/icons/clipboard.svg", icon_color))
        self.inspect_btn.setIcon(get_colored_icon("assets/icons/search-lens.svg", "#ffffff"))
        if hasattr(self, 'download_btn') and self.download_btn:
            self.download_btn.setIcon(QIcon())
        self.empty_state_widget.update_icon_color("assets/icons/search-lens.svg", icon_color)
        self.search_empty_state.update_icon_color("assets/icons/search-lens.svg", icon_color)
        if hasattr(self, 'playlist_widget') and hasattr(self.playlist_widget, 'sub_info_icon'):
            self.playlist_widget.sub_info_icon.setPixmap(get_colored_icon("assets/icons/info.svg", icon_color).pixmap(16, 16))
        for card in self.search_card_widgets:
            card.update_icon_colors(icon_color)
        self.update_guide_theme()

    def update_accent_colors(self):
        if hasattr(self, 'empty_state_widget') and self.empty_state_widget:
            self.empty_state_widget.update_accent_color()
        if hasattr(self, 'search_empty_state') and self.search_empty_state:
            self.search_empty_state.update_accent_color()
        self.update_guide_theme()

    def update_guide_theme(self):
        if not hasattr(self, 'guide_dashboard'):
            return
        is_dark = (self.main_app.theme_manager.get_actual_theme() == "dark")
        accent_hex = self.main_app.theme_manager.get_accent_hex()
        
        card_bg = "#1e293b" if is_dark else "#ffffff"
        border_color = "#334155" if is_dark else "#cbd5e1"
        text_color = "#f8fafc" if is_dark else "#1e293b"
        sub_text_color = "#94a3b8" if is_dark else "#64748b"
        btn_bg = "#0f172a" if is_dark else "#f8fafc"

        if hasattr(self, 'guide_welcome_title'):
            self.guide_welcome_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {text_color};")
        if hasattr(self, 'guide_welcome_sub'):
            self.guide_welcome_sub.setStyleSheet(f"font-size: 13px; color: {sub_text_color};")
            
        if hasattr(self, 'qactions_container'):
            self.qactions_container.setStyleSheet(f"""
                QFrame#QActionsContainer {{
                    background-color: {card_bg};
                    border: 1px solid {border_color};
                    border-radius: 10px;
                    padding: 8px;
                }}
            """)
            
        btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {accent_hex};
                color: {accent_hex};
            }}
        """
        for btn in [getattr(self, 'btn_quick_paste', None), getattr(self, 'btn_quick_search', None), getattr(self, 'btn_quick_settings', None)]:
            if btn:
                btn.setStyleSheet(btn_style)

        bg_card_action = "#131926" if is_dark else "#ffffff"
        border_color_action = "#1e293b" if is_dark else "#e2e8f0"
        text_color_action = "#f1f5f9" if is_dark else "#0f172a"
        
        action_btn_style = f"""
            QPushButton#btn_cancel_inline {{
                background-color: {bg_card_action};
                border: 1px solid {border_color_action};
                border-radius: 8px;
                padding: 8px 16px;
                color: {text_color_action};
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#btn_cancel_inline:hover {{
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #3b82f6;
            }}
            QPushButton#btn_download_inline {{
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#btn_download_inline:hover {{
                background-color: #60a5fa;
            }}
            QPushButton#btn_download_inline:disabled {{
                background-color: {border_color_action};
                color: {sub_text_color};
            }}
        """
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setStyleSheet(action_btn_style)
        if hasattr(self, 'download_btn'):
            self.download_btn.setStyleSheet(action_btn_style)
                
        card_style = f"""
            QFrame#GuideCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QFrame#GuideCard:hover {{
                border: 1px solid {accent_hex};
            }}
        """
        if hasattr(self, 'guide_cards'):
            for card, lbl_icon, lbl_title, lbl_sub, icon_path in self.guide_cards:
                card.setStyleSheet(card_style)
                lbl_title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {text_color}; border: none; background: transparent;")
                lbl_sub.setStyleSheet(f"font-size: 11.5px; color: {sub_text_color}; border: none; background: transparent;")
                icon_color = "#f1f5f9" if is_dark else "#1e293b"
                lbl_icon.setPixmap(get_colored_icon(icon_path, icon_color).pixmap(26, 26))

        if hasattr(self, 'playlist_widget'):
            self.playlist_widget.update_theme()
        if hasattr(self, 'preview_widget'):
            self.preview_widget.update_theme()

    def retranslate_ui(self):
        if hasattr(self, 'url_input'):
            self.url_input.setPlaceholderText(tr("url_placeholder", "Enter URL or search YouTube..."))
        if hasattr(self, 'guide_welcome_title'):
            self.guide_welcome_title.setText(tr("guide_welcome_title", "Welcome to AHS-MediaDL"))
        if hasattr(self, 'guide_welcome_sub'):
            self.guide_welcome_sub.setText(tr("guide_welcome_sub", "The fast and premium media downloader of your choice"))
        if hasattr(self, 'btn_quick_paste'):
            self.btn_quick_paste.setText(tr("quick_action_paste", "📋 Paste & Download"))
        if hasattr(self, 'btn_quick_search'):
            self.btn_quick_search.setText(tr("quick_action_search", "🔍 Search YouTube"))
        if hasattr(self, 'btn_quick_settings'):
            self.btn_quick_settings.setText(tr("quick_action_settings", "⚙️ Open Settings"))
            
        steps = [
            ("assets/icons/clipboard.svg", tr("step_1_title", "1. Copy Link"), tr("step_1_sub", "Copy a video/playlist link from any supported platform")),
            ("assets/icons/search-lens.svg", tr("step_2_title", "2. Paste or Search"), tr("step_2_sub", "Paste link above or enter search query")),
            ("assets/icons/download.svg", tr("step_3_title", "3. Choose & Download"), tr("step_3_sub", "Pick format/quality and click Download"))
        ]
        if hasattr(self, 'guide_cards'):
            for idx, (card, lbl_icon, lbl_title, lbl_sub, icon_path) in enumerate(self.guide_cards):
                if idx < len(steps):
                    _, step_title, step_sub = steps[idx]
                    lbl_title.setText(step_title)
                    lbl_sub.setText(step_sub)

    def show_package_dialog(self):
        dialog = PackagesDialog(self)
        dialog.exec()