"""General MIDI instrument and percussion mappings for arrangement support."""

import re


GM_INSTRUMENTS = {
    "acoustic_grand_piano": 0,
    "bright_acoustic_piano": 1,
    "electric_grand_piano": 2,
    "honky_tonk_piano": 3,
    "electric_piano_1": 4,
    "electric_piano_2": 5,
    "harpsichord": 6,
    "clavinet": 7,
    "celesta": 8,

    "glockenspiel": 9,
    "music_box": 10,
    "vibraphone": 11,
    "marimba": 12,
    "xylophone": 13,
    "tubular_bells": 14,
    "dulcimer": 15,

    "drawbar_organ": 16,
    "percussive_organ": 17,
    "rock_organ": 18,
    "church_organ": 19,
    "reed_organ": 20,
    "accordion": 21,
    "harmonica": 22,
    "tango_accordion": 23,

    "acoustic_guitar_nylon": 24,
    "acoustic_guitar_steel": 25,
    "electric_guitar_jazz": 26,
    "electric_guitar_clean": 27,
    "electric_guitar_muted": 28,
    "overdriven_guitar": 29,
    "distortion_guitar": 30,
    "guitar_harmonics": 31,

    "acoustic_bass": 32,
    "electric_bass_finger": 33,
    "electric_bass_pick": 34,
    "fretless_bass": 35,
    "slap_bass_1": 36,
    "slap_bass_2": 37,
    "synth_bass_1": 38,
    "synth_bass_2": 39,

    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "tremolo_strings": 44,
    "pizzicato_strings": 45,
    "orchestral_harp": 46,
    "timpani": 47,

    "string_ensemble_1": 48,
    "string_ensemble_2": 49,
    "synth_strings_1": 50,
    "synth_strings_2": 51,
    "choir_aahs": 52,
    "voice_oohs": 53,
    "synth_voice": 54,
    "orchestra_hit": 55,

    "trumpet": 56,
    "trombone": 57,
    "tuba": 58,
    "muted_trumpet": 59,
    "french_horn": 60,
    "brass_section": 61,
    "synth_brass_1": 62,
    "synth_brass_2": 63,

    "soprano_sax": 64,
    "alto_sax": 65,
    "tenor_sax": 66,
    "baritone_sax": 67,
    "oboe": 68,
    "english_horn": 69,
    "bassoon": 70,
    "clarinet": 71,
    "piccolo": 72,
    "flute": 73,
    "recorder": 74,
    "pan_flute": 75,
    "blown_bottle": 76,
    "shakuhachi": 77,
    "whistle": 78,
    "ocarina": 79,

    "lead_square": 80,
    "lead_sawtooth": 81,
    "lead_calliope": 82,
    "lead_chiff": 83,
    "lead_charang": 84,
    "lead_voice": 85,
    "lead_fifths": 86,
    "lead_bass_lead": 87,

    "pad_new_age": 88,
    "pad_warm": 89,
    "pad_polysynth": 90,
    "pad_choir": 91,
    "pad_bowed": 92,
    "pad_metallic": 93,
    "pad_halo": 94,
    "pad_sweep": 95,

    "fx_rain": 96,
    "fx_soundtrack": 97,
    "fx_crystal": 98,
    "fx_atmosphere": 99,
    "fx_brightness": 100,
    "fx_goblins": 101,
    "fx_echoes": 102,
    "fx_sci_fi": 103,

    "sitar": 104,
    "banjo": 105,
    "shamisen": 106,
    "koto": 107,
    "kalimba": 108,
    "bagpipe": 109,
    "fiddle": 110,
    "shanai": 111,

    "tinkle_bell": 112,
    "agogo": 113,
    "steel_drums": 114,
    "woodblock": 115,
    "taiko_drum": 116,
    "melodic_tom": 117,
    "synth_drum": 118,
    "reverse_cymbal": 119,

    "guitar_fret_noise": 120,
    "breath_noise": 121,
    "seashore": 122,
    "bird_tweet": 123,
    "telephone_ring": 124,
    "helicopter": 125,
    "applause": 126,
    "gunshot": 127,
}


GM_PERCUSSION = {
    "kick_acoustic": 35,
    "kick": 36,
    "snare_acoustic": 38,
    "clap": 39,
    "snare_electric": 40,
    "closed_hihat": 42,
    "low_tom": 45,
    "open_hihat": 46,
    "mid_tom": 47,
    "crash": 49,
    "high_tom": 50,
    "ride": 51,
    "ride_bell": 53,
    "tambourine": 54,
}


ARRANGEMENT_PRESETS = {
    "neutral": {
        "lead": "acoustic_grand_piano",
        "bass": "acoustic_bass",
        "harmony": "string_ensemble_1",
        "pad": "pad_warm",
    },
    "happy": {
        "lead": "acoustic_grand_piano",
        "bass": "electric_bass_finger",
        "harmony": "string_ensemble_1",
        "pad": "pad_polysynth",
    },
    "sad": {
        "lead": "acoustic_grand_piano",
        "bass": "acoustic_bass",
        "harmony": "string_ensemble_1",
        "pad": "pad_choir",
    },
    "relaxed": {
        "lead": "electric_piano_1",
        "bass": "acoustic_bass",
        "harmony": "string_ensemble_2",
        "pad": "pad_warm",
    },
    "angry": {
        "lead": "distortion_guitar",
        "bass": "electric_bass_pick",
        "harmony": "brass_section",
        "pad": "pad_sweep",
    },
    "energetic": {
        "lead": "lead_sawtooth",
        "bass": "synth_bass_1",
        "harmony": "brass_section",
        "pad": "pad_sweep",
    },
    "melancholic": {
        "lead": "electric_piano_2",
        "bass": "fretless_bass",
        "harmony": "string_ensemble_2",
        "pad": "pad_halo",
    },
}


def get_instrument_program(name: str, default: int = 0) -> int:
    return GM_INSTRUMENTS.get(name, default)


def get_drum_note(name: str, default: int = 36) -> int:
    return GM_PERCUSSION.get(name, default)


def get_arrangement_preset(emotion: str) -> dict[str, str]:
    return ARRANGEMENT_PRESETS.get(emotion, ARRANGEMENT_PRESETS["neutral"]).copy()


PROMPT_INSTRUMENT_HINTS = {
    "xylophone": "xylophone",
    "marimba": "marimba",
    "vibraphone": "vibraphone",
    "glockenspiel": "glockenspiel",
    "bells": "tubular_bells",
    "tubular bells": "tubular_bells",

    "grand piano": "acoustic_grand_piano",
    "piano": "acoustic_grand_piano",
    "electric piano": "electric_piano_1",
    "ep": "electric_piano_1",
    "organ": "drawbar_organ",

    "guitar": "acoustic_guitar_steel",
    "acoustic guitar": "acoustic_guitar_steel",
    "nylon guitar": "acoustic_guitar_nylon",
    "electric guitar": "electric_guitar_clean",

    "bass": "electric_bass_finger",
    "double bass": "contrabass",
    "synth bass": "synth_bass_1",

    "violin": "violin",
    "viola": "viola",
    "cello": "cello",
    "contrabass": "contrabass",
    "strings": "string_ensemble_1",
    "string": "string_ensemble_1",
    "harp": "orchestral_harp",
    "timpani": "timpani",

    "pad": "pad_warm",
    "choir": "choir_aahs",
    "vocal": "choir_aahs",

    "oboe": "oboe",
    "english horn": "english_horn",
    "bassoon": "bassoon",
    "clarinet": "clarinet",
    "piccolo": "piccolo",
    "flute": "flute",
    "recorder": "recorder",
    "pan flute": "pan_flute",

    "sax": "alto_sax",
    "alto sax": "alto_sax",
    "tenor sax": "tenor_sax",
    "baritone sax": "baritone_sax",
    "soprano sax": "soprano_sax",

    "trumpet": "trumpet",
    "trombone": "trombone",
    "tuba": "tuba",
    "french horn": "french_horn",
    "horn": "french_horn",
    "brass": "brass_section",

    "lead": "lead_sawtooth",
    "synth": "lead_sawtooth",
}


def _build_prompt_instrument_hints() -> dict[str, str]:
    hints = {}

    # Add exact phrase versions for every GM instrument name automatically.
    for instrument_name in GM_INSTRUMENTS:
        phrase = instrument_name.replace("_", " ")
        hints[phrase] = instrument_name

    # Keep hand-written aliases and preferred defaults for broad user terms.
    hints.update(PROMPT_INSTRUMENT_HINTS)
    return hints


PROMPT_INSTRUMENT_HINTS = _build_prompt_instrument_hints()


BASS_INSTRUMENTS = {
    "acoustic_bass",
    "electric_bass_finger",
    "electric_bass_pick",
    "fretless_bass",
    "synth_bass_1",
    "synth_bass_2",
    "contrabass",
    "tuba",
}


HARMONY_INSTRUMENTS = {
    "violin",
    "viola",
    "cello",
    "string_ensemble_1",
    "string_ensemble_2",
    "synth_strings_1",
    "synth_strings_2",
    "choir_aahs",
    "voice_oohs",
    "pad_warm",
    "pad_polysynth",
    "pad_choir",
    "pad_halo",
    "pad_sweep",
    "brass_section",
}


LEAD_INSTRUMENT_PRIORITY = [
    "oboe",
    "clarinet",
    "flute",
    "piccolo",
    "violin",
    "viola",
    "trumpet",
    "alto_sax",
    "tenor_sax",
    "acoustic_grand_piano",
    "electric_piano_1",
    "electric_guitar_clean",
]


PROMPT_STYLE_HINTS = {
    "orchestral": {
        "lead": "violin",
        "bass": "contrabass",
        "harmony": "string_ensemble_1",
        "pad": "choir_aahs",
    },
    "cinematic": {
        "lead": "violin",
        "bass": "contrabass",
        "harmony": "string_ensemble_2",
        "pad": "pad_halo",
    },
    "lofi": {
        "lead": "electric_piano_1",
        "bass": "electric_bass_finger",
        "harmony": "pad_warm",
        "pad": "pad_halo",
    },
    "jazz": {
        "lead": "electric_piano_1",
        "bass": "acoustic_bass",
        "harmony": "alto_sax",
        "pad": "drawbar_organ",
    },
    "rock": {
        "lead": "electric_guitar_clean",
        "bass": "electric_bass_pick",
        "harmony": "overdriven_guitar",
        "pad": "rock_organ",
    },
    "pop": {
        "lead": "acoustic_grand_piano",
        "bass": "electric_bass_finger",
        "harmony": "string_ensemble_1",
        "pad": "pad_polysynth",
    },
}


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _normalize_prompt(prompt: str) -> str:
    prompt_text = (prompt or "").lower()
    prompt_text = re.sub(r"[_\-]+", " ", prompt_text)
    prompt_text = re.sub(r"\s+", " ", prompt_text)
    return prompt_text.strip()


def extract_requested_instruments_from_prompt(prompt: str) -> list[str]:
    normalized = _normalize_prompt(prompt)
    matched_instruments = []

    for phrase in sorted(PROMPT_INSTRUMENT_HINTS.keys(), key=len, reverse=True):
        instrument_name = PROMPT_INSTRUMENT_HINTS[phrase]
        if phrase in normalized:
            matched_instruments.append(instrument_name)

    return _dedupe_preserve_order(matched_instruments)


def infer_arrangement_from_prompt(prompt: str, emotion: str) -> dict[str, str]:
    arrangement = get_arrangement_preset(emotion)
    normalized = _normalize_prompt(prompt)
    arrangement["add_drums"] = "no"

    # Style preset first
    for style, style_preset in PROMPT_STYLE_HINTS.items():
        if style in normalized:
            arrangement.update(style_preset)

    matched_instruments = extract_requested_instruments_from_prompt(prompt)

    if matched_instruments:
        bass_choice = next(
            (name for name in matched_instruments if name in BASS_INSTRUMENTS),
            None,
        )

        harmony_choice = next(
            (name for name in matched_instruments if name in HARMONY_INSTRUMENTS),
            None,
        )

        lead_choice = next(
            (name for name in LEAD_INSTRUMENT_PRIORITY if name in matched_instruments),
            None,
        )

        if not lead_choice:
            lead_choice = next(
                (
                    name
                    for name in matched_instruments
                    if name not in BASS_INSTRUMENTS and name not in HARMONY_INSTRUMENTS
                ),
                matched_instruments[0],
            )

        arrangement["lead"] = lead_choice

        if bass_choice:
            arrangement["bass"] = bass_choice

        if harmony_choice:
            arrangement["harmony"] = harmony_choice

        remaining = [
            name
            for name in matched_instruments
            if name not in {
                arrangement["lead"],
                arrangement.get("bass"),
                arrangement.get("harmony"),
            }
        ]

        if not harmony_choice and remaining:
            arrangement["harmony"] = remaining[0]

        if not bass_choice:
            support_bass = next(
                (name for name in remaining if name in BASS_INSTRUMENTS),
                None,
            )
            if support_bass:
                arrangement["bass"] = support_bass

        # Optional: if user mentions many instruments, use one extra as pad support
        extra_pad = next(
            (
                name
                for name in remaining
                if name
                not in {
                    arrangement["lead"],
                    arrangement.get("bass"),
                    arrangement.get("harmony"),
                }
            ),
            None,
        )
        if extra_pad:
            arrangement["pad"] = extra_pad

    # Drum intent
    if any(word in normalized for word in ["drum", "drums", "beat", "percussion", "rhythm"]):
        arrangement["add_drums"] = "yes"

    if any(
        phrase in normalized
        for phrase in ["no drum", "no drums", "without drum", "without drums", "no percussion"]
    ):
        arrangement["add_drums"] = "no"

    return arrangement
