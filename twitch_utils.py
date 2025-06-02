import requests
import time
import os
from datetime import datetime, timedelta, timezone

# To store the access token and its expiry time
TWITCH_ACCESS_TOKEN = None
TWITCH_TOKEN_EXPIRY_TIME = 0
# A small buffer (in seconds) before the actual expiry to request a new token
TOKEN_EXPIRY_BUFFER = 60 

# Environment variables for credentials for security (alternative to config file for this part)
# However, the plan specifies config file, so we'll primarily rely on passed arguments.
# CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
# CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')

def get_twitch_access_token(client_id: str, client_secret: str):
    """
    Fetches a Twitch App Access Token or returns a cached one if still valid.

    Args:
        client_id (str): Your Twitch application's Client ID.
        client_secret (str): Your Twitch application's Client Secret.

    Returns:
        str: The App Access Token, or None if an error occurs.
    """
    global TWITCH_ACCESS_TOKEN, TWITCH_TOKEN_EXPIRY_TIME

    current_time = time.time()

    # Check if a valid token exists and is not about to expire
    if TWITCH_ACCESS_TOKEN and current_time < (TWITCH_TOKEN_EXPIRY_TIME - TOKEN_EXPIRY_BUFFER):
        print("Using cached Twitch access token.")
        return TWITCH_ACCESS_TOKEN

    if not client_id or not client_secret:
        print("Error: Twitch Client ID or Client Secret is missing.")
        return None

    token_url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    try:
        response = requests.post(token_url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        data = response.json()
        TWITCH_ACCESS_TOKEN = data.get('access_token')
        expires_in = data.get('expires_in')

        if not TWITCH_ACCESS_TOKEN:
            print(f"Error: Could not retrieve access token from Twitch. Response: {data}")
            return None
        
        if expires_in:
            TWITCH_TOKEN_EXPIRY_TIME = current_time + expires_in
            print(f"New Twitch access token obtained. Expires in: {expires_in} seconds.")
        else:
            # If expires_in is not provided, set a default long expiry (e.g. 60 days)
            # Twitch app access tokens typically last around 60 days.
            TWITCH_TOKEN_EXPIRY_TIME = current_time + (60 * 24 * 60 * 60) 
            print("New Twitch access token obtained. Expiry time not explicitly provided by API, assuming long duration.")

        return TWITCH_ACCESS_TOKEN

    except requests.exceptions.RequestException as e:
        print(f"Error during Twitch authentication request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Twitch authentication: {e}")
        return None

def get_top_twitch_clips(access_token: str, client_id: str, game_id: str = None, broadcaster_id: str = None, language: str = None, period_hours: int = 24, count: int = 100):
    """
    Fetches top Twitch clips based on specified criteria.

    Args:
        access_token (str): Valid Twitch App Access Token.
        client_id (str): Your Twitch application's Client ID.
        game_id (str, optional): ID of the game to filter clips by. Defaults to None (all games).
        broadcaster_id (str, optional): ID of the broadcaster to filter clips by. Defaults to None.
                                        (Note: The API can fetch for EITHER game_id OR broadcaster_id, not both simultaneously for top clips in general)
        language (str, optional): Language code (e.g., "en", "fr") to filter clips. Defaults to None.
        period_hours (int, optional): How far back to look for clips, in hours. Defaults to 24.
        count (int, optional): Number of clips to fetch (max 100). Defaults to 100.

    Returns:
        list: A list of dictionaries, where each dictionary contains details of a clip.
                Returns an empty list if an error occurs or no clips are found.
                Clip details include: 'id', 'title', 'creator_name', 'twitch_clip_url', 
                                    'download_url', 'view_count', 'duration', 'game_id', 'language', 'created_at'.
    """
    if not access_token or not client_id:
        print("Error: Missing access_token or client_id for fetching clips.")
        return []

    clips_url = 'https://api.twitch.tv/helix/clips'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Client-Id': client_id
    }

    # Calculate the start time for fetching clips
    start_time_dt = datetime.now(timezone.utc) - timedelta(hours=period_hours)
    started_at = start_time_dt.isoformat()

    params = {
        'first': min(max(1, count), 100), # Ensure count is between 1 and 100
        'started_at': started_at
    }

    if broadcaster_id:
        params['broadcaster_id'] = broadcaster_id
    elif game_id: # API prefers one or the other for general queries, not both.
        params['game_id'] = game_id
    # If neither broadcaster_id nor game_id is provided, it fetches top clips across Twitch.

    if language:
        params['language'] = language # Note: Twitch API documentation for clips doesn't explicitly list language as a request parameter.
                                    # This might require filtering after fetching if the API doesn't support it directly.
                                    # For now, we include it and will rely on API behavior or post-filtering.

    print(f"Fetching clips with params: {params}")

    try:
        response = requests.get(clips_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        clips_data = data.get('data', [])
        if not clips_data:
            print("No clips found matching the criteria.")
            return []

        processed_clips = []
        for clip_info in clips_data:
            thumbnail_url = clip_info.get('thumbnail_url')
            download_url = None
            if thumbnail_url:
                # Transform thumbnail URL to MP4 URL:
                # Example: https://clips-media-assets2.twitch.tv/AT-cm%7C123-preview-480x272.jpg 
                # Becomes: https://clips-media-assets2.twitch.tv/AT-cm%7C123.mp4
                download_url = thumbnail_url.split('-preview-')[0] + '.mp4'
            
            # If language was a query param and API filtered, great. 
            # If not, and language is specified, we might need to filter here.
            # For now, assume API handles it or we accept what API returns matching other criteria.
            if language and clip_info.get('language') != language:
                # This post-filtering might be necessary if the API's language param is not effective for 'clips' endpoint
                # print(f"Skipping clip due to language mismatch: expected {language}, got {clip_info.get('language')}")
                continue


            processed_clips.append({
                'id': clip_info.get('id'),
                'title': clip_info.get('title'),
                'creator_name': clip_info.get('broadcaster_name'), # broadcaster_name is streamer name
                'twitch_clip_url': clip_info.get('url'),
                'download_url': download_url,
                'view_count': clip_info.get('view_count'),
                'duration': clip_info.get('duration'), # Duration in seconds
                'game_id': clip_info.get('game_id'),
                'language': clip_info.get('language'),
                'created_at': clip_info.get('created_at')
            })
        
        # Sort by view_count in descending order
        processed_clips.sort(key=lambda x: x.get('view_count', 0), reverse=True)

        return processed_clips

    except requests.exceptions.RequestException as e:
        print(f"Error during Twitch clips request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during clip processing: {e}")
        return []

if __name__ == '__main__':
    # Example Usage:
    # To run this test, you would need to have valid Twitch Client ID and Secret.
    # You can temporarily hardcode them here for testing, or set them as environment variables
    # if you adapt the code to read them (not part of current task).
    # For this subtask, we assume client_id and client_secret are passed from main.py (via config)
    
    # Simulate getting credentials from config (as would happen in main.py)
    # Replace with your actual test credentials if you want to run this directly
    # IMPORTANT: Do not commit real credentials to the repository.
    TEST_CLIENT_ID = "YOUR_TEST_TWITCH_CLIENT_ID"  # Replace for local testing
    TEST_CLIENT_SECRET = "YOUR_TEST_TWITCH_CLIENT_SECRET" # Replace for local testing

    if TEST_CLIENT_ID == "YOUR_TEST_TWITCH_CLIENT_ID" or TEST_CLIENT_SECRET == "YOUR_TEST_TWITCH_CLIENT_SECRET":
        print("Please replace placeholder TEST_CLIENT_ID and TEST_CLIENT_SECRET in twitch_utils.py for testing.")
        print("Skipping direct test of get_twitch_access_token.")
    else:
        print("Attempting to get Twitch access token...")
        token = get_twitch_access_token(TEST_CLIENT_ID, TEST_CLIENT_SECRET)
        if token:
            print(f"Access Token: {token[:20]}...") # Print first 20 chars for verification
            print("Attempting to get token again (should use cache)...")
            token2 = get_twitch_access_token(TEST_CLIENT_ID, TEST_CLIENT_SECRET)
            if token2:
                print(f"Second Token: {token2[:20]}...")
                assert token == token2, "Tokens should match if cache is working!"
            else:
                print("Failed to get token the second time.")
        else:
            print("Failed to get access token.")
    
    print("\n--- Testing get_top_twitch_clips ---")
    TEST_CLIENT_ID_CLIPS = "YOUR_TEST_TWITCH_CLIENT_ID"  # Replace for local testing
    TEST_CLIENT_SECRET_CLIPS = "YOUR_TEST_TWITCH_CLIENT_SECRET" # Replace for local testing
    
    if TEST_CLIENT_ID_CLIPS == "YOUR_TEST_TWITCH_CLIENT_ID" or TEST_CLIENT_SECRET_CLIPS == "YOUR_TEST_TWITCH_CLIENT_SECRET":
        print("Please replace placeholder credentials for clip testing in twitch_utils.py.")
        print("Skipping direct test of get_top_twitch_clips.")
    else:
        print("Attempting to get Twitch access token for clip testing...")
        test_token = get_twitch_access_token(TEST_CLIENT_ID_CLIPS, TEST_CLIENT_SECRET_CLIPS)
        if test_token:
            print(f"Access Token obtained: {test_token[:20]}...")
            
            # Example: Get top 5 clips for "Just Chatting" (game_id='509658') in English from last 48 hours
            print("\nFetching top clips (Just Chatting, EN, last 48h, top 5)...")
            clips = get_top_twitch_clips(
                access_token=test_token,
                client_id=TEST_CLIENT_ID_CLIPS,
                game_id='509658', # Just Chatting
                language='en',
                period_hours=48,
                count=5
            )
            
            if clips:
                print(f"Found {len(clips)} clips:")
                for i, clip in enumerate(clips):
                    print(f"  Clip {i+1}:")
                    print(f"    Title: {clip['title']}")
                    print(f"    Creator: {clip['creator_name']}")
                    print(f"    Views: {clip['view_count']}")
                    print(f"    Duration: {clip['duration']}s")
                    print(f"    Download URL: {clip['download_url']}")
                    print(f"    Twitch URL: {clip['twitch_clip_url']}")
                    print(f"    Game ID: {clip['game_id']}")
                    print(f"    Language: {clip['language']}")
            else:
                print("No clips found for the criteria.")

            # Example: Get top 3 clips overall (no game_id, no language specified) from last 24 hours
            print("\nFetching top clips (Overall, last 24h, top 3)...")
            overall_clips = get_top_twitch_clips(
                access_token=test_token,
                client_id=TEST_CLIENT_ID_CLIPS,
                period_hours=24,
                count=3
            )
            if overall_clips:
                print(f"Found {len(overall_clips)} overall clips:")
                for i, clip in enumerate(overall_clips):
                    print(f"  Clip {i+1}: {clip['title']} by {clip['creator_name']} (Views: {clip['view_count']})")
            else:
                print("No overall clips found.")
        else:
            print("Failed to get access token, cannot test get_top_twitch_clips.")
