"""Persistence layer.

Uses Google Firestore when credentials are configured; otherwise a
thread-safe local JSON store with the same interface, so the whole
platform runs offline. Collections mirror the logical schema:
customers, features, predictions, lead_scores, recommendations, audit.
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import logger


class BaseStore:
    def put(self, collection: str, doc_id: str, data: dict) -> None: ...
    def get(self, collection: str, doc_id: str) -> dict | None: ...
    def list(self, collection: str) -> list[dict]: ...
    def audit(self, action: str, detail: dict) -> None:
        self.put(
            "audit",
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"),
            {"action": action, "detail": detail, "at": datetime.now(timezone.utc).isoformat()},
        )


class FirestoreStore(BaseStore):
    def __init__(self, project_id: str):
        from google.cloud import firestore

        self._db = firestore.Client(project=project_id or None)
        logger.info("Firestore store initialised (project=%s)", project_id or "default")

    def put(self, collection: str, doc_id: str, data: dict) -> None:
        self._db.collection(collection).document(doc_id).set(data)

    def get(self, collection: str, doc_id: str) -> dict | None:
        snap = self._db.collection(collection).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def list(self, collection: str) -> list[dict]:
        return [d.to_dict() for d in self._db.collection(collection).stream()]


class LocalJSONStore(BaseStore):
    """File-backed store: one JSON file per collection. Good enough for demos."""

    def __init__(self, root: str):
        base = Path(__file__).resolve().parents[2]  # backend/
        self._root = Path(root) if Path(root).is_absolute() else base / root
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        logger.info("Local JSON store at %s", self._root.resolve())

    def _load(self, collection: str) -> dict:
        if collection not in self._cache:
            path = self._root / f"{collection}.json"
            self._cache[collection] = json.loads(path.read_text()) if path.exists() else {}
        return self._cache[collection]

    def _flush(self, collection: str) -> None:
        path = self._root / f"{collection}.json"
        path.write_text(json.dumps(self._cache[collection], indent=1, default=str))

    def put(self, collection: str, doc_id: str, data: dict) -> None:
        with self._lock:
            self._load(collection)[doc_id] = data
            self._flush(collection)

    def get(self, collection: str, doc_id: str) -> dict | None:
        with self._lock:
            return self._load(collection).get(doc_id)

    def list(self, collection: str) -> list[dict]:
        with self._lock:
            return list(self._load(collection).values())


def _create_store() -> BaseStore:
    settings = get_settings()
    creds = settings.google_application_credentials or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds and Path(creds).exists():
        try:
            return FirestoreStore(settings.firestore_project_id)
        except Exception as exc:
            logger.warning("Firestore unavailable (%s) — using local store", exc)
    return LocalJSONStore(settings.local_store_path)


store: BaseStore = _create_store()
