# %% [markdown]
# POP909 preprocessing and emotion-conditioned MIDI-GPT preparation
# Run this file cell by cell in Google Colab.

# %%
!pip -q install "midigpt[train]" pandas mido pyarrow kagglehub

# %%
from pathlib import Path
import json
import random
import math
import shutil

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import mido

from google.colab import drive
drive.mount("/content/drive")

DRIVE_ROOT = Path("/content/drive/MyDrive/FYP_MIDI")
RAW_DIR = DRIVE_ROOT / "raw_midi"
DATASET_DIR = DRIVE_ROOT / "dataset"
RAW_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
TRAIN_RATIO = 0.70
VALID_RATIO = 0.15
TEST_RATIO = 0.15
MIN_TRACKS = 1
MIN_NOTES = 30
AUTO_LABEL = True

assert abs(TRAIN_RATIO + VALID_RATIO + TEST_RATIO - 1.0) < 1e-6
print("Drive workspace:", DRIVE_ROOT)

# %% [markdown]
# Download POP909 only when raw_midi is empty. You can also upload your own MIDI files there.

# %%
if not list(RAW_DIR.rglob("*.mid")) and not list(RAW_DIR.rglob("*.midi")):
    import kagglehub
    kaggle_path = Path(kagglehub.dataset_download("nishtha711/pop909"))
    downloaded = list(kaggle_path.rglob("*.mid")) + list(kaggle_path.rglob("*.midi"))
    for source in downloaded:
        target = RAW_DIR / source.name
        if not target.exists():
            shutil.copy2(source, target)

midi_files = sorted(list(RAW_DIR.rglob("*.mid")) + list(RAW_DIR.rglob("*.midi")))
print("MIDI files:", len(midi_files))
assert midi_files, "No MIDI files found. Upload files to FYP_MIDI/raw_midi first."

# %%
def midi_features(path: Path) -> dict:
    """Extract simple, explainable features for initial labels."""
    midi = mido.MidiFile(path)
    tempo_values = []
    note_count = 0
    active = 0
    max_polyphony = 0
    ticks = max(1, midi.length)

    for track in midi.tracks:
        for message in track:
            if message.type == "set_tempo":
                tempo_values.append(mido.tempo2bpm(message.tempo))
            if message.type == "note_on" and message.velocity > 0:
                note_count += 1
                active += 1
                max_polyphony = max(max_polyphony, active)
            elif message.type in {"note_off", "note_on"} and message.velocity == 0:
                active = max(0, active - 1)

    bpm = sum(tempo_values) / len(tempo_values) if tempo_values else 120.0
    duration = max(1.0, midi.length)
    density = note_count / duration
    return {
        "tempo": round(float(bpm), 2),
        "duration_seconds": round(float(duration), 2),
        "note_count": int(note_count),
        "note_density": round(float(density), 4),
        "max_polyphony": int(max_polyphony),
        "track_count": len(midi.tracks),
    }


def initial_labels(features: dict) -> dict:
    """Create weak labels; review these labels before model training."""
    tempo = features["tempo"]
    density = features["note_density"]

    if tempo >= 135 or density >= 5.0:
        emotion, valence, arousal = "energetic", 0.80, 0.90
        style = "energetic"
    elif tempo <= 78 and density <= 2.0:
        emotion, valence, arousal = "relaxed", 0.65, 0.20
        style = "calm"
    elif tempo <= 95:
        emotion, valence, arousal = "sad", 0.25, 0.30
        style = "calm"
    else:
        emotion, valence, arousal = "happy", 0.80, 0.70
        style = "pop"

    return {
        "emotion": emotion,
        "style": style,
        "valence": valence,
        "arousal": arousal,
        "label_source": "auto",
    }


# %%
rows = []
for index, path in enumerate(midi_files, start=1):
    try:
        features = midi_features(path)
        if features["note_count"] < MIN_NOTES or features["track_count"] < MIN_TRACKS:
            continue
        labels = initial_labels(features)
        rows.append({"filename": path.name, **features, **labels})
    except Exception as exc:
        print("Skipped", path.name, type(exc).__name__, str(exc))

metadata = pd.DataFrame(rows).sort_values("filename").reset_index(drop=True)
metadata_path = DRIVE_ROOT / "metadata_auto.csv"
metadata.to_csv(metadata_path, index=False)
print("Usable MIDI:", len(metadata))
print("Saved:", metadata_path)
display(metadata.head())
display(metadata["emotion"].value_counts())

# %% [markdown]
# Review `metadata_auto.csv` in Google Drive. Change incorrect emotion/style/valence/arousal labels.
# Save the reviewed file as `metadata.csv`. The training cells use `metadata.csv` when present.

# %%
reviewed_path = DRIVE_ROOT / "metadata.csv"
if reviewed_path.exists():
    metadata = pd.read_csv(reviewed_path)
    print("Using reviewed labels:", reviewed_path)
else:
    print("Using auto labels for now. Create metadata.csv after manual review.")

required_columns = {"filename", "emotion", "style", "valence", "arousal"}
missing = required_columns - set(metadata.columns)
if missing:
    raise ValueError(f"Missing metadata columns: {sorted(missing)}")

# %%
random.seed(SEED)
records = metadata.to_dict("records")
random.shuffle(records)
n_total = len(records)
n_train = int(n_total * TRAIN_RATIO)
n_valid = int(n_total * VALID_RATIO)

splits = {
    "train": records[:n_train],
    "valid": records[n_train:n_train + n_valid],
    "test": records[n_train + n_valid:],
}
for name, values in splits.items():
    split_path = DRIVE_ROOT / f"metadata_{name}.csv"
    pd.DataFrame(values).to_csv(split_path, index=False)
    print(name, len(values), split_path)

# %% [markdown]
# Convert the split MIDI files to the official MIDI-GPT parquet format.

# %%
from midigpt import Score

def create_parquet(split_records: list[dict], output_path: Path):
    music_col, num_tracks_col, total_notes_col, beats_col, filename_col = [], [], [], [], []
    skipped = 0

    for record in split_records:
        path = RAW_DIR / record["filename"]
        try:
            midi_bytes = path.read_bytes()
            score = Score.from_bytes(midi_bytes)
            if not score.tracks:
                skipped += 1
                continue
            total_notes = sum(len(bar.notes) for track in score.tracks for bar in track.bars)
            if total_notes < MIN_NOTES or len(score.tracks) < MIN_TRACKS:
                skipped += 1
                continue
            max_bars = max(len(track.bars) for track in score.tracks)
            music_col.append(midi_bytes)
            filename_col.append(record["filename"])
            num_tracks_col.append(len(score.tracks))
            total_notes_col.append(total_notes)
            beats_col.append(float(max_bars * 4))
        except Exception:
            skipped += 1

    if not music_col:
        raise RuntimeError(f"No valid MIDI rows for {output_path}")

    table = pa.table({
        "filename": pa.array(filename_col),
        "music": pa.array(music_col, type=pa.large_binary()),
        "num_tracks": pa.array(num_tracks_col, type=pa.int32()),
        "total_notes": pa.array(total_notes_col, type=pa.int64()),
        "loop_duration_beats": pa.array(beats_col, type=pa.float64()),
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)
    print("Saved", output_path, "rows=", len(music_col), "skipped=", skipped)


for split_name, split_records in splits.items():
    create_parquet(split_records, DATASET_DIR / split_name / "00000.parquet")

# %%
for split_name in ("train", "valid", "test"):
    path = DATASET_DIR / split_name / "00000.parquet"
    table = pq.read_table(path)
    print(split_name, table.num_rows, table.column_names)

# %% [markdown]
# Condition label encoders. These IDs are consumed by the custom ConditionEncoder.

# %%
EMOTIONS = ["neutral", "happy", "sad", "relaxed", "angry", "energetic", "melancholic"]
STYLES = ["neutral", "calm", "pop", "classical", "energetic"]

label_config = {
    "emotion_to_id": {name: i for i, name in enumerate(EMOTIONS)},
    "style_to_id": {name: i for i, name in enumerate(STYLES)},
    "emotion_labels": EMOTIONS,
    "style_labels": STYLES,
}
with open(DRIVE_ROOT / "label_config.json", "w", encoding="utf-8") as handle:
    json.dump(label_config, handle, indent=2)
print(label_config)

# %% [markdown]
# ConditionEncoder smoke test. This confirms the label input produces a 768-D vector.

# %%
import torch
from torch import nn

class EmotionConditionAdapter(nn.Module):
    def __init__(self, hidden_size=768):
        super().__init__()
        self.emotion = nn.Embedding(len(EMOTIONS), hidden_size)
        self.style = nn.Embedding(len(STYLES), hidden_size)
        self.numeric = nn.Sequential(nn.Linear(6, hidden_size), nn.LayerNorm(hidden_size), nn.GELU())
        self.fusion = nn.Sequential(
            nn.Linear(hidden_size * 3, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(self, emotion_id, style_id, valence_arousal, tempo_range):
        numeric = torch.cat([valence_arousal, tempo_range / 200.0], dim=-1)
        numeric = torch.cat([numeric, numeric.mean(-1, keepdim=True), numeric.std(-1, keepdim=True)], dim=-1)
        numeric = self.numeric(numeric)
        return self.fusion(torch.cat([
            self.emotion(emotion_id),
            self.style(style_id),
            numeric,
        ], dim=-1))

adapter = EmotionConditionAdapter().cuda() if torch.cuda.is_available() else EmotionConditionAdapter()
device = next(adapter.parameters()).device
sample = adapter(
    torch.tensor([2], device=device),
    torch.tensor([1], device=device),
    torch.tensor([[0.20, 0.30]], device=device),
    torch.tensor([[60.0, 90.0]], device=device),
)
print("Condition vector:", sample.shape)
assert sample.shape == (1, 768)

# %% [markdown]
# At this point the data and labels are ready. The next training stage must use a custom
# MIDI-GPT wrapper that accepts these condition tensors. Do not call the standard
# fine_tune.py as a conditional run yet; it currently trains on input_ids only.
