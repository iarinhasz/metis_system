"""O grupo "revisores": quem decide no gate de integridade, sem poder mexer no resto."""

from typing import Final

from django.contrib.auth.models import Group, Permission

REVIEWERS_GROUP: Final = "revisores"
# Ver o run e os achados, e decidir no gate (continuar ou encerrar).
PERMISSIONS: Final = (
    ("attempts", "view_run"),
    ("attempts", "decide_run"),
    ("integrity", "view_integrityreport"),
    ("integrity", "view_integrityfinding"),
)


def ensure_reviewers_group() -> Group:
    group, _ = Group.objects.get_or_create(name=REVIEWERS_GROUP)
    for app_label, codename in PERMISSIONS:
        permission = Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        ).first()
        if permission is not None:
            group.permissions.add(permission)
    return group
