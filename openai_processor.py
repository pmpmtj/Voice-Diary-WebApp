"""
OpenAI Processor Module

This module provides functions for processing transcriptions using the OpenAI API.
It replaces the local LLM processing with OpenAI's cloud-based API for faster processing.
"""

import os
import json
import logging
import time
import tiktoken
from datetime import datetime
import re
from typing import Dict, List, Optional, Union, Any

try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletion
    from openai.types import CompletionUsage
except ImportError:
    raise ImportError("OpenAI Python package is required. Install it with 'pip install openai'")

# Local imports
from openai_config import OPENAI_CONFIG, USAGE_TRACKING, COST_ESTIMATES

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(USAGE_TRACKING.get('log_file', 'openai_usage.log')),
        logging.StreamHandler()
    ]
)

# Cache for API requests to save costs
_api_cache = {}

def get_openai_client() -> OpenAI:
    """Initialize and return the OpenAI client"""
    api_key = OPENAI_CONFIG.get('api_key') or os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OpenAI API key is not set. Please set it in openai_config.py or as the OPENAI_API_KEY environment variable.")
    
    return OpenAI(api_key=api_key)

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logging.warning(f"Could not count tokens using tiktoken: {str(e)}")
        # Fallback: rough estimate (not as accurate)
        return len(text.split()) * 1.3  # Rough approximation

def estimate_cost(usage: CompletionUsage, model: str) -> float:
    """Estimate the cost based on token usage and model"""
    if model not in COST_ESTIMATES:
        logging.warning(f"Unknown model for cost estimation: {model}")
        return 0.0
    
    rates = COST_ESTIMATES[model]
    prompt_cost = (usage.prompt_tokens / 1000) * rates["input"]
    completion_cost = (usage.completion_tokens / 1000) * rates["output"]
    
    return prompt_cost + completion_cost

def log_usage(response: ChatCompletion, prompt_text: str, model: str) -> None:
    """Log API usage information"""
    if not USAGE_TRACKING.get('track_tokens', True):
        return
    
    usage = response.usage
    cost = estimate_cost(usage, model)
    
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost": f"${cost:.6f}",
        "prompt_excerpt": prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text
    }
    
    logging.info(f"OpenAI API Usage: {json.dumps(log_entry)}")

def call_openai_api(
    messages: List[Dict[str, str]], 
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call the OpenAI API with the given messages
    
    Args:
        messages: List of message objects with role and content
        model: Model to use (defaults to the one in config)
        
    Returns:
        The processed response from the API
    """
    model = model or OPENAI_CONFIG.get('model', 'gpt-4o')
    client = get_openai_client()
    
    # Create a cache key based on the request
    if OPENAI_CONFIG.get('enable_caching', True):
        cache_key = json.dumps({
            'model': model,
            'messages': messages,
            'temperature': OPENAI_CONFIG.get('temperature'),
            'max_tokens': OPENAI_CONFIG.get('max_tokens'),
        })
        
        # Return cached response if available
        if cache_key in _api_cache:
            logging.info("Using cached response")
            return _api_cache[cache_key]
    
    # Prepare API call parameters
    params = {
        'model': model,
        'messages': messages,
        'temperature': OPENAI_CONFIG.get('temperature', 0.3),
        'max_tokens': OPENAI_CONFIG.get('max_tokens', 2048),
        'top_p': OPENAI_CONFIG.get('top_p', 0.9),
        'frequency_penalty': OPENAI_CONFIG.get('frequency_penalty', 0.0),
        'presence_penalty': OPENAI_CONFIG.get('presence_penalty', 0.0),
    }
    
    # Add response format if specified and using a compatible model
    if OPENAI_CONFIG.get('response_format') == 'json' and model in ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']:
        params['response_format'] = {'type': 'json_object'}
    
    # Implement exponential backoff retry mechanism
    max_retries = 3
    retry_delay = 1  # Starting delay in seconds
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**params)
            
            # Log usage information
            if USAGE_TRACKING.get('track_tokens', True):
                prompt_text = "\n".join([msg['content'] for msg in messages])
                log_usage(response, prompt_text, model)
            
            result = {
                'text': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            # Cache the result
            if OPENAI_CONFIG.get('enable_caching', True) and 'cache_key' in locals():
                _api_cache[cache_key] = result
                
            return result
            
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error(f"API call failed after {max_retries} attempts: {str(e)}")
                raise

def process_transcription(
    transcription: str, 
    ongoing_entries: str,
    prompt_template: str
) -> Dict[str, Any]:
    """
    Process a transcription using the OpenAI API
    
    Args:
        transcription: The transcription text to process
        ongoing_entries: Previous diary entries
        prompt_template: The prompt template from prompts.py
        
    Returns:
        A dictionary with the analysis results, organized entry, and to-do items
    """
    # Prepare the messages for the API call
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful diary organization assistant that organizes entries and extracts to-do items."
        },
        {
            "role": "user", 
            "content": prompt_template
        }
    ]
    
    # Call the OpenAI API
    response = call_openai_api(messages)
    analysis = response['text']
    
    # Extract to-do items and organized entry
    todo_items = extract_todo_items(analysis)
    organized_entry = extract_organized_entry(analysis)
    
    # Send demo email if enabled
    from send_email import send_demo_email
    success, message = send_demo_email(transcription)
    if success:
        print(f"Demo email sent: {message}")
    else:
        print(f"Demo email failed: {message}")

    return {
        'analysis': analysis,
        'todo_items': todo_items,
        'organized_entry': organized_entry or transcription,
        'usage': response['usage']
    }

def extract_todo_items(analysis: str) -> List[str]:
    """Extract to-do items from the model's analysis"""
    # Look for the TO-DO ITEMS section in the analysis
    todo_section_match = re.search(r'## TO-DO ITEMS\s+(.*?)(?=##|\Z)', analysis, re.DOTALL)
    
    if not todo_section_match:
        return []
        
    todo_section = todo_section_match.group(1).strip()
    
    # If no to-do items were found
    if "No to-do items detected" in todo_section:
        return []
        
    # Extract individual items (assuming they're in a list format)
    todo_items = []
    for line in todo_section.split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('*'):
            todo_items.append(line[1:].strip())
        elif re.match(r'^\d+\.', line):  # Numbered list
            todo_items.append(re.sub(r'^\d+\.', '', line).strip())
    
    return todo_items

def extract_organized_entry(analysis: str) -> Optional[str]:
    """Extract the organized entry from the model's analysis"""
    # Look for the ORGANIZED ENTRY section in the analysis
    entry_section_match = re.search(r'## ORGANIZED ENTRY\s+(.*?)(?=##|\Z)', analysis, re.DOTALL)
    
    if not entry_section_match:
        return None
        
    organized_entry = entry_section_match.group(1).strip()
    return organized_entry 