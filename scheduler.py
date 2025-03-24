"""
Automated Audio Pipeline Scheduler

This script runs three operations sequentially based on the configured interval:
1. download-from-gdrive.py - Downloads audio files from Google Drive
2. local_whisper.py/openai_whisper.py - Transcribes the downloaded audio files based on configured model
3. process_transcription.py - Processes transcriptions with OpenAI API

Author: [Your Name]
Date: [Current Date]
"""

import subprocess
import time
import logging
import os
import sys
import json
import traceback
from datetime import datetime, timedelta
# Import the FFmpeg path setup function
from ffmpeg_utils import setup_ffmpeg_path

# Configure FFmpeg path early
ffmpeg_path = setup_ffmpeg_path()

# Load configuration
def load_config():
    """Load configuration from config.json file"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print("Please create a config.json file before running the scheduler.")
        sys.exit(1)
    
    # Try to load and parse the config file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate that required sections exist
        if "scheduler" not in config:
            print("ERROR: Missing 'scheduler' section in config.json")
            sys.exit(1)
            
        return config
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config.json: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load config.json: {str(e)}")
        sys.exit(1)

# Load transcription configuration to determine which transcription script to use
def load_transcribe_config():
    """Load transcription configuration to determine which transcription script to use"""
    try:
        # Try to import the transcription configuration
        from transcribe_config import TRANSCRIBE_CONFIG
        return TRANSCRIBE_CONFIG
    except ImportError:
        logging.warning("transcribe_config.py not found. Will use local_whisper.py by default.")
        return {"model_type": "local"}

# Check for OpenAI API key at startup
def check_openai_api_key():
    """Check if OpenAI API key is configured"""
    # Check environment variable
    if os.environ.get('OPENAI_API_KEY'):
        return True
        
    # Check openai_config.py
    try:
        import openai_config
        if hasattr(openai_config, 'OPENAI_CONFIG') and openai_config.OPENAI_CONFIG.get('api_key'):
            return True
    except ImportError:
        pass
    
    # Check transcribe_config.py
    try:
        from transcribe_config import TRANSCRIBE_CONFIG
        if TRANSCRIBE_CONFIG.get('api_key'):
            return True
    except ImportError:
        pass
        
    logging.warning("""
=====================================================================
WARNING: OpenAI API key not found in environment or config files.
The transcription processing step may fail.
Run 'python setup_openai.py' to configure your API key.
=====================================================================
""")
    return False

# Load config
config = load_config()
scheduler_config = config.get("scheduler", {})
diary_config = config.get("diary_manager", {})

# Configure logging
log_level_str = scheduler_config.get("log_level", "INFO")
log_level = getattr(logging, log_level_str)
log_file = scheduler_config.get("log_file", "pipeline_scheduler.log")

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Log FFmpeg status
if ffmpeg_path:
    logging.info(f"FFmpeg configured: {ffmpeg_path}")
else:
    logging.warning("FFmpeg not found! Audio processing may be affected.")

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the scripts to run (use absolute paths for reliability)
scripts = scheduler_config.get("scripts", {})
DOWNLOAD_SCRIPT_PATH = os.path.join(SCRIPT_DIR, scripts.get("download", "download-from-gdrive.py"))
PROCESS_SCRIPT_PATH = os.path.join(SCRIPT_DIR, scripts.get("process", "process_transcription.py"))

# Determine which transcription script to use based on the configuration
transcribe_config = load_transcribe_config()
model_type = transcribe_config.get("model_type", "local")

if model_type == "local":
    TRANSCRIBE_SCRIPT_PATH = os.path.join(SCRIPT_DIR, scripts.get("transcribe", "local_whisper.py"))
else:
    # For whisper-1 and 4o-transcribe, use openai_whisper.py
    TRANSCRIBE_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "openai_whisper.py")

logging.info(f"Using transcription model: {model_type}")
logging.info(f"Transcription script: {TRANSCRIBE_SCRIPT_PATH}")

# Get the path to the Python executable that's running this script
# This ensures we use the same Python environment with all installed packages
PYTHON_EXECUTABLE = sys.executable

# Get the interval from config
def calculate_interval_seconds(config):
    """
    Calculate interval in seconds based on configuration.
    The 'runs_per_day' in config.json represents how many times the pipeline runs per day.
    If runs_per_day is 0: run once and exit
    Otherwise: convert runs per day to seconds interval (86400/N)
    """
    runs_per_day = config.get("scheduler", {}).get("runs_per_day", 1)
    
    # If runs_per_day is 0, we'll run once and exit
    if runs_per_day == 0:
        return 0
        
    # Convert "runs per day" to seconds: 86400 seconds / N runs
    seconds_per_day = 86400
    interval_seconds = seconds_per_day / runs_per_day
    logging.info(f"Configured to run {runs_per_day} times per day (every {int(interval_seconds)} seconds)")
    return int(interval_seconds)

def update_config_date(new_date):
    """Update the current_date in the config file"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        # Read the current config
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Update the date
        if "diary_manager" not in config_data:
            config_data["diary_manager"] = {}
        
        config_data["diary_manager"]["current_date"] = new_date
        
        # Write the updated config back
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logging.info(f"Updated config.json with new date: {new_date}")
        return True
    except Exception as e:
        logging.error(f"Error updating config.json: {str(e)}")
        return False

def check_for_day_change():
    """Check if the day has changed and create a new diary file if needed"""
    # Skip check if auto update is disabled
    if not diary_config.get("auto_update_date", True):
        logging.info("Auto date update disabled in config, skipping day change check")
        return False
    
    # Get the current date from config
    config_date = diary_config.get("current_date", "")
    
    # Get today's date
    today_date = datetime.now().strftime("%y%m%d")
    
    # If no change, return early
    if config_date == today_date:
        return False
    
    logging.info(f"Date change detected from {config_date} to {today_date}")
    
    # Format for new diary filename
    file_format = diary_config.get("entries_file_format", "{date}_ongoing_entries.txt")
    new_diary_filename = file_format.replace("{date}", today_date)
    new_diary_path = os.path.join(SCRIPT_DIR, new_diary_filename)
    
    # Create the new diary file if it doesn't exist yet
    if not os.path.exists(new_diary_path):
        try:
            with open(new_diary_path, 'w', encoding='utf-8') as f:
                full_date = datetime.now().strftime("%Y-%m-%d")
                f.write(f"# Diary Entries for {full_date}\n\n")
            logging.info(f"Created new diary file for today: {new_diary_filename}")
            
            # Add a note about the day change to the new file
            with open(new_diary_path, 'a', encoding='utf-8') as f:
                f.write(f"## System Note - {datetime.now().strftime('%H:%M')}\n\n")
                f.write("New day started. Previous entries are in the previous day's file.\n\n")
            
            # Update the config with the new date
            update_config_date(today_date)
            
            # Also update our local config copy
            diary_config["current_date"] = today_date
            
            return True
        except Exception as e:
            logging.error(f"Error creating new diary file: {str(e)}")
            return False
    else:
        # If file exists but config date is outdated, update config
        update_config_date(today_date)
        diary_config["current_date"] = today_date
        return True
    
    return False

def run_pipeline():
    """Run the complete pipeline: download files, transcribe audio, process with OpenAI API"""
    logging.info("Starting pipeline execution")
    
    # First, check if the day has changed
    day_changed = check_for_day_change()
    if day_changed:
        logging.info("Day change detected, diary file updated")
    
    # Step 1: Download files from Google Drive
    logging.info("Step 1: Downloading files from Google Drive")
    try:
        download_process = subprocess.run(
            [PYTHON_EXECUTABLE, DOWNLOAD_SCRIPT_PATH],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',  # Explicitly set encoding to utf-8
            errors='replace'   # Replace characters that can't be decoded
        )
        logging.info(f"Download script output: {download_process.stdout}")
        if download_process.stderr:
            logging.warning(f"Download script errors: {download_process.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Download script failed with exit code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
        # Continue to transcription anyway - there might be previously downloaded files
    
    # Step 2: Transcribe downloaded audio files
    logging.info(f"Step 2: Transcribing audio files using {model_type} model")
    try:
        whisper_process = subprocess.run(
            [PYTHON_EXECUTABLE, TRANSCRIBE_SCRIPT_PATH],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        logging.info(f"Transcription script output: {whisper_process.stdout}")
        if whisper_process.stderr:
            logging.warning(f"Transcription script errors: {whisper_process.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Transcription script failed with exit code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
        # Continue to processing anyway - there might still be a transcription file
    
    # Step 3: Process transcriptions with OpenAI API
    logging.info("Step 3: Processing transcriptions with OpenAI API")
    try:
        process_transcription = subprocess.run(
            [PYTHON_EXECUTABLE, PROCESS_SCRIPT_PATH],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        logging.info(f"Processing script output: {process_transcription.stdout}")
        if process_transcription.stderr:
            logging.warning(f"Processing script errors: {process_transcription.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Processing script failed with exit code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
    
    logging.info("Pipeline execution completed")

def main():
    """Main function to run the scheduler"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run the audio diary pipeline at regular intervals.")
    parser.add_argument("--set-date", nargs='?', const="", metavar="YYMMDD", 
                        help="Set the current date (format: YYMMDD). If no date is provided, use today's date.")
    args = parser.parse_args()
    
    # Handle --set-date argument
    if args.set_date is not None:
        # If no specific date is provided, use today's date
        if args.set_date == "":
            new_date = datetime.now().strftime("%y%m%d")
            print(f"Setting date to today: {new_date}")
        else:
            # Validate the provided date format
            if len(args.set_date) != 6 or not args.set_date.isdigit():
                print("Error: Date must be in YYMMDD format (e.g., 210730 for July 30, 2021)")
                sys.exit(1)
            new_date = args.set_date
            print(f"Setting date to: {new_date}")
        
        # Update the config file
        if update_config_date(new_date):
            print("Date updated successfully in config.json")
            # Also update our local copy
            if "diary_manager" in config:
                config["diary_manager"]["current_date"] = new_date
        else:
            print("Failed to update date in config.json")
        
        # Exit after setting the date
        sys.exit(0)
    
    # Get the interval in seconds
    interval_seconds = calculate_interval_seconds(config)
    
    # Check for OpenAI API key at startup
    check_openai_api_key()
    
    # If interval is 0, run once and exit
    if interval_seconds == 0:
        logging.info("Running pipeline once and exiting")
        run_pipeline()
        logging.info("Done. Exiting.")
        return
    
    # Run in a loop with the specified interval
    try:
        while True:
            # Run the pipeline
            run_pipeline()
            
            # Calculate and display the next run time
            next_run = datetime.now() + timedelta(seconds=interval_seconds)
            logging.info(f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Sleep until the next run
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
        print("\nScheduler stopped by user. Exiting.")
    except Exception as e:
        logging.error(f"Error in scheduler: {str(e)}")
        logging.error(traceback.format_exc())
        print(f"Error in scheduler: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 