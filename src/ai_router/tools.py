from __future__ import annotations

from typing import Any


def build_tools(grounding: str | None, *, latitude: float | None = None, longitude: float | None = None) -> list[dict[str, Any]]:
    if grounding == "search":
        return [{"type": "google_search"}]
    if grounding == "maps":
        tool: dict[str, Any] = {"type": "google_maps"}
        if latitude is not None:
            tool["latitude"] = latitude
        if longitude is not None:
            tool["longitude"] = longitude
        return [tool]
    return []
