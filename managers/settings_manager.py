import os
import json
import time
import shutil
from PyQt6.QtCore import QObject, pyqtSignal
from utils.helpers import get_data_path
from utils.logger import logger

class SettingsManager(QObject):
    _instance = None
    _initialized = False

    setting_changed = pyqtSignal(str, object)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, parent=None):
        if self.__class__._initialized:
            return
        super().__init__(parent)
        self.__class__._initialized = True

        self.settings_file = get_data_path(os.path.join('data', 'settings.json'))
        self.defaults = {
            "last_save_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
            "language": "system",
            "notifications": True,
            "show_thumbnails": True,
            "theme": "auto",
            "accent_theme": "orange",
            "font_family": "System Default",
            "scaling": "auto",
            "font_size": 12,
            "download_path_type": "downloads",
            "custom_path": "",
            "speed_limit_type": "unlimited",
            "custom_speed_value": 100,
            "custom_speed_unit": "KB",
            "concurrent_type": "3",
            "custom_concurrent_value": 3,
            "mix_playlist_limit": 50,
            "primary_sub_lang": "ar",
            "secondary_sub_lang": "en",
            "download_any_sub_fallback": True,
            "video_container": "mp4",
            "embed_subtitles": True,
            "autoplay_subtitles": True,
            "external_sub_format": "srt",
            "audio_sub_format": "lrc",
            "embed_audio_sub": True,
            "audio_container": "mp3",
            "quality_fallback": True,
            "first_launch": True,
            "run_in_background": True,
            "clipboard_monitor": True,
            "auto_collect_links": True,
            "cookies_type": "none",
            "custom_cookies_path": "",
            "remember_format_choice": False,
            "saved_format_choice": "",
            "collected_links": [],
            "all_time_rx": 0
        }
        self.data = {}
        self._last_mtime = 0.0
        self.load()

    def _sync_if_modified_externally(self):
        """يحدث البيانات في الذاكرة إذا تم تعديل الملف من عملية أخرى (مثل النافذة الرئيسية والـ Listener)."""
        try:
            if os.path.exists(self.settings_file):
                mtime = os.path.getmtime(self.settings_file)
                if mtime > self._last_mtime:
                    self.load()
        except OSError:
            pass

    def load(self):
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        if not os.path.exists(self.settings_file):
            self.data = dict(self.defaults)
            self.save_data(self.data)
            return
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                self.data = dict(self.defaults)
                if isinstance(loaded_data, dict):
                    self.data.update(loaded_data)
                self._last_mtime = os.path.getmtime(self.settings_file)
                return
            except json.JSONDecodeError as e:
                logger.error(f"Settings file corrupted, backing up: {e}")
                bak_file = self.settings_file + ".bak"
                try:
                    shutil.copy2(self.settings_file, bak_file)
                except Exception:
                    pass
                self.data = dict(self.defaults)
                return
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                else:
                    logger.error(f"Permission denied reading settings after retries: {e}")
                    if not self.data:
                        self.data = dict(self.defaults)
                    return
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
                if not self.data:
                    self.data = dict(self.defaults)
                return

    def get(self, key, default=None):
        self._sync_if_modified_externally()
        if default is None:
            default = self.defaults.get(key)
        return self.data.get(key, default)

    def set(self, key, value, save_immediately=True):
        old_val = self.data.get(key)
        self.data[key] = value
        if save_immediately:
            self.save()
        if old_val != value:
            self.setting_changed.emit(key, value)

    def set_many(self, updates_dict):
        """تحديث عدة إعدادات دفعة واحدة وحفظها على القرص في عملية كتابة واحدة فقط."""
        changed_items = []
        for key, value in updates_dict.items():
            old_val = self.data.get(key)
            self.data[key] = value
            if old_val != value:
                changed_items.append((key, value))
        self.save()
        for key, value in changed_items:
            self.setting_changed.emit(key, value)

    def get_all(self):
        self._sync_if_modified_externally()
        return self.data

    def save_data(self, data):
        try:
            tmp_file = self.settings_file + '.tmp'
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    with open(tmp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.flush()
                        os.fsync(f.fileno())
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.2)
                    else:
                        raise
                        
            for attempt in range(max_retries):
                try:
                    os.replace(tmp_file, self.settings_file)
                    self._last_mtime = os.path.getmtime(self.settings_file)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.2)
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def save(self):
        self.save_data(self.data)

    def reset_to_defaults(self):
        self.data = dict(self.defaults)
        self.save()