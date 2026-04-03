from django.utils.deprecation import MiddlewareMixin

from app.apps.usage.api_auth import resolve_api_key


class ApiKeyTenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.api_credential = None
        token = (request.headers.get("Authorization") or "").strip()
        if token.startswith("Bearer "):
            token = token[7:].strip()
        if not token:
            token = (request.headers.get("X-API-Key") or "").strip()
        if not token or not token.startswith("sk_"):
            return None
        cred = resolve_api_key(token)
        if cred:
            request.tenant = cred.tenant
            request.api_credential = cred
        return None
