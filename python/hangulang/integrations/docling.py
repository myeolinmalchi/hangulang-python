from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from hangulang import convert_to_doclang, convert_to_markdown, convert_to_payload
from hangulang._api import DocumentInput
from hangulang.integrations._payload import (
    iter_payload_blocks,
    payload_metadata,
    records_as_dicts,
    source_display,
)

DoclingHandoffFormat = Literal["handoff", "payload", "doclang", "markdown"]


@dataclass(frozen=True, slots=True)
class DoclingHandoff:
    """Framework-neutral handoff payload for a Docling HWP backend."""

    source: str
    schema_version: str | None
    doclang_version: str | None
    semantic_payload: dict[str, Any]
    blocks: list[dict[str, Any]]
    assets: list[Any]
    losses: list[Any]
    doclang_xml: str | None = None
    markdown: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HangulangDoclingAdapter:
    """Docling-facing adapter built on Hangulang semantic outputs."""

    def __init__(
        self,
        *,
        include_locations: bool = True,
        include_doclang: bool = True,
        include_markdown: bool = False,
    ) -> None:
        self.include_locations = include_locations
        self.include_doclang = include_doclang
        self.include_markdown = include_markdown

    def convert(
        self,
        input: DocumentInput,
        *,
        format: DoclingHandoffFormat = "handoff",
        include_locations: bool | None = None,
    ) -> dict[str, Any] | str:
        resolved_locations = (
            self.include_locations if include_locations is None else include_locations
        )
        if format == "payload":
            return convert_to_payload(input, include_locations=resolved_locations)
        if format == "doclang":
            return convert_to_doclang(input, include_locations=resolved_locations)
        if format == "markdown":
            return convert_to_markdown(input, include_locations=resolved_locations)
        if format == "handoff":
            return self.to_handoff(
                input,
                include_locations=resolved_locations,
            ).to_dict()

        raise ValueError(
            "format must be 'handoff', 'payload', 'doclang', or 'markdown'"
        )

    def to_handoff(
        self,
        input: DocumentInput,
        *,
        include_locations: bool | None = None,
    ) -> DoclingHandoff:
        resolved_locations = (
            self.include_locations if include_locations is None else include_locations
        )
        payload = convert_to_payload(input, include_locations=resolved_locations)
        metadata = payload_metadata(input, payload)
        doclang_xml = (
            convert_to_doclang(input, include_locations=resolved_locations)
            if self.include_doclang
            else None
        )
        markdown = (
            convert_to_markdown(input, include_locations=resolved_locations)
            if self.include_markdown
            else None
        )

        return DoclingHandoff(
            source=source_display(input),
            schema_version=_optional_string(metadata.get("schema_version")),
            doclang_version=_optional_string(metadata.get("doclang_version")),
            semantic_payload=payload,
            blocks=records_as_dicts(iter_payload_blocks(payload)),
            assets=_list_or_empty(payload.get("assets")),
            losses=_list_or_empty(payload.get("losses")),
            doclang_xml=doclang_xml,
            markdown=markdown,
        )


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
