from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from reports.models import Report
from reports.services.snapshot import build_target_snapshot


class AlreadyReportedError(Exception):
    pass


@transaction.atomic
def create_report(
    *, reporter, target, reason: str, details: str = "", snapshot=None
) -> Report:
    ct = ContentType.objects.get_for_model(target, for_concrete_model=False)

    report = Report(
        reporter=reporter,
        reason=reason,
        details=details,
        target_content_type=ct,
        target_object_id=str(target.pk),
        target_snapshot=(
            snapshot if snapshot is not None else build_target_snapshot(target)
        ),
    )

    try:
        report.save()
    except IntegrityError:
        raise AlreadyReportedError()

    return report
