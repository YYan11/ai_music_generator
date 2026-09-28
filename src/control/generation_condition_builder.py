import re
from typing import Dict, Any

from .gm_instruments import extract_requested_instruments_from_prompt


def _ensure_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [str(value).strip()] if str(value).strip() else []


def _merge_instruments(user_instruments: list[str], suggested_instruments: list[str]) -> list[str]:
    merged = []
    seen = set()

    for instrument in user_instruments + suggested_instruments:
        norm = instrument.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            merged.append(instrument)

    return merged


def _has_solo_instrument_intent(text: str) -> bool:
    normalized = text.lower()
    return bool(
        re.search(
            r"\b(solo|only|just|single instrument|one instrument|单乐器|只有|只要)\b",
            normalized,
        )
    )


def _supporting_instruments_for_emotion(emotion: str) -> list[str]:
    normalized = str(emotion or "").lower()
    if normalized in {"sad", "melancholic", "relaxed", "calm", "lonely", "romantic"}:
        return ["acoustic_bass", "string_ensemble_1", "pad_warm"]
    if normalized in {"energetic", "angry", "excited", "anxious"}:
        return ["electric_bass_finger", "brass_section", "pad_sweep"]
    if normalized in {"hopeful"}:
        return ["electric_bass_finger", "string_ensemble_1", "flute"]
    return ["electric_bass_finger", "string_ensemble_1", "pad_warm"]


def extract_requested_length(text: str) -> tuple[int | None, float | None]:
    """Read a requested length in bars, seconds or minutes."""
    normalized = text.lower()

    bar_match = re.search(r"(?:\b|^)(\d+)\s*(?:bars?|measures?|小节)", normalized)
    if bar_match:
        return max(4, min(64, int(bar_match.group(1)))), None

    time_match = re.search(
        r"(?:\b|^)(\d+(?:\.\d+)?)\s*(minutes?|mins?|seconds?|secs?|分钟|分|秒)",
        normalized,
    )
    if time_match:
        value = float(time_match.group(1))
        unit = time_match.group(2)
        seconds = (
            value * 60.0
            if unit.startswith(("minute", "min")) or unit in {"分钟", "分"}
            else value
        )
        return None, max(15.0, min(300.0, seconds))

    return None, None


def build_generation_conditions(
    payload: Dict[str, Any],
    emotion_result: Dict[str, Any],
    music_context: Dict[str, Any],
) -> Dict[str, Any]:
    prompt_summary = str(payload.get("prompt_summary", "")).strip()
    user_message = str(payload.get("message", "")).strip()
    conversation_state = payload.get("conversation_state", {})
    if not isinstance(conversation_state, dict):
        conversation_state = {}

    selected_emotion = _ensure_list(payload.get("emotion", []))
    selected_style = _ensure_list(payload.get("style", []))
    selected_instruments = _ensure_list(payload.get("instruments", []))
    prompt_instruments = extract_requested_instruments_from_prompt(user_message)
    explicit_instruments = selected_instruments or prompt_instruments
    use_override = bool(payload.get("use_emotion_override", False))
    state_style = _ensure_list(conversation_state.get("style", []))
    state_instruments = _ensure_list(conversation_state.get("instruments", []))
    requested_bars, requested_seconds = extract_requested_length(
        f"{user_message} {prompt_summary}"
    )

    final_emotion = (
        selected_emotion[0]
        if use_override and selected_emotion
        else conversation_state.get("emotion", emotion_result.get("emotion", "neutral"))
    )
    final_style = selected_style or state_style

    suggested_instruments = music_context.get("preferred_instruments", [])
    if explicit_instruments:
        solo_intent = _has_solo_instrument_intent(f"{user_message} {prompt_summary}")
        if len(explicit_instruments) == 1 and not solo_intent:
            final_instruments = _merge_instruments(
                explicit_instruments,
                _supporting_instruments_for_emotion(final_emotion),
            )[:4]
            instrument_mode = "custom"
        else:
            final_instruments = _merge_instruments(explicit_instruments, [])
            instrument_mode = "single" if len(final_instruments) == 1 else "custom"
    else:
        final_instruments = _merge_instruments(state_instruments, suggested_instruments)
        instrument_mode = "arranged"

    tempo_range = music_context.get("tempo_range", [85, 110])
    velocity_range = music_context.get("velocity_range", [60, 90])
    density_level = music_context.get("density_level", "medium")
    control_token = music_context.get("control_token", "EMOTION_NEUTRAL")

    prompt_parts = []

    if final_emotion:
        prompt_parts.append(f"{final_emotion} mood")

    if final_style:
        prompt_parts.append(f"{', '.join(final_style)} style")

    if final_instruments:
        prompt_parts.append(f"using {', '.join(final_instruments)}")

    prompt_parts.append(f"tempo range {tempo_range[0]}-{tempo_range[1]} BPM")
    prompt_parts.append(f"density {density_level}")

    if prompt_summary:
        prompt_parts.append(f"summary: {prompt_summary}")
    elif user_message:
        prompt_parts.append(f"user request: {user_message}")

    output_description = "single-instrument" if instrument_mode == "single" else "custom-instrument" if instrument_mode == "custom" else "multi-instrument"
    generation_prompt = f"Generate a {output_description} symbolic MIDI piece with " + ", ".join(prompt_parts) + "."

    return {
        "final_emotion": final_emotion,
        "valence": emotion_result.get("valence", 0.5),
        "arousal": emotion_result.get("arousal", 0.5),
        "style": final_style,
        "instruments": final_instruments,
        "instrument_mode": instrument_mode,
        "tempo_range": tempo_range,
        "velocity_range": velocity_range,
        "density_level": density_level,
        "control_token": control_token,
        "generation_prompt": generation_prompt,
        "requested_bars": requested_bars,
        "requested_seconds": requested_seconds,
    }


if __name__ == "__main__":
    sample_payload = {
        "message": "I want a calm piano song with soft background feeling",
        "prompt_summary": "Soft relaxing study music",
        "emotion": [],
        "style": ["lofi"],
        "instruments": ["piano"],
    }

    sample_emotion_result = {
        "emotion": "relaxed",
        "valence": 0.7,
        "arousal": 0.2,
        "matched_emotions": ["relaxed"],
    }

    sample_music_context = {
        "emotion": "relaxed",
        "valence": 0.7,
        "arousal": 0.2,
        "tempo_range": [70, 100],
        "velocity_range": [45, 80],
        "density_level": "low_medium",
        "preferred_instruments": ["piano", "strings", "pad", "flute"],
        "control_token": "EMOTION_RELAXED",
    }

    result = build_generation_conditions(
        sample_payload,
        sample_emotion_result,
        sample_music_context,
    )

    print(result)
