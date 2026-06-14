from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from os import PathLike
from typing import Literal, TypeAlias

BBoxResolution: TypeAlias = Literal["none", "page", "block", "span"]


class AssetPolicy(str, Enum):
    """How embedded assets should be represented."""

    INLINE = "inline"
    REFERENCE = "reference"
    WRITE = "write"
    URI = "uri"
    IGNORE = "ignore"


@dataclass(frozen=True, slots=True)
class ConversionOptions:
    include_locations: bool = False
    bbox_resolution: BBoxResolution = "none"
    asset_policy: AssetPolicy = AssetPolicy.INLINE
    asset_output_dir: str | PathLike[str] | None = None
    uri_prefix: str | None = None
    report_losses: bool = False


def coerce_asset_policy(value: AssetPolicy | str) -> AssetPolicy:
    if isinstance(value, AssetPolicy):
        return value

    try:
        return AssetPolicy(value)
    except ValueError as exc:
        allowed = ", ".join(policy.value for policy in AssetPolicy)
        message = f"unknown asset policy {value!r}; expected one of {allowed}"
        raise ValueError(message) from exc
