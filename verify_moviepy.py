# verify_moviepy.py
try:
    import moviepy
    print(f"Successfully imported moviepy.")
    print(f"Moviepy version: {moviepy.__version__}")
    print(f"Moviepy path: {moviepy.__file__}")
    
    import moviepy.editor
    print(f"Successfully imported moviepy.editor.")
    
    # Test a basic moviepy.editor functionality
    clip = moviepy.editor.ColorClip(size=(100,100), color=(255,0,0), duration=1)
    print(f"Successfully created a ColorClip object from moviepy.editor of duration: {clip.duration}s.")
    clip.close()
    print("Moviepy test successful.")
    
except ImportError as e:
    print(f"ImportError: {e}")
except AttributeError as e:
    print(f"AttributeError: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python sys.path: {sys.path}")
