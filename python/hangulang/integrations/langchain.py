from __future__ import annotations

from typing import Any, Literal

from hangulang import convert_to_payload
from hangulang._api import DocumentInput
from hangulang.integrations._payload import (
    document_text,
    iter_payload_blocks,
    payload_metadata,
)

LoadMode = Literal["blocks", "document"]


class HangulangLoader:
    """LangChain loader that emits Documents from Hangulang semantic payloads."""

    def __init__(
        self,
        path: DocumentInput,
        *,
        include_locations: bool = True,
        mode: LoadMode = "blocks",
        include_payload: bool = False,
    ) -> None:
        self.path = path
        self.include_locations = include_locations
        self.mode = mode
        self.include_payload = include_payload

    def load(self) -> list[Any]:
        Document = _document_type()
        payload = convert_to_payload(
            self.path,
            include_locations=self.include_locations,
        )

        if self.mode == "document":
            metadata = payload_metadata(self.path, payload)
            if self.include_payload:
                metadata["hangulang_payload"] = payload
            return [
                Document(
                    page_content=document_text(payload),
                    metadata=metadata,
                )
            ]

        if self.mode != "blocks":
            raise ValueError("mode must be 'blocks' or 'document'")

        documents = []
        for record in iter_payload_blocks(payload):
            metadata = {
                "source": _source_display(self.path),
                **record.metadata,
            }
            if self.include_payload:
                metadata["hangulang_payload"] = payload
            documents.append(
                Document(
                    page_content=record.text,
                    metadata=metadata,
                )
            )
        return documents


def _document_type() -> Any:
    try:
        from langchain_core.documents import Document
    except ImportError as exc:
        raise ImportError(
            "LangChain support requires `hangulang[langchain]`."
        ) from exc

    return Document


def _source_display(path: DocumentInput) -> str:
    from hangulang.integrations._payload import source_display

    return source_display(path)
