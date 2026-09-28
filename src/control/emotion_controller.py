from .emotion_detection import detect_emotion
from .emotion_mapper import map_emotion_to_music


def process_emotion_text(text: str):
    emotion_result = detect_emotion(text)
    music_result = map_emotion_to_music(emotion_result)

    return {
        "emotion_result": emotion_result,
        "music_result": music_result,
    }


if __name__ == "__main__":
    test_text = "I want a calm and peaceful piano song"
    result = process_emotion_text(test_text)
    print(result)
