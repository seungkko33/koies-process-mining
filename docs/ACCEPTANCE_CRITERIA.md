# 개발 Acceptance Criteria 체크리스트

## 데이터 기반
- [ ] 합성 golden event dataset 존재
- [ ] 실제 데이터가 repository에 없음
- [ ] event ordering deterministic
- [ ] mapping version 추적
- [ ] case rule version 추적

## 분석 정확성
- [ ] DFG 손계산 결과 일치
- [ ] Variant 손계산 결과 일치
- [ ] Rework 손계산 결과 일치
- [ ] Throughput percentile 테스트
- [ ] 동일 timestamp tie-breaker 테스트

## 성능
- [ ] 1M benchmark
- [ ] 5M benchmark
- [ ] 20M benchmark 계획 또는 결과
- [ ] full Pandas materialization 없음
- [ ] API result limit

## 보안
- [ ] PII fixture 없음
- [ ] raw params application logging 없음
- [ ] `.env`/data gitignore
- [ ] external AI default off
- [ ] SQL injection test

## UX
- [ ] loading/error/empty 구분
- [ ] filter summary
- [ ] graph threshold
- [ ] metrics에 단위/정의 제공

## File Ingestion Vertical Slice (2026-09-01)
- [x] Browser CSV/CSV.GZ/Parquet chunk upload와 UUID staging
- [x] DuckDB direct scan schema/fast profile
- [x] server-bounded preview (max 200)
- [x] versioned Event Log mapping과 timestamp parse preview
- [x] technical validation, quarantine, normalized ZSTD Parquet
- [x] READY Dataset → 기존 Overview/DFG datasource
- [x] Dataset list/import/profile/mapping/quality/analyze UI
- [x] unsupported format/signature/path traversal/orphan cleanup tests
- [x] 100K ingestion benchmark
- [x] 1M optional ingestion benchmark
- [x] 5M manual ingestion benchmark
- [x] 20M guard/preflight와 명시적 실행 계획
- [ ] 실제 공제정보망 case/timestamp/activity/PII 의미 검증

## Semantic Contract and scale readiness (2026-09-01)

- [x] versioned Semantic Contract와 Raw/Parsed/UTC/Display timestamp preview
- [x] IANA timezone validation, UTC canonical storage, DST-capable ICU conversion
- [x] PII classification, attribute retention, optional keyed HMAC
- [x] exact versioned Method → Business Activity mapping과 coverage
- [x] Source/Business DFG switch와 provenance metadata
- [x] allowed-root Local Path COPY/REFERENCE와 source drift detection
- [x] atomic normalized/quarantine finalization과 protected artifact cleanup
- [x] expanded semantic/technical data quality regression
- [x] reusable-source 5M benchmark와 machine-readable JSON result
- [ ] trusted in-app browser screenshot/DOM/console/responsive QA
