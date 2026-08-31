# 프로세스 마이닝 계산 규격

## 1. 분석 입력 계약
모든 계산은 최소 다음 컬럼을 요구한다.
- case_id
- activity
- event_ts

모든 필터는 event log에 적용되되, case-level 필터와 event-level 필터를 구분한다.

## 2. Case Count
`COUNT(DISTINCT case_id)`

## 3. Event Count
`COUNT(*)`

## 4. Activity Frequency
activity별 event 수 및 case 수를 동시에 제공한다.

## 5. Start / End Activity
case별 첫 event / 마지막 event의 activity.
동률은 DATA_MODEL의 정렬 규칙으로 결정한다.

## 6. Directly-Follows Graph (DFG)
각 case의 정렬된 이벤트에서 바로 다음 activity를 연결한다.

예:
```text
A,B,C,C,D
→ A→B, B→C, C→C, C→D
```

Edge 지표:
- transition_count
- distinct_case_count
- transition_case_share
- median_delta_ms
- p90_delta_ms

## 7. Throughput Time
case 마지막 event_ts - 첫 event_ts.

집계:
- average
- median
- p75
- p90
- p95
- max

평균만 기본 KPI로 쓰지 않는다. 긴 꼬리 분포를 고려하여 median/p90을 함께 표시한다.

## 8. Transition Time / Waiting Proxy
다음 event의 timestamp - 현재 event의 timestamp.
메서드 로그에서는 순수 대기시간과 실행시간이 섞일 수 있으므로 UI 명칭을 초기에는 `전이 소요시간`으로 사용하고 업무적 의미가 확인된 후 `대기시간`으로 변경한다.

## 9. Variant
case별 ordered activity sequence를 canonical sequence로 생성하고 hash한다.

지표:
- rank
- sequence
- case_count
- case_share
- median throughput
- p90 throughput
- average events per case
- rework rate

Noise 제어:
- Top-N variants
- cumulative case coverage

## 10. Rework
동일 case에서 동일 activity가 2회 이상 발생한 경우 activity rework로 정의하는 1차 규칙.

지표:
```text
rework_case_rate = cases_with_rework / total_cases
```
추후 업무별 정상 반복을 제외하기 위한 rule table을 지원한다.

## 11. Self-loop
DFG에서 A→A. 반복 저장/재처리/재시도 가능성의 신호로 표시하되 곧바로 업무 오류로 단정하지 않는다.

## 12. Bottleneck Score
MVP에서는 단일 마법 점수보다 다음 지표를 함께 제공한다.
- transition frequency
- median transition time
- p90 transition time
- affected case count
- case share

선택적 정규화 score는 UI 정렬용으로만 사용하고 원 지표를 항상 공개한다.

## 13. Failure / Error Analysis
result_code가 존재하면:
- activity별 failure rate
- edge별 failure 이후 경로
- failure case throughput
- success/failure variant 비교

## 14. Path Search
사용자가 `A → B → C` 포함 case를 조회 가능해야 한다.
모드:
- exact contiguous path
- ordered contains path

대규모 검색은 SQL window/sequence 전략으로 구현하고 API에서 제한을 둔다.

## 15. Compare Mode
두 필터 집합 A/B 비교:
- case volume delta
- throughput delta
- rework delta
- activity frequency delta
- edge frequency delta
- variant share delta

예: 기간 전/후, 조직 A/B, 성공/실패.

## 16. Conformance Checking — Phase 3
참조 프로세스 모델이 확정된 경우 수행.
후보:
- token-based replay
- alignment-based diagnostics
- fitness
- deviation paths

MVP 필수 범위가 아니다.

## 17. 통계 주의사항
- 전체 평균 하나만으로 병목 판단 금지
- case 수가 매우 적은 edge는 경고 표시
- 필터로 case 일부 event만 잘릴 때 throughput 정의가 왜곡될 수 있음
- timestamp timezone/clock skew를 품질 체크
- batch log는 일반 사용자 업무와 별도 process domain으로 분리 고려
