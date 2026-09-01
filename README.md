# 공제정보망 프로세스 마이닝 플랫폼 개발 패키지

## 1. 목적
이 저장소는 공제정보망의 대규모 메서드/변수 로그(초기 목표 2,000만 건 이상)를 로컬 환경에서 분석하여 업무 프로세스를 발견하고, 병목·재작업·이상경로·업무 변형(variant)·처리시간을 시각적으로 분석하는 프로세스 마이닝 프로그램을 개발하기 위한 설계·지침·PRD 패키지다.

핵심 원칙은 **Local-first / SQL-first / AI-assisted** 이다.

- 원천 데이터는 원칙적으로 외부 AI 서비스에 업로드하지 않는다.
- 대용량 계산은 DuckDB가 수행한다.
- 저장 포맷은 Parquet을 기본으로 한다.
- AI는 원천 로그 전체를 읽는 엔진이 아니라, 코드 생성·SQL 작성·결과 해석·문서화 보조 역할을 수행한다.
- 1단계 MVP의 프로세스 마이닝 핵심 지표는 DuckDB SQL로 구현한다.
- PM4Py는 라이선스 검토 후 2단계 선택 모듈로 도입한다.

## 2. 권장 기술 스택

### 데이터 계층
- DuckDB: 로컬 분석 DB 및 쿼리 엔진
- Apache Parquet: 대용량 컬럼형 파일 저장
- PyArrow 또는 Polars: ETL 보조

### 백엔드
- Python 3.12+ 권장
- FastAPI
- Pydantic
- DuckDB Python client
- 선택: Polars, PyArrow

### 프론트엔드
- React + TypeScript + Vite
- Apache ECharts: KPI/분포/시계열/히트맵
- Cytoscape.js: 프로세스 네트워크 그래프
- TanStack Query: API 상태 관리
- 선택: TanStack Table

### 프로세스 마이닝
1. MVP: 자체 SQL 기반 DFG/Variant/Throughput/Rework/Bottleneck 엔진
2. 확장: PM4Py Adapter (라이선스 검토 후)

## 3. 프로젝트 성공의 가장 중요한 전제
메서드 로그를 곧바로 프로세스 마이닝 이벤트로 간주하지 않는다. 먼저 아래 세 가지를 정의해야 한다.

1. `case_id`: 하나의 업무 건을 묶는 키
2. `activity`: 기술 메서드를 업무 활동으로 변환한 명칭
3. `event_timestamp`: 활동 순서를 정렬할 신뢰 가능한 시각

예: `ClaimService.saveClaim()` 자체가 분석상의 activity가 아니라, 매핑 규칙을 통해 `공제금 청구 접수`로 변환될 수 있어야 한다.

## 4. 권장 개발 순서

### Phase 0 — 데이터 적합성 검증
- 원천 필드 사전 작성
- 개인정보/민감정보 식별
- case key 후보 탐색
- timestamp 품질 확인
- method → business activity 매핑 가능성 검증
- 100만~500만 건 샘플 벤치마크

### Phase 1 — 데이터 엔진
- 사용자가 내려받은 CSV/Parquet → localhost upload → normalized Parquet 변환
- 정규화 이벤트 로그 생성
- DuckDB 기반 지표 집계
- 품질검증 리포트

### Phase 2 — 분석 UI
- 프로세스 맵
- Variant Explorer
- 병목/체류시간
- 재작업
- Case Explorer
- 필터

### Phase 3 — 고급 프로세스 마이닝
- Conformance Checking
- Petri Net / BPMN 연계
- 이상경로 탐지
- 비교 분석

### Phase 4 — AI 분석 보조
- 자연어 질의 → 승인 가능한 SQL 초안
- 분석 결과 요약
- 이상 구간 설명
- 보고서 초안 생성

## 5. 파일 안내

| 파일 | 역할 |
|---|---|
| `AGENTS.md` | Codex 등 AI 코딩 에이전트의 최상위 개발 지침 |
| `CLAUDE.md` | Claude Code 사용 시 프로젝트 지침 |
| `PRD.md` | 실제 개발을 위한 상세 제품 요구사항 문서 |
| `ARCHITECTURE.md` | 전체 시스템 아키텍처와 컴포넌트 책임 |
| `DATA_MODEL.md` | 이벤트 로그, 원천 로그, 매핑 및 집계 모델 |
| `PROCESS_MINING_SPEC.md` | 프로세스 마이닝 계산 정의 |
| `SECURITY.md` | 데이터 보안·비식별화·AI 사용 통제 |
| `PERFORMANCE.md` | 2,000만+ 이벤트 성능 전략 및 벤치마크 |
| `UI_UX_SPEC.md` | 화면/상호작용/시각화 요구사항 |
| `TEST_STRATEGY.md` | 단위/통합/데이터/성능 테스트 전략 |
| `ROADMAP.md` | 단계별 구축 로드맵 |
| `DEVELOPMENT_WORKFLOW.md` | Git, 브랜치, 작업 단위, AI 작업 절차 |
| `LICENSE_POLICY.md` | OSS 및 PM4Py 라이선스 정책 |
| `INITIAL_CODEX_PROMPT.md` | Codex에 첫 개발 작업을 지시하는 시작 프롬프트 |
| `OPEN_SOURCE_REFERENCE_GUIDE.md` | PM4Py/Cytoscape/NHS/bpmn-js 등 OSS 조사·라이선스·AI 적용 지침 |
| `scripts/fetch_references.ps1` | Windows에서 공개 OSS reference를 `_references/`로 불러오는 스크립트 |
| `templates/REFERENCE_ADOPTION_PROMPT.md` | Codex/Claude가 외부 소스를 안전하게 분석·적용하기 위한 프롬프트 |
| `sql/*.sql` | 초기 DuckDB 스키마와 분석 SQL 템플릿 |
| `config/app.example.yaml` | 실행 설정 예시 |

## 6. 반드시 지켜야 할 금지사항
- 실제 원천 로그를 Git에 커밋하지 않는다.
- 실제 개인정보 또는 업무식별키를 AI 채팅에 붙여넣지 않는다.
- 개발 편의를 위해 case_id 정의를 임의로 확정하지 않는다.
- 모든 2천만 건을 Pandas DataFrame 하나로 올리는 구현을 기본 경로로 삼지 않는다.
- UI에서 원천 이벤트를 무제한 반환하는 API를 만들지 않는다.
- PM4Py를 법무/라이선스 검토 없이 제품의 필수 의존성으로 확정하지 않는다.

## 7. 참고한 현재 공식 자료
- DuckDB Performance / larger-than-memory: https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads
- DuckDB Parquet query: https://duckdb.org/docs/current/guides/file_formats/query_parquet
- DuckDB Environment: https://duckdb.org/docs/current/guides/performance/environment
- PM4Py repository/license: https://github.com/process-intelligence-solutions/pm4py
- OpenAI Codex AGENTS.md 안내: https://openai.com/index/introducing-codex/
- OpenAI Harness Engineering: https://openai.com/index/harness-engineering/

## 8. Phase 0/1 skeleton 실행

현재 skeleton은 합성 데이터만 사용하며 다음 vertical slice를 제공한다.

```text
합성 Event Log → DuckDB DFG/Overview → FastAPI → React Overview/Cytoscape Process Map
```

### Backend 설치 및 실행 (PowerShell)

저장소 루트에서 실행한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `http://127.0.0.1:8000/health`
- Overview: `http://127.0.0.1:8000/api/overview`
- DFG: `http://127.0.0.1:8000/api/dfg`
- API 문서: `http://127.0.0.1:8000/docs`

기본 설정은 `config/app.example.yaml`에서 읽는다. 로컬 설정 파일을 사용하려면
`config/app.yaml`을 만들고 다음 환경 변수를 지정한다. `config/app.yaml`은 Git에서 제외된다.

```powershell
$env:PROCESS_MINING_CONFIG = "config/app.yaml"
```

### 합성 Event Log 생성

generator는 이벤트를 한 행씩 기록하므로 전체 결과를 Python 메모리에 적재하지 않는다. 출력은
기본적으로 Git 제외 경로인 `data/synthetic/event_log.csv`에 저장된다.

```powershell
python scripts/generate_synthetic_events.py --cases 1000
```

### Frontend 설치 및 실행

새 터미널에서 다음을 실행한다.

```powershell
cd frontend
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`을 열면 Vite proxy를 통해 로컬 FastAPI를 조회한다.
좌측 `Process Map`에서 Cytoscape.js 그래프, minimum transition frequency, node/edge 상세,
pan/zoom, fit/reset 및 transition table을 확인할 수 있다.

### DFG benchmark harness

benchmark는 합성 CSV를 streaming 생성하고 DuckDB로 적재한 뒤 동일한 DFG SQL을 측정한다.
`--events`에는 임의의 양수를 사용할 수 있으며 권장 규모는 100K, 1M, 5M, 20M이다.

```powershell
python scripts/benchmark_dfg.py --events 100000
python scripts/benchmark_dfg.py --events 1000000 --work-dir data/benchmarks/1m
```

`--work-dir`을 생략하면 CSV와 DuckDB는 임시 디렉터리에서 실행 후 제거된다. 2026-08-31
개발 PC의 100K smoke benchmark는 생성 5.315초, 적재 0.409초, DFG 0.175초였다.
Python peak memory 값은 `tracemalloc` 기준으로 DuckDB native memory를 포함하지 않는다.
1M/5M/20M은 이번 단계에서 실행하지 않았다.

### 검증 명령

```powershell
pytest
ruff check backend scripts
mypy
cd frontend
npm run lint
npm run test
npm run typecheck
npm run build
```

Golden fixture는 `backend/tests/fixtures/golden_event_log.json`에 있는 완전 합성 3개 case
(`A-B-C`, `A-B-B-C`, `A-D-C`)이며, DFG 빈도·case share·전이시간 백분위와 overview를 검증한다.

## 9. Local File Ingestion vertical slice

현재 primary ingestion은 운영 DB 연결이 아니라 **사용자가 내려받은 로컬 CSV/CSV.GZ/Parquet의
Browser Upload**다. 모든 처리는 localhost 안에서 끝나며 실제 Dataset을 외부 서비스로 전송하지
않는다.

```text
Local file → chunked staging → DuckDB direct scan → fast profile/preview
→ versioned Event Log mapping → validation/quarantine → normalized Parquet
→ dataset-aware Overview/DFG/Process Map
```

Frontend의 `Datasets` 메뉴에서 upload, profile, 최대 200행 preview, case/activity/timestamp mapping,
timestamp parse preview, data-quality 확인과 READY Dataset 분석 이동을 한 workspace에서 수행한다.
API의 핵심 경로는 다음과 같다.

- `POST /api/datasets/upload`
- `GET /api/datasets`, `GET /api/datasets/{dataset_id}/profile`
- `GET /api/datasets/{dataset_id}/preview?limit=100` (서버 최대 200)
- `POST /api/datasets/{dataset_id}/mappings`
- `POST /api/datasets/{dataset_id}/normalize`
- `GET /api/datasets/{dataset_id}/quality`
- `DELETE /api/datasets/{dataset_id}`
- `GET /api/overview?dataset_id=...`, `GET /api/dfg?dataset_id=...`

업로드는 1 MiB chunk로 UUID staging 디렉터리에 복사하며 SHA-256을 streaming 계산한다. DuckDB의
CSV/Parquet scan과 SQL/COPY가 profile, validation, ZSTD Parquet 정규화를 수행하므로 전체 row를
Pandas, Python list 또는 JSON으로 만들지 않는다. 원본은 immutable이며 새 mapping은 `events-vN`
산출물을 만든다. 잘못된 행은 원본 값을 복제하지 않고 source row number와 technical failure code만
quarantine에 남긴다. 유효 행이 하나 이상이면 일부 격리가 있어도 `READY`, 유효 행이 없으면
`FAILED_NO_VALID_EVENTS` 정책을 사용한다.

대용량 source는 원래 다운로드 파일, staging copy, normalized/quarantine Parquet 및 DuckDB spill이
동시에 필요하다. 알려진 upload 크기에 대해 staging 볼륨 여유 공간을 source 크기의 2.5배 이상으로
사전 확인하지만, 운영자는 실제 column 폭과 spill을 고려해 더 큰 여유를 확보해야 한다.

### Ingestion benchmark

```powershell
$env:PYTHONPATH = "backend"
python -m scripts.benchmark_ingestion --events 100000
python -m scripts.benchmark_ingestion --events 1000000
# 장시간 수동 실행만 허용
python -m scripts.benchmark_ingestion --events 5000000 --work-dir data/benchmarks/5m
python -m scripts.benchmark_ingestion --events 20000000 --work-dir data/benchmarks/20m
```

`--work-dir`을 생략하면 모든 benchmark artifact는 종료 후 제거된다. `tracemalloc` 수치는 Python
allocation만 측정하며 DuckDB native memory는 포함하지 않는다. 2026-09-01 개발 PC 측정:

| events | staging | profile | validation | normalization | DFG | total (generation 포함) | source | normalized | Python peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 0.122s | 0.677s | 0.416s | 0.165s | 0.156s | 4.550s | 12,597,940 B | 1,170,818 B | 2,384,189 B |
| 1,000,000 | 0.388s | 0.919s | 2.483s | 0.548s | 0.801s | 45.918s | 126,978,863 B | 12,768,747 B | 2,385,887 B |

환경별 결과가 달라지므로 이 값은 제품 보장이 아닌 개발 baseline이다. 5M/20M은 실행하지 않았다.
결정 근거는 `docs/ADR-002-browser-upload-vs-local-path-import.md`,
`docs/ADR-003-normalized-parquet.md`, `docs/ADR-004-dataset-versioning.md`에 기록한다.

## Semantic Contract와 업무 활동 분석 흐름

1. 백엔드와 프런트엔드를 실행한다.
2. 브라우저 업로드 또는 허용 root 아래의 Local Path Import로 Dataset을 등록한다.
3. schema/profile과 bounded preview를 확인한다.
4. case/activity/timestamp, source/display timezone, ordering, PII/retention을 Semantic Contract로 저장한다.
5. Raw/Parsed/UTC/Display timestamp preview와 Data Quality를 확인한다.
6. Normalize를 실행해 canonical UTC Parquet을 만든다.
7. exact Method → Business Activity mapping version을 만들고 coverage를 확인한다.
8. Overview와 Process Map에서 Source Activity/Business Activity를 전환한다.
9. Artifacts에서 active/pinned 상태와 disk usage를 확인하고 과거 inactive version만 명시적으로 정리한다.

Local Path Import는 `config/app.yaml`의 `dataset_import.allowed_roots`가 비어 있으면 비활성화된다.
`COPY`는 재현성과 원본 변경 격리를 우선하는 기본값이고, `REFERENCE`는 checksum/size/mtime을
매 작업 전에 검증하는 low-copy 방식이다. 임의 파일 탐색 API는 제공하지 않는다.

case ID HMAC을 활성화하려면 repository 밖의 local secret source에
`KOIES_PSEUDONYMIZATION_KEY`를 설정한다. 설정명은 `security.pseudonymization_key_env`로 변경할
수 있으나 secret 값 자체는 YAML, `.env` 예시, DB metadata, Git에 저장하지 않는다.

## Scale benchmark

```powershell
# 5M: source가 있으면 재사용하고 generation/application 시간을 분리한다.
.\.venv\Scripts\python.exe scripts\benchmark_ingestion.py `
  --events 5000000 --work-dir data/benchmarks --reuse-source

# 20M: preflight를 검토한 명시적 확인 없이는 실행되지 않는다.
.\.venv\Scripts\python.exe scripts\benchmark_ingestion.py `
  --events 20000000 --work-dir data/benchmarks --reuse-source --confirm-large-run
```

결과는 기본적으로 ignored local path인 `data/benchmarks/benchmark-results/*.json`에 저장된다.
`source_generation_seconds`, `application_processing_seconds`, `overall_seconds`를 별도로 보며,
application total은 staging/import부터 DFG까지의 wall-clock 시간이다. 5M/20M은 CI에서 실행하지 않는다.
