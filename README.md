# hangulang-python

`hangulang-python`은 **HWP 5.0** 및 **HWPX** 문서(한컴오피스 / 한글)를
Python에서 다루기 위한 `hangulang` Rust core의 Python binding / integration
package입니다.

Rust `hangulang`은 [`rhwp`](https://github.com/edwardkim/rhwp) 파서 코어 위에서
문서를 semantic IR로 낮추고, DocLang XML, semantic payload, Markdown, resource
asset/URI 참조를 생성합니다. `hangulang-python`은 이 엔진을 Python wheel,
Pythonic API, typed error, CLI, optional integration 형태로 제공합니다.

> **상태:** v0.1 alpha — 활발히 개발 중. 현재 native extension은
> `vendor/hangulang` submodule의 Rust `hangulang` 엔진을 연결합니다. 공개 배포
> 전에는 crates.io dependency 전환 여부와 wheel release 정책을 확정해야 합니다.

---

## 왜 만들었나

HWP/HWPX는 한국 공공기관, 법무, 교육, 기업 문서 워크플로에서 여전히 중요합니다.
하지만 Python 문서 처리 생태계에서는 PDF/DOCX에 비해 HWP/HWPX의 구조화된
extraction 도구가 부족합니다.

`hangulang-python`은 이 공백을 다음 역할로 채웁니다:

- **Rust parser/exporter를 재사용합니다.** HWP 파싱을 Python에서 다시 구현하지
  않고, Rust `hangulang`이 검증한 semantic extraction 결과를 Python으로 노출합니다.
- **텍스트가 아니라 구조를 전달합니다.** DocLang XML, Markdown, semantic payload,
  asset reference, layout metadata를 first-class output으로 다룹니다.
- **Python workflow에 맞춥니다.** `dict`, `str`, dataclass option, typed exception,
  CLI entrypoint를 제공합니다.
- **무거운 통합은 선택 사항입니다.** LangChain, Docling adapter는 core conversion
  API와 분리합니다.
- **`rhwp` raw model을 직접 노출하지 않습니다.** 저수준 parser 구조가 아니라,
  downstream pipeline에서 바로 쓰기 쉬운 semantic export 계약을 제공합니다.

## 프로젝트 범위

`hangulang-python`은 Rust `hangulang`의 대체제가 아니라, Python 배포와 통합을 위한
wrapper layer입니다.

| 레이어 | 책임 |
|--------|------|
| `rhwp` | HWP/HWPX 파일 포맷 파싱, 내부 문서 모델, 렌더 트리 제공 |
| `hangulang` Rust core | `rhwp` 모델을 semantic IR로 낮추고 DocLang / payload / Markdown / asset을 생성 |
| `hangulang-python` native extension | PyO3 경계에서 Rust core 호출, JSON/문자열/asset 반환 |
| Python API | Pythonic 함수, 옵션 dataclass, typed exception, asset write 정책 |
| Integrations | LangChain, Docling 등 외부 adapter |

`rhwp-python`이 저수준 parser binding에 가깝다면, `hangulang-python`은 바로 사용할
수 있는 고수준 문서 변환 API를 지향합니다.

---

## 설치

현재는 alpha 개발 상태입니다. Python 3.10+와 Rust toolchain이 필요합니다.

개발 환경:

```bash
git submodule update --init --recursive
uv venv --python 3.12 .venv
uv pip install -e '.[dev]'
```

native extension을 명시적으로 다시 빌드할 때:

```bash
VIRTUAL_ENV=.venv .venv/bin/maturin develop
```

wheel build:

```bash
.venv/bin/maturin build --interpreter .venv/bin/python
```

> **의존성 참고:** Rust core는 `vendor/hangulang` Git submodule로 고정합니다.
> Cargo dependency는 package 이름 `hangulang`을 `hangulang-engine` alias로
> 가져옵니다.
>
> ```toml
> hangulang-engine = { package = "hangulang", path = "vendor/hangulang", features = ["serde"] }
> ```

---

## 빠른 시작

### Python API

```python
from hangulang import convert_to_doclang, convert_to_markdown, convert_to_payload

xml = convert_to_doclang("document.hwp")
markdown = convert_to_markdown("document.hwpx")
payload = convert_to_payload("document.hwp", include_locations=True)
```

입력은 파일 경로 또는 bytes를 받을 수 있습니다:

```python
from pathlib import Path
from hangulang import convert_to_payload

data = Path("document.hwp").read_bytes()
payload = convert_to_payload(data)
```

옵션이 늘어나는 경우 `ConversionOptions`를 사용할 수 있습니다:

```python
from hangulang import ConversionOptions, convert_to_doclang

options = ConversionOptions(include_locations=True)
xml = convert_to_doclang("document.hwp", options)
```

### 출력 API

| API | 출력 | 비고 |
|-----|------|------|
| `convert_to_doclang` | `str` | DocLang v0.6 XML |
| `convert_to_markdown` | `str` | 같은 Rust semantic IR에서 직접 생성 |
| `convert_to_payload` | `dict` | stable semantic payload JSON을 Python dict로 반환 |
| `extract_assets` | `list[ExtractedAsset]` | embedded image/resource asset 추출 또는 참조 |

### Asset 처리

이미지는 Rust core의 resource policy를 통해 data URI, asset file, URI prefix로 다룰
수 있습니다.

```python
from hangulang import AssetPolicy, extract_assets

assets = extract_assets(
    "document.hwp",
    asset_policy=AssetPolicy.WRITE,
    output_dir="assets",
)

for asset in assets:
    print(asset.path, asset.mime_type, asset.uri)
```

---

## CLI

Python package는 `hangulang` console script를 제공합니다.

```bash
hangulang convert document.hwp --format doclang
hangulang convert document.hwp --format markdown
hangulang convert document.hwp --format payload --locations
hangulang assets document.hwp --out assets/
```

CLI는 별도 변환 구현을 갖지 않습니다. public Python API를 얇게 호출하므로, API와
CLI의 동작은 같은 Rust core를 공유합니다.

---

## 옵션과 오류

### ConversionOptions

```python
from hangulang import AssetPolicy, ConversionOptions

options = ConversionOptions(
    include_locations=True,
    asset_policy=AssetPolicy.INLINE,
    report_losses=False,
)
```

| 옵션 | 기본값 | 의미 |
|------|--------|------|
| `include_locations` | `False` | layout location / bbox metadata 요청 |
| `bbox_resolution` | `"none"` | Python API용 bbox 해상도 의도 표현 |
| `asset_policy` | `AssetPolicy.INLINE` | inline, write, URI reference 등 asset 처리 방식 |
| `asset_output_dir` | `None` | asset write 정책에서 사용할 출력 디렉터리 |
| `uri_prefix` | `None` | downstream storage용 asset URI prefix |
| `report_losses` | `False` | loss reporting API 확장용 예약 필드 |

### 예외

| 예외 | 의미 |
|------|------|
| `HangulangError` | 모든 package error의 base class |
| `UnsupportedFormatError` | 지원하지 않는 입력 형식, 암호화/배포용 문서 등 |
| `ParseError` | 파일 읽기 또는 parser 단계 실패 |
| `ConversionError` | XML/JSON/asset 직렬화 등 변환 단계 실패 |

---

## Optional integrations

Core package는 LangChain이나 Docling을 필수 의존성으로 설치하지 않습니다.

| 모듈 | 상태 | 역할 |
|------|------|------|
| `hangulang.integrations.langchain` | implemented | block/document 단위 LangChain `Document` loader |
| `hangulang.integrations.docling` | implemented | Docling handoff / payload / DocLang / Markdown adapter |

LangChain integration은 `langchain-core>=1.0,<2.0`을 기준으로 분리합니다:

```bash
uv pip install -e '.[langchain]'
```

LangChain loader는 기본적으로 semantic payload의 텍스트 블록을 각각 하나의
`Document`로 반환하고, `source`, `schema_version`, `doclang_version`, `block_id`,
`block_kind`, `page_number`, `bbox`, resource metadata를 가능한 범위에서 보존합니다.

```python
from hangulang.integrations.langchain import HangulangLoader

docs = HangulangLoader("document.hwp", include_locations=True).load()
```

문서 전체를 하나의 `Document`로 받아야 하는 경우:

```python
docs = HangulangLoader("document.hwp", mode="document").load()
```

Docling adapter는 특정 Docling runtime class에 hard dependency를 두지 않고,
framework-neutral handoff dict를 반환합니다. 필요하면 payload, DocLang XML,
Markdown만 따로 받을 수 있습니다.

```python
from hangulang.integrations.docling import HangulangDoclingAdapter

adapter = HangulangDoclingAdapter(include_locations=True)
handoff = adapter.convert("document.hwp", format="handoff")
xml = adapter.convert("document.hwp", format="doclang")
```

---

## 아키텍처

```text
 HWP 5.0 (.hwp) ─┐
                 ├─► hangulang Rust core ─┬─► DocLang XML ───────► Python str
 HWPX (.hwpx) ──┘                         ├─► semantic payload ─► Python dict
                                           ├─► Markdown ─────────► Python str
                                           └─► resource assets ──► ExtractedAsset

 Python API / CLI ─► PyO3 native extension ─► Rust convert APIs
```

Python layer의 원칙:

- parser logic은 Rust에 둡니다.
- Python은 API 안정성, packaging, typing, 오류 매핑, integration을 담당합니다.
- heavy downstream dependency는 optional extra 또는 별도 adapter에 둡니다.
- public API는 procedural function을 먼저 안정화하고, 반복 변환/상태가 필요해질 때
  object-oriented API를 추가합니다.

---

## 개발

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy python/hangulang
cargo test
.venv/bin/maturin build --interpreter .venv/bin/python
```

현재 Python 테스트는 `vendor/hangulang/tests/fixtures`의 Rust `hangulang` fixture
corpus를 재사용합니다.

Phase별 구현 계획은 [`docs/implementation-plan.md`](docs/implementation-plan.md)에
정리되어 있습니다.

---

## 로드맵

- `hangulang` Rust submodule을 CI와 wheel build 흐름에 포함.
- CI에서 Python test, Rust extension build, type check, wheel smoke test 실행.
- `convert_to_payload` loss reporting과 Python option model 정교화.
- asset URI/write 정책의 downstream contract 확정.
- LangChain loader chunking strategy와 metadata schema 안정화.
- Docling runtime plugin contract가 확정되면 handoff adapter를 공식 backend로 연결.
- macOS, Linux, Windows wheel build matrix 구성.
- `hangulang` / `rhwp` crates.io publish 이후 PyPI 안정 배포.

---

## 라이선스

MIT. 자세한 내용은 [`LICENSE`](LICENSE)를 참고하세요.

본 프로젝트는 독립적인 오픈소스 프로젝트입니다. HWP/HWPX는 한글과컴퓨터(Hancom
Inc.)의 포맷이며, 본 프로젝트는 한컴과 제휴 관계가 없습니다. DocLang은 LF AI &
Data Foundation의 프로젝트입니다. `rhwp`는 © Edward Kim (MIT)입니다.
