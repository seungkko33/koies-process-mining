# OPEN_SOURCE_REFERENCE_GUIDE.md — 프로세스 마이닝 OSS 조사 및 AI 코딩 적용 가이드

> 기준일: 2026-08-31
> 목적: 공제정보망 로컬 프로세스 마이닝 플랫폼을 개발할 때 공개 소스코드를 안전하게 조사하고, AI 코딩 도구(Codex/Claude Code 등)가 참고하되 라이선스·아키텍처 오염 없이 필요한 부분만 적용하도록 하는 기준 문서.

## 1. 결론 요약

이 프로젝트에서 공개 소스는 하나를 통째로 포크하여 출발하는 것보다, 역할별로 다른 프로젝트를 참고하는 것이 적합하다.

| 우선순위 | 프로젝트 | 주 용도 | 2026-08 기준 공개 지표 | 라이선스 판단 | 적용 방식 |
|---|---|---|---|---|---|
| A | PM4Py | 프로세스 마이닝 알고리즘/개념/API 기준 | GitHub 약 969 stars, 351 forks, PyPI 월 12만+ 수준 | AGPL-3.0 | **참고/검증 전용**, 제품 코드 직접 복사 금지. 상용 라이선스 검토 후 Adapter 가능 |
| A | Cytoscape.js | DFG/Process Map 웹 시각화 | GitHub 약 11.2k stars, 1.7k forks | MIT | 직접 의존성 사용 권장 |
| A | NHS England ProcessMining | 실제 분석 프로젝트 구조/노트북/데이터 흐름 | 공공기관 공개 사례 | 저장소 자체 MIT | 구조·테스트·분석 흐름 참고. PM4Py 의존성은 별도 라이선스 검토 |
| B | bpmn-js / examples | BPMN 2.0 렌더링/모델링 | bpmn-js 약 9.5k stars, examples 약 2k stars | bpmn.io license / examples MIT | BPMN 기능이 필요해질 때 선택 도입. 워터마크 조건 확인 |
| B | ApromoreCore | 대형 프로세스 마이닝 제품 아키텍처 | 약 143 stars, 79 forks | LGPL-3.0, 저장소 deprecated | 코드 채택보다 제품 구조/기능 분해 참고용 |
| C | ProM Framework | 학술 알고리즘/플러그인 생태계 | GitHub 지표는 낮지만 학술 표준급 역사 | 개별 패키지/배포 라이선스 확인 필요 | 알고리즘 검증·개념 참고용 |
| C | Cortado | Variant Explorer, interactive/incremental discovery UI 아이디어 | 공개 데스크톱 앱 | GPL-3.0 | UX/기능 아이디어 참고. 직접 코드 혼입 금지 |
| C | Heraclitus | DuckDB 기반 대용량 PM 아이디어 | 신생, GitHub 0 stars | MIT | 실험/아이디어 참고. 성숙도 검증 필요 |

### 핵심 선택

1. **분석 엔진**: DuckDB SQL 자체 구현을 기본으로 유지한다.
2. **알고리즘 정답 비교**: PM4Py를 별도 실험환경 또는 라이선스 승인된 Adapter에서 비교 기준으로 사용한다.
3. **프로세스 맵 UI**: Cytoscape.js를 제품 의존성으로 채택하는 것이 가장 합리적이다.
4. **업무형 구현 패턴**: NHS England ProcessMining의 분석 흐름과 synthetic/fake data 접근을 참고한다.
5. **BPMN**: MVP 필수 기능이 아니다. Phase 3 이후 bpmn-js를 검토한다.

---

## 2. 왜 PM4Py가 1순위 참고 자료인가

PM4Py는 현재 공개 Python 프로세스 마이닝 생태계에서 가장 널리 사용되는 프로젝트 중 하나다. Process Discovery, DFG, Alpha/Inductive Miner, Petri Net, Conformance Checking, Declare, XES 처리, 다양한 시각화까지 폭넓게 구현되어 있다.

특히 우리 프로젝트에서 유용한 참고 영역은 다음과 같다.

- Event Log 표준 컬럼 개념
- DFG 정의 및 결과 구조
- Start/End activity 계산
- Variant 계산
- Inductive Miner 계열의 입출력 모델
- Conformance Checking 개념 및 지표
- Petri Net/Process Tree 표현 방식
- Synthetic log를 활용한 알고리즘 테스트 방식

그러나 **오픈소스 PM4Py는 AGPL-3.0**이다. 폐쇄형 사내 제품에 코드를 복사하거나 핵심 런타임 의존성으로 넣는 것은 조직의 법무/라이선스 검토 없이 진행하지 않는다. PM4Py 제공사는 폐쇄형/상용 용도의 별도 라이선스 옵션을 제공한다.

### 프로젝트 정책

- `_references/pm4py`가 존재하더라도 **읽기 전용 참고 디렉터리**다.
- Codex/Claude는 PM4Py 파일을 target source directory로 복사하지 않는다.
- PM4Py 구현을 line-by-line 번역하거나 이름만 바꾸어 재작성하지 않는다.
- 알고리즘은 공개된 수학적 정의/논문/프로젝트의 공개 API 동작을 기준으로 독립 구현한다.
- 필요하면 synthetic fixture에 대해 `우리 SQL 결과 == PM4Py 결과` 형태의 검증만 수행한다.
- 실제 제품에서 PM4Py를 import하는 코드는 `adapters/pm4py/` 아래로 격리하고 feature flag로 꺼질 수 있어야 한다.

---

## 3. Cytoscape.js — 직접 적용 권장

Cytoscape.js는 네트워크/그래프 분석 및 브라우저 시각화 라이브러리로, DFG 기반 Process Map에 매우 잘 맞는다.

적용 대상:

- activity node
- directly-follows edge
- frequency/throughput 기반 edge width
- node frequency/average duration 표시
- zoom/pan
- node/edge selection
- graph layout
- threshold/Top-N에 따른 동적 graph 축소
- 선택한 node/edge와 KPI/Case Explorer 연계

MIT 라이선스이므로 라이선스 고지 의무를 지키는 전제에서 제품 의존성으로 사용하는 것이 PM4Py보다 훨씬 단순하다.

### 권장 구현 경계

```text
DuckDB SQL
  -> DFG DTO
FastAPI
  -> /api/process-map
React Query
  -> ProcessMapPage
Cytoscape.js
  -> ProcessGraph component
```

UI 컴포넌트가 SQL 또는 process-mining 계산을 수행하지 않도록 한다.

---

## 4. NHS England ProcessMining — 실제 업무형 프로젝트 참고

NHS England의 공개 ProcessMining 저장소는 fake/synthetic data를 사용한 실제 분석 프로젝트 구조를 보여 준다. 우리 프로젝트에 특히 유용한 부분은 다음과 같다.

- 실제 민감 데이터를 공개 저장소에 넣지 않는 방식
- 데이터 생성/준비 → 분석 → 출력의 단계 분리
- Notebook/스크립트 기반 탐색 분석의 구성
- 프로세스 마이닝 라이브러리를 업무 분석에 연결하는 예시

저장소 자체의 코드는 MIT이지만 PM4Py 등 외부 dependency의 라이선스는 별도로 판단해야 한다.

우리 프로젝트에서는 이 프로젝트를 제품 소스의 베이스로 포크하지 않고 **분석 워크플로우와 테스트 데이터 운영 방식**을 참고한다.

---

## 5. bpmn-js — Phase 3 이후 선택 적용

bpmn-js는 BPMN 2.0 XML을 웹에서 렌더링하고 편집하는 성숙한 toolkit이다. 프로세스 마이닝 결과를 정형 BPMN으로 내보내거나, 발견된 프로세스와 표준 업무 프로세스를 비교하는 기능을 만들 때 유용하다.

다만 MVP의 Process Map은 BPMN editor가 아니라 **실제 로그에서 발견된 DFG를 탐색하는 화면**이므로 Cytoscape.js가 더 적합하다.

주의:

- bpmn-js 저장소의 라이선스에는 표시되는 bpmn.io watermark를 제거하거나 가리지 말라는 조건이 있다.
- examples 저장소는 별도로 MIT로 제공되는 예제가 많다.
- 실제 도입 시 `LICENSE_POLICY.md`의 dependency review 절차를 따른다.

---

## 6. Apromore / ProM / Cortado의 위치

### ApromoreCore

오픈소스 코어는 대규모 Java 기반 제품의 Portal, Process Discovery 등 구조를 볼 수 있다는 장점이 있다. 그러나 저장소 자체가 deprecated로 표시되어 있으므로 신규 제품의 직접 베이스로는 권장하지 않는다.

참고할 것:

- 기능을 plugin/service 단위로 분리하는 방식
- event log repository와 분석 기능의 분리
- 대형 process-mining 제품의 화면/기능 구성

### ProM

프로세스 마이닝 연구 생태계에서 중요한 프레임워크다. GitHub star 수만으로 가치를 평가하면 안 된다. 다만 현대적인 React/FastAPI/DuckDB 제품 구현의 베이스로 사용하기보다는 알고리즘 개념 및 결과 검증 자료로 보는 것이 적합하다.

### Cortado

Variant Explorer와 interactive/incremental process discovery UX를 참고하기 좋다. GPL-3.0이므로 폐쇄형 제품에 코드를 직접 혼합하지 않는다.

---

## 7. GitHub 공개 코드 '불러오기 → 분석 → 적용' 표준 방식

### 원칙

공개 저장소를 현재 제품 Git history 안에 무작정 merge하지 않는다. 대신 아래 구조를 사용한다.

```text
koies-process-mining/
├─ app/ or src/                 # 실제 제품 코드
├─ docs/
├─ templates/
├─ scripts/
└─ _references/                # gitignore. 외부 공개 저장소 로컬 clone
   ├─ cytoscape.js/
   ├─ nhs-processmining/
   ├─ bpmn-js-examples/
   └─ pm4py/                   # AGPL: read-only reference
```

`_references/` 전체는 우리 GitHub 저장소에 커밋하지 않는다.

### Step 1 — 불러오기

Windows에서는 프로젝트 루트에서 다음을 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\fetch_references.ps1
```

Bash 환경에서는:

```bash
bash ./scripts/fetch_references.sh
```

스크립트는 공개 저장소를 `_references/` 아래에 shallow clone한다.

### Step 2 — AI에게 분석시키기

Codex/Claude에 `templates/REFERENCE_ADOPTION_PROMPT.md`를 사용한다.

AI의 첫 작업은 코드를 쓰는 것이 아니라 다음 표를 만드는 것이다.

| Target Feature | Reference | 참고 파일 | 가져올 개념 | 라이선스 위험 | 제품 구현 위치 | 구현 방식 |
|---|---|---|---|---|---|---|
| DFG | PM4Py | discovery/dfg | 입출력/검증 개념 | High/AGPL | backend/analytics/dfg.py | clean-room SQL |
| Process Map | Cytoscape.js | demos/docs | graph render pattern | Low/MIT | frontend/... | npm dependency |

이 산출물을 `docs/REFERENCE_ADOPTION_PLAN.md`로 저장한다.

### Step 3 — 적용 승인 규칙

- MIT/BSD/Apache 등 permissive dependency: 라이선스 고지 및 dependency review 후 직접 의존성 사용 가능.
- LGPL: linking/배포 조건을 검토한 뒤 결정.
- GPL/AGPL: 별도 승인 전 **소스 복사/내장 금지**.
- 라이선스 불명: 적용 금지.

### Step 4 — 작은 단위로 적용

한 번에 외부 프로젝트 전체를 '우리 코드로 변환'하라고 지시하지 않는다.

좋은 작업 단위:

1. Cytoscape.js reference를 분석한다.
2. 우리 `ProcessGraph` 인터페이스를 먼저 설계한다.
3. synthetic DFG 10 nodes로 렌더링한다.
4. API DTO를 연결한다.
5. threshold/selection 기능을 추가한다.
6. 테스트를 작성한다.

나쁜 작업 단위:

> PM4Py와 Apromore를 참고해서 프로세스 마이닝 프로그램 전체를 만들어.

이런 요청은 출처 추적이 어려워지고 라이선스 위험과 구조적 복제가 발생할 수 있다.

---

## 8. 가장 추천하는 실전 개발 순서

### Sprint A — permissive OSS만으로 Vertical Slice

1. DuckDB SQL DFG 구현
2. FastAPI `GET /api/process-map`
3. Cytoscape.js Process Map
4. synthetic event log
5. golden test

이 단계에서는 PM4Py를 제품 dependency로 사용하지 않는다.

### Sprint B — Reference Validation

1. 별도 development/reference environment에 PM4Py 설치 또는 clone
2. 동일 synthetic log로 DFG/Variant 결과 생성
3. 우리 DuckDB SQL 결과와 비교
4. 차이를 문서화
5. 제품 런타임에서는 PM4Py 없이 동일 결과 유지

### Sprint C — 업무형 탐색 UX

NHS example, Cortado, Apromore의 UI/분석 흐름을 참고하여:

- filter
- variant explorer
- bottleneck
- case explorer
- rework
- comparison

순서로 구현한다.

### Sprint D — BPMN/Conformance

라이선스 및 필요성을 검토한 뒤:

- bpmn-js viewer/modeler
- 표준 업무 BPMN import
- discovered process와 기준 모델 비교
- PM4Py commercial license 또는 독립 알고리즘 구현 여부 결정

---

## 9. Codex에 바로 붙여넣을 핵심 명령

아래 프롬프트는 `templates/REFERENCE_ADOPTION_PROMPT.md`에도 저장한다.

```text
먼저 AGENTS.md, PRD.md, ARCHITECTURE.md, LICENSE_POLICY.md,
OPEN_SOURCE_REFERENCE_GUIDE.md를 읽어라.

그 다음 _references/ 아래 공개 저장소를 읽되 어떤 코드도 바로 복사하지 마라.
현재 작업의 목적과 관련 있는 파일만 조사하고
1) 참고 가능한 아키텍처/알고리즘/UX 패턴,
2) 라이선스,
3) 우리 프로젝트에 적용 가능한 부분,
4) 직접 복사하면 안 되는 부분,
5) 구현 계획 및 테스트 계획
을 docs/REFERENCE_ADOPTION_PLAN.md에 먼저 작성하라.

PM4Py/GPL/AGPL 계열 코드는 제품 소스에 복사하거나 line-by-line으로 재작성하지 마라.
Cytoscape.js 등 permissive dependency는 직접 의존성 방식과 자체 구현 방식 중 더 단순한 것을 제안하라.

계획 작성 후 현재 요청한 단 하나의 feature만 구현하라.
대규모 계산은 DuckDB SQL-first 원칙을 유지하고 전체 데이터를 Pandas로 적재하지 마라.
작업 완료 후 사용한 외부 reference와 적용 방식을 보고하라.
```

---

## 10. Reference 업데이트 정책

외부 저장소는 지속적으로 변경되므로 무조건 최신 코드를 자동 반영하지 않는다.

권장 방식:

1. `_references/`는 필요할 때 수동 갱신.
2. 실제 제품 dependency는 package lockfile로 버전 고정.
3. 외부 코드를 참고하여 중요한 설계 결정을 내렸다면 `docs/ADR-*`에 당시 commit SHA를 기록.
4. 라이선스 파일/NOTICE를 dependency upgrade 때 재검토.
5. Codex가 외부 reference를 적용한 PR에는 `External References` 항목을 남긴다.

---

## 11. 프로젝트별 공개 주소

- PM4Py: https://github.com/process-intelligence-solutions/pm4py
- Cytoscape.js: https://github.com/cytoscape/cytoscape.js
- NHS England ProcessMining: https://github.com/nhsengland/ProcessMining
- bpmn-js: https://github.com/bpmn-io/bpmn-js
- bpmn-js examples: https://github.com/bpmn-io/bpmn-js-examples
- ApromoreCore: https://github.com/apromore/ApromoreCore
- ProM Framework: https://github.com/promworkbench/ProM-Framework
- Cortado: https://github.com/cortado-tool/cortado

## 12. 최종 권고

공제정보망 프로젝트에서는 **'유명 프로세스 마이닝 OSS를 통째로 가져오기'보다 'DuckDB 자체 분석 엔진 + Cytoscape.js UI + 공개 구현을 검증 기준으로 활용'하는 방식**이 가장 안전하다.

특히 PM4Py는 다운로드/커뮤니티/알고리즘 범위 면에서 가장 중요한 reference지만, AGPL 때문에 **제품 코드의 출발점이 아니라 알고리즘 사전과 검증 오라클(reference oracle)** 로 취급하는 것이 적절하다.
