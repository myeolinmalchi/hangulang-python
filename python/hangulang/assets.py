from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from hangulang.exceptions import ConversionError


@dataclass(frozen=True, slots=True)
class ExtractedAsset:
    """Reference to an extracted or externally addressable document asset."""

    id: str
    path: str | None = None
    uri: str | None = None
    mime_type: str | None = None

    @classmethod
    def from_mapping(cls, value: object) -> ExtractedAsset:
        if not isinstance(value, Mapping):
            raise ConversionError("asset entry was not a JSON object")

        raw = value
        asset_id = _required_string(raw, "id")
        path = _optional_string(raw, "path")
        uri = _optional_string(raw, "uri")
        mime_type = _optional_string(raw, "mime_type")
        return cls(id=asset_id, path=path, uri=uri, mime_type=mime_type)


def _required_string(value: Mapping[Any, Any], key: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or raw == "":
        raise ConversionError(f"asset entry is missing required string field {key!r}")
    return raw


def _optional_string(value: Mapping[Any, Any], key: str) -> str | None:
    raw = value.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ConversionError(f"asset field {key!r} must be a string when present")
    return raw
