# ADR-008: artifact는 자동 삭제하지 않고 명시적으로 관리한다

- 상태: Accepted
- 날짜: 2026-09-01

## Context

contract version마다 normalized/quarantine Parquet이 생기므로 disk usage가 누적된다. 자동 retention은 분석
재현성을 훼손하고 사용자 의도 없이 데이터를 삭제할 수 있다.

## Decision

SOURCE/NORMALIZED/QUARANTINE artifact metadata에 contract/mapping version, relative path, size, created,
active, pinned을 기록한다. 새 artifact는 같은 type의 이전 것을 inactive로 만든다. source는 Dataset 삭제에서만,
active/pinned은 개별 cleanup으로 삭제하지 못한다. 사용자가 inactive/unpinned artifact를 명시적으로 삭제한다.

Parquet은 final과 같은 volume에 temporary file을 쓰고 성공 시 atomic replace한다. normalized canonical file을
마지막에 교체하며 실패 시 temporary만 제거하고 기존 active final을 유지한다.

## Consequences

disk 회수는 자동이 아니며 UI가 managed usage와 보호 사유를 보여준다. process termination 뒤 남은 untracked
temporary 탐지/복구는 후속 startup reconciliation 대상이다.
