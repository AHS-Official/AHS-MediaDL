import os
import json
from utils.helpers import get_app_dir

DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Downloads')
CONFIG_FILE = os.path.join(get_app_dir(), "config.json")

default_config = {
    "language": "system",
    "save_mode": "auto",
    "custom_path": DEFAULT_DOWNLOAD_PATH,
    "notifications": True,
    "data_saver": False,
    "show_thumbnails": True,
    "allow_downgrade": True,
    "theme": "auto",
    "speed_limit": "0",
    "concurrent_downloads": 1,
    "browser_cookies": "none",
    "last_video_format": "bestvideo[height<=1080]+bestaudio/best",
    "last_audio_format": "mp3-128",
    "last_sub_state": False,
    "font_family": "system", 
    "font_size": 12,
    "window_width": 700,
    "window_height": 650,
    "embed_subs_default": True,
    "primary_sub_lang": "ar",
    "secondary_sub_lang": "en"
}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                for key in default_config:
                    if key not in loaded:
                        loaded[key] = default_config[key]
                return loaded
        except:
            return default_config.copy()
    return default_config.copy()

def save_settings(config_dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=4)

app_config = load_settings()