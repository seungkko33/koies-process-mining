# ADR-002: Browser Upload와 Local Path Import

## Status
Accepted for the ingestion MVP.

## Context
주 사용 흐름은 사용자가 공제정보망에서 내려받은 CSV/Parquet 파일을 localhost 애플리케이션에
등록하는 방식이다. 브라우저 multipart upload는 이해하기 쉽고 브라우저 보안 경계를 따르지만,
수 GB 파일에서는 같은 PC 안에서 staging 복사가 한 번 발생한다. 임의 로컬 경로 입력은 복사를
줄일 수 있으나 서버 프로세스가 접근할 수 있는 파일 시스템을 과도하게 노출할 위험이 있다.

## Decision
- MVP의 유일한 사용자 입력 경로는 `POST /api/datasets/upload` 기반 Browser Upload다.
- 업로드는 `UploadFile`을 1 MiB chunk로 읽어 UUID staging 디렉터리에 기록한다.
- 원래 파일명은 표시용 metadata로만 보존하고 저장 경로에는 사용하지 않는다.
- Local Path Import는 구현하지 않고, 향후 별도 adapter로만 추가한다.
- 향후 adapter도 사용자가 서버의 임의 경로를 탐색하는 API가 되어서는 안 된다. 명시적으로
  허용된 root, canonical path 검증, read-only access와 사용자 확인이 필요하다.

## Consequences
Browser Upload는 단순하고 이식 가능하며 현재 UI와 일관된다. 대신 source와 staging이 동시에
존재하므로 추가 디스크와 복사 시간이 든다. UI progress는 네트워크 전송이 아니라 localhost로
복사된 byte 진행률을 의미한다.

## Revisit Trigger
- 수 GB 파일의 staging 복사가 전체 적재 시간 또는 디스크 사용량의 주된 병목이 될 때
- 패키지형 데스크톱 배포로 신뢰 가능한 native file picker를 제공할 수 있을 때

