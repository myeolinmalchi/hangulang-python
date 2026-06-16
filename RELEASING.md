# Releasing & Versioning Policy

이 문서는 `hangulang`(PyPI 패키지) 의 버전 정책과 릴리즈 절차를 정의합니다.
다운스트림(특히 Docling backend) 이 잦은 핀 변경 PR 없이 통합을 유지할 수 있도록,
**계약(contract) 이 깨지지 않는 한 `0.1.x` 패치로만 릴리즈**하는 것을 원칙으로 합니다.

## 핵심 원칙

1. **계약을 `0.1` 라인에 동결한다.** 계약을 깨지 않는 모든 변경(기능 추가, 버그픽스,
   손실 보강, 코어 내부 변경)은 **patch 범프**(`0.1.x`) 로만 나갑니다.
2. **`0.2.0` (minor) 은 계약을 의도적으로 깰 때만** 올립니다.
3. **파이썬 패키지 버전과 Rust 코어 버전을 디커플한다.** 파이썬 버전은 코어 내부
   버전이 아니라 *파이썬이 노출하는 계약* 을 추적합니다. 코어가 내부적으로 `0.2.0`
   이 되어도, 파이썬 대면 계약이 그대로면 파이썬은 `0.1.x` 를 유지합니다.

## 무엇이 "계약" 인가

계약은 **출력 바이트가 아니라 타입/스키마/API 표면** 으로 정의합니다.

| 표면 | 구체 대상 | 계약 |
|------|-----------|------|
| **Python API** | `convert_to_doclang`, `convert_to_markdown`, `convert_to_payload`, `extract_assets`, `ConversionOptions`, `AssetPolicy`, `ExtractedAsset`, 예외 계층(`HangulangError`/`ConversionError`/`ParseError`/`UnsupportedFormatError`) | ✅ |
| **Payload 스키마** | `schema_version`(현재 `hangulang.semantic.v1`) 와 그 필드 구조 | ✅ |
| **CLI** | `hangulang` 엔트리포인트와 플래그 | ✅ |
| 출력 내용(바이트) | DocLang XML / Markdown 의 실제 텍스트 | ❌ (계약 아님) |

## patch(`0.1.x`) vs minor(`0.2.0`) 결정

**`0.1.x` patch 로 나가는 변경 (계약 유지):**

- 버그픽스, 손실 보강, 변환 충실도 개선
- Python API 에 **선택적** 인자/메서드/함수 **추가**
- payload 에 **필드 추가** (소비자는 unknown 필드를 무시하므로 호환)
- 코어 submodule 의 내부 변경으로 파이썬 대면 표면이 바뀌지 않는 경우
- 출력 내용 변화 (예: 이전에 버려지던 텍스트를 구제) — 단 CHANGELOG 에 명시

**`0.2.0` minor 로 올려야 하는 변경 (계약 파기):**

- Python API 의 제거 / 이름변경 / 시그니처 비호환 변경
- payload 필드의 제거 / 이름변경 / 타입·의미 변경
  - 이때 코어의 `PAYLOAD_SCHEMA_VERSION` 도 `hangulang.semantic.v2` 로 동시에 올립니다.
- CLI 플래그의 비호환 변경
- 지원 Python 버전 하한 상향 등 설치 호환성 변경

> 판단이 애매하면 "기존 Docling backend 코드가 수정 없이 계속 동작하는가?" 를 기준으로
> 삼습니다. 동작하면 patch, 깨지면 minor 입니다.

## 다운스트림(Docling) 핀 가이드

Docling backend 는 다음과 같이 핀을 겁니다:

```toml
# >=0.1.0, <0.2.0 — 모든 0.1.x 패치가 PR 없이 자동 유입됩니다.
hangulang ~= 0.1.0
```

`0.2.0` 이 릴리즈될 때만 **딱 한 번** 핀을 넓히는 PR 을 올리면 됩니다.

추가로 런타임 이중 안전장치로, payload 를 소비할 때 `schema_version` 을 단언하세요.
이러면 패키지 버전과 무관하게 스키마 비호환이 들어오면 즉시 잡힙니다.

```python
from hangulang import convert_to_payload

payload = convert_to_payload(data)
assert payload["schema_version"] == "hangulang.semantic.v1"
```

## 릴리즈 절차

버전 소스는 **두 곳** 이며 항상 동일하게 유지합니다:

- `pyproject.toml` → `[project].version`
- `Cargo.toml` → `[package].version`

### 1. 코어(submodule) 동기화 (코어 변경을 반영하는 경우)

`vendor/hangulang` 은 `myeolinmalchi/hangulang` 의 `main` 을 추적하는 git submodule
입니다. 반영할 코어 커밋/태그로 이동합니다.

```bash
git -C vendor/hangulang fetch
git -C vendor/hangulang checkout <core-commit-or-tag>   # 예: v0.2.0 또는 특정 커밋
git add vendor/hangulang
```

### 2. 버전 범프

patch 예시(`0.1.4` → `0.1.5`):

- `pyproject.toml` 의 `version`
- `Cargo.toml` 의 `version`

두 값을 동일하게 수정합니다.

### 3. CHANGELOG 갱신

`CHANGELOG.md` 최상단에 새 항목을 추가합니다. 출력 동작이 바뀐 patch 라면 그 사실을
명시합니다. 동기화한 코어 버전/커밋도 함께 기록합니다.

### 4. 사전 점검 (로컬)

```bash
maturin build
pytest
mypy
ruff check
```

### 5. 태그 → 자동 배포

태그를 푸시하면 `.github/workflows/release.yml` 이 sdist + 멀티 OS abi3 wheel 을
빌드해 **PyPI 로 trusted publishing** 합니다.

```bash
git tag v0.1.5
git push origin v0.1.5
```

> 참고: 파이썬 패키지는 코어를 submodule 째로 정적 빌드해 wheel 에 담으므로,
> 코어 크레이트의 crates.io publish 블로커(rhwp git 의존성)와 무관하게 **PyPI 배포가
> 가능** 합니다.

## `0.2.0` (계약 파기) 릴리즈

위 절차에 더해:

1. 계약 파기 내용을 CHANGELOG 에 **Breaking changes** 절로 분리해 기술합니다.
2. payload 스키마가 바뀌었다면 코어 `PAYLOAD_SCHEMA_VERSION` 을 `...v2` 로 올린 커밋을
   submodule 로 반영합니다.
3. Docling backend 쪽에 핀을 넓히는(`>=0.1,<0.3` 등) 마이그레이션 안내를 남깁니다.
