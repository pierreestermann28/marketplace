import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record):
        timestamp = (
            datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        )
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "batch_id", None):
            payload["batch_id"] = record.batch_id
        if getattr(record, "listing_id", None):
            payload["listing_id"] = record.listing_id
        if record.args:
            payload["args"] = record.args
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
