# Twitch Compilation Bot

This Python script automates the creation and publication of daily video compilations to YouTube, based on popular clips from Twitch.

## Features

*   Fetches top clips from Twitch based on configurable criteria (game, language, period).
*   Downloads the selected clips.
*   Compiles the downloaded clips into a single video file using MoviePy.
    *   Supports custom video resolution (e.g., 720p, 1080p).
    *   Optional: Adds crossfade transitions between clips.
    *   Optional: Adds a customizable text bumper at the beginning of the video.
*   Generates dynamic video titles, descriptions (including streamer credits), and tags for YouTube.
*   Authenticates with YouTube (OAuth 2.0) and uploads the compiled video.
*   Manages a compilation counter to number daily compilations.
*   Configurable via an external `config.ini` file.
*   Logs operational details to both console and a rotating log file (`logs/twitch_compilation_bot.log`).

## Prerequisites

*   **Python 3.7+**
*   **FFmpeg**: Required by MoviePy for video processing. Ensure FFmpeg is installed and accessible in your system's PATH.
    *   You can download it from [ffmpeg.org](https://ffmpeg.org/download.html).
*   **ImageMagick** (Optional, but recommended for `TextClip` font rendering): MoviePy's `TextClip` feature may rely on ImageMagick for font handling and text rendering, especially for custom fonts or complex text.
    *   Install from [imagemagick.org](https://imagemagick.org/script/download.php).
    *   You might also need to configure ImageMagick's policy file (`policy.xml`) to allow text rendering if you encounter issues.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    # If this were a git repo:
    # git clone <repository_url>
    # cd <repository_directory>
    # For now, just ensure all files are in the same directory.
    ```

2.  **Install Dependencies:**
    Create a virtual environment (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
    Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Twitch API Credentials:**
    *   Go to the [Twitch Developer Console](https://dev.twitch.tv/console/).
    *   Register a new application (Category: "Application Integration" or similar).
    *   You will get a **Client ID** and **Client Secret**.
    *   You do not need to set an OAuth Redirect URL for this script as it uses App Access Tokens (Client Credentials Flow) for Twitch.

4.  **YouTube API Credentials:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project (or select an existing one).
    *   Enable the **"YouTube Data API v3"** for your project.
        *   Search for "YouTube Data API v3" in the API Library and enable it.
    *   Create OAuth 2.0 credentials:
        *   Go to "Credentials" in the APIs & Services section.
        *   Click "Create Credentials" -> "OAuth client ID".
        *   Choose "Desktop app" as the Application type.
        *   Give it a name (e.g., "TwitchCompilationBot").
        *   After creation, download the JSON file. Rename this file to `client_secret.json` and place it in the root directory of the project (alongside `main.py`).
    *   **Important**: The first time you run the script, you will be prompted to authorize the application through your web browser. This will create a `token.json` file in the project directory, which stores your OAuth tokens for future runs.

5.  **Configure the Bot:**
    *   Rename `config.ini.example` to `config.ini`.
    *   Open `config.ini` and fill in the required values:
        *   **[Twitch]**
            *   `CLIENT_ID`: Your Twitch application's Client ID.
            *   `CLIENT_SECRET`: Your Twitch application's Client Secret.
            *   `GAME_ID` (Optional): ID of a specific game/category on Twitch (e.g., `509658` for "Just Chatting"). Find Game IDs using the [Twitch API documentation](https://dev.twitch.tv/docs/api/reference/#get-games) or external tools. If blank, fetches from all categories.
            *   `GAME_NAME` (Optional): A readable name for the game specified in `GAME_ID` (e.g., "Just Chatting"). Used for video titles/tags.
            *   `CLIP_LANGUAGE` (Optional): Language code for clips (e.g., "en", "fr").
            *   `CLIP_PERIOD`: How far back to look for clips (e.g., `last_24_hours`, `last_7_days`).
        *   **[YouTube]**
            *   `CLIENT_SECRET_FILE`: Path to your YouTube client secrets JSON file (default: `client_secret.json`).
            *   `CHANNEL_ID`: Your YouTube Channel ID where videos will be uploaded. (Find this in your YouTube account settings or advanced settings).
            *   `PRIVACY_STATUS`: Privacy for uploaded videos (`public`, `private`, or `unlisted`). **Default is `private` for safety.**
            *   `CATEGORY_ID`: YouTube video category ID (e.g., `20` for Gaming, `22` for People & Blogs).
            *   `VIDEO_TITLE_FORMAT`: Format string for the YouTube video title. Placeholders: `{X}` for compilation number, `{GAME_NAME_PREFIX}` for the game name (e.g., "FORTNITE ").
            *   `DESCRIPTION_INTRO`: Default introductory text for the YouTube video description.
            *   `BASE_TAGS`: Comma-separated list of default tags for YouTube videos.
        *   **[Video]**
            *   `RESOLUTION`: Target video resolution (`720p` or `1080p`).
            *   `TARGET_DURATION_MINUTES`: Approximate target duration for the compilation in minutes.
            *   `ADD_TITLE_BUMPER`: `True` or `False` to enable/disable the title bumper.
            *   `TITLE_BUMPER_TEXT_FORMAT`: Format string for the bumper text. Placeholders: `{X}` for number, `{GAME_NAME}` for game name.
            *   `BUMPER_DURATION_SECONDS`: Duration of the title bumper.
        *   **[General]**
            *   `LOG_LEVEL`: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

## Running the Script

1.  Ensure your virtual environment is activated (if you created one).
2.  Make sure `config.ini` is correctly filled out.
3.  Run the main script:
    ```bash
    python main.py
    ```
4.  **First YouTube Run**: The first time you run it, your web browser will open, asking you to log in to your Google account and authorize the script to manage your YouTube videos. After successful authorization, a `token.json` file will be created, and the script will continue. Subsequent runs will use this token file automatically.

## Log Files

*   Log files are stored in the `logs/` directory (e.g., `logs/twitch_compilation_bot.log`).
*   The log file rotates when it reaches 5MB, keeping up to 5 backup files.

## How it Works

1.  **Configuration**: Loads settings from `config.ini`.
2.  **Compilation Number**: Reads the current compilation number from `compilation_counter.txt`.
3.  **Twitch API**: Fetches top clips using your Twitch app credentials.
4.  **Download**: Downloads the MP4 files of these clips into `temp_clips/`.
5.  **Video Compilation**: Uses MoviePy to:
    *   Create a title bumper (if enabled).
    *   Concatenate the downloaded clips.
    *   Apply transitions (if enabled).
    *   Resize to the target resolution.
    *   The final video is saved in the `compilations/` folder (e.g., `compilations/compilation_jour_n123.mp4`).
6.  **YouTube Metadata**: Generates the video title, description (including credits to streamers), and tags.
7.  **YouTube Upload**: Authenticates with YouTube using OAuth 2.0 and uploads the compiled video.
8.  **Post-Upload**:
    *   Increments the compilation number in `compilation_counter.txt`.
    *   Cleans up the downloaded clips from the `temp_clips/` folder.

## Troubleshooting

*   **MoviePy/FFmpeg Errors**: Ensure FFmpeg is installed and in your system's PATH. Errors like "ffmpeg returned error code 1" often point to an FFmpeg issue or specific video file incompatibility.
*   **MoviePy TextClip/ImageMagick Errors**: If `TextClip` fails (e.g., "Font not found", "Policy not allowing text"), ensure ImageMagick is installed and its `policy.xml` allows text rendering. You might need to specify a full path to a `.ttf` font file in `video_utils.py` if default fonts aren't working.
*   **YouTube Quota Errors**: The YouTube Data API v3 has daily quotas. If you upload many videos or run the script frequently, you might hit these limits. Check your Google Cloud Console for quota usage.
*   **Authentication Issues**:
    *   **Twitch**: Double-check your Client ID and Secret in `config.ini`.
    *   **YouTube**: Ensure `client_secret.json` is correct and from a project with YouTube Data API v3 enabled. If `token.json` becomes corrupted, delete it and re-run the script to re-authorize.
```
