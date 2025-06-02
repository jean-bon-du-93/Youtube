import configparser
import os

CONFIG_FILE = 'config.ini'

def load_config():
    config = configparser.ConfigParser()
    
    # Create config.ini from example if it doesn't exist
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists('config.ini.example'):
            with open('config.ini.example', 'r') as f_example:
                example_content = f_example.read()
            with open(CONFIG_FILE, 'w') as f_config:
                f_config.write(example_content)
            print(f"'{CONFIG_FILE}' not found. Copied from 'config.ini.example'. Please fill in your details.")
        else:
            raise FileNotFoundError(f"'{CONFIG_FILE}' and 'config.ini.example' not found. Please create a '{CONFIG_FILE}'.")

    config.read(CONFIG_FILE)
    
    settings = {
        'twitch_client_id': config.get('Twitch', 'CLIENT_ID', fallback=None),
        'twitch_client_secret': config.get('Twitch', 'CLIENT_SECRET', fallback=None),
        'twitch_game_id': config.get('Twitch', 'GAME_ID', fallback=None),
        'twitch_clip_language': config.get('Twitch', 'CLIP_LANGUAGE', fallback=None),
        'twitch_clip_period': config.get('Twitch', 'CLIP_PERIOD', fallback='last_24_hours'),
        
        'youtube_client_secret_file': config.get('YouTube', 'CLIENT_SECRET_FILE', fallback='client_secret.json'),
        'youtube_channel_id': config.get('YouTube', 'CHANNEL_ID', fallback=None),
        'youtube_privacy_status': config.get('YouTube', 'PRIVACY_STATUS', fallback='public'),

        'video_resolution': config.get('Video', 'RESOLUTION', fallback='720p'),
        'video_intro_file': config.get('Video', 'INTRO_FILE', fallback=None),
        'video_outro_file': config.get('Video', 'OUTRO_FILE', fallback=None),
    }

    # Validate required fields
    if not settings['twitch_client_id'] or settings['twitch_client_id'] == 'YOUR_TWITCH_CLIENT_ID':
        raise ValueError("Twitch CLIENT_ID is not set in config.ini")
    if not settings['twitch_client_secret'] or settings['twitch_client_secret'] == 'YOUR_TWITCH_CLIENT_SECRET':
        raise ValueError("Twitch CLIENT_SECRET is not set in config.ini")
    if not settings['youtube_channel_id'] or settings['youtube_channel_id'] == 'YOUR_YOUTUBE_CHANNEL_ID':
        raise ValueError("YouTube CHANNEL_ID is not set in config.ini")
        
    return settings

if __name__ == '__main__':
    # Example usage
    try:
        app_config = load_config()
        print("Configuration loaded successfully:")
        for key, value in app_config.items():
            print(f"  {key}: {value}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading configuration: {e}")
