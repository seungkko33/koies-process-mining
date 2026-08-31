# 데이터 아키텍처 및 데이터 모델

## 1. 목적
본 문서는 공제정보망의 기술 로그를 프로세스 마이닝이 가능한 Event Log로 변환하기 위한 데이터 계약을 정의한다. 실제 컬럼명은 원천 시스템 조사 후 매핑하되, 논리 개념은 본 문서를 유지한다.

## 2. 핵심 개념

### 2.1 Case
분석상 하나의 업무 처리 건. 예: 청구건, 계약건, 지급건, 민원건, 배치작업건 등.

**절대 원칙:** case_id는 단순 session_id나 사용자 ID와 동일하다고 가정하지 않는다. 업무의 시작부터 종료까지 동일한 건을 연결할 수 있는 업무 키가 필요하다.

### 2.2 Activity
업무적으로 의미 있는 단계. 기술 메서드와 1:1일 수도 있지만 일반적으로 N:1 매핑이 필요하다.

예:
```text
ClaimController.insert()
ClaimService.save()
ClaimDAO.insertClaim()
        ↓ mapping
공제금 청구 접수
```

### 2.3 Event
특정 case에서 activity가 특정 시점에 발생한 기록.

### 2.4 Variant
한 case의 activity sequence. 동일한 sequence를 가진 case들을 하나의 variant로 그룹화한다.

## 3. Raw Log 논리 스키마
| 컬럼 | 타입 예시 | 설명 | 민감도 |
|---|---|---|---|
| source_system | VARCHAR | 원천 시스템 | 낮음 |
| raw_event_id | VARCHAR | 원천 이벤트 식별자 | 중간 |
| event_ts_raw | VARCHAR/TIMESTAMP | 원천 발생시각 | 중간 |
| class_name | VARCHAR | 클래스 | 낮음 |
| method_name | VARCHAR | 메서드 | 낮음 |
| module_name | VARCHAR | 모듈 | 낮음 |
| params_raw | VARCHAR/JSON | 메서드 변수 | 매우 높음 가능 |
| result_code | VARCHAR | 결과 코드 | 중간 |
| elapsed_ms | BIGINT | 수행시간 | 낮음 |
| user_id | VARCHAR | 사용자 ID | 높음 |
| session_id | VARCHAR | 세션 | 높음 |
| request_id | VARCHAR | 요청 | 중간 |
| client_ip | VARCHAR | IP | 높음 |
| server_id | VARCHAR | 서버 | 낮음 |
| source_sequence | BIGINT | 원천 순서 | 낮음 |

실제 원천 스키마 조사 후 `docs/DATA_DICTIONARY_TEMPLATE.md`에 기록한다.

## 4. Curated Event Log 스키마

### 필수
| 컬럼 | 타입 | 정의 |
|---|---|---|
| event_id | VARCHAR | 정규화 이벤트의 유일 ID |
| case_id | VARCHAR | 비식별된 분석 case key |
| activity | VARCHAR | 업무 activity |
| event_ts | TIMESTAMP | 이벤트 정렬용 시각 |

### 권장
| 컬럼 | 타입 | 정의 |
|---|---|---|
| source_method | VARCHAR | 원 기술 메서드 |
| source_class | VARCHAR | 원 클래스 |
| module | VARCHAR | 업무/기술 모듈 |
| lifecycle | VARCHAR | start/complete/unknown |
| org_code | VARCHAR | 조직 분류(필요 시 비식별) |
| actor_hash | VARCHAR | 비식별 사용자/처리자 |
| result_code | VARCHAR | 성공/실패/업무 결과 |
| duration_ms | BIGINT | 메서드 또는 활동 시간 |
| source_sequence | BIGINT | 동시 timestamp 정렬 보조 |
| ingest_sequence | BIGINT | ETL 정렬 보조 |
| mapping_version | VARCHAR | activity mapping 버전 |
| case_rule_version | VARCHAR | case 추출 규칙 버전 |
| ingestion_batch_id | VARCHAR | 적재 배치 |
| event_date | DATE | 파티션/필터 보조 |

## 5. Activity Mapping 테이블
```text
activity_mapping
- mapping_id
- mapping_version
- enabled
- priority
- source_system
- class_pattern
- method_pattern
- module_pattern
- condition_expression(optional)
- activity_name
- activity_group
- valid_from
- valid_to
- description
```

규칙 충돌 시 `priority`가 높은 규칙을 적용하고, 동일 priority 다중 매칭은 품질 오류로 기록한다.

## 6. Case Rule
```text
case_rule
- rule_id
- rule_version
- process_domain
- priority
- extraction_source        # request_id / JSON path / column / composite
- extraction_expression
- hash_required
- fallback_rule_id
- valid_from
- valid_to
- description
```

Case rule 예:
```text
process_domain = CLAIM
extraction_source = params_json
expression = $.claimNo
hash_required = true
```

## 7. 비식별화
원본 업무 키는 curated 계층에서 직접 사용하지 않는 것을 기본으로 한다.

권장:
- HMAC-SHA256 기반 deterministic token
- salt/secret는 데이터 파일/저장소와 분리
- 동일 원본 값은 동일 token으로 변환하여 join 가능
- 일방향 hash만으로 dictionary attack이 가능한 짧은 값은 HMAC 사용

## 8. 정렬 규칙
동일 case 내 순서:
```text
ORDER BY event_ts, source_sequence, ingest_sequence, event_id
```
`source_sequence`가 없으면 원천 시스템 조사 후 신뢰 가능한 tie-breaker를 정의한다.

## 9. 중복 정의
잠정 중복키:
```text
source_system + raw_event_id
```
raw_event_id가 없으면 후보:
```text
hash(event_ts_raw, class_name, method_name, request_id, source_sequence)
```
중복 삭제 규칙은 반드시 보고 가능해야 한다.

## 10. 품질 지표
적재마다 계산:
- total_raw_rows
- parsed_rows
- rejected_rows
- duplicate_rows
- missing_timestamp_rate
- missing_case_rate
- unmapped_activity_rate
- ambiguous_mapping_count
- timestamp_outlier_count
- invalid_duration_count
- case_single_event_rate
- case_extreme_length_rate

## 11. Partition 전략
Parquet은 우선 `event_date` 또는 월 단위로 분리한다.

예:
```text
curated/process_domain=CLAIM/year=2026/month=08/*.parquet
```
단, 작은 파일이 과도하게 늘어나지 않도록 파일 크기와 row group을 실제 벤치마크로 조정한다.

## 12. 집계 모델

### activity_summary
- filter_signature
- activity
- event_count
- case_count
- median_duration_ms
- p90_duration_ms
- rework_case_count

### dfg_edges
- filter_signature
- from_activity
- to_activity
- transition_count
- case_count
- median_wait_ms
- p90_wait_ms

### variant_summary
- filter_signature
- variant_hash
- activity_sequence_json
- case_count
- share
- median_throughput_ms
- p90_throughput_ms
- rework_rate

## 13. 데이터 보존
Raw, curated, aggregate의 보존기간을 분리한다. MVP에서는 삭제를 자동화하지 말고 정책 확정 후 구현한다.
