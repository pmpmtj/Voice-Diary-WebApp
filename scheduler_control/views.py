from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import subprocess
import os
import signal
import psutil
import sys
import time
import json
from .models import SchedulerStatus, SchedulerLog
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.core.management import call_command
from io import StringIO
from functools import wraps

def demo_user_required(view_func):
    """Decorator to handle demo user access"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
            
        if request.user.username == 'visita':
            # If demo user tries to access non-demo pages, redirect to demo
            if view_func.__name__ != 'demo_view':
                return redirect('demo')
        else:
            # If regular user tries to access demo page, redirect to dashboard
            if view_func.__name__ == 'demo_view':
                return redirect('dashboard')
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@demo_user_required
def demo_view(request):
    """Demo view for visita user"""
    status, created = SchedulerStatus.objects.get_or_create()
    logs = SchedulerLog.objects.all().order_by('-timestamp')[:5]  # Get last 5 logs
    
    # Load configurations
    config = load_config()
    email_config = load_email_config()
    
    return render(request, 'scheduler_control/demo.html', {
        'status': status,
        'logs': logs,
        'config': config,
        'email_config': email_config
    })

# Global variable to store the scheduler process
scheduler_process = None

def load_config():
    """Load configuration from config.json file"""
    config_path = os.path.join(settings.BASE_DIR, 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config.json: {str(e)}")
        return {}

def load_email_config():
    """Load configuration from email_config.json file"""
    config_path = os.path.join(settings.BASE_DIR, 'email_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading email_config.json: {str(e)}")
        return {'email': {'to': '', 'subject': '', 'message': ''}, 'send_demo_email': False}

# Load config at module level
config = load_config()
web_interface_config = config.get('web_interface', {})

def find_scheduler_process():
    """Find the running scheduler process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
        try:
            if 'scheduler.py' in ' '.join(proc.info['cmdline'] or []):
                # Accept any status except terminated or zombie
                if proc.info['status'] not in ['terminated', 'zombie']:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

@login_required
@demo_user_required
def dashboard(request):
    """Main dashboard view"""
    status, created = SchedulerStatus.objects.get_or_create()
    logs = SchedulerLog.objects.all().order_by('-timestamp')[:10]  # Get last 10 logs
    
    # Load configurations
    config = load_config()
    email_config = load_email_config()
    
    return render(request, 'scheduler_control/dashboard.html', {
        'status': status,
        'logs': logs,
        'config': config,
        'email_config': email_config
    })

@login_required
@require_POST
def toggle_scheduler(request):
    """Toggle the scheduler on/off"""
    status, created = SchedulerStatus.objects.get_or_create()
    global scheduler_process
    
    try:
        if not status.is_running:
            # Get the full path to scheduler.py
            scheduler_path = os.path.join(settings.BASE_DIR, 'scheduler.py')
            python_exe = sys.executable
            
            # Start the scheduler
            scheduler_process = subprocess.Popen(
                [python_exe, scheduler_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Give the process a moment to start
            startup_delay = web_interface_config.get('process_startup_delay', 2)
            time.sleep(startup_delay)
            
            # Check if process started successfully
            if scheduler_process.poll() is not None:
                error_output = scheduler_process.stderr.read()
                # Check if the error is just about no files to process
                if "No audio files found" in error_output or "No transcription to process" in error_output:
                    # This is a normal case when there are no files to process
                    status.is_running = True
                    status.last_started = timezone.now()
                    status.save()
                    
                    SchedulerLog.objects.create(
                        user=request.user,
                        action='start',
                        success=True
                    )
                    messages.success(request, 'Scheduler started successfully (no files to process)')
                    return redirect('dashboard')
                else:
                    raise Exception(f"Failed to start scheduler: {error_output}")
            
            status.is_running = True
            status.last_started = timezone.now()
            status.save()
            
            SchedulerLog.objects.create(
                user=request.user,
                action='start',
                success=True
            )
            messages.success(request, 'Scheduler started successfully')
        else:
            # Stop the scheduler
            proc = find_scheduler_process()
            if proc:
                proc.terminate()
                try:
                    termination_timeout = web_interface_config.get('process_termination_timeout', 5)
                    proc.wait(timeout=termination_timeout)
                except psutil.TimeoutExpired:
                    proc.kill()
            
            status.is_running = False
            status.last_stopped = timezone.now()
            status.save()
            
            SchedulerLog.objects.create(
                user=request.user,
                action='stop',
                success=True
            )
            messages.success(request, 'Scheduler stopped successfully')
            
    except Exception as e:
        SchedulerLog.objects.create(
            user=request.user,
            action='start' if not status.is_running else 'stop',
            success=False,
            error_message=str(e)
        )
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('dashboard')

@login_required
def get_status(request):
    """API endpoint to get current scheduler status"""
    status, created = SchedulerStatus.objects.get_or_create()
    
    # Check if process is actually running
    proc = find_scheduler_process()
    is_running = proc is not None
    
    # Only update status if it's been more than grace period since last start
    if status.is_running != is_running:
        if not is_running and status.last_started:
            grace_period = web_interface_config.get('status_check_grace_period', 5)
            time_since_start = (timezone.now() - status.last_started).total_seconds()
            if time_since_start > grace_period:  # Only update if it's been more than grace period
                status.is_running = is_running
                status.last_stopped = timezone.now()
                status.save()
        elif is_running:  # If we found a running process, always update
            status.is_running = is_running
            status.save()
    
    return JsonResponse({
        'is_running': status.is_running,
        'last_started': status.last_started.isoformat() if status.last_started else None,
        'last_stopped': status.last_stopped.isoformat() if status.last_stopped else None
    })

@login_required
@csrf_protect
@require_POST
def update_runs_per_day(request):
    """Update the runs per day configuration in config.json"""
    try:
        data = json.loads(request.body)
        runs_per_day = data.get('runs_per_day')
        
        if runs_per_day is None:
            return JsonResponse({
                'success': False,
                'error': 'Missing runs_per_day parameter'
            })
            
        if not isinstance(runs_per_day, int) or runs_per_day < 0:
            return JsonResponse({
                'success': False,
                'error': 'Invalid runs_per_day value. Must be a non-negative integer.'
            })
            
        # Get the path to setup_num_runs.py
        setup_script = os.path.join(settings.BASE_DIR, 'setup_num_runs.py')
        python_exe = sys.executable
        
        # Run the setup script
        result = subprocess.run(
            [python_exe, setup_script, str(runs_per_day)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return JsonResponse({
                'success': False,
                'error': f'Failed to update configuration: {result.stderr}'
            })
            
        # Calculate the interval text
        if runs_per_day == 0:
            interval = "Run once and exit"
        else:
            seconds_per_day = 86400
            interval_seconds = seconds_per_day / runs_per_day
            
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
            if seconds > 0 and not parts:
                parts.append(f"{int(seconds)} second{'s' if seconds > 1 else ''}")
                
            interval = "Every " + " and ".join(parts)
        
        return JsonResponse({
            'success': True,
            'interval': interval
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@csrf_protect
@require_POST
def update_email_config(request):
    """Update the email configuration in email_config.json"""
    try:
        data = json.loads(request.body)
        
        # Validate email configuration
        email_config = data.get('email', {})
        send_demo_email = data.get('send_demo_email', False)
        
        if send_demo_email:
            # Validate required fields when send_demo_email is True
            if not email_config.get('to'):
                return JsonResponse({
                    'success': False,
                    'error': 'Recipient email is required when send demo email is enabled'
                })
            
            if not email_config.get('subject'):
                return JsonResponse({
                    'success': False,
                    'error': 'Subject is required when send demo email is enabled'
                })
            
            if not email_config.get('message'):
                return JsonResponse({
                    'success': False,
                    'error': 'Message is required when send demo email is enabled'
                })
        
        # Prepare the configuration
        config = {
            'email': email_config,
            'send_demo_email': send_demo_email
        }
        
        # Save to email_config.json
        config_path = os.path.join(settings.BASE_DIR, 'email_config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        
        return JsonResponse({
            'success': True
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def email_config(request):
    """Email configuration page"""
    email_config = load_email_config()
    return render(request, 'scheduler_control/email_config.html', {
        'email_config': email_config
    })

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
@csrf_protect
@require_POST
def execute_management_command(request):
    """Execute Django management commands"""
    try:
        data = json.loads(request.body)
        command = data.get('command')
        args = data.get('args', [])
        
        if not command:
            return JsonResponse({
                'success': False,
                'error': 'Command is required'
            })
            
        # Only allow specific commands
        allowed_commands = ['createsuperuser', 'createuser', 'changepassword']
        if command not in allowed_commands:
            return JsonResponse({
                'success': False,
                'error': f'Command not allowed. Allowed commands: {", ".join(allowed_commands)}'
            })
            
        # Capture command output
        output = StringIO()
        try:
            call_command(command, *args, stdout=output)
            return JsonResponse({
                'success': True,
                'output': output.getvalue()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'output': output.getvalue()
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }) 