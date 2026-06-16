# Changelog

## 0.1.1 - 2026-06-16

- Sync the vendored `hangulang` core to its v2 conversion-fidelity work
  (commit `1d36315`). No Python API or payload-schema changes — additive only,
  so `schema_version` stays `hangulang.semantic.v1`.
- Hyperlinks now surface as `kind: "href"` inline nodes with a `uri` field in the
  semantic payload (and `<href>` in DocLang XML, `[anchor](uri)` in Markdown).
- In-text flow objects (tables, pictures, formulas) are positioned at their true
  character offset within ordinary paragraphs.
- Wider EqEdit→LaTeX symbol coverage; layout-failure and table-cell-collision
  diagnostics surface through the loss report; OTSL grid size is capped.

## 0.1.0 - 2026-06-15

- Publish the initial Python/Rust package release for HWP/HWPX conversion.
- Add Python APIs for DocLang XML, Markdown, semantic payload, and asset extraction.
- Add typed options/errors, CLI entrypoint, and optional LangChain/Docling handoff integrations.
- Build abi3 wheels through the release workflow and track the vendored `hangulang` submodule's `main` branch.
