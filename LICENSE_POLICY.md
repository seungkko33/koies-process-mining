# 오픈소스 라이선스 정책

## 1. 목적
사내 업무용 프로그램이라 하더라도 배포 방식, 네트워크 제공 방식, 소스 결합 구조에 따라 라이선스 의무가 달라질 수 있으므로 의존성 도입 전에 검토한다.

## 2. PM4Py
현재 공식 GitHub의 오픈소스 버전은 AGPL-3.0으로 안내되고 있으며 폐쇄형 상업 사용을 위한 별도 라이선스도 제공된다.

따라서 본 프로젝트는:
1. MVP에서 PM4Py를 필수 dependency로 사용하지 않는다.
2. DuckDB SQL로 기본 분석을 독립 구현한다.
3. PM4Py는 optional adapter로 격리한다.
4. 도입 전 조직 법무/라이선스 담당 검토를 수행한다.
5. 필요 시 상용 라이선스를 검토한다.

이 문서는 법률 자문이 아니다.

## 3. 의존성 정책
신규 패키지 추가 시 기록:
- package
- version
- license
- purpose
- direct/transitive
- distribution impact
- approved/rejected

## 4. 선호
가능하면 permissive license(MIT/BSD/Apache-2.0)를 우선 검토하되 기능·보안·유지보수성을 함께 고려한다.
