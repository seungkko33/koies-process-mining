# ADR-001: Local-first DuckDB + Parquet 아키텍처

## Status
Accepted for MVP design.

## Context
2,000만 건 이상의 공제정보망 로그는 일반 LLM context에 직접 제공하기 어렵고, 내부/민감정보가 포함될 가능성이 있다. 분석은 반복적으로 수행되며 filter, group, window, path 계산이 필요하다.

## Decision
- raw/curated 대용량 저장은 Parquet 중심
- 로컬 analytical SQL engine은 DuckDB
- backend는 Python/FastAPI
- external AI는 raw data plane과 분리
- process mining MVP는 SQL-first

## Consequences
장점:
- 데이터 외부 반출 최소화
- 저비용 로컬 개발
- 대용량 column scan과 집계에 적합
- 설치 구성 단순

단점/주의:
- multi-user concurrency 확장 시 재설계 가능
- high-cardinality variant와 복잡 aggregation은 benchmark 필요
- 데이터 의미 모델링(case/activity)이 별도 필요

## Revisit Trigger
- 수억~수십억 event에서 SLO 불충족
- 동시사용자 증가
- 실시간 처리 요구
- 중앙 사내 분석 플랫폼 요구
