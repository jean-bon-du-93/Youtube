import logging # Import logging at the top
from config import load_config, setup_logging # Added setup_logging
from utils import get_compilation_number, increment_compilation_number, generate_youtube_video_title 
from twitch_utils import get_twitch_access_token, get_top_twitch_clips
from video_utils import download_clip, create_compilation, cleanup_temp_clips
from youtube_utils import get_youtube_service, upload_video_to_youtube

def main():
    app_config = None 
    # --- Setup Logging (early as possible) ---
    try:
        app_config = load_config()
        setup_logging(log_level_str=app_config.get('log_level', 'INFO')) 
    except (FileNotFoundError, ValueError) as e:
        setup_logging() 
        logging.error(f"Configuration Error: {e}")
        logging.error("Please ensure 'config.ini' is correctly set up with actual values.")
        return 
    except Exception as e:
        setup_logging() 
        logging.error(f"A critical error occurred during initial setup: {e}", exc_info=True)
        return

    logging.info("Application started.")
    logging.debug(f"Loaded configuration: {app_config}")

    twitch_token = None
    valid_clips = [] 
    downloaded_clip_paths = []
    successfully_downloaded_clip_infos = [] 
    compilation_output_path = None
    youtube_video_title = None
    youtube_video_description = None 
    youtube_video_tags = []        

    try:
        current_comp_num = get_compilation_number()
        logging.info(f"Current compilation number: {current_comp_num}")

        # --- Twitch Authentication ---
        if app_config: # Should always be true here due to early exit, but good practice
            logging.info("Attempting Twitch authentication...")
            twitch_token = get_twitch_access_token(
                app_config['twitch_client_id'],
                app_config['twitch_client_secret']
            )
            if twitch_token:
                logging.info("Successfully obtained Twitch token.")
            else:
                logging.error("Failed to obtain Twitch token. Check credentials and network. Exiting.")
                return
        else: # Should not be reached
            logging.error("Configuration not loaded. Exiting.")
            return
        
        # --- Fetch Twitch Clips ---
        if twitch_token and app_config:
            logging.info("Attempting to fetch Twitch clips...")
            period_str = app_config.get('twitch_clip_period', 'last_24_hours')
            try:
                period_hours = int(period_str.split('_')[1])
            except (IndexError, ValueError) as e:
                logging.warning(f"Invalid format for twitch_clip_period ('{period_str}'). Defaulting to 24 hours. Error: {e}")
                period_hours = 24

            clips_data_from_twitch = get_top_twitch_clips( 
                access_token=twitch_token,
                client_id=app_config['twitch_client_id'],
                game_id=app_config.get('twitch_game_id'),
                language=app_config.get('twitch_clip_language'),
                period_hours=period_hours,
                count=100 
            )
            
            if clips_data_from_twitch:
                logging.info(f"Successfully fetched {len(clips_data_from_twitch)} clip(s) initially from Twitch API.")
                valid_clips = [clip for clip in clips_data_from_twitch if clip.get('download_url')]
                logging.info(f"Found {len(valid_clips)} clips with a valid download URL.")
                if not valid_clips:
                    logging.warning("No clips with valid download URLs found. Cannot proceed. Exiting.")
                    return
            else:
                logging.warning("No clips fetched from Twitch. Check criteria or API response. Exiting.")
                return
        
        # --- Download Clips ---
        if valid_clips:
            logging.info(f"Attempting to download {len(valid_clips)} clips...")
            for clip_info in valid_clips: 
                logging.info(f"  Downloading clip: {clip_info.get('title', 'N/A')} (ID: {clip_info.get('id')})")
                file_path = download_clip(clip_info) 
                if file_path:
                    downloaded_clip_paths.append(file_path)
                    successfully_downloaded_clip_infos.append(clip_info) 
                    logging.info(f"  Successfully downloaded to: {file_path}")
                else:
                    logging.warning(f"  Failed to download clip: {clip_info.get('title', 'N/A')}. Skipping.")
            
            if not downloaded_clip_paths:
                logging.error("No clips were successfully downloaded. Cannot create a compilation. Exiting.")
                return
            else:
                logging.info(f"Successfully downloaded {len(downloaded_clip_paths)} out of {len(valid_clips)} initially selected clips.")
        else:
            logging.error("No valid clips were available to download. Exiting.") 
            return

        # --- Create Video Compilation ---
        if downloaded_clip_paths and app_config:
            logging.info(f"Proceeding to video compilation with {len(downloaded_clip_paths)} clips.")
            
            next_comp_num_for_filename = current_comp_num + 1 
            output_comp_filename = f"compilation_jour_n{next_comp_num_for_filename}.mp4"
            
            target_duration_seconds = int(app_config.get('video_target_duration_minutes', 11)) * 60
            resolution_str = app_config.get('video_resolution', '720p')
            add_transitions = app_config.get('video_add_transitions', True) 
            transition_duration = app_config.get('video_transition_duration', 1.0) 

            bumper_text = None
            bumper_duration = 0.0 
            if app_config.get('video_add_title_bumper', True): 
                bumper_text_format = app_config.get('video_title_bumper_text_format', "COMPIL DU JOUR n°{X}")
                game_name_for_bumper = app_config.get('twitch_game_name') 
                next_comp_num_for_title = current_comp_num + 1
                bumper_text = bumper_text_format.replace("{X}", str(next_comp_num_for_title))
                if "{GAME_NAME}" in bumper_text: 
                    if game_name_for_bumper: bumper_text = bumper_text.replace("{GAME_NAME}", game_name_for_bumper)
                    else: bumper_text = bumper_text.replace("\n{GAME_NAME}", "").replace("{GAME_NAME}", "")
                elif "{GAME_NAME_PREFIX}" in bumper_text: 
                     if game_name_for_bumper: bumper_text = bumper_text.replace("{GAME_NAME_PREFIX}", game_name_for_bumper.upper() + " ")
                     else: bumper_text = bumper_text.replace("{GAME_NAME_PREFIX}", "")
                bumper_duration = app_config.get('video_bumper_duration_seconds', 5.0)
                logging.info(f"Generated bumper text: '{bumper_text}' for {bumper_duration}s")

            compilation_output_path = create_compilation(
                clip_file_paths=downloaded_clip_paths, output_filename=output_comp_filename,
                target_duration_seconds=target_duration_seconds, resolution_str=resolution_str,
                add_transitions=add_transitions, transition_duration=transition_duration,
                title_bumper_text=bumper_text, bumper_duration=bumper_duration
            )

            if compilation_output_path:
                logging.info(f"Video compilation created successfully: {compilation_output_path}")
                next_comp_num_for_yt_title = current_comp_num + 1
                game_name_for_yt_title = app_config.get('twitch_game_name')
                title_format_from_config = app_config.get('youtube_video_title_format')
                youtube_video_title = generate_youtube_video_title(
                    compilation_number=next_comp_num_for_yt_title, game_name=game_name_for_yt_title,
                    title_format=title_format_from_config
                )
                logging.info(f"Generated YouTube Video Title: {youtube_video_title}")

                description_intro = app_config.get('youtube_description_intro', "Retrouvez les meilleurs moments Twitch de la journée !")
                streamer_credits = ["Clips par :"]
                if successfully_downloaded_clip_infos:
                    for clip_data in successfully_downloaded_clip_infos:
                        creator = clip_data.get('creator_name', 'N/A')
                        twitch_url = clip_data.get('twitch_clip_url', '')
                        if twitch_url: streamer_credits.append(f"[{creator}]({twitch_url})")
                        else: streamer_credits.append(creator) 
                    description_credits_text = "\n".join(streamer_credits)
                    youtube_video_description = f"{description_intro}\n\n{description_credits_text}"
                else: youtube_video_description = description_intro
                logging.info(f"Generated YouTube Description (first 100 chars):\n{youtube_video_description[:100]}...")

                base_tags_str = app_config.get('youtube_base_tags', "Twitch,Compilation,Gaming,Highlights")
                youtube_tags = [tag.strip() for tag in base_tags_str.split(',') if tag.strip()]
                game_name_for_tags = app_config.get('twitch_game_name')
                if game_name_for_tags: youtube_tags.append(game_name_for_tags)
                streamer_names_for_tags = set()
                if successfully_downloaded_clip_infos:
                    for clip_data in successfully_downloaded_clip_infos:
                        creator = clip_data.get('creator_name')
                        if creator: streamer_names_for_tags.add(creator.replace(" ", ""))
                youtube_tags.extend(list(streamer_names_for_tags))
                youtube_tags = youtube_tags[:30] 
                logging.info(f"Generated YouTube Tags: {youtube_tags}")
            else:
                logging.error("Video compilation failed. Exiting.")
                return
        else:
            logging.error("No downloaded clips available to compile, or config missing. Exiting.")
            return

        # --- YouTube Upload ---
        if compilation_output_path and youtube_video_title and app_config:
            logging.info("Attempting YouTube Upload...")
            youtube_service = get_youtube_service(client_secrets_file=app_config['youtube_client_secret_file'])
            
            if youtube_service:
                video_id = upload_video_to_youtube(
                    youtube_service=youtube_service, file_path=compilation_output_path,
                    title=youtube_video_title, description=youtube_video_description,
                    tags=youtube_tags, category_id=app_config.get('youtube_category_id', "20"),
                    privacy_status=app_config.get('youtube_privacy_status', "private")
                )
                if video_id:
                    logging.info(f"Successfully uploaded video to YouTube! Video ID: {video_id}")
                    logging.info("Performing Post-Publication Tasks...")
                    new_comp_num = increment_compilation_number(current_comp_num)
                    logging.info(f"Compilation counter incremented to: {new_comp_num}")
                    cleanup_temp_clips() 
                    logging.info(f"SUCCESS! Compilation {new_comp_num} published: https://www.youtube.com/watch?v={video_id}")
                else:
                    logging.error("YouTube upload failed.")
            else:
                logging.error("Failed to get YouTube service. Cannot upload video.")
        else:
            logging.warning("Not enough data to proceed with YouTube upload (missing video path, title, or config).")
        
    except Exception as e: 
        logging.error(f"An unexpected error occurred in main operation: {e}", exc_info=True)
    
    logging.info("Application finished.")

if __name__ == '__main__':
    main()
