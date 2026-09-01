# PRD — 공제정보망 로그 기반 Local Process Mining Platform

- 문서 상태: Draft for Development
- 제품 유형: Local-first analytical desktop/web application
- 초기 대상: 2,000만+ 메서드/변수 로그
- 핵심 데이터 엔진: DuckDB + Parquet
- 백엔드: Python + FastAPI
- 프론트엔드: React + TypeScript
- 핵심 시각화: Cytoscape.js + Apache ECharts
- 프로세스 마이닝 전략: SQL-first, PM4Py optional

---

# 1. 제품 개요

## 1.1 문제 정의
공제정보망에는 사용자의 업무 처리 및 시스템 실행 과정이 대규모 메서드/변수 로그로 축적되어 있다. 이러한 로그에는 실제 업무 프로세스의 순서, 반복, 실패, 병목, 우회경로, 시스템 호출 패턴이 반영되어 있을 가능성이 높다.

그러나 일반적인 생성형 AI 서비스에 2,000만 건 이상의 원천 로그를 직접 업로드해 분석하는 접근은 다음 문제가 있다.

1. 업로드/컨텍스트 용량 한계
2. 민감정보 및 내부 데이터 외부 전송 위험
3. 매 분석마다 전체 데이터를 재전송해야 하는 비효율
4. 재현 가능한 정량 분석보다 샘플 기반 추론에 의존할 위험
5. 프로세스 마이닝에 필요한 정렬·집계·경로 탐색을 LLM이 직접 수행하기에는 부적합

따라서 본 제품은 **데이터 분석은 로컬 DuckDB가 수행하고, AI는 코드 작성·질의 보조·결과 해석 역할만 담당하는 Local-first 프로세스 마이닝 플랫폼**으로 설계한다.

## 1.2 제품 비전
업무 담당자가 공제정보망 로그를 기반으로 다음 질문에 스스로 답할 수 있게 한다.

- 실제 업무는 어떤 순서로 처리되고 있는가?
- 가장 많이 발생하는 정상 프로세스는 무엇인가?
- 동일 업무가 왜 여러 경로로 분기되는가?
- 어느 단계에서 가장 오래 머무는가?
- 어떤 활동이 반복적으로 수행되는가?
- 오류 발생 이후 어떤 경로로 이동하는가?
- 특정 기간/조직/업무유형의 프로세스가 다른 집단과 어떻게 다른가?
- 알려진 표준 프로세스와 실제 로그는 얼마나 일치하는가?

## 1.3 제품 원칙
1. Local-first
2. SQL-first
3. Data quality before visualization
4. Reproducible analytics
5. Explainable metrics
6. Privacy by design
7. Modular PM engine
8. Progressive disclosure: 복잡한 분석은 사용자가 필요할 때만 노출

---

# 2. 목표와 비목표

## 2.1 목표
### G1. 대규모 로컬 분석
최소 2,000만 events를 단일 고성능 PC에서 처리할 수 있는 분석 기반을 제공한다.

### G2. 기술 로그의 업무 이벤트화
method/class/params 기반 로그를 business activity event로 변환할 수 있는 versioned mapping 체계를 제공한다.

### G3. 핵심 프로세스 마이닝
MVP에서 다음을 제공한다.
- DFG
- Variant
- Throughput
- Rework
- Bottleneck
- Start/End Activity
- Error path
- Case Explorer

### G4. 시각적 분석
복잡한 SQL 없이 기간/업무/조직 필터를 적용하여 process map과 지표를 확인한다.

### G5. 데이터 품질 관리
case 미매핑, activity 미매핑, timestamp 오류를 사용자에게 명확히 보여준다.

### G6. 확장성
향후 PM4Py 또는 다른 process mining engine, 사내 서버 배포, AI 분석 보조를 추가할 수 있게 한다.

## 2.2 비목표 — MVP
- 실시간 스트리밍 분석
- 운영계 DB에 직접 write
- 프로세스 자동 제어/RPA 실행
- 완전한 BPMN 편집기
- 외부 SaaS 기반 원천 데이터 분석
- AI가 raw log 전체를 직접 읽는 기능
- 분산 Spark cluster 구축
- 조직 전체 multi-tenant 서비스

---

# 3. 사용자 및 역할

## 3.1 Primary User — 분석 담당자
목표:
- 로그 기반 업무 흐름 분석
- 병목/반복/이상경로 발견
- 분석 결과 보고

필요 기능:
- 필터
- process map
- variant
- case drill-down
- export of aggregated result

## 3.2 Process Owner / 업무 담당자
목표:
- 실제 업무 흐름 검증
- 매핑 오류 확인
- 개선대상 파악

## 3.3 개발/데이터 관리자
목표:
- raw ingestion
- mapping rule 관리
- case rule 관리
- 성능 설정
- 데이터 품질 모니터링

## 3.4 시스템 관리자 — 향후
사내 다중사용자 배포 시 권한/감사/설정 관리.

---

# 4. 핵심 사용자 여정

## Journey A — 데이터 준비
1. 사용자가 공제정보망에서 내려받은 CSV/Parquet 파일을 localhost UI에서 업로드한다.
2. 시스템이 schema와 row count를 검사한다.
3. timestamp parsing 및 민감 필드 후보를 탐지한다.
4. 사용자가 process domain과 case rule을 선택한다.
5. system이 method→activity mapping을 적용한다.
6. raw → Parquet → curated event log를 생성한다.
7. 품질 리포트를 표시한다.
8. 최소 품질 기준을 통과하면 분석 가능 상태가 된다.

## Journey B — 전체 흐름 탐색
1. 분석 기간 선택
2. process domain 선택
3. Overview KPI 확인
4. Process Map 이동
5. frequency threshold 조정
6. 특정 edge 선택
7. 병목 상세 확인
8. 관련 case/variant 확인

## Journey C — 반복 처리 분석
1. Rework 화면 이동
2. rework rate 높은 activity 정렬
3. activity 선택
4. 정상 반복인지 이상 반복인지 업무 담당자 검토
5. 대표 variant/case 확인

## Journey D — 기간 비교
1. Compare 화면
2. A: 이전월, B: 이번월
3. throughput/rework/variant 변화를 확인
4. 증가한 transition/variant drill-down

---

# 5. 데이터 수집 및 적재 요구사항

## FR-DATA-001 원천 파일 등록
시스템은 최소 CSV와 Parquet 입력을 지원해야 한다.
Primary 방식은 사용자가 다운로드한 로컬 파일의 Browser Upload다. 선택 확장은 제한된 Local Path
Import 또는 DB export connector이며 운영 DB 직접 연결은 MVP 범위가 아니다.

Acceptance:
- CSV/CSV.GZ/Parquet 파일 선택과 chunked localhost upload
- unsupported/corrupt 파일은 명확한 오류와 FAILED state 또는 안전한 사전 거부
- 파일 크기와 scan 후 실제 행 수 표시
- raw data 자체를 application log에 기록하지 않음

## FR-DATA-002 Schema Profiling
입력 파일의 컬럼명, 데이터형 추정, null 비율, distinct 추정치를 표시한다.

PII 후보 탐지:
- 주민번호 유사
- 계좌번호 유사
- 전화/이메일
- IP
- 이름 가능 문자열

자동 판단은 경고이며 최종 분류는 사용자/관리자가 확인한다.

## FR-DATA-003 CSV → Parquet 변환
대용량 CSV는 반복 쿼리 전에 Parquet으로 변환한다.

요구:
- chunk/stream 기반
- 전체 파일의 Python memory materialization 금지
- ingestion batch id 생성
- failure/reject 기록

## FR-DATA-004 Timestamp Normalization
사용자가 원 timestamp 컬럼 및 timezone을 설정할 수 있어야 한다.

검증:
- parse failure rate
- future outlier
- extreme old date
- timezone mismatch

## FR-DATA-005 Case Extraction
하나 이상의 규칙을 사용해 case_id를 생성한다.

지원 후보:
- direct column
- JSON path
- composite key
- request/session correlation
- fallback

case_id 원문은 HMAC 기반 token으로 저장 가능해야 한다.

## FR-DATA-006 Activity Mapping
기술 로그를 business activity로 매핑한다.

매핑 조건:
- exact method
- method pattern
- class + method
- module + method
- optional result/parameter condition

모든 event에 mapping_version을 저장한다.

## FR-DATA-007 Quarantine
다음 이벤트는 별도 quarantine에 분류한다.
- timestamp parse 실패
- 필수 컬럼 결손
- mapping conflict
- invalid case extraction

분석 dataset에 조용히 포함하거나 삭제하지 않는다.

## FR-DATA-008 Data Quality Gate
기본 임계치 예:
- timestamp parse success >= 99%
- case mapping >= 프로젝트별 기준
- ambiguous activity mapping = 0 권장

임계치는 설정 가능해야 한다.

---

# 6. Event Log 요구사항

## FR-EVENT-001 Canonical Schema
필수:
- event_id
- case_id
- activity
- event_ts

## FR-EVENT-002 Deterministic Ordering
동일 case의 이벤트 순서는 항상 동일하게 재현되어야 한다.

정렬:
`event_ts, source_sequence, ingest_sequence, event_id`

## FR-EVENT-003 Version Traceability
모든 분석 결과는 최소 다음에 연결 가능해야 한다.
- ingestion_batch_id
- mapping_version
- case_rule_version

## FR-EVENT-004 No Raw Params by Default
curated event log에는 raw params 전체를 저장하지 않는다. 분석에 필요한 attribute만 whitelist 추출한다.

---

# 7. 분석 엔진 요구사항

## FR-AN-001 Overview
입력: FilterSpec
출력:
- case_count
- event_count
- activity_count
- median_throughput
- p90_throughput
- rework_rate
- failure_rate(optional)

## FR-AN-002 DFG
Input:
- FilterSpec
- frequency mode
- min case share
- top nodes/edges

Output Node:
- activity
- event_count
- case_count
- case_share

Output Edge:
- source
- target
- transition_count
- case_count
- case_share
- median_transition_ms
- p90_transition_ms

## FR-AN-003 Variant
case별 activity sequence를 생성하고 빈도 순으로 집계한다.

API는 전체 variant를 무제한 반환하지 않는다.

Default:
- top 100
- pagination or cursor

## FR-AN-004 Throughput
case start~end 차이를 계산한다.

필수 통계:
- median
- p75
- p90
- p95
- average

## FR-AN-005 Rework
동일 case 내 동일 activity 2회 이상 발생을 기본 rework로 정의한다.
정상 반복 제외 rule은 향후 configuration으로 지원.

## FR-AN-006 Bottleneck
각 transition에 대해 frequency와 duration을 함께 제공한다.
단일 score를 제공하는 경우 score 식과 component를 UI에 공개한다.

## FR-AN-007 Start/End
case별 start/end activity ranking.

## FR-AN-008 Error Path
result_code 또는 success flag가 있는 경우 실패 전후 경로 분석을 지원한다.

## FR-AN-009 Path Search
정확 연속경로와 순서 포함경로를 지원한다.

## FR-AN-010 Compare
A/B FilterSpec을 받아 동일 metric의 차이를 계산한다.

## FR-AN-011 Case Detail
hashed case id에 대해 ordered event timeline을 반환한다.

보안:
- raw params 없음
- page/row limit

---

# 8. 필터 요구사항

## FilterSpec 초안
```json
{
  "date_from": "2026-01-01",
  "date_to": "2026-01-31",
  "process_domain": ["CLAIM"],
  "org_codes": [],
  "activities_include": [],
  "activities_exclude": [],
  "result_codes": [],
  "mapping_version": "v1",
  "case_attributes": {}
}
```

## FR-FILTER-001 Filter Pushdown
가능한 필터는 SQL/Parquet scan 단계까지 내려가야 한다.
프론트엔드에서 수백만 row를 받아 filtering하지 않는다.

## FR-FILTER-002 Filter Reproducibility
분석 결과와 함께 filter spec을 저장/복사할 수 있어야 한다.

## FR-FILTER-003 Event vs Case Filtering
필터 적용으로 case의 일부 event만 제거될 경우 throughput 의미가 바뀔 수 있으므로 정책을 명시한다.

권장 모드:
- `event_filter`: 조건에 맞는 event만 분석
- `case_filter`: 조건에 맞는 case를 찾은 뒤 해당 case의 전체 event sequence 분석

UI는 둘을 혼동하지 않게 한다.

---

# 9. Backend/API 요구사항

## 9.1 기본 API 구조
```text
GET  /health
GET  /api/meta/datasets
GET  /api/meta/activities
GET  /api/data-quality
POST /api/analytics/overview
POST /api/analytics/dfg
POST /api/analytics/variants
POST /api/analytics/performance
POST /api/analytics/rework
POST /api/analytics/compare
POST /api/cases/search
GET  /api/cases/{case_id}
```

## 9.2 Response Envelope
```json
{
  "data": {},
  "meta": {
    "query_ms": 1234,
    "rows": 100,
    "filter_signature": "...",
    "mapping_version": "v1"
  },
  "warnings": []
}
```

## NFR-API-001 Result Limit
모든 list API에 limit/pagination 적용.

## NFR-API-002 Query Timeout
long-running query는 timeout 또는 cancel 가능 구조를 가진다.

## NFR-API-003 SQL Safety
사용자 문자열을 SQL에 직접 interpolation 하지 않는다.

## NFR-API-004 Error Taxonomy
최소:
- VALIDATION_ERROR
- DATASET_NOT_READY
- DATA_QUALITY_ERROR
- QUERY_TIMEOUT
- QUERY_FAILED
- NOT_FOUND
- SECURITY_BLOCKED

---

# 10. Frontend 요구사항

## 10.1 Application Shell
- 좌측 navigation
- 상단 global filter
- main content
- optional right detail panel

## FR-UI-001 Overview Page
KPI + trend + bottleneck + top variant summary.

Acceptance:
- filter 변경 반영
- loading/error/empty 구분
- 숫자 단위/기간 명시

## FR-UI-002 Process Map
Cytoscape.js 기반.

기능:
- pan/zoom
- fit
- node/edge selection
- threshold
- frequency/performance mode
- details panel

## FR-UI-003 Variant Page
table + sequence visualization.

## FR-UI-004 Performance Page
percentile, transition ranking, distribution.

## FR-UI-005 Rework Page
rework activity와 대표 variant/case.

## FR-UI-006 Case Explorer
비식별 case timeline.

## FR-UI-007 Data Quality
적재 batch와 오류율.

## FR-UI-008 Mapping Admin
초기에는 read-only 또는 file-driven configuration으로 시작 가능. 추후 편집 UI.

---

# 11. 성능 요구사항

## NFR-PERF-001 데이터 규모
20M+ events에서 동작해야 한다.

## NFR-PERF-002 메모리
전체 dataset을 Python object/DataFrame으로 materialize 하지 않는다.

## NFR-PERF-003 DuckDB Out-of-core
NVMe temp directory를 사용 가능하게 한다.

## NFR-PERF-004 잠정 응답 목표
- common overview warm: <=3s
- common DFG: <=10s
- top variants: <=15s
- case detail: <=3s

전체기간 고비용 분석은 별도 loading/cancel UX를 허용한다.

## NFR-PERF-005 Graph Limit
기본 render:
- nodes <=100
- edges <=300

사용자가 threshold를 낮출 때 성능 경고.

---

# 12. 보안 요구사항

## NFR-SEC-001 Local-only Default
백엔드는 기본 `127.0.0.1` bind.

## NFR-SEC-002 No External Data Egress
실제 로그를 외부 AI/API로 보내는 기능은 기본적으로 존재하지 않는다.

## NFR-SEC-003 PII Masking
case, actor 등 식별키는 curated 단계에서 비식별 가능해야 한다.

## NFR-SEC-004 Secret
secret은 repo에 저장하지 않는다.

## NFR-SEC-005 Logging
raw params/PII 로그 금지.

## NFR-SEC-006 Export
export가 구현될 경우 집계 결과와 case detail export를 분리하고 민감정보 검토를 거친다.

---

# 13. 데이터 품질 요구사항

## NFR-DQ-001 분석 전 품질 가시성
품질 문제를 숨기지 않는다.

## NFR-DQ-002 Mapping Coverage
unmapped rate를 표시.

## NFR-DQ-003 Case Coverage
missing case rate 표시.

## NFR-DQ-004 Timestamp Quality
parse error와 timezone warning 표시.

## NFR-DQ-005 Reprocessing
rule 수정 후 동일 raw batch를 다시 curated로 생성 가능.

---

# 14. AI 기능 — Phase 4

## AI-001 Natural Language Filter
예:
“지난달 지급 업무 중 실패 건만 보여줘”
→ FilterSpec 초안 생성
→ 사용자가 확인
→ API 호출

AI가 raw SQL을 직접 생성/실행하는 것보다 FilterSpec 변환을 우선한다.

## AI-002 Result Explanation
AI 입력:
- filter summary
- aggregate metrics
- top bottleneck
- top variants

출력:
- 관찰 사실
- 가능한 해석
- 추가 확인 필요 항목

사실과 추론을 구분한다.

## AI-003 SQL Assistant — 개발/고급사용자
허용 view만 SELECT.
실행 전 validation.

## AI-004 Report Draft
집계 결과를 이용해 업무 개선 보고서 초안 생성.

---

# 15. 고급 프로세스 마이닝 — Phase 3+

## ADV-001 Reference Model
표준 업무 프로세스 모델 등록.

## ADV-002 Conformance
실제 로그와 참조 모델 차이.

## ADV-003 Model Discovery
Inductive Miner/Petri Net 등.

## ADV-004 PM Engine Adapter
PM4Py 등 외부 엔진을 교체 가능하게 인터페이스화.

라이선스 검토 전 MVP dependency 금지.

---

# 16. 데이터 저장 구조

```text
data/
├ raw/
│  └ <batch>/...
├ parquet/
│  ├ raw/
│  └ curated/
│     └ process_domain=.../year=.../month=.../*.parquet
├ quarantine/
└ temp/

db/
└ process_mining.duckdb
```

DB에는 다음 성격을 저장한다.
- metadata
- rules
- small dimensions
- aggregate tables/cache
- 필요 시 curated internal table

Parquet direct query와 DuckDB internal table은 benchmark 후 선택 가능하게 한다.

---

# 17. Configuration 요구사항

```yaml
app:
  host: 127.0.0.1
  port: 8000

data:
  raw_dir: ./data/raw
  curated_dir: ./data/parquet/curated
  quarantine_dir: ./data/quarantine

duckdb:
  path: ./db/process_mining.duckdb
  threads: 6
  memory_limit: 20GB
  temp_directory: ./data/temp
  preserve_insertion_order: false
analytics:
  max_nodes: 100
  max_edges: 300
  max_variants: 100
  case_page_size: 100
security:
  allow_external_ai: false
  allow_raw_export: false
```

---

# 18. 관측성 및 운영

## OBS-001 Query Metrics
기록:
- endpoint
- query name
- duration
- rows
- cache hit
- error type

## OBS-002 Dataset Metadata
- source batch
- curated created_at
- rules version
- row count
- quality metrics

## OBS-003 Diagnostics
설정 화면에서:
- DuckDB version
- database path
- memory limit
- thread count
- temp directory
- disk free space

실제 secret 또는 raw path 상세는 필요 수준에서만 표시.

---

# 19. 실패 및 예외 처리

## E-001 Data file missing
분석 중 파일 경로가 사라진 경우 dataset unavailable 처리.

## E-002 DuckDB OOM
사용자 메시지:
- 분석 범위를 줄이거나
- memory/temp 설정 확인
- 개발 diagnostics 확인

앱이 강제 종료되지 않도록 가능한 예외 처리.

## E-003 Query timeout
현재 필터와 query type을 유지한 채 취소/재시도.

## E-004 Corrupt parquet
batch를 degraded 상태로 표시.

## E-005 Mapping conflict
해당 event quarantine 또는 unmapped로 처리하고 품질 화면 표시.

## E-006 Empty result
정상 empty state. 시스템 오류와 구분.

---

# 20. Acceptance Criteria — MVP 전체

MVP는 다음 조건을 모두 만족할 때 완료로 본다.

### 데이터
- [ ] 최소 20M 규모 benchmark dataset을 처리
- [ ] CSV/Parquet ingestion 경로 존재
- [ ] curated event log 생성
- [ ] mapping/case rule version 기록
- [ ] data quality report 생성

### 분석
- [ ] overview 계산 golden test 통과
- [ ] DFG golden test 통과
- [ ] variant golden test 통과
- [ ] throughput percentile 검증
- [ ] rework 검증
- [ ] case timeline 검증

### UI
- [ ] Global Filter
- [ ] Overview
- [ ] Process Map
- [ ] Variants
- [ ] Performance
- [ ] Rework
- [ ] Case Explorer
- [ ] Data Quality

### 성능
- [ ] 전체 dataset을 Pandas로 적재하지 않음
- [ ] common query SLO 벤치마크 기록
- [ ] graph element limits 적용

### 보안
- [ ] raw data git 제외
- [ ] secret git 제외
- [ ] actual PII fixture 없음
- [ ] external AI raw data path 없음
- [ ] application logs에 raw params 없음

### 개발 품질
- [ ] unit/integration tests
- [ ] typecheck/lint
- [ ] README 실행 절차
- [ ] architecture/data model 문서 동기화

---

# 21. Epic 및 개발 티켓 분해

## EPIC 0 — Repository/Foundation
### T0.1 Repository skeleton
### T0.2 Config loader
### T0.3 DuckDB connection manager
### T0.4 Structured logging
### T0.5 Synthetic fixture generator

## EPIC 1 — Ingestion
### T1.1 File inspection
### T1.2 CSV→Parquet
### T1.3 Batch metadata
### T1.4 Timestamp normalization
### T1.5 Quarantine
### T1.6 Data quality metrics

## EPIC 2 — Mapping/Case
### T2.1 Activity mapping schema
### T2.2 Rule evaluator
### T2.3 Case extractor
### T2.4 HMAC tokenizer
### T2.5 Mapping coverage report

## EPIC 3 — Event Log
### T3.1 Curated schema
### T3.2 deterministic ordering
### T3.3 duplicate handling
### T3.4 partition writer

## EPIC 4 — Analytics
### T4.1 Overview SQL
### T4.2 DFG SQL
### T4.3 Variant SQL
### T4.4 Throughput SQL
### T4.5 Rework SQL
### T4.6 Bottleneck SQL
### T4.7 Path search
### T4.8 Compare

## EPIC 5 — API
### T5.1 FilterSpec
### T5.2 Overview endpoint
### T5.3 DFG endpoint
### T5.4 Variants endpoint
### T5.5 Case endpoint
### T5.6 Error taxonomy

## EPIC 6 — Frontend
### T6.1 Shell/navigation
### T6.2 Filter bar
### T6.3 Overview
### T6.4 Process Map
### T6.5 Variants
### T6.6 Performance
### T6.7 Rework
### T6.8 Case Explorer
### T6.9 Data Quality

## EPIC 7 — Hardening
### T7.1 Benchmark suite
### T7.2 Caching
### T7.3 OOM diagnostics
### T7.4 packaging/run scripts
### T7.5 security review

## EPIC 8 — Advanced
### T8.1 Compare UI
### T8.2 PM adapter
### T8.3 Conformance
### T8.4 AI assistant

---

# 22. 우선 구현할 Vertical Slice
가장 먼저 아래 한 줄을 end-to-end로 구현한다.

**합성 event log → DuckDB DFG 계산 → FastAPI JSON → React process map**

이 vertical slice가 성공하면 architecture의 가장 중요한 연결이 검증된다.

단, 그 전에 golden dataset과 계산 test를 먼저 만든다.

---

# 23. 주요 리스크와 대응

## R1 Case ID를 찾지 못함 — 매우 높음
영향: 프로세스 마이닝 자체가 무의미해질 수 있음.
대응:
- 업무 domain 하나부터 시작
- params의 업무식별키 후보 분석
- request/session correlation 분석
- case notion을 여러 개 지원

## R2 Method와 Activity가 과도하게 1:1 — 높음
영향: 수백~수천 node의 unreadable graph.
대응:
- mapping layer
- activity hierarchy
- technical/business view 분리

## R3 Timestamp 의미 불명 — 높음
영향: 순서/소요시간 오류.
대응:
- timestamp semantics 조사
- server clock/timezone 검증
- sequence tie-breaker

## R4 Variant explosion — 높음
대응:
- business activity abstraction
- Top-N
- cumulative coverage
- infrequent path filtering

## R5 Memory/OOM — 중간
대응:
- Parquet
- pushdown
- DuckDB out-of-core
- query split
- aggregate cache
- benchmark

## R6 PII leakage — 매우 높음
대응:
- raw params 미보존
- masking
- no external AI
- git/data separation

## R7 PM4Py license — 중간/법적
대응:
- optional adapter
- legal review
- commercial license if needed

## R8 UI가 복잡해짐 — 중간
대응:
- overview→drilldown
- threshold
- default sensible view
- table alternative

---

# 24. Phase 0에서 반드시 답해야 하는 질문
실제 개발 전에 다음 질문에 답변을 문서화한다.

1. 로그의 실제 row 수와 기간은?
2. 컬럼 수와 평균 row size는?
3. params는 JSON인가, 문자열인가?
4. 업무 식별키가 params에 존재하는가?
5. request_id/session_id는 어느 범위까지 지속되는가?
6. 한 업무 case가 여러 session을 넘나드는가?
7. timestamp는 시작 시각인가 종료 시각인가?
8. duration이 별도 존재하는가?
9. 메서드 호출 중 중첩 호출이 많은가?
10. 로그가 UI/Service/DAO까지 모두 포함하는가?
11. 동일 업무가 배치와 온라인에서 다르게 기록되는가?
12. 성공/실패 코드가 있는가?
13. 사용자/조직 정보가 필요한가?
14. 분석 대상의 첫 process domain은 무엇인가?
15. 표준 프로세스 문서가 존재하는가?

---

# 25. 최종 권장 구현 판단
본 프로젝트는 일반적인 AI 분석 과제가 아니라 **로그 기반 분석 제품 개발 과제**로 정의해야 한다.

가장 적절한 초기 구조는:

```text
Raw Logs
→ Parquet
→ DuckDB normalization
→ Curated Event Log
→ SQL Process Metrics
→ FastAPI
→ React Visual Analytics
→ Optional AI Interpretation
```

2,000만 건 규모에서 가장 큰 위험은 “DuckDB가 데이터를 못 다루는가”가 아니라 **로그를 올바른 case/activity 이벤트로 의미 변환할 수 있는가**이다. 따라서 개발 자원의 우선순위는 화려한 UI보다 Phase 0 데이터 의미 검증과 mapping 체계에 둔다.

---

# 26. File-based Local Ingestion 확정사항

## Primary ingestion
MVP는 운영 DB에 직접 연결하지 않는다. 사용자가 별도로 내려받은 CSV/CSV.GZ/Parquet 파일을
localhost browser UI에 upload하는 방식이 primary path다. DB export connector와 제한된 Local Path
Import는 미래 adapter 후보이며 현재 제품의 전제가 아니다.

## 구현된 Dataset journey
1. multipart upload를 UUID staging 경로에 chunk 저장하고 SHA-256/크기를 기록한다.
2. DuckDB direct scan으로 schema, row count, fast profile과 bounded preview를 생성한다.
3. 사용자가 case_id/activity/event_ts 및 선택 필드를 명시하고 versioned mapping을 저장한다.
4. DuckDB SQL이 technical validation을 수행해 valid/quarantine을 분리한다.
5. valid row를 canonical ZSTD Parquet으로 materialize한다.
6. 유효 event가 있으면 Dataset을 READY로 표시하고 기존 Overview/DFG datasource로 선택한다.

## Scope와 정책
- source activity column을 canonical activity로 직접 연결하며 Method→Business Activity rule engine은
  후속 Phase다.
- timezone은 사용자 입력 metadata로 기록한다. 실제 timezone 의미가 확정되지 않은 상태에서 임의
  변환하지 않는다.
- null/empty case 또는 activity, null/invalid timestamp, suspected duplicate event는 격리한다.
- 일부 invalid row가 있어도 valid row가 1개 이상이면 `PASSED_WITH_QUARANTINE`으로 분석 가능하다.
- 전체 유효 row가 0이면 READY로 승격하지 않는다.
- preview와 profile sample은 데이터 이해용으로만 제공하고 raw data browser/export로 확장하지 않는다.

## Phase: Semantic Contract와 scale readiness

- 기존 MappingDefinition을 유지하면서 versioned `SemanticContract`가 case policy, canonical UTC timestamp,
  deterministic ordering, PII classification, attribute retention, 선택적 keyed HMAC을 고정한다.
- naive timestamp는 IANA source timezone을 필수로 하며 aware timestamp의 내장 offset은 우선한다.
- exact Method → Business Activity mapping은 append-only version과 `KEEP_SOURCE`,
  `GROUP_AS_UNMAPPED`, `EXCLUDE` 정책을 제공한다. Source/Business DFG는 동일 API의 optional context다.
- Dataset source, normalized, quarantine artifact의 size/active/pinned 상태를 추적한다. 자동 삭제는 하지 않는다.
- Local Path Import는 configured allowed roots에 한정하고 COPY를 기본값으로 한다. REFERENCE는 source drift를
  감지하면 `SOURCE_CHANGED`가 되어 기존 READY 분석을 조용히 재사용하지 않는다.
- 5M benchmark는 source generation과 application processing을 분리한다. 20M은 명시적 확인과 disk preflight가
  필요한 수동 작업이며 CI 범위가 아니다.
