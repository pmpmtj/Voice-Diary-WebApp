"""
Email Configuration Setup Script

This script provides functions to update email configuration parameters in email_config.json.
It can be used both as a command-line tool and as a module imported by other scripts.

Usage as command-line tool:
    python setup_email_params.py [options]

Options:
    --recipient EMAIL    Set the recipient email address
    --subject TEXT      Set the email subject
    --message TEXT      Set the email message
    --send-demo BOOL    Set whether to send demo email (true/false)
    --show             Show current configuration
    --help             Show this help message

Example:
    python setup_email_params.py --recipient "user@example.com" --subject "New Subject"
"""

import json
import os
import re
import argparse
from typing import Optional, Dict, Any
from pathlib import Path

CONFIG_FILE = 'email_config.json'

class EmailConfigError(Exception):
    """Base exception for email configuration errors."""
    pass

class InvalidEmailError(EmailConfigError):
    """Exception raised for invalid email format."""
    pass

class ConfigFileError(EmailConfigError):
    """Exception raised for configuration file errors."""
    pass

def validate_email(email: str) -> bool:
    """
    Validate email format using regex pattern.
    
    Args:
        email: The email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def load_config() -> Dict[str, Any]:
    """
    Load the current email configuration.
    
    Returns:
        Dict[str, Any]: The loaded configuration
        
    Raises:
        ConfigFileError: If there's an error reading or parsing the config file
    """
    try:
        config_path = Path(CONFIG_FILE)
        if not config_path.exists():
            # Create default config if file doesn't exist
            default_config = {
                "email": {
                    "to": "recipient@example.com",
                    "subject": "Test Email from Gmail API",
                    "message": "This is a test email sent using the Gmail API."
                },
                "send_demo_email": False
            }
            save_config(default_config)
            return default_config
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Validate config structure
        if not isinstance(config, dict):
            raise ConfigFileError("Configuration must be a JSON object")
        if 'email' not in config:
            raise ConfigFileError("Configuration missing 'email' section")
        if not isinstance(config['email'], dict):
            raise ConfigFileError("'email' section must be a JSON object")
            
        return config
        
    except json.JSONDecodeError as e:
        raise ConfigFileError(f"Invalid JSON in {CONFIG_FILE}: {str(e)}")
    except Exception as e:
        raise ConfigFileError(f"Error loading configuration: {str(e)}")

def save_config(config: Dict[str, Any]) -> None:
    """
    Save the email configuration to file.
    
    Args:
        config: The configuration to save
        
    Raises:
        ConfigFileError: If there's an error saving the config file
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        raise ConfigFileError(f"Error saving configuration: {str(e)}")

def update_recipient(email: str) -> bool:
    """
    Update the recipient email address.
    
    Args:
        email: The new recipient email address
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        InvalidEmailError: If the email format is invalid
    """
    try:
        if not validate_email(email):
            raise InvalidEmailError(f"Invalid email format: {email}")
            
        config = load_config()
        config['email']['to'] = email
        save_config(config)
        return True
    except InvalidEmailError as e:
        print(f"Error: {str(e)}")
        return False
    except Exception as e:
        print(f"Error updating recipient: {str(e)}")
        return False

def update_subject(subject: str) -> bool:
    """
    Update the email subject.
    
    Args:
        subject: The new email subject
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not subject or not isinstance(subject, str):
            raise ValueError("Subject must be a non-empty string")
            
        config = load_config()
        config['email']['subject'] = subject
        save_config(config)
        return True
    except Exception as e:
        print(f"Error updating subject: {str(e)}")
        return False

def update_message(message: str) -> bool:
    """
    Update the email message.
    
    Args:
        message: The new email message
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not message or not isinstance(message, str):
            raise ValueError("Message must be a non-empty string")
            
        config = load_config()
        config['email']['message'] = message
        save_config(config)
        return True
    except Exception as e:
        print(f"Error updating message: {str(e)}")
        return False

def update_send_demo_email(send_demo: bool) -> bool:
    """
    Update whether to send demo email.
    
    Args:
        send_demo: True to enable demo email, False to disable
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not isinstance(send_demo, bool):
            raise ValueError("send_demo must be a boolean value")
            
        config = load_config()
        config['send_demo_email'] = send_demo
        save_config(config)
        return True
    except Exception as e:
        print(f"Error updating send_demo_email: {str(e)}")
        return False

def show_config() -> None:
    """
    Display the current email configuration.
    
    Raises:
        ConfigFileError: If there's an error loading the configuration
    """
    try:
        config = load_config()
        print("\nCurrent Email Configuration:")
        print("---------------------------")
        print(f"Recipient: {config['email']['to']}")
        print(f"Subject: {config['email']['subject']}")
        print(f"Message: {config['email']['message']}")
        print(f"Send Demo Email: {config['send_demo_email']}")
        print("---------------------------\n")
    except Exception as e:
        print(f"Error displaying configuration: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Update email configuration parameters')
    
    parser.add_argument('--recipient', help='Set the recipient email address')
    parser.add_argument('--subject', help='Set the email subject')
    parser.add_argument('--message', help='Set the email message')
    parser.add_argument('--send-demo', type=str, choices=['true', 'false'], 
                       help='Set whether to send demo email (true/false)')
    parser.add_argument('--show', action='store_true', help='Show current configuration')
    
    args = parser.parse_args()
    
    try:
        if args.show:
            show_config()
            return
        
        if not any([args.recipient, args.subject, args.message, args.send_demo]):
            parser.print_help()
            return
        
        success = True
        
        if args.recipient:
            if not update_recipient(args.recipient):
                success = False
        
        if args.subject:
            if not update_subject(args.subject):
                success = False
        
        if args.message:
            if not update_message(args.message):
                success = False
        
        if args.send_demo:
            if not update_send_demo_email(args.send_demo.lower() == 'true'):
                success = False
        
        if success:
            print("\nConfiguration updated successfully!")
            show_config()
        else:
            print("\nSome updates failed. Please check the error messages above.")
            
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 