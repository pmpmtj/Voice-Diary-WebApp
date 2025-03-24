"""
FFmpeg Utilities

This module provides utilities for setting up the FFmpeg path in the system environment,
which is required by Whisper for audio processing.
"""

import os
import sys
import logging
import subprocess

def setup_ffmpeg_path():
    """
    Set up FFmpeg path in system environment
    
    This function:
    1. Checks if FFmpeg is already in the system PATH
    2. If not, tries to use local ffmpeg.exe in the project directory
    3. Adds the ffmpeg binary directory to the PATH
    
    Returns:
    --------
    str
        Path to ffmpeg binary, or None if not found
    """
    # Initialize logging
    logging.getLogger(__name__)
    
    # First check if FFmpeg is already in the PATH
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=False
        )
        if result.returncode == 0:
            logging.info("FFmpeg found in system PATH")
            return "ffmpeg"  # Return the command name since it's in PATH
    except (FileNotFoundError, subprocess.SubprocessError):
        logging.info("FFmpeg not found in system PATH")
    
    # Next, check for a local ffmpeg.exe in the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
    
    if os.path.exists(ffmpeg_path):
        logging.info(f"Using local FFmpeg: {ffmpeg_path}")
        # Add the directory to the PATH environment variable
        os.environ["PATH"] = f"{script_dir};{os.environ['PATH']}"
        return ffmpeg_path
    
    # Check if FFmpeg is in a common Windows directory
    if sys.platform == 'win32':
        common_paths = [
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'ffmpeg', 'bin'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'ffmpeg', 'bin'),
            os.path.join(os.environ.get('USERPROFILE', 'C:\\Users\\' + os.getlogin()), 'ffmpeg', 'bin')
        ]
        
        for path in common_paths:
            ffmpeg_exe = os.path.join(path, 'ffmpeg.exe')
            if os.path.exists(ffmpeg_exe):
                logging.info(f"Found FFmpeg in common location: {ffmpeg_exe}")
                # Add to PATH
                os.environ["PATH"] = f"{path};{os.environ['PATH']}"
                return ffmpeg_exe
    
    # If we get here, FFmpeg wasn't found
    logging.warning("FFmpeg not found! Audio processing may fail.")
    logging.warning("Please install FFmpeg and ensure it's in your PATH, or place ffmpeg.exe in the project directory.")
    return None

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Test the function
    ffmpeg_path = setup_ffmpeg_path()
    
    if ffmpeg_path:
        print(f"FFmpeg found at: {ffmpeg_path}")
    else:
        print("FFmpeg not found. Please install FFmpeg to use audio processing functionality.") 