from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from hangulang import (
    AssetPolicy,
    HangulangError,
    convert_to_doclang,
    convert_to_markdown,
    convert_to_payload,
    extract_assets,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            _run_convert(args)
        elif args.command == "assets":
            _run_assets(args)
        else:  # pragma: no cover - argparse prevents this.
            parser.error(f"unknown command {args.command}")
    except HangulangError as exc:
        print(f"hangulang: {exc}", file=sys.stderr)
        return 1

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hangulang")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="convert a document")
    convert.add_argument("input", help="input .hwp or .hwpx file")
    convert.add_argument(
        "--format",
        choices=["doclang", "markdown", "payload"],
        required=True,
        help="output format",
    )
    convert.add_argument(
        "--locations",
        action="store_true",
        help="include location and bbox metadata when available",
    )
    convert.add_argument("--out", help="write output to this file")

    assets = subparsers.add_parser("assets", help="extract embedded assets")
    assets.add_argument("input", help="input .hwp or .hwpx file")
    assets.add_argument("--out", required=True, help="asset output directory")
    assets.add_argument(
        "--uri-prefix",
        help="URI prefix to report for downstream asset storage systems",
    )

    return parser


def _run_convert(args: argparse.Namespace) -> None:
    if args.format == "doclang":
        output = convert_to_doclang(args.input, include_locations=args.locations)
    elif args.format == "markdown":
        output = convert_to_markdown(args.input, include_locations=args.locations)
    else:
        payload = convert_to_payload(args.input, include_locations=args.locations)
        output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    _write_or_print(output, args.out)


def _run_assets(args: argparse.Namespace) -> None:
    assets = extract_assets(
        args.input,
        asset_policy=AssetPolicy.WRITE,
        output_dir=args.out,
        uri_prefix=args.uri_prefix,
    )
    output = json.dumps(
        [asdict(asset) for asset in assets],
        ensure_ascii=False,
        indent=2,
    )
    _write_or_print(output + "\n", None)


def _write_or_print(output: str, output_path: str | None) -> None:
    if output_path is None:
        print(output, end="")
        return

    Path(output_path).write_text(output, encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
