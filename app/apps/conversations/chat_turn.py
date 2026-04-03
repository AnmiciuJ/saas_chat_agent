import config
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from app.apps.knowledge_base.models import KnowledgeBase
from app.apps.models_registry.models import InferenceBaseModel
from app.apps.models_registry.resolver import resolve_default_base_model_id
from app.apps.tenants.models import Tenant, TenantMembership, UserAccount
from app.apps.usage.record import record_chat_usage
from online_service.chat_pipeline import run_assistant_generation
from online_service.retrieve import run_retrieval

from .models import ChatMessage, Conversation


def _default_model_key(tenant_id):
    bid = resolve_default_base_model_id(tenant_id)
    if not bid:
        return None
    try:
        return InferenceBaseModel.objects.get(pk=bid).model_key
    except InferenceBaseModel.DoesNotExist:
        return None


def _history_messages_payload(hist):
    out = []
    for m in hist:
        if m.role == ChatMessage.Role.USER:
            out.append({"role": "user", "content": m.content})
        elif m.role == ChatMessage.Role.ASSISTANT:
            out.append({"role": "assistant", "content": m.content})
    return out


def process_chat_turn(tenant_id, user_account_id, conversation_id, knowledge_base_id, user_text):
    text = (user_text or "").strip()
    if not text:
        return {"error": "empty_content"}
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return {"error": "invalid_tenant"}
    if tenant.status != Tenant.Status.ACTIVE:
        return {"error": "tenant_inactive"}
    try:
        user = UserAccount.objects.get(pk=user_account_id, is_active=True)
    except UserAccount.DoesNotExist:
        return {"error": "invalid_user"}
    m = TenantMembership.objects.filter(tenant=tenant, user_account=user).first()
    if not m:
        return {"error": "forbidden"}
    kb = None
    if knowledge_base_id is not None:
        try:
            kb = KnowledgeBase.objects.get(pk=knowledge_base_id, tenant=tenant)
        except KnowledgeBase.DoesNotExist:
            return {"error": "invalid_knowledge_base"}
        if kb.status != KnowledgeBase.Status.ACTIVE:
            return {"error": "knowledge_base_inactive"}
    now = timezone.now()
    with transaction.atomic():
        if conversation_id:
            try:
                conv = Conversation.objects.select_for_update().get(
                    pk=conversation_id,
                    tenant=tenant,
                )
            except Conversation.DoesNotExist:
                return {"error": "invalid_conversation"}
            if conv.user_account_id and conv.user_account_id != user.id:
                return {"error": "forbidden"}
            if kb and conv.knowledge_base_id and conv.knowledge_base_id != kb.id:
                return {"error": "knowledge_base_mismatch"}
            if kb and not conv.knowledge_base_id:
                conv.knowledge_base = kb
                conv.updated_at = now
                conv.save(update_fields=["knowledge_base", "updated_at"])
            if not conv.user_account_id:
                conv.user_account = user
                conv.updated_at = now
                conv.save(update_fields=["user_account", "updated_at"])
        else:
            conv = Conversation.objects.create(
                tenant=tenant,
                knowledge_base=kb,
                user_account=user,
                title=text[:120] if text else None,
                summary=None,
                status=Conversation.Status.OPEN,
                last_message_at=None,
                created_at=now,
                updated_at=now,
            )
        retrieval = None
        if kb:
            retrieval = run_retrieval(tenant.id, kb.id, text, top_k=None, snapshot_id=None)
        mx = ChatMessage.objects.filter(conversation=conv).aggregate(m=Max("sequence"))["m"]
        next_seq = (mx or 0) + 1
        hist = list(
            ChatMessage.objects.filter(conversation=conv).order_by("-sequence")[:20]
        )
        hist.reverse()
        base_id = resolve_default_base_model_id(tenant.id)
        mk = _default_model_key(tenant.id) or (config.LLM_DEFAULT_MODEL or "").strip() or None
        hist_payload = _history_messages_payload(hist)
        gen = run_assistant_generation(text, retrieval, hist_payload, mk)
        if gen.get("error"):
            return {"error": gen["error"], "detail": gen.get("detail")}
        assistant_text = gen["assistant_text"]
        pt = gen.get("prompt_tokens")
        ct = gen.get("completion_tokens")
        um = ChatMessage.objects.create(
            tenant=tenant,
            conversation=conv,
            sequence=next_seq,
            role=ChatMessage.Role.USER,
            content=text,
            used_base_model=None,
            rewritten_query=None,
            pipeline_trace=None,
            prompt_tokens=None,
            completion_tokens=None,
            retrieval_refs=None,
            created_at=now,
        )
        trace = (retrieval or {}).get("pipeline_trace")
        refs = (retrieval or {}).get("items")
        rw = (retrieval or {}).get("rewritten_query")
        am = ChatMessage.objects.create(
            tenant=tenant,
            conversation=conv,
            sequence=next_seq + 1,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            used_base_model_id=base_id,
            rewritten_query=rw,
            pipeline_trace=trace,
            prompt_tokens=pt,
            completion_tokens=ct,
            retrieval_refs=refs,
            created_at=now,
        )
        conv.last_message_at = now
        conv.updated_at = now
        if not conv.title and text:
            conv.title = text[:120]
        conv.save(update_fields=["last_message_at", "updated_at", "title"])
        record_chat_usage(tenant.id, conv.id, pt, ct, now)
    return {
        "conversation_id": conv.id,
        "user_message_id": um.id,
        "assistant_message_id": am.id,
        "assistant_text": assistant_text,
        "retrieval_refs": refs,
        "pipeline_trace": trace,
        "rewritten_query": rw,
    }
