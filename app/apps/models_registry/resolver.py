from .models import EmbeddingModel, TenantModelBinding


def resolve_default_base_model_id(tenant_id):
    q = TenantModelBinding.objects.filter(
        tenant_id=tenant_id,
        enabled=True,
        base_model__is_active=True,
    ).select_related("base_model")
    d = q.filter(is_default=True).first()
    if d:
        return d.base_model_id
    b = q.order_by("priority", "id").first()
    if b:
        return b.base_model_id
    return None


def resolve_active_embedding_model(embedding_model_id):
    try:
        return EmbeddingModel.objects.get(pk=int(embedding_model_id), is_active=True)
    except (ValueError, EmbeddingModel.DoesNotExist):
        return None
