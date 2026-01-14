from django.db.models import Sum
from .services import PermissionService

def storage_stats(request):
    """Add storage statistics to template context"""
    if request.user.is_authenticated:
        user_files = PermissionService.get_user_files(request.user)
        total_size = user_files.aggregate(total=Sum('size'))['total'] or 0
        file_count = user_files.count()
        
        return {
            'user_storage_used': total_size,
            'user_file_count': file_count,
        }
    return {}