"""
Configuration settings for transcription models.
This file contains settings for different transcription models:
1. Local Whisper (using local model files)
2. OpenAI Whisper API (whisper-1)
3. OpenAI 4o Transcribe API
"""

# Transcription model configuration
TRANSCRIBE_CONFIG = {
    'model_type': 'whisper-1',
    'api_key': "",
    'local_model': {
        'model_name': 'base',
        'model_directory': './model',
        'device': 'cpu'
    },
    'whisper_api': {
        'model': 'whisper-1',
        'language': None,
        'prompt': "",
        'response_format': 'text',
        'temperature': 0.0
    },
    '4o_transcribe': {
        'model': 'gpt-4o',
        'language': None,
        'prompt': "",
        'response_format': 'text',
        'temperature': 0.0
    },
    'chunk_audio': False,
    'max_chunk_size': 1440000,
    'vad_filter': False,
    'vad_threshold': 0.5
}

# Transcription output configuration
OUTPUT_CONFIG = {
    "output_format": "text",  # Options: "text", "json", "vtt", "srt"
    "output_file": "transcription.txt",  # Default output file
    "timestamps": False,  # Whether to include timestamps
    "word_timestamps": False,  # Whether to include word-level timestamps (only available with certain models)
    "append_output": False,  # Whether to append to existing output file
}

# Meta-information about model capabilities
MODEL_CAPABILITIES = {
    "local": {
        "languages": ["en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk", "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk", "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw", "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc", "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo", "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl", "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"],
        "supports_word_timestamps": True,
        "max_input_length": "25 minutes",
        "chunk_size_required": True,
    },
    "whisper-1": {
        "languages": ["en"],
        "supports_word_timestamps": True,
        "max_input_length": "25 minutes",
        "chunk_size_required": False,
    },
    "4o-transcribe": {
        "languages": ["all languages"],
        "supports_word_timestamps": True, 
        "max_input_length": "4 hours",
        "chunk_size_required": False,
    }
} 