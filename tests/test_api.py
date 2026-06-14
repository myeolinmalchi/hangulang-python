from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("hangulang._native")

from hangulang import (  # noqa: E402
    AssetPolicy,
    ConversionOptions,
    UnsupportedFormatError,
    convert_to_doclang,
    convert_to_markdown,
    convert_to_payload,
    extract_assets,
)

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "vendor" / "hangulang" / "tests" / "fixtures"
)


def fixture_path(relative: str) -> Path:
    path = FIXTURE_ROOT / relative
    if not path.exists():
        pytest.skip(f"fixture not available: {path}")
    return path


def test_convert_to_doclang_accepts_path(tmp_path):
    sample = fixture_path("paragraphs/para-001.hwp")

    xml = convert_to_doclang(sample)

    assert "<doclang" in xml
    assert 'version="0.6"' in xml


def test_convert_to_markdown_accepts_bytes():
    markdown = convert_to_markdown(fixture_path("pairs/para-001.hwpx").read_bytes())

    assert markdown.strip()
    assert "bootstrap" not in markdown


def test_convert_to_payload_accepts_location_option():
    payload = convert_to_payload(
        fixture_path("mixed/exam-social.hwp"),
        include_locations=True,
    )

    assert payload["schema_version"] == "hangulang.semantic.v1"
    assert payload["doclang_version"] == "0.6"
    assert payload["sections"]


def test_conversion_options_are_accepted(tmp_path):
    sample = fixture_path("paragraphs/para-001.hwp")
    options = ConversionOptions(include_locations=True)

    xml = convert_to_doclang(sample, options)

    assert "<doclang" in xml
    assert "<location" in xml


def test_unsupported_path_extension_maps_to_custom_error(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_text("not hwp", encoding="utf-8")

    with pytest.raises(UnsupportedFormatError):
        convert_to_doclang(sample)


def test_extract_assets_write_policy_creates_output_directory(tmp_path):
    sample = fixture_path("pictures/hwp-img-001.hwp")
    output_dir = tmp_path / "assets"

    assets = extract_assets(
        sample,
        asset_policy=AssetPolicy.WRITE,
        output_dir=output_dir,
    )

    assert assets
    assert assets[0].path
    assert (output_dir / assets[0].path).is_file()
    assert output_dir.is_dir()
