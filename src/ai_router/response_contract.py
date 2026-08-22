"""Validation helpers for the public AIRouter.complete_auto response contract."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from typing import Any


COMMON_FIELDS = ("output_type", "intent", "route", "provider", "model", "url_citations")
SUPPORTED_OUTPUT_TYPES = {
    "text",
    "translation",
    "image",
    "audio",
    "embedding",
    "video_analysis",
}


class ResponseContractError(ValueError):
    """Raised when a successful router result violates the public response contract."""


def validate_response_envelope(result: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a shallow copy of a successful ``complete_auto`` result.

    The validator deliberately checks shape, not provider quality. Provider/model
    identity is metadata, while the output-specific checks prevent consumers from
    receiving an apparently successful but unusable artifact.
    """
    if not isinstance(result, Mapping):
        raise ResponseContractError("response must be a mapping")

    missing = [field for field in COMMON_FIELDS if field not in result]
    if missing:
        raise ResponseContractError(f"missing common response fields: {', '.join(missing)}")

    for field in ("output_type", "intent", "route", "provider", "model"):
        if not isinstance(result[field], str) or not result[field].strip():
            raise ResponseContractError(f"{field} must be a non-empty string")

    output_type = result["output_type"]
    if output_type not in SUPPORTED_OUTPUT_TYPES:
        raise ResponseContractError(f"unsupported output_type in successful response: {output_type}")
    if result["intent"] != output_type and not (output_type == "text" and result["intent"] == "text"):
        raise ResponseContractError("intent must match output_type for executable responses")

    citations = result["url_citations"]
    if not isinstance(citations, list) or any(not isinstance(url, str) or not url.startswith(("http://", "https://")) for url in citations):
        raise ResponseContractError("url_citations must be a list of HTTP(S) URL strings")

    if output_type == "text" and not any(key in result for key in ("text", "answer", "response")):
        # Structured text is allowed when it contains model-defined fields, but
        # the envelope must still expose at least one non-metadata payload field.
        metadata = set(COMMON_FIELDS) | {"annotations", "grounding_metadata", "grounding_sources"}
        if not any(key not in metadata for key in result):
            raise ResponseContractError("text response has no content field")
    elif output_type == "translation":
        if not any(isinstance(result.get(key), str) and result[key].strip() for key in ("translation", "text")):
            raise ResponseContractError("translation response needs non-empty translation or text")
    elif output_type in {"image", "audio"}:
        _validate_base64_artifact(result)
        if not isinstance(result.get("mime_type"), str) or not result["mime_type"].strip():
            raise ResponseContractError(f"{output_type} response needs mime_type")
        if output_type == "audio" and "sample_rate_hz" in result and not isinstance(result["sample_rate_hz"], int):
            raise ResponseContractError("audio sample_rate_hz must be an integer when present")
    elif output_type == "embedding":
        embeddings = result.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise ResponseContractError("embedding response needs a non-empty embeddings list")
        for item in embeddings:
            if not isinstance(item, Mapping) or not isinstance(item.get("values"), list) or not item["values"]:
                raise ResponseContractError("each embedding needs a non-empty values list")

    return dict(result)


def _validate_base64_artifact(result: Mapping[str, Any]) -> None:
    encoded = result.get("data_base64")
    if not isinstance(encoded, str) or not encoded:
        raise ResponseContractError("media response needs non-empty data_base64")
    try:
        base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ResponseContractError("data_base64 is not valid Base64") from exc
