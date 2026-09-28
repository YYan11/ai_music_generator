import json
import os
import random
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.control.emotion_controller import process_emotion_text


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parents[1]
ENV_PATH = PROJECT_DIR / ".env"


def _load_env_file() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [str(value).strip()] if str(value).strip() else []


_load_env_file()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
DEFAULT_MODEL = os.getenv("LLAMA_MODEL", "llama3")

SYSTEM_PROMPT = (
    "You are Text Muse, a warm and conversational AI assistant inside a music generation app. "
    "You can chat naturally with users on general topics, respond supportively, and hold casual conversation. "
    "When the user talks about music generation, help them shape mood, style, instruments, tempo, atmosphere, and arrangement choices. "
    "Do not force every reply back to music if the user is just chatting normally. "
    "Only guide the conversation toward music generation when it is relevant to the user's message. "
    "Sound natural, supportive, and human-like, similar to a helpful AI assistant. "
    "Vary your wording so your replies do not feel repetitive or robotic. "
    "If the user gives a clear music idea, summarize it naturally and help refine it. "
    "If the music request is vague, ask one short follow-up question or offer two or three concrete suggestions. "
    "Use the conversation history when relevant so the chat feels continuous. "
    "Do not claim you already generated music unless the app says so. "
    "Keep replies concise, conversational, and useful."
)

MUSIC_INTENT_KEYWORDS = {
    "music",
    "song",
    "melody",
    "midi",
    "generate",
    "composition",
    "track",
    "instrument",
    "piano",
    "violin",
    "guitar",
    "drum",
    "drums",
    "flute",
    "oboe",
    "clarinet",
    "tempo",
    "style",
    "genre",
    "jazz",
    "rock",
    "pop",
    "lofi",
    "orchestral",
    "cinematic",
    "sad",
    "happy",
    "relaxed",
    "energetic",
    "angry",
    "melancholic",
    "romantic",
    "anxious",
    "hopeful",
    "lonely",
}


def _normalize_history(messages: list[dict]) -> list[dict]:
    normalized = []

    for message in messages:
        role = message.get("role", "").strip().lower()
        content = str(message.get("content", "")).strip()

        if role not in {"user", "assistant"} or not content:
            continue

        normalized.append({"role": role, "content": content})

    return normalized[-12:]


def _detect_chat_mode(user_message: str, conversation_state: dict[str, object]) -> str:
    normalized = user_message.strip().lower()
    if not normalized:
        return "general_chat"

    if any(keyword in normalized for keyword in MUSIC_INTENT_KEYWORDS):
        return "music_assistant"

    if conversation_state.get("emotion") or conversation_state.get("style") or conversation_state.get("instruments"):
        if any(keyword in normalized for keyword in {"more", "change", "add", "remove", "make", "use", "without", "with"}):
            return "music_assistant"

    return "general_chat"


def _build_fallback_reply(
    user_message: str,
    emotion_pipeline: dict[str, object],
    selected_emotions: list[str],
) -> str:
    emotion_value = emotion_pipeline.get("emotion_result")
    music_value = emotion_pipeline.get("music_result")
    emotion_result = emotion_value if isinstance(emotion_value, dict) else {}
    music_context = music_value if isinstance(music_value, dict) else {}

    mood = selected_emotions[0] if selected_emotions else str(
        emotion_result.get("emotion", "neutral")
    )
    tempo_value = music_context.get("tempo_range", [85, 110])
    tempo_range = tempo_value if isinstance(tempo_value, list) and len(tempo_value) >= 2 else [85, 110]
    density = str(music_context.get("density_level", "medium"))
    instrument_value = music_context.get(
        "preferred_instruments", ["piano", "strings"]
    )
    instruments = (
        [str(instrument) for instrument in instrument_value]
        if isinstance(instrument_value, list)
        else ["piano", "strings"]
    )
    instrument_text = ", ".join(instruments[:3])
    clean_message = user_message.lower()

    mentioned_instruments = [
        instrument
        for instrument in [
            "piano",
            "violin",
            "cello",
            "oboe",
            "clarinet",
            "flute",
            "guitar",
            "drums",
            "bass",
            "strings",
            "synth",
        ]
        if instrument in clean_message
    ]
    instrument_focus = ", ".join(mentioned_instruments[:3]) if mentioned_instruments else instrument_text

    has_style = any(
        word in clean_message
        for word in [
            "jazz",
            "rock",
            "pop",
            "lofi",
            "cinematic",
            "orchestral",
            "ambient",
            "classical",
        ]
    )
    has_emotion = mood != "neutral"
    has_specific_direction = has_emotion or has_style or bool(mentioned_instruments)

    if has_specific_direction:
        templates = [
            (
                f"That gives me a clearer direction. It feels {mood}, so I would shape it around "
                f"{tempo_range[0]}-{tempo_range[1]} BPM with a {density.replace('_', ' ')} texture, "
                f"using {instrument_focus}. If you want, I can help refine the atmosphere even more before you generate it."
            ),
            (
                f"I can work with that. Right now the idea leans {mood}, and a good setup would be "
                f"{instrument_focus} with a tempo around {tempo_range[0]}-{tempo_range[1]} BPM. "
                f"That should give you a {density.replace('_', ' ')} arrangement with a more natural musical direction."
            ),
            (
                f"Nice concept. Based on what you described, I would keep the mood {mood}, use "
                f"{instrument_focus}, and stay near {tempo_range[0]}-{tempo_range[1]} BPM. "
                f"You can generate now, or tell me whether you want it softer, darker, brighter, or more dramatic."
            ),
        ]
        return random.choice(templates)

    follow_ups = [
        "I can help shape that. Do you want it to feel calm, sad, dramatic, or energetic?",
        "We can build this together. What mood or genre do you want the music to have?",
        "Tell me a little more about the feeling you want. For example, should it sound soft, emotional, cinematic, or upbeat?",
    ]
    suggestion_templates = [
        (
            "I can help with that. A useful next step is to tell me the mood, a style, and one or two instruments. "
            "For example: 'sad cinematic piano and violin' or 'relaxed jazz with flute and soft drums.'"
        ),
        (
            "We can refine it step by step. Try giving me an emotion, a genre, and a lead instrument so I can shape a better music idea."
        ),
    ]
    return random.choice(follow_ups + suggestion_templates)


def chat_with_llama(payload: dict) -> dict[str, object]:
    history = _normalize_history(payload.get("messages", []))
    user_message = str(payload.get("message", "")).strip()

    if not user_message:
        raise ValueError("Message is required.")

    prompt_summary = str(payload.get("prompt_summary", "")).strip()
    emotion = _ensure_list(payload.get("emotion", []))
    conversation_state = payload.get("conversation_state", {})
    if not isinstance(conversation_state, dict):
        conversation_state = {}
    chat_mode = _detect_chat_mode(user_message, conversation_state)
    emotion_pipeline = process_emotion_text(user_message)
    auto_emotion = emotion_pipeline["emotion_result"].get("emotion", "neutral")
    music_context = emotion_pipeline["music_result"]

    if not emotion and auto_emotion and auto_emotion != "neutral":
        emotion = [auto_emotion]

    user_context_parts = []

    if chat_mode == "music_assistant":
        if prompt_summary:
            user_context_parts.append(f"Selected prompt summary: {prompt_summary}")

        if emotion:
            user_context_parts.append(f"Selected emotions: {', '.join(emotion)}")

        if conversation_state.get("emotion"):
            user_context_parts.append(
                f"Conversation emotion memory: {conversation_state.get('emotion')}"
            )
        if conversation_state.get("style"):
            user_context_parts.append(
                f"Conversation style memory: {conversation_state.get('style')}"
            )
        if conversation_state.get("instruments"):
            user_context_parts.append(
                "Conversation instrument memory: "
                + ", ".join(str(item) for item in conversation_state.get("instruments", []))
            )
        if conversation_state.get("drums"):
            user_context_parts.append(
                f"Conversation drum preference: {conversation_state.get('drums')}"
            )
        if conversation_state.get("atmosphere"):
            user_context_parts.append(
                "Conversation atmosphere memory: "
                + ", ".join(str(item) for item in conversation_state.get("atmosphere", []))
            )

        user_context_parts.append(
            f"Auto-detected emotion: {emotion_pipeline['emotion_result'].get('emotion', 'neutral')}"
        )
        user_context_parts.append(
            f"Emotion valence: {emotion_pipeline['emotion_result'].get('valence', 0.5)}"
        )
        user_context_parts.append(
            f"Emotion arousal: {emotion_pipeline['emotion_result'].get('arousal', 0.5)}"
        )
        user_context_parts.append(
            f"Suggested tempo range: {music_context.get('tempo_range', [85, 110])}"
        )
        user_context_parts.append(
            f"Suggested velocity range: {music_context.get('velocity_range', [60, 90])}"
        )
        user_context_parts.append(
            f"Suggested density level: {music_context.get('density_level', 'medium')}"
        )

        preferred_instruments = music_context.get("preferred_instruments", [])
        if preferred_instruments:
            user_context_parts.append(
                f"Suggested instruments from emotion: {', '.join(preferred_instruments)}"
            )

        user_context_parts.append(
            f"Emotion control token: {music_context.get('control_token', 'EMOTION_NEUTRAL')}"
        )

        user_context_parts.append("Mode: music assistant")
    else:
        user_context_parts.append("Mode: general chat")
        if conversation_state.get("emotion") or conversation_state.get("style") or conversation_state.get("instruments"):
            user_context_parts.append(
                "Keep any existing music preferences in memory, but do not force this reply into music advice unless the user asks for it."
            )

    contextualized_message = user_message
    if user_context_parts:
        contextualized_message = (
            f"{user_message}\n\nApp context:\n" + "\n".join(user_context_parts)
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": contextualized_message})

    request_body = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.85,
            "top_p": 0.92,
        },
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_payload = json.loads(error_body)
            message = error_payload.get("error", error_body)
        except json.JSONDecodeError:
            message = error_body or str(exc)
        reply_text = _build_fallback_reply(user_message, emotion_pipeline, emotion)
        return {
            "reply": reply_text,
            "model": "fallback-assistant",
            "emotion_result": emotion_pipeline["emotion_result"],
            "music_context": music_context,
            "warning": f"Ollama API error: {message}",
        }
    except URLError as exc:
        reply_text = _build_fallback_reply(user_message, emotion_pipeline, emotion)
        return {
            "reply": reply_text,
            "model": "fallback-assistant",
            "emotion_result": emotion_pipeline["emotion_result"],
            "music_context": music_context,
            "warning": (
                "Could not reach Ollama. Start Ollama and make sure it is running on "
                f"{OLLAMA_URL}."
            ),
        }

    reply_text = response_data.get("message", {}).get("content", "").strip()
    if not reply_text:
        raise ValueError("Ollama returned an empty chat response.")

    return {
        "reply": reply_text,
        "model": response_data.get("model", DEFAULT_MODEL),
        "chat_mode": chat_mode,
        "emotion_result": emotion_pipeline["emotion_result"],
        "music_context": music_context,
    }
