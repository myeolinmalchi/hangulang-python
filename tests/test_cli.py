from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("hangulang._native")

from hangulang._cli import main  # noqa: E402

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "vendor" / "hangulang" / "tests" / "fixtures"
)


def fixture_path(relative: str) -> Path:
    path = FIXTURE_ROOT / relative
    if not path.exists():
        pytest.skip(f"fixture not available: {path}")
    return path


def test_cli_convert_payload_writes_json_to_stdout(tmp_path, capsys):
    sample = fixture_path("pairs/para-001.hwpx")

    exit_code = main(
        ["convert", str(sample), "--format", "payload", "--locations"],
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["schema_version"] == "hangulang.semantic.v1"
    assert payload["sections"]


def test_cli_assets_creates_output_directory(tmp_path, capsys):
    sample = fixture_path("pictures/hwp-img-001.hwp")
    output_dir = tmp_path / "assets"

    exit_code = main(["assets", str(sample), "--out", str(output_dir)])

    captured = capsys.readouterr()
    assets = json.loads(captured.out)
    assert exit_code == 0
    assert assets
    assert (output_dir / assets[0]["path"]).is_file()
    assert output_dir.is_dir()
