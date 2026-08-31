# Reference Adoption Prompt — Codex / Claude Code

먼저 다음 파일을 반드시 읽어라.

1. `AGENTS.md`
2. `PRD.md`
3. `ARCHITECTURE.md`
4. `LICENSE_POLICY.md`
5. `OPEN_SOURCE_REFERENCE_GUIDE.md`
6. 현재 작업과 관련된 specification/test 문서

그 다음 `_references/` 아래 공개 저장소를 조사하되 **어떤 코드도 바로 제품 소스로 복사하지 마라.**

## 1단계 — Reference 분석
현재 feature와 직접 관련 있는 reference 파일만 골라 분석한다.

`docs/REFERENCE_ADOPTION_PLAN.md`에 아래 표를 작성한다.

| Target Feature | Reference Repo | Files/Modules Reviewed | License | Reusable Concept | Direct Dependency? | Copy Allowed? | Proposed Target Module | Test Strategy |
|---|---|---|---|---|---|---|---|---|

그리고 다음을 명시한다.

- 무엇을 참고하는가
- 왜 해당 reference가 적합한가
- 어떤 부분은 참고하지 않는가
- dependency 추가 여부
- 라이선스 영향
- 우리 architecture와 다른 점
- clean-room 독립 구현이 필요한 부분

## 2단계 — 라이선스 Gate

- PM4Py, GPL, AGPL source: 제품 소스에 복사 금지. line-by-line 번역/변형 금지.
- LGPL: 링크/배포 방식 검토 없이 복사·내장 금지.
- MIT/BSD/Apache: 라이선스/NOTICE 조건을 확인한 뒤 dependency 사용을 우선 검토.
- 라이선스가 불명확하면 적용하지 말고 질문/리스크로 남긴다.

## 3단계 — 구현

계획이 끝나면 현재 요청한 **단 하나의 feature**만 구현한다.

프로젝트 규칙:

- 대규모 분석은 DuckDB SQL-first.
- 전체 event log를 Pandas DataFrame 하나에 적재하지 않는다.
- 실제 운영 로그를 읽거나 외부로 보내지 않는다.
- synthetic fixture로 먼저 검증한다.
- UI는 계산을 수행하지 않고 API 결과를 표현한다.
- Process Map은 Cytoscape.js를 우선한다.

## 4단계 — 완료 보고

다음을 보고한다.

1. 변경 파일
2. 적용한 외부 reference와 해당 license
3. dependency 추가 여부
4. 외부 코드를 직접 복사했는지 여부 — 기본 답은 No여야 한다
5. 구현한 기능
6. 테스트 결과
7. 성능 영향
8. 보안 영향
9. 미해결 리스크
