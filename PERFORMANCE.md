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

## 11. Ingestion 성능 구조

- upload: `UploadFile`을 1 MiB chunk로 staging에 기록하며 같은 pass에서 SHA-256 계산
- schema: DuckDB CSV sniffer 또는 Parquet metadata 기반 `DESCRIBE SELECT`
- fast profile: 모든 column의 null/approx distinct/min/max를 단일 aggregate scan으로 계산하고,
  sample은 별도 최대 20행 scan에서 column당 최대 3개만 보존
- preview: SQL `LIMIT`과 backend hard cap 200을 함께 적용
- validation: source를 DuckDB가 직접 scan하여 mapping/flag를 임시 Parquet으로 materialize
- normalization: valid projection만 ZSTD Parquet, invalid 식별자/사유만 별도 quarantine Parquet
- analytics: normalized Parquet를 직접 scan하며 기존 projection/filter 조건을 source scan까지 전달

Python은 orchestration과 bounded metadata 변환만 수행한다. 전체 file/row list, Pandas, Python CSV
row loop를 사용하지 않는다. CSV fast profile은 안전한 parsing을 위해 raw 값 scan을 VARCHAR로
고정하고, inferred type은 별도 schema scan에서 제공한다.

현재 FastAPI의 request-scoped DuckDB connection은 Windows file handle cleanup 경합을 막기 위해
프로세스 안에서 직렬화한다. 동시 query 처리량보다 single-user local 안정성을 우선한 결정이며,
background job 또는 multi-user 요구가 생기면 long-lived connection/worker ownership을 재설계한다.

## 12. Disk 및 benchmark baseline (2026-09-01)

알려진 upload 크기의 2.5배보다 staging volume free space가 작으면 시작 전에 거부한다. 이는
최저 보호선이며 source download, staging copy, validation/normalized/quarantine Parquet, DuckDB
database와 temp spill이 동시에 존재할 수 있으므로 운영 공간 보장은 아니다.

| events | generation | staging | schema | profiling | validation | normalization | DFG | total | source bytes | normalized bytes | Python peak bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 2.375s | 0.122s | 0.133s | 0.677s | 0.416s | 0.165s | 0.156s | 4.550s | 12,597,940 | 1,170,818 | 2,384,189 |
| 1,000,000 | 40.054s | 0.388s | 0.132s | 0.919s | 2.483s | 0.548s | 0.801s | 45.918s | 126,978,863 | 12,768,747 | 2,385,887 |

Python peak은 `tracemalloc`이며 DuckDB native allocation과 OS page cache를 포함하지 않는다.
5M/20M은 자동 실행하지 않았으며 명시적 CLI로만 측정한다. source generation이 total의 대부분을
차지하므로 ingestion 비교에는 개별 단계 시간을 함께 사용한다.

## Benchmark contract

`source_generation_seconds`는 synthetic fixture 준비 시간이다. `application_processing_seconds`는 source가
준비된 뒤 staging/import, schema, profile, Semantic Contract, validation, normalization/quarantine Parquet,
DFG가 끝날 때까지의 wall-clock이다. `overall_seconds`만 generation을 포함한다. 단계 합은 Parquet write가
겹칠 수 있으므로 application total로 사용하지 않는다.

source는 `data/benchmarks/sources/`에서 `--reuse-source`로 재사용할 수 있고 source/run/result 모두 Git ignore
대상이다. JSON result에는 OS 이름, Python/DuckDB version, logical CPU, configured threads/memory, format,
free disk, DuckDB temp spill, Python tracemalloc peak을 기록한다. process RSS는 새 dependency 없이 신뢰할 수
있는 측정 경로가 없어 `null`과 사유를 명시하며 추정하지 않는다.

20M 이상은 `--confirm-large-run`이 없으면 preflight 출력 후 중단한다. estimate는 130 bytes/event source와
configured free-space multiplier를 사용하며 실제 실행 직전에도 staging storage가 free space를 다시 검사한다.
5M/20M benchmark는 CI, 일반 test command, 자동 startup에서 실행하지 않는다.

## 2026-09-01 5M measured result

환경: Windows, Python 3.14.4, DuckDB 1.5.5, logical CPU 16, DuckDB threads 6,
memory limit 20GB, CSV → ZSTD Parquet. 두 결과는 local ignored JSON으로 저장했다.

| metric | source 생성 run | 동일 source 재사용 run |
|---|---:|---:|
| events / valid / invalid | 5,000,000 / 5,000,000 / 0 | 동일 |
| cases / activities | 1,364,013 / 5 | 동일 |
| synthetic generation | 50.550s | 0.000s |
| staging/import | 1.519s | 1.018s |
| schema | 0.158s | 0.083s |
| profile | 1.872s | 1.360s |
| Semantic Contract | 1.220s | 1.143s |
| validation | 15.746s | 14.412s |
| normalized write | 3.238s | 2.758s |
| quarantine write | 0.146s | 0.118s |
| DFG | 6.582s | 6.063s |
| **KOIES application processing** | **31.092s** | **27.521s** |
| overall | 81.744s | 27.585s |
| source size | 639,342,921 B | 동일 source |
| normalized size | 95,709,755 B | 95,753,179 B |
| quarantine size | 213 B | 213 B |
| Python tracemalloc peak | 2,374,946 B | 2,374,496 B |
| DuckDB temp spill | 0 B | 0 B |

첫 run의 managed/free disk delta는 약 1.62GB였고 source reuse run은 약 740MB였다. 이는 filesystem free-space
delta이며 source, staged copy, normalized artifact, DuckDB file을 포함하고 OS allocation 차이도 있으므로 artifact
size의 정확한 합으로 해석하지 않는다. Python tracemalloc은 전체 event log가 Python heap에 올라가지 않았음을
뒷받침하지만 DuckDB native memory/RSS 상한 증거는 아니다.
