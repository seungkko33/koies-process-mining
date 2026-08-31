# 구축 로드맵

## Stage 0 — Feasibility / 1~2주 단위 작업
산출물:
- 실제 로그 데이터 사전
- PII 분류
- case key 후보 2~3개
- timestamp 신뢰도 분석
- top method frequency
- method→activity 초기 mapping
- 1M benchmark

Exit Criteria:
- 80% 이상 이벤트에서 유효 timestamp
- 핵심 업무 도메인에서 case 연결 가능성 확인
- activity mapping 전략 합의

## Stage 1 — Data Foundation
- ingestion CLI
- CSV/DB export → Parquet
- rejection/quarantine
- masking
- DuckDB schema
- curated event log
- data quality report

## Stage 2 — Analytics MVP
- overview metrics
- DFG
- variants
- throughput
- rework
- bottleneck
- FastAPI

## Stage 3 — Visual MVP
- React shell
- filters
- overview
- process map
- variants
- case explorer
- data quality

## Stage 4 — Operational Hardening
- performance tuning
- caching/materialization
- logging
- error handling
- configuration
- packaging
- local installer/run script

## Stage 5 — Advanced Mining
- compare
- conformance
- reference model
- PM adapter
- optional PM4Py after legal review

## Stage 6 — AI Assistance
- natural-language filter assistant
- aggregate result explanation
- report generation
- guarded SQL assistant

## 우선순위 원칙
P0: 데이터 정확성/보안/재현성
P1: 핵심 분석
P2: 시각화 편의
P3: 고급 알고리즘
P4: 생성형 AI 기능
