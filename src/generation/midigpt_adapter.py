import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import mido

from src.control.gm_instruments import GM_INSTRUMENTS


PROJECT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_NAME = "yellow_medium"
MIDI_GPT_CHECKPOINT_DIR = PROJECT_DIR / "checkpoints" / "midi_gpt"
_checkpoint_override = os.environ.get("MIDI_GPT_CHECKPOINT", "").strip()
LOCAL_CHECKPOINT = Path(_checkpoint_override) if _checkpoint_override else (
    MIDI_GPT_CHECKPOINT_DIR / "yellow_medium-final.safetensors"
)
SOUNDFONT_PATH = Path(
    os.environ.get(
        "MIDI_SOUNDFONT",
        str(PROJECT_DIR / "assets" / "soundfonts" / "default.sf2"),
    )
)
MUSESCORE_PATH = Path(
    os.environ.get(
        "MUSESCORE_PATH",
        r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
    )
)

INSTRUMENT_ALIASES = {
    "piano": 0,
    "guitar": 24,
    "bass": 32,
    "strings": 48,
    "string": 48,
    "violin": 40,
    "cello": 42,
    "flute": 73,
    "pad": 88,
    "synth": 80,
    "drum": 0,
    "drums": 0,
    "percussion": 0,
}
INSTRUMENT_PROGRAMS = {**GM_INSTRUMENTS, **INSTRUMENT_ALIASES}

CONTROL_LEVELS = {
    "low": {
        "max_polyphony": 2,
    },
    "medium": {
        "max_polyphony": 3,
    },
    "high": {
        "max_polyphony": 5,
    },
}

CONTROL_LEVEL_INDEX = {
    "low": 2,
    "medium": 4,
    "high": 7,
}


def build_midigpt_controls(conditions: dict[str, Any]) -> dict[str, Any]:
    """Convert emotion, style, and instruments into MIDI-GPT settings."""
    emotion = str(conditions.get("final_emotion") or "neutral").lower()
    arousal = float(conditions.get("arousal") or 0.5)
    valence = float(conditions.get("valence") or 0.5)
    density = str(conditions.get("density_level") or "medium")

    # The emotion mapper already gives a density level.
    # MIDI-GPT needs this as small number levels, so we simplify it here.
    note_density = {
        "low": "low",
        "low_medium": "low",
        "medium": "medium",
        "medium_high": "high",
        "high": "high",
    }.get(density, "medium")

    # Calm or sad music should sound lighter.
    # Energetic music should sound fuller and more active.
    if emotion in {"calm", "relaxed", "sad", "melancholic", "romantic", "lonely"} or arousal < 0.35:
        polyphony = "low"
        note_duration = "long"
    elif emotion in {"energetic", "angry", "excited", "anxious"} or arousal > 0.75:
        polyphony = "high"
        note_duration = "short"
        note_density = "high"
    else:
        polyphony = "medium"
        note_duration = "medium"

    # Valence roughly means negative to positive emotion.
    # Positive emotion can use a brighter/higher pitch range.
    pitch_range = "higher" if valence >= 0.65 else "lower" if valence <= 0.35 else "medium"

    return {
        "note_density": note_density,
        "drum_attribute_levels": {"note_density": CONTROL_LEVEL_INDEX[note_density]},
        "polyphony": polyphony,
        "note_duration": note_duration,
        "pitch_range": pitch_range,
        "attribute_levels": CONTROL_LEVELS[note_density],
        "style": conditions.get("style", []),
        "instruments": clean_instrument_list(conditions.get("instruments", [])),
        "generation_prompt": conditions.get("generation_prompt", ""),
    }


def create_midigpt_music(request_data: dict[str, Any], conditions: dict[str, Any]) -> dict[str, Any]:
    """Generate a MIDI file using the MIDI-GPT pretrained model."""
    controls = build_midigpt_controls(conditions)

    try:
        from midigpt import Bar, Score, Track
        from midigpt.inference import (
            GenerationRequest,
            InferenceConfig,
            InferenceEngine,
            TrackPrompt,
        )
    except ImportError as exc:
        raise RuntimeError(
            "MIDI-GPT import failed in the website Python environment: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    midi_path = OUTPUT_DIR / f"midigpt_music_{timestamp}.mid"
    audio_path = OUTPUT_DIR / f"midigpt_music_{timestamp}.wav"

    instruments = build_model_instrument_layout(
        controls["instruments"],
        str(conditions.get("final_emotion") or "neutral"),
    )
    requested_bars = conditions.get("requested_bars")
    requested_seconds = conditions.get("requested_seconds")
    if requested_bars is None and requested_seconds:
        bpm = choose_bpm(conditions)
        requested_bars = round(float(requested_seconds) * bpm / (60 * 4))
    if requested_bars is None:
        requested_bars = 16
    requested_bars = max(4, min(64, int(requested_bars)))
    generation_bars = min(24, requested_bars)
    # Keep a stable four-track arrangement for coherence.
    model_instruments = instruments[:4]
    tracks = [
        make_empty_track(
            Track,
            Bar,
            instrument_name=instrument,
            bars_per_track=generation_bars,
        )
        for instrument in model_instruments
    ]
    score = Score(tracks=tracks, tempo=bpm_to_midi_tempo(choose_bpm(conditions)))

    track_prompts = []
    for index, instrument in enumerate(model_instruments):
        track_prompts.append(
            TrackPrompt(
                id=index,
                bars=list(range(generation_bars)),
                autoregressive=True,
            )
        )

    if not LOCAL_CHECKPOINT.exists():
        raise FileNotFoundError(
            "MIDI-GPT checkpoint not found. Put yellow_medium-final.safetensors in "
            f"{MIDI_GPT_CHECKPOINT_DIR} or set MIDI_GPT_CHECKPOINT."
        )

    engine = InferenceEngine.from_checkpoint(str(LOCAL_CHECKPOINT))

    generation_warning = ""
    primary_config = InferenceConfig(
        model_dim=8,
        bars_per_step=1,
        tracks_per_step=1,
        seed=-1,
        temperature=choose_temperature(conditions.get("arousal")),
        top_p=0.95,
        mask_mode="attention",
        max_attempts=20,
        novelty_check=False,
        temperature_escalation=1.20,
        silence_check=False,
        polyphony_hard_limit=0,
    )
    retry_config = InferenceConfig(
        model_dim=8,
        bars_per_step=1,
        tracks_per_step=1,
        seed=-1,
        temperature=0.98,
        top_p=0.98,
        mask_mode="attention",
        max_attempts=30,
        novelty_check=False,
        temperature_escalation=1.12,
        silence_check=False,
        polyphony_hard_limit=0,
    )

    try:
        result = run_midigpt_session(engine, score, GenerationRequest, track_prompts, primary_config)
    except RuntimeError as exc:
        if not is_retryable_generation_error(exc):
            raise
        generation_warning = f"Primary MIDI-GPT sampling retried after: {exc}"
        result = run_midigpt_session(engine, score, GenerationRequest, track_prompts, retry_config)

    result.to_midi(str(midi_path))
    used_instruments = model_instruments
    if requested_bars > generation_bars:
        extend_midi_to_bars(midi_path, source_bars=generation_bars, target_bars=requested_bars)
    diversify_midi_file(midi_path, conditions)
    apply_song_structure(midi_path, requested_bars, conditions)
    enforce_midi_length(midi_path, requested_bars)
    improve_midi_file(midi_path, used_instruments, conditions)

    audio_generated = False
    audio_message = ""
    try:
        audio_generated, audio_message = render_midigpt_audio(midi_path, audio_path)
    except Exception as exc:
        audio_message = f"MIDI generated, but WAV rendering failed: {exc}"

    output_seconds = round((requested_bars * 4 * 60) / max(1, choose_bpm(conditions)), 2)
    output = {
        "model_name": "midi-gpt",
        "checkpoint_name": CHECKPOINT_NAME,
        "bars": requested_bars,
        "midigpt_generated_bars": generation_bars,
        "selection_metrics": {
            "bars": requested_bars,
            "output_seconds": output_seconds,
            "midigpt_generated_bars": generation_bars,
        },
        "emotion": conditions.get("final_emotion", "neutral"),
        "style": controls["style"],
        "instruments": used_instruments,
        "midigpt_controls": controls,
        "midi_file": midi_path.name,
        "midi_path": str(midi_path),
        "audio_render_message": audio_message,
        "created_at": timestamp,
    }
    if generation_warning:
        output["generation_warning"] = generation_warning
    if audio_generated and audio_path.exists():
        output["audio_file"] = audio_path.name
        output["audio_path"] = str(audio_path)

    return output


def render_midigpt_audio(midi_path: Path, wav_output_path: Path) -> tuple[bool, str]:
    """Render MIDI-GPT output without importing the baseline generator."""
    renderer = shutil.which("fluidsynth")
    if renderer and SOUNDFONT_PATH.exists():
        try:
            subprocess.run(
                [
                    renderer,
                    "-ni",
                    str(SOUNDFONT_PATH),
                    str(midi_path),
                    "-F",
                    str(wav_output_path),
                    "-r",
                    "44100",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True, f"Rendered WAV with FluidSynth using {SOUNDFONT_PATH.name}"
        except subprocess.CalledProcessError as exc:
            error = (exc.stderr or "").strip()
            return False, f"FluidSynth rendering failed: {error or exc}"

    musescore = MUSESCORE_PATH if MUSESCORE_PATH.exists() else None
    if musescore is None:
        for name in ("MuseScore4", "MuseScore3", "musescore4", "musescore3", "mscore"):
            command = shutil.which(name)
            if command:
                musescore = Path(command)
                break

    if musescore:
        try:
            subprocess.run(
                [str(musescore), "-o", str(wav_output_path), str(midi_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if wav_output_path.exists() and wav_output_path.stat().st_size > 0:
                return True, f"Rendered WAV with MuseScore using {musescore.name}"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            return False, f"MuseScore rendering failed: {exc}"

    return False, "MIDI saved. No separate MIDI-GPT audio renderer is available."


def clean_instrument_list(value: Any) -> list[str]:
    """Normalize requested instruments while preserving explicit drum requests."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]

    instruments = []
    seen = set()
    for item in value:
        name = str(item).strip().lower().replace("-", "_").replace(" ", "_")
        if not name:
            continue
        if name in {"drums", "percussion"}:
            name = "drum"
        if name not in seen:
            seen.add(name)
            instruments.append(name)

    return instruments


def build_model_instrument_layout(instruments: list[str], emotion: str) -> list[str]:
    """Use requested instruments as lead, then add stable support tracks."""
    cleaned = clean_instrument_list(instruments)
    if not cleaned:
        cleaned = ["acoustic_grand_piano"]

    lead = next((name for name in cleaned if name != "drum"), "acoustic_grand_piano")
    normalized_emotion = str(emotion or "").lower()
    bass = (
        "acoustic_bass"
        if normalized_emotion in {"sad", "melancholic", "relaxed", "calm", "romantic", "lonely"}
        else "electric_bass_finger"
    )
    harmony = (
        "brass_section"
        if normalized_emotion in {"angry", "energetic", "excited", "anxious"}
        else "string_ensemble_1"
    )

    layout = [lead]
    for name in cleaned:
        if name not in layout and name != "drum":
            layout.append(name)

    for name in [bass, harmony, "drum"]:
        if name not in layout:
            layout.append(name)

    return layout[:4]


def make_empty_track(
    track_class: Any,
    bar_class: Any,
    instrument_name: str,
    bars_per_track: int,
) -> Any:
    """Create an empty MIDI-GPT track for one instrument."""
    program = INSTRUMENT_PROGRAMS.get(instrument_name.lower(), 0)
    track_type = "drum" if instrument_name.lower() == "drum" else "melodic"
    bars = [bar_class() for _ in range(bars_per_track)]

    return track_class(instrument=program, track_type=track_type, bars=bars)


def run_midigpt_session(
    engine: Any,
    score: Any,
    generation_request_class: Any,
    track_prompts: list[Any],
    config: Any,
) -> Any:
    """Run one MIDI-GPT sampling pass with the provided inference config."""
    return engine.session(
        score,
        generation_request_class(
            tracks=track_prompts,
            config=config,
        ),
    ).run()


def is_retryable_generation_error(error: RuntimeError) -> bool:
    """Identify MIDI-GPT candidate rejection errors that can benefit from retry."""
    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            "max attempts",
            "no acceptable candidate",
            "0 notes",
            "silence_check",
            "novelty_check",
        )
    )


def add_support_tracks(path: Path, instruments: list[str]) -> None:
    """Create simple extra instrument tracks from the main generated melody."""
    if len(instruments) <= 1:
        return

    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    main_notes = collect_main_notes(midi)
    if not main_notes:
        return

    for track_index, instrument in enumerate(instruments[1:3], start=1):
        support_track = build_support_track(
            main_notes,
            instrument,
            channel=track_index,
            ticks_per_beat=midi.ticks_per_beat,
        )
        midi.tracks.append(support_track)

    midi.save(path)


def extend_main_track(path: Path, repeat_count: int) -> None:
    """Repeat the main melody so the output sounds more like a complete piece."""
    if repeat_count <= 1:
        return

    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    original_messages = [
        message.copy()
        for message in midi.tracks[0]
        if message.type != "end_of_track"
    ]
    if not original_messages:
        return

    new_track = mido.MidiTrack()
    pitch_changes = [0, 2, -1, 4]

    for repeat_index in range(repeat_count):
        pitch_change = pitch_changes[repeat_index % len(pitch_changes)]

        for message in original_messages:
            new_message = message.copy()
            if hasattr(new_message, "note"):
                new_message.note = max(0, min(127, new_message.note + pitch_change))
            new_track.append(new_message)

    new_track.append(mido.MetaMessage("end_of_track", time=0))
    midi.tracks[0] = new_track
    midi.save(path)


def extend_midi_to_bars(path: Path, source_bars: int, target_bars: int) -> None:
    """Repeat generated bars until the MIDI reaches the requested length."""
    if target_bars <= source_bars:
        return

    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    source_ticks = midi.ticks_per_beat * 4 * max(1, source_bars)
    target_ticks = midi.ticks_per_beat * 4 * max(1, target_bars)
    repeat_count = max(1, (target_bars + source_bars - 1) // source_bars)

    for track_index, track in enumerate(midi.tracks):
        absolute_messages = []
        current_tick = 0
        for message in track:
            current_tick += message.time
            if message.type == "end_of_track":
                continue
            absolute_messages.append((current_tick, message.copy()))

        if not absolute_messages:
            continue

        repeated_messages = []
        for repeat_index in range(repeat_count):
            offset = repeat_index * source_ticks
            pitch_shift = [0, 0, 2, 0, 0, -1, 2, 0][repeat_index % 8]
            harmony_shift = [0, 0, 0, 0, 0, -1, 1, 0][repeat_index % 8]
            velocity_shift = [0, -4, 3, -2, 2, -3, 4, -1][repeat_index % 8]

            for tick, message in absolute_messages:
                absolute_tick = tick + offset
                if absolute_tick > target_ticks:
                    continue
                new_message = message.copy()
                if repeat_index > 0 and new_message.is_meta:
                    continue
                if repeat_index > 0 and new_message.type == "program_change":
                    continue
                if hasattr(new_message, "note") and getattr(new_message, "channel", 0) != 9:
                    shift = pitch_shift if track_index == 0 else harmony_shift
                    new_message.note = max(0, min(127, new_message.note + shift))
                if new_message.type == "note_on" and getattr(new_message, "velocity", 0) > 0:
                    new_message.velocity = max(24, min(112, new_message.velocity + velocity_shift))
                repeated_messages.append((absolute_tick, new_message))

        repeated_messages.sort(key=lambda item: item[0])
        new_track = mido.MidiTrack()
        last_tick = 0
        for absolute_tick, message in repeated_messages:
            message.time = max(0, absolute_tick - last_tick)
            new_track.append(message)
            last_tick = absolute_tick
        new_track.append(mido.MetaMessage("end_of_track", time=max(0, target_ticks - last_tick)))
        midi.tracks[track_index] = new_track

    midi.save(path)


def diversify_midi_file(path: Path, conditions: dict[str, Any]) -> None:
    """Add phrase-level variation so long outputs do not sound copy-pasted."""
    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    bar_ticks = midi.ticks_per_beat * 4
    total_ticks = get_midi_length_ticks(midi)
    emotion = str(conditions.get("final_emotion") or "neutral").lower()

    for track_index, track in enumerate(midi.tracks):
        notes, non_note_events = extract_track_notes(track)
        if len(notes) < 4:
            continue

        has_drum_notes = any(note["channel"] == 9 for note in notes)
        if has_drum_notes:
            varied_notes = vary_drum_notes(notes, track_index, bar_ticks)
        else:
            varied_notes = vary_melodic_notes(notes, track_index, bar_ticks, total_ticks, emotion)

        midi.tracks[track_index] = rebuild_track(non_note_events, varied_notes, total_ticks)

    midi.save(path)


def enforce_midi_length(path: Path, target_bars: int) -> None:
    """Trim or pad every track so the saved MIDI ends at the requested bar count."""
    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    target_ticks = midi.ticks_per_beat * 4 * max(1, int(target_bars))
    for track_index, track in enumerate(midi.tracks):
        notes, non_note_events = extract_track_notes(track)
        clipped_notes = []
        for note in notes:
            if note["start"] >= target_ticks:
                continue
            clipped_note = note.copy()
            clipped_note["end"] = max(clipped_note["start"] + 1, min(target_ticks, note["end"]))
            clipped_notes.append(clipped_note)

        clipped_events = [
            (tick, message)
            for tick, message in non_note_events
            if tick <= target_ticks
        ]
        midi.tracks[track_index] = rebuild_track(clipped_events, clipped_notes, target_ticks)

    midi.save(path)


def apply_song_structure(path: Path, target_bars: int, conditions: dict[str, Any]) -> None:
    """Shape generated notes into intro, body, chorus, and ending sections."""
    midi = mido.MidiFile(path)
    if not midi.tracks:
        return

    bar_ticks = midi.ticks_per_beat * 4
    target_ticks = bar_ticks * max(1, int(target_bars))
    emotion = str(conditions.get("final_emotion") or "neutral").lower()

    for track_index, track in enumerate(midi.tracks):
        notes, non_note_events = extract_track_notes(track)
        if len(notes) < 2:
            continue

        has_drum_notes = any(note["channel"] == 9 for note in notes)
        shaped_notes = shape_section_notes(
            notes,
            track_index=track_index,
            target_bars=target_bars,
            bar_ticks=bar_ticks,
            has_drum_notes=has_drum_notes,
            emotion=emotion,
        )
        if not has_drum_notes:
            shaped_notes = add_cadence_note(
                shaped_notes,
                track_index=track_index,
                bar_ticks=bar_ticks,
                target_ticks=target_ticks,
                emotion=emotion,
            )

        midi.tracks[track_index] = rebuild_track(non_note_events, shaped_notes, target_ticks)

    midi.save(path)


def shape_section_notes(
    notes: list[dict[str, int]],
    track_index: int,
    target_bars: int,
    bar_ticks: int,
    has_drum_notes: bool,
    emotion: str,
) -> list[dict[str, int]]:
    """Apply simple section dynamics without destroying the generated melody."""
    shaped = []
    intro_bars = 2 if target_bars < 16 else 4
    ending_bars = 2 if target_bars < 16 else 4
    chorus_start = max(intro_bars, int(target_bars * 0.55))
    chorus_end = max(chorus_start + 1, target_bars - ending_bars)

    for note_index, note in enumerate(notes):
        bar = note["start"] // max(1, bar_ticks)
        section = get_song_section(bar, intro_bars, chorus_start, chorus_end, target_bars - ending_bars)

        if should_drop_section_note(section, note_index, track_index, has_drum_notes):
            continue

        shaped_note = note.copy()
        velocity_scale = {
            "intro": 0.68,
            "body": 0.88,
            "chorus": 1.06,
            "ending": 0.72,
        }[section]
        if track_index > 0 and not has_drum_notes:
            velocity_scale *= 0.88

        shaped_note["velocity"] = max(24, min(112, int(note["velocity"] * velocity_scale)))

        if not has_drum_notes and track_index == 0 and section == "chorus":
            chorus_lift = 1 if emotion in {"sad", "melancholic", "calm", "relaxed"} else 2
            shaped_note["pitch"] = max(0, min(127, note["pitch"] + chorus_lift))

        if section == "ending":
            duration = max(1, shaped_note["end"] - shaped_note["start"])
            shaped_note["end"] = shaped_note["start"] + max(duration, bar_ticks // 2)

        shaped.append(shaped_note)

    return shaped


def get_song_section(
    bar: int,
    intro_bars: int,
    chorus_start: int,
    chorus_end: int,
    ending_start: int,
) -> str:
    """Return a coarse song section name for a bar index."""
    if bar < intro_bars:
        return "intro"
    if bar >= ending_start:
        return "ending"
    if chorus_start <= bar < chorus_end:
        return "chorus"
    return "body"


def should_drop_section_note(
    section: str,
    note_index: int,
    track_index: int,
    has_drum_notes: bool,
) -> bool:
    """Thin support notes in intro and ending so sections have clearer shape."""
    if section not in {"intro", "ending"}:
        return False
    if track_index == 0 and not has_drum_notes:
        return False
    if has_drum_notes:
        return note_index % 3 == 1
    return note_index % 2 == 1


def add_cadence_note(
    notes: list[dict[str, int]],
    track_index: int,
    bar_ticks: int,
    target_ticks: int,
    emotion: str,
) -> list[dict[str, int]]:
    """Add a final held note so the MIDI resolves instead of stopping abruptly."""
    if not notes or target_ticks <= bar_ticks:
        return notes

    pitch_class = most_common_pitch_class(notes)
    average_pitch = sum(note["pitch"] for note in notes) / len(notes)
    if track_index == 0:
        pitch = nearest_pitch_for_class(pitch_class, int(average_pitch), 60, 76)
        velocity = 72 if emotion in {"energetic", "excited", "angry"} else 58
    elif track_index == 1:
        pitch = nearest_pitch_for_class(pitch_class, int(average_pitch) - 12, 36, 60)
        velocity = 52
    else:
        pitch = nearest_pitch_for_class(pitch_class, int(average_pitch), 48, 72)
        velocity = 46

    start = max(0, target_ticks - bar_ticks)
    cadence_note = {
        "start": start,
        "end": target_ticks,
        "pitch": pitch,
        "velocity": velocity,
        "channel": notes[0].get("channel", 0),
    }
    return notes + [cadence_note]


def most_common_pitch_class(notes: list[dict[str, int]]) -> int:
    """Find the pitch class that appears most often in a note list."""
    counts: dict[int, int] = {}
    for note in notes:
        pitch_class = note["pitch"] % 12
        counts[pitch_class] = counts.get(pitch_class, 0) + 1
    return max(counts.items(), key=lambda item: item[1])[0]


def nearest_pitch_for_class(pitch_class: int, center: int, low: int, high: int) -> int:
    """Choose a pitch with the requested class inside a practical register."""
    candidates = [pitch for pitch in range(low, high + 1) if pitch % 12 == pitch_class]
    if not candidates:
        return max(low, min(high, center))
    return min(candidates, key=lambda pitch: abs(pitch - center))


def get_midi_length_ticks(midi: mido.MidiFile) -> int:
    """Return the absolute end tick across all tracks."""
    length = 0
    for track in midi.tracks:
        tick = 0
        for message in track:
            tick += message.time
        length = max(length, tick)
    return length


def extract_track_notes(track: mido.MidiTrack) -> tuple[list[dict[str, int]], list[tuple[int, mido.Message]]]:
    """Split a track into note pairs and non-note events."""
    notes = []
    non_note_events = []
    active_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
    tick = 0

    for message in track:
        tick += message.time
        if message.type == "end_of_track":
            continue

        is_note_on = message.type == "note_on" and getattr(message, "velocity", 0) > 0
        is_note_end = message.type == "note_off" or (
            message.type == "note_on" and getattr(message, "velocity", 0) == 0
        )

        if is_note_on:
            key = (getattr(message, "channel", 0), message.note)
            active_notes.setdefault(key, []).append((tick, message.velocity))
            continue

        if is_note_end:
            key = (getattr(message, "channel", 0), message.note)
            started = active_notes.get(key, [])
            if started:
                start_tick, velocity = started.pop()
                notes.append(
                    {
                        "start": start_tick,
                        "end": max(start_tick + 1, tick),
                        "pitch": message.note,
                        "velocity": velocity,
                        "channel": getattr(message, "channel", 0),
                    }
                )
            continue

        non_note_events.append((tick, message.copy()))

    notes.sort(key=lambda note: (note["start"], note["pitch"]))
    return notes, non_note_events


def vary_melodic_notes(
    notes: list[dict[str, int]],
    track_index: int,
    bar_ticks: int,
    total_ticks: int,
    emotion: str,
) -> list[dict[str, int]]:
    """Apply small deterministic changes to repeated melodic phrases."""
    varied = []
    pitch_patterns = {
        "sad": [0, 0, -1, 0, 1, 0, 0, -2],
        "melancholic": [0, -1, 0, -1, 1, 0, -2, 0],
        "calm": [0, 0, 1, 0, -1, 0, 1, 0],
        "relaxed": [0, 0, 1, 0, -1, 0, 1, 0],
        "romantic": [0, 1, 0, 2, 0, -1, 1, 0],
        "angry": [0, 2, 0, -1, 2, 0, -1, 1],
        "energetic": [0, 1, -1, 2, 0, 2, -1, 1],
        "excited": [0, 1, -1, 2, 0, 2, -1, 1],
    }
    pitch_pattern = pitch_patterns.get(emotion, [0, 1, 0, -1, 1, 0, -1, 0])
    duration_scales = [1.0, 0.96, 1.04, 1.0, 0.98, 1.03, 1.0, 0.97]
    velocity_offsets = [0, -3, 2, -2, 3, -2, 2, -1]

    for note_index, note in enumerate(notes):
        start = note["start"]
        duration = max(1, note["end"] - note["start"])
        bar = start // max(1, bar_ticks)
        phrase = bar // 4
        pattern_index = (bar + phrase + track_index * 2) % len(pitch_pattern)
        varied_note = note.copy()

        if bar > 0:
            pitch_shift = pitch_pattern[pattern_index]
            if track_index > 0:
                pitch_shift = int(round(pitch_shift * 0.5))
            varied_note["pitch"] = max(0, min(127, note["pitch"] + pitch_shift))

            if duration > bar_ticks // 8:
                scale = duration_scales[(note_index + phrase + track_index) % len(duration_scales)]
                duration = max(bar_ticks // 24, int(duration * scale))

            varied_note["velocity"] = max(
                24,
                min(112, note["velocity"] + velocity_offsets[(bar + note_index) % len(velocity_offsets)]),
            )

        varied_note["start"] = start
        varied_note["end"] = max(start + 1, min(total_ticks, start + duration))
        varied.append(varied_note)

    return varied


def vary_drum_notes(
    notes: list[dict[str, int]],
    track_index: int,
    bar_ticks: int,
) -> list[dict[str, int]]:
    """Vary drum dynamics without changing drum instruments."""
    varied = []
    velocity_offsets = [0, -6, 5, -4, 7, -5, 3, -3]

    for note_index, note in enumerate(notes):
        varied_note = note.copy()
        bar = note["start"] // max(1, bar_ticks)
        if bar > 0:
            offset = velocity_offsets[(bar + note_index + track_index) % len(velocity_offsets)]
            varied_note["velocity"] = max(24, min(112, note["velocity"] + offset))
        varied.append(varied_note)

    return varied


def rebuild_track(
    non_note_events: list[tuple[int, mido.Message]],
    notes: list[dict[str, int]],
    total_ticks: int,
) -> mido.MidiTrack:
    """Build a MIDI track from absolute events."""
    events: list[tuple[int, int, mido.Message]] = []
    for tick, message in non_note_events:
        events.append((max(0, tick), 1, message.copy()))

    for note in notes:
        start = max(0, min(total_ticks, note["start"]))
        end = max(start + 1, min(total_ticks, note["end"]))
        channel = max(0, min(15, note["channel"]))
        pitch = max(0, min(127, note["pitch"]))
        velocity = max(1, min(127, note["velocity"]))
        events.append((start, 2, mido.Message("note_on", channel=channel, note=pitch, velocity=velocity, time=0)))
        events.append((end, 0, mido.Message("note_off", channel=channel, note=pitch, velocity=0, time=0)))

    events.sort(key=lambda item: (item[0], item[1]))
    track = mido.MidiTrack()
    last_tick = 0
    for tick, _, message in events:
        message.time = max(0, tick - last_tick)
        track.append(message)
        last_tick = tick

    track.append(mido.MetaMessage("end_of_track", time=max(0, total_ticks - last_tick)))
    return track


def collect_main_notes(midi: mido.MidiFile) -> list[dict[str, int]]:
    """Read note start times from the first generated track."""
    notes = []
    active_notes = {}
    current_tick = 0

    for message in midi.tracks[0]:
        current_tick += message.time

        if message.type == "note_on" and message.velocity > 0:
            active_notes[(message.channel, message.note)] = (current_tick, message.velocity)

        if message.type == "note_off" or (
            message.type == "note_on" and getattr(message, "velocity", 0) == 0
        ):
            key = (message.channel, message.note)
            started = active_notes.pop(key, None)
            if started:
                start_tick, velocity = started
                notes.append(
                    {
                        "start": start_tick,
                        "duration": max(120, current_tick - start_tick),
                        "pitch": message.note,
                        "velocity": velocity,
                    }
                )

    return notes


def build_support_track(
    main_notes: list[dict[str, int]],
    instrument: str,
    channel: int,
    ticks_per_beat: int,
) -> mido.MidiTrack:
    """Build a calm accompaniment line for one extra instrument."""
    track = mido.MidiTrack()
    program = INSTRUMENT_PROGRAMS.get(instrument, 48)
    track.append(mido.Message("program_change", channel=channel, program=program, time=0))

    bar_ticks = ticks_per_beat * 4
    selected_notes = choose_support_notes(main_notes, instrument, bar_ticks)
    last_tick = 0

    for note in selected_notes:
        start = note["start"]
        duration = note["duration"]
        pitch = note["pitch"]
        velocity = note["velocity"]

        track.append(
            mido.Message(
                "note_on",
                channel=channel,
                note=pitch,
                velocity=velocity,
                time=max(0, start - last_tick),
            )
        )
        track.append(
            mido.Message(
                "note_off",
                channel=channel,
                note=pitch,
                velocity=0,
                time=duration,
            )
        )
        last_tick = start + duration

    return track


def choose_support_notes(
    main_notes: list[dict[str, int]],
    instrument: str,
    bar_ticks: int,
) -> list[dict[str, int]]:
    """Choose fewer, longer notes so support tracks do not copy the melody."""
    chosen = []
    used_bars = set()

    for note in main_notes:
        bar = note["start"] // max(1, bar_ticks)
        if bar in used_bars:
            continue
        used_bars.add(bar)

        start = int(bar * bar_ticks)

        if instrument == "bass":
            root = max(36, min(52, note["pitch"] - 24))
            fifth = max(36, min(55, root + 7))
            chosen.extend(
                [
                    {
                        "start": start,
                        "duration": int(bar_ticks // 2),
                        "pitch": int(root),
                        "velocity": 64,
                    },
                    {
                        "start": start + int(bar_ticks // 2),
                        "duration": int(bar_ticks // 2),
                        "pitch": int(fifth),
                        "velocity": 58,
                    },
                ]
            )
        else:
            root = max(50, min(74, note["pitch"] + 5))
            harmony = max(50, min(79, root + 7))
            chosen.extend(
                [
                    {
                        "start": start,
                        "duration": int(bar_ticks),
                        "pitch": int(root),
                        "velocity": 56,
                    },
                    {
                        "start": start,
                        "duration": int(bar_ticks),
                        "pitch": int(harmony),
                        "velocity": 50,
                    },
                ]
            )

    return chosen


def choose_bpm(conditions: dict[str, Any]) -> int:
    """Choose a simple tempo from emotion/arousal."""
    emotion = str(conditions.get("final_emotion") or "neutral").lower()
    try:
        arousal = float(conditions.get("arousal") or 0.5)
    except (TypeError, ValueError):
        arousal = 0.5

    if emotion in {"calm", "relaxed", "sad", "melancholic", "romantic", "lonely"} or arousal < 0.35:
        return 82
    if emotion in {"energetic", "angry", "excited", "anxious"} or arousal > 0.75:
        return 128
    return 105


def bpm_to_midi_tempo(bpm: int) -> int:
    """Convert BPM into the tempo format used inside MIDI files."""
    return int(60_000_000 / max(1, bpm))


def choose_temperature(value: Any) -> float:
    """Use higher arousal to make MIDI-GPT sampling slightly more varied."""
    try:
        arousal = float(value)
    except (TypeError, ValueError):
        arousal = 0.5

    return max(0.82, min(0.96, 0.82 + (arousal * 0.16)))


def improve_midi_file(path: Path, instruments: list[str], conditions: dict[str, Any]) -> None:
    """Apply light metadata cleanup without rewriting the generated melody."""
    midi = mido.MidiFile(path)
    tempo = bpm_to_midi_tempo(choose_bpm(conditions))

    for track_index, track in enumerate(midi.tracks):
        instrument = instruments[track_index] if track_index < len(instruments) else "piano"
        program = INSTRUMENT_PROGRAMS.get(instrument, 0)

        has_program = any(message.type == "program_change" for message in track)
        if not has_program and instrument != "drum":
            track.insert(0, mido.Message("program_change", channel=track_index, program=program, time=0))

        for message in track:
            if message.type == "set_tempo":
                message.tempo = tempo

            if message.type == "program_change" and instrument != "drum":
                message.program = program

    midi.save(path)


def fix_pitch_for_instrument(
    pitch: int,
    instrument: str,
    tick: int = 0,
    ticks_per_beat: int = 480,
) -> int:
    """Move each instrument into a better range and add small bar variation."""
    bar = tick // max(1, ticks_per_beat * 4)
    bar_changes = [0, 2, 4, 5, 7, 5, 4, 2]
    change = bar_changes[bar % len(bar_changes)]

    if instrument == "bass":
        bass_changes = [0, -5, 0, -7, 0, -5, -3, -7]
        return max(36, min(55, pitch - 24 + bass_changes[bar % len(bass_changes)]))
    if instrument in {"flute", "pad"}:
        return max(60, min(84, pitch + 12 + change))
    if instrument == "strings":
        return max(48, min(79, pitch + [0, 0, 5, 5, 7, 7, 5, 2][bar % 8]))
    return max(45, min(76, pitch + change))


def fix_velocity_for_instrument(velocity: int, instrument: str) -> int:
    """Balance volume so all tracks do not sound equally strong."""
    if instrument in {"strings", "pad", "flute"}:
        return max(35, min(90, velocity - 12))
    if instrument == "bass":
        return max(45, min(95, velocity - 5))
    return max(40, min(105, velocity))
