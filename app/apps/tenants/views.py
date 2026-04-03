import json
import re

import config
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Plan, Tenant, TenantMembership, UserAccount

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


def _json_body(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    required = ("tenant_name", "slug", "contact_email", "password")
    for k in required:
        if k not in data or not str(data[k]).strip():
            return JsonResponse({"error": "missing_field", "field": k}, status=400)
    slug = data["slug"].strip().lower()
    if not _SLUG_RE.match(slug):
        return JsonResponse({"error": "invalid_slug"}, status=400)
    if Tenant.objects.filter(slug=slug).exists():
        return JsonResponse({"error": "slug_taken"}, status=409)
    if UserAccount.objects.filter(email=data["contact_email"].strip().lower()).exists():
        return JsonResponse({"error": "email_taken"}, status=409)
    plan = None
    code = data.get("plan_code")
    if code:
        plan = Plan.objects.filter(code=code, is_active=True).first()
        if not plan:
            return JsonResponse({"error": "invalid_plan_code"}, status=400)
    else:
        plan = Plan.objects.filter(is_active=True).order_by("id").first()
    now = timezone.now()
    with transaction.atomic():
        user = UserAccount.objects.create(
            email=data["contact_email"].strip().lower(),
            password_hash=make_password(data["password"]),
            display_name=data.get("display_name") or "",
            is_active=True,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        tenant = Tenant.objects.create(
            name=data["tenant_name"].strip(),
            slug=slug,
            status=Tenant.Status.PENDING_REVIEW,
            contact_email=data["contact_email"].strip(),
            plan=plan,
            review_note=None,
            reviewed_at=None,
            archived_at=None,
            created_at=now,
            updated_at=now,
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user_account=user,
            role=TenantMembership.Role.OWNER,
            created_at=now,
        )
    return JsonResponse(
        {
            "tenant_id": tenant.id,
            "user_id": user.id,
            "status": tenant.status,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return JsonResponse({"error": "missing_field"}, status=400)
    try:
        user = UserAccount.objects.get(email=email)
    except UserAccount.DoesNotExist:
        return JsonResponse({"error": "invalid_credentials"}, status=401)
    if not user.password_hash or not check_password(password, user.password_hash):
        return JsonResponse({"error": "invalid_credentials"}, status=401)
    if not user.is_active:
        return JsonResponse({"error": "inactive"}, status=403)
    request.session["user_account_id"] = user.id
    rows = []
    for m in TenantMembership.objects.select_related("tenant").filter(user_account=user):
        rows.append(
            {
                "tenant_id": m.tenant_id,
                "slug": m.tenant.slug,
                "role": m.role,
                "tenant_status": m.tenant.status,
            }
        )
    return JsonResponse({"user_id": user.id, "tenants": rows})


@require_http_methods(["GET"])
def me(request):
    uid = request.session.get("user_account_id")
    if not uid:
        return JsonResponse({"error": "unauthorized"}, status=401)
    try:
        user = UserAccount.objects.get(pk=uid)
    except UserAccount.DoesNotExist:
        return JsonResponse({"error": "unauthorized"}, status=401)
    rows = []
    for m in TenantMembership.objects.select_related("tenant").filter(user_account=user):
        rows.append(
            {
                "tenant_id": m.tenant_id,
                "slug": m.tenant.slug,
                "role": m.role,
                "tenant_status": m.tenant.status,
            }
        )
    return JsonResponse({"user_id": user.id, "email": user.email, "tenants": rows})


@csrf_exempt
@require_http_methods(["POST"])
def approve_tenant(request, tenant_id):
    secret = request.headers.get("X-Internal-Secret") or ""
    if not config.INTERNAL_API_SECRET or secret != config.INTERNAL_API_SECRET:
        return JsonResponse({"error": "forbidden"}, status=403)
    try:
        data = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    approve = bool(data.get("approve"))
    now = timezone.now()
    if approve:
        plan_id = data.get("plan_id")
        plan = None
        if plan_id is not None:
            plan = Plan.objects.filter(pk=plan_id, is_active=True).first()
            if not plan:
                return JsonResponse({"error": "invalid_plan_id"}, status=400)
        tenant.status = Tenant.Status.ACTIVE
        tenant.plan = plan if plan is not None else tenant.plan
        tenant.review_note = data.get("review_note") or ""
        tenant.reviewed_at = now
        tenant.updated_at = now
        tenant.save(
            update_fields=[
                "status",
                "plan",
                "review_note",
                "reviewed_at",
                "updated_at",
            ]
        )
    else:
        tenant.status = Tenant.Status.SUSPENDED
        tenant.review_note = data.get("review_note") or ""
        tenant.reviewed_at = now
        tenant.updated_at = now
        tenant.save(
            update_fields=["status", "review_note", "reviewed_at", "updated_at"]
        )
    return JsonResponse(
        {"tenant_id": tenant.id, "status": tenant.status},
        status=200,
    )


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    request.session.flush()
    return JsonResponse({"ok": True})
