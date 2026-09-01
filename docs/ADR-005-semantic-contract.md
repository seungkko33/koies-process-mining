# ADR-005: Semantic Contract를 MappingDefinition 상위 aggregate로 둔다

- 상태: Accepted
- 날짜: 2026-09-01

## Context

column 선택만으로는 case null policy, ordering, timezone, PII/retention과 재현 가능한 분석 의미를 설명할 수 없다.
기존 MappingDefinition/API와 READY Dataset은 이미 검증된 baseline이므로 파괴적 migration도 피해야 한다.

## Decision

MappingDefinition은 low-level source column binding으로 유지하고, Dataset별 append-only `SemanticContract`가
mapping version을 참조한다. contract는 case policy, canonical timestamp contract, ordering, PII classification,
retention, HMAC 여부, business mapping provenance와 ACTIVE/SUPERSEDED status를 보존한다. 기존 `/mappings`는
mapping과 contract를 같은 transaction에서 만들고 명시적 `/semantic-contracts` endpoint도 제공한다.

## Consequences

기존 client는 계속 동작하고 새 분석은 contract version provenance를 갖는다. 초기 구현은 null/empty case를
REJECT로 고정하며 복잡한 case extraction rule/AI classification은 extension point에 남긴다.
