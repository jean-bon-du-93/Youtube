import requests
import os
import re
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip # Added TextClip
from moviepy.video.compositing.transitions import crossfadein

TEMP_DOWNLOAD_FOLDER = 'temp_clips'
COMPILATIONS_FOLDER = 'compilations'

def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    sanitized = re.sub(r'[\/*?:"<>|]', "", filename)
    sanitized = sanitized.replace(" ", "_")
    return sanitized[:200]

def download_clip(clip_info: dict, download_folder: str = TEMP_DOWNLOAD_FOLDER):
    if not clip_info or not clip_info.get('download_url'):
        print("Error: Invalid clip_info or missing download_url.")
        return None
    download_url = clip_info['download_url']
    clip_id = clip_info.get('id', 'unknown_id')
    creator_name = sanitize_filename(clip_info.get('creator_name', 'unknown_creator'))
    title_part = sanitize_filename(clip_info.get('title', 'untitled'))
    filename = f"{clip_id}_{creator_name}_{title_part}.mp4"
    if len(filename) > 255:
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
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
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
        if os.path.exists(file_path): os.remove(file_path)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while downloading {filename}: {e}")
        if os.path.exists(file_path): os.remove(file_path)
        return None

def parse_resolution(resolution_str="720p"):
    if resolution_str == "1080p": return (1920, 1080)
    elif resolution_str == "720p": return (1280, 720)
    else:
        print(f"Unknown resolution string: {resolution_str}. Defaulting to 720p.")
        return (1280, 720)

def create_compilation(
    clip_file_paths: list, 
    output_filename: str, 
    target_duration_seconds: int = 11 * 60, 
    resolution_str: str = "720p",
    add_transitions: bool = True,
    transition_duration: float = 1.0,
    title_bumper_text: str = None,
    bumper_duration: float = 5.0
    ):
    target_width, target_height = parse_resolution(resolution_str)
    moviepy_clips = []
    current_total_duration = 0

    if title_bumper_text:
        try:
            print(f"Creating title bumper: '{title_bumper_text}' for {bumper_duration}s.")
            bumper_txt_clip = TextClip(
                title_bumper_text, fontsize=70, color='white', bg_color='black',
                font='Arial', size=(target_width, target_height), method='caption'
            ).set_duration(bumper_duration)
            moviepy_clips.append(bumper_txt_clip)
            current_total_duration += bumper_txt_clip.duration
        except Exception as e:
            print(f"Error creating title bumper: {e}. Proceeding without bumper.")

    for clip_path in clip_file_paths:
        if not os.path.exists(clip_path):
            print(f"Warning: Clip file not found: {clip_path}. Skipping.")
            continue
        clip = None
        try:
            clip = VideoFileClip(clip_path)
            if clip.duration is None or clip.duration <= 0:
                print(f"Warning: Clip {clip_path} has invalid or zero duration. Skipping.")
                clip.close()
                continue

            if clip.h != target_height or clip.w != target_width:
                print(f"Resizing clip {os.path.basename(clip_path)} from {clip.size} to target height {target_height}.")
                original_duration = clip.duration
                clip_resized = clip.resize(height=target_height)
                clip.close()
                clip = clip_resized
                if clip.w != target_width:
                    print(f"Centering clip {os.path.basename(clip_path)} on a {target_width}x{target_height} background.")
                    clip = CompositeVideoClip([clip.set_position("center")], size=(target_width, target_height), bg_color=(0,0,0)).set_duration(original_duration)
            
            effective_duration_to_add = clip.duration
            has_actual_video_clips = any(isinstance(c, VideoFileClip) for c in moviepy_clips) # Check if actual video clips (not TextClip) are already in list
            
            if has_actual_video_clips and add_transitions:
                 effective_duration_to_add -= transition_duration
            
            if moviepy_clips and (current_total_duration + effective_duration_to_add > target_duration_seconds + 30) and current_total_duration >= target_duration_seconds * 0.8:
                print(f"Adding clip {os.path.basename(clip_path)} would exceed target. Stopping.")
                clip.close()
                break
            
            moviepy_clips.append(clip)
            
            # Corrected duration update logic
            if not has_actual_video_clips: # This is the first VideoFileClip
                 current_total_duration += clip.duration
            else: # This is a subsequent VideoFileClip
                 current_total_duration += effective_duration_to_add if add_transitions else clip.duration

            print(f"Added clip: {os.path.basename(clip_path)}, new estimated total duration: {current_total_duration:.2f}s")
            if current_total_duration >= target_duration_seconds:
                print("Target duration reached or exceeded.")
                break
        except Exception as e:
            print(f"Error processing clip {clip_path}: {e}. Skipping.")
            if clip and hasattr(clip, 'close') and callable(clip.close):
                clip.close()

    if not any(isinstance(c, VideoFileClip) for c in moviepy_clips):
        print("Error: No actual video clips were successfully processed for the compilation.")
        for clip_obj in moviepy_clips: # Clean up any potential TextClips if no videos
            if hasattr(clip_obj, 'close') and callable(clip_obj.close):
                clip_obj.close()
        return None

    final_compilation = None
    try:
        if add_transitions and len([c for c in moviepy_clips if isinstance(c, VideoFileClip)]) > 1 or \
           (add_transitions and isinstance(moviepy_clips[0], TextClip) and len(moviepy_clips) > 1 ) : # Ensure transitions apply between video clips or bumper and first video clip
            
            print(f"Concatenating {len(moviepy_clips)} clips with {transition_duration}s crossfade transitions...")
            
            # Find first clip to be part of transition (could be TextClip or VideoFileClip)
            processed_video = moviepy_clips[0]
            if processed_video.duration is None: raise ValueError("First clip for transition has no duration.")
            processed_video = processed_video.set_duration(float(processed_video.duration), change_end=True)

            for i in range(1, len(moviepy_clips)):
                clip_to_add = moviepy_clips[i]
                if clip_to_add.duration is None: raise ValueError(f"Clip {i} has no duration.")
                clip_to_add = clip_to_add.set_duration(float(clip_to_add.duration), change_end=True)
                
                # Ensure previous clip (processed_video) has a valid duration for set_start
                if processed_video.duration is None: raise ValueError("Current composed video has no duration before adding next clip.")
                
                processed_video = CompositeVideoClip([
                    processed_video, 
                    clip_to_add.set_start(processed_video.duration - transition_duration).crossfadein(transition_duration)
                ]).set_duration(processed_video.duration - transition_duration + clip_to_add.duration)
            final_compilation = processed_video
        else:
            print(f"Concatenating {len(moviepy_clips)} clips without transitions...")
            final_compilation = concatenate_videoclips(moviepy_clips, method="compose")
        
        if not os.path.exists(COMPILATIONS_FOLDER): os.makedirs(COMPILATIONS_FOLDER)
        full_output_path = os.path.join(COMPILATIONS_FOLDER, output_filename)
        print(f"Writing final compilation to: {full_output_path} (Est. Duration: {final_compilation.duration:.2f}s)")
        final_compilation.write_videofile(
            full_output_path, codec="libx264", audio_codec="aac", preset="medium",
            ffmpeg_params=['-crf', '23'], threads=4
        )
        print("Compilation written successfully.")
        return full_output_path
    except Exception as e:
        print(f"Error during final video concatenation or writing: {e}")
        # import traceback; traceback.print_exc();
        return None
    finally:
        for clip_obj in moviepy_clips:
            if hasattr(clip_obj, 'close') and callable(clip_obj.close):
                clip_obj.close()
        if final_compilation and hasattr(final_compilation, 'close') and callable(final_compilation.close) and final_compilation not in moviepy_clips:
            final_compilation.close()

def cleanup_temp_clips(temp_folder: str = TEMP_DOWNLOAD_FOLDER):
    """
    Deletes all files within the temporary clips folder.

    Args:
        temp_folder (str, optional): The path to the temporary clips folder. 
                                    Defaults to TEMP_DOWNLOAD_FOLDER.
    """
    if not os.path.isdir(temp_folder):
        print(f"Temporary folder '{temp_folder}' not found. No cleanup needed or wrong path.")
        return False

    print(f"Cleaning up temporary folder: {temp_folder}")
    files_deleted_count = 0
    errors_encountered = False
    for filename in os.listdir(temp_folder):
        file_path = os.path.join(temp_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path) # Use unlink to remove files/links
                print(f"  Deleted: {filename}")
                files_deleted_count += 1
            # Optionally, could add rmtree for subdirs if they were ever created, but current plan doesn't.
        except Exception as e:
            print(f"  Error deleting file {file_path}: {e}")
            errors_encountered = True
    
    if errors_encountered:
        print(f"Cleanup of '{temp_folder}' completed with some errors.")
        return False
    else:
        print(f"Cleanup of '{temp_folder}' completed. {files_deleted_count} file(s) deleted.")
        # Optionally, remove the folder itself if it's empty and desired.
        # try:
        #     if not os.listdir(temp_folder): # Check if empty
        #         os.rmdir(temp_folder)
        #         print(f"  Also removed empty directory: {temp_folder}")
        # except Exception as e:
        #     print(f"  Error removing directory {temp_folder}: {e}")
        return True

if __name__ == '__main__':
    print("--- Testing download_clip (requires a direct MP4 URL) ---")
    sample_clip_info_valid = {
        'id': 'testclip001', 'download_url': 'https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4',
        'creator_name': 'TestStreamer', 'title': 'My Awesome Test Clip Title With Special Chars /*?:"<>|'
    }
    if 'sample-videos.com' in sample_clip_info_valid['download_url']:
        print("Placeholder URL in download_clip test. Skipping actual download test for it.")
    else:
        print("\nTesting with a valid sample MP4 URL...")
        downloaded_path = download_clip(sample_clip_info_valid)
        if downloaded_path: print(f"Test clip downloaded to: {downloaded_path}")
        else: print("Test clip download failed.")
    
    print("\n--- Testing sanitize_filename ---")
    test_filenames = [
        "normal_filename.mp4", "filename with spaces.mp4", "file/with/slashes.mp4",
        "file*with?invalid<chars>:\"|pipe.mp4",
        "a_very_long_filename_that_might_exceed_system_limits_and_needs_to_be_truncated_properly_to_avoid_errors_when_saving_the_file_to_the_disk_this_is_just_a_test_to_see_how_it_handles_it.mp4"
    ]
    for tf in test_filenames: print(f"Original: '{tf}' -> Sanitized: '{sanitize_filename(tf)}'")

    print("\n--- Testing create_compilation (with bumper and transitions if clips found) ---")
    if not os.path.exists(TEMP_DOWNLOAD_FOLDER): os.makedirs(TEMP_DOWNLOAD_FOLDER)
    sample_clips_for_compilation = [] # Ensure initialized
    if os.path.exists(TEMP_DOWNLOAD_FOLDER): # Ensure temp_clips exists for test consistency
        for item in os.listdir(TEMP_DOWNLOAD_FOLDER):
            if item.endswith(".mp4") and item not in sample_clips_for_compilation: # Avoid duplicates if run multiple times
                item_path = os.path.join(TEMP_DOWNLOAD_FOLDER, item)
                try:
                    with VideoFileClip(item_path) as test_clip_obj: 
                        if test_clip_obj.duration > 0: 
                            sample_clips_for_compilation.append(item_path)
                except Exception as e_test_clip:
                    print(f"Could not read {item_path} as a video (or file is invalid/empty): {e_test_clip}, skipping for test.")
                if len(sample_clips_for_compilation) >= 2: # Max 2 for faster test
                    break 
    
    if sample_clips_for_compilation and len(sample_clips_for_compilation) >= 1: 
        print(f"Found {len(sample_clips_for_compilation)} sample clips for testing compilation: {sample_clips_for_compilation}")
        output_comp_bumper = create_compilation(
            clip_file_paths=sample_clips_for_compilation,
            output_filename="test_compilation_bumper.mp4", target_duration_seconds=20, resolution_str="360p",
            add_transitions=True if len(sample_clips_for_compilation) >= 2 else False, transition_duration=0.5,
            title_bumper_text="EPIC COMPILATION \nNo. 42 - Test!", bumper_duration=3.0
        )
        if output_comp_bumper: print(f"Test compilation with bumper created: {output_comp_bumper}")
        else: print("Test compilation with bumper failed.")
    else:
        print("Skipping bumper compilation test as no valid sample clips were provided (need at least 1, 2 for transitions).")
    
    print("\n--- Testing cleanup_temp_clips ---")
    # Create some dummy files in temp_clips for testing
    if not os.path.exists(TEMP_DOWNLOAD_FOLDER):
        os.makedirs(TEMP_DOWNLOAD_FOLDER)
    
    dummy_files_for_cleanup = [
        os.path.join(TEMP_DOWNLOAD_FOLDER, "dummy_cleanup_1.mp4"),
        os.path.join(TEMP_DOWNLOAD_FOLDER, "dummy_cleanup_2.txt"),
        os.path.join(TEMP_DOWNLOAD_FOLDER, "dummy_cleanup_3.jpg")
    ]
    for df_path in dummy_files_for_cleanup:
        with open(df_path, 'w') as f:
            f.write("dummy content for cleanup test")
    
    print(f"Created dummy files in {TEMP_DOWNLOAD_FOLDER} for cleanup test.")
    if os.listdir(TEMP_DOWNLOAD_FOLDER): # Check if there are files to delete
        cleanup_success = cleanup_temp_clips()
        print(f"Cleanup successful: {cleanup_success}")
        # Verify cleanup (folder might still exist if it contained unremovable items or compilation outputs)
        remaining_files_after_cleanup = [f for f in os.listdir(TEMP_DOWNLOAD_FOLDER) if "dummy_cleanup" in f]
        if not remaining_files_after_cleanup:
            print(f"Verified: Dummy cleanup files in {TEMP_DOWNLOAD_FOLDER} are removed.")
        else:
            print(f"Warning: {TEMP_DOWNLOAD_FOLDER} still contains dummy cleanup files: {remaining_files_after_cleanup}")
    else:
        print("No dummy files were created in temp_clips to test cleanup, or folder was already empty.")
