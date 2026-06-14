from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from os import PathLike
from typing import Any

from hangulang._api import DocumentInput

JsonMap = dict[str, Any]


@dataclass(frozen=True, slots=True)
class PayloadBlockRecord:
    text: str
    metadata: JsonMap


def source_display(input: DocumentInput) -> str:
    if isinstance(input, bytes):
        return "<bytes>"
    if isinstance(input, PathLike):
        return str(input)
    return input


def payload_metadata(input: DocumentInput, payload: JsonMap) -> JsonMap:
    sections = payload.get("sections")
    assets = payload.get("assets")
    losses = payload.get("losses")
    return {
        "source": source_display(input),
        "schema_version": payload.get("schema_version"),
        "doclang_version": payload.get("doclang_version"),
        "section_count": len(sections) if isinstance(sections, list) else 0,
        "asset_count": len(assets) if isinstance(assets, list) else 0,
        "loss_count": len(losses) if isinstance(losses, list) else 0,
    }


def document_text(payload: JsonMap) -> str:
    return "\n\n".join(record.text for record in iter_payload_blocks(payload))


def iter_payload_blocks(payload: JsonMap) -> Iterable[PayloadBlockRecord]:
    root = {
        "schema_version": payload.get("schema_version"),
        "doclang_version": payload.get("doclang_version"),
        "asset_count": _list_len(payload.get("assets")),
        "loss_count": _list_len(payload.get("losses")),
    }
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_index = _int_or_none(section.get("index"))
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            continue
        yield from _walk_blocks(
            blocks,
            root=root,
            section_index=section_index,
            parent_id=None,
            context={},
        )


def records_as_dicts(records: Iterable[PayloadBlockRecord]) -> list[JsonMap]:
    return [
        {
            "text": record.text,
            "metadata": record.metadata,
        }
        for record in records
    ]


def _walk_blocks(
    blocks: list[Any],
    *,
    root: JsonMap,
    section_index: int | None,
    parent_id: str | None,
    context: JsonMap,
) -> Iterable[PayloadBlockRecord]:
    for block_index, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue

        metadata = _block_metadata(
            root,
            section_index=section_index,
            block_index=block_index,
            block=block,
            parent_id=parent_id,
            context=context,
        )
        text = _block_text(block).strip()
        if text:
            yield PayloadBlockRecord(text=text, metadata=metadata)

        block_id = _string_or_none(block.get("id")) or parent_id
        children = block.get("children")
        if isinstance(children, list):
            yield from _walk_blocks(
                children,
                root=root,
                section_index=section_index,
                parent_id=block_id,
                context={**context, "container": "children"},
            )

        items = block.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_blocks = item.get("blocks")
                if isinstance(item_blocks, list):
                    item_index = _int_or_none(item.get("index"))
                    yield from _walk_blocks(
                        item_blocks,
                        root=root,
                        section_index=section_index,
                        parent_id=block_id,
                        context={
                            **context,
                            "container": "list_item",
                            "list_item_index": item_index,
                        },
                    )

        table = block.get("table")
        if isinstance(table, dict):
            cells = table.get("cells")
            if isinstance(cells, list):
                for cell in cells:
                    if not isinstance(cell, dict):
                        continue
                    cell_blocks = cell.get("blocks")
                    if isinstance(cell_blocks, list):
                        yield from _walk_blocks(
                            cell_blocks,
                            root=root,
                            section_index=section_index,
                            parent_id=block_id,
                            context={
                                **context,
                                "container": "table_cell",
                                "table_row": _int_or_none(cell.get("row")),
                                "table_col": _int_or_none(cell.get("col")),
                                "row_span": _int_or_none(cell.get("row_span")),
                                "col_span": _int_or_none(cell.get("col_span")),
                            },
                        )


def _block_metadata(
    root: JsonMap,
    *,
    section_index: int | None,
    block_index: int,
    block: JsonMap,
    parent_id: str | None,
    context: JsonMap,
) -> JsonMap:
    metadata: JsonMap = {
        **root,
        **{key: value for key, value in context.items() if value is not None},
        "section_index": section_index,
        "block_index": block_index,
        "block_id": block.get("id"),
        "block_kind": block.get("kind"),
    }
    if parent_id is not None:
        metadata["parent_id"] = parent_id

    _merge_location(metadata, block.get("location"))
    _merge_optional(metadata, "heading_level", block.get("level"))
    _merge_optional(metadata, "ordered", block.get("ordered"))
    _merge_optional(metadata, "thread_id", block.get("thread_id"))
    _merge_optional(metadata, "custom_namespace", block.get("custom_namespace"))
    _merge_resource(metadata, block.get("resource"))
    _merge_formula(metadata, block.get("formula"))
    _merge_table(metadata, block.get("table"))
    return metadata


def _block_text(block: JsonMap) -> str:
    text = _string_or_none(block.get("text"))
    if text:
        return text

    formula = block.get("formula")
    if isinstance(formula, dict):
        latex = _string_or_none(formula.get("latex"))
        raw = _string_or_none(formula.get("raw_eqedit"))
        return latex or raw or ""

    resource = block.get("resource")
    if isinstance(resource, dict):
        return _string_or_none(resource.get("uri")) or ""

    inlines = block.get("inlines")
    if isinstance(inlines, list):
        return "".join(_inline_text(inline) for inline in inlines)

    return ""


def _inline_text(inline: Any) -> str:
    if not isinstance(inline, dict):
        return ""
    text = _string_or_none(inline.get("text")) or ""
    children = inline.get("children")
    if isinstance(children, list):
        text += "".join(_inline_text(child) for child in children)
    return text


def _merge_location(metadata: JsonMap, location: Any) -> None:
    if not isinstance(location, dict):
        return
    _merge_optional(metadata, "location_status", location.get("status"))
    page = _int_or_none(location.get("page"))
    if page is not None:
        metadata["page_index"] = page
        metadata["page_number"] = page + 1
    bbox = location.get("bbox")
    if isinstance(bbox, dict):
        metadata["bbox"] = bbox
    _merge_optional(metadata, "bbox_resolution", location.get("resolution"))
    _merge_optional(metadata, "location_reason", location.get("reason"))


def _merge_resource(metadata: JsonMap, resource: Any) -> None:
    if not isinstance(resource, dict):
        return
    _merge_optional(metadata, "resource_uri", resource.get("uri"))
    _merge_optional(metadata, "resource_mime", resource.get("mime"))
    _merge_optional(metadata, "resource_asset_path", resource.get("asset_path"))


def _merge_formula(metadata: JsonMap, formula: Any) -> None:
    if not isinstance(formula, dict):
        return
    _merge_optional(metadata, "formula_latex", formula.get("latex"))
    _merge_optional(metadata, "formula_raw_eqedit", formula.get("raw_eqedit"))


def _merge_table(metadata: JsonMap, table: Any) -> None:
    if not isinstance(table, dict):
        return
    _merge_optional(metadata, "table_rows", table.get("rows"))
    _merge_optional(metadata, "table_cols", table.get("cols"))
    _merge_optional(metadata, "table_caption", table.get("caption"))


def _merge_optional(metadata: JsonMap, key: str, value: Any) -> None:
    if value is not None:
        metadata[key] = value


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0
