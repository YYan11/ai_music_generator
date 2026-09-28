import re
from typing import Dict, List
from .emotion_dict import EMOTION_KEYWORDS


def preprocess_text(text: str) -> str:
    """Preprocess the input text for emotion detection."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def match_emotion(text: str) -> List[str]:
    """Match the input text to one or more emotions whose keywords appear in the text."""
    clean_text = preprocess_text(text)
    matched_emo = []

    for emotion, data in EMOTION_KEYWORDS.items():
        for keyword in data["keywords"]:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, clean_text):
                matched_emo.append(emotion)
                break

    return matched_emo


def get_emotion(matched_emo: List[str]) -> str:
    """Pick the main emotion label."""
    if not matched_emo:
        return "neutral"

    emo_list = [
        "anxious",
        "lonely",
        "relaxed",
        "romantic",
        "hopeful",
        "happy",
        "sad",
        "energetic",
        "melancholic",
        "angry"
    ]

    for emotion in emo_list:
        if emotion in matched_emo:
            return emotion

    return matched_emo[0]


def average_valence_arousal(matched_emo: List[str]) -> Dict[str, float]:
    """Calculate average valence and arousal for multiple matched emotions."""
    if not matched_emo:
        return {"valence": 0.5, "arousal": 0.5}

    avg_val = sum(EMOTION_KEYWORDS[e]["valence"] for e in matched_emo) / len(matched_emo)
    avg_aro = sum(EMOTION_KEYWORDS[e]["arousal"] for e in matched_emo) / len(matched_emo)

    return {
        "valence": round(avg_val, 2),
        "arousal": round(avg_aro, 2),
    }


def detect_emotion(text: str) -> Dict[str, object]:
    """Detect emotion, main emotion label, and average valence/arousal."""
    matched_emo = match_emotion(text)
    main_emotion = get_emotion(matched_emo)
    val_aro = average_valence_arousal(matched_emo)

    return {
        "emotion": main_emotion,
        "valence": val_aro["valence"],
        "arousal": val_aro["arousal"],
        "matched_emotions": matched_emo,
    }


if __name__ == "__main__":
    test_text = "I am feeling very happy and energetic today!"
    result = detect_emotion(test_text)
    print(result)
