from django.core.exceptions import FieldDoesNotExist


def for_tenant(queryset, tenant):
    model = queryset.model
    try:
        model._meta.get_field("tenant_id")
        return queryset.filter(tenant_id=tenant.id)
    except FieldDoesNotExist:
        pass
    try:
        model._meta.get_field("tenant")
        return queryset.filter(tenant=tenant)
    except FieldDoesNotExist:
        return queryset
