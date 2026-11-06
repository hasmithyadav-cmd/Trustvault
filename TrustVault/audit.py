import hashlib
import json
from datetime import datetime, timezone
from extensions import db
from models import AuditLog

GENESIS = "0" * 64

def _payload(timestamp, actor_id, document_id, action, detail, previous_hash):
    return json.dumps({
        "timestamp": timestamp.isoformat(),
        "actor_id": actor_id,
        "document_id": document_id,
        "action": action,
        "detail": detail,
        "previous_hash": previous_hash,
    }, sort_keys=True, separators=(",", ":"))

def write_audit(action, actor_id=None, document_id=None, detail=""):
    previous = db.session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    previous_hash = previous.entry_hash if previous else GENESIS
    # SQLite stores timezone-naive datetimes; use naive UTC consistently so
    # the hash payload is identical before and after a database round-trip.
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    digest = hashlib.sha256(_payload(timestamp, actor_id, document_id, action, detail, previous_hash).encode()).hexdigest()
    entry = AuditLog(
        timestamp=timestamp, actor_id=actor_id, document_id=document_id,
        action=action, detail=detail, previous_hash=previous_hash, entry_hash=digest
    )
    db.session.add(entry)
    db.session.commit()
    return entry

def verify_audit_chain():
    expected_previous = GENESIS
    entries = db.session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    for entry in entries:
        if entry.previous_hash != expected_previous:
            return False
        calculated = hashlib.sha256(
            _payload(entry.timestamp, entry.actor_id, entry.document_id, entry.action,
                     entry.detail, entry.previous_hash).encode()
        ).hexdigest()
        if calculated != entry.entry_hash:
            return False
        expected_previous = entry.entry_hash
    return True
