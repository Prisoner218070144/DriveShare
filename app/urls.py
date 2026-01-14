from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import url_handlers

urlpatterns = [
    # Root redirect
    path('', RedirectView.as_view(url='dashboard/', permanent=False), name='home'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    
    # User views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('files/', views.list_files, name='files'),
    path('upload/', views.upload_file, name='upload'),
    
    # File operations
    path('file/<uuid:file_id>/preview/', views.preview_file, name='preview'),
    path('file/<uuid:file_id>/stream/', views.stream_file, name='stream'),
    path('file/<uuid:file_id>/download/', views.download_file, name='download'),
    path('file/<uuid:file_id>/share/', views.share_file, name='share'),
    
    # Admin views
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/logs/', views.admin_logs, name='admin_logs'),
    path('management/drive-access/', views.admin_drive_access, name='admin_drive_access'),
    path('management/file-preview/', views.admin_file_preview, name='admin_file_preview'),
    
    # Protected file access (handled by middleware)
    path('protected/<path:file_path>', url_handlers.protected_file_handler),
]