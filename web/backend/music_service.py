import os
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]

# Prefer the installed MIDI-GPT wheel. Adding the repository's raw
# `src/python` directory first can shadow the wheel and omit its native
# `_core` extension on Windows.
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))



def _ensure_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value = str(value).strip()
    return [value] if value else []


def _output_url(filename: str | None) -> str:
    port = os.environ.get("PORT", "8000")
    return f"http://127.0.0.1:{port}/outputs/{filename}" if filename else ""


def generate_music_for_request(
    prompt: str,
    emotion: str | list[str] = "",
    instruments=None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(payload or {})
    instruments = _ensure_list(instruments)
    selected_emotions = _ensure_list(emotion)
    model_name = str(payload.get("model") or "midi-gpt").strip()

    from src.control.emotion_controller import process_emotion_text
    from src.control.generation_condition_builder import build_generation_conditions
    from src.generation.service import generate_music_from_conditions

    emotion_pipeline = process_emotion_text(prompt)
    if selected_emotions:
        emotion_pipeline["emotion_result"]["emotion"] = selected_emotions[0]

    request_data = {
        "prompt": prompt,
        "message": str(payload.get("message") or prompt).strip(),
        "emotion": selected_emotions,
        "style": _ensure_list(payload.get("style")),
        "instruments": instruments,
        "conversation_memory": payload.get("conversation_memory", ""),
        "conversation_state": payload.get("conversation_state", {}),
        "messages": payload.get("messages", []),
        "emotion_result": emotion_pipeline["emotion_result"],
        "music_context": emotion_pipeline["music_result"],
    }

    generation_conditions = build_generation_conditions(
        payload=request_data,
        emotion_result=emotion_pipeline["emotion_result"],
        music_context=emotion_pipeline["music_result"],
    )
    result = generate_music_from_conditions(
        request_data=request_data,
        conditions=generation_conditions,
        model_name=model_name,
    )

    midi_file = result.get("midi_file")
    audio_file = result.get("audio_file")
    midi_url = _output_url(midi_file)
    audio_url = _output_url(audio_file)

    return {
        "prompt": prompt,
        "model_name": result.get("model_name", model_name),
        "requested_model": result.get("requested_model", model_name),
        "fallback_reason": result.get("fallback_reason", ""),
        "emotion": result.get("emotion", emotion_pipeline["emotion_result"].get("emotion", "neutral")),
        "emotion_result": emotion_pipeline["emotion_result"],
        "music_context": emotion_pipeline["music_result"],
        "generation_conditions": generation_conditions,
        "style": result.get("style", generation_conditions.get("style", [])),
        "instruments": result.get("instruments", generation_conditions.get("instruments", [])),
        "bars": result.get("bars", generation_conditions.get("requested_bars")),
        "arrangement": result.get("arrangement", {}),
        "token_count": result.get("token_count", 0),
        "selection_metrics": result.get("selection_metrics", {}),
        "midi_file": midi_file,
        "audio_file": audio_file,
        "midiFile": midi_file,
        "audioFile": audio_file,
        "download_url": midi_url,
        "audio_url": audio_url,
        "midiUrl": midi_url,
        "audioUrl": audio_url,
        "createdAt": result.get("created_at"),
        "created_at": result.get("created_at"),
    }
