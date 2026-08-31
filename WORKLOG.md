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
