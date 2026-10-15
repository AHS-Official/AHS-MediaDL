from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from utils.locales import tr
from utils.theme import get_accent_hex
from utils.helpers import get_colored_icon, get_current_theme_color

class UIManager:
    def __init__(self, main_window):
        self.mw = main_window

    def toggle_sidebar(self):
        icon_color = get_current_theme_color()
        accent_color = get_accent_hex()
        is_rtl = (self.mw.layoutDirection() == Qt.LayoutDirection.RightToLeft)

        target_width = 60 if self.mw.sidebar_expanded else 215
        start_width = self.mw.sidebar.width()

        self.mw.sidebar_anim = QPropertyAnimation(self.mw.sidebar, b"minimumWidth")
        self.mw.sidebar_anim.setDuration(220)
        self.mw.sidebar_anim.setStartValue(start_width)
        self.mw.sidebar_anim.setEndValue(target_width)
        self.mw.sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.mw.sidebar_max_anim = QPropertyAnimation(self.mw.sidebar, b"maximumWidth")
        self.mw.sidebar_max_anim.setDuration(220)
        self.mw.sidebar_max_anim.setStartValue(start_width)
        self.mw.sidebar_max_anim.setEndValue(target_width)
        self.mw.sidebar_max_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        if self.mw.sidebar_expanded:
            self.mw.logo_text.hide()
            self.mw.header_spacer.hide()
            self.mw.btn_menu.hide()
            self.mw.btn_nav_home.setText("")
            self.mw.btn_nav_downloads.setText("")
            self.mw.btn_nav_history.setText("")
            self.mw.btn_nav_settings.setText("")
            self.mw.lbl_logo.setToolTip("MediaDL — Click to expand")
            self.mw.sidebar_expanded = False
        else:
            self.mw.logo_text.show()
            self.mw.header_spacer.show()
            self.mw.btn_menu.show()
            self.mw.btn_nav_home.setText(tr("nav_home"))
            self.mw.btn_nav_downloads.setText(tr("nav_downloads"))
            self.mw.btn_nav_history.setText(tr("nav_history"))
            self.mw.btn_nav_settings.setText(tr("nav_settings"))
            collapse_icon = "expand.svg" if is_rtl else "collapse.svg"
            self.mw.btn_menu.setIcon(get_colored_icon(f"assets/icons/{collapse_icon}", icon_color))
            self.mw.lbl_logo.setToolTip("")
            self.mw.sidebar_expanded = True

        self.mw._refresh_nav_icons()
        self.mw.sidebar_anim.start()
        self.mw.sidebar_max_anim.start()

    def fade_widget_transition(self, stack_widget, target_index):
        if stack_widget.currentIndex() == target_index:
            return
        target_widget = stack_widget.widget(target_index)
        if not target_widget:
            return
        effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(effect)
        stack_widget.setCurrentIndex(target_index)
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(300)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        if not hasattr(self.mw, '_transitions'):
            self.mw._transitions = []
        self.mw._transitions = [a for a in self.mw._transitions if a.state() != QPropertyAnimation.State.Stopped]
        def on_finished(w=target_widget):
            w.setGraphicsEffect(None)
        animation.finished.connect(on_finished)
        self.mw._transitions.append(animation)
        animation.start()

    def change_page(self, index, animate=True):
        if index == 3:
            if animate:
                self.fade_widget_transition(self.mw.main_stack, 1)
            else:
                self.mw.main_stack.setCurrentIndex(1)
            self.mw.btn_nav_settings.setChecked(True)
            self.mw.btn_nav_home.setChecked(False)
            self.mw.btn_nav_downloads.setChecked(False)
            self.mw.btn_nav_history.setChecked(False)
        else:
            if animate:
                self.fade_widget_transition(self.mw.main_stack, 0)
                self.fade_widget_transition(self.mw.pages_stack, index)
            else:
                self.mw.main_stack.setCurrentIndex(0)
                self.mw.pages_stack.setCurrentIndex(index)
            self.mw.btn_nav_home.setChecked(index == 0)
            self.mw.btn_nav_downloads.setChecked(index == 1)
            self.mw.btn_nav_history.setChecked(index == 2)
            self.mw.btn_nav_settings.setChecked(False)
            if hasattr(self.mw, 'page_title_lbl'):
                if index == 0:
                    self.mw.page_title_lbl.setText(tr("nav_home"))
                elif index == 1:
                    self.mw.page_title_lbl.setText(tr("nav_downloads"))
                elif index == 2:
                    self.mw.page_title_lbl.setText(tr("nav_history"))
            if index == 2 and hasattr(self.mw, 'page_history'):
                self.mw.page_history.load_history_ui()
        self.mw._refresh_nav_icons()

    def run_sidebar_teaser_animation(self):
        start_width = self.mw.sidebar.width()
        target_width = start_width - 15
        
        self.mw.teaser_anim1 = QPropertyAnimation(self.mw.sidebar, b"minimumWidth")
        self.mw.teaser_anim1.setDuration(200)
        self.mw.teaser_anim1.setStartValue(start_width)
        self.mw.teaser_anim1.setEndValue(target_width)
        self.mw.teaser_anim1.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.mw.teaser_anim2 = QPropertyAnimation(self.mw.sidebar, b"minimumWidth")
        self.mw.teaser_anim2.setDuration(400)
        self.mw.teaser_anim2.setStartValue(target_width)
        self.mw.teaser_anim2.setEndValue(start_width)
        self.mw.teaser_anim2.setEasingCurve(QEasingCurve.Type.OutElastic)
        
        self.mw.teaser_anim1.finished.connect(self.mw.teaser_anim2.start)
        self.mw.teaser_anim1.start()
