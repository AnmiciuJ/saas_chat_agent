from django.utils.deprecation import MiddlewareMixin

from app.apps.tenants.models import Tenant


class TenantContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if getattr(request, "tenant", None) is not None:
            return None
        request.tenant = None
        raw = request.headers.get("X-Tenant-ID") or request.META.get("HTTP_X_TENANT_ID")
        if not raw:
            return None
        try:
            request.tenant = Tenant.objects.get(pk=int(raw))
        except (ValueError, Tenant.DoesNotExist):
            request.tenant = None
        return None
