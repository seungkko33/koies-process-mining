# 원천 로그 데이터 사전 템플릿

> 실제 로그를 조사할 때 본 문서를 복사하여 작성한다. 민감한 예제값은 문서에 넣지 않는다.

| No | 원천 컬럼명 | 논리명 | 타입 | Null% | Distinct 추정 | 예제(합성) | 민감도 | Process Mining 용도 | 비고 |
|---:|---|---|---|---:|---:|---|---|---|---|
| 1 | | event timestamp | | | | 2026-01-01 10:00:00 | S1 | event_ts 후보 | |
| 2 | | method | | | | saveClaim | S1 | activity mapping | |
| 3 | | parameter | | | | {"case":"X001"} | S3 | case key 후보 | 실제값 기록 금지 |

## Timestamp 조사
- timezone:
- 생성 시점: method start / end / log write?
- millisecond precision:
- clock skew 가능성:

## Case 후보
| 후보 키 | 위치 | 업무 의미 | coverage | uniqueness | 여러 세션 지속 여부 | 평가 |
|---|---|---|---:|---:|---|---|
| | | | | | | |

## Activity Mapping 후보
| Class/Method pattern | 업무 Activity | 근거 | 신뢰도 | 비고 |
|---|---|---|---|---|
| | | | | |

## 민감정보
| 필드 | 민감 유형 | 필요성 | 처리 정책 |
|---|---|---|---|
| | | | remove/hash/generalize |
