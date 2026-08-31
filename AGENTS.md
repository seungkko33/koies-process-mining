# AGENTS.md — 공제정보망 프로세스 마이닝 프로젝트 AI 개발 지침

## 0. 이 파일의 역할
이 파일은 Codex 및 유사 코딩 에이전트가 저장소를 수정할 때 반드시 따라야 하는 최상위 작업 규칙이다. 세부 설계의 단일 진실 공급원(System of Record)은 각 전문 문서이며, 이 파일은 길게 모든 것을 반복하지 않고 작업 방향과 금지사항을 제공한다.

## 1. 먼저 읽을 문서
작업 시작 시 아래 순서대로 관련 문서를 읽는다.

1. `PRD.md`
2. `ARCHITECTURE.md`
3. `DATA_MODEL.md`
4. `PROCESS_MINING_SPEC.md`
5. `SECURITY.md`
6. `PERFORMANCE.md`
7. `UI_UX_SPEC.md`
8. `TEST_STRATEGY.md`
9. `DEVELOPMENT_WORKFLOW.md`
10. 해당 작업과 연관된 `docs/` 문서

설계와 코드가 충돌하면 임의로 코드를 우선하지 말고 문서의 요구사항을 기준으로 판단한다. 요구사항 자체가 모순되면 변경 범위를 최소화하고 TODO/Decision 항목으로 남긴다.

## 2. 아키텍처 원칙
- Local-first: 실제 로그 데이터는 로컬 경계 안에서 처리한다.
- SQL-first: 대규모 집계는 가능한 한 DuckDB SQL에서 수행한다.
- Stream/scan-first: 2천만 건 전체를 Python 메모리에 적재하지 않는다.
- Parquet-first: 원천 스냅샷 및 정규화 데이터의 기본 파일 포맷은 Parquet이다.
- API는 집계 결과를 제공하며 대량 원천행을 반환하지 않는다.
- Frontend는 계산 로직을 소유하지 않는다. 계산 정의는 backend/query layer에 둔다.
- 비즈니스 activity 명칭과 기술 method 명칭을 분리한다.
- case_id 생성 규칙은 명시적·버전 관리 가능해야 한다.
- 분석 결과는 재현 가능해야 하며 사용한 필터/규칙 버전을 함께 기록한다.

## 3. 데이터 보안 절대 규칙
- 실제 운영 로그, 주민번호, 계좌번호, 전화번호, 이메일, 주소, 인증토큰, 세션토큰, 내부식별자 원문을 코드/테스트/프롬프트에 삽입하지 않는다.
- 샘플 데이터는 완전 합성 데이터만 사용한다.
- raw data 경로는 `.gitignore` 대상이어야 한다.
- 데이터 export 기능은 기본 비활성화 또는 명시적 사용자 작업으로 제한한다.
- 외부 AI API 호출 코드가 원천 데이터나 case 단위 세부 데이터를 전송하지 않도록 한다.
- 로깅 시 SQL 바인드 값, 원본 params_json, PII가 출력되지 않게 한다.
- 모든 민감 필드는 ingestion 단계에서 masking/hash/tokenization 전략을 적용할 수 있도록 설계한다.

## 4. DuckDB 사용 규칙
- 무분별한 `SELECT *`를 API 경로에서 사용하지 않는다.
- 대량 쿼리는 projection/filter pushdown을 살릴 수 있도록 필요한 컬럼만 선택한다.
- 메모리 제한과 temp directory는 설정 파일에서 조절 가능해야 한다.
- 메모리가 부족한 환경을 고려하여 `threads`, `memory_limit`, `temp_directory`, `preserve_insertion_order` 설정을 노출한다.
- 대량 테이블에 인덱스를 자동으로 생성하지 않는다. 성능 측정으로 효과가 입증된 경우만 추가한다.
- 중복된 복잡 SQL은 view 또는 query module로 추출한다.
- 대규모 `list()`/`string_agg()`/PIVOT 사용은 OOM 가능성을 검토한다.

## 5. Python 규칙
- Python 데이터 처리에서 Pandas 전체 적재를 기본 패턴으로 사용하지 않는다.
- 가능하면 DuckDB relation/SQL, Arrow batch, Polars lazy 연산을 사용한다.
- 함수는 타입 힌트를 제공한다.
- API 요청/응답은 Pydantic schema로 명시한다.
- 데이터 접근 계층과 API 계층을 분리한다.
- SQL 문자열 조립 시 사용자 입력을 직접 보간하지 않는다.
- 비즈니스 지표 정의는 코드 곳곳에 중복하지 않는다.

## 6. Frontend 규칙
- React + TypeScript.
- 서버 집계 결과만 시각화한다.
- Process Map은 Cytoscape.js 기반을 우선한다.
- 일반 KPI/차트는 ECharts 기반을 우선한다.
- 1만 개 이상의 node/edge를 한 번에 렌더링하지 않는다. 빈도/비율 threshold 및 Top-N 필터를 둔다.
- 모든 차트 선택은 전역 필터 상태와 연결하되, 무한 상호 업데이트가 발생하지 않게 한다.
- URL 또는 명시적인 query state로 필터 재현성을 지원하는 방향을 유지한다.

## 7. 프로세스 마이닝 계산 규칙
아래 세 컬럼이 정상화되기 전에는 고급 분석을 구현하지 않는다.
- `case_id`
- `activity`
- `event_ts`

동일 timestamp 이벤트의 정렬 기준을 명시한다. 권장 우선순위:
1. event_ts
2. source_sequence
3. ingest_sequence

핵심 지표의 정의는 `PROCESS_MINING_SPEC.md`를 따른다.

## 8. PM4Py 규칙
- MVP의 필수 의존성으로 추가하지 않는다.
- 별도 adapter/interface 뒤에 둔다.
- 오픈소스 PM4Py는 AGPL-3.0이므로 조직의 라이선스 검토 또는 상용 라이선스 확인 전 제품 핵심 경로에 결합하지 않는다.
- PM4Py와 자체 SQL 계산의 결과가 비교 가능한 테스트를 만든다.

## 9. 변경 작업 방식
한 번의 작업은 가능한 한 하나의 목적만 가진다.

작업 전:
1. 관련 문서 확인
2. 영향 파일 확인
3. 테스트 전략 결정
4. 데이터 보안 영향 확인

작업 후:
1. formatter/linter
2. unit tests
3. affected integration tests
4. 변경 요약
5. 남은 위험/미검증 항목 보고

## 10. Definition of Done
기능은 다음을 만족해야 완료다.
- 요구사항 또는 acceptance criteria에 연결됨
- 테스트 추가/수정
- 민감정보 노출 없음
- 대용량 처리 경로에서 전체 메모리 적재 없음
- 오류 처리와 사용자 메시지 존재
- 필요한 문서 업데이트
- 주요 SQL은 작은 fixture로 결과 검증
- 성능에 민감한 기능은 최소 benchmark 결과 기록

## 11. 절대 금지
- 테스트를 통과시키기 위해 실제 요구사항을 삭제/완화
- 오류를 숨기기 위한 무차별 try/except
- 타입 오류를 `Any` 남용으로 회피
- API에서 무제한 rows 반환
- 운영 데이터 경로 hardcoding
- raw 로그를 클라우드 AI로 전송
- case_id를 임의의 row number로 확정
- method_name을 그대로 business activity로 단정
- 라이선스 검토 없이 AGPL 코드를 복사/내장

## 12. 응답 형식 권장
코딩 에이전트가 작업 완료를 보고할 때 아래를 포함한다.
- 변경한 내용
- 왜 그렇게 설계했는지
- 실행한 테스트
- 성능 영향
- 보안 영향
- 미해결 항목

## 13. 외부 OSS Reference 사용 규칙
- 공개 소스 조사/적용 전에 `OPEN_SOURCE_REFERENCE_GUIDE.md`를 읽는다.
- `_references/`는 읽기 전용 참고 clone이며 제품 Git history에 포함하지 않는다.
- 외부 코드를 본 직후 바로 구현하지 말고 먼저 `docs/REFERENCE_ADOPTION_PLAN.md`를 작성한다.
- PM4Py/GPL/AGPL source를 제품 코드에 복사하거나 line-by-line 변형하지 않는다.
- permissive OSS도 dependency/NOTICE/license 조건을 기록한다.
- 외부 reference를 사용한 작업 완료 보고에는 저장소명, 라이선스, 적용 방식, 직접 복사 여부를 명시한다.
