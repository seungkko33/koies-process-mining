# 보안·개인정보·AI 사용 통제 설계

## 1. 기본 원칙
공제정보망 로그는 메서드 변수에 개인정보, 계약/청구번호, 인증정보, 내부 시스템 구조가 포함될 수 있다고 가정한다. 따라서 프로그램은 데이터 최소화와 로컬 처리 원칙을 기본값으로 갖는다.

## 2. Trust Boundary
```text
[운영 시스템] --export--> [로컬 보안 영역]
                              ├ Raw
                              ├ Curated
                              ├ DuckDB
                              ├ Backend
                              └ Frontend

[외부 AI] <--- raw/case detail 전송 금지 ---X--- [로컬 보안 영역]
```

## 3. 데이터 분류
- S0 공개/비민감: 기술 문서, 합성 샘플
- S1 내부: 메서드명, 모듈명, 구조
- S2 기밀: 조직/사용자 연계 로그
- S3 민감: 개인정보, 계약/청구정보, 인증정보

S2/S3는 외부 AI 프롬프트에 포함하지 않는다.

## 4. Ingestion 통제
- raw 파일 읽기 전 파일 권한 확인
- 원천 checksum 기록
- params_raw는 즉시 필요한 key만 추출
- 추출 후 curated 계층에는 raw params를 기본 미보존
- PII column 자동 검사 규칙 지원

## 5. 비식별
- case key: HMAC tokenization 권장
- actor/user: 별도 HMAC namespace
- IP: 필요 없으면 제거, 필요 시 prefix/generalization
- 자유 텍스트: 기본 분석 대상에서 제외

## 6. Secret 관리
- `.env`는 git 제외
- HMAC secret, DB credential, API key를 코드에 작성 금지
- 운영 배포 시 OS secret store 또는 사내 보안 표준 적용

## 7. API 통제
MVP가 단일 사용자 localhost라 하더라도 다음을 적용한다.
- CORS 최소화
- query param validation
- response row limit
- path traversal 방지
- SQL injection 방지
- export endpoint 별도 권한/확인

사내 다중 사용자 전환 시:
- SSO/사내 인증
- RBAC
- 분석 대상 업무 권한
- 감사로그

## 8. AI 기능 정책
외부 AI 허용 입력:
- schema
- 컬럼 통계(민감값 제외)
- 집계 결과
- 비식별된 소량 예제
- 소스코드

금지 입력:
- raw params
- 원 case_id
- 주민번호/계좌/전화/이메일
- 토큰/credential
- 사용자별 상세 event history

자연어→SQL 기능을 제공하면:
1. 허용된 view만 대상
2. SELECT only
3. LIMIT 강제
4. statement parser 검증
5. 실행 전 비용/범위 제한
6. 가능하면 사용자 승인 후 실행

## 9. 로깅
애플리케이션 로그에 기록 가능:
- endpoint
- query duration
- result row count
- filter field names
- error code

기록 금지:
- raw SQL에 포함된 민감 literal
- 원 params_json
- secret
- 원 사용자 식별자

## 10. Git 정책
`.gitignore` 필수:
```text
/data/
/db/
*.duckdb
*.parquet
*.csv
.env
logs/
```
합성 fixture만 `tests/fixtures/`에 허용한다.

## 11. 보안 검토 게이트
- Phase 0: 데이터 분류/PII 탐지
- Phase 1: masking rule 검증
- Phase 2: UI 노출 검토
- Phase 4: AI 기능 threat review
