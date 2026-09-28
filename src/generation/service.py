from typing import Any

from .baseline_adapter import generate_with_baseline


def generate_music_from_conditions(
    request_data: dict[str, Any],
    conditions: dict[str, Any],
    model_name: str = "baseline",
) -> dict[str, Any]:
    """Small generation interface used by the backend."""
    selected_model = (model_name or "baseline").strip().lower()

    if selected_model in {"baseline", "baseline-transformer", "local"}:
        return generate_with_baseline(request_data, conditions)

    if selected_model in {"midi-gpt", "midigpt"}:
        try:
            from .midigpt_adapter import create_midigpt_music

            return create_midigpt_music(request_data, conditions)
        except (FileNotFoundError, ImportError, ModuleNotFoundError) as exc:
            # Keep the website usable when the optional research checkpoint is absent.
            fallback = generate_with_baseline(request_data, conditions)
            fallback["requested_model"] = selected_model
            fallback["fallback_reason"] = str(exc)
            return fallback
        except RuntimeError as exc:
            fallback = generate_with_baseline(request_data, conditions)
            fallback["requested_model"] = selected_model
            fallback["fallback_reason"] = str(exc)
            return fallback
        except ValueError as exc:
            fallback = generate_with_baseline(request_data, conditions)
            fallback["requested_model"] = selected_model
            fallback["fallback_reason"] = str(exc)
            return fallback

    raise ValueError(f"Unknown generation model: {model_name}")


def preview_midigpt_controls(conditions: dict[str, Any]) -> dict[str, Any]:
    from .midigpt_adapter import build_midigpt_controls

    return build_midigpt_controls(conditions)
