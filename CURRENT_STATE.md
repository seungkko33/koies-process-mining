# CURRENT_STATE.md — 개발 상태 체크포인트

> AI 코딩 세션이 끊기거나 다른 PC/에이전트로 전환될 때 가장 먼저 읽는 파일이다. 매 작업 종료 시 갱신한다.

## 현재 Phase
설계 완료 / 구현 전

## 현재 구현 상태
- [x] Architecture drafted
- [x] PRD drafted
- [x] Data model drafted
- [x] Process mining metric spec drafted
- [x] Security/performance/test policy drafted
- [ ] Repository application skeleton
- [ ] Synthetic fixture generator
- [ ] DuckDB connection/config module
- [ ] Golden DFG test
- [ ] FastAPI skeleton
- [ ] React skeleton

## 현재 핵심 결정
- Local-first
- DuckDB + Parquet
- SQL-first process mining MVP
- FastAPI + React
- PM4Py optional after license review
- External AI raw-data egress prohibited

## 다음 작업
`INITIAL_CODEX_PROMPT.md`를 사용하여 Phase 0/1 application skeleton을 생성한다.

## Blocker
실제 로그 구조가 아직 반영되지 않았으므로 다음 항목은 임의 확정 금지:
- case_id source
- timestamp semantics
- business activity mapping
- PII fields

## 최근 테스트
구현 전이므로 없음.

## 최근 변경
2026-08-31: 초기 설계/PRD 개발 패키지 작성.
