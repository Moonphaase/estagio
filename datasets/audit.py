from .models import AuditLog


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(request, action, resource, resource_id, description="", changes=None):
    """
    Regista uma entrada de auditoria.

    Uso:
        audit(request, "create", "dataset", dataset.id, "Dataset 'X' criado")
        audit(request, "update", "dataset", dataset.id, "Dataset editado", changes={"name": {"before": "A", "after": "B"}})
        audit(request, "delete", "dataset", dataset.id, "Dataset 'X' apagado")
    """
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        resource=resource,
        resource_id=resource_id,
        description=description,
        changes=changes or {},
        ip_address=get_client_ip(request),
    )


def audit_dataset_changes(before, after):
    """
    Compara dois dicts e devolve apenas os campos que mudaram.
    Uso: audit_dataset_changes(before_dict, after_dict)
    """
    changes = {}
    for key in after:
        if key in before and before[key] != after[key]:
            changes[key] = {"before": before[key], "after": after[key]}
    return changes