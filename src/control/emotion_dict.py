import re
from typing import Dict, List

EMOTION_KEYWORDS = {
    "happy": {
        "keywords": ["happy", "joy", "joyful", "excited", "cheerful", "delighted", "positive", "bright"],
        "valence": 0.90,
        "arousal": 0.75,
    },

    "sad": {
        "keywords": ["sad", "sorrow", "melancholy", "depressed", "gloomy", "negative", "dark", "heartbroken", "upset", "crying"],
        "valence": 0.15,
        "arousal": 0.25,
    },

    "relaxed": {
        "keywords": ["relaxed", "calm", "peaceful", "serene", "tranquil", "chill", "soothing", "soft", "restful", "gentle"],
        "valence": 0.70,
        "arousal": 0.20,
    },

    "angry": {
        "keywords": ["angry", "rage", "furious", "irritated", "frustrated", "aggressive", "hostile", "annoyed", "mad"],
        "valence": 0.10,
        "arousal": 0.90,
    },

    "energetic": {
        "keywords": ["energetic", "powerful", "lively", "vibrant", "dynamic", "intense", "upbeat", "strong", "workout", "hype", "active"],
        "valence": 0.85,
        "arousal": 0.95,
    },

    "melancholic": {
        "keywords": ["melancholic", "melancholy",  "gloomy", "sorrowful", "mournful", "gloomy"],
        "valence": 0.20,
        "arousal": 0.35,
    },

    "romantic": {
        "keywords": ["romantic", "love", "lovely", "sweet", "tender", "warm", "affection", "heartwarming"],
        "valence": 0.80,
        "arousal": 0.45,
    },

    "anxious": {
        "keywords": ["anxious", "nervous", "worried", "tense", "stress", "stressed", "uneasy", "restless"],
        "valence": 0.25,
        "arousal": 0.80,
    },

    "hopeful": {
        "keywords": ["hopeful", "hope", "optimistic", "uplifting", "inspiring", "motivated", "encouraging"],
        "valence": 0.75,
        "arousal": 0.60,
    },

    "lonely": {
        "keywords": ["lonely", "alone", "isolated", "empty", "homesick", "missing", "distant"],
        "valence": 0.20,
        "arousal": 0.30,
    },

}
