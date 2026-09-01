# ADR-003: CSV/Parquet source에서 normalized Parquet 생성

## Status
Accepted for the ingestion MVP.

## Context
CSV는 반복 분석에 비효율적이고 source schema가 분석 계약과 다르다. Parquet source도 사용자가
선택한 case/activity/timestamp 의미와 기술적 validation을 반영한 canonical Event Log가 필요하다.

## Decision
- CSV, CSV.GZ, Parquet 모두 DuckDB가 직접 scan한다. Python은 row를 파싱하지 않는다.
- mapping version별 validation 결과를 임시 Parquet으로 한 번 materialize하고, DuckDB SQL로
  valid normalized Event Log와 quarantine을 분리한다.
- normalized 파일은 `data/parquet/curated/{dataset_id}/events-v{mapping_version}.parquet`이다.
- `COPY ... FORMAT PARQUET`, ZSTD compression, row group 122,880을 사용한다.
- source staging 파일은 immutable로 취급하며 mapping 변경으로 덮어쓰지 않는다.
- partitioning은 실제 date/domain query 분포가 확인되기 전에는 적용하지 않는다.

## Consequences
분석은 canonical schema와 columnar scan을 사용하고, source 재업로드 없이 재정규화할 수 있다.
대신 source, staging, 임시 validation, normalized, quarantine 및 DuckDB spill 공간이 동시에 필요할
수 있다. 구현은 업로드 전에 알려진 크기의 2.5배 여유 공간을 보수적으로 확인한다.

## Revisit Trigger
- 20M 실제형 합성 benchmark에서 단일 Parquet row-group 또는 파일 크기가 SLO를 충족하지 못할 때
- 날짜/업무 domain filter 분포가 안정되어 partition pruning 이점이 검증될 때

