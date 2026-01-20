from typing import Any


def build_target_snapshot(target: Any) -> dict:
    if not target:
        return {}

    data = {
        "model": getattr(getattr(target, "_meta", None), "label_lower", None),
        "id": getattr(target, "pk", None),
    }

    for key in ("title", "slug", "status"):
        if hasattr(target, key):
            val = getattr(target, key)
            if val not in (None, ""):
                data[key] = val

    listing = getattr(target, "listing", None)
    if listing is not None:
        data["listing_id"] = getattr(listing, "pk", None)
        if hasattr(listing, "title") and listing.title:
            data["listing_title"] = listing.title

    return data
