# ADR-004: Dataset 및 Mapping Versioning

## Status
Accepted for the ingestion MVP.

## Context
동일 source 파일은 서로 다른 case 정의나 activity/timestamp 매핑으로 분석될 수 있다. 매핑 변경이
원본을 수정하거나 이전 분석의 의미를 암묵적으로 바꾸면 재현성이 깨진다.

## Decision
- 업로드마다 UUID `dataset_id`, SHA-256 checksum, file size, schema version을 기록한다.
- MappingDefinition은 Dataset 안에서 증가하는 정수 `version`을 갖고 append-only로 저장한다.
- 새 mapping은 source를 재수집하지 않으며 새 `events-vN.parquet`과 `quarantine-vN.parquet`을 만든다.
- Dataset의 `mapping_version`/`normalization_version`은 현재 분석에 선택된 최신 산출물을 가리킨다.
- Dataset이 `READY`일 때만 Overview/DFG datasource로 사용할 수 있다.
- 이번 MVP는 이전 version 파일을 자동 삭제하지 않는다. Dataset 전체 삭제만 명시적으로 제공한다.

## Consequences
source와 mapping의 provenance가 유지되고 재정규화가 가능하다. 다만 mapping version이 누적될수록
디스크 사용량이 증가하며, 과거 version 선택/정리 정책은 후속 Phase에서 별도로 설계해야 한다.

## Revisit Trigger
- mapping rollback/과거 version 비교 UI가 필요할 때
- 보존 기간 또는 storage quota가 정해질 때
