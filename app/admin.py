from django.contrib import admin
from .models import File, FilePermission, VirtualFolder, Tag, AuditLog, StreamingSession

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'owner', 'file_type', 'size', 'created_at')
    list_filter = ('file_type', 'owner')
    search_fields = ('original_name', 'owner__email')

@admin.register(FilePermission)
class FilePermissionAdmin(admin.ModelAdmin):
    list_display = ('file', 'user', 'permission', 'granted_at')
    list_filter = ('permission',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'file', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__email', 'file__original_name')

@admin.register(StreamingSession)
class StreamingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'file', 'start_time', 'bytes_streamed', 'completed')
    list_filter = ('completed', 'start_time')

admin.site.register(VirtualFolder)
admin.site.register(Tag)