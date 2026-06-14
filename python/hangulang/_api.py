from __future__ import annotations

import json
from dataclasses import replace
from importlib import import_module
from os import PathLike
from typing import Any, TypeAlias, cast

from hangulang.assets import ExtractedAsset
from hangulang.exceptions import (
    ConversionError,
    HangulangError,
    ParseError,
    UnsupportedFormatError,
)
from hangulang.options import (
    AssetPolicy,
    BBoxResolution,
    ConversionOptions,
    coerce_asset_policy,
)

DocumentInput: TypeAlias = str | bytes | PathLike[str]

_native: Any | None

try:
    _native = import_module("hangulang._native")
except ImportError as exc:  # pragma: no cover - exercised only before build.
    _native = None
    _native_import_error: ImportError | None = exc
else:
    _native_import_error = None


def convert_to_doclang(
    input: DocumentInput,
    options: ConversionOptions | None = None,
    *,
    include_locations: bool | None = None,
    bbox_resolution: BBoxResolution | None = None,
) -> str:
    """Convert an HWP/HWPX document to DocLang XML."""

    native = _require_native()
    resolved = _resolve_options(
        options,
        include_locations=include_locations,
        bbox_resolution=bbox_resolution,
    )

    try:
        return cast(
            str,
            native.convert_to_doclang(
                input,
                resolved.include_locations,
                resolved.asset_policy.value,
                resolved.uri_prefix,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_native_error(exc) from exc


def convert_to_markdown(
    input: DocumentInput,
    options: ConversionOptions | None = None,
    *,
    include_locations: bool | None = None,
    bbox_resolution: BBoxResolution | None = None,
) -> str:
    """Convert an HWP/HWPX document to Markdown."""

    native = _require_native()
    resolved = _resolve_options(
        options,
        include_locations=include_locations,
        bbox_resolution=bbox_resolution,
    )

    try:
        return cast(
            str,
            native.convert_to_markdown(
                input,
                resolved.include_locations,
                resolved.asset_policy.value,
                resolved.uri_prefix,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_native_error(exc) from exc


def convert_to_payload(
    input: DocumentInput,
    options: ConversionOptions | None = None,
    *,
    include_locations: bool | None = None,
    bbox_resolution: BBoxResolution | None = None,
) -> dict[str, Any]:
    """Convert an HWP/HWPX document to a semantic JSON-compatible payload."""

    native = _require_native()
    resolved = _resolve_options(
        options,
        include_locations=include_locations,
        bbox_resolution=bbox_resolution,
    )

    try:
        payload_json = native.convert_to_payload_json(
            input,
            resolved.include_locations,
            resolved.asset_policy.value,
            resolved.uri_prefix,
        )
        payload = json.loads(payload_json)
    except Exception as exc:  # noqa: BLE001
        raise _map_native_error(exc) from exc

    if not isinstance(payload, dict):
        raise ConversionError("native payload output was not a JSON object")

    return cast(dict[str, Any], payload)


def extract_assets(
    input: DocumentInput,
    options: ConversionOptions | None = None,
    *,
    asset_policy: AssetPolicy | str | None = None,
    output_dir: str | PathLike[str] | None = None,
    uri_prefix: str | None = None,
) -> list[ExtractedAsset]:
    """Extract or reference embedded document assets."""

    native = _require_native()
    resolved = _resolve_options(
        options,
        asset_policy=asset_policy,
        asset_output_dir=output_dir,
        uri_prefix=uri_prefix,
    )

    try:
        assets_json = native.extract_assets_json(
            input,
            resolved.asset_policy.value,
            _stringify_optional_path(resolved.asset_output_dir),
            resolved.uri_prefix,
        )
        raw_assets = json.loads(assets_json)
    except Exception as exc:  # noqa: BLE001
        raise _map_native_error(exc) from exc

    if not isinstance(raw_assets, list):
        raise ConversionError("native asset output was not a JSON array")

    return [ExtractedAsset.from_mapping(asset) for asset in raw_assets]


def _resolve_options(
    options: ConversionOptions | None,
    *,
    include_locations: bool | None = None,
    bbox_resolution: BBoxResolution | None = None,
    asset_policy: AssetPolicy | str | None = None,
    asset_output_dir: str | PathLike[str] | None = None,
    uri_prefix: str | None = None,
) -> ConversionOptions:
    resolved = options if options is not None else ConversionOptions()

    if not isinstance(resolved, ConversionOptions):
        raise TypeError("options must be a ConversionOptions instance")

    updates: dict[str, Any] = {}
    if include_locations is not None:
        updates["include_locations"] = include_locations
    if bbox_resolution is not None:
        updates["bbox_resolution"] = bbox_resolution
    if asset_policy is not None:
        updates["asset_policy"] = coerce_asset_policy(asset_policy)
    if asset_output_dir is not None:
        updates["asset_output_dir"] = asset_output_dir
    if uri_prefix is not None:
        updates["uri_prefix"] = uri_prefix

    resolved = replace(resolved, **updates)
    if resolved.bbox_resolution != "none" and not resolved.include_locations:
        resolved = replace(resolved, include_locations=True)
    return resolved


def _require_native() -> Any:
    if _native is None:
        raise ConversionError(
            "hangulang native extension is not installed. "
            "Install a built wheel or run `maturin develop`."
        ) from _native_import_error

    return _native


def _map_native_error(exc: BaseException) -> HangulangError:
    if isinstance(exc, HangulangError):
        return exc

    message = str(exc)
    if message.startswith("unsupported_format:"):
        return UnsupportedFormatError(_strip_error_code(message))
    if message.startswith("parse_error:"):
        return ParseError(_strip_error_code(message))
    if message.startswith("conversion_error:"):
        return ConversionError(_strip_error_code(message))
    if isinstance(exc, (OSError, ValueError, TypeError)):
        return ParseError(message)

    return ConversionError(message)


def _strip_error_code(message: str) -> str:
    return message.split(":", 1)[1].strip()


def _stringify_optional_path(path: str | PathLike[str] | None) -> str | None:
    return None if path is None else str(path)
