import re

_TENANT_OPTIONAL_EXACT = frozenset(
    {
        "/api/v1/tenants/register",
        "/api/v1/tenants/login",
        "/api/v1/tenants/logout",
        "/api/v1/tenants/me",
    }
)

_TENANT_OPTIONAL_INFERENCE = frozenset(
    {
        "/api/v1/inference/base-models",
        "/api/v1/inference/embedding-models",
    }
)

_APPROVE = re.compile(r"^/api/v1/tenants/\d+/approve$")


def is_tenant_optional_path(path):
    if path in _TENANT_OPTIONAL_EXACT:
        return True
    if path in _TENANT_OPTIONAL_INFERENCE:
        return True
    if _APPROVE.match(path):
        return True
    return False
