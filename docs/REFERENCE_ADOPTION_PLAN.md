# Reference Adoption Plan — Cytoscape.js Process Map

> 작성일: 2026-08-31  
> 대상 기능: Synthetic Event Log → DuckDB DFG → FastAPI → React Process Map  
> 조사 기준 commit: `cytoscape/cytoscape.js@fd3595bbf0eaac76ef2a6984a29e85703c239703`

## 1. 채택 요약

| Target Feature | Reference Repo | Files/Modules Reviewed | License | Reusable Concept | Direct Dependency? | Copy Allowed? | Proposed Target Module | Test Strategy |
|---|---|---|---|---|---|---|---|---|
| Process graph rendering | `cytoscape/cytoscape.js` | `README.md`, `package.json`, `LICENSE`, `documentation/demos/initialisation/code.js` | MIT | container 초기화, node/edge element data, stylesheet, layout | Yes — `cytoscape@3.34.2` | Dependency 사용만 허용; source copy 없음 | `frontend/src/features/process-map/ProcessGraph.tsx` | 변환 함수 unit test + 실제 API 연동 + rendered interaction |
| Node/edge selection | `cytoscape/cytoscape.js` | initialisation demo, `documentation/md/events.md` | MIT | delegated `tap` event와 selected state | Yes | source copy 없음 | `ProcessGraph.tsx`, `ProcessDetails.tsx` | node/edge 선택 시 detail state 검증 |
| View controls | `cytoscape/cytoscape.js` | `documentation/md/core/fit.md`, `core/reset.md`, `core/userPanningEnabled.md`, `core/userZoomingEnabled.md` | MIT | `fit()`, `reset()`, 기본 pan/zoom | Yes | source copy 없음 | `ProcessMapPage.tsx` | fit/reset control smoke test |
| Graph complexity control | `cytoscape/cytoscape.js` | `documentation/md/performance.md` | MIT | edge 수 제한, 단순 style, label/animation 비용 주의 | Yes | source copy 없음 | backend DFG limits + `processMapModel.ts` threshold | golden limit test + threshold transform unit test |

## 2. 선택 이유

- 현재 Architecture와 UI/UX spec이 DFG renderer로 Cytoscape.js를 우선 지정한다.
- API의 집계 DTO를 Cytoscape element data로 얇게 변환할 수 있어 분석 계산과 렌더링 책임을 분리할 수 있다.
- 기본 pan/zoom, selection, fit/reset API가 있어 별도 graph interaction engine을 만들 필요가 없다.
- MIT 라이선스이므로 제품 runtime dependency로 사용할 수 있으며, lockfile로 버전을 고정할 수 있다.

## 3. 우리 Architecture 적용 방식

```text
curated.event_log
  → backend/app/analytics/dfg.py (DuckDB SQL)
  → GET /api/dfg (bounded DFG DTO)
  → frontend/src/api/dfg.ts
  → processMapModel.ts (DTO → renderer element adapter)
  → ProcessGraph.tsx (Cytoscape lifecycle/interaction only)
  → ProcessMapPage.tsx (filter and selected detail state)
```

- 비즈니스 지표 계산과 정렬은 backend에서만 수행한다.
- API는 설정의 `max_process_nodes`와 `max_process_edges`를 상한으로 적용한다.
- frontend의 minimum transition frequency는 이미 받은 bounded aggregate를 표현 단계에서 줄이는 control이며, 원천 event를 재계산하지 않는다.
- Cytoscape instance는 React component mount 시 생성하고 unmount 시 `destroy()`한다.
- node와 edge의 data key는 안정적인 자체 ID를 사용하며 화면 label과 분리한다.

## 4. 라이선스와 source copy

- Cytoscape.js: MIT, npm direct dependency.
- 배포물에는 npm dependency가 포함되며 MIT copyright/permission notice 유지가 필요하다.
- 외부 저장소의 JavaScript source, demo source, CSS를 제품 코드로 복사하지 않는다.
- API 사용법과 element/style/event 개념만 참고해 현재 프로젝트 구조에 맞게 독립 작성한다.

## 5. 적용하지 않는 Reference

| Reference | 결정 | 이유 |
|---|---|---|
| PM4Py | 미적용 | AGPL-3.0이며 이번 단계는 SQL DFG와 renderer 연결이다. 향후 별도 reference oracle 후보로만 유지한다. |
| NHS England ProcessMining | 미조사/미적용 | 이번 기능에 필요한 합성 fixture와 SQL 계약이 이미 존재해 추가 workflow reference가 필요하지 않다. |
| bpmn-js | 미적용 | 현재 화면은 발견된 DFG 탐색기이며 BPMN viewer/editor가 아니다. Phase 3 이후 검토한다. |
| Cytoscape layout extension(dagre 등) | 미적용 | 초기 vertical slice는 core `breadthfirst` layout으로 충분하며 dependency 폭을 최소화한다. |

## 6. 검증 계획

- Backend: golden node/edge/total metadata, empty log, deterministic order, configured result limit, `/api/dfg` envelope.
- Frontend: DTO validation, threshold/topology conversion, empty/error model, stable IDs.
- Integration: 합성 golden fixture를 DuckDB에 적재하고 FastAPI `/api/dfg`를 실제 React dev server가 조회하는 흐름 검증.
- Performance: 100K/1M/5M/20M 선택형 benchmark harness만 제공하고 이번 작업에서 20M을 자동 실행하지 않는다.

