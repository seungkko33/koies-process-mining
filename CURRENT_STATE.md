# CURRENT_STATE.md — 개발 상태 체크포인트

> AI 코딩 세션이 끊기거나 다른 PC/에이전트로 전환될 때 가장 먼저 읽는 파일이다. 매 작업 종료 시 갱신한다.

## 현재 Phase
Phase 0/1 + Semantic Contract/Large Import/Business Activity/Lifecycle/5M readiness 완료

## 현재 구현 상태
- [x] Architecture drafted
- [x] PRD drafted
- [x] Data model drafted
- [x] Process mining metric spec drafted
- [x] Security/performance/test policy drafted
- [x] Repository application skeleton
- [x] Streaming synthetic fixture generator
- [x] DuckDB connection/config module
- [x] Golden DFG/overview/API tests
- [x] FastAPI `/health`, `/api/overview`, `/api/dfg`
- [x] React Overview skeleton
- [x] Cytoscape.js Process Map vertical slice
- [x] DFG benchmark harness and 100K development baseline
- [x] CSV/CSV.GZ/Parquet chunk upload and UUID staging
- [x] DuckDB direct schema/fast profile/bounded preview
- [x] Versioned Event Log mapping and timestamp parse preview
- [x] Technical validation, quarantine, normalized ZSTD Parquet
- [x] Dataset-aware existing Overview/DFG
- [x] React Dataset import/profile/mapping/quality/analyze workspace
- [x] Ingestion benchmark harness, 100K mandatory and 1M optional baseline
- [x] Versioned Semantic Contract, UTC timezone normalization, PII/retention/HMAC extension
- [x] Exact Method → Business Activity mapping, coverage, Source/Business DFG
- [x] COPY/REFERENCE Local Path Import allowed-root security and source drift detection
- [x] Atomic artifact materialization, active/pinned lifecycle and disk usage UI
- [x] 5M measured benchmark with reusable source and machine-readable results

## 현재 핵심 결정
- Local-first
- DuckDB + Parquet
- SQL-first process mining MVP
- FastAPI + React
- Cytoscape.js 3.34.2 direct dependency (MIT)
- PM4Py is not a runtime dependency
- External AI raw-data egress prohibited
- Primary ingestion is downloaded local file Browser Upload; operational DB direct connection is out of scope
- Partial invalid policy: at least one valid row may become READY with quarantine
- Request-scoped DuckDB connections are serialized for reliable Windows file-handle cleanup
- Canonical analytical timestamp is UTC; display timezone is presentation metadata
- Local Path COPY is default; REFERENCE is opt-in with checksum/size/mtime drift checks
- Artifact cleanup is explicit; source/active/pinned artifacts are protected

## 다음 작업
실제 데이터 없이 다음 Phase를 준비한다. 우선순위는 startup temporary reconciliation,
mapping-version comparison, long-operation cancel/recovery와 사용자 승인 후 20M benchmark다.

## Blocker
실제 로그 구조가 아직 반영되지 않았으므로 다음 항목은 임의 확정 금지:
- case_id source
- timestamp semantics
- business activity mapping
- PII fields

## 최근 테스트
- Backend: pytest 34 passed, Ruff passed, strict mypy passed
- Frontend: Vitest 18 passed, ESLint passed, TypeScript passed, Vite production build passed
- npm audit: 0 vulnerabilities
- Vite proxy HTTP E2E: CSV upload → Semantic Contract → READY → activity mapping → source/business DFG passed
- 100K ingestion: total 4.550s, staging 0.122s, normalization 0.165s, DFG 0.156s
- 1M ingestion: total 45.918s, staging 0.388s, normalization 0.548s, DFG 0.801s
- 5M: generation 50.550s, application 31.092s; reused source application 27.521s
- 20M: 미실행, no-confirm guard와 6.5GB required preflight 검증
- Browser QA: in-app browser native pipe trust failure로 screenshot/DOM/console/responsive 미검증
- git diff --check passed (Windows CRLF conversion warnings only)

## 최근 변경
2026-09-01: Semantic Contract, UTC normalization, keyed HMAC, activity mapping/coverage/business DFG,
Local Path COPY/REFERENCE, artifact lifecycle/atomic finalization, expanded quality/UI와 5M benchmark 구현.
2026-09-01: Local file Dataset ingestion, profiling, mapping, validation/quarantine,
normalized Parquet, Dataset UI, existing analytics integration과 100K/1M benchmark 구현.
2026-08-31: DFG API, Cytoscape.js Process Map, frontend adapter tests, benchmark harness 구현.
2026-08-31: 초기 설계/PRD 개발 패키지 작성.
