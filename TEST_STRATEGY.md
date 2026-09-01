# 테스트 및 QA 전략

## 1. 테스트 원칙
프로세스 마이닝 제품에서 “화면이 뜬다”보다 “계산이 맞다”가 더 중요하다. 모든 핵심 지표는 사람이 검증 가능한 작은 event fixture로 golden test를 만든다.

## 2. Unit Test
### Backend
- filter validation
- case ordering
- DFG generation
- variant hash
- rework calculation
- percentile result
- mapping priority
- masking

### Frontend
- filter state
- API response parsing
- graph threshold
- empty/error/loading states

## 3. Golden Dataset
작은 합성 데이터:
```text
Case1: A B C
Case2: A B B C
Case3: A D C
```
수작업 기대값을 문서화:
- cases=3
- rework cases=1
- A→B=2
- B→B=1
- etc.

## 4. Data Quality Tests
- null timestamp
- invalid timezone
- no case key
- duplicate raw event
- mapping no-match
- mapping multi-match
- impossible negative duration
- timestamp reversal
- extreme case length

## 5. Integration Tests
- Parquet fixture → DuckDB → API → expected JSON
- API → frontend mock → graph
- mapping version change → reprocessing

## 6. Performance Tests
규모별 synthetic event generator 사용.
- 100k CI-friendly
- 1M local benchmark
- 5M/20M manual benchmark

메모리 peak와 wall time 함께 기록.

## 7. Security Tests
- SQL injection payload
- path traversal
- oversized response request
- disallowed export
- PII-like strings in application logs
- secret scanning

## 8. Regression Gate
PR 전 최소:
- unit tests pass
- lint/typecheck
- golden process metrics pass
- no secret/data file tracked

## 9. User Acceptance Tests
업무 담당자가 확인:
1. 선택 기간 case 수가 기존 시스템 집계와 설명 가능한 범위에서 일치하는가?
2. 대표 정상 프로세스가 실제 업무와 일치하는가?
3. 알려진 예외 case가 variant로 확인되는가?
4. 병목으로 알려진 구간이 성능 지표로 드러나는가?
5. mapping 오해가 없는가?

## 10. Ingestion vertical slice regression

완전 합성 fixture만 사용한다.

- valid CSV: 기존 3-case/10-event golden semantics
- valid Parquet: 같은 semantic rows를 DuckDB로 생성한 binary fixture
- invalid CSV: null/empty case/activity, invalid timestamp, duplicate event와 valid subset
- large synthetic: streaming generator를 100K 필수, 1M 선택 local benchmark에 사용

Backend integration은 upload → profile/preview → mapping/timestamp preview → validation → normalized
Parquet → dataset-aware Overview/DFG를 하나의 테스트에서 검증한다. 별도 테스트는 Parquet parity,
invalid quarantine, unsupported/signature 오류, path traversal, 200행 server cap, cleanup, state-machine
invalid transition을 검증한다. quarantine row 수와 failure code는 DuckDB direct query로 확인한다.

Frontend unit은 DTO runtime parsing, upload/status/error state model, required mapping validation,
data-quality KPI와 byte formatting을 검증한다. production-like HTTP flow와 실제 browser rendering은
unit test와 구분해 결과를 보고한다.

20M benchmark는 test suite에 포함하지 않는다. 5M/20M은 사용자가 명시적으로 실행한 경우에만
결과를 기록한다.

## 11. Semantic Contract and scale-readiness regression

합성 로그만 사용하여 다음 계약 경계를 자동 검증한다.

- append-only Semantic Contract 생성/조회/버전 전환
- naive timestamp의 필수 IANA source timezone, invalid timezone 거부, offset-aware timestamp의 UTC 변환
- case ID 및 event ID의 keyed HMAC 결정성, event ID DROP, 숫자 속성 pseudonymization 거부
- 동일 timestamp의 기술 오류와 의미상 순서 모호성 분리
- exact Activity Mapping coverage와 KEEP_SOURCE/GROUP_AS_UNMAPPED/EXCLUDE 정책
- Source/Business DFG의 contract/mapping/normalization provenance와 실제 Business Activity 수
- allowed-root Local Path COPY/REFERENCE, traversal 차단, REFERENCE drift 감지
- source/active/pinned artifact 삭제 차단과 atomic normalization failure recovery

5M은 generation과 application processing을 분리하여 필수 수동 실행한다. 20M은
`--confirm-large-run`과 disk preflight를 모두 통과한 명시적 실행만 허용한다.
