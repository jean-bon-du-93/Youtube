# In youtube_utils.py
import os
import pickle # For older google-auth versions, might be json for newer
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload # Added for video upload
import time # For resumable upload retry logic

# Path to store the token (pickle or json format depending on library version)
# google-auth > 2.0.0 uses token.json, older versions might use token.pickle
TOKEN_FILE = 'token.json' 
# Scopes required for YouTube video upload
YOUTUBE_API_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

def get_youtube_service(client_secrets_file: str):
    """
    Authenticates with the YouTube API using OAuth 2.0 and returns a service object.

    Handles token storage and refresh. Requires user interaction for the first run.

    Args:
        client_secrets_file (str): Path to the client_secret.json file obtained
                                   from Google Cloud Console.

    Returns:
        A Google API client service object for YouTube, or None if authentication fails.
    """
    if not os.path.exists(client_secrets_file):
        print(f"Error: YouTube client secrets file not found at '{client_secrets_file}'.")
        print("Please download it from Google Cloud Console and place it correctly.")
        return None

    creds = None
    # The TOKEN_FILE stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        try:
            # For google-auth library version >= 2.0.0 (uses JSON)
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, YOUTUBE_API_SCOPES)
        except Exception as e: # Broad exception for potential format issues (e.g. old pickle)
            print(f"Error loading token from {TOKEN_FILE}: {e}. Will try to re-authenticate.")
            creds = None # Ensure creds is None to trigger re-auth
            # Optionally, delete the problematic token file:
            # try:
            #     os.remove(TOKEN_FILE)
            #     print(f"Removed problematic token file: {TOKEN_FILE}")
            # except OSError:
            #     pass


    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing YouTube access token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing YouTube access token: {e}")
                print("User may need to re-authorize. Deleting old token file if it exists.")
                if os.path.exists(TOKEN_FILE):
                    try:
                        os.remove(TOKEN_FILE)
                    except OSError as del_err:
                        print(f"Error deleting token file {TOKEN_FILE}: {del_err}")
                creds = None # Force re-authentication
        else:
            print("YouTube credentials not found or invalid, initiating OAuth flow...")
            print(f"Please follow the authentication prompts from your browser for YouTube access.")
            print(f"Ensure '{client_secrets_file}' is correctly configured.")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, YOUTUBE_API_SCOPES)
                # Instruct user about the local server for the OAuth flow
                # The default method runs a local server.
                # For environments without a browser or display, alternative methods might be needed,
                # but InstalledAppFlow is standard for command-line tools.
                creds = flow.run_local_server(port=0) 
            except FileNotFoundError:
                print(f"Critical Error: The client_secrets_file '{client_secrets_file}' was not found during flow creation, though it was checked earlier.")
                return None
            except Exception as e:
                print(f"Error during YouTube OAuth flow: {e}")
                # import traceback; traceback.print_exc(); # For detailed error
                return None
        
        # Save the credentials for the next run
        if creds:
            try:
                with open(TOKEN_FILE, 'w') as token_f:
                    token_f.write(creds.to_json()) # For google-auth >= 2.0.0
                print(f"YouTube credentials saved to {TOKEN_FILE}")
            except Exception as e:
                print(f"Error saving YouTube credentials to {TOKEN_FILE}: {e}")

    if not creds:
        print("Failed to obtain YouTube credentials.")
        return None
    
    try:
        youtube_service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)
        print("YouTube service created successfully.")
        return youtube_service
    except Exception as e:
        print(f"Error building YouTube service: {e}")
        return None

def upload_video_to_youtube(
    youtube_service, 
    file_path: str, 
    title: str, 
    description: str, 
    tags: list, 
    category_id: str = "20", # "20" is Gaming
    privacy_status: str = "private", # Default to private for safety; can be "public" or "unlisted"
    # channel_id: str = None # channel_id is not directly used in videos().insert for the authenticated user.
                            # Uploads go to the authenticated user's channel.
                            # For specifying a brand account, ensure the OAuth token has right permissions.
    retries: int = 3,
    retry_delay_seconds: int = 60 # Delay for resumable upload retries
    ):
    """
    Uploads a video file to YouTube.

    Args:
        youtube_service: Authorized YouTube API service object.
        file_path (str): Path to the video file to upload.
        title (str): Title of the video.
        description (str): Description of the video.
        tags (list): A list of tags (strings) for the video.
        category_id (str, optional): Category ID for the video. Defaults to "20" (Gaming).
        privacy_status (str, optional): Privacy status ("public", "private", "unlisted"). 
                                        Defaults to "private".
        retries (int, optional): Number of times to retry upload on resumable errors.
        retry_delay_seconds (int, optional): Seconds to wait before retrying.


    Returns:
        str: The ID of the uploaded video, or None if upload failed.
    """
    if not os.path.exists(file_path):
        print(f"Error: Video file not found at '{file_path}'. Cannot upload.")
        return None

    try:
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False # Default to not made for kids
            }
        }

        print(f"Initiating YouTube upload for: {title}")
        print(f"  File: {file_path}")
        print(f"  Privacy: {privacy_status}, Category: {category_id}")

        media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        # The resumable upload is handled by the Google API client library.
        # It will automatically retry on intermittent network issues.
        # We add a manual retry loop for specific error types if needed,
        # but generally, the library's resumable capabilities are robust.
        
        request = youtube_service.videos().insert(
            part=",".join(body.keys()), # snippet,status
            body=body,
            media_body=media_body
        )

        response = None
        current_retry = 0
        while response is None:
            try:
                print("Uploading chunk...")
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")
                if response:
                    print(f"Upload successful! Video ID: {response.get('id')}")
                    return response.get('id')
            except Exception as e: # Catches resumable upload errors like HttpError, BrokenPipeError etc.
                current_retry += 1
                if current_retry > retries:
                    print(f"Upload failed after {retries} retries.")
                    print(f"Last error during upload: {e}")
                    return None # Failed after retries
                
                print(f"Error during upload: {e}. Retrying ({current_retry}/{retries}) in {retry_delay_seconds}s...")
                time.sleep(retry_delay_seconds)
                # Re-establish request for retry if needed, but library often handles this.
                # If using simple request.execute() without chunks, this manual loop is more critical.
                # With request.next_chunk(), the library manages retry state better.

    except Exception as e:
        print(f"An unexpected error occurred setting up the YouTube upload: {e}")
        # import traceback; traceback.print_exc() # For detailed error
        return None
    
    return None # Should be returned from within loop on success or after retries


if __name__ == '__main__':
    # This test requires a 'client_secret.json' file to be present.
    # The user will be prompted to authenticate via browser on the first run.
    print("--- Testing YouTube Authentication ---")
    
    # Create a dummy client_secret.json for testing if it doesn't exist
    # IMPORTANT: For actual use, the user MUST provide their own client_secret.json
    CLIENT_SECRET_FILE_FOR_TEST = 'client_secret.json' # Or 'test_client_secret.json'
    if not os.path.exists(CLIENT_SECRET_FILE_FOR_TEST):
        print(f"Warning: '{CLIENT_SECRET_FILE_FOR_TEST}' not found for testing.")
        print("To test YouTube authentication, you need a valid client_secret.json from Google Cloud Console.")
        print("This test will likely fail or prompt for a non-existent file if you proceed without it.")
        # You could create a placeholder to see the error:
        # with open(CLIENT_SECRET_FILE_FOR_TEST, 'w') as f:
        #     f.write('{"installed":{"client_id":"DUMMY","project_id":"DUMMY","auth_uri":"https_DUMMY","token_uri":"https_DUMMY","auth_provider_x509_cert_url":"https_DUMMY","client_secret":"DUMMY","redirect_uris":["http://localhost"]}}')
        # print(f"Created a DUMMY '{CLIENT_SECRET_FILE_FOR_TEST}'. The auth flow will fail but test the path.")
    
    # Remove token.json before testing if you want to force re-authentication
    # if os.path.exists(TOKEN_FILE):
    #     os.remove(TOKEN_FILE)
    #     print(f"Removed existing {TOKEN_FILE} for fresh authentication test.")

    youtube_service_auth_test = get_youtube_service(client_secrets_file=CLIENT_SECRET_FILE_FOR_TEST) # Renamed variable for clarity
    if youtube_service_auth_test:
        print("Successfully obtained YouTube service object for auth test.")
    else:
        print("Failed to obtain YouTube service object for auth test.")
    print("Ensure you have your actual 'client_secret.json' from Google Cloud Console for the script to work for auth.")

    print("\n--- Testing YouTube Video Upload (Conceptual) ---")
    # This test is conceptual as it requires:
    # 1. Successful authentication (a valid token.json from previous get_youtube_service run).
    # 2. A valid video file to upload.
    # 3. The user to have their YouTube Data API v3 quota available.

    # To run this test:
    # a) Ensure client_secret.json is present and you've authenticated at least once.
    # b) Create a dummy video file, e.g., 'dummy_video.mp4'.
    #    (You can create a very short one with moviepy or ffmpeg if you want a real file)
    
    DUMMY_VIDEO_FILE = 'dummy_video_for_upload_test.mp4'

    if not os.path.exists(TOKEN_FILE):
        print(f"{TOKEN_FILE} not found. Please run the authentication part of the test first (get_youtube_service).")
    elif not os.path.exists(DUMMY_VIDEO_FILE):
        print(f"Dummy video file '{DUMMY_VIDEO_FILE}' not found. Please create a small MP4 file for testing.")
        print(f"Example: Create a short video, or copy one to this path.")
        # To create a dummy file for testing structure (not a real video):
        # with open(DUMMY_VIDEO_FILE, 'w') as f: f.write("dummy video content")
    else:
        print("Attempting to get YouTube service for upload test...")
        # Use the same variable name 'youtube' as the function expects, or pass explicitly
        youtube_service_upload_test = get_youtube_service(client_secrets_file=CLIENT_SECRET_FILE_FOR_TEST)
        if youtube_service_upload_test:
            print("YouTube service obtained. Attempting to upload conceptual dummy video...")
            video_id = upload_video_to_youtube(
                youtube_service=youtube_service_upload_test,
                file_path=DUMMY_VIDEO_FILE,
                title="Test Upload - Dummy Video",
                description="This is a test video uploaded by a Python script. Please ignore/delete.",
                tags=["test", "python", "api_upload"],
                category_id="22", # People & Blogs (less restrictive than Gaming sometimes for tests)
                privacy_status="private" # IMPORTANT: Keep private for tests
            )
            if video_id:
                print(f"Conceptual upload test SUCCEEDED. Video ID: {video_id}")
                print(f"Check your YouTube studio for the private video: https://www.youtube.com/watch?v={video_id}")
            else:
                print("Conceptual upload test FAILED.")
        else:
            print("Failed to get YouTube service, cannot test upload.")
    print("Remember to delete any test videos uploaded to YouTube.")
