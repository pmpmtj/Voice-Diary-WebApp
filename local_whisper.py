#!/usr/bin/env python3
"""
Local Whisper - A customized version of OpenAI's Whisper CLI that only uses models from the local ./model directory

This script is a modified version of Whisper's CLI that:
1. Only loads models from the ./model directory
2. Does not download models from the internet
3. Uses configuration from config.json for paths and settings
4. Automatically transcribes all files in the downloads directory
5. Creates a single transcription file for OpenAI API processing
"""

import sys
import io
import argparse
import os
import sys
import traceback
import warnings
import json
from typing import List, Optional, Tuple, Union
from datetime import datetime
import re

import numpy as np
import torch
import tqdm
# Ensure whisper is importable
try:
    import whisper
    from whisper.audio import FRAMES_PER_SECOND, HOP_LENGTH, N_FRAMES, SAMPLE_RATE
    from whisper.tokenizer import LANGUAGES, TO_LANGUAGE_CODE
    from whisper.utils import (
        format_timestamp, optional_float, optional_int, str2bool, get_writer
    )
except ImportError:
    print("Error: Whisper package not found. Please install it using pip.")
    sys.exit(1)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_config(config_path="config.json"):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        print(f"Configuration file {config_path} not found. Using default settings.")
        # Return a default configuration
        return {
            "downloads_directory": "./downloads",
            "output_file": "transcription.txt",
            "processed_directory": "./processed_audio",
            "model": {
                "folder": "./model",
                "name": "my_model.pt"
            },
            "transcription": {
                "task": "transcribe",
                "language": None,
                "temperature": 0,
                "word_timestamps": False
            },
            "advanced": {
                "best_of": 5,
                "beam_size": 5,
                "patience": None,
                "length_penalty": None,
                "suppress_tokens": "-1",
                "initial_prompt": None,
                "condition_on_previous_text": True,
                "fp16": True,
                "threads": 0
            },
            "verbose": True,
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    except json.JSONDecodeError:
        print(f"Error parsing {config_path}. Using default settings.")
        sys.exit(1)

def load_local_model(model_folder, model_name, device):
    """
    Load a Whisper model from the specified model folder
    
    Parameters:
    -----------
    model_folder : str
        Path to the folder containing the model
    model_name : str
        Name of the model file (with .pt extension)
    device : str
        The device to load the model onto ("cpu" or "cuda")
        
    Returns:
    --------
    model : whisper.model.Whisper
        The loaded Whisper model
    """
    if not os.path.exists(model_folder):
        os.makedirs(model_folder, exist_ok=True)
        print(f"Created directory {model_folder} - please place your models here")
    
    model_path = os.path.join(model_folder, model_name)
    
    if not os.path.isfile(model_path):
        available_models = [f for f in os.listdir(model_folder) if f.endswith(".pt")]
        if available_models:
            models_list = ", ".join(available_models)
            raise RuntimeError(
                f"Model '{model_name}' not found in {model_folder}. Available models: {models_list}"
            )
        else:
            raise RuntimeError(
                f"No models found in {model_folder}. Please place your .pt model files in this directory."
            )
    
    print(f"Loading model from {model_path}")
    checkpoint = torch.load(model_path, map_location=device)
    
    from whisper.model import Whisper, ModelDimensions
    dims = ModelDimensions(**checkpoint["dims"])
    model = Whisper(dims)
    model.load_state_dict(checkpoint["model_state_dict"])
    
    return model.to(device)

def get_audio_files_from_directory(directory_path):
    """Get all audio files from the specified directory."""
    # Common audio file extensions
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']
    
    audio_files = []
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        print(f"Created directory {directory_path} - please place your audio files here")
        return []
    
    # List all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        # Check if it's a file and has an audio extension
        if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(file_path)
    
    # Sort audio files by filename (which now includes date prefix)
    # This ensures chronological processing
    audio_files.sort()
    
    return audio_files

def append_transcription_to_file(transcription, audio_file, output_file):
    """Append the transcription to the specified output file."""
    # Extract the basename from the full path
    base_filename = os.path.basename(audio_file)
    
    # Try to extract date from filename (assuming format YYYYMMDD_HHMMSS_mmm_originalname.ext)
    # First try the format with milliseconds
    date_match = re.match(r"^(\d{8}_\d{6}_\d{3})_(.+)$", base_filename)
    
    if date_match:
        # File has our date prefix format with milliseconds
        date_str = date_match.group(1)
        original_name = date_match.group(2)
        
        # Format the date for better readability
        try:
            # Parse with milliseconds format YYYYMMDD_HHMMSS_mmm
            recording_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S_%f')
            formatted_date = recording_date.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Show only milliseconds, not microseconds
            date_info = f"[Recorded at: {formatted_date}]"
        except ValueError:
            # Try the old format without milliseconds
            try:
                recording_date = datetime.strptime(date_str[:15], '%Y%m%d_%H%M%S')
                formatted_date = recording_date.strftime('%Y-%m-%d %H:%M:%S')
                date_info = f"[Recorded at: {formatted_date}]"
            except ValueError:
                date_info = f"[Original date prefix: {date_str}]"
                original_name = base_filename
    else:
        # Check for the old format without milliseconds
        date_match = re.match(r"^(\d{8}_\d{6})_(.+)$", base_filename)
        if date_match:
            # File has our older date prefix format without milliseconds
            date_str = date_match.group(1)
            original_name = date_match.group(2)
            
            try:
                recording_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                formatted_date = recording_date.strftime('%Y-%m-%d %H:%M:%S')
                date_info = f"[Recorded at: {formatted_date}]"
            except ValueError:
                date_info = f"[Original date prefix: {date_str}]"
                original_name = base_filename
        else:
            # No date prefix found, use only the original filename
            date_info = ""
            original_name = base_filename
    
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n--- Transcription of {original_name} ---\n")
        if date_info:
            f.write(f"{date_info}\n")
        f.write(f"[Transcribed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n\n")
        f.write(transcription)
        f.write("\n\n" + "-" * 80 + "\n")

def move_processed_files(audio_files, target_directory, verbose=True):
    """
    Move processed audio files to a target directory.
    
    Parameters:
    -----------
    audio_files : list
        List of paths to audio files that have been processed
    target_directory : str
        Path to the directory where processed files should be moved
    verbose : bool
        Whether to print progress messages
    
    Returns:
    --------
    moved_files : list
        List of files that were successfully moved
    """
    # Create the target directory if it doesn't exist
    if not os.path.exists(target_directory):
        os.makedirs(target_directory, exist_ok=True)
        if verbose:
            print(f"Created directory for processed files: {target_directory}")
    
    moved_files = []
    failed_moves = []
    
    if verbose:
        print(f"\nMoving processed audio files to {target_directory}...")
    
    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        target_path = os.path.join(target_directory, filename)
        
        # Check if a file with the same name already exists in the target directory
        if os.path.exists(target_path):
            # Add timestamp to filename to make it unique
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{name}_{timestamp}{ext}"
            target_path = os.path.join(target_directory, new_filename)
            
            if verbose:
                print(f"File {filename} already exists in target directory, renaming to {new_filename}")
        
        try:
            # Move the file
            os.rename(audio_file, target_path)
            moved_files.append(target_path)
            
            if verbose:
                print(f"Moved: {filename} -> {target_directory}")
                
        except Exception as e:
            failed_moves.append((audio_file, str(e)))
            if verbose:
                print(f"Failed to move {filename}: {str(e)}")
    
    # Print summary
    if verbose:
        if moved_files:
            print(f"\nSuccessfully moved {len(moved_files)} files to {target_directory}")
        if failed_moves:
            print(f"Failed to move {len(failed_moves)} files")
            for file_path, error in failed_moves:
                print(f"  - {os.path.basename(file_path)}: {error}")
    
    return moved_files

def initialize_transcription_file(output_file, verbose=True):
    """
    Initialize the transcription file with a header.
    
    Parameters:
    -----------
    output_file : str
        Path to the output file
    verbose : bool
        Whether to print progress messages
    """
    # Clear the file and add a header
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Audio Transcriptions - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Generated by Local Whisper\n")
            f.write(f"# Files processed in chronological order based on recording time\n\n")
        
        if verbose:
            print(f"Initialized transcription file: {output_file}")
            
    except Exception as e:
        print(f"Error initializing transcription file: {str(e)}")

def save_individual_transcription(transcript, audio_file, output_dir):
    """
    Save an individual transcription to the received_transcriptions directory
    with metadata about which model produced it and when.
    
    Args:
        transcript: The transcription text
        audio_file: The path to the original audio file
        output_dir: The directory to save transcriptions
    """
    try:
        # Create the directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        # Get the base filename without extension
        audio_filename = os.path.basename(audio_file)
        base_name, _ = os.path.splitext(audio_filename)
        
        # Create a filename with timestamp and model info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_name}_local_whisper_{timestamp}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        # Write the transcription with metadata
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Transcription of {audio_filename}\n")
            f.write(f"# Model: local_whisper\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Original file: {audio_file}\n\n")
            f.write(transcript)
        
        print(f"Saved individual transcription to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving individual transcription: {str(e)}")
        return False

def main():
    # Load configuration
    config = load_config()
    
    # Parse command-line arguments (these will override config file settings)
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using the local Whisper model with settings from config.json",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--config", type=str, default="config.json",
        help="path to the configuration file"
    )
    parser.add_argument(
        "--device", default=config["device"],
        help="device to use for PyTorch inference"
    )
    parser.add_argument(
        "--verbose", type=str2bool, default=config["verbose"],
        help="whether to print out the progress and debug messages"
    )
    
    args = parser.parse_args()
    
    # If a different config file was specified, reload the config
    if args.config != "config.json":
        config = load_config(args.config)
    
    # Extract configuration values
    model_folder = config["model"]["folder"]
    model_name = config["model"]["name"]
    downloads_dir = config["downloads_directory"]
    output_file = config["output_file"]
    processed_dir = config.get("processed_directory", "./processed_audio")  # Default if not in config
    verbose = args.verbose  # Use command-line argument if provided, otherwise use config
    device = args.device    # Use command-line argument if provided, otherwise use config
    
    transcription_config = config["transcription"]
    advanced_config = config["advanced"]
    
    # Set up multi-threading for CPU inference
    if advanced_config["threads"] > 0:
        torch.set_num_threads(advanced_config["threads"])
    
    # Process temperature
    temperature = transcription_config["temperature"]
    if temperature > 0:
        # Use a tuple of temperatures increasing up to 1.0 for fallback
        temperature = tuple(np.arange(temperature, 1.0 + 1e-6, 0.2))
    else:
        temperature = [temperature]
    
    # Initialize the model
    try:
        model = load_local_model(model_folder, model_name, device)
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        sys.exit(1)
    
    # Set English language for English-only models
    model_name_base = os.path.splitext(model_name)[0]
    language = transcription_config["language"]
    if model_name_base.endswith(".en") and language not in {"en", "English"}:
        if language is not None:
            warnings.warn(
                f"{model_name} is an English-only model but received '{language}'; using English instead."
            )
        language = "en"
    
    # Get all audio files from the downloads directory
    audio_files = get_audio_files_from_directory(downloads_dir)
    
    if not audio_files:
        print(f"No audio files found in {downloads_dir}. Please add audio files to this directory.")
        sys.exit(1)
    
    print(f"Found {len(audio_files)} audio files in {downloads_dir}")
    
    # Keep track of successfully processed files
    processed_files = []
    
    # Initialize output file with a header
    initialize_transcription_file(output_file, verbose)
    
    # Process each audio file
    for i, audio_path in enumerate(audio_files, 1):
        try:
            # Print which file we're processing
            if verbose:
                print(f"\nProcessing file {i}/{len(audio_files)}: {os.path.basename(audio_path)}")
            
            # Transcribe the audio
            result = whisper.transcribe(
                model=model,
                audio=audio_path,
                temperature=temperature,
                task=transcription_config["task"],
                language=language,
                verbose=verbose,
                word_timestamps=transcription_config["word_timestamps"],
                best_of=advanced_config["best_of"],
                beam_size=advanced_config["beam_size"],
                patience=advanced_config["patience"],
                length_penalty=advanced_config["length_penalty"],
                suppress_tokens=advanced_config["suppress_tokens"],
                initial_prompt=advanced_config["initial_prompt"],
                condition_on_previous_text=advanced_config["condition_on_previous_text"],
                fp16=advanced_config["fp16"],
            )
            
            # Extract the text from the result
            transcription_text = result["text"]
            
            # Append to the combined output file
            append_transcription_to_file(transcription_text, audio_path, output_file)
            
            # Add to list of successfully processed files
            processed_files.append(audio_path)
            
            if verbose:
                print(f"Transcription of {os.path.basename(audio_path)} appended to {output_file}")
                
            # After transcription is successfully created and before the file is moved to processed,
            # add code to save the individual transcription:
            received_dir = config.get("received_transcriptions_directory", "./received_transcriptions")
            save_individual_transcription(result["text"], audio_path, received_dir)
            
        except Exception as e:
            traceback.print_exc()
            print(f"Skipping {audio_path} due to {type(e).__name__}: {str(e)}")
    
    # Move successfully processed files to the processed directory
    if processed_files:
        move_processed_files(processed_files, processed_dir, verbose)
    
    print(f"\nAll transcriptions have been saved to {output_file}")
    print(f"The transcription file is ready for OpenAI API processing")

if __name__ == "__main__":
    main() 