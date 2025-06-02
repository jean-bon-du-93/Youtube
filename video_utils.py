import requests
import os
import re # For sanitizing filenames
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip # Added imports
# It's good practice to handle potential moviepy import errors if it's optional
# but for this project, it's a core requirement.

TEMP_DOWNLOAD_FOLDER = 'temp_clips'
COMPILATIONS_FOLDER = 'compilations' # Folder for final videos

def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    # Remove invalid characters
    sanitized = re.sub(r'[\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    # Truncate if too long (OS limits vary, 200 is generally safe for parts of the name)
    return sanitized[:200]

def download_clip(clip_info: dict, download_folder: str = TEMP_DOWNLOAD_FOLDER):
    """
    Downloads a single clip to the specified folder.

    Args:
        clip_info (dict): A dictionary containing clip details, including 
                            'download_url', 'id', 'creator_name', and 'title'.
        download_folder (str, optional): The folder to download clips to. 
                                        Defaults to TEMP_DOWNLOAD_FOLDER.

    Returns:
        str: The local file path of the downloaded clip, or None if download failed.
    """
    if not clip_info or not clip_info.get('download_url'):
        print("Error: Invalid clip_info or missing download_url.")
        return None

    download_url = clip_info['download_url']
    
    # Create a somewhat descriptive filename
    # Using clip ID for uniqueness, creator and title for readability
    clip_id = clip_info.get('id', 'unknown_id')
    creator_name = sanitize_filename(clip_info.get('creator_name', 'unknown_creator'))
    title_part = sanitize_filename(clip_info.get('title', 'untitled'))
    
    # Ensure filename is not excessively long
    filename = f"{clip_id}_{creator_name}_{title_part}.mp4"
    if len(filename) > 255: # Max filename length on some systems
        filename = f"{clip_id}_{creator_name[:50]}_{title_part[:50]}.mp4"


    if not os.path.exists(download_folder):
        try:
            os.makedirs(download_folder)
            print(f"Created temporary download folder: {download_folder}")
        except OSError as e:
            print(f"Error creating download folder {download_folder}: {e}")
            return None
    
    file_path = os.path.join(download_folder, filename)

    print(f"Attempting to download: {clip_info.get('title', 'N/A')} from {download_url} to {file_path}")

    try:
        response = requests.get(download_url, stream=True, timeout=30) # Added timeout
        response.raise_for_status() # Check for HTTP errors

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully downloaded {filename}")
        return file_path
    
    except requests.exceptions.Timeout:
        print(f"Error: Timeout while trying to download {filename} from {download_url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading clip {filename} from {download_url}: {e}")
        if os.path.exists(file_path): # Clean up partially downloaded file
            os.remove(file_path)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while downloading {filename}: {e}")
        if os.path.exists(file_path): # Clean up
            os.remove(file_path)
        return None

if __name__ == '__main__':
    print("--- Testing download_clip (requires a direct MP4 URL) ---")
    # This test requires a publicly accessible MP4 URL.
    # Replace with a real, short MP4 URL for testing.
    # For example, a short sample video.
    # IMPORTANT: Using a real Twitch clip URL obtained from previous steps would be ideal
    # but that requires running the full auth and fetch flow.
    
    # Example clip_info (replace with actual data if possible, or a test MP4)
    # To make this test runnable, you'd need a direct link to an MP4 file.
    # Many "sample MP4" files are available online for testing.
    # e.g., find one at https://file-examples.com/index.php/sample-video-files/sample-mp4-files/
    
    # Using a placeholder structure for clip_info
    sample_clip_info_valid = {
        'id': 'testclip001',
        'download_url': 'https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4', # Replace with a working sample MP4 URL
        'creator_name': 'TestStreamer',
        'title': 'My Awesome Test Clip Title With Special Chars /*?:"<>|'
    }
    sample_clip_info_invalid_url = {
        'id': 'testclip002',
        'download_url': 'https://invalid.url/clip.mp4',
        'creator_name': 'ErrorMan',
        'title': 'NonExistentClip'
    }
    sample_clip_info_no_url = {
        'id': 'testclip003',
        'creator_name': 'NoUrlMan',
        'title': 'ClipWithoutUrl'
    }

    if sample_clip_info_valid['download_url'] == 'https_sample_videos_com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4'.replace("_","//"): # crude check for placeholder
        print("Please replace the placeholder 'download_url' in video_utils.py's test section with a real MP4 URL to run the download test.")
    else:
        print("\nTesting with a valid sample MP4 URL...")
        downloaded_path = download_clip(sample_clip_info_valid)
        if downloaded_path:
            print(f"Test clip downloaded to: {downloaded_path}")
            # To be a good citizen, delete the test file after download
            # if os.path.exists(downloaded_path):
            #     os.remove(downloaded_path)
            #     print(f"Cleaned up: deleted {downloaded_path}")
        else:
            print("Test clip download failed.")

    print("\nTesting with an invalid URL...")
    download_clip(sample_clip_info_invalid_url)
    
    print("\nTesting with missing URL...")
    download_clip(sample_clip_info_no_url)

    # Test sanitize_filename (can be run without network)
    print("\n--- Testing sanitize_filename ---")
    test_filenames = [
        "normal_filename.mp4",
        "filename with spaces.mp4",
        "file/with/slashes.mp4",
           "file*with?invalid<chars>:\"|pipe.mp4",
        "a_very_long_filename_that_might_exceed_system_limits_and_needs_to_be_truncated_properly_to_avoid_errors_when_saving_the_file_to_the_disk_this_is_just_a_test_to_see_how_it_handles_it.mp4"
    ]
    for tf in test_filenames:
        print(f"Original: '{tf}' -> Sanitized: '{sanitize_filename(tf)}'")

def parse_resolution(resolution_str="720p"):
    """Parses a resolution string like "720p" or "1080p" into (width, height)."""
    if resolution_str == "1080p":
        return (1920, 1080)
    elif resolution_str == "720p":
        return (1280, 720)
    else: # Default to 720p if unknown
        print(f"Unknown resolution string: {resolution_str}. Defaulting to 720p.")
        return (1280, 720)

def create_compilation(
    clip_file_paths: list, 
    output_filename: str, 
    target_duration_seconds: int = 11 * 60, 
    resolution_str: str = "720p",
    # Optional: intro_file_path: str = None, 
    # Optional: outro_file_path: str = None,
    # Optional: add_transitions: bool = False
    ):
    """
    Creates a video compilation from a list of clip file paths.

    Args:
        clip_file_paths (list): List of paths to the downloaded video clips.
        output_filename (str): The desired name for the output file (e.g., "compilation_123.mp4").
                                It will be saved in the COMPILATIONS_FOLDER.
        target_duration_seconds (int, optional): Target duration for the compilation in seconds. 
                                                Defaults to 11 minutes (660 seconds).
        resolution_str (str, optional): Desired resolution ("720p" or "1080p"). Defaults to "720p".
        # intro_file_path (str, optional): Path to an intro video.
        # outro_file_path (str, optional): Path to an outro video.
        # add_transitions (bool, optional): Whether to add crossfade transitions (not implemented in this version).


    Returns:
        str: The full path to the created compilation video, or None if an error occurred.
    """
    if not clip_file_paths:
        print("Error: No clip file paths provided for compilation.")
        return None

    target_width, target_height = parse_resolution(resolution_str)
    
    processed_clips = []
    current_total_duration = 0
    final_compilation_obj = None


    # Optional: Load intro clip
    # if intro_file_path and os.path.exists(intro_file_path):
    #     try:
    #         intro_clip = VideoFileClip(intro_file_path).resize(width=target_width) # Or height=target_height
    #         # Consider aspect ratio if intro isn't 16:9
    #         processed_clips.append(intro_clip)
    #         current_total_duration += intro_clip.duration
    #     except Exception as e:
    #         print(f"Error loading intro clip {intro_file_path}: {e}")


    for clip_path in clip_file_paths:
        if not os.path.exists(clip_path):
            print(f"Warning: Clip file not found: {clip_path}. Skipping.")
            continue
        
        clip = None # Initialize clip variable for this scope
        try:
            clip = VideoFileClip(clip_path)
            
            # Resize if necessary, maintaining aspect ratio
            if clip.h != target_height or clip.w != target_width:
                print(f"Resizing clip {os.path.basename(clip_path)} from {clip.size} to target height {target_height} (maintaining aspect ratio).")
                clip_resized = clip.resize(height=target_height)
                clip.close() # Close original clip
                clip = clip_resized # Assign resized clip to current clip variable
                
                if clip.w != target_width:
                    # If width is still not matching after height resize (clip aspect ratio not 16:9)
                    # Center it on a black background of target_width x target_height
                    print(f"Centering clip {os.path.basename(clip_path)} on a {target_width}x{target_height} background.")
                    centered_clip = CompositeVideoClip([clip.set_position("center")], size=(target_width, target_height))
                    # Note: CompositeVideoClip does not need explicit close for the 'clip' passed if 'clip' is managed separately
                    clip = centered_clip # The new 'clip' is the CompositeVideoClip


            if processed_clips and (current_total_duration + clip.duration > target_duration_seconds + 30) and current_total_duration >= target_duration_seconds * 0.8:
                print(f"Adding clip {os.path.basename(clip_path)} (duration: {clip.duration}s) would exceed target duration significantly. Stopping here.")
                if hasattr(clip, 'close') and callable(clip.close): # Ensure it's a closable clip object
                    clip.close() 
                break 
            
            processed_clips.append(clip)
            current_total_duration += clip.duration
            print(f"Added clip: {os.path.basename(clip_path)}, new total duration: {current_total_duration:.2f}s")

            if current_total_duration >= target_duration_seconds:
                print("Target duration reached or exceeded.")
                break
        
        except Exception as e:
            print(f"Error processing clip {clip_path}: {e}. Skipping.")
            if clip and hasattr(clip, 'close') and callable(clip.close): # Ensure clip object exists and close it
                clip.close()


    # Optional: Load outro clip
    # if outro_file_path and os.path.exists(outro_file_path):
    #     try:
    #         outro_clip = VideoFileClip(outro_file_path).resize(width=target_width)
    #         processed_clips.append(outro_clip)
    #         current_total_duration += outro_clip.duration
    #     except Exception as e:
    #         print(f"Error loading outro clip {outro_file_path}: {e}")

    if not processed_clips:
        print("Error: No clips were successfully processed for the compilation.")
        return None

    try:
        # Note: If CompositeVideoClips were used for centering, they are already composed.
        # concatenate_videoclips will put them one after another.
        final_compilation_obj = concatenate_videoclips(processed_clips, method="compose")
        
        if not os.path.exists(COMPILATIONS_FOLDER):
            os.makedirs(COMPILATIONS_FOLDER)
        
        full_output_path = os.path.join(COMPILATIONS_FOLDER, output_filename)

        print(f"Writing final compilation to: {full_output_path} (Duration: {final_compilation_obj.duration:.2f}s)")
        ffmpeg_params = ['-crf', '23'] 
        final_compilation_obj.write_videofile(
            full_output_path, 
            codec="libx264", 
            audio_codec="aac",
            preset="medium", 
            ffmpeg_params=ffmpeg_params,
            threads=4 
        )
        print("Compilation written successfully.")
        return full_output_path

    except Exception as e:
        print(f"Error during final video concatenation or writing: {e}")
        return None
    finally:
        for clip_obj in processed_clips:
            if hasattr(clip_obj, 'close') and callable(clip_obj.close):
                clip_obj.close()
        if final_compilation_obj and hasattr(final_compilation_obj, 'close') and callable(final_compilation_obj.close):
            final_compilation_obj.close()


if __name__ == '__main__':
    # ... (keep existing test code for download_clip and sanitize_filename) ...
    print("\n--- Testing create_compilation (requires actual video files) ---")
    
    # To test this, you need some sample MP4 files in TEMP_DOWNLOAD_FOLDER
    # For example, create a few short dummy MP4 files or use the output from download_clip test if it worked.
    # Let's assume 'temp_clips' exists and has some .mp4 files from previous steps or manual placement.
    
    if not os.path.exists(TEMP_DOWNLOAD_FOLDER):
        os.makedirs(TEMP_DOWNLOAD_FOLDER)
    
    sample_clips_for_compilation = []
    
    # Example: try to find any mp4 files in temp_clips
    if os.path.exists(TEMP_DOWNLOAD_FOLDER):
        for item in os.listdir(TEMP_DOWNLOAD_FOLDER):
            if item.endswith(".mp4"):
                item_path = os.path.join(TEMP_DOWNLOAD_FOLDER, item)
                try:
                    # Test if it's a valid video file by trying to get its duration with MoviePy
                    with VideoFileClip(item_path) as test_clip_obj: # Use 'with' for automatic close
                        if test_clip_obj.duration > 0: 
                            sample_clips_for_compilation.append(item_path)
                except Exception as e_test_clip:
                    print(f"Could not read {item_path} as a video (or file is invalid/empty): {e_test_clip}, skipping for test.")
                if len(sample_clips_for_compilation) >= 3: 
                    break
    
    if not sample_clips_for_compilation:
        print("No valid sample MP4 files found in 'temp_clips/' to test compilation.")
        print(f"Please add some .mp4 files to '{TEMP_DOWNLOAD_FOLDER}' and ensure they are valid video files.")
        # You could add a dummy clip creation here for basic testing if MoviePy is confirmed installed:
        # dummy_file = os.path.join(TEMP_DOWNLOAD_FOLDER, "dummy_test_clip.mp4")
        # if not os.path.exists(dummy_file):
        #     try:
        #         from moviepy.editor import ColorClip
        #         ColorClip(size=(1280, 720), color=(0,0,0), duration=1).write_videofile(dummy_file, codec="libx264", fps=25)
        #         sample_clips_for_compilation.append(dummy_file)
        #         print("Created a dummy_test_clip.mp4 for testing.")
        #     except Exception as e_dummy:
        #         print(f"Could not create dummy clip for testing: {e_dummy}")
        # else:
        #    # If dummy file exists from a previous run, consider adding it
        #    try:
        #        with VideoFileClip(dummy_file) as test_clip_obj:
        #             if test_clip_obj.duration > 0: sample_clips_for_compilation.append(dummy_file)
        #    except: pass


    if sample_clips_for_compilation:
        print(f"Found {len(sample_clips_for_compilation)} sample clips for testing compilation: {sample_clips_for_compilation}")
        output_comp_path = create_compilation(
            clip_file_paths=sample_clips_for_compilation,
            output_filename="test_compilation_output.mp4",
            target_duration_seconds=10, 
            resolution_str="720p"
        )
        if output_comp_path:
            print(f"Test compilation created successfully: {output_comp_path}")
            # if os.path.exists(output_comp_path): # Clean up test file
            #     os.remove(output_comp_path)
            #     print(f"Cleaned up test compilation: {output_comp_path}")
        else:
            print("Test compilation failed.")
    else:
        print("Skipping compilation test as no valid sample clips were provided or found.")
