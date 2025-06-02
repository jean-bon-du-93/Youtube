import configparser
import os
import logging # Import logging module
import logging.handlers # For RotatingFileHandler

CONFIG_FILE = 'config.ini'
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'twitch_compilation_bot.log')

def setup_logging(log_level_str='INFO'):
    """Configures logging for the application.
    
    Logs to both a rotating file and the console.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Determine log level
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Root logger configuration
    logger = logging.getLogger()
    
    # Clear existing handlers if any (important for re-running in some environments like notebooks)
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(log_level)

    # File Handler (Rotating)
    # Rotates logs, keeping up to 5 backup files of 5MB each.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level) # Set level for file handler

    # Console Handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s: %(message)s') # Simpler format for console
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level) # Or a different level like logging.WARNING for less console noise

    # Add handlers to the root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
            
    logging.info("Logging setup complete. Logging to console and %s at level %s.", LOG_FILE, log_level_str)


def load_config():
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists('config.ini.example'):
            with open('config.ini.example', 'r') as f_example:
                example_content = f_example.read()
            with open(CONFIG_FILE, 'w') as f_config:
                f_config.write(example_content)
            # Use logging here if setup_logging could be called before, otherwise print
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
        'twitch_game_name': config.get('Twitch', 'GAME_NAME', fallback=None),
        
        'youtube_client_secret_file': config.get('YouTube', 'CLIENT_SECRET_FILE', fallback='client_secret.json'),
        'youtube_channel_id': config.get('YouTube', 'CHANNEL_ID', fallback=None),
        'youtube_privacy_status': config.get('YouTube', 'PRIVACY_STATUS', fallback='public'),
        'youtube_video_title_format': config.get('YouTube', 'VIDEO_TITLE_FORMAT', fallback="MEILLEURS CLIPS TWITCH {GAME_NAME_PREFIX}🔥 Compil du Jour n°{X}"),
        'youtube_description_intro': config.get('YouTube', 'DESCRIPTION_INTRO', fallback="Retrouvez les meilleurs moments Twitch de la journée !"),
        'youtube_base_tags': config.get('YouTube', 'BASE_TAGS', fallback="Twitch,Compilation,Gaming,Highlights"),
        'youtube_category_id': config.get('YouTube', 'CATEGORY_ID', fallback="20"),

        'video_resolution': config.get('Video', 'RESOLUTION', fallback='720p'),
        'video_intro_file': config.get('Video', 'INTRO_FILE', fallback=None),
        'video_outro_file': config.get('Video', 'OUTRO_FILE', fallback=None),
        'video_target_duration_minutes': config.getint('Video', 'TARGET_DURATION_MINUTES', fallback=11),
        'video_add_title_bumper': config.getboolean('Video', 'ADD_TITLE_BUMPER', fallback=True),
        'video_title_bumper_text_format': config.get('Video', 'TITLE_BUMPER_TEXT_FORMAT', fallback="COMPIL DU JOUR n°{X}"),
        'video_bumper_duration_seconds': config.getfloat('Video', 'BUMPER_DURATION_SECONDS', fallback=5.0),
        
        # Add log level from config
        'log_level': config.get('General', 'LOG_LEVEL', fallback='INFO')
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
    # Example usage when config.py is run directly
    try:
        app_config = load_config() # Load config first to get log level
        setup_logging(log_level_str=app_config.get('log_level', 'INFO')) # Then setup logging
        logging.info("This is an info message from config.py test run.")
        logging.debug(f"Loaded configuration for test: {app_config}")
        logging.warning("This is a warning message from config.py test run.")
    except (FileNotFoundError, ValueError) as e_config:
        # If config fails, setup basic logging to report this error
        setup_logging() # Use default log level
        logging.error(f"Configuration Error during config.py test run: {e_config}")
    except Exception as e_general:
        setup_logging()
        logging.error(f"An unexpected error occurred during config.py test run: {e_general}", exc_info=True)
