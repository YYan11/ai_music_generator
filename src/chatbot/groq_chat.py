import os

from src.chatbot.llama_chat import (
    SYSTEM_PROMPT,
    _detect_chat_mode,
    _ensure_list,
    _normalize_history,
)
from src.control.emotion_controller import process_emotion_text


DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def chat_with_groq(payload: dict) -> dict[str, object]:
    """Chat using a Groq-hosted LLaMA model for online deployment."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    user_message = str(payload.get("message", "")).strip()
    if not user_message:
        raise ValueError("Message is required.")

    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("The groq package is not installed.") from exc

    history = _normalize_history(payload.get("messages", []))
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
        user_context_parts.extend(
            [
                f"Auto-detected emotion: {emotion_pipeline['emotion_result'].get('emotion', 'neutral')}",
                f"Emotion valence: {emotion_pipeline['emotion_result'].get('valence', 0.5)}",
                f"Emotion arousal: {emotion_pipeline['emotion_result'].get('arousal', 0.5)}",
                f"Suggested tempo range: {music_context.get('tempo_range', [85, 110])}",
                f"Suggested velocity range: {music_context.get('velocity_range', [60, 90])}",
                f"Suggested density level: {music_context.get('density_level', 'medium')}",
                f"Emotion control token: {music_context.get('control_token', 'EMOTION_NEUTRAL')}",
                "Mode: music assistant",
            ]
        )
        preferred_instruments = music_context.get("preferred_instruments", [])
        if preferred_instruments:
            user_context_parts.append(
                f"Suggested instruments from emotion: {', '.join(preferred_instruments)}"
            )
    else:
        user_context_parts.append("Mode: general chat")
        if (
            conversation_state.get("emotion")
            or conversation_state.get("style")
            or conversation_state.get("instruments")
        ):
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

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.85,
        top_p=0.92,
    )
    reply_text = (completion.choices[0].message.content or "").strip()
    if not reply_text:
        raise ValueError("Groq returned an empty chat response.")

    return {
        "reply": reply_text,
        "model": f"groq:{DEFAULT_MODEL}",
        "chat_mode": chat_mode,
        "emotion_result": emotion_pipeline["emotion_result"],
        "music_context": music_context,
    }
