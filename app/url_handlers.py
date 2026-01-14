from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import File

def protected_file_handler(request, file_path):
    """Handle requests to protected files - ensures all access goes through permission checks"""
    # This should never be directly accessed in production
    # It's a safety net that redirects to the proper streaming endpoint
    
    # Extract file UUID from path
    try:
        file_uuid = file_path.split('/')[0]  # First part is the UUID filename
        file_obj = get_object_or_404(File, stored_name=file_uuid)
        
        # Redirect to streaming endpoint which will check permissions
        return HttpResponseRedirect(f'/file/{file_obj.id}/stream/')
    except:
        # If we can't identify the file, return 404
        return HttpResponse('File not found', status=404)