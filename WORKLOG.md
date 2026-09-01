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
