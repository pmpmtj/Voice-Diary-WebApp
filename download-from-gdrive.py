import os
import io
import json
import pickle
import sys
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import time

# Set stdout to use utf-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# If modifying these scopes, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'
FOLDER_NAME = 'a-daily-log'  # Your Google Drive folder name

def load_config():
    """Load configuration from config.json file"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        # Get folders list from config or use default if not present
        folders = config.get('gdrive', {}).get('folders', ['a-daily-log'])
        
        # Get file extensions configuration
        file_extensions = config.get('gdrive', {}).get('file_extensions', {
            'include': ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'],
            'exclude': []
        })
        
        return {
            'folders': folders,
            'file_extensions': file_extensions
        }
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        # Return default configuration if config file is missing or invalid
        return {
            'folders': ['a-daily-log'],
            'file_extensions': {
                'include': ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'],
                'exclude': []
            }
        }

def check_credentials_file():
    """Check if credentials.json exists and provide help if not."""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: '{CREDENTIALS_FILE}' file not found!")
        print("\nTo create your credentials file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select an existing one")
        print("3. Enable the Google Drive API:")
        print("   - Navigate to 'APIs & Services' > 'Library'")
        print("   - Search for 'Google Drive API' and enable it")
        print("4. Create OAuth credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Select 'Desktop app' as application type")
        print("   - Download the JSON file and rename it to 'credentials.json'")
        print("   - Place it in the same directory as this script")
        print("\nThen run this script again.")
        return False
    return True

def authenticate_google_drive():
    """Authenticate with Google Drive API using OAuth."""
    creds = None
    
    # The token.pickle file stores the user's access and refresh tokens
    # It is created automatically when the authorization flow completes for the first time
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # If no valid credentials are available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not check_credentials_file():
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def find_folder_by_name(service, folder_name):
    """Find a folder by name in Google Drive."""
    if folder_name.lower() == 'root':
        # The root folder in Google Drive has a special ID: 'root'
        return {'id': 'root', 'name': 'My Drive'}
        
    # Search for folders with the given name
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        return None
    else:
        # Return the first matching folder
        return items[0]

def find_file_by_name_in_folder(service, file_name, folder_id):
    """Find a file by name in a specific Google Drive folder."""
    # Search for files with the given name in the specified folder
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        return None
    else:
        # Return the first matching file
        return items[0]

def list_files_in_folder(service, folder_id, file_extensions):
    """List all files in the given folder, filtered by file extensions."""
    include_extensions = file_extensions.get('include', [])
    exclude_extensions = file_extensions.get('exclude', [])
    
    # Base query to get files from the folder that are not trashed
    query = f"'{folder_id}' in parents and trashed=false"
    
    # Add file type filtering if extensions are specified
    if include_extensions:
        extension_queries = []
        for ext in include_extensions:
            extension_queries.append(f"name contains '{ext}'")
        if extension_queries:
            query += f" and ({' or '.join(extension_queries)})"
    
    results = service.files().list(
        q=query,
        spaces='drive',
        # Add request for createdTime and modifiedTime to use for chronological ordering
        fields='files(id, name, mimeType, createdTime, modifiedTime)'
    ).execute()
    
    files = results.get('files', [])
    
    # Apply exclusion filters if needed
    if exclude_extensions and files:
        filtered_files = []
        for file in files:
            name = file.get('name', '').lower()
            if not any(name.endswith(ext.lower()) for ext in exclude_extensions):
                filtered_files.append(file)
        files = filtered_files
    
    # Sort files by createdTime to ensure chronological order
    files.sort(key=lambda x: x.get('createdTime', ''))
    
    return files

def download_file(service, file_id, file_name):
    """Download a file from Google Drive."""
    print(f"Downloading {file_name}...")
    
    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    # Request to get the file content
    request = service.files().get_media(fileId=file_id)
    
    # Create a BytesIO stream to download the file
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    
    # Download the file in chunks
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"  Progress: {int(status.progress() * 100)}%")
    
    # Save the file to disk
    file_path = os.path.join('downloads', file_name)
    with open(file_path, 'wb') as f:
        f.write(file_io.getvalue())
    
    print(f"Download completed: {file_path}")
    return file_path

def delete_file(service, file_id, file_name):
    """Delete a file from Google Drive."""
    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File '{file_name}' deleted successfully from Google Drive.")
        return True
    except Exception as e:
        print(f"Error deleting file '{file_name}': {str(e)}")
        return False

def download_all_files(service, files):
    """Download all files from the list."""
    print(f"\nDownloading all {len(files)} files from folder...")
    
    # Create a downloads directory if it doesn't exist
    download_dir = 'downloads'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"Created directory: {download_dir}")
    
    # Keep track of successfully downloaded files
    downloaded_files = []
    
    # Download each file
    for i, file in enumerate(files, 1):
        file_name = file['name']
        file_id = file['id']
        
        # Skip Google Docs, Sheets, etc. that need export
        mime_type = file.get('mimeType', '')
        if 'google-apps' in mime_type and mime_type != 'application/vnd.google-apps.folder':
            print(f"Skipping Google Workspace file: {file_name} (requires export)")
            continue
        
        # Extract creation time for chronological ordering
        created_time_str = file.get('createdTime', '')
        if created_time_str:
            # Convert ISO 8601 format to a datetime object
            from datetime import datetime
            try:
                # Format: YYYY-MM-DDTHH:MM:SS.sssZ (e.g., 2024-03-23T12:34:56.789Z)
                # Handle different possible formats Google might return
                if '.' in created_time_str:  # Check if it includes milliseconds
                    created_time = datetime.strptime(created_time_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                else:
                    created_time = datetime.strptime(created_time_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
                
                # Format as YYYYMMDD_HHMMSS_mmm for filename prefix (including milliseconds)
                # Add current microseconds if not provided by Google Drive to ensure uniqueness
                date_prefix = created_time.strftime('%Y%m%d_%H%M%S')
                # Add microseconds - either from the parsed time or current time
                if '.' in created_time_str:
                    date_prefix += "_" + created_time.strftime('%f')[:3]
                else:
                    # Use current time's microseconds if the API didn't provide any
                    date_prefix += "_" + datetime.now().strftime('%f')[:3]
                
                # Add prefix to filename
                prefixed_file_name = f"{date_prefix}_{file_name}"
            except ValueError:
                # In case of parsing error, use original filename
                print(f"Warning: Could not parse creation time for {file_name}")
                prefixed_file_name = file_name
        else:
            prefixed_file_name = file_name
        
        # Create path for downloaded file with date prefix
        file_path = os.path.join(download_dir, prefixed_file_name)
        
        print(f"\nDownloading file {i}/{len(files)}: {file_name} as {prefixed_file_name}")
        try:
            # Download the file
            request = service.files().get_media(fileId=file_id)
            
            # Create a BytesIO stream to store the downloaded file
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            
            # Download the file
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download progress: {int(status.progress() * 100)}%")
            
            # Save the file
            file_stream.seek(0)
            with open(file_path, 'wb') as f:
                f.write(file_stream.read())
            
            print(f"File '{file_name}' downloaded successfully as '{prefixed_file_name}'!")
            # Store original file info and the new filename for reference
            file_info = file.copy()
            file_info['local_filename'] = prefixed_file_name
            downloaded_files.append(file_info)
            
            # Add a small delay to ensure files have different timestamps
            # even if Google Drive reports the same creation time
            time.sleep(0.1)
        except Exception as e:
            print(f"Error downloading '{file_name}': {str(e)}")
    
    print(f"\nDownload complete! All files saved to the '{download_dir}' directory.")
    return downloaded_files

def delete_files_without_confirmation(service, downloaded_files):
    """Delete files from Google Drive without asking for confirmation."""
    if not downloaded_files:
        print("No files were successfully downloaded, so none will be deleted.")
        return
    
    print(f"\nAutomatically deleting {len(downloaded_files)} files from Google Drive...")
    deleted_count = 0
    
    for file in downloaded_files:
        # Get the original file name (without date prefix)
        file_name = file['name']
        file_id = file['id']
        
        if delete_file(service, file_id, file_name):
            deleted_count += 1
    
    print(f"Deletion complete! {deleted_count} out of {len(downloaded_files)} files were deleted from Google Drive.")
    return deleted_count

def main():
    print(f"Authenticating with Google Drive...")
    
    try:
        # Load configuration
        config = load_config()
        folders = config['folders']
        file_extensions = config['file_extensions']
        
        # Authenticate with Google Drive
        creds = authenticate_google_drive()
        service = build('drive', 'v3', credentials=creds)
        
        all_downloaded_files = []
        
        # Process each folder in the list
        for folder_name in folders:
            print(f"\nProcessing folder: {folder_name}")
            
            # Find the folder
            folder = find_folder_by_name(service, folder_name)
            
            if not folder:
                print(f"Folder '{folder_name}' not found in your Google Drive. Skipping.")
                continue
                
            print(f"Folder found! ID: {folder['id']}")
            
            # List all files in the folder
            print(f"Listing files in '{folder['name']}' folder:")
            files = list_files_in_folder(service, folder['id'], file_extensions)
            
            if not files:
                print(f"No matching files found in '{folder['name']}' folder.")
                continue
                
            print("\nFiles in folder:")
            for i, file in enumerate(files, 1):
                print(f"{i}. {file['name']} ({file.get('mimeType', 'unknown type')})")
            
            # Download all files and get list of successfully downloaded files
            downloaded_files = download_all_files(service, files)
            
            # Add these files to our master list
            all_downloaded_files.extend(downloaded_files)
            
            # Delete the downloaded files from this specific Google Drive folder
            print(f"\nDeleting files from '{folder['name']}' folder in Google Drive...")
            delete_files_without_confirmation(service, downloaded_files)
        
        # Summary
        if all_downloaded_files:
            print(f"\nTotal downloaded files: {len(all_downloaded_files)}")
            print(f"Total deleted files: {len(all_downloaded_files)}")
        else:
            print("\nNo files were downloaded from any folder.")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please make sure you have:")
        print("1. Installed all required packages (pip install -r requirements.txt)")
        print("2. Set up proper Google Drive API credentials")
        print("3. Enabled the Google Drive API in your Google Cloud project")

if __name__ == '__main__':
    main()
