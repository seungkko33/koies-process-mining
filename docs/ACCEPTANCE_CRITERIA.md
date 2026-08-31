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
