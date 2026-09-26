"""Small shared factories used by stage 1 data models."""

from datetime import datetime
from uuid import uuid4


def _generate_id() -> str:
    return uuid4().hex


def _generate_timestamp() -> str:
    return datetime.now().isoformat()
