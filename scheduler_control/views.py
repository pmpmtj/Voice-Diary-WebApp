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
from .models import SchedulerStatus, SchedulerLog
from django.conf import settings

# Global variable to store the scheduler process
scheduler_process = None

def find_scheduler_process():
    """Find the running scheduler process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'scheduler.py' in ' '.join(proc.info['cmdline'] or []):
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
            
            # Check if process started successfully
            if scheduler_process.poll() is not None:
                error_output = scheduler_process.stderr.read()
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
                    proc.wait(timeout=5)
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
    return JsonResponse({
        'is_running': status.is_running,
        'last_started': status.last_started.isoformat() if status.last_started else None,
        'last_stopped': status.last_stopped.isoformat() if status.last_stopped else None
    }) 