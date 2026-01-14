from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os

class File(models.Model):
    FILE_TYPES = [
        ('document', 'Document'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('archive', 'Archive'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stored_name = models.CharField(max_length=255)  # Changed from UUIDField to CharField
    original_name = models.CharField(max_length=500)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_files')
    size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    duration = models.IntegerField(null=True, blank=True)
    preview_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    parent_folder = models.ForeignKey('VirtualFolder', null=True, blank=True, 
                                     on_delete=models.SET_NULL, related_name='files')
    tags = models.ManyToManyField('Tag', blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['owner', 'created_at']),
            models.Index(fields=['file_type']),
            models.Index(fields=['mime_type']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.owner.username})"
    
    def get_storage_path(self):
        """Get the absolute path to the stored file"""
        from django.conf import settings
        return os.path.join(settings.STORAGE_ROOT, self.stored_name)
    
    def get_file_extension(self):
        return os.path.splitext(self.original_name)[1].lower()


class FilePermission(models.Model):
    PERMISSION_TYPES = [
        (1, 'Read'),
        (2, 'Write'),
        (4, 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_permissions')
    permission = models.IntegerField(choices=PERMISSION_TYPES, default=1)
    granted_at = models.DateTimeField(default=timezone.now)
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                  related_name='granted_permissions')
    
    class Meta:
        unique_together = ['file', 'user']
        indexes = [
            models.Index(fields=['file', 'user']),
            models.Index(fields=['user', 'permission']),
        ]
    
    def has_permission(self, required_perm):
        """Check if permission includes required permission using bitwise operations"""
        return (self.permission & required_perm) == required_perm


class VirtualFolder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', null=True, blank=True, 
                              on_delete=models.CASCADE, related_name='children')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['name', 'parent', 'owner']
        indexes = [
            models.Index(fields=['owner', 'parent']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.owner.username})"
    
    def get_path(self):
        """Get the virtual folder path as string"""
        path_parts = []
        folder = self
        while folder:
            path_parts.insert(0, folder.name)
            folder = folder.parent
        return '/'.join(path_parts)


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#5E81AC')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class AuditLog(models.Model):
    ACTION_TYPES = [
        ('upload', 'File Upload'),
        ('download', 'File Download'),
        ('view', 'File View'),
        ('stream_start', 'Stream Start'),
        ('stream_end', 'Stream End'),
        ('permission_grant', 'Permission Grant'),
        ('permission_revoke', 'Permission Revoke'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('delete', 'File Delete'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                            related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['file', 'action']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"


class StreamingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='streaming_sessions')
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='streaming_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    bytes_streamed = models.BigIntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', 'start_time']),
        ]