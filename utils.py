import os

COMPILATION_COUNTER_FILE = 'compilation_counter.txt'

def get_compilation_number():
    """Reads the compilation number from the counter file.
    
    Returns:
        int: The current compilation number. Defaults to 0 if file not found or invalid.
    """
    if not os.path.exists(COMPILATION_COUNTER_FILE):
        return 0
    try:
        with open(COMPILATION_COUNTER_FILE, 'r') as f:
            number_str = f.read().strip()
            return int(number_str)
    except ValueError:
        # If the file contains non-integer data, default to 0
        print(f"Warning: '{COMPILATION_COUNTER_FILE}' contained invalid data. Resetting to 0.")
        return 0
    except Exception as e:
        print(f"Error reading '{COMPILATION_COUNTER_FILE}': {e}. Defaulting to 0.")
        return 0

def increment_compilation_number(current_number):
    """Increments the compilation number and saves it to the counter file.
    
    Args:
        current_number (int): The current compilation number to increment.
    
    Returns:
        int: The new compilation number.
    """
    new_number = current_number + 1
    try:
        with open(COMPILATION_COUNTER_FILE, 'w') as f:
            f.write(str(new_number))
        return new_number
    except Exception as e:
        print(f"Error writing to '{COMPILATION_COUNTER_FILE}': {e}. Number may not have been saved.")
        # Return the new number anyway, but the save failed
        return new_number

if __name__ == '__main__':
    # Example Usage
    print(f"Initial compilation number: {get_compilation_number()}")
    
    # Simulate a successful compilation and increment
    current_num = get_compilation_number()
    new_num = increment_compilation_number(current_num)
    print(f"New compilation number after increment: {new_num}")
    
    # Verify it's saved
    print(f"Verification read from file: {get_compilation_number()}")

    # Test case: What if the file is manually emptied or corrupted?
    # To test this, you might manually delete or corrupt compilation_counter.txt
    # and then run this script again.
    # For example, create an empty compilation_counter.txt then run:
    # open(COMPILATION_COUNTER_FILE, 'w').close() 
    # print(f"Test with empty file: {get_compilation_number()}") # Should be 0
    # with open(COMPILATION_COUNTER_FILE, 'w') as f: f.write("abc")
    # print(f"Test with corrupt file: {get_compilation_number()}") # Should be 0 and print warning
    # increment_compilation_number(get_compilation_number()) # Should reset to 1
    # print(f"Value after corrupt file increment: {get_compilation_number()}")


def generate_youtube_video_title(compilation_number: int, game_name: str = None, title_format: str = "MEILLEURS CLIPS TWITCH {GAME_NAME_PREFIX}🔥 Compil du Jour n°{X}"):
    """
    Generates a video title for YouTube.

    Args:
        compilation_number (int): The current compilation number.
        game_name (str, optional): The name of the game. If provided, it's included in the title.
        title_format (str, optional): A format string for the title. 
                                        Placeholders: {X} for number, {GAME_NAME_PREFIX} for "GAME_NAME " or empty.

    Returns:
        str: The generated video title.
    """
    
    game_name_prefix = ""
    if game_name:
        game_name_prefix = game_name.upper() + " " # Example: "FORTNITE "
    
    # Replace placeholders
    title = title_format.replace("{X}", str(compilation_number))
    title = title.replace("{GAME_NAME_PREFIX}", game_name_prefix)
    
    # Ensure no double spaces if game_name_prefix was empty and format expected a space after it
    title = title.replace("  ", " ").strip() 
    
    return title

if __name__ == '__main__':
    # ... (existing test code for compilation counter) ...

    print("\n--- Testing generate_youtube_video_title ---")
    print(f"Title (no game): {generate_youtube_video_title(compilation_number=123)}")
    print(f"Title (with game): {generate_youtube_video_title(compilation_number=124, game_name='Valorant')}")
    print(f"Title (with game, custom format): {generate_youtube_video_title(compilation_number=125, game_name='Apex Legends', title_format='BEST OF {GAME_NAME_PREFIX} Clips - #{X}')}")
    print(f"Title (no game, custom format): {generate_youtube_video_title(compilation_number=126, title_format='Twitch Highlights #{X}')}")
