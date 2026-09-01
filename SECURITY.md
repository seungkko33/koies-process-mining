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

## 12. Uploaded Dataset 경계

- Browser Upload만 허용하며 arbitrary local path/browsing API는 제공하지 않는다.
- client filename은 basename 검증 후 표시용으로만 저장한다. 실제 저장명은 UUID directory 아래
  `source.csv`, `source.csv.gz`, `source.parquet`으로 고정한다.
- UUID와 모든 상대 경로를 resolve하여 staging/curated/quarantine/temp root 밖 접근을 차단한다.
- 허용 확장자는 CSV/CSV.GZ/Parquet뿐이며 Parquet `PAR1`, gzip magic 및 기본 CSV text signature를
  확인한 뒤 DuckDB parser로 실제 format을 검증한다.
- DuckDB file path와 query filter 값은 bound parameter로 전달한다. column identifier만 탐지된 schema와
  mapping allowlist를 검증한 뒤 SQL identifier quoting한다.
- exception/API error에는 Dataset 원문 값이나 parser 내부 literal을 노출하지 않는다.
- profile sample과 preview는 API 응답에만 제한적으로 포함하며 application log에는 기록하지 않는다.
- quarantine에는 raw column을 복제하지 않고 source row number와 technical failure code만 기록한다.
- Dataset 삭제는 검증된 UUID의 정확한 하위 directory만 제거한다.

실제 data, `*.csv`, `*.parquet`, `*.duckdb`, `.env`는 Git에서 제외하며 오직 완전 합성
`backend/tests/fixtures`만 명시적으로 허용한다. 이 Phase에는 외부 API/AI 호출 경로가 없다.

## Local Path Import

- `dataset_import.allowed_roots`가 비어 있으면 endpoint는 disabled다.
- absolute/canonical resolution 뒤 allowed root descendant인지 확인하며 relative path, `..`, symlink escape,
  directory, unexpected extension, Windows device path, 명시적으로 허용하지 않은 UNC를 차단한다.
- 임의 directory listing이나 filesystem browsing API를 제공하지 않는다.
- COPY가 기본값이다. REFERENCE는 checksum/size/mtime을 manifest에 보존하고 mapping/normalization/analysis
  전에 재검증한다. drift error에는 실제 path나 raw content를 포함하지 않는다.

## PII와 pseudonymization

column classification은 `NONE`, `POTENTIAL_PII`, `PII`, `SENSITIVE`이고 최종 판단은 사용자 contract다.
optional attribute retention은 KEEP/DROP/PSEUDONYMIZE이며 explicit mapping되지 않은 raw column은 normalized
Parquet에 복제하지 않는다. PII/SENSITIVE optional attribute는 retention 미지정 시 DROP이다.

case pseudonymization은 keyed HMAC-SHA256이다. key-derived inner/outer pad만 bound BLOB parameter로 DuckDB
vector SQL에 전달하며 plain SHA-256 case hashing을 사용하지 않는다. secret은 configured environment variable에서
읽고 repository/YAML/DB/log/error에 기록하지 않는다. 비활성 Dataset은 secret 없이 기존 기능이 동작한다.
