"""
Process Transcriptions with OpenAI API (previously Llama 3.1)

This script:
1. Reads the transcription output from the local_whisper.py script
2. Processes it using the OpenAI API
3. Adds the organized content to date-prefixed diary files
4. Extracts to-do items to to_do.txt

Part of the audio diary pipeline.
"""

import os
import sys
import json
import logging
from datetime import datetime
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openai_processor.log'),
        logging.StreamHandler()
    ]
)

# Import OpenAI processor module
try:
    import openai_processor
except ImportError:
    logging.error("Could not import OpenAI processor module. Please ensure openai_processor.py is in the current directory.")
    sys.exit(1)

def load_config():
    """Load the main configuration file"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading config: {str(e)}")
        return {}

def get_diary_file_path():
    """
    Returns the appropriate diary file path with YYMMDD date prefix based on config.
    Creates a new file for each day.
    """
    # Load config to get current date
    config = load_config()
    diary_config = config.get("diary_manager", {})
    
    # Get current date from config (fallback to today if not found)
    date_str = diary_config.get("current_date", datetime.now().strftime("%y%m%d"))
    
    # Get file format from config
    file_format = diary_config.get("entries_file_format", "{date}_ongoing_entries.txt")
    diary_filename = file_format.replace("{date}", date_str)
    
    # Get legacy filename from config
    legacy_file = diary_config.get("legacy_file", "ongoing_entries.txt")
    
    # Get full path to the file
    diary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), diary_filename)
    
    # Check if file exists, if not, create it with a header
    if not os.path.exists(diary_path):
        try:
            # Try to get current date in full format
            if len(date_str) == 6:  # If it's in YYMMDD format
                # Try to parse the date
                try:
                    year = int("20" + date_str[0:2])
                    month = int(date_str[2:4])
                    day = int(date_str[4:6])
                    full_date = f"{year}-{month:02d}-{day:02d}"
                except ValueError:
                    # If parsing fails, use today's date
                    full_date = datetime.now().strftime("%Y-%m-%d")
            else:
                # If not in expected format, use today's date
                full_date = datetime.now().strftime("%Y-%m-%d")
                
            with open(diary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Diary Entries for {full_date}\n\n")
            logging.info(f"Created new diary file: {diary_filename}")
        except Exception as e:
            logging.error(f"Error creating new diary file: {str(e)}")
            # Fall back to the default ongoing_entries.txt if there's an error
            return legacy_file
    
    return diary_path

def get_previous_entries():
    """Get previous entries from diary files based on config settings"""
    # Load config
    config = load_config()
    diary_config = config.get("diary_manager", {})
    
    entries = ""
    
    # Get current date from config
    date_str = diary_config.get("current_date", datetime.now().strftime("%y%m%d"))
    
    # Get file format and create current filename
    file_format = diary_config.get("entries_file_format", "{date}_ongoing_entries.txt")
    current_file = file_format.replace("{date}", date_str)
    
    # Get legacy filename
    legacy_file = diary_config.get("legacy_file", "ongoing_entries.txt")
    
    # Check if current file exists and read it
    if os.path.exists(current_file):
        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                entries = f.read()
        except Exception as e:
            logging.warning(f"Could not read current diary file: {str(e)}")
    
    # If no entries found, try the legacy file
    if not entries and os.path.exists(legacy_file):
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                entries = f.read()
        except Exception as e:
            logging.warning(f"Could not read legacy entries file: {str(e)}")
    
    return entries

def get_diary_organization_prompt(diary_entry, ongoing_entries):
    """Import the prompt template from prompts.py"""
    try:
        from prompts import get_diary_organization_prompt
        return get_diary_organization_prompt(diary_entry, ongoing_entries)
    except ImportError:
        logging.warning("Could not import prompt from prompts.py, using default prompt")
        # Default prompt if import fails
        prompt = f"""
        You are an intelligent diary organizer. Your task is to analyze a new diary entry and determine how it relates to previous entries. You should categorize and organize the content.

        # PREVIOUS DIARY ENTRIES:
        {ongoing_entries if ongoing_entries else "No previous entries exist yet."}

        # NEW DIARY ENTRY:
        {diary_entry}

        Please provide a detailed analysis with the following structure:

        ## ENTRY CATEGORIZATION
        - **Main Topics**: [Identify 1-2 main topics or themes in this entry]
        - **Emotional Tone**: [Analyze the emotional tone of the entry]
        - **Related Previous Entries**: [Identify any connections to previous entries]

        ## ORGANIZED ENTRY
        [Rewrite the entry with proper formatting while preserving all original content]

        ## TO-DO ITEMS
        [Extract any tasks, to-do items, or intentions mentioned in the entry. If none are found, write "No to-do items detected."]
        """
        return prompt

def read_transcription_file(config):
    """Read the transcription file specified in config.json"""
    try:
        output_file = config.get("output_file", "daily.txt")
        if not os.path.exists(output_file):
            logging.error(f"Transcription file {output_file} not found")
            return None
            
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if file has content
        if not content.strip():
            logging.warning(f"Transcription file {output_file} is empty")
            return None
            
        return content
    except Exception as e:
        logging.error(f"Error reading transcription file: {str(e)}")
        return None

def process_with_openai(transcription):
    """Process the transcription with OpenAI API"""
    # Get the appropriate dated diary file path from config
    diary_path = get_diary_file_path()
    ongoing_entries = get_previous_entries()
    
    # Get the organization prompt
    prompt = get_diary_organization_prompt(transcription, ongoing_entries)
    
    # Process with OpenAI API
    logging.info("Analyzing transcription with OpenAI API...")
    try:
        result = openai_processor.process_transcription(
            transcription,
            ongoing_entries,
            prompt
        )
        
        # Extract to-do items from the results
        todo_items = result['todo_items']
        if todo_items:
            logging.info(f"Found {len(todo_items)} to-do items")
            
            # Append to-do items to the to-do file
            try:
                todo_path = "to_do.txt"
                with open(todo_path, 'a', encoding='utf-8') as file:
                    # Add timestamp to each to-do item
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    file.write(f"\n--- Added on {timestamp} ---\n")
                    for item in todo_items:
                        file.write(f"- {item}\n")
                logging.info(f"To-do items saved to {todo_path}")
            except Exception as e:
                logging.error(f"Error saving to-do items: {str(e)}")
        else:
            logging.info("No to-do items found in the transcription")
        
        # Get the organized entry
        organized_entry = result['organized_entry']
        if not organized_entry:
            logging.warning("Could not extract organized entry. Using original transcription.")
            organized_entry = transcription
        
        # Append the entry to the dated diary file
        try:
            with open(diary_path, 'a', encoding='utf-8') as file:
                # Add a timestamp and separator
                timestamp = datetime.now().strftime("%H:%M")
                file.write(f"\n\n## Entry at {timestamp}\n\n")
                file.write(organized_entry)
            logging.info(f"Entry appended to {diary_path}")
            
            # Log token usage if available
            if 'usage' in result:
                usage = result['usage']
                logging.info(f"Token usage: {usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion = {usage['total_tokens']} total")
            
            return True
        except Exception as e:
            logging.error(f"Error appending entry: {str(e)}")
            return False
            
    except Exception as e:
        logging.error(f"Error processing with OpenAI API: {str(e)}")
        return False

def main():
    """Main entry point"""
    logging.info("Starting OpenAI API processing of transcription")
    
    # Load configuration
    config = load_config()
    
    # Read the transcription file
    transcription = read_transcription_file(config)
    if transcription is None:
        logging.error("No transcription to process")
        sys.exit(1)
    
    # Process the transcription with OpenAI API
    success = process_with_openai(transcription)
    
    if success:
        logging.info("Successfully processed transcription with OpenAI API")
        
        # Clear the transcription file to prevent reprocessing
        try:
            output_file = config.get("output_file", "daily.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                pass  # Just open and close to clear the file
            logging.info(f"Cleared transcription file {output_file}")
        except Exception as e:
            logging.error(f"Error clearing transcription file: {str(e)}")
    else:
        logging.error("Failed to process transcription")
        sys.exit(1)
    
    logging.info("OpenAI API processing complete")

if __name__ == "__main__":
    main() 