import os
import sys
from http import HTTPStatus
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def load_project_env() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_project_env()

try:
    from .firebase_service import save_generation_history, verify_firebase_token
    from .music_service import generate_music_for_request
except ImportError:
    # Keep direct execution working: python backend/app.py
    from firebase_service import save_generation_history, verify_firebase_token
    from music_service import generate_music_for_request


FRONTEND_DIR = ROOT_DIR / "web" / "frontend"
OUTPUT_DIR = ROOT_DIR / "outputs"

app = Flask(__name__, static_folder=None)
CORS(app)


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/health")
def health():
    midigpt_status = "unavailable"
    midigpt_error = ""
    try:
        import midigpt  # type: ignore
        import midigpt._core  # type: ignore
        midigpt_status = "available"
    except Exception as exc:
        midigpt_error = f"{type(exc).__name__}: {exc}"

    return jsonify({
        "status": "ok",
        "python": sys.executable,
        "midigpt": midigpt_status,
        "midigpt_error": midigpt_error,
    })


@app.get("/api/library")
def library():
    items = []
    for path in sorted(OUTPUT_DIR.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.suffix.lower() not in {".mid", ".midi", ".wav"}:
            continue

        if path.suffix.lower() == ".wav":
            continue

        audio_file = path.with_suffix(".wav")
        item = {
            "midi_file": path.name,
            "download_url": f"/outputs/{path.name}",
            "created_at": path.stem.replace("baseline_music_", "").replace("midigpt_music_", ""),
            "emotion": "neutral",
        }
        if audio_file.exists():
            item["audio_file"] = audio_file.name
            item["audio_url"] = f"/outputs/{audio_file.name}"
        items.append(item)

    return jsonify({"items": items})


@app.post("/api/generate")
def generate():
    user = verify_firebase_token(request.headers.get("Authorization", ""))
    if not user:
        return jsonify({"error": "Please login before generating music."}), 401

    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    try:
        result = generate_music_for_request(
            prompt=prompt,
            emotion=payload.get("emotion", ""),
            instruments=payload.get("instruments", []),
            payload=payload,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        return jsonify({"error": f"Music generation failed: {exc}"}), HTTPStatus.INTERNAL_SERVER_ERROR

    save_generation_history(user_id=user["uid"], payload=payload, result=result)
    return jsonify(result)


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required."}), HTTPStatus.BAD_REQUEST

    try:
        provider = os.getenv("CHAT_PROVIDER", "groq").strip().lower()

        if provider == "groq":
            from src.chatbot.groq_chat import chat_with_groq

            return jsonify(chat_with_groq(payload))
        if provider in {"ollama", "local", "llama"}:
            from src.chatbot.llama_chat import chat_with_llama

            return jsonify(chat_with_llama(payload))

        raise ValueError(
            "Invalid CHAT_PROVIDER. Use 'groq' for online LLaMA or 'ollama' for local LLaMA."
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        return jsonify({"error": f"Chat request failed: {exc}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@app.get("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.get("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), debug=False)
