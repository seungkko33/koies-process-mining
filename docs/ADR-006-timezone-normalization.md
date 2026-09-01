# ADR-006: 분석 timestamp는 UTC로 정규화한다

- 상태: Accepted
- 날짜: 2026-09-01

## Context

naive local timestamp나 서로 다른 offset을 wall time 그대로 정렬하면 DFG 순서와 duration이 달라질 수 있다.
수동 offset 계산은 DST, historical rule, timezone database 변경에 취약하다.

## Decision

aware input의 offset/zone을 우선하고 naive input에는 IANA `source_timezone`을 요구한다. DuckDB ICU
`timezone()`과 timezone database로 instant를 계산한 뒤 UTC fields를 plain `TIMESTAMP`로 Parquet에 저장한다.
display timezone은 분석 저장과 분리하고 preview에서 Raw/Parsed/UTC/Display를 함께 보여준다.

## Consequences

canonical arithmetic와 ordering이 host timezone에서 독립한다. ICU가 DST gap을 처리하는 표준 동작을
따르며 애플리케이션이 offset을 직접 계산하지 않는다. raw string은 source artifact에만 보존한다.
