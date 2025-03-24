from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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
def dashboard(request):
    """Main dashboard view"""
    status, created = SchedulerStatus.objects.get_or_create()
    logs = SchedulerLog.objects.all().order_by('-timestamp')[:10]  # Get last 10 logs
    return render(request, 'scheduler_control/dashboard.html', {
        'status': status,
        'logs': logs
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