# -*- coding: utf-8 -*-
"""The logger for agentscope."""

import logging


_DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-7s | "
    "%(module)s:%(funcName)s:%(lineno)s - %(message)s"
)

logger = logging.getLogger("as")


def setup_logger(
    level: str,
    filepath: str | None = None,
) -> None:
    """Set up the agentscope logger.

    Args:
        level (`str`):
            The logging level, chosen from "INFO", "DEBUG", "WARNING",
            "ERROR", "CRITICAL".
        filepath (`str | None`, optional):
            The filepath to save the logging output.
    """
    if level not in ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError(
            f"Invalid logging level: {level}. Must be one of "
            f"'INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'.",
        )
    logger.handlers.clear()
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    logger.addHandler(handler)

    if filepath:
        handler = logging.FileHandler(filepath)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)

    logger.propagate = False


setup_logger("INFO")


def build_log_record(
    run_id: str | None = None,
    session_id: str | None = None,
    event_type: str | None = None,
    fields: dict | None = None,
    secrets: list[str] | None = None,
) -> dict:
    """Build one structured, redacted log record.

    Correlation ids (run_id/session_id) and the event type always come
    through; every string value in ``fields`` is scrubbed of the given
    secret values, and credential-like keys are replaced wholesale.
    """
    from ._utils._common import _generate_id

    safe_fields: dict = {}
    for key, value in (fields or {}).items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("api_key", "apikey", "password", "secret", "token", "credential")):
            safe_fields[key] = "[REDACTED]"
        elif isinstance(value, str) and secrets:
            redacted = value
            for secret in secrets:
                if secret:
                    redacted = redacted.replace(secret, "[REDACTED]")
            safe_fields[key] = redacted
        else:
            safe_fields[key] = value

    return {
        "log_id": _generate_id(),
        "run_id": run_id,
        "session_id": session_id,
        "event_type": event_type,
        "fields": safe_fields,
    }
