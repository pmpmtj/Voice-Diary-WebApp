# Transcription System Web Interface Manual

## Overview
This document provides comprehensive instructions for setting up, using, and maintaining the web interface for the Transcription System. The web interface allows you to control the transcription scheduler through a user-friendly dashboard.

## Table of Contents
1. [Setup Instructions](#setup-instructions)
2. [Starting the Web Interface](#starting-the-web-interface)
3. [User Management](#user-management)
4. [Using the Dashboard](#using-the-dashboard)
5. [Troubleshooting](#troubleshooting)
6. [Technical Details](#technical-details)

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Django 5.1.7
- Required Python packages (install using `pip install -r requirements.txt`):
  - django
  - djangorestframework
  - django-crispy-forms
  - crispy-bootstrap5
  - psutil

### Initial Setup
1. Ensure all required packages are installed:
   ```bash
   pip install django djangorestframework django-crispy-forms crispy-bootstrap5 psutil
   ```

2. Create the database and apply migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Create a superuser account:
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create your admin account.

## Starting the Web Interface

### Starting the Server
1. Open a terminal in the project directory
2. Run the development server:
   ```bash
   python manage.py runserver
   ```
3. Access the web interface at http://127.0.0.1:8000/

### Stopping the Server
If you need to stop the server and the terminal is closed:
1. Open Task Manager (Ctrl + Shift + Esc)
2. Find the Python process running the Django server
3. Right-click and select "End Task"

Or use PowerShell:
```powershell
Get-Process python | Where-Object {$_.CommandLine -like '*manage.py runserver*'} | Stop-Process -Force
```

## User Management

### Creating New Users
1. Log in as superuser
2. Access the admin interface at http://127.0.0.1:8000/admin/
3. Click on "Users" under "Authentication and Authorization"
4. Click "Add User" and fill in the details

### Managing User Permissions
1. Access the admin interface
2. Go to Users
3. Click on a user to edit their permissions
4. Set appropriate permissions (staff status, superuser status, etc.)

## Using the Dashboard

### Main Features
1. **Scheduler Control**
   - Toggle switch to start/stop the transcription scheduler
   - Real-time status display
   - Last action timestamp

2. **Activity Log**
   - Recent scheduler actions
   - User who performed the action
   - Success/failure status
   - Timestamp of actions

### How to Use
1. **Starting the Scheduler**
   - Log in to the dashboard
   - Click the toggle switch to the "on" position
   - Wait for confirmation message
   - Status will update to "Running"

2. **Stopping the Scheduler**
   - Click the toggle switch to the "off" position
   - Wait for confirmation message
   - Status will update to "Stopped"

3. **Monitoring Status**
   - Status updates automatically every 5 seconds
   - Check the activity log for recent actions
   - Look for success/failure indicators

## Troubleshooting

### Common Issues
1. **Server Won't Start**
   - Check if port 8000 is already in use
   - Ensure all required packages are installed
   - Check for Python version compatibility

2. **Can't Log In**
   - Verify username and password
   - Check if account is active
   - Try resetting password through admin interface

3. **Scheduler Control Issues**
   - Check if scheduler.py is in the correct location
   - Verify file permissions
   - Check system logs for errors

### Error Messages
- "Server already running": Kill the existing process using Task Manager or PowerShell
- "Database errors": Run migrations again
- "Permission denied": Check file permissions and user rights

## Technical Details

### Project Structure
```
transcription_web/
├── manage.py
├── transcription_web/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── scheduler_control/
│   ├── __init__.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── templates/
│       └── scheduler_control/
│           ├── base.html
│           ├── dashboard.html
│           └── login.html
└── static/
```

### Key Files
- `scheduler_control/models.py`: Database models for scheduler status and logs
- `scheduler_control/views.py`: Logic for handling scheduler control
- `scheduler_control/templates/`: HTML templates for the web interface
- `transcription_web/settings.py`: Django project settings

### Database Models
1. **SchedulerStatus**
   - Tracks if scheduler is running
   - Records last start/stop times
   - Updates automatically

2. **SchedulerLog**
   - Records all scheduler actions
   - Tracks user who performed action
   - Stores success/failure status
   - Includes timestamps

### Security Features
- User authentication required
- CSRF protection
- Secure password handling
- Session management

## Maintenance

### Regular Tasks
1. **Database Backup**
   - Backup `db.sqlite3` regularly
   - Keep backup copies in a secure location

2. **Log Management**
   - Monitor log files for errors
   - Clean up old logs periodically

3. **User Management**
   - Review user accounts regularly
   - Update permissions as needed
   - Remove inactive accounts

### Updates
1. **Package Updates**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Database Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## Support
For additional support or questions:
1. Check the main project README.md
2. Review the Django documentation
3. Contact system administrator

## Notes
- Keep the development server running while using the web interface
- Monitor system resources when scheduler is running
- Regular backups are recommended
- Keep the system updated with security patches 