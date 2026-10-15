from utils.logger import logger
import os
from datetime import datetime

class NotificationManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.notifications_list = []
        self.has_unread_notifications = False

    def add_notification(self, title, message, tray_icon=None, icon=None):
        now_str = datetime.now().strftime("%I:%M %p")
        self.notifications_list.insert(0, {
            "title": title,
            "message": message,
            "time": now_str,
            "read": False
        })
        self.has_unread_notifications = True
        
        # Check if system tray notifications are enabled
        if self.settings.get("notifications", True) and tray_icon is not None:
            try:
                from PyQt6.QtWidgets import QSystemTrayIcon
                from PyQt6.QtGui import QIcon, QPixmap
                from utils.helpers import resource_path
                
                qicon = None
                if icon is not None:
                    if isinstance(icon, QPixmap) and not icon.isNull():
                        qicon = QIcon(icon)
                    elif isinstance(icon, QIcon) and not icon.isNull():
                        qicon = icon
                
                if qicon is None or qicon.isNull():
                    icon_path = resource_path(os.path.join('assets', 'icon.ico'))
                    if os.path.exists(icon_path):
                        qicon = QIcon(icon_path)
                    else:
                        qicon = QSystemTrayIcon.MessageIcon.Information

                # Show system notification with video thumbnail image
                tray_icon.showMessage(
                    title,
                    message,
                    qicon,
                    5000
                )
            except Exception as e:
                logger.warning(f"Error showing tray message: {e}")

    def get_notifications(self):
        return self.notifications_list

    def clear_notifications(self):
        self.notifications_list.clear()
        self.has_unread_notifications = False

    def has_unread(self):
        return self.has_unread_notifications

    def mark_all_read(self):
        for item in self.notifications_list:
            item["read"] = True
        self.has_unread_notifications = False
