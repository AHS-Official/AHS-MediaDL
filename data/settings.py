import os

DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Downloads')

app_config = {   'allow_downgrade': True,
    'browser_cookies': 'none',
    'concurrent_downloads': 3,
    'custom_path': '',
    'data_saver': False,
    'embed_lyrics': False,
    'embed_subs_default': False,
    'font_family': 'System Default',
    'font_size': 11,
    'language': 'system',
    'last_audio_format': 'm4a-128',
    'last_sub_state': False,
    'last_video_format': 'bestvideo[height<=720]+bestaudio/best',
    'lyrics_format': 'lrc',
    'notifications': True,
    'output_format': 'mp4',
    'primary_sub_lang': 'ar',
    'save_mode': 'auto',
    'secondary_sub_lang': 'en',
    'show_thumbnails': True,
    'speed_limit': '0',
    'subtitle_output_format': 'srt',
    'theme': 'auto',
    'ui_scaling': 'System Default (Auto)',
    'video_container': 'mp4'}

def load_settings():
    return app_config

def save_settings(config_dict):
    import pprint
    global app_config
    app_config.update(config_dict)
    
    file_path = os.path.abspath(__file__)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("app_config = {"):
                start_idx = i
                break
                
        if start_idx != -1:
            end_idx = -1
            bracket_count = 0
            for i in range(start_idx, len(lines)):
                bracket_count += lines[i].count('{') - lines[i].count('}')
                if bracket_count == 0:
                    end_idx = i
                    break
                    
            if end_idx != -1:
                dict_str = "app_config = " + pprint.pformat(app_config, indent=4) + "\n"
                new_lines = lines[:start_idx] + [dict_str] + lines[end_idx+1:]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
    except Exception as e:
        print(f"Error saving settings to file: {e}")
