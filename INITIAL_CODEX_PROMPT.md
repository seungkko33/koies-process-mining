# Codex 첫 개발 시작 프롬프트

아래 프롬프트를 저장소 루트에서 Codex에 전달한다.

---

이 저장소는 공제정보망 2,000만 건 이상의 메서드 로그를 로컬에서 분석하는 프로세스 마이닝 플랫폼이다.

작업을 시작하기 전에 반드시 `AGENTS.md`, `PRD.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `PROCESS_MINING_SPEC.md`, `SECURITY.md`, `PERFORMANCE.md`, `TEST_STRATEGY.md`를 읽어라.

이번 작업은 **Phase 0/1 기반 프로젝트 skeleton 구축**이다. 실제 운영 데이터는 사용하지 말고 합성 데이터만 사용하라.

목표:
1. Python FastAPI backend와 React+TypeScript frontend의 기본 디렉터리 구조를 만든다.
2. DuckDB 연결/설정 모듈을 만든다.
3. `config/app.example.yaml`을 읽는 설정 구조를 만든다.
4. 테스트용 합성 Event Log generator를 만든다.
5. 3개 case 정도의 golden fixture를 만든다.
6. DuckDB에서 DFG를 계산하는 최소 analytics 모듈과 unit test를 만든다.
7. `/health`와 `/api/overview`의 최소 API skeleton을 만든다.
8. README에 실행 명령을 갱신한다.

제약:
- 실제 데이터가 필요하다고 요청하지 말라.
- Pandas에 전체 dataset을 올리는 구조를 만들지 말라.
- PM4Py를 dependency로 추가하지 말라.
- raw data, *.parquet, *.duckdb, .env가 git에 들어가지 않게 `.gitignore`를 작성하라.
- SQL은 parameterized query를 사용하라.
- 모든 계산은 `PROCESS_MINING_SPEC.md` 정의를 따라라.
- 변경 완료 후 테스트, typecheck/lint 결과와 미해결 위험을 보고하라.

이 작업에서는 화려한 UI보다 **데이터 계약, 테스트, DuckDB 분석의 정확성**을 우선하라.

---
