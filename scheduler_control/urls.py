from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('toggle/', views.toggle_scheduler, name='toggle_scheduler'),
    path('status/', views.get_status, name='get_status'),
    path('login/', auth_views.LoginView.as_view(template_name='scheduler_control/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
] 