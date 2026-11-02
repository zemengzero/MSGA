"""Privacy-preserving audit records for protected restore operations."""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .backup import restore_backup


AUDIT_WARNING = "数据恢复成功，但审计记录未写入"


@dataclass(frozen=True)
class RestoreReport:
    protection_path: Path
    audit_warning: str
    operation_id: str


def _timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _append_event(audit_path, record):
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n")


def _record(store, operation_id, event, backup_file, protection_file="", error_type=""):
    return {
        "operation_id": operation_id,
        "timestamp": _timestamp(),
        "event": event,
        "backup_file": backup_file,
        "protection_file": protection_file,
        "error_type": error_type,
        "writes_disabled": bool(store.writes_disabled),
    }


def _try_append(audit_path, record):
    try:
        _append_event(audit_path, record)
        return True
    except Exception:
        return False


def _file_name(value):
    return Path(value).name if value else ""


def restore_with_audit(store, source, protection_dir, audit_path):
    """Restore once and append start/result events without blocking recovery."""
    source = Path(source)
    operation_id = uuid.uuid4().hex
    backup_file = _file_name(source)
    audit_ok = _try_append(
        audit_path,
        _record(store, operation_id, "started", backup_file),
    )

    try:
        protection = restore_backup(store, source, protection_dir)
    except Exception as exc:
        _try_append(
            audit_path,
            _record(
                store,
                operation_id,
                "failed",
                backup_file,
                _file_name(getattr(exc, "protection_path", None)),
                type(exc).__name__,
            ),
        )
        raise

    audit_ok = (
        _try_append(
            audit_path,
            _record(
                store,
                operation_id,
                "succeeded",
                backup_file,
                _file_name(protection),
            ),
        )
        and audit_ok
    )
    return RestoreReport(
        protection_path=protection,
        audit_warning="" if audit_ok else AUDIT_WARNING,
        operation_id=operation_id,
    )
