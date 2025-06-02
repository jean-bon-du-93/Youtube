from config import load_config
from utils import get_compilation_number
from twitch_utils import get_twitch_access_token, get_top_twitch_clips
from video_utils import download_clip # Added import

def main():
    app_config = None
    twitch_token = None
    valid_clips = [] # Initialize to avoid issues if prior steps fail

    try:
        app_config = load_config()
        print("Configuration loaded in main.py.")

        current_comp_num = get_compilation_number()
        print(f"Current compilation number: {current_comp_num}")

        # --- Twitch Authentication ---
        if app_config:
            print("Attempting Twitch authentication...")
            twitch_token = get_twitch_access_token(
                app_config['twitch_client_id'],
                app_config['twitch_client_secret']
            )
            if twitch_token:
                print(f"Successfully obtained Twitch token.")
            else:
                print("Failed to obtain Twitch token. Check credentials and network. Exiting.")
                return
        else:
            print("Configuration not loaded. Exiting.")
            return
        
        # --- Fetch Twitch Clips ---
        if twitch_token and app_config:
            print("\nAttempting to fetch Twitch clips...")
            # Convert twitch_clip_period (e.g., "last_24_hours") to int
            period_str = app_config.get('twitch_clip_period', 'last_24_hours')
            try:
                period_hours = int(period_str.split('_')[1])
            except (IndexError, ValueError) as e:
                print(f"Warning: Invalid format for twitch_clip_period ('{period_str}'). Defaulting to 24 hours. Error: {e}")
                period_hours = 24

            clips = get_top_twitch_clips(
                access_token=twitch_token,
                client_id=app_config['twitch_client_id'],
                game_id=app_config.get('twitch_game_id'),
                language=app_config.get('twitch_clip_language'),
                period_hours=period_hours,
                count=100 
            )
            
            if clips:
                print(f"Successfully fetched {len(clips)} clip(s) initially.")
                valid_clips = [clip for clip in clips if clip.get('download_url')]
                print(f"Found {len(valid_clips)} clips with a valid download URL.")
                if not valid_clips:
                    print("No clips with valid download URLs found. Cannot proceed. Exiting.")
                    return
            else:
                print("No clips fetched from Twitch. Check criteria or API response. Exiting.")
                return
        
        # --- Download Clips ---
        downloaded_clip_paths = []
        if valid_clips: # Proceed only if there are clips to download
            print(f"\nAttempting to download {len(valid_clips)} clips...")
            for clip_info in valid_clips:
                print(f"  Downloading clip: {clip_info.get('title', 'N/A')} (ID: {clip_info.get('id')})")
                file_path = download_clip(clip_info) # Uses default temp_clips folder
                if file_path:
                    downloaded_clip_paths.append(file_path)
                    print(f"  Successfully downloaded to: {file_path}")
                else:
                    print(f"  Failed to download clip: {clip_info.get('title', 'N/A')}. Skipping.")
            
            if not downloaded_clip_paths:
                print("\nNo clips were successfully downloaded. Cannot create a compilation. Exiting.")
                return
            else:
                print(f"\nSuccessfully downloaded {len(downloaded_clip_paths)} out of {len(valid_clips)} initially selected clips.")
                # For now, just print the paths
                # print("Downloaded clip paths:")
                # for path in downloaded_clip_paths:
                #     print(f"  - {path}")
        else:
            # This case should ideally be caught earlier, but as a safeguard:
            print("No valid clips were available to download. Exiting.")
            return
        # --- End Download Clips ---

        # ... rest of your application logic (video compilation, YouTube upload) will follow here ...
        if downloaded_clip_paths:
             print(f"\nProceeding to video compilation with {len(downloaded_clip_paths)} clips.")


    except (FileNotFoundError, ValueError) as e: # Specifically for config errors
        print(f"Configuration Error: {e}")
        print("Please ensure 'config.ini' is correctly set up with actual values.")
        return
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
        # import traceback # Uncomment for detailed debugging
        # print(traceback.format_exc()) # Uncomment for detailed debugging
        return

if __name__ == '__main__':
    main()
