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
