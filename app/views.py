import os
import json
import uuid
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.conf import settings
from pathlib import Path
from .models import File, AuditLog, StreamingSession
from .services import FileStorageService, StreamingService, PermissionService, AuditService
from .utils import validate_file_upload

@require_http_methods(['GET', 'POST'])
def login_view(request):
    """User login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                AuditService.log_action(user, 'login', request=request)
                return redirect('dashboard')
        except User.DoesNotExist:
            pass
        
        return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    """User logout"""
    AuditService.log_action(request.user, 'logout', request=request)
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    """User dashboard"""
    user_files = PermissionService.get_user_files(request.user)
    
    # Get statistics
    total_size = user_files.aggregate(total=Sum('size'))['total'] or 0
    file_count = user_files.count()
    
    # Recent files
    recent_files = user_files.order_by('-created_at')[:10]
    
    # Files by type
    files_by_type = user_files.values('file_type').annotate(count=Count('id'))
    
    context = {
        'files': recent_files,
        'total_size': total_size,
        'file_count': file_count,
        'files_by_type': files_by_type,
        'user_file_count': file_count,
        'user_storage_used': total_size,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
@require_http_methods(['GET', 'POST'])
@ensure_csrf_cookie
def upload_file(request):
    """Upload new file"""
    if request.method == 'POST':
        # Check if it's AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX upload
            uploaded_file = request.FILES.get('file')
        else:
            # Form upload
            uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        # Validate file
        validation_error = validate_file_upload(uploaded_file)
        if validation_error:
            return JsonResponse({'error': validation_error}, status=400)
        
        try:
            # Save file to storage
            stored_name, file_size, original_name = FileStorageService.save_uploaded_file(uploaded_file)
            
            # Get file path and detect type
            file_path = os.path.join(settings.STORAGE_ROOT, stored_name)
            mime_type, file_type = FileStorageService.detect_file_type(file_path)
            
            # Check if preview is available
            preview_available = FileStorageService.get_preview_info(mime_type, file_type)
            
            # Create file record
            file_obj = File.objects.create(
                stored_name=stored_name,
                original_name=original_name,
                owner=request.user,
                size=file_size,
                mime_type=mime_type,
                file_type=file_type,
                preview_available=preview_available
            )
            
            # Log the upload
            AuditService.log_action(
                request.user,
                'upload',
                file=file_obj,
                details={
                    'file_name': original_name,
                    'file_size': file_size,
                    'mime_type': mime_type,
                    'file_type': file_type
                },
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'file_id': str(file_obj.id),
                'file_name': file_obj.original_name
            })
            
        except Exception as e:
            # Clean up if file was partially saved
            if 'stored_name' in locals():
                file_path = os.path.join(settings.STORAGE_ROOT, stored_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return JsonResponse({'error': str(e)}, status=500)
    
    # For GET request, return upload form
    return render(request, 'upload.html')

@login_required
def list_files(request):
    """List files with filtering and pagination"""
    user_files = PermissionService.get_user_files(request.user)
    
    # Apply filters
    file_type = request.GET.get('type')
    if file_type:
        user_files = user_files.filter(file_type=file_type)
    
    search_query = request.GET.get('q')
    if search_query:
        user_files = user_files.filter(
            Q(original_name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Pagination
    paginator = Paginator(user_files.order_by('-created_at'), 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'file_types': File.FILE_TYPES,
        'selected_type': file_type,
        'search_query': search_query or '',
    }
    
    return render(request, 'files.html', context)

@login_required
def preview_file(request, file_id):
    """Preview file content"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check permission
    if not PermissionService.has_permission(request.user, file_obj, PermissionService.READ):
        return HttpResponse('Access denied', status=403)
    
    # Log preview action
    AuditService.log_action(
        request.user,
        'view',
        file=file_obj,
        details={'preview': True},
        request=request
    )
    
    context = {
        'file': file_obj,
        'is_owner': file_obj.owner == request.user,
        'can_download': PermissionService.has_permission(
            request.user, file_obj, PermissionService.READ
        ),
    }
    
    return render(request, 'preview.html', context)

@login_required
def stream_file(request, file_id):
    """Stream media file with byte-range support"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check permission
    if not PermissionService.has_permission(request.user, file_obj, PermissionService.READ):
        return HttpResponse('Access denied', status=403)
    
    file_path = file_obj.get_storage_path()
    
    if not os.path.exists(file_path):
        return HttpResponse('File not found', status=404)
    
    file_size = os.path.getsize(file_path)
    
    # Parse range header for partial content
    range_header = request.META.get('HTTP_RANGE')
    range_tuple = StreamingService.parse_range_header(range_header, file_size)
    
    # Generate session ID for tracking
    session_id = request.GET.get('session_id') or str(uuid.uuid4())
    
    if range_tuple:
        # Partial content response
        start_byte, end_byte = range_tuple
        
        # Start or update streaming session
        if range_header and start_byte == 0:
            # Start of stream
            AuditService.start_streaming_session(request.user, file_obj, session_id)
            AuditService.log_action(
                request.user,
                'stream_start',
                file=file_obj,
                details={'session_id': session_id, 'range': range_header},
                request=request
            )
        
        # Stream the file chunk
        response = StreamingHttpResponse(
            StreamingService.stream_file_chunks(file_path, start_byte, end_byte),
            status=206,  # Partial Content
            content_type=file_obj.mime_type
        )
        
        response['Content-Range'] = StreamingService.get_content_range_header(
            start_byte, end_byte, file_size
        )
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = str(end_byte - start_byte + 1)
        
        # Update streaming session
        bytes_streamed = end_byte - start_byte + 1
        duration_param = request.GET.get('duration', '0')
        try:
            duration_seconds = int(float(duration_param))
        except ValueError:
            duration_seconds = 0
            
        AuditService.update_streaming_session(
            session_id, bytes_streamed, duration_seconds
        )
        
    else:
        # Full file response (download)
        response = StreamingHttpResponse(
            StreamingService.stream_file_chunks(file_path, 0, file_size - 1),
            content_type=file_obj.mime_type
        )
        response['Content-Length'] = str(file_size)
        response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
        
        # Log download
        AuditService.log_action(
            request.user,
            'download',
            file=file_obj,
            details={'full_download': True},
            request=request
        )
    
    return response

@login_required
def download_file(request, file_id):
    """Download file directly"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check permission
    if not PermissionService.has_permission(request.user, file_obj, PermissionService.READ):
        return HttpResponse('Access denied', status=403)
    
    file_path = file_obj.get_storage_path()
    
    if not os.path.exists(file_path):
        return HttpResponse('File not found', status=404)
    
    file_size = os.path.getsize(file_path)
    
    def file_iterator():
        with open(file_path, 'rb') as f:
            while chunk := f.read(settings.CHUNK_SIZE):
                yield chunk
    
    response = StreamingHttpResponse(file_iterator(), content_type=file_obj.mime_type)
    response['Content-Length'] = str(file_size)
    response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
    
    # Log download
    AuditService.log_action(
        request.user,
        'download',
        file=file_obj,
        request=request
    )
    
    return response

@login_required
@require_http_methods(['POST'])
def share_file(request, file_id):
    """Share file with another user"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check permission - only owner or users with ADMIN permission can share
    if (file_obj.owner != request.user and 
        not PermissionService.has_permission(request.user, file_obj, PermissionService.ADMIN)):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        user_email = data.get('email')
        permission_type = int(data.get('permission', PermissionService.READ))
        
        # Find user
        target_user = User.objects.get(email=user_email)
        
        # Don't share with owner
        if target_user == file_obj.owner:
            return JsonResponse({'error': 'Cannot share with file owner'}, status=400)
        
        # Grant permission
        PermissionService.grant_permission(file_obj, target_user, permission_type, request.user)
        
        return JsonResponse({'success': True})
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(['GET', 'POST'])
def register_view(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if not username or not password1 or not password2:
            return render(request, 'register.html', {'error': 'All fields are required'})
        
        if password1 != password2:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        
        if email and User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already exists'})
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        
        # Log the user in
        login(request, user)
        AuditService.log_action(user, 'registration', request=request)
        return redirect('dashboard')
    
    return render(request, 'register.html')

@login_required
def profile_view(request):
    """User profile"""
    # Get recent activity
    recent_activity = AuditLog.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'recent_activity': recent_activity,
    }
    
    return render(request, 'profile.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """Admin dashboard with system statistics"""
    # System statistics
    total_files = File.objects.count()
    total_size = File.objects.aggregate(total=Sum('size'))['total'] or 0
    total_users = User.objects.count()
    
    # Recent activity
    recent_logs = AuditLog.objects.select_related('user', 'file').order_by('-created_at')[:50]
    
    # Active streaming sessions (last 1 hour)
    active_sessions = StreamingSession.objects.filter(
        end_time__isnull=True,
        start_time__gte=timezone.now() - timedelta(hours=1)
    ).select_related('user', 'file')
    
    # Storage usage by user
    storage_by_user = User.objects.annotate(
        total_size=Sum('owned_files__size'),
        file_count=Count('owned_files')
    ).order_by('-total_size')
    
    # Max storage for percentage calculation
    max_storage = storage_by_user.first().total_size if storage_by_user else 1
    
    context = {
        'total_files': total_files,
        'total_size': total_size,
        'total_users': total_users,
        'recent_logs': recent_logs,
        'active_sessions': active_sessions,
        'storage_by_user': storage_by_user,
        'max_storage': max_storage,
        'action_types': AuditLog.ACTION_TYPES,
    }
    
    return render(request, 'admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_logs(request):
    """View audit logs with filtering"""
    logs = AuditLog.objects.select_related('user', 'file').order_by('-created_at')
    
    # Apply filters
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user__email__icontains=user_filter)
    
    # Pagination
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_types': AuditLog.ACTION_TYPES,
        'selected_action': action_filter,
        'selected_user': user_filter or '',
    }
    
    return render(request, 'admin_logs.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_drive_access(request):
    """Admin access to entire drive"""
    drive_path = request.GET.get('path', 'F:/')
    
    # Security: Validate path is within allowed drives
    allowed_drives = ['F:/', 'C:/', 'D:/', 'E:/']
    if not any(drive_path.startswith(drive) for drive in allowed_drives):
        drive_path = 'F:/'
    
    try:
        # List files and directories
        items = []
        path_obj = Path(drive_path)
        
        if path_obj.exists() and path_obj.is_dir():
            # List directories first
            for item in path_obj.iterdir():
                try:
                    item_info = {
                        'name': item.name,
                        'path': str(item),
                        'is_dir': item.is_dir(),
                        'size': item.stat().st_size if item.is_file() else 0,
                        'modified': item.stat().st_mtime,
                    }
                    items.append(item_info)
                except (PermissionError, OSError):
                    # Skip items we can't access
                    continue
        
        # Sort: directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return JsonResponse({
            'path': drive_path,
            'items': items,
            'parent': str(path_obj.parent) if str(path_obj.parent) != drive_path else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_file_preview(request):
    """Preview file from drive (admin only)"""
    file_path = request.GET.get('path')
    
    if not file_path:
        return JsonResponse({'error': 'No file path provided'}, status=400)
    
    # Security check
    if not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    try:
        # Get file info
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        
        # Check if it's a text file that can be previewed
        text_extensions = ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() in text_extensions and file_size < 1024 * 1024:  # 1MB limit
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Read first 50KB
                return JsonResponse({
                    'type': 'text',
                    'content': content,
                    'size': file_size,
                    'path': file_path
                })
        else:
            # For binary files, just return metadata
            return JsonResponse({
                'type': 'binary',
                'size': file_size,
                'path': file_path,
                'message': 'Binary file cannot be previewed in browser'
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)