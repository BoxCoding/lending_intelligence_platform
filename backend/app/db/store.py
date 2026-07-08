"""Persistence layer.

Uses Google Firestore when credentials are configured; otherwise a
thread-safe local JSON store with the same interface, so the whole
platform runs offline. Collections mirror the logical schema:
customers, features, predictions, lead_scores, recommendations, audit.

Firestore is accessed over its plain REST API (google-auth + requests)
rather than the official google-cloud-firestore SDK. The SDK's gRPC
transport pulls in ~40MB of grpc/protobuf, which is the difference
between fitting under a serverless function's deployment-size limit
(e.g. Vercel) or not. See docs/DEPLOYMENT.md.
"""

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from app.core.config import get_settings
from app.core.logging import logger

FIRESTORE_SCOPES = ["https://www.googleapis.com/auth/datastore"]


class BaseStore:
    def put(self, collection: str, doc_id: str, data: dict) -> None: ...
    def get(self, collection: str, doc_id: str) -> dict | None: ...
    def list(self, collection: str) -> list[dict]: ...
    def audit(self, action: str, detail: dict) -> None:
        self.put(
            "audit",
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f"),
            {"action": action, "detail": detail, "at": datetime.now(UTC).isoformat()},
        )


def _encode_value(value):
    """Python value -> Firestore REST typed value."""
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):  # must precede int: bool is an int subclass
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {k: _encode_value(v) for k, v in value.items()}}}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [_encode_value(v) for v in value]}}
    return {"stringValue": str(value)}  # fallback: never fail a write on an odd type


def _decode_value(value: dict):
    """Firestore REST typed value -> Python value."""
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return value["doubleValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "timestampValue" in value:
        return value["timestampValue"]
    if "mapValue" in value:
        return _decode_fields(value["mapValue"].get("fields", {}))
    if "arrayValue" in value:
        return [_decode_value(v) for v in value["arrayValue"].get("values", [])]
    return None


def _decode_fields(fields: dict) -> dict:
    return {k: _decode_value(v) for k, v in fields.items()}


class FirestoreStore(BaseStore):
    """Firestore over REST, authenticated with a service-account JWT."""

    def __init__(
        self,
        project_id: str,
        database: str = "(default)",
        inline_json: str = "",
        creds_path: str = "",
    ):
        import requests
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        info = json.loads(inline_json) if inline_json else json.loads(Path(creds_path).read_text())
        self._credentials = service_account.Credentials.from_service_account_info(
            info, scopes=FIRESTORE_SCOPES
        )
        self._auth_request = Request()
        self._session = requests.Session()
        self._project = info.get("project_id") or project_id
        self._database = database
        self._base_url = (
            f"https://firestore.googleapis.com/v1/projects/{self._project}"
            f"/databases/{self._database}/documents"
        )
        logger.info(
            "Firestore (REST) store initialised (project=%s, database=%s)",
            self._project,
            database,
        )

    def _headers(self) -> dict:
        if not self._credentials.valid:
            self._credentials.refresh(self._auth_request)
        return {"Authorization": f"Bearer {self._credentials.token}"}

    def _doc_url(self, collection: str, doc_id: str) -> str:
        return f"{self._base_url}/{quote(collection, safe='')}/{quote(doc_id, safe='')}"

    def put(self, collection: str, doc_id: str, data: dict) -> None:
        body = {"fields": {k: _encode_value(v) for k, v in data.items()}}
        resp = self._session.patch(
            self._doc_url(collection, doc_id), headers=self._headers(), json=body
        )
        resp.raise_for_status()

    def get(self, collection: str, doc_id: str) -> dict | None:
        resp = self._session.get(self._doc_url(collection, doc_id), headers=self._headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _decode_fields(resp.json().get("fields", {}))

    def list(self, collection: str) -> list[dict]:
        out: list[dict] = []
        params = {"pageSize": 300}
        url = f"{self._base_url}/{quote(collection, safe='')}"
        while True:
            resp = self._session.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            body = resp.json()
            out.extend(_decode_fields(d.get("fields", {})) for d in body.get("documents", []))
            token = body.get("nextPageToken")
            if not token:
                break
            params["pageToken"] = token
        return out


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
    inline = settings.firebase_credentials_json or os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    creds = settings.google_application_credentials or os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )
    if creds and not Path(creds).is_absolute():
        creds = str(Path(__file__).resolve().parents[2] / creds)
    if inline or (creds and Path(creds).exists()):
        try:
            return FirestoreStore(
                settings.firestore_project_id,
                database=settings.firestore_database,
                inline_json=inline,
                creds_path=creds,
            )
        except Exception as exc:
            logger.warning("Firestore unavailable (%s) — using local store", exc)
    return LocalJSONStore(settings.local_store_path)


store: BaseStore = _create_store()
