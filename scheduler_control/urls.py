from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('demo/', views.demo_view, name='demo'),
    path('toggle/', views.toggle_scheduler, name='toggle_scheduler'),
    path('status/', views.get_status, name='get_status'),
    path('update-runs-per-day/', views.update_runs_per_day, name='update_runs_per_day'),
    path('update-email-config/', views.update_email_config, name='update_email_config'),
    path('email-config/', views.email_config, name='email_config'),
    path('execute-command/', views.execute_management_command, name='execute_management_command'),
    path('login/', auth_views.LoginView.as_view(template_name='scheduler_control/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Recording functionality URLs
    path('record/', views.record, name='record'),
    path('process-audio/', views.process_audio, name='process_audio'),
] 