from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SchedulerStatus(models.Model):
    """Model to track the scheduler's current status"""
    is_running = models.BooleanField(default=False)
    last_started = models.DateTimeField(null=True, blank=True)
    last_stopped = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Scheduler Status"
    
    def __str__(self):
        return f"Scheduler {'Running' if self.is_running else 'Stopped'}"

class SchedulerLog(models.Model):
    """Model to log scheduler actions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # 'start' or 'stop'
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} {self.action}ed scheduler at {self.timestamp}" 