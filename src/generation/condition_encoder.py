"""Learned condition encoder for emotion-aware MIDI-GPT experiments."""

from __future__ import annotations

from typing import Any

import torch
from torch import Tensor, nn


EMOTION_LABELS = (
    "neutral",
    "happy",
    "sad",
    "relaxed",
    "angry",
    "energetic",
    "melancholic",
    "romantic",
    "anxious",
    "hopeful",
    "lonely",
)

STYLE_LABELS = (
    "neutral",
    "calm",
    "pop",
    "classical",
    "energetic",
)

EMOTION_TO_ID = {label: index for index, label in enumerate(EMOTION_LABELS)}
STYLE_TO_ID = {label: index for index, label in enumerate(STYLE_LABELS)}
DENSITY_TO_ID = {"low": 0, "low_medium": 1, "medium": 2, "medium_high": 3, "high": 4}


def _label_id(value: Any, labels: dict[str, int]) -> int:
    return labels.get(str(value or "neutral").strip().lower(), 0)


def conditions_to_tensors(
    conditions: dict[str, Any],
    device: torch.device | str = "cpu",
) -> dict[str, Tensor]:
    """Convert one structured request into tensors for the condition encoder."""
    tempo_range = conditions.get("tempo_range") or [85, 110]
    if not isinstance(tempo_range, (list, tuple)) or len(tempo_range) < 2:
        tempo_range = [85, 110]

    return {
        "emotion_id": torch.tensor([_label_id(conditions.get("final_emotion"), EMOTION_TO_ID)], device=device),
        "style_id": torch.tensor([_label_id(conditions.get("style", ["neutral"])[0] if conditions.get("style") else "neutral", STYLE_TO_ID)], device=device),
        "valence_arousal": torch.tensor(
            [[float(conditions.get("valence", 0.5)), float(conditions.get("arousal", 0.5))]],
            dtype=torch.float32,
            device=device,
        ),
        "tempo_range": torch.tensor([[float(tempo_range[0]), float(tempo_range[1])]], dtype=torch.float32, device=device),
        "density_id": torch.tensor([DENSITY_TO_ID.get(str(conditions.get("density_level", "medium")), 2)], device=device),
    }


class EmotionConditionAdapter(nn.Module):
    """Fuse categorical and numeric music conditions into a MIDI-GPT-sized vector."""

    def __init__(self, hidden_size: int = 768) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.emotion_embedding = nn.Embedding(len(EMOTION_LABELS), hidden_size)
        self.style_embedding = nn.Embedding(len(STYLE_LABELS), hidden_size)
        self.density_embedding = nn.Embedding(len(DENSITY_TO_ID), hidden_size)
        self.numeric_projection = nn.Sequential(
            nn.Linear(6, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
        )
        self.fusion = nn.Sequential(
            nn.Linear(hidden_size * 4, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(
        self,
        emotion_id: Tensor,
        style_id: Tensor,
        valence_arousal: Tensor,
        tempo_range: Tensor,
        density_id: Tensor,
    ) -> Tensor:
        tempo = tempo_range / 200.0
        numeric = torch.cat([valence_arousal, tempo], dim=-1)
        numeric = torch.cat([numeric, numeric.mean(dim=-1, keepdim=True), numeric.std(dim=-1, keepdim=True)], dim=-1)
        numeric_vector = self.numeric_projection(numeric)
        fused = torch.cat(
            [
                self.emotion_embedding(emotion_id),
                self.style_embedding(style_id),
                self.density_embedding(density_id),
                numeric_vector,
            ],
            dim=-1,
        )
        return self.fusion(fused)
