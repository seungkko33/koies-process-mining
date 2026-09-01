# ADR-007: exact Method → Business Activity mapping을 query-time EventSource로 적용한다

- 상태: Accepted
- 날짜: 2026-09-01

## Context

method-level activity는 업무 사용자가 해석하기 어렵지만 원본 구조와 여러 mapping version 비교 가능성은
보존해야 한다. 정규화 때 원본 activity를 덮어쓰면 재다운로드/재정규화가 필요하다.

## Decision

Dataset별 append-only ActivityMappingSet/Entry를 저장하고 exact match만 구현한다. Business EventSource가
canonical Parquet과 mapping entry를 DuckDB에서 join해 기존 DFG module에 주입한다. unmapped policy는
KEEP_SOURCE(기본), GROUP_AS_UNMAPPED, EXCLUDE다. DFG response는 contract/mapping/normalization provenance와
coverage를 반환한다.

## Consequences

동일 source artifact에서 version을 바꿔 즉시 재분석할 수 있다. prefix/wildcard/regex/priority rule engine과
mapping comparison UI는 후속 scope다.
