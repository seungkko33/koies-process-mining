# WORKLOG.md

개발 세션별로 짧게 기록한다. 장문의 설계는 전문 문서에 작성하고 이 파일은 연속성 확보에 사용한다.

## Template
### YYYY-MM-DD — 작업 제목
- 목표:
- 변경:
- 테스트:
- 결정:
- 미해결:
- 다음 작업:

---

### 2026-08-31 — Initial planning package
- 목표: 20M+ 공제정보망 로그 기반 로컬 프로세스 마이닝 플랫폼 개발 기준 수립
- 변경: PRD, Architecture, Data Model, Security, Performance, Test, AI agent instructions 작성
- 테스트: 구현 전
- 결정: Local-first / DuckDB+Parquet / SQL-first / PM4Py optional
- 미해결: 실제 case key, timestamp semantics, activity mapping
- 다음 작업: application skeleton + synthetic golden dataset

### 2026-08-31 — DFG API to Cytoscape Process Map vertical slice
- 목표: 합성 Event Log에서 실제 FastAPI DFG 응답과 React Process Map까지 end-to-end 연결
- 변경: bounded `/api/dfg`, DFG metadata/empty/ordering tests, Cytoscape renderer, frequency threshold, node/edge detail, fit/reset, table alternative, benchmark harness
- 테스트: pytest 12 passed, frontend Vitest 6 passed, Ruff/mypy/ESLint/typecheck/build passed, npm audit 0 vulnerabilities
- 결정: Cytoscape.js 3.34.2를 MIT runtime dependency로 채택; 외부 source copy 없음; PM4Py/bpmn-js 미적용
- 성능: 100K synthetic events — 생성 5.315s, 적재 0.409s, DFG 0.175s; 1M/5M/20M 미실행
- 미해결: 실제 case key/timestamp/activity mapping/PII 정의, 대규모 benchmark, browser screenshot QA
- 다음 작업: Parquet ingestion + data quality + versioned mapping/case rule vertical slice

### 2026-09-01 — Local File Ingestion + Data Quality + Mapping vertical slice
- 목표: 사용자가 내려받은 CSV/Parquet를 localhost에서 reliable Event Log로 변환하고 기존 분석에 연결
- 변경: UUID Dataset/state/manifest, chunk upload+SHA-256, DuckDB direct scan/fast profile/preview,
  versioned mapping, timestamp preview, SQL validation, quarantine, ZSTD normalized Parquet,
  dataset-aware Overview/DFG, React Dataset workspace, safe delete와 3개 ingestion ADR
- 테스트: backend pytest 22 passed, Ruff/mypy passed; frontend Vitest 14 passed,
  ESLint/typecheck/build passed; npm audit 0 vulnerabilities; git diff --check passed
- E2E: Vite proxy로 3-case/10-event CSV upload→mapping→READY→Overview/DFG 통과
  (3 cases, 10 events, 4 nodes, 5 edges, A→B=2)
- 성능: 100K total 4.550s/staging 0.122s/normalization 0.165s/DFG 0.156s,
  1M total 45.918s/staging 0.388s/normalization 0.548s/DFG 0.801s
- 결정: Browser Upload primary, Local Path adapter future only; source immutable; mapping별 artifact;
  부분 invalid는 valid row가 있으면 quarantine과 함께 READY; Windows file lock 회피를 위해 DB scope 직렬화
- dependency: python-multipart 0.0.32 (Apache-2.0), FastAPI multipart streaming에 필요
- 미해결: 실제 case/timestamp/activity/PII 의미, timezone conversion, old mapping artifact retention,
  5M/20M benchmark; Browser plugin cache mismatch로 screenshot/console/responsive QA 미실행
- 다음 작업: 실제 데이터 반입 전 semantic mapping/PII governance 확정 및 수동 대규모 benchmark

### 2026-09-01 — Semantic Contract + Business Activity + Scale Readiness
- 목표: 실제 데이터 반입 전 재현 가능한 의미 계약, UTC ordering, method→business 분석, 대용량 import와 artifact 운영 준비
- 변경: MappingDefinition 상위 Semantic Contract, IANA/ICU UTC normalization, Raw/Parsed/UTC/Display preview,
  PII/retention/keyed HMAC, append-only exact ActivityMappingSet과 coverage/3 unmapped policy, Business EventSource/DFG provenance,
  allowed-root COPY/REFERENCE import와 source drift, atomic Parquet, active/pinned cleanup, disk UI, expanded quality와 frontend workflow
- 테스트: backend pytest 34, frontend Vitest 18; Ruff/strict mypy/ESLint/typecheck/build/audit/diff check 최종 통과
- E2E: localhost Vite proxy에서 synthetic upload→contract→normalize→activity mapping→source/business DFG 200 확인
- 성능: 5M generation 50.550s + application 31.092s; reused source application 27.521s; source 639,342,921 B,
  normalized 약 95.7MB, Python tracemalloc 약 2.37MB, DuckDB spill 0 B
- 결정: UTC canonical, COPY default/REFERENCE opt-in, query-time business mapping, explicit retention, synchronous 유지,
  20M manual confirmation required, 새 dependency 없음
- 미해결: browser native bridge trust failure로 rendered screenshot/DOM/console/responsive QA 미검증;
  process RSS 미측정; crash 뒤 orphan temp startup reconciliation/cancel API와 mapping comparison UI는 후속
- 다음 작업: 위 운영 hardening 후 disk 여유와 사용자 확인 하에 20M 수동 benchmark
