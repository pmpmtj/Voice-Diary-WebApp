"""
OpenAI API Setup Script

This script helps you set up your OpenAI API key for the diary application.
It will:
1. Guide you through setting up your API key
2. Test the connection to OpenAI API
3. Update the configuration file

Usage:
python setup_openai.py
"""

import os
import json
import getpass
import sys

try:
    from openai import OpenAI
except ImportError:
    print("Error: OpenAI Python package not found.")
    print("Please install it first with: pip install openai")
    sys.exit(1)

def save_api_key(api_key, save_to_env=False, save_to_config=True):
    """Save the API key to the configuration file and/or environment variable"""
    success = True
    
    # Save to configuration file
    if save_to_config:
        try:
            # Check if openai_config.py exists
            if os.path.exists('openai_config.py'):
                # Read the current content
                with open('openai_config.py', 'r') as file:
                    content = file.read()
                
                # Replace the API key line
                if '"api_key": ""' in content:
                    content = content.replace('"api_key": ""', f'"api_key": "{api_key}"')
                    
                    # Write the updated content
                    with open('openai_config.py', 'w') as file:
                        file.write(content)
                        
                    print("✅ API key saved to openai_config.py")
                else:
                    print("⚠️ Could not locate API key line in openai_config.py")
                    success = False
            else:
                print("⚠️ openai_config.py not found")
                success = False
        except Exception as e:
            print(f"❌ Error saving API key to config file: {str(e)}")
            success = False
    
    # Save to environment variable
    if save_to_env:
        # For Windows, use setx command
        if os.name == 'nt':
            try:
                os.system(f'setx OPENAI_API_KEY "{api_key}"')
                print("✅ API key saved to environment variable (will be available in new terminal sessions)")
            except Exception as e:
                print(f"❌ Error setting environment variable: {str(e)}")
                success = False
        # For Unix-like systems, suggest adding to profile
        else:
            print("\nTo permanently save your API key as an environment variable, add this line to your shell profile:")
            print(f'export OPENAI_API_KEY="{api_key}"')
    
    return success

def test_api_key(api_key):
    """Test the API key by making a simple request to OpenAI API"""
    print("\nTesting API key with a simple request...")
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI connection successful!' if you receive this message."}
            ],
            max_tokens=20
        )
        result = response.choices[0].message.content.strip()
        
        if "successful" in result.lower():
            print(f"✅ API connection test successful!")
            print(f"API response: {result}")
            return True
        else:
            print(f"⚠️ API responded but with unexpected content: {result}")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("       OpenAI API Setup for Audio Diary Application")
    print("=" * 60)
    print("\nThis script will help you set up your OpenAI API key.")
    print("You can get an API key from: https://platform.openai.com/api-keys")
    
    # Check if API key is already set in environment
    existing_key = os.environ.get('OPENAI_API_KEY')
    if existing_key:
        print("\nFound existing API key in environment variable.")
        use_existing = input("Do you want to use this key? (y/n): ").lower().strip()
        if use_existing == 'y':
            api_key = existing_key
        else:
            api_key = getpass.getpass("\nEnter your OpenAI API key: ")
    else:
        api_key = getpass.getpass("\nEnter your OpenAI API key: ")
    
    # Test the API key
    if test_api_key(api_key):
        # Ask where to save the API key
        print("\nWhere would you like to save your API key?")
        print("1. Save in configuration file (openai_config.py)")
        print("2. Save as environment variable")
        print("3. Save in both places")
        print("4. Don't save (not recommended)")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            save_api_key(api_key, save_to_env=False, save_to_config=True)
        elif choice == '2':
            save_api_key(api_key, save_to_env=True, save_to_config=False)
        elif choice == '3':
            save_api_key(api_key, save_to_env=True, save_to_config=True)
        elif choice == '4':
            print("\n⚠️ API key not saved. You'll need to set it manually each time.")
        else:
            print("\n❌ Invalid choice. API key not saved.")
            
        print("\n✅ Setup complete! You can now use the OpenAI API in your diary application.")
    else:
        print("\n❌ Setup failed. Please check your API key and try again.")
    
    print("\nAdditional recommendations:")
    print("- Keep your API key secure and don't share it")
    print("- Monitor your usage on the OpenAI dashboard")
    print("- Consider setting a budget limit on your OpenAI account")
    print("\nFor more information, visit: https://platform.openai.com/docs")

if __name__ == "__main__":
    main() 