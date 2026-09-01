from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.config import Settings
from app.datasets.errors import DatasetError
from app.schemas.datasets import DatasetFileType


class DatasetStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._staging_root = settings.data.staging_dir.resolve()
        self._curated_root = settings.data.curated_dir.resolve()
        self._quarantine_root = settings.data.quarantine_dir.resolve()
        self._temp_root = settings.data.temp_dir.resolve()

    @staticmethod
    def validate_filename(filename: str | None) -> tuple[str, DatasetFileType, str]:
        if not filename or filename in {".", ".."}:
            raise DatasetError("INVALID_FILENAME", "A file name is required", 400)
        normalized = filename.replace("\\", "/")
        if "/" in normalized:
            raise DatasetError(
                "INVALID_FILENAME",
                "File names must not contain directory components",
                400,
            )
        lower_name = normalized.lower()
        if lower_name.endswith(".csv.gz"):
            return normalized, DatasetFileType.CSV_GZ, "source.csv.gz"
        if lower_name.endswith(".csv"):
            return normalized, DatasetFileType.CSV, "source.csv"
        if lower_name.endswith(".parquet"):
            return normalized, DatasetFileType.PARQUET, "source.parquet"
        raise DatasetError(
            "UNSUPPORTED_FILE_TYPE",
            "Supported file types are CSV, CSV.GZ, and Parquet",
            415,
        )

    async def write_upload(
        self,
        upload: UploadFile,
        dataset_id: str,
        staged_filename: str,
        file_type: DatasetFileType,
    ) -> tuple[int, str, Path]:
        self._validate_dataset_id(dataset_id)
        expected_size = upload.size
        if expected_size is not None:
            self._require_free_space(expected_size)

        directory = self._dataset_directory(self._staging_root, dataset_id)
        directory.mkdir(parents=True, exist_ok=False)
        target = self._resolve_under(directory, staged_filename)
        checksum = hashlib.sha256()
        size = 0
        try:
            with target.open("xb") as output:
                while chunk := await upload.read(
                    self._settings.quality.upload_chunk_size_bytes
                ):
                    output.write(chunk)
                    checksum.update(chunk)
                    size += len(chunk)
            if size == 0:
                raise DatasetError("EMPTY_FILE", "The uploaded file is empty")
            self._validate_signature(target, file_type)
            return size, checksum.hexdigest(), target
        except Exception:
            if directory.exists():
                shutil.rmtree(directory)
            raise
        finally:
            await upload.close()

    def stage_local_file(
        self,
        source: Path,
        dataset_id: str,
        staged_filename: str,
        file_type: DatasetFileType,
    ) -> tuple[int, str, Path]:
        """Chunk-copy a generated benchmark source through the same staging boundary."""
        self._validate_dataset_id(dataset_id)
        self._require_free_space(source.stat().st_size)
        directory = self._dataset_directory(self._staging_root, dataset_id)
        directory.mkdir(parents=True, exist_ok=False)
        target = self._resolve_under(directory, staged_filename)
        checksum = hashlib.sha256()
        size = 0
        try:
            with source.open("rb") as input_file, target.open("xb") as output_file:
                while chunk := input_file.read(
                    self._settings.quality.upload_chunk_size_bytes
                ):
                    output_file.write(chunk)
                    checksum.update(chunk)
                    size += len(chunk)
            self._validate_signature(target, file_type)
            return size, checksum.hexdigest(), target
        except Exception:
            if directory.exists():
                shutil.rmtree(directory)
            raise

    def resolve_local_import(self, raw_path: str) -> tuple[Path, DatasetFileType, str]:
        if not raw_path.strip():
            raise DatasetError("INVALID_LOCAL_PATH", "A local file path is required", 400)
        normalized = raw_path.replace("/", "\\") if os.name == "nt" else raw_path
        if any(part == ".." for part in Path(normalized).parts):
            raise DatasetError("PATH_TRAVERSAL", "Local path traversal is not allowed", 403)
        if normalized.startswith(("\\\\?\\", "\\\\.\\")):
            raise DatasetError("DEVICE_PATH_BLOCKED", "Windows device paths are not allowed", 403)
        if normalized.startswith("\\\\") and not self._settings.dataset_import.allow_unc_paths:
            raise DatasetError("UNC_PATH_BLOCKED", "UNC paths are not enabled", 403)
        candidate = Path(normalized)
        if not candidate.is_absolute():
            raise DatasetError("RELATIVE_PATH_BLOCKED", "Local import paths must be absolute", 403)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as error:
            raise DatasetError(
                "LOCAL_SOURCE_MISSING",
                "The local source file is unavailable",
                404,
            ) from error
        allowed_roots = [root.resolve() for root in self._settings.dataset_import.allowed_roots]
        if not allowed_roots:
            raise DatasetError(
                "LOCAL_IMPORT_DISABLED",
                "Configure at least one allowed local import root",
                403,
            )
        if not any(root == resolved.parent or root in resolved.parents for root in allowed_roots):
            raise DatasetError(
                "PATH_OUTSIDE_ALLOWED_ROOT",
                "Local path is outside allowed roots",
                403,
            )
        if not resolved.is_file():
            raise DatasetError("LOCAL_SOURCE_NOT_FILE", "Local import requires a file", 400)
        _safe_name, file_type, staged_filename = self.validate_filename(resolved.name)
        self._validate_signature(resolved, file_type)
        return resolved, file_type, staged_filename

    def inspect_local_source(self, source: Path) -> tuple[int, int, str]:
        stat = source.stat()
        if stat.st_size == 0:
            raise DatasetError("EMPTY_FILE", "The local source file is empty")
        return stat.st_size, stat.st_mtime_ns, self.hash_file(source)

    @staticmethod
    def hash_file(path: Path, chunk_size: int = 1_048_576) -> str:
        checksum = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(chunk_size):
                checksum.update(chunk)
        return checksum.hexdigest()

    def staged_path(self, dataset_id: str, staged_filename: str) -> Path:
        directory = self._dataset_directory(self._staging_root, dataset_id)
        return self._resolve_under(directory, staged_filename)

    def normalized_path(self, relative_filename: str) -> Path:
        return self._resolve_under(self._curated_root, relative_filename)

    def quarantine_path(self, relative_filename: str) -> Path:
        return self._resolve_under(self._quarantine_root, relative_filename)

    def staging_relative_path(self, dataset_id: str, staged_filename: str) -> str:
        return self.staged_path(dataset_id, staged_filename).relative_to(
            self._staging_root
        ).as_posix()

    def artifact_path(self, storage_area: str, relative_path: str) -> Path:
        roots = {
            "STAGING": self._staging_root,
            "CURATED": self._curated_root,
            "QUARANTINE": self._quarantine_root,
            "TEMP": self._temp_root,
        }
        root = roots.get(storage_area)
        if root is None:
            raise DatasetError("INVALID_ARTIFACT", "Artifact storage area is invalid", 409)
        return self._resolve_under(root, relative_path)

    def normalization_paths(self, dataset_id: str, version: int) -> tuple[Path, Path, Path]:
        normalized_directory = self._dataset_directory(self._curated_root, dataset_id)
        quarantine_directory = self._dataset_directory(self._quarantine_root, dataset_id)
        temp_directory = self._dataset_directory(self._temp_root, dataset_id)
        normalized_directory.mkdir(parents=True, exist_ok=True)
        quarantine_directory.mkdir(parents=True, exist_ok=True)
        temp_directory.mkdir(parents=True, exist_ok=True)
        return (
            self._resolve_under(normalized_directory, f"events-v{version}.parquet"),
            self._resolve_under(quarantine_directory, f"quarantine-v{version}.parquet"),
            self._resolve_under(temp_directory, f"validation-v{version}.parquet"),
        )

    def atomic_temp_path(self, final_path: Path) -> Path:
        return self._resolve_under(
            final_path.parent,
            f".tmp-{uuid4().hex[:8]}.parquet",
        )

    @staticmethod
    def finalize_atomic(temp_path: Path, final_path: Path) -> None:
        temp_path.replace(final_path)

    def relative_curated_path(self, path: Path) -> str:
        return path.resolve().relative_to(self._curated_root).as_posix()

    def relative_quarantine_path(self, path: Path) -> str:
        return path.resolve().relative_to(self._quarantine_root).as_posix()

    def remove_file(self, path: Path) -> None:
        resolved = path.resolve()
        allowed_roots = {
            self._curated_root,
            self._quarantine_root,
            self._temp_root,
        }
        if not any(root == resolved.parent or root in resolved.parents for root in allowed_roots):
            raise DatasetError(
                "SECURITY_BLOCKED",
                "Refusing to remove a file outside data roots",
                403,
            )
        if resolved.is_file():
            resolved.unlink()

    def cleanup_dataset(self, dataset_id: str) -> None:
        self._validate_dataset_id(dataset_id)
        for root in (
            self._staging_root,
            self._curated_root,
            self._quarantine_root,
            self._temp_root,
        ):
            target = self._dataset_directory(root, dataset_id)
            if target.exists():
                shutil.rmtree(target)

    def available_bytes(self) -> int:
        self._staging_root.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(self._staging_root).free

    def _require_free_space(self, expected_size: int) -> None:
        required = int(
            expected_size * self._settings.quality.minimum_free_space_multiplier
        )
        if self.available_bytes() < required:
            raise DatasetError(
                "INSUFFICIENT_DISK_SPACE",
                "Not enough local disk space for staging, normalization, and DuckDB spill",
                507,
            )

    @staticmethod
    def _validate_signature(path: Path, file_type: DatasetFileType) -> None:
        size = path.stat().st_size
        with path.open("rb") as source:
            prefix = source.read(4)
            if file_type == DatasetFileType.PARQUET:
                if size < 8:
                    raise DatasetError("INVALID_PARQUET", "Invalid Parquet file")
                source.seek(-4, 2)
                suffix = source.read(4)
                if prefix != b"PAR1" or suffix != b"PAR1":
                    raise DatasetError("INVALID_PARQUET", "Invalid Parquet file")
            elif file_type == DatasetFileType.CSV_GZ:
                if prefix[:2] != b"\x1f\x8b":
                    raise DatasetError("INVALID_CSV_GZ", "Invalid gzip-compressed CSV file")
            elif b"\x00" in prefix:
                raise DatasetError("INVALID_CSV", "CSV files must be text data")

    @staticmethod
    def _validate_dataset_id(dataset_id: str) -> None:
        try:
            parsed = UUID(dataset_id)
        except ValueError as error:
            raise DatasetError("INVALID_DATASET_ID", "Invalid dataset identifier", 400) from error
        if str(parsed) != dataset_id:
            raise DatasetError("INVALID_DATASET_ID", "Invalid dataset identifier", 400)

    @classmethod
    def _dataset_directory(cls, root: Path, dataset_id: str) -> Path:
        cls._validate_dataset_id(dataset_id)
        return cls._resolve_under(root, dataset_id)

    @staticmethod
    def _resolve_under(root: Path, relative: str) -> Path:
        resolved_root = root.resolve()
        candidate = (resolved_root / relative).resolve()
        if candidate == resolved_root or resolved_root not in candidate.parents:
            raise DatasetError("SECURITY_BLOCKED", "Unsafe dataset path", 403)
        return candidate
