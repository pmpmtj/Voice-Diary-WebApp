"""
Configuration settings for OpenAI API integration.
This file contains settings for the OpenAI API integration used for processing transcriptions.
"""

# OpenAI API configuration
OPENAI_CONFIG = {
    # Your OpenAI API key (left empty for security - set in environment variable or fill in)
    "api_key": "",  # Set your API key here or use environment variable OPENAI_API_KEY
    
    # The model to use for processing transcriptions
    "model": "gpt-3.5-turbo",  # Options: "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"
    
    # Generation parameters
    "temperature": 0.3,
    "max_tokens": 2048,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    
    # Cost control options
    "enable_caching": True,  # Cache identical requests to save on costs
    "track_usage": True,     # Track API usage in a log file
    
    # Response format options (for newer models)
    "response_format": "text",  # Can be "text" or "json"
}

# Usage tracking configuration
USAGE_TRACKING = {
    "log_file": "openai_usage.log",
    "log_level": "INFO",
    "track_tokens": True,
    "track_cost": True,
}

# Cost estimate configuration (per 1K tokens)
COST_ESTIMATES = {
    "gpt-4o": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-4o-mini": {
        "input": 0.005,
        "output": 0.015
    },
    "gpt-3.5-turbo": {
        "input": 0.001,
        "output": 0.002
    }
} 