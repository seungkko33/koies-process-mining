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
