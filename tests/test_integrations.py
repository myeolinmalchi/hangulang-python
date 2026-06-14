from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("hangulang._native")

from hangulang.integrations.docling import (  # noqa: E402
    DoclingHandoff,
    HangulangDoclingAdapter,
)
from hangulang.integrations.langchain import HangulangLoader  # noqa: E402

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "vendor" / "hangulang" / "tests" / "fixtures"
)


def fixture_path(relative: str) -> Path:
    path = FIXTURE_ROOT / relative
    if not path.exists():
        pytest.skip(f"fixture not available: {path}")
    return path


def test_docling_adapter_returns_handoff_with_blocks_and_doclang(tmp_path):
    sample = fixture_path("paragraphs/para-001.hwp")

    handoff = HangulangDoclingAdapter().to_handoff(sample)

    assert isinstance(handoff, DoclingHandoff)
    assert handoff.schema_version == "hangulang.semantic.v1"
    assert handoff.doclang_version == "0.6"
    assert handoff.doclang_xml is not None
    assert handoff.doclang_xml.startswith("<doclang")
    assert handoff.blocks
    assert handoff.blocks[0]["text"]
    assert handoff.blocks[0]["metadata"]["block_id"]


def test_docling_adapter_convert_supports_multiple_formats(tmp_path):
    sample = fixture_path("pairs/para-001.hwpx")
    adapter = HangulangDoclingAdapter(include_doclang=False)

    result = adapter.convert(sample, format="handoff")

    assert isinstance(result, dict)
    assert result["schema_version"] == "hangulang.semantic.v1"
    assert result["blocks"]
    assert adapter.convert(sample, format="doclang").startswith("<doclang")
    assert adapter.convert(sample, format="markdown").strip()
    payload = adapter.convert(sample, format="payload")
    assert isinstance(payload, dict)
    assert payload["schema_version"] == "hangulang.semantic.v1"


def test_langchain_loader_emits_block_documents_with_metadata(tmp_path):
    pytest.importorskip("langchain_core.documents")
    sample = fixture_path("paragraphs/para-001.hwp")

    documents = HangulangLoader(sample, include_locations=True).load()

    assert documents
    assert documents[0].page_content
    assert documents[0].metadata["source"] == str(sample)
    assert documents[0].metadata["schema_version"] == "hangulang.semantic.v1"
    assert documents[0].metadata["doclang_version"] == "0.6"
    assert documents[0].metadata["block_id"]
    assert "page_number" in documents[0].metadata
    assert "bbox" in documents[0].metadata


def test_langchain_loader_document_mode(tmp_path):
    pytest.importorskip("langchain_core.documents")
    sample = fixture_path("pairs/para-001.hwpx")

    documents = HangulangLoader(sample, mode="document").load()

    assert len(documents) == 1
    assert documents[0].page_content
    assert documents[0].metadata["section_count"] >= 1
