#!/usr/bin/env python3
"""
Audio Diary System Status

This script displays the current status and configuration of the audio diary system:
- Scheduler settings (runs per day, next scheduled run)
- Transcription model details (type, endpoint, settings)
- OpenAI instruction model details (model type, endpoint, settings)
- System health and file statistics
"""

import os
import sys
import json
import datetime
import argparse
from pathlib import Path
import textwrap

def load_main_config():
    """Load the main configuration from config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config.json: {str(e)}")
        return {}

def load_transcribe_config():
    """Load the transcription configuration"""
    try:
        from transcribe_config import TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
        return TRANSCRIBE_CONFIG, OUTPUT_CONFIG, MODEL_CAPABILITIES
    except ImportError:
        print("Transcription config not found. Run setup_transcribe_model.py to configure.")
        return {}, {}, {}

def load_openai_config():
    """Load the OpenAI processing configuration"""
    try:
        from openai_config import OPENAI_CONFIG
        return OPENAI_CONFIG
    except ImportError:
        print("OpenAI config not found. Run setup_openai.py to configure.")
        return {}

def check_api_keys():
    """Check for API keys in configs and environment"""
    keys = {
        "OPENAI_API_KEY": {
            "env": os.environ.get("OPENAI_API_KEY") is not None,
            "transcribe_config": False,
            "openai_config": False
        }
    }
    
    # Check transcribe_config
    try:
        from transcribe_config import TRANSCRIBE_CONFIG
        keys["OPENAI_API_KEY"]["transcribe_config"] = bool(TRANSCRIBE_CONFIG.get("api_key", ""))
    except:
        pass
    
    # Check openai_config
    try:
        from openai_config import OPENAI_CONFIG
        keys["OPENAI_API_KEY"]["openai_config"] = bool(OPENAI_CONFIG.get("api_key", ""))
    except:
        pass
    
    return keys

def get_file_stats():
    """Get statistics about important files"""
    stats = {}
    
    # Check download directory
    download_path = Path("./downloads")
    if download_path.exists() and download_path.is_dir():
        audio_files = list(download_path.glob("*.mp3")) + list(download_path.glob("*.m4a")) + \
                      list(download_path.glob("*.wav")) + list(download_path.glob("*.ogg")) + \
                      list(download_path.glob("*.flac"))
        stats["downloads"] = {
            "exists": True,
            "audio_files": len(audio_files),
            "last_modified": datetime.datetime.fromtimestamp(download_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if audio_files else "N/A"
        }
    else:
        stats["downloads"] = {"exists": False}
    
    # Check processed directory
    processed_path = Path("./processed_audio")
    if processed_path.exists() and processed_path.is_dir():
        audio_files = list(processed_path.glob("*.mp3")) + list(processed_path.glob("*.m4a")) + \
                      list(processed_path.glob("*.wav")) + list(processed_path.glob("*.ogg")) + \
                      list(processed_path.glob("*.flac"))
        stats["processed"] = {
            "exists": True,
            "audio_files": len(audio_files),
            "last_modified": datetime.datetime.fromtimestamp(processed_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if audio_files else "N/A"
        }
    else:
        stats["processed"] = {"exists": False}
    
    # Check received transcriptions directory
    received_path = Path("./received_transcriptions")
    if received_path.exists() and received_path.is_dir():
        transcription_files = list(received_path.glob("*.txt"))
        
        # Count transcriptions by model type
        model_counts = {}
        for file in transcription_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read(200)  # Read just the header
                    if "# Model:" in content:
                        model_line = [line for line in content.split('\n') if "# Model:" in line][0]
                        model_type = model_line.replace("# Model:", "").strip()
                        model_counts[model_type] = model_counts.get(model_type, 0) + 1
            except:
                pass
        
        stats["received_transcriptions"] = {
            "exists": True,
            "files": len(transcription_files),
            "model_counts": model_counts,
            "last_modified": datetime.datetime.fromtimestamp(received_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if transcription_files else "N/A"
        }
    else:
        stats["received_transcriptions"] = {"exists": False}
    
    # Check transcription file
    transcription_path = Path("transcription.txt")
    if transcription_path.exists() and transcription_path.is_file():
        stats["transcription"] = {
            "exists": True,
            "size": f"{transcription_path.stat().st_size / 1024:.2f} KB",
            "last_modified": datetime.datetime.fromtimestamp(transcription_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        stats["transcription"] = {"exists": False}
    
    # Check diary entries
    diary_files = list(Path(".").glob("*_ongoing_entries.txt"))
    if diary_files:
        stats["diary"] = {
            "exists": True,
            "files": len(diary_files),
            "latest": max(diary_files, key=lambda p: p.stat().st_mtime).name,
            "last_modified": datetime.datetime.fromtimestamp(max(diary_files, key=lambda p: p.stat().st_mtime).stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        stats["diary"] = {"exists": False}
    
    # Check to-do file
    todo_path = Path("to_do.txt")
    if todo_path.exists() and todo_path.is_file():
        with open(todo_path, 'r', encoding='utf-8') as f:
            todo_content = f.read()
        stats["todo"] = {
            "exists": True,
            "size": f"{todo_path.stat().st_size / 1024:.2f} KB",
            "items": todo_content.count("- "),
            "last_modified": datetime.datetime.fromtimestamp(todo_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        stats["todo"] = {"exists": False}
    
    return stats

def format_as_table(data, headers=None, column_widths=None):
    """Format data as a simple ASCII table"""
    if not data:
        return ""
    
    if headers:
        data = [headers] + data
    
    if not column_widths:
        column_widths = [max(len(str(row[i])) for row in data) for i in range(len(data[0]))]
    
    # Create the format string based on column widths
    format_str = " | ".join(f"{{:{width}}}" for width in column_widths)
    
    # Create the header separator
    separator = "-+-".join("-" * width for width in column_widths)
    
    # Format the table
    result = []
    for i, row in enumerate(data):
        result.append(format_str.format(*[str(item) for item in row]))
        if i == 0 and headers:
            result.append(separator)
    
    return "\n".join(result)

def get_next_run_time(config):
    """Get the next scheduled run time based on config"""
    runs_per_day = config.get("scheduler", {}).get("runs_per_day", 1)
    
    if runs_per_day == 0:
        return "One-time run (no scheduling)"
    
    # Calculate interval in seconds
    seconds_per_day = 86400
    interval_seconds = seconds_per_day / runs_per_day
    
    # Look for the log file to determine last run time
    log_file = config.get("scheduler", {}).get("log_file", "pipeline_scheduler.log")
    last_run_time = None
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            # Search for "Starting pipeline execution" lines in reverse
            for line in reversed(lines):
                if "Starting pipeline execution" in line:
                    # Extract timestamp
                    timestamp_part = line.split(" - ")[0].strip()
                    last_run_time = datetime.datetime.strptime(timestamp_part, "%Y-%m-%d %H:%M:%S,%f")
                    break
        except:
            pass
    
    if last_run_time:
        next_run_time = last_run_time + datetime.timedelta(seconds=interval_seconds)
        # If next run time is in the past, calculate the next future run
        if next_run_time < datetime.datetime.now():
            elapsed = (datetime.datetime.now() - last_run_time).total_seconds()
            periods_elapsed = int(elapsed / interval_seconds) + 1
            next_run_time = last_run_time + datetime.timedelta(seconds=periods_elapsed * interval_seconds)
        
        return next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return "Unknown (no previous runs found)"

def get_transcribe_model_info(transcribe_config):
    """Get information about the transcription model"""
    model_type = transcribe_config.get("model_type", "local")
    
    if model_type == "local":
        model_name = transcribe_config.get("local_model", {}).get("model_name", "base")
        device = transcribe_config.get("local_model", {}).get("device", "cpu")
        return {
            "type": "Local Whisper",
            "model": f"{model_name} (running on {device})",
            "endpoint": "N/A (local processing)",
            "details": f"Local whisper model stored in {transcribe_config.get('local_model', {}).get('model_directory', './model')}"
        }
    elif model_type == "whisper-1":
        return {
            "type": "OpenAI Whisper API",
            "model": "whisper-1",
            "endpoint": "https://api.openai.com/v1/audio/transcriptions",
            "details": f"Response format: {transcribe_config.get('whisper_api', {}).get('response_format', 'text')}, Language: {transcribe_config.get('whisper_api', {}).get('language', 'auto-detect')}"
        }
    elif model_type == "4o-transcribe":
        return {
            "type": "OpenAI 4o Transcribe",
            "model": transcribe_config.get("4o_transcribe", {}).get("model", "gpt-4o"),
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "details": f"Response format: {transcribe_config.get('4o_transcribe', {}).get('response_format', 'text')}, Language: {transcribe_config.get('4o_transcribe', {}).get('language', 'auto-detect')}"
        }
    else:
        return {
            "type": "Unknown",
            "model": "N/A",
            "endpoint": "N/A",
            "details": "Unknown transcription model type"
        }

def get_openai_model_info(openai_config):
    """Get information about the OpenAI instruction model"""
    model = openai_config.get("model", "gpt-4o")
    
    # Determine the endpoint based on the model name
    if model.startswith("gpt-4") or model.startswith("gpt-3.5"):
        endpoint = "https://api.openai.com/v1/chat/completions"
    else:
        endpoint = "Unknown endpoint"
    
    return {
        "type": "OpenAI API",
        "model": model,
        "endpoint": endpoint,
        "details": f"Temperature: {openai_config.get('temperature', 0.3)}, Max tokens: {openai_config.get('max_tokens', 'Not specified')}"
    }

def display_system_status(args):
    """Display the complete system status"""
    # Load configurations
    main_config = load_main_config()
    transcribe_config, output_config, model_capabilities = load_transcribe_config()
    openai_config = load_openai_config()
    api_keys = check_api_keys()
    file_stats = get_file_stats()
    
    # Header
    print("\n" + "=" * 80)
    print(" " * 25 + "AUDIO DIARY SYSTEM STATUS")
    print("=" * 80)
    
    # Scheduler information
    print("\n📅 SCHEDULER")
    print("-" * 80)
    runs_per_day = main_config.get("scheduler", {}).get("runs_per_day", 1)
    
    if runs_per_day == 0:
        print("Mode: One-time run (no scheduling)")
    else:
        print(f"Runs per day: {runs_per_day}")
        print(f"Interval: Every {86400 // runs_per_day} seconds ({86400 // runs_per_day // 60} minutes)")
        print(f"Next scheduled run: {get_next_run_time(main_config)}")
    
    # Transcription model information
    print("\n🎤 TRANSCRIPTION MODEL")
    print("-" * 80)
    transcribe_info = get_transcribe_model_info(transcribe_config)
    print(f"Type: {transcribe_info['type']}")
    print(f"Model: {transcribe_info['model']}")
    print(f"Endpoint: {transcribe_info['endpoint']}")
    print(f"Details: {transcribe_info['details']}")
    
    if transcribe_config.get("chunk_audio", False):
        chunk_size_minutes = transcribe_config.get("max_chunk_size", 24 * 60 * 1000) // (60 * 1000)
        print(f"Audio chunking: Enabled (max chunk size: {chunk_size_minutes} minutes)")
    else:
        print("Audio chunking: Disabled")
    
    # OpenAI instruction model information
    print("\n🧠 INSTRUCTION MODEL")
    print("-" * 80)
    if openai_config:
        openai_info = get_openai_model_info(openai_config)
        print(f"Type: {openai_info['type']}")
        print(f"Model: {openai_info['model']}")
        print(f"Endpoint: {openai_info['endpoint']}")
        print(f"Details: {openai_info['details']}")
        
        # Cost information
        if "cost_estimates" in args and "COST_ESTIMATES" in dir(openai_config):
            print("\nCost estimates:")
            for model, costs in openai_config.COST_ESTIMATES.items():
                print(f"  - {model}: ${costs['input']}/1K tokens (input), ${costs['output']}/1K tokens (output)")
    else:
        print("OpenAI configuration not found. Run setup_openai.py to configure.")
    
    # API Keys status
    print("\n🔑 API KEYS")
    print("-" * 80)
    for key_name, sources in api_keys.items():
        sources_found = [source for source, found in sources.items() if found]
        if sources_found:
            print(f"{key_name}: ✅ Configured in {', '.join(sources_found)}")
        else:
            print(f"{key_name}: ❌ Not configured")
    
    # File statistics
    if "files" in args:
        print("\n📁 FILE STATISTICS")
        print("-" * 80)
        
        # Downloads directory
        if file_stats["downloads"]["exists"]:
            print(f"Downloads directory: {file_stats['downloads']['audio_files']} audio files")
            if file_stats["downloads"]["audio_files"] > 0:
                print(f"  Last modified: {file_stats['downloads']['last_modified']}")
        else:
            print("Downloads directory: Not found")
        
        # Processed directory
        if file_stats["processed"]["exists"]:
            print(f"Processed directory: {file_stats['processed']['audio_files']} audio files")
            if file_stats["processed"]["audio_files"] > 0:
                print(f"  Last modified: {file_stats['processed']['last_modified']}")
        else:
            print("Processed directory: Not found")
        
        # Received transcriptions directory
        if file_stats["received_transcriptions"]["exists"]:
            print(f"Received transcriptions: {file_stats['received_transcriptions']['files']} files")
            if file_stats["received_transcriptions"]["model_counts"]:
                print("  Model breakdown:")
                for model, count in file_stats["received_transcriptions"]["model_counts"].items():
                    print(f"    - {model}: {count} transcriptions")
            if file_stats["received_transcriptions"]["files"] > 0:
                print(f"  Last modified: {file_stats['received_transcriptions']['last_modified']}")
        else:
            print("Received transcriptions: Not found")
        
        # Transcription file
        if file_stats["transcription"]["exists"]:
            print(f"Transcription file: {file_stats['transcription']['size']}")
            print(f"  Last modified: {file_stats['transcription']['last_modified']}")
        else:
            print("Transcription file: Not found")
        
        # Diary entries
        if file_stats["diary"]["exists"]:
            print(f"Diary entries: {file_stats['diary']['files']} files")
            print(f"  Latest file: {file_stats['diary']['latest']}")
            print(f"  Last modified: {file_stats['diary']['last_modified']}")
        else:
            print("Diary entries: Not found")
        
        # To-do file
        if file_stats["todo"]["exists"]:
            print(f"To-do file: {file_stats['todo']['size']} ({file_stats['todo']['items']} items)")
            print(f"  Last modified: {file_stats['todo']['last_modified']}")
        else:
            print("To-do file: Not found")
    
    print("\n" + "=" * 80)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Display audio diary system status")
    parser.add_argument("--files", action="store_true", help="Include file statistics")
    parser.add_argument("--cost-estimates", action="store_true", help="Include cost estimates for OpenAI API")
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    display_system_status(vars(args))

if __name__ == "__main__":
    main() 