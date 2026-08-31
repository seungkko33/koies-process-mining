# CLAUDE.md — Claude Code 프로젝트 지침

이 저장소의 최상위 공통 개발 규칙은 `AGENTS.md`를 기준으로 한다. Claude Code는 작업 시작 전에 `AGENTS.md`와 해당 기능의 전문 문서를 먼저 읽는다.

## 우선순위
1. 데이터 보안
2. 분석 결과의 정확성/재현성
3. 대용량 처리 안정성
4. 단순한 구조
5. UI 편의성
6. 구현 속도

## 프로젝트 핵심 문장
**AI가 2천만 건을 직접 분석하는 프로그램이 아니라, DuckDB가 계산하고 AI가 개발과 해석을 보조하는 로컬 프로세스 마이닝 플랫폼을 만든다.**

## 작업 시 행동 규칙
- 대규모 데이터 처리 코드는 먼저 SQL/DuckDB 접근을 검토한다.
- Pandas `read_*`로 전체 원천 데이터를 적재하는 코드를 만들지 않는다.
- 실제 데이터를 요구하지 말고 schema 또는 합성 fixture로 개발한다.
- PII가 포함될 수 있는 컬럼은 출력하지 않는다.
- 코드를 크게 재구성하기 전 관련 문서와 현재 테스트를 확인한다.
- 불명확한 요구사항은 가장 보수적인 데이터/보안 가정을 택하고 문서에 가정을 기록한다.

## 구현 전 체크
- 이 기능이 raw/staging/curated/aggregate 중 어느 계층인가?
- case_id와 activity 정의에 영향을 주는가?
- 전체 범위 쿼리에서 2천만+ events를 어떻게 처리하는가?
- API 응답 크기 제한은 있는가?
- 필터가 SQL까지 pushdown 되는가?
- 사용자 입력이 SQL injection에 안전한가?
- 기능이 실제 로그를 외부로 내보낼 가능성이 있는가?

## 문서 동기화
다음 변경은 반드시 문서도 함께 갱신한다.
- DB schema → `DATA_MODEL.md`
- 분석식 → `PROCESS_MINING_SPEC.md`
- API contract → `PRD.md` 및 API 문서
- 보안 정책 → `SECURITY.md`
- 성능 설정/벤치마크 → `PERFORMANCE.md`
- UI 흐름 → `UI_UX_SPEC.md`
