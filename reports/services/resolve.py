from django.db import transaction
from django.utils import timezone

from reports.models import Report


@transaction.atomic
def resolve_report(*, report: Report, by_user) -> Report:
    if report.is_resolved:
        return report

    report.is_resolved = True
    report.resolved_at = timezone.now()
    report.resolved_by = by_user
    report.save(update_fields=["is_resolved", "resolved_at", "resolved_by"])
    return report
