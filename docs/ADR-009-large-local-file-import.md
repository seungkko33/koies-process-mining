# ADR-009: Local Path Import는 COPY 기본, opt-in REFERENCE를 제공한다

- 상태: Accepted
- 날짜: 2026-09-01

## Context

같은 PC의 수 GB file을 browser multipart로 보내고 staging에 다시 쓰면 불필요한 이동과 disk peak가 생긴다.
반면 arbitrary filesystem API와 mutable external reference는 보안/재현성 위험이다.

## Decision

`POST /api/datasets/import-local`은 configured `allowed_roots` 아래의 absolute canonical file만 받는다.
directory listing은 제공하지 않는다. relative/traversal/symlink escape/device/비허용 UNC/directory/extension을
차단한다. COPY가 기본이며 browser upload와 같은 UUID staging을 만든다. REFERENCE는 opt-in이고 checksum,
size, mtime manifest를 저장해 mapping/normalization/analysis 전에 drift를 검증한다.

## Consequences

COPY는 disk를 더 사용하지만 source immutability와 재현성이 높다. REFERENCE는 low-copy지만 원본 변경/삭제 시
`SOURCE_CHANGED`가 되어 READY artifact를 자동 재사용하지 않는다. watcher나 자동 re-import는 구현하지 않는다.
