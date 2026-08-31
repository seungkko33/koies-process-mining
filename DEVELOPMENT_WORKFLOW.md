# 개발 및 바이브 코딩 워크플로

## 1. 원칙
AI에게 “프로세스 마이닝 앱 전체를 만들어줘”라고 한 번에 요청하지 않는다. PRD의 epic을 작은 vertical slice로 쪼개고 테스트와 함께 구현한다.

## 2. 권장 저장소 구조
```text
repo/
├ AGENTS.md
├ PRD.md
├ ARCHITECTURE.md
├ docs/
├ backend/
│  ├ app/
│  │  ├ api/
│  │  ├ analytics/
│  │  ├ ingestion/
│  │  ├ repositories/
│  │  ├ schemas/
│  │  └ security/
│  └ tests/
├ frontend/
│  ├ src/
│  │  ├ api/
│  │  ├ components/
│  │  ├ features/
│  │  ├ pages/
│  │  └ types/
│  └ tests/
├ sql/
├ config/
├ scripts/
└ data/ # ignored
```

## 3. 브랜치
- `main`: 항상 실행 가능한 상태
- `feat/<name>`
- `fix/<name>`
- `docs/<name>`

개인 단독 개발이어도 checkpoint commit을 자주 만든다.

## 4. AI 작업 단위 템플릿
```text
목표:
관련 요구사항:
수정 허용 파일:
수정 금지 파일:
입력/출력 계약:
보안 제약:
성능 제약:
Acceptance Criteria:
반드시 실행할 테스트:
```

## 5. 권장 첫 구현 순서
1. repository skeleton
2. synthetic event generator
3. DuckDB connection/config
4. schema
5. golden event fixture
6. DFG SQL + test
7. variant SQL + test
8. overview API
9. frontend overview
10. process map API/UI

## 6. AI 코드 검토 질문
매 작업 후 AI에게 별도 검토 세션에서 질문:
- 전체 데이터를 메모리에 올리는 부분이 있는가?
- SQL injection 위험이 있는가?
- PII가 로그에 남는가?
- 계산 정의가 spec과 일치하는가?
- 20M events에서 병목이 될 부분은?
- 테스트가 구현을 실제로 검증하는가?

## 7. Git에 포함하면 안 되는 것
- raw data
- parquet operational data
- duckdb files
- .env
- credentials
- screenshots containing PII

## 8. 문서 중심 운영
OpenAI Codex의 AGENTS.md는 목차/가이드 역할로 사용하고 세부 지식은 docs에 유지한다. 작업이 끝나면 코드뿐 아니라 설계 문서가 현재 구현을 반영하는지 확인한다.
