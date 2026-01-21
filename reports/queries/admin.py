from reports.models import Report


def get_unresolved_reports(limit=None):
    qs = (
        Report.objects.filter(is_resolved=False)
        .select_related("listing__seller", "reporter")
        .order_by("-created_at")
    )
    if limit:
        qs = qs[:limit]
    return qs
