from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from app.apps.isolation.exempt import is_tenant_optional_path


class TenantRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path
        if not path.startswith("/api/v1/"):
            return None
        if is_tenant_optional_path(path):
            return None
        if getattr(request, "tenant", None) is not None:
            return None
        return JsonResponse({"error": "tenant_required"}, status=400)
