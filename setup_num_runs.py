#!/usr/bin/env python
"""
Setup Number of Pipeline Runs Per Day

This script allows you to configure how many times the audio diary pipeline 
runs per day. It updates the runs_per_day setting in config.json.

Usage:
    python setup_num_runs.py <number_of_runs>
    python setup_num_runs.py --help

Examples:
    python setup_num_runs.py 1     # Run once per day (every 24 hours)
    python setup_num_runs.py 2     # Run twice per day (every 12 hours)
    python setup_num_runs.py 24    # Run every hour
    python setup_num_runs.py 0     # Run once and exit
"""

import os
import sys
import json
import argparse
from datetime import timedelta

def load_config():
    """Load configuration from config.json file"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    # Try to load and parse the config file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config, config_path
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config.json: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load config.json: {str(e)}")
        sys.exit(1)

def save_config(config, config_path):
    """Save the updated configuration to config.json file"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save config.json: {str(e)}")
        sys.exit(1)

def calculate_interval(runs_per_day):
    """Calculate interval in seconds based on runs per day"""
    if runs_per_day == 0:
        return "Run once and exit"
        
    seconds_per_day = 86400
    interval_seconds = seconds_per_day / runs_per_day
    
    # Format the interval as a human-readable time
    days, remainder = divmod(interval_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
    if seconds > 0 and not parts:  # Only show seconds if no larger units or value is small
        parts.append(f"{int(seconds)} second{'s' if seconds > 1 else ''}")
    
    if parts:
        return "Every " + " and ".join(parts)
    else:
        return "Every 24 hours"  # Fallback for when no parts could be generated

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Configure how many times the audio diary pipeline runs per day",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_num_runs.py 1     # Run once per day (every 24 hours)
  python setup_num_runs.py 2     # Run twice per day (every 12 hours)
  python setup_num_runs.py 24    # Run every hour
  python setup_num_runs.py 0     # Run once and exit
        """
    )
    
    parser.add_argument(
        "runs_per_day", 
        type=int, 
        nargs="?",  # Make it optional
        help="Number of times to run the pipeline per day (0 to run once and exit)"
    )
    
    parser.add_argument(
        "--show", 
        action="store_true", 
        help="Show current configuration without changing it"
    )
    
    args = parser.parse_args()
    
    # Load current configuration
    config, config_path = load_config()
    
    # Make sure scheduler section exists
    if "scheduler" not in config:
        config["scheduler"] = {}
    
    # Get current runs_per_day or default to 1
    current_runs = config["scheduler"].get("runs_per_day", 1)
    
    # If --show flag or no arguments, just show current configuration
    if args.show or args.runs_per_day is None:
        print(f"Current configuration: {current_runs} {'run' if current_runs == 1 else 'runs'} per day")
        print(f"Interval: {calculate_interval(current_runs)}")
        return
    
    # Validate input
    if args.runs_per_day < 0:
        print("ERROR: Number of runs per day cannot be negative")
        sys.exit(1)
    
    # Update the configuration
    config["scheduler"]["runs_per_day"] = args.runs_per_day
    
    # Save the updated configuration
    if save_config(config, config_path):
        print(f"Successfully updated runs per day to: {args.runs_per_day}")
        print(f"Interval: {calculate_interval(args.runs_per_day)}")
        
        # Show restart message
        if current_runs != args.runs_per_day:
            print("\nNOTE: Restart the scheduler for changes to take effect.")
            print("      If the scheduler is running, stop it and start it again.")

if __name__ == "__main__":
    main() 