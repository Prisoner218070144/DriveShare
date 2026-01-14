from django.core.exceptions import PermissionDenied

def is_owner_or_admin(user, file_obj):
    """Check if user is owner or admin"""
    return file_obj.owner == user or user.is_superuser

def owner_or_admin_required():
    """Decorator to check if user is owner or admin"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # This will be used in views that have file_id parameter
            from .models import File
            from .services import PermissionService
            
            file_id = kwargs.get('file_id')
            if file_id:
                file_obj = File.objects.get(id=file_id)
                if not is_owner_or_admin(request.user, file_obj):
                    raise PermissionDenied("You don't have permission to access this file.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator