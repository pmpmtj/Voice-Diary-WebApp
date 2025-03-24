# Audio Diary with Whisper Transcription and OpenAI Processing

A complete audio diary system that:
1. Downloads audio recordings from Google Drive
2. Transcribes them using OpenAI's Whisper (locally)
3. Processes the transcriptions with OpenAI API to organize and extract insights
4. Maintains an ongoing record of diary entries and to-do items

## Features

- **Google Drive Integration**: Automatically downloads audio files from specified folders
- **Local Whisper Transcription**: Converts audio to text without sending data to external APIs
- **OpenAI-Powered Analysis**: Uses OpenAI API to organize transcriptions and extract to-do items
- **Scheduled Operation**: Runs automatically at configurable intervals with next sync time display
- **Flexible Configuration**: Easy to customize via config files
- **Date-Based File Management**: Creates separate diary files for each day with YYMMDD date prefixes
- **Cost Management**: Includes token counting and usage tracking for OpenAI API calls

## Quick Start

### Prerequisites

- Python 3.7 or higher
- PyTorch with CUDA support (recommended for GPU acceleration)
- Google Drive API credentials
- FFmpeg installed or available in the system path
- OpenAI API key (for diary processing)

### Installation

1. Clone this repository
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up Google Drive API credentials:
   - Create a project in Google Cloud Console
   - Enable the Google Drive API
   - Create OAuth credentials and download as `credentials.json`
   - Place `credentials.json` in the project directory

4. Set up the OpenAI API:
   - Get an API key from OpenAI (https://platform.openai.com/api-keys)
   - Run the setup script to configure it:
     ```
     python setup_openai.py
     ```

5. Configure the system:
   - Edit `config.json` to specify Google Drive folders and settings
   - Edit `openai_config.py` to customize the OpenAI model settings

6. Ensure FFmpeg is installed:
   - The system will try to find FFmpeg in your system PATH
   - Alternatively, place `ffmpeg.exe` in the project directory (Windows)
   - The scheduler will automatically configure FFmpeg at startup

### Running the Pipeline

Start the automated scheduler to run the pipeline at regular intervals:
```
python scheduler.py
```

The scheduler will:
- Download new audio files from Google Drive
- Transcribe them using Whisper
- Process the transcriptions with OpenAI API
- Display the next scheduled sync time
- Repeat at the interval specified in config.json

#### Configuring Scheduler Frequency

To configure how many times per day the pipeline runs:
```
python setup_num_runs.py <number_of_runs>
```

Examples:
```
python setup_num_runs.py 1     # Run once per day (every 24 hours)
python setup_num_runs.py 2     # Run twice per day (every 12 hours)
python setup_num_runs.py 24    # Run every hour
python setup_num_runs.py 0     # Run once and exit
```

To view the current schedule without changing it:
```
python setup_num_runs.py --show
```

Remember to restart the scheduler after changing the frequency for the changes to take effect.

### Individual Components

Run each step separately if needed:
```
python download-from-gdrive.py  # Download audio files
python local_whisper.py         # Transcribe audio files
python process_transcription.py # Process with OpenAI API
```

### Managing Diary Files

The system automatically creates date-prefixed diary files (e.g., `240323_ongoing_entries.txt`) for each day.

To manually set the date (useful after system downtime):
```
python scheduler.py --set-date YYMMDD
```

For example, to set the date to March 23, 2024:
```
python scheduler.py --set-date 240323
```

If no date is specified, it will use today's date:
```
python scheduler.py --set-date
```

## OpenAI API Integration

This project now uses OpenAI's API for processing transcriptions instead of a local LLM. This provides several benefits:

### Benefits of OpenAI API Integration

- **Faster Processing**: Cloud-based processing is much faster than local models
- **Higher Quality Results**: Access to state-of-the-art models like GPT-4o
- **Reduced Resource Requirements**: No need for powerful GPU or large model files
- **Simpler Setup**: Eliminates the need to download and manage large model files

### Configuration

The OpenAI integration can be configured in `openai_config.py`:

```python
# OpenAI API configuration
OPENAI_CONFIG = {
    # Your OpenAI API key
    "api_key": "",  # Set your API key here or use environment variable
    
    # The model to use for processing
    "model": "gpt-4o",  # Options: "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"
    
    # Generation parameters
    "temperature": 0.3,
    "max_tokens": 2048,
    # ... other parameters
}
```

### Cost Management

To help manage costs:

1. **Token Tracking**: The system logs token usage for each API call
2. **Caching**: Identical requests are cached to avoid redundant API calls
3. **Model Selection**: You can choose more cost-effective models like gpt-3.5-turbo
4. **Usage Logs**: Check `openai_usage.log` for detailed usage information

### Troubleshooting

- **API Key Issues**: Run `python setup_openai.py` to test and configure your API key
- **Cost Concerns**: Set `"model"` to `"gpt-3.5-turbo"` for more economical processing
- **Rate Limits**: The system includes automatic retries with exponential backoff

## How It Works

### 1. Audio Download

The `download-from-gdrive.py` script:
- Authenticates with Google Drive using OAuth
- Searches for audio files in configured folders
- Downloads files to the local `downloads` directory

### 2. Transcription

The `local_whisper.py` script:
- Loads a local Whisper model
- Transcribes all audio files in the `downloads` directory
- Saves transcriptions to a single file
- Moves processed audio files to the `processed_audio` directory

### 3. OpenAI Processing

The `process_transcription.py` script:
- Connects to the OpenAI API
- Reads the transcription file
- Processes the content to organize and analyze it
- Extracts to-do items and saves them to `to_do.txt`
- Adds the organized entry to the appropriate date-prefixed diary file

### 4. Scheduling

The `scheduler.py` script:
- Runs the complete pipeline at regular intervals
- Logs all operations for monitoring and debugging
- Displays the next scheduled run time
- Manages the sequence of operations
- Handles day changes and creates new diary files as needed

### 5. Date Management

The system:
- Tracks the current date in `config.json`
- Creates a new date-prefixed file each day
- Detects date changes even after system downtime
- Provides a utility for manually setting dates when needed

## Configuration

### Main Configuration (config.json)

```json
{
  "downloads_directory": "./downloads",
  "output_file": "transcription.txt",
  "processed_directory": "./processed_audio",
  "model": {
    "folder": "path/to/whisper/model",
    "name": "my_model.pt"
  },
  "diary_manager": {
    "current_date": "240323",
    "entries_file_format": "{date}_ongoing_entries.txt",
    "legacy_file": "ongoing_entries.txt",
    "auto_update_date": true
  },
  "scheduler": {
    "runs_per_day": 1,
    "log_file": "pipeline_scheduler.log",
    "log_level": "INFO",
    "scripts": {
      "download": "download-from-gdrive.py",
      "transcribe": "local_whisper.py",
      "process": "process_transcription.py"
    }
  }
}
```

### OpenAI Configuration (openai_config.py)

```python
OPENAI_CONFIG = {
    # API key and model settings
    "api_key": "",  # Set your API key here or use environment variable
    "model": "gpt-4o",
    
    # Generation parameters
    "temperature": 0.3,
    "max_tokens": 2048,
    "top_p": 0.9,
    
    # Cost control options
    "enable_caching": True,
    "track_usage": True,
}
```

## Output Files

- **transcription.txt**: Raw transcriptions from audio files
- **YYMMDD_ongoing_entries.txt**: Date-prefixed organized diary entries for each day
- **to_do.txt**: Extracted to-do items and action points
- **openai_usage.log**: Log of OpenAI API usage and token counts

## Troubleshooting

- **Google Drive Authentication**: If authorization fails, delete `token.pickle` and restart
- **Model Loading Issues**: Check paths in configuration files and adjust memory settings
- **OpenAI API Issues**: Run `python setup_openai.py` to diagnose and fix API problems
- **Transcription Quality**: Adjust Whisper settings in `config.json` for better results
- **FFmpeg Issues**: Make sure FFmpeg is installed and in your PATH, or place ffmpeg.exe in the project directory
- **Date Management**: If the system was down for multiple days, use the `--set-date` utility to set the correct date

## System Requirements

- **Minimum**: 8GB RAM, modern CPU, internet connection
- **Recommended**: 16GB+ RAM, NVIDIA GPU with 8GB+ VRAM for faster local transcription
- **Disk Space**: ~2GB for Whisper model and audio files
- **FFmpeg**: Required for audio processing (automatically detected or can be placed in project directory)
- **Internet**: Required for OpenAI API access and Google Drive integration

## License

[Insert license information]

---

For issues, suggestions, or contributions, please open an issue in the repository. 