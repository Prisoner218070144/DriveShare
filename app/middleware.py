from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

class PermissionMiddleware(MiddlewareMixin):
    """Middleware to enforce permission checks on all file access"""
    
    def process_request(self, request):
        # Check if request is for protected files
        if request.path.startswith('/protected/'):
            return HttpResponse(
                'Direct file access not allowed. Use streaming endpoints.',
                status=403
            )
        
        return None