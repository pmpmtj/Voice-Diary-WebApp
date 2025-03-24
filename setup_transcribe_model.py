#!/usr/bin/env python3
"""
Setup Transcribe Model

This script allows you to configure which transcription model to use:
1. Local Whisper (using local model files)
2. OpenAI Whisper API (whisper-1)
3. OpenAI 4o Transcribe API

It updates the transcribe_config.py file with your selected configuration.
"""

import os
import sys
import json
import argparse
import shutil
import re
from getpass import getpass

def load_config():
    """Load the transcription configuration."""
    try:
        from transcribe_config import TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
        return TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
    except ImportError:
        print("Error: Could not import transcribe_config.py. Make sure the file exists.")
        sys.exit(1)

def save_config(config):
    """Save the updated configuration to transcribe_config.py."""
    # Read the existing file content
    try:
        with open('transcribe_config.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: transcribe_config.py not found.")
        sys.exit(1)
    
    # Create a backup
    shutil.copy2('transcribe_config.py', 'transcribe_config.py.bak')
    print(f"Created backup: transcribe_config.py.bak")
    
    # Find the TRANSCRIBE_CONFIG dictionary and update it
    pattern = r"TRANSCRIBE_CONFIG\s*=\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    config_str = "TRANSCRIBE_CONFIG = " + json.dumps(config, indent=4).replace("null", "None").replace("true", "True").replace("false", "False")
    
    # Replace single quotes for string values but keep "None", "True", "False" as is
    config_str = re.sub(r'"([^"]+)":', r"'\1':", config_str)  # Replace double quotes in keys with single quotes
    config_str = re.sub(r':\s*"([^"]+)"', r": '\1'", config_str)  # Replace double quotes for string values with single quotes
    
    updated_content = re.sub(pattern, config_str, content, flags=re.DOTALL)
    
    # Write the updated content back to the file
    with open('transcribe_config.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("Configuration updated successfully!")

def test_openai_api(api_key):
    """Test if the OpenAI API key is valid."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        models = client.models.list()
        return True, "API key is valid. Connection to OpenAI successful."
    except Exception as e:
        return False, f"Error connecting to OpenAI API: {str(e)}"

def interactive_setup():
    """Interactive setup for transcription model configuration."""
    current_config, output_config, model_capabilities = load_config()
    
    print("\n===== Transcription Model Setup =====\n")
    print("Available transcription models:")
    print("1. Local Whisper (runs on your machine)")
    print("2. OpenAI Whisper API (whisper-1)")
    print("3. OpenAI 4o Transcribe API (gpt-4o)")
    
    while True:
        try:
            choice = int(input("\nSelect a model (1-3): "))
            if choice < 1 or choice > 3:
                print("Invalid choice. Please select 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    if choice == 1:
        # Local Whisper setup
        current_config["model_type"] = "local"
        print("\n== Local Whisper Setup ==")
        print("Available models: tiny, base, small, medium, large")
        print("Note: Larger models are more accurate but require more resources")
        
        model_name = input(f"Model name [{current_config['local_model']['model_name']}]: ").strip()
        if model_name and model_name in ["tiny", "base", "small", "medium", "large"]:
            current_config["local_model"]["model_name"] = model_name
        
        model_dir = input(f"Model directory [{current_config['local_model']['model_directory']}]: ").strip()
        if model_dir:
            current_config["local_model"]["model_directory"] = model_dir
        
        device = input(f"Device (cuda/cpu) [{current_config['local_model']['device']}]: ").strip()
        if device and device in ["cuda", "cpu"]:
            current_config["local_model"]["device"] = device
        
    else:
        # OpenAI API setup (whisper-1 or 4o)
        if choice == 2:
            current_config["model_type"] = "whisper-1"
            print("\n== OpenAI Whisper API Setup ==")
        else:
            current_config["model_type"] = "4o-transcribe"
            print("\n== OpenAI 4o Transcribe API Setup ==")
        
        # Get API key
        api_key = current_config.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
        new_api_key = getpass("OpenAI API Key (press Enter to use environment variable or current value): ").strip()
        
        if new_api_key:
            print("Testing API key...")
            success, message = test_openai_api(new_api_key)
            if success:
                print(f"✓ {message}")
                current_config["api_key"] = new_api_key
            else:
                print(f"✗ {message}")
                use_anyway = input("Use this API key anyway? (y/n): ").lower()
                if use_anyway == 'y':
                    current_config["api_key"] = new_api_key
                else:
                    print("Setup canceled. Please try again with a valid API key.")
                    return
        
        # Advanced settings
        print("\nWould you like to configure advanced settings? (y/n)")
        advanced = input().lower() == 'y'
        
        if advanced:
            if choice == 2:
                # Whisper-1 advanced settings
                config_section = current_config["whisper_api"]
                
                language = input("Language code (e.g., 'en', leave empty for auto-detection): ").strip()
                config_section["language"] = language if language else None
                
                prompt = input("Processing prompt (context to help guide transcription): ").strip()
                config_section["prompt"] = prompt
                
                formats = ["text", "vtt", "srt", "verbose_json", "json"]
                print(f"Available formats: {', '.join(formats)}")
                format_choice = input(f"Response format [{config_section['response_format']}]: ").strip()
                if format_choice in formats:
                    config_section["response_format"] = format_choice
                
                temp = input(f"Temperature (0.0-1.0) [{config_section['temperature']}]: ").strip()
                try:
                    temp_val = float(temp)
                    if 0.0 <= temp_val <= 1.0:
                        config_section["temperature"] = temp_val
                except ValueError:
                    pass  # Keep default if invalid
            
            else:
                # 4o-transcribe advanced settings
                config_section = current_config["4o_transcribe"]
                
                language = input("Language code (e.g., 'en', leave empty for auto-detection): ").strip()
                config_section["language"] = language if language else None
                
                prompt = input("Processing prompt (context to help guide transcription): ").strip()
                config_section["prompt"] = prompt
                
                formats = ["text", "json"]
                print(f"Available formats: {', '.join(formats)}")
                format_choice = input(f"Response format [{config_section['response_format']}]: ").strip()
                if format_choice in formats:
                    config_section["response_format"] = format_choice
                
                temp = input(f"Temperature (0.0-1.0) [{config_section['temperature']}]: ").strip()
                try:
                    temp_val = float(temp)
                    if 0.0 <= temp_val <= 1.0:
                        config_section["temperature"] = temp_val
                except ValueError:
                    pass  # Keep default if invalid
    
    # Common settings for all models
    print("\n== Common Settings ==")
    
    chunk_audio = input(f"Chunk audio for processing (True/False) [{current_config['chunk_audio']}]: ").strip()
    if chunk_audio.lower() in ["true", "false"]:
        current_config["chunk_audio"] = chunk_audio.lower() == "true"
    
    if current_config["chunk_audio"]:
        max_chunk = input(f"Maximum chunk size in minutes [{current_config['max_chunk_size'] // (60 * 1000)}]: ").strip()
        try:
            chunk_minutes = int(max_chunk)
            current_config["max_chunk_size"] = chunk_minutes * 60 * 1000  # Convert to milliseconds
        except ValueError:
            pass  # Keep default if invalid
    
    vad_filter = input(f"Apply voice activity detection (True/False) [{current_config['vad_filter']}]: ").strip()
    if vad_filter.lower() in ["true", "false"]:
        current_config["vad_filter"] = vad_filter.lower() == "true"
    
    # Output settings
    print("\n== Output Settings ==")
    print(f"Current output file: {output_config['output_file']}")
    
    # Save the updated configuration
    save_config(current_config)
    print(f"\nTranscription model set to: {current_config['model_type']}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Setup transcription model")
    parser.add_argument(
        "--model",
        choices=["local", "whisper-1", "4o-transcribe"],
        help="Set the transcription model type directly"
    )
    parser.add_argument(
        "--api-key",
        help="Set the OpenAI API key directly (only applicable for whisper-1 and 4o-transcribe)"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the current configuration without modifying it"
    )
    return parser.parse_args()

def show_current_config():
    """Display the current configuration."""
    current_config, output_config, model_capabilities = load_config()
    
    print("\n===== Current Transcription Configuration =====\n")
    print(f"Model Type: {current_config['model_type']}")
    
    if current_config["model_type"] == "local":
        print("\nLocal Whisper Configuration:")
        print(f"  Model: {current_config['local_model']['model_name']}")
        print(f"  Directory: {current_config['local_model']['model_directory']}")
        print(f"  Device: {current_config['local_model']['device']}")
        
    elif current_config["model_type"] == "whisper-1":
        print("\nOpenAI Whisper API Configuration:")
        print(f"  API Key: {'Configured' if current_config.get('api_key') or os.environ.get('OPENAI_API_KEY') else 'Not configured'}")
        print(f"  Language: {current_config['whisper_api']['language'] or 'Auto-detect'}")
        print(f"  Response Format: {current_config['whisper_api']['response_format']}")
        print(f"  Temperature: {current_config['whisper_api']['temperature']}")
        
    elif current_config["model_type"] == "4o-transcribe":
        print("\nOpenAI 4o Transcribe Configuration:")
        print(f"  API Key: {'Configured' if current_config.get('api_key') or os.environ.get('OPENAI_API_KEY') else 'Not configured'}")
        print(f"  Language: {current_config['4o_transcribe']['language'] or 'Auto-detect'}")
        print(f"  Response Format: {current_config['4o_transcribe']['response_format']}")
        print(f"  Temperature: {current_config['4o_transcribe']['temperature']}")
    
    print("\nCommon Settings:")
    print(f"  Chunk Audio: {current_config['chunk_audio']}")
    print(f"  Max Chunk Size: {current_config['max_chunk_size'] // (60 * 1000)} minutes")
    print(f"  VAD Filter: {current_config['vad_filter']}")
    
    print("\nOutput Settings:")
    print(f"  Output File: {output_config['output_file']}")
    print(f"  Output Format: {output_config['output_format']}")
    print(f"  Include Timestamps: {output_config['timestamps']}")
    print()

def command_line_setup(args):
    """Configure via command line arguments."""
    current_config, _, _ = load_config()
    
    if args.model:
        current_config["model_type"] = args.model
        print(f"Model type set to: {args.model}")
    
    if args.api_key and args.model in ["whisper-1", "4o-transcribe"]:
        current_config["api_key"] = args.api_key
        print("API key configured")
    
    if args.model or args.api_key:
        save_config(current_config)
        print("Configuration updated successfully")

def main():
    """Main function to run the setup process."""
    args = parse_args()
    
    if args.show:
        show_current_config()
    elif args.model or args.api_key:
        command_line_setup(args)
    else:
        interactive_setup()

if __name__ == "__main__":
    main() 