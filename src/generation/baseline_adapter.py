from datetime import datetime
import math
from pathlib import Path
import random
from typing import Any
import wave

from src.control.gm_instruments import (
    infer_arrangement_from_prompt,
    get_drum_note,
    get_instrument_program,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TICKS_PER_BEAT = 480
BEATS_PER_BAR = 4
BAR_TICKS = TICKS_PER_BEAT * BEATS_PER_BAR

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11, 12],
    "minor": [0, 2, 3, 5, 7, 8, 10, 12],
}

EMOTION_SCALE = {
    "happy": "major",
    "relaxed": "major",
    "energetic": "major",
    "sad": "minor",
    "angry": "minor",
    "melancholic": "minor",
    "romantic": "major",
    "anxious": "minor",
    "hopeful": "major",
    "lonely": "minor",
    "neutral": "major",
}

INSTRUMENT_ALIASES = {
    "piano": "acoustic_grand_piano",
    "guitar": "acoustic_guitar_steel",
    "electric_guitar": "electric_guitar_clean",
    "bass": "electric_bass_finger",
    "strings": "string_ensemble_1",
    "string": "string_ensemble_1",
    "pad": "pad_warm",
    "synth": "lead_sawtooth",
    "flute": "flute",
    "violin": "violin",
    "cello": "cello",
    "brass": "brass_section",
}


def generate_with_baseline(
    request_data: dict[str, Any],
    conditions: dict[str, Any],
) -> dict[str, Any]:
    """Generate a lightweight arranged MIDI file from the app conditions."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    midi_path = OUTPUT_DIR / f"baseline_music_{timestamp}.mid"
    audio_path = OUTPUT_DIR / f"baseline_music_{timestamp}.wav"

    emotion = str(conditions.get("final_emotion") or "neutral").lower()
    prompt = str(request_data.get("prompt") or request_data.get("message") or "")
    arrangement = infer_arrangement_from_prompt(prompt, emotion)
    instruments = _choose_instruments(conditions, arrangement)
    instrument_mode = str(conditions.get("instrument_mode") or "arranged")
    requested_names = [str(item).strip().lower() for item in conditions.get("instruments", []) if str(item).strip()]
    requested_drums = any(name in {"drum", "drums", "percussion"} for name in requested_names)
    add_drums = requested_drums or (
        instrument_mode == "arranged"
        and (arrangement.get("add_drums") == "yes" or emotion in {"happy", "energetic", "angry"})
    )
    bpm = _choose_bpm(conditions)
    scale_name = EMOTION_SCALE.get(emotion, "major")
    scale = SCALES[scale_name]
    root = _choose_root(emotion)
    bars = _choose_bar_count(conditions)

    tracks = [_tempo_track(bpm)]
    if instrument_mode == "single":
        tracks.append(_build_lead_track(instruments["lead"], scale, root, bars, emotion))
    elif instrument_mode == "custom":
        requested = [
            _normalize_instrument(str(item).strip().lower())
            for item in conditions.get("instruments", [])
            if str(item).strip()
        ]
        builders = [
            lambda name: _build_lead_track(name, scale, root, bars, emotion),
            lambda name: _build_harmony_track(name, scale, root, bars),
            lambda name: _build_bass_track(name, scale, root, bars),
            lambda name: _build_pad_track(name, scale, root, bars),
        ]
        for index, name in enumerate(requested[:4]):
            tracks.append(builders[index](name))
    else:
        tracks.extend([
            _build_lead_track(instruments["lead"], scale, root, bars, emotion),
            _build_bass_track(instruments["bass"], scale, root, bars),
            _build_harmony_track(instruments["harmony"], scale, root, bars),
            _build_pad_track(instruments["pad"], scale, root, bars),
        ])

    if add_drums:
        tracks.append(_build_drum_track(bars, emotion))

    _write_midi_file(midi_path, tracks)
    audio_generated = _render_midi_preview(midi_path, audio_path)
    requested_output_instruments = [
        _normalize_instrument(str(item).strip().lower())
        for item in conditions.get("instruments", [])
        if str(item).strip() and str(item).strip().lower() not in {"drum", "drums", "percussion"}
    ]
    output_instruments = (
        requested_output_instruments
        if instrument_mode in {"single", "custom"} and requested_output_instruments
        else _unique_instruments(instruments)
    )
    output_seconds = round((bars * BEATS_PER_BAR * 60) / max(1, bpm), 2)
    output_ticks = bars * BAR_TICKS

    return {
        "model_name": "baseline",
        "bars": bars,
        "emotion": emotion,
        "style": conditions.get("style", []),
        "instruments": output_instruments,
        "arrangement": {
            **instruments,
            "instrument_mode": instrument_mode,
            "add_drums": "yes" if add_drums else "no",
        },
        "token_count": output_ticks,
        "selection_metrics": {
            "bars": bars,
            "bpm": bpm,
            "output_seconds": output_seconds,
        },
        "midi_file": midi_path.name,
        "midi_path": str(midi_path),
        "audio_file": audio_path.name if audio_generated else None,
        "audio_path": str(audio_path) if audio_generated else None,
        "created_at": timestamp,
        "baseline_details": {
            "bpm": bpm,
            "scale": scale_name,
            "arrangement": instruments,
        },
    }


def _render_midi_preview(path: Path, output_path: Path, sample_rate: int = 22050) -> bool:
    """Render a lightweight WAV preview without requiring FluidSynth or MuseScore."""
    try:
        import mido

        tempo = 500000
        seconds = 0.0
        active: dict[tuple[int, int], tuple[float, int]] = {}
        notes: list[tuple[float, float, int, int]] = []
        for message in mido.merge_tracks(mido.MidiFile(path).tracks):
            seconds += mido.tick2second(message.time, TICKS_PER_BEAT, tempo)
            if message.type == "set_tempo":
                tempo = message.tempo
            elif message.type == "note_on" and message.velocity > 0:
                active[(getattr(message, "channel", 0), message.note)] = (seconds, message.velocity)
            elif message.type in {"note_off", "note_on"}:
                key = (getattr(message, "channel", 0), message.note)
                started = active.pop(key, None)
                if started:
                    notes.append((started[0], max(seconds, started[0] + 0.04), message.note, started[1]))

        duration = min(max(seconds + 0.25, 0.5), 90.0)
        samples = int(duration * sample_rate)
        audio = [0.0] * samples
        for start, end, note, velocity in notes:
            first = max(0, int(start * sample_rate))
            last = min(samples, int(end * sample_rate))
            frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))
            amplitude = min(0.24, max(0.04, velocity / 127.0 * 0.22))
            length = max(1, last - first)
            for index in range(first, last):
                position = index - first
                envelope = min(1.0, position / max(1, int(sample_rate * 0.02)))
                envelope *= min(1.0, (length - position) / max(1, int(sample_rate * 0.08)))
                audio[index] += amplitude * envelope * math.sin(2.0 * math.pi * frequency * index / sample_rate)

        peak = max((abs(value) for value in audio), default=0.0)
        scale = 0.9 / peak if peak > 0.9 else 1.0
        pcm = bytearray()
        for value in audio:
            pcm.extend(int(max(-1.0, min(1.0, value * scale)) * 32767).to_bytes(2, "little", signed=True))
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(pcm))
        return output_path.exists() and output_path.stat().st_size > 44
    except Exception:
        return False


def _choose_instruments(
    conditions: dict[str, Any],
    arrangement: dict[str, str],
) -> dict[str, str]:
    requested = [
        _normalize_instrument(str(item).strip().lower())
        for item in conditions.get("instruments", [])
        if str(item).strip() and str(item).strip().lower() not in {"drum", "drums", "percussion"}
    ]
    chosen = arrangement.copy()

    if requested:
        chosen["lead"] = requested[0]
    if len(requested) > 1:
        chosen["harmony"] = requested[1]
    if len(requested) > 2:
        chosen["bass"] = requested[2]

    return {
        "lead": _normalize_instrument(chosen.get("lead", "acoustic_grand_piano")),
        "bass": _normalize_instrument(chosen.get("bass", "acoustic_bass")),
        "harmony": _normalize_instrument(chosen.get("harmony", "string_ensemble_1")),
        "pad": _normalize_instrument(chosen.get("pad", "pad_warm")),
    }


def _normalize_instrument(instrument: str) -> str:
    return INSTRUMENT_ALIASES.get(instrument, instrument)


def _choose_bpm(conditions: dict[str, Any]) -> int:
    tempo_range = conditions.get("tempo_range", [85, 110])
    if not isinstance(tempo_range, list) or len(tempo_range) < 2:
        return 100
    return int((int(tempo_range[0]) + int(tempo_range[1])) / 2)


def _choose_bar_count(conditions: dict[str, Any]) -> int:
    requested_bars = conditions.get("requested_bars")
    if requested_bars is not None:
        return max(4, min(64, int(requested_bars)))

    requested_seconds = conditions.get("requested_seconds")
    if requested_seconds is not None:
        bpm = _choose_bpm(conditions)
        return max(
            4,
            min(64, round(float(requested_seconds) * bpm / (60 * BEATS_PER_BAR))),
        )

    # Without a length requirement, vary the song length instead of always
    # producing the previous fixed 12-bar output.
    target_seconds = random.choice([60.0, 90.0, 120.0])
    bpm = _choose_bpm(conditions)
    return max(
        4,
        min(64, round(target_seconds * bpm / (60 * BEATS_PER_BAR))),
    )

def _choose_root(emotion: str) -> int:
    return {
        "happy": 60,
        "relaxed": 57,
        "energetic": 62,
        "sad": 57,
        "angry": 50,
        "melancholic": 53,
        "romantic": 60,
        "anxious": 55,
        "hopeful": 62,
        "lonely": 53,
    }.get(emotion, 60)


def _tempo_track(bpm: int) -> list[tuple[int, bytes]]:
    tempo = int(60_000_000 / max(1, bpm))
    return [(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big"))]


def _build_lead_track(
    instrument: str,
    scale: list[int],
    root: int,
    bars: int,
    emotion: str,
) -> list[tuple[int, bytes]]:
    events = [_program_change(0, instrument)]
    phrase = [0, 2, 4, 5, 4, 2, 1, 0] if emotion in {"sad", "melancholic", "lonely", "anxious"} else [0, 2, 4, 5, 7, 5, 4, 2]
    answer = [4, 5, 4, 2, 1, 2, 0, 0] if emotion in {"sad", "melancholic", "lonely", "anxious"} else [7, 5, 4, 2, 4, 5, 2, 0]
    rhythm_templates = (
        [(0, 2), (2, 2)]
        if emotion in {"relaxed", "sad", "melancholic", "romantic", "lonely"}
        else [(0, 1), (1, 1), (2, 1), (3, 1)]
    )

    for bar in range(bars):
        phrase_shape = answer if bar % 4 == 2 else phrase
        phrase_variation = 1 if bar % 8 in {4, 5} else 0
        cadence_drop = -1 if bar % 4 == 3 else 0
        for step, beats in rhythm_templates:
            start = (bar * BAR_TICKS) + (step * TICKS_PER_BEAT)
            phrase_index = ((bar % 2) * 4 + step) % len(phrase_shape)
            degree = phrase_shape[phrase_index] + phrase_variation + cadence_drop
            octave_lift = 12 if bar % 8 == 6 and step >= 2 else 0
            note = _degree_to_note(root, scale, degree, octave_lift)
            duration = max(TICKS_PER_BEAT // 2, beats * TICKS_PER_BEAT - 60)
            velocity = 70 + (4 if bar % 4 in {1, 2} else 0) + (3 if step == 0 else 0)
            events.extend(_note(0, note, velocity, start, duration))

    return events


def _build_bass_track(instrument: str, scale: list[int], root: int, bars: int) -> list[tuple[int, bytes]]:
    events = [_program_change(1, instrument)]
    progression = _chord_progression()

    for bar in range(bars):
        degree = progression[bar % len(progression)]
        note = _degree_to_note(root - 24, scale, degree)
        fifth = _degree_to_note(root - 24, scale, degree + 4)
        bar_start = bar * BAR_TICKS
        events.extend(_note(1, note, 66, bar_start, TICKS_PER_BEAT * 2))
        events.extend(_note(1, fifth, 58, bar_start + TICKS_PER_BEAT * 2, TICKS_PER_BEAT))
        if bar % 4 in {1, 3}:
            approach = _degree_to_note(root - 24, scale, degree + 1)
            events.extend(_note(1, approach, 50, bar_start + TICKS_PER_BEAT * 3, TICKS_PER_BEAT - 80))
        else:
            events.extend(_note(1, note, 56, bar_start + TICKS_PER_BEAT * 3, TICKS_PER_BEAT - 80))

    return events


def _build_harmony_track(
    instrument: str,
    scale: list[int],
    root: int,
    bars: int,
) -> list[tuple[int, bytes]]:
    events = [_program_change(2, instrument)]
    chord_degrees = [(degree, degree + 2, degree + 4) for degree in _chord_progression()]

    for bar in range(bars):
        start = bar * BAR_TICKS
        chord = chord_degrees[bar % len(chord_degrees)]
        for degree in chord:
            note = _degree_to_note(root, scale, degree)
            events.extend(_note(2, note, 50 + (bar % 3) * 4, start, BAR_TICKS - 120))
        if bar % 4 == 3:
            for degree in chord[:2]:
                note = _degree_to_note(root, scale, degree + 7)
                events.extend(_note(2, note, 42, start + TICKS_PER_BEAT * 3, TICKS_PER_BEAT - 80))

    return events


def _build_pad_track(
    instrument: str,
    scale: list[int],
    root: int,
    bars: int,
) -> list[tuple[int, bytes]]:
    events = [_program_change(3, instrument)]

    for bar in range(0, bars, 2):
        degree = _chord_progression()[bar % 4]
        note = _degree_to_note(root, scale, degree, 12)
        harmony = _degree_to_note(root, scale, degree + 2, 12)
        start = bar * BAR_TICKS
        events.extend(_note(3, note, 34, start, BAR_TICKS * 2 - 180))
        events.extend(_note(3, harmony, 28, start, BAR_TICKS * 2 - 180))

    return events


def _build_drum_track(bars: int, emotion: str) -> list[tuple[int, bytes]]:
    events = []
    kick = get_drum_note("kick")
    snare = get_drum_note("snare_acoustic")
    hihat = get_drum_note("closed_hihat")
    crash = get_drum_note("crash")
    hihat_interval = TICKS_PER_BEAT // 2 if emotion in {"energetic", "angry"} else TICKS_PER_BEAT

    for bar in range(bars):
        bar_start = bar * BAR_TICKS
        if bar % 8 == 0:
            events.extend(_note(9, crash, 62, bar_start, 180))
        for beat in range(BEATS_PER_BAR):
            start = bar_start + (beat * TICKS_PER_BEAT)
            drum = kick if beat in {0, 2} else snare
            events.extend(_note(9, drum, 74 + (beat % 2) * 6, start, 120))
            events.extend(_note(9, hihat, 38, start, 60))
            if hihat_interval < TICKS_PER_BEAT:
                events.extend(_note(9, hihat, 46, start + hihat_interval, 60))
        if bar % 4 == 3:
            events.extend(_note(9, snare, 48, bar_start + TICKS_PER_BEAT * 3 + TICKS_PER_BEAT // 2, 90))

    return events


def _program_change(channel: int, instrument: str) -> tuple[int, bytes]:
    program = get_instrument_program(instrument, 0)
    return (0, bytes([0xC0 | channel, program]))


def _note(
    channel: int,
    note: int,
    velocity: int,
    start: int,
    duration: int,
) -> list[tuple[int, bytes]]:
    status_on = 0x90 | channel
    status_off = 0x80 | channel
    return [
        (start, bytes([status_on, note, velocity])),
        (start + duration, bytes([status_off, note, 0])),
    ]


def _write_midi_file(path: Path, tracks: list[list[tuple[int, bytes]]]) -> None:
    header = b"MThd" + (6).to_bytes(4, "big")
    header += (1).to_bytes(2, "big")
    header += len(tracks).to_bytes(2, "big")
    header += TICKS_PER_BEAT.to_bytes(2, "big")

    chunks = [_track_chunk(track) for track in tracks]
    path.write_bytes(header + b"".join(chunks))


def _track_chunk(events: list[tuple[int, bytes]]) -> bytes:
    data = bytearray()
    last_tick = 0

    for tick, payload in sorted(events, key=lambda item: item[0]):
        data.extend(_var_len(max(0, tick - last_tick)))
        data.extend(payload)
        last_tick = tick

    data.extend(_var_len(0))
    data.extend(b"\xff\x2f\x00")
    return b"MTrk" + len(data).to_bytes(4, "big") + bytes(data)


def _var_len(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    bytes_out = [buffer]

    while value:
        buffer = (value & 0x7F) | 0x80
        bytes_out.insert(0, buffer)
        value >>= 7

    return bytes(bytes_out)


def _degree_to_note(root: int, scale: list[int], degree: int, octave_shift: int = 0) -> int:
    scale_steps = scale[:-1] if len(scale) > 1 else scale
    octave, index = divmod(int(degree), len(scale_steps))
    return _clamp_note(root + scale_steps[index] + (octave * 12) + octave_shift)


def _chord_progression() -> list[int]:
    return [0, 5, 3, 4]


def _clamp_note(note: int) -> int:
    return max(0, min(127, int(note)))


def _unique_instruments(instruments: dict[str, str]) -> list[str]:
    ordered = []
    seen = set()
    for instrument in instruments.values():
        if instrument and instrument not in seen:
            seen.add(instrument)
            ordered.append(instrument)
    return ordered
