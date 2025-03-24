"""
Gmail API Email Sender

This script uses the Gmail API to send emails. It requires:
1. OAuth2 credentials (credentials_gmail.json)
2. Email configuration (email_config.json)

The script will:
1. Load email settings from email_config.json
2. Authenticate with Gmail API using Gmail-specific credentials
3. Send the configured email with optional attachments
"""

import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

# If modifying these scopes, delete the token_gmail.pickle file
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/'
]
CREDENTIALS_FILE = 'credentials_gmail.json'
TOKEN_FILE = 'token_gmail.pickle'

def load_email_config():
    """Load email configuration from email_config.json file"""
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        return config.get('email', {})
    except Exception as e:
        print(f"Error loading email config: {str(e)}")
        return None

def check_credentials_file():
    """Check if credentials_gmail.json exists and provide help if not."""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: '{CREDENTIALS_FILE}' file not found!")
        print("\nTo create your Gmail credentials file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Enable the Gmail API:")
        print("   - Navigate to 'APIs & Services' > 'Library'")
        print("   - Search for 'Gmail API' and enable it")
        print("4. Create OAuth credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Select 'Desktop app' as application type")
        print("   - Download the JSON file and rename it to 'credentials_gmail.json'")
        print("   - Place it in the same directory as this script")
        print("\nThen run this script again.")
        return False
    return True

def authenticate_gmail():
    """Authenticate with Gmail API using OAuth."""
    creds = None
    
    # The token_gmail.pickle file stores the user's access and refresh tokens
    if os.path.exists(TOKEN_FILE):
        print(f"Found existing {TOKEN_FILE} file")
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
            print("Current scopes:", creds.scopes)
            
    # If no valid credentials are available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
        else:
            if not check_credentials_file():
                return None
            
            print("\nStarting OAuth flow...")
            print("This will open a browser window for authentication.")
            print("You will be asked to approve Gmail permissions.")
            print("After approval, the token will be saved for future use.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        print(f"Saving token to {TOKEN_FILE}...")
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')}

def create_message_with_attachment(sender, to, subject, message_text, attachment_path=None):
    """Create a message for an email with optional attachment."""
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Add the message body
    msg = MIMEText(message_text)
    message.attach(msg)

    # Add attachment if provided
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attachment = MIMEApplication(f.read())
            attachment.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=os.path.basename(attachment_path)
            )
            message.attach(attachment)

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')}

def send_message(service, user_id, message):
    """Send an email message."""
    try:
        sent_message = service.users().messages().send(
            userId=user_id,
            body=message
        ).execute()
        print(f'Message Id: {sent_message["id"]}')
        return sent_message
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def send_demo_email(transcription_text):
    """Send a demo email with transcription as attachment."""
    try:
        # Load email configuration
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        
        if not config.get('send_demo_email', False):
            return False, "Demo email not enabled in config"
        
        email_config = config.get('email', {})
        if not all(key in email_config for key in ['to', 'subject', 'message']):
            return False, "Missing required email parameters in config"

        # Create temporary file with transcription
        temp_file = 'demo_result.txt'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(transcription_text)

        # Authenticate with Gmail
        creds = authenticate_gmail()
        if not creds:
            return False, "Failed to authenticate with Gmail"

        try:
            # Create Gmail API service
            service = build('gmail', 'v1', credentials=creds)
            
            # Get the authenticated user's email address
            user_profile = service.users().getProfile(userId='me').execute()
            sender = user_profile['emailAddress']
            
            # Create and send the email with attachment
            message = create_message_with_attachment(
                sender,
                email_config['to'],
                email_config['subject'],
                email_config['message'],
                temp_file
            )
            
            result = send_message(service, 'me', message)
            
            # Clean up temporary file
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temporary file: {e}")
            
            if result:
                return True, "Demo email sent successfully"
            else:
                return False, "Failed to send demo email"
                
        except Exception as e:
            return False, f"Error sending demo email: {str(e)}"
            
    except Exception as e:
        return False, f"Error in demo email process: {str(e)}"

def main():
    print("Starting Gmail API Email Sender")
    print("Using credentials from:", CREDENTIALS_FILE)
    
    # Load email configuration
    email_config = load_email_config()
    if not email_config:
        print("Failed to load email configuration. Please check email_config.json")
        return

    # Authenticate with Gmail
    print("\nAuthenticating with Gmail...")
    creds = authenticate_gmail()
    if not creds:
        print("Failed to authenticate with Gmail")
        return

    try:
        # Create Gmail API service
        service = build('gmail', 'v1', credentials=creds)
        
        # Get the authenticated user's email address
        user_profile = service.users().getProfile(userId='me').execute()
        sender = user_profile['emailAddress']
        print(f"\nAuthenticated as: {sender}")
        
        # Create and send the email
        print("\nCreating email message...")
        message = create_message(
            sender,
            email_config['to'],
            email_config['subject'],
            email_config['message']
        )
        
        print("Sending email...")
        result = send_message(service, 'me', message)
        
        if result:
            print("\nEmail sent successfully!")
        else:
            print("\nFailed to send email.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == '__main__':
    main() 