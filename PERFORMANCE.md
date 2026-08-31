# 대용량 성능 설계 및 벤치마크 계획

## 1. 목표 데이터 규모
초기 기준: 20,000,000+ raw/event rows.
향후 수억 건으로 증가 가능성을 고려하되, MVP를 분산 플랫폼으로 과설계하지 않는다.

## 2. 하드웨어 기준선
권장 개발 기준선:
- CPU: 8 physical/효율 코어 이상 권장
- RAM: 32 GB 최소 권장, 64 GB 선호
- Disk: NVMe SSD, 여유공간 충분히 확보
- OS: Windows 개발 가능. 대량 장기 운영은 Linux도 평가.

이 값은 구매 요구사항이 아니라 벤치마크 기준선이다.

## 3. DuckDB 설정
설정 파일에서 조절:
```yaml
duckdb:
  threads: 6
  memory_limit: 20GB
  temp_directory: D:/process-mining-temp
  preserve_insertion_order: false
```
실제 값은 PC 자원과 동시 실행 앱을 고려한다.

DuckDB 공식 문서상 out-of-core 처리가 grouping/join/sort/window에 적용되지만 복잡한 blocking operator 조합이나 일부 aggregate는 OOM이 가능하므로 쿼리 분해와 사전집계를 사용한다.

## 4. 성능 핵심 전략
1. CSV 반복 스캔 금지 → Parquet 변환
2. 필요한 column만 읽기
3. 날짜/업무 filter를 최대한 조기에 적용
4. UI 요청마다 전체 variant sequence를 재계산하지 않도록 캐시 고려
5. 1만+ graph element 렌더링 방지
6. 대규모 export는 별도 job
7. `EXPLAIN/EXPLAIN ANALYZE` 사용

## 5. Parquet 전략
- 날짜/업무 domain partition
- 너무 작은 파일 다수 생성 금지
- row group은 실제 workload로 검증
- zstd 또는 기본 압축 비교
- projection/filter pushdown 유지

## 6. 임시 성능 SLO — 실제 데이터 벤치마크 후 확정
기준선 PC에서 다음을 목표로 실측한다.

| 작업 | 잠정 목표 |
|---|---:|
| Overview, 최근 1개월 | warm 3초 이내 |
| DFG, 일반 필터 | 10초 이내 |
| Variant Top 100 | 15초 이내 |
| Case 검색 | 3초 이내 |
| 20M 전체 기본 집계 | 60초 이내를 목표로 최적화 |
| CSV→Parquet 초기 변환 | 30분 이내 목표, 원천 포맷별 실측 |

이는 제품 보장이 아니라 개발 acceptance target이다. 실제 컬럼 수·디스크·원천 파일 품질에 따라 조정한다.

## 7. 벤치마크 세트
- 100k 합성
- 1M 합성
- 5M 비식별 샘플 또는 현실형 합성
- 20M 운영형 로컬 샘플

각 규모에서:
- scan
- group by activity
- DFG
- variant
- percentile
- path search
- compare
측정.

## 8. OOM 대응
- threads 감소
- memory_limit 조정
- temp directory NVMe 지정
- 쿼리 분리
- 중간 결과 materialization
- holistic aggregate 제거/대체
- Python materialization 여부 점검

## 9. API 결과 제한
- process map nodes: 기본 100 이하
- edges: 기본 300 이하
- variants: 기본 100
- case list: page size 50~200
- raw-like event list: pagination 필수

## 10. 성능 회귀 방지
핵심 SQL마다 benchmark test를 두고 기준 대비 2배 이상 악화 시 원인 분석한다.
