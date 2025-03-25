"""
Demo Email Sender with Audio Transcription

This script:
1. Checks for audio files in ./media/audio_uploads
2. Transcribes the audio using configured model
3. Sends an email with the transcription
4. Cleans up processed files

Author: [Your Name]
Date: [Current Date]
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Import required modules from existing codebase
from transcribe_config import TRANSCRIBE_CONFIG
from openai_whisper import transcribe_with_whisper1, transcribe_with_4o, load_config
from send_email import load_email_config, send_demo_email

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_audio_uploads():
    """Check if there are any audio files in the uploads directory"""
    upload_dir = Path("./media/audio_uploads")
    
    if not upload_dir.exists():
        logging.error("Upload directory not found: ./media/audio_uploads")
        return None
        
    # Get all audio files
    audio_files = list(upload_dir.glob("*.mp3")) + list(upload_dir.glob("*.wav"))
    
    if not audio_files:
        logging.info("No audio files found in uploads directory")
        return None
        
    # Return the first audio file found
    return str(audio_files[0])

def process_audio_file(audio_path):
    """Process the audio file using configured transcription model"""
    try:
        logging.info(f"Processing audio file: {audio_path}")
        
        # Load configurations
        transcribe_config, output_config, model_capabilities = load_config()
        
        # Determine which transcription function to use based on model type
        model_type = transcribe_config.get('model_type', 'whisper-1')
        
        if model_type == 'whisper-1':
            transcription = transcribe_with_whisper1(audio_path, transcribe_config, output_config)
        elif model_type == '4o-transcribe':
            transcription = transcribe_with_4o(audio_path, transcribe_config, output_config)
        else:
            logging.error(f"Unsupported model type: {model_type}")
            return None
        
        if not transcription:
            logging.error("No transcription generated")
            return None
            
        logging.info("Transcription completed successfully")
        return transcription
        
    except Exception as e:
        logging.error(f"Error processing audio file: {str(e)}")
        return None

def cleanup_processed_file(audio_path):
    """Delete the processed audio file"""
    try:
        os.remove(audio_path)
        logging.info(f"Deleted processed file: {audio_path}")
    except Exception as e:
        logging.error(f"Error deleting file: {str(e)}")

async def main():
    """Main function to run the demo email pipeline"""
    logging.info("Starting demo email pipeline")
    
    # Check for audio files
    audio_file = check_audio_uploads()
    if not audio_file:
        logging.info("No audio files to process. Exiting.")
        return
        
    # Process the audio file
    transcription = process_audio_file(audio_file)
    if not transcription:
        logging.error("Failed to process audio file. Exiting.")
        return
        
    # Load email configuration
    try:
        email_config = load_email_config()
    except Exception as e:
        logging.error(f"Error loading email config: {str(e)}")
        return
        
    # Send email with transcription
    try:
        send_demo_email(transcription)
        logging.info("Email sent successfully")
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return
        
    # Cleanup
    cleanup_processed_file(audio_file)
    
    logging.info("Demo email pipeline completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 