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
