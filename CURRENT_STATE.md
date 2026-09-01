# CURRENT_STATE.md — 개발 상태 체크포인트

> AI 코딩 세션이 끊기거나 다른 PC/에이전트로 전환될 때 가장 먼저 읽는 파일이다. 매 작업 종료 시 갱신한다.

## 현재 Phase
Phase 0/1 vertical slice 완료 — Process Map 탐색 기능 진입점

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

## 현재 핵심 결정
- Local-first
- DuckDB + Parquet
- SQL-first process mining MVP
- FastAPI + React
- Cytoscape.js 3.34.2 direct dependency (MIT)
- PM4Py optional after license review
- External AI raw-data egress prohibited

## 다음 작업
Parquet ingestion/data-quality vertical slice를 구현한다. CSV/Parquet 입력을 DuckDB scan으로
정규화하고 quarantine 및 mapping/case rule version을 기록한 뒤 현재 DFG API에 연결한다.

## Blocker
실제 로그 구조가 아직 반영되지 않았으므로 다음 항목은 임의 확정 금지:
- case_id source
- timestamp semantics
- business activity mapping
- PII fields

## 최근 테스트
- Backend: pytest 12 passed, Ruff passed, mypy passed
- Frontend: Vitest 6 passed, ESLint passed, TypeScript passed, Vite production build passed
- npm audit: 0 vulnerabilities
- 100K synthetic benchmark: generation 5.315s, ingestion 0.409s, DFG 0.175s
- 1M/5M/20M benchmark 및 browser screenshot QA는 미실행

## 최근 변경
2026-08-31: DFG API, Cytoscape.js Process Map, frontend adapter tests, benchmark harness 구현.
2026-08-31: 초기 설계/PRD 개발 패키지 작성.
