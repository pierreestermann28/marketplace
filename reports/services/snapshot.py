from typing import Any


PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def _stringify(value):
    if value is None:
        return None
    return str(value)


def _normalize_value(value):
    if isinstance(value, PRIMITIVE_TYPES):
        return value
    return _stringify(value)


def _normalize_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return {}
    return {key: _normalize_value(val) for key, val in snapshot.items()}


def build_target_snapshot(target: Any) -> dict:
    if not target:
        return {}

    data = {
        "model": getattr(getattr(target, "_meta", None), "label_lower", None),
        "id": _stringify(getattr(target, "pk", None)),
    }

    for key in ("title", "slug", "status"):
        if hasattr(target, key):
            val = getattr(target, key)
            if val not in (None, ""):
                data[key] = val

    listing = getattr(target, "listing", None)
    if listing is not None:
        data["listing_id"] = _stringify(getattr(listing, "pk", None))
        if hasattr(listing, "title") and listing.title:
            data["listing_title"] = listing.title

    return data
