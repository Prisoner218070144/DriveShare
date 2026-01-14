import os
import uuid
import hashlib
import mimetypes
from typing import Optional, Tuple, Generator
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from .models import File, FilePermission, AuditLog, StreamingSession

# Install python-magic if not installed: pip install python-magic
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

class FileStorageService:
    """Handles all file storage operations with explicit control"""
    
    @staticmethod
    def save_uploaded_file(uploaded_file: UploadedFile) -> Tuple[str, int, str]:
        """Save uploaded file to storage and return (stored_name, size, original_name)"""
        original_name = uploaded_file.name
        
        # Generate unique filename with original extension
        file_ext = os.path.splitext(original_name)[1]
        stored_name = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(settings.STORAGE_ROOT, stored_name)
        
        # Create storage directory if it doesn't exist
        os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
        
        # Write file in chunks to handle large files
        chunk_size = 8192  # 8KB chunks for writing
        total_size = 0
        
        with open(file_path, 'wb') as dest:
            for chunk in uploaded_file.chunks(chunk_size):
                dest.write(chunk)
                total_size += len(chunk)
        
        return stored_name, total_size, original_name
    
    @staticmethod
    def detect_file_type(file_path: str) -> Tuple[str, str]:
        """Detect MIME type and categorize file"""
        mime_type = 'application/octet-stream'
        
        try:
            if MAGIC_AVAILABLE:
                # Use python-magic for accurate MIME detection
                mime = magic.Magic(mime=True)
                mime_type = mime.from_file(file_path)
            else:
                # Fallback to mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
        except:
            mime_type = 'application/octet-stream'
        
        # Categorize based on MIME type
        if mime_type.startswith('image/'):
            file_type = 'image'
        elif mime_type.startswith('audio/'):
            file_type = 'audio'
        elif mime_type.startswith('video/'):
            file_type = 'video'
        elif mime_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'text/plain', 'text/html', 'application/json', 'text/csv']:
            file_type = 'document'
        elif mime_type in ['application/zip', 'application/x-rar-compressed', 
                          'application/x-tar', 'application/x-7z-compressed']:
            file_type = 'archive'
        else:
            file_type = 'other'
        
        return mime_type, file_type
    
    @staticmethod
    def get_preview_info(mime_type: str, file_type: str) -> bool:
        """Check if file can be previewed"""
        previewable_types = ['image', 'document', 'audio', 'video']
        previewable_mimes = [
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml',
            'application/pdf', 'text/plain', 'text/html', 'application/json', 'text/csv',
            'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-wav',
            'video/mp4', 'video/webm', 'video/ogg', 'video/x-msvideo', 'video/quicktime'
        ]
        
        return file_type in previewable_types or mime_type in previewable_mimes
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class StreamingService:
    """Handles byte-range streaming for audio/video files"""
    
    @staticmethod
    def parse_range_header(range_header: str, file_size: int) -> Optional[Tuple[int, int]]:
        """Parse HTTP Range header and return (start, end) bytes"""
        if not range_header or 'bytes=' not in range_header:
            return None
        
        try:
            range_str = range_header.split('bytes=')[1]
            parts = range_str.split('-')
            
            if len(parts) != 2:
                return None
            
            start_str, end_str = parts
            
            # Parse start byte
            start = int(start_str) if start_str else 0
            
            # Parse end byte
            if end_str:
                end = int(end_str)
                if end >= file_size:
                    end = file_size - 1
            else:
                end = file_size - 1
            
            # Validate range
            if start < 0 or start > end or end >= file_size:
                return None
                
            return start, end
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def stream_file_chunks(file_path: str, start_byte: int, end_byte: int, 
                          chunk_size: int = settings.CHUNK_SIZE) -> Generator[bytes, None, None]:
        """Generator that yields file chunks for streaming"""
        with open(file_path, 'rb') as f:
            f.seek(start_byte)
            bytes_to_read = end_byte - start_byte + 1
            
            while bytes_to_read > 0:
                chunk = f.read(min(chunk_size, bytes_to_read))
                if not chunk:
                    break
                yield chunk
                bytes_to_read -= len(chunk)
    
    @staticmethod
    def get_content_range_header(start: int, end: int, file_size: int) -> str:
        """Generate Content-Range header string"""
        return f"bytes {start}-{end}/{file_size}"


class PermissionService:
    """Handles permission checks and management"""
    
    # Permission flags (bitwise)
    READ = 1   # 001
    WRITE = 2  # 010
    ADMIN = 4  # 100
    
    @staticmethod
    def has_permission(user, file_obj, required_permission: int) -> bool:
        """Check if user has required permission for file"""
        # Owner has all permissions
        if file_obj.owner == user:
            return True
        
        # Admin users have all permissions
        if user.is_superuser:
            return True
        
        # Check explicit permissions
        try:
            permission = FilePermission.objects.get(file=file_obj, user=user)
            return (permission.permission & required_permission) == required_permission
        except FilePermission.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_files(user):
        """Get all files user has access to (including shared files)"""
        # Files owned by user
        owned_files = File.objects.filter(owner=user)
        
        # Files shared with user
        shared_permissions = FilePermission.objects.filter(user=user)
        shared_files = File.objects.filter(
            id__in=shared_permissions.values_list('file_id', flat=True)
        )
        
        # Combine and return unique files
        file_ids = set(owned_files.values_list('id', flat=True))
        file_ids.update(shared_files.values_list('id', flat=True))
        
        return File.objects.filter(id__in=file_ids)
    
    @staticmethod
    def grant_permission(file_obj, user, permission_type: int, granted_by):
        """Grant permission to user for file"""
        with transaction.atomic():
            permission, created = FilePermission.objects.update_or_create(
                file=file_obj,
                user=user,
                defaults={
                    'permission': permission_type,
                    'granted_by': granted_by,
                    'granted_at': timezone.now()
                }
            )
            
            # Log the action
            AuditLog.objects.create(
                user=granted_by,
                action='permission_grant',
                file=file_obj,
                details={
                    'target_user_id': user.id,
                    'target_user_email': user.email,
                    'permission_type': permission_type,
                    'file_id': str(file_obj.id),
                    'file_name': file_obj.original_name
                }
            )
            
            return permission


class AuditService:
    """Handles audit logging"""
    
    @staticmethod
    def log_action(user, action: str, file=None, details=None, request=None):
        """Log user action"""
        log_data = {
            'user': user,
            'action': action,
            'file': file,
            'details': details or {},
            'created_at': timezone.now()
        }
        
        if request:
            log_data['ip_address'] = request.META.get('REMOTE_ADDR')
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT')
        
        return AuditLog.objects.create(**log_data)
    
    @staticmethod
    def start_streaming_session(user, file_obj, session_id: str):
        """Start a new streaming session"""
        return StreamingSession.objects.create(
            user=user,
            file=file_obj,
            session_id=session_id,
            start_time=timezone.now()
        )
    
    @staticmethod
    def update_streaming_session(session_id: str, bytes_streamed: int, 
                               duration_seconds: int = 0, completed: bool = False):
        """Update streaming session"""
        try:
            session = StreamingSession.objects.get(session_id=session_id)
            session.bytes_streamed = bytes_streamed
            session.duration_seconds = duration_seconds
            if completed:
                session.end_time = timezone.now()
                session.completed = True
            session.save()
            return session
        except StreamingSession.DoesNotExist:
            return None