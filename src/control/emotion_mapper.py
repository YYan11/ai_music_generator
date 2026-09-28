from typing import Dict, Any

EMOTION_ON_MUSIC = {
    "happy": {
        "tempo_range": [110, 140],
        "velocity_range": [80, 110],
        "density_level": "medium_high",
        "preferred_instruments": ["piano", "guitar", "drums"],
        "control_token": "EMOTION_HAPPY",
    },
    "sad": {
        "tempo_range": [60, 90],
        "velocity_range": [40, 75],
        "density_level": "low",
        "preferred_instruments": ["piano", "strings", "violin"],
        "control_token": "EMOTION_SAD",
    },
    "relaxed": {
        "tempo_range": [70, 100],
        "velocity_range": [45, 80],
        "density_level": "low_medium",
        "preferred_instruments": ["piano", "strings", "pad", "flute"],
        "control_token": "EMOTION_RELAXED",
    },
    "energetic": {
        "tempo_range": [130, 170],
        "velocity_range": [90, 120],
        "density_level": "high",
        "preferred_instruments": ["drums", "bass", "synth", "electric_guitar"],
        "control_token": "EMOTION_ENERGETIC",
    },
    "angry": {
        "tempo_range": [120, 160],
        "velocity_range": [95, 127],
        "density_level": "high",
        "preferred_instruments": ["drums", "bass", "electric_guitar", "brass"],
        "control_token": "EMOTION_ANGRY",
    },

    "melancholic": {
        "tempo_range": [55, 85],
        "velocity_range": [35, 70],
        "density_level": "low",
        "preferred_instruments": ["piano", "strings", "cello"],
        "control_token": "EMOTION_MELANCHOLIC",
    },
    "romantic": {
        "tempo_range": [75, 105],
        "velocity_range": [50, 85],
        "density_level": "low_medium",
        "preferred_instruments": ["piano", "strings", "guitar", "flute"],
        "control_token": "EMOTION_ROMANTIC",
    },
    "anxious": {
        "tempo_range": [100, 135],
        "velocity_range": [65, 100],
        "density_level": "medium_high",
        "preferred_instruments": ["strings", "synth", "piano", "pad"],
        "control_token": "EMOTION_ANXIOUS",
    },
    "hopeful": {
        "tempo_range": [95, 125],
        "velocity_range": [65, 100],
        "density_level": "medium",
        "preferred_instruments": ["piano", "guitar", "strings", "flute"],
        "control_token": "EMOTION_HOPEFUL",
    },
    "lonely": {
        "tempo_range": [55, 85],
        "velocity_range": [35, 70],
        "density_level": "low",
        "preferred_instruments": ["piano", "cello", "strings", "pad"],
        "control_token": "EMOTION_LONELY",
    },
    
    "neutral": {
        "tempo_range": [85, 110],
        "velocity_range": [60, 90],
        "density_level": "medium",
        "preferred_instruments": ["piano", "strings"],
        "control_token": "EMOTION_NEUTRAL",
    },
}

def map_emotion_to_music(emotion_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert detected emotion data into music generation conditions.
    """
    emotion = emotion_data.get("emotion", "neutral")

    music_profile = EMOTION_ON_MUSIC.get(emotion, EMOTION_ON_MUSIC["neutral"])

    return {
        "emotion": emotion,
        "valence": emotion_data.get("valence", 0.5),
        "arousal": emotion_data.get("arousal", 0.5),
        "tempo_range": music_profile["tempo_range"],
        "velocity_range": music_profile["velocity_range"],
        "density_level": music_profile["density_level"],
        "preferred_instruments": music_profile["preferred_instruments"],
        "control_token": music_profile["control_token"],
    }


if __name__ == "__main__":
    sample_emotion = {
        "emotion": "happy",
        "valence": 0.9,
        "arousal": 0.8,
        "matched_emotions": ["happy", "energetic"],
    }

    result = map_emotion_to_music(sample_emotion)
    print(result)
