# UI/UX 상세 규격

## 1. 제품 사용 시나리오
사용자는 프로세스 전문가가 아닌 업무 담당자/관리자도 포함한다. 따라서 화면은 “복잡한 그래프를 보여주는 도구”보다 “업무 흐름의 문제를 찾고 근거 case까지 추적하는 분석 도구”여야 한다.

## 2. 정보 구조
```text
1. Overview
2. Process Map
3. Variants
4. Performance / Bottleneck
5. Rework / Error
6. Case Explorer
7. Compare
8. Data Quality
9. Mapping & Rules
10. Settings
```

## 3. Global Filter
상단 고정 또는 접이식 패널.
- Date range
- Process domain
- Organization
- Activity include/exclude
- Result code
- Case attribute
- Variant
- Minimum case frequency
- Mapping version

필터 적용 시 현재 조건을 `Filter Summary`로 사람이 읽을 수 있게 표시한다.

## 4. Overview
### KPI 카드
- Cases
- Events
- Activities
- Median Throughput
- P90 Throughput
- Rework Rate
- Failure Rate(가능 시)

### Charts
- case volume trend
- throughput trend
- top activities
- top bottleneck transitions
- variant concentration

## 5. Process Map
### 기본 레이아웃
좌→우 흐름.
Start/End는 명확히 분리.

### Node
표시:
- activity name
- case count 또는 event count
- frequency share
- 성능 mode에서는 median processing/transition 관련 값

### Edge
- from → to
- transition count
- case count
- median/p90 time

### Noise control
- case coverage slider
- edge threshold
- top activities
- hide self-loop option

### Interaction
- Node click → side panel
- Edge click → side panel
- Double click → 해당 activity/edge로 filter
- Reset view
- Fit graph
- Export image는 민감정보 노출 경고 포함

## 6. Variant Explorer
Table columns:
- rank
- compact sequence
- case count
- share
- median throughput
- p90 throughput
- rework rate
- failure rate

선택 시 오른쪽에 mini-process visualization.

## 7. Performance
- transition duration distribution
- activity/edge heatmap
- percentile chart
- slowest cases table (비식별 id)

## 8. Rework/Error
- rework activity ranking
- self-loop ranking
- repeated path
- result code distribution
- error 이후 대표 경로

## 9. Case Explorer
### 검색
- hashed case id
- 기간
- variant
- activity 포함

### 상세
Timeline:
```text
09:01 접수
09:03 검증
09:11 보완요청
10:02 검증
10:05 승인
```
민감 raw params는 기본 숨김/미적재.

## 10. Compare
좌 A, 우 B filter set.
차이 강조:
- volume
- throughput
- rework
- DFG edges
- variants

## 11. Data Quality
필수 화면.
- ingestion batch
- rejected rows
- missing case
- unmapped activity
- timestamp errors
- mapping conflicts
- duplicate rate

품질 경고가 임계치를 넘으면 분석 화면에 banner 표시.

## 12. Mapping & Rules
관리자/개발자 기능.
- method → activity mapping
- rule priority
- test mapping against synthetic/sample metadata
- version publish
- rollback

## 13. 사용자 메시지
“데이터가 없습니다”와 “쿼리 실패”를 구분한다.
장시간 분석 시 loading 상태와 취소 가능성을 제공한다.

## 14. 접근성/가독성
- 색만으로 상태 구분하지 않는다.
- 수치에 단위 표기
- 긴 activity 이름 tooltip
- graph legend 제공
- 모든 주요 결과를 table로도 확인 가능하게 한다.

## 15. Dataset workspace

좌측 `Datasets` navigation은 `/datasets/import`와 동등한 단일 workspace를 제공한다.

1. **Import**: file picker와 drag/drop, CSV/CSV.GZ/Parquet 안내, filename/size, upload progress,
   profiling/failed 상태
2. **Dataset List**: filename, type, size, row count, status, 생성 시각, 명시적 삭제
3. **Profile**: inferred schema, observed null, approximate distinct, min/max, bounded sample과 최대 20행
   table preview
4. **Event Mapping**: case/activity/timestamp 필수 dropdown, event id 및 method/status/duration/system/
   source sequence 선택, timestamp format/timezone, parse preview
5. **Data Quality**: total/valid/invalid, unique case/activity, null/empty/invalid timestamp, duplicate,
   single-event case 및 outcome
6. **Analyze**: READY Dataset을 global selection으로 설정하고 Overview 또는 Process Map으로 이동

상태는 색뿐 아니라 `UPLOADING`, `PROFILING`, `MAPPING_REQUIRED`, `VALIDATING`, `READY`, `FAILED`
text label로 표시한다. 브라우저는 file을 parsing하지 않고 upload progress만 계산한다. profile/preview는
bounded API 응답만 렌더링하며 20M row table이나 arbitrary raw data browser를 제공하지 않는다.

## Semantic/Activity/Lifecycle workspace

- Semantic Contract: source column profile, explicit case/activity/timestamp, source/display timezone, case PII/HMAC,
  deterministic ordering 설명과 Raw/Parsed/UTC/Display preview
- Data Quality: technical outcome과 semantic warning 분리, same timestamp events, ambiguous cases,
  events-per-case distribution, large cases
- Activity Mapping: frequency descending exact mapping table, search, mapped/unmapped filter, three unmapped policies,
  activity/event coverage, append-only version select/create
- Process Map: Source Activity/Business Activity switch와 source/business count, coverage, displayed node/edge,
  contract/activity/normalization provenance
- Artifacts: raw/normalized/quarantine/previous/temp/total disk usage, active/pinned 표시, 보호 상태를 반영한 cleanup
- Local Path: 사용자가 이미 알고 있는 allowed absolute path 입력만 제공하고 directory browser는 제공하지 않음

percentage를 추정하지 않는다. operation이 실행 중이면 실제 current step과 elapsed 기준 metadata만 보여준다.
`SOURCE_CHANGED`는 READY와 다른 text/error state로 표시하고 재분석을 막는다.
