import os
import re
from typing import Optional
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

def validate_file_upload(uploaded_file: UploadedFile) -> Optional[str]:
    """Validate uploaded file"""
    # Check file size
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        return f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024*1024*1024)}GB"
    
    # Check file extension
    filename = uploaded_file.name.lower()
    dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.php', '.py', '.js']
    
    for ext in dangerous_extensions:
        if filename.endswith(ext):
            return f"File type {ext} is not allowed"
    
    return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove directory components
    filename = os.path.basename(filename)
    
    # Replace spaces and special characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250 - len(ext)] + ext
    
    return filename

def get_mime_category(mime_type: str) -> str:
    """Get category from MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    elif 'pdf' in mime_type or 'document' in mime_type or 'text' in mime_type:
        return 'document'
    else:
        return 'other'