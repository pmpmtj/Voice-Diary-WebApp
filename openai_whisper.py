#!/usr/bin/env python3
"""
OpenAI Whisper API Transcription

This script transcribes audio files using OpenAI's API:
- whisper-1 API endpoint 
- 4o transcribe API endpoint

It processes audio files in the downloads directory, supporting both
individual files and batch processing based on the configuration.
"""

import os
import sys
import json
import argparse
import logging
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import asyncio
import concurrent.futures
import traceback

try:
    import openai
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    print("Error: OpenAI package not found. Install it with pip install openai")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openai_whisper.log'),
        logging.StreamHandler()
    ]
)

# Load the configuration
def load_config():
    """Load the transcription configuration."""
    try:
        from transcribe_config import TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
        return TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
    except ImportError:
        logging.error("Error: Could not import transcribe_config.py. Run setup_transcribe_model.py first.")
        sys.exit(1)

def load_main_config():
    """Load the main configuration file."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading config.json: {str(e)}")
        return {
            "downloads_directory": "./downloads",
            "output_file": "transcription.txt",
            "processed_directory": "./processed_audio"
        }

def get_openai_client():
    """Initialize and return the OpenAI client."""
    transcribe_config, _, _ = load_config()
    api_key = transcribe_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logging.error("OpenAI API key is not set. Please run setup_transcribe_model.py to configure it.")
        sys.exit(1)
    
    return OpenAI(api_key=api_key)

def get_async_openai_client():
    """Initialize and return the AsyncOpenAI client."""
    transcribe_config, _, _ = load_config()
    api_key = transcribe_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logging.error("OpenAI API key is not set. Please run setup_transcribe_model.py to configure it.")
        sys.exit(1)
    
    return AsyncOpenAI(api_key=api_key)

def find_audio_files(directory):
    """Find all audio files in the specified directory."""
    audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.mp4']
    audio_files = []
    
    # Check if directory exists
    if not os.path.exists(directory):
        logging.warning(f"Directory {directory} does not exist")
        return audio_files
    
    # Scan directory for audio files
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(file_path)
    except Exception as e:
        logging.error(f"Error scanning directory {directory}: {str(e)}")
    
    return audio_files

def ensure_processed_directory(directory):
    """Ensure the processed audio directory exists."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")
        except Exception as e:
            logging.error(f"Error creating directory {directory}: {str(e)}")
            return False
    return True

def calculate_duration(file_path):
    """Calculate estimated duration of an audio file in seconds."""
    try:
        # Try to use ffprobe to get duration
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return float(result.stdout.strip())
    except Exception:
        # Fallback: use file size as a very rough estimate (3MB ≈ 1 minute)
        file_size = os.path.getsize(file_path)
        return (file_size / (3 * 1024 * 1024)) * 60  # Convert to seconds

def transcribe_with_whisper1(file_path, config, output_config):
    """Transcribe an audio file using the whisper-1 API."""
    client = get_openai_client()
    
    # Prepare parameters
    whisper_config = config["whisper_api"]
    params = {
        "model": whisper_config["model"],
        "response_format": whisper_config["response_format"],
        "temperature": whisper_config["temperature"],
    }
    
    # Add optional parameters if provided
    if whisper_config["language"]:
        params["language"] = whisper_config["language"]
    
    if whisper_config["prompt"]:
        params["prompt"] = whisper_config["prompt"]
    
    # Open the audio file
    try:
        with open(file_path, "rb") as audio_file:
            logging.info(f"Transcribing {file_path} with whisper-1 API...")
            
            start_time = time.time()
            response = client.audio.transcriptions.create(
                file=audio_file,
                **params
            )
            end_time = time.time()
            
            # Process and return the response
            if whisper_config["response_format"] == "text":
                # The response is already the text content when response_format is 'text'
                transcript = response
            elif whisper_config["response_format"] in ["verbose_json", "json"]:
                # For JSON formats, dump the JSON content
                try:
                    transcript = json.dumps(response.model_dump(), indent=2)
                except AttributeError:
                    # If response is not an object with model_dump method, convert directly
                    if isinstance(response, dict):
                        transcript = json.dumps(response, indent=2)
                    else:
                        transcript = str(response)
            else:
                # For other formats (vtt, srt), convert to string
                transcript = str(response)
            
            logging.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
            return transcript
            
    except Exception as e:
        logging.error(f"Error transcribing {file_path}: {str(e)}")
        traceback.print_exc()
        return None

def transcribe_with_4o(file_path, config, output_config):
    """Transcribe an audio file using the 4o transcribe API."""
    client = get_openai_client()
    
    # Prepare parameters
    transcribe_config = config["4o_transcribe"]
    
    # Open the audio file
    try:
        with open(file_path, "rb") as audio_file:
            logging.info(f"Transcribing {file_path} with 4o transcribe API...")
            
            start_time = time.time()
            
            # Call the appropriate API based on whether we're using chat or a dedicated endpoint
            # Currently, 4o transcription is done via the chat completions API
            response = client.chat.completions.create(
                model=transcribe_config["model"],
                temperature=transcribe_config["temperature"],
                messages=[
                    {"role": "system", "content": "Transcribe the audio accurately"},
                    {"role": "user", "content": [
                        {"type": "text", "text": transcribe_config["prompt"] if transcribe_config["prompt"] else "Please transcribe this audio."},
                        {"type": "audio_file", "audio_file": audio_file}
                    ]}
                ]
            )
            
            end_time = time.time()
            transcript = response.choices[0].message.content
            
            logging.info(f"Transcription completed in {end_time - start_time:.2f} seconds")
            return transcript
            
    except Exception as e:
        logging.error(f"Error transcribing {file_path} with 4o API: {str(e)}")
        traceback.print_exc()
        return None

def chunk_audio_file(file_path, max_chunk_size_ms, output_dir=None):
    """
    Split audio file into chunks of specified maximum size.
    
    Args:
        file_path: Path to the audio file
        max_chunk_size_ms: Maximum chunk size in milliseconds
        output_dir: Directory to save chunks (if None, uses temp directory)
        
    Returns:
        List of file paths to the chunks
    """
    max_chunk_size_sec = max_chunk_size_ms / 1000
    
    try:
        # Calculate duration
        duration = calculate_duration(file_path)
        if duration <= max_chunk_size_sec:
            # No need to chunk
            return [file_path]
            
        # Create a temporary directory if not provided
        temp_dir = output_dir if output_dir else tempfile.mkdtemp()
        
        # Calculate number of chunks
        num_chunks = int(duration / max_chunk_size_sec) + 1
        chunk_files = []
        
        # Extract the file extension
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        
        # Use ffmpeg to split the file
        import subprocess
        for i in range(num_chunks):
            start_time = i * max_chunk_size_sec
            output_file = os.path.join(temp_dir, f"{file_base}_chunk{i}{file_ext}")
            
            # Use ffmpeg to extract the chunk
            cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-ss", str(start_time),
                "-t", str(max_chunk_size_sec),
                "-c", "copy",  # Use copy codec for speed
                output_file
            ]
            
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Check if the file was created and has some content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                chunk_files.append(output_file)
        
        logging.info(f"Split {file_path} into {len(chunk_files)} chunks")
        return chunk_files
        
    except Exception as e:
        logging.error(f"Error chunking audio file {file_path}: {str(e)}")
        return [file_path]  # Return the original file on error

def save_individual_transcription(transcript, audio_file, output_dir, model_type):
    """
    Save an individual transcription to the received_transcriptions directory
    with metadata about which model produced it and when.
    
    Args:
        transcript: The transcription text
        audio_file: The path to the original audio file
        output_dir: The directory to save transcriptions
        model_type: The type of model used (whisper-1 or 4o-transcribe)
    """
    try:
        # Create the directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created directory: {output_dir}")
        
        # Get the base filename without extension
        audio_filename = os.path.basename(audio_file)
        base_name, _ = os.path.splitext(audio_filename)
        
        # Create a filename with timestamp and model info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_name}_{model_type}_{timestamp}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        # Write the transcription with metadata
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Transcription of {audio_filename}\n")
            f.write(f"# Model: {model_type}\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Original file: {audio_file}\n\n")
            f.write(transcript)
        
        logging.info(f"Saved individual transcription to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Error saving individual transcription: {str(e)}")
        return False

async def transcribe_audio_files(audio_files, config, output_config):
    """Transcribe a list of audio files."""
    transcripts = []
    
    # Determine if we should chunk audio files
    should_chunk = config.get("chunk_audio", False)
    max_chunk_size = config.get("max_chunk_size", 24 * 60 * 1000)  # Default 24 mins
    
    # Get the transcription model type
    model_type = config["model_type"]
    
    # Load main config to get received_transcriptions_directory
    main_config = load_main_config()
    received_dir = main_config.get("received_transcriptions_directory", "./received_transcriptions")
    
    # Process each audio file
    for file_path in audio_files:
        logging.info(f"Processing {file_path}")
        
        file_chunks = []
        if should_chunk:
            # Chunk the audio file
            file_chunks = chunk_audio_file(file_path, max_chunk_size)
        else:
            file_chunks = [file_path]
        
        # Process each chunk
        chunk_transcripts = []
        for chunk in file_chunks:
            # Transcribe the chunk based on model type
            if model_type == "whisper-1":
                transcript = transcribe_with_whisper1(chunk, config, output_config)
            elif model_type == "4o-transcribe":
                transcript = transcribe_with_4o(chunk, config, output_config)
            else:
                logging.error(f"Unknown model type: {model_type}")
                continue
            
            if transcript:
                chunk_transcripts.append(transcript)
                
                # Save individual transcription to received_transcriptions directory
                save_individual_transcription(transcript, 
                                             file_path if chunk == file_path else chunk, 
                                             received_dir, 
                                             model_type)
            
            # If chunks are in a temp directory, clean up
            if should_chunk and chunk != file_path:
                try:
                    os.remove(chunk)
                except:
                    pass
        
        # Combine chunk transcripts
        if chunk_transcripts:
            combined_transcript = "\n".join(chunk_transcripts)
            transcripts.append(combined_transcript)
    
    return transcripts

def save_transcriptions(transcripts, output_file, append=False):
    """Save transcriptions to the output file."""
    mode = 'a' if append else 'w'
    
    try:
        with open(output_file, mode, encoding='utf-8') as f:
            # Add a timestamp if not appending (new file)
            if not append:
                f.write(f"# Transcriptions {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            # Write each transcript with a separator
            for i, transcript in enumerate(transcripts):
                f.write(f"\n--- Transcription {i+1} ---\n\n")
                f.write(transcript)
                f.write("\n\n")
        
        logging.info(f"Saved {len(transcripts)} transcriptions to {output_file}")
        return True
    except Exception as e:
        logging.error(f"Error saving transcriptions: {str(e)}")
        return False

def move_to_processed(file_path, processed_dir):
    """Move a file to the processed directory."""
    if not os.path.exists(file_path):
        logging.warning(f"File not found: {file_path}")
        return False
    
    try:
        # Create processed directory if it doesn't exist
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)
        
        # Get the destination path
        file_name = os.path.basename(file_path)
        processed_path = os.path.join(processed_dir, file_name)
        
        # If the file already exists in the processed directory, add a timestamp
        if os.path.exists(processed_path):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            base_name, ext = os.path.splitext(file_name)
            processed_path = os.path.join(processed_dir, f"{base_name}_{timestamp}{ext}")
        
        # Move the file
        shutil.move(file_path, processed_path)
        logging.info(f"Moved {file_path} to {processed_path}")
        return True
    except Exception as e:
        logging.error(f"Error moving file {file_path} to processed directory: {str(e)}")
        return False

async def main():
    """Main function to run the transcription process."""
    try:
        # Load configurations
        transcribe_config, output_config, model_capabilities = load_config()
        main_config = load_main_config()
        
        # Get directories from main config
        downloads_dir = main_config.get("downloads_directory", "./downloads")
        processed_dir = main_config.get("processed_directory", "./processed_audio")
        output_file = main_config.get("output_file", "transcription.txt")
        
        # Check for valid model type
        model_type = transcribe_config["model_type"]
        if model_type not in ["whisper-1", "4o-transcribe"]:
            logging.error(f"Invalid model type for this script: {model_type}")
            logging.error("This script only supports 'whisper-1' and '4o-transcribe' models.")
            logging.error("Use local_whisper.py for local transcription or run setup_transcribe_model.py to change model type.")
            sys.exit(1)
        
        # Ensure the processed directory exists
        if not ensure_processed_directory(processed_dir):
            sys.exit(1)
        
        # Find audio files to transcribe
        audio_files = find_audio_files(downloads_dir)
        
        if not audio_files:
            logging.info(f"No audio files found in {downloads_dir}")
            return
        
        logging.info(f"Found {len(audio_files)} audio files to transcribe")
        
        # Transcribe the audio files
        transcripts = await transcribe_audio_files(audio_files, transcribe_config, output_config)
        
        if not transcripts:
            logging.warning("No transcriptions produced")
            return
        
        # Save the transcriptions
        if save_transcriptions(transcripts, output_file, output_config.get("append_output", False)):
            # Move processed files
            for file_path in audio_files:
                move_to_processed(file_path, processed_dir)
        
    except Exception as e:
        logging.error(f"Error in transcription process: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Transcribe audio files using OpenAI API")
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main()) 