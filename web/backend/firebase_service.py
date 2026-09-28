import json
import os
from pathlib import Path


_firebase_app = None


def _get_firebase_app():
    """Initialise Firebase Admin only when server credentials are configured."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return None

    service_account_file = (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if service_account_file:
        path = Path(service_account_file)
        if not path.exists():
            return None
        credential = credentials.Certificate(str(path))
    elif service_account_json:
        credential = credentials.Certificate(json.loads(service_account_json))
    else:
        return None

    _firebase_app = firebase_admin.initialize_app(credential)
    return _firebase_app


def verify_firebase_token(authorization_header: str) -> dict | None:
    """Verify a Firebase ID token, with an explicit local-only test switch."""
    if not authorization_header.startswith("Bearer "):
        return None

    token = authorization_header.removeprefix("Bearer ").strip()
    if not token:
        return None

    if os.environ.get("FIREBASE_LOCAL_AUTH_BYPASS", "").lower() in {"1", "true", "yes"}:
        return {"uid": "local-test-user", "auth_mode": "local-bypass"}

    app = _get_firebase_app()
    if app is None:
        return None

    try:
        from firebase_admin import auth
        return auth.verify_id_token(token, app=app)
    except Exception:
        return None


def save_generation_history(user_id: str, payload: dict, result: dict) -> None:
    """Persist a generation when Firebase Admin is configured.

    The frontend also stores the user-facing history record, so this backend
    write is best-effort and avoids breaking local MIDI generation.
    """
    app = _get_firebase_app()
    if app is None:
        return

    try:
        from firebase_admin import firestore
        firestore.client(app=app).collection("users").document(user_id).collection("generations").add({
            "prompt": payload.get("prompt", ""),
            "emotion": result.get("emotion", "neutral"),
            "midi_file": result.get("midi_file", ""),
            "audio_file": result.get("audio_file", ""),
            "midi_url": result.get("midiUrl", ""),
            "audio_url": result.get("audioUrl", ""),
            "created_at": firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        return
