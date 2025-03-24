# Transcription Options

This project now supports multiple transcription models:

1. **Local Whisper** - Uses OpenAI's Whisper model locally (default)
2. **OpenAI Whisper API (whisper-1)** - Uses OpenAI's original whisper-1 API endpoint
3. **OpenAI 4o Transcribe** - Uses the new GPT-4o model's audio transcription capabilities

## Setting Up Transcription Models

Use the `setup_transcribe_model.py` script to configure which transcription model to use:

```bash
python setup_transcribe_model.py
```

This will start an interactive setup where you can select your preferred model and configure its settings.

### Command Line Options

You can also set the model directly via command line:

```bash
# Set to use OpenAI's whisper-1 API
python setup_transcribe_model.py --model whisper-1

# Set to use GPT-4o for transcription
python setup_transcribe_model.py --model 4o-transcribe

# Set to use local Whisper
python setup_transcribe_model.py --model local

# Show current configuration
python setup_transcribe_model.py --show
```

## Model Comparison

| Feature | Local Whisper | Whisper-1 API | 4o Transcribe |
|---------|--------------|---------------|---------------|
| Price | Free (local) | $ | $$ |
| Max Length | 25 minutes | 25 minutes | 4 hours |
| Accuracy | Good | Better | Best |
| Speed | Depends on hardware | Fast | Fast |
| Internet | Not required | Required | Required |
| Languages | 99 languages | All languages | All languages |

## Configuration Details

The configuration is stored in `transcribe_config.py`. The system will automatically use the appropriate transcription script based on the configured model:

- `local_whisper.py` for local models
- `openai_whisper.py` for whisper-1 and 4o-transcribe models

## Example Usage

### Local Whisper

Good for privacy-focused setups or when internet connectivity is limited:

```bash
python setup_transcribe_model.py --model local
python scheduler.py
```

### OpenAI Whisper API

Good balance of accuracy and cost:

```bash
python setup_transcribe_model.py --model whisper-1
python scheduler.py
```

### 4o Transcribe

Best accuracy and features:

```bash
python setup_transcribe_model.py --model 4o-transcribe
python scheduler.py
```

## Troubleshooting

If you encounter issues with transcription:

1. **API Key Issues**: Run `setup_transcribe_model.py` to reconfigure your API key
2. **Model Not Found**: Ensure you have the correct OpenAI API access level
3. **Local Model Issues**: Check if you have the right CUDA/CPU configurations

## Advanced Chunking

For very long audio files, the system can automatically chunk audio before transcription. Configure this in the setup or directly in `transcribe_config.py`:

```python
TRANSCRIBE_CONFIG = {
    # ... other settings ...
    "chunk_audio": True,
    "max_chunk_size": 24 * 60 * 1000,  # 24 minutes in milliseconds
}
``` 