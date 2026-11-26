from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
except ImportError:  # pragma: no cover - dependency is declared in project manifests
    boto3 = None
    Config = None
    BotoCoreError = ClientError = EndpointConnectionError = Exception


class MinioAdapter:
    """S3-compatible storage adapter with an explicit local fallback for demos."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_dir: str | None = None,
        mode: str | None = None,
    ):
        project_root = Path(__file__).resolve().parents[2]
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "minioadmin"))
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))
        self.region = os.getenv("MINIO_REGION", "us-east-1")
        self.base_dir = Path(base_dir) if base_dir else project_root / "app" / "minio_data"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.mode = (mode or os.getenv("MINIO_MODE", "auto")).lower()
        self._client = self._build_client() if self.mode in {"auto", "real"} else None

    def _build_client(self) -> Any:
        if boto3 is None:
            if self.mode == "real":
                raise RuntimeError("boto3 is required when MINIO_MODE=real")
            return None
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                connect_timeout=float(os.getenv("MINIO_CONNECT_TIMEOUT", "1.5")),
                read_timeout=float(os.getenv("MINIO_READ_TIMEOUT", "5")),
                retries={"max_attempts": 1, "mode": "standard"},
            ),
        )

    @property
    def is_real(self) -> bool:
        return self._client is not None

    def _fallback_buckets(self) -> list[str]:
        buckets = [child.name for child in sorted(self.base_dir.iterdir()) if child.is_dir()]
        if not buckets:
            for name in ["features", "quality-events", "evidence"]:
                (self.base_dir / name).mkdir(parents=True, exist_ok=True)
                buckets.append(name)
        return buckets

    def list_buckets(self) -> Dict[str, Any]:
        if self._client is not None:
            try:
                buckets = sorted(item["Name"] for item in self._client.list_buckets().get("Buckets", []))
                return {"endpoint": self.endpoint, "buckets": buckets, "status": "connected", "backend": "s3"}
            except (BotoCoreError, ClientError, EndpointConnectionError) as error:
                if self.mode == "real":
                    raise RuntimeError(f"Unable to connect to S3-compatible storage at {self.endpoint}: {error}") from error
        return {"endpoint": self.endpoint, "buckets": self._fallback_buckets(), "status": "simulated", "backend": "local"}

    def list_objects(self, bucket: str | None = None) -> Dict[str, Any]:
        storage = self.list_buckets()
        buckets = [bucket] if bucket else storage["buckets"]
        if storage["backend"] == "s3" and self._client is not None:
            objects = []
            for bucket_name in buckets:
                try:
                    paginator = self._client.get_paginator("list_objects_v2")
                    for page in paginator.paginate(Bucket=bucket_name):
                        for item in page.get("Contents", []):
                            objects.append(
                                {
                                    "bucket": bucket_name,
                                    "object_name": item["Key"],
                                    "size_bytes": item.get("Size", 0),
                                    "updated_at": item["LastModified"].isoformat(),
                                }
                            )
                except (BotoCoreError, ClientError) as error:
                    if self.mode == "real":
                        raise RuntimeError(f"Unable to list objects in bucket '{bucket_name}': {error}") from error
            return {"endpoint": self.endpoint, "bucket": bucket, "objects": objects, "status": "connected", "backend": "s3"}

        objects = []
        for bucket_name in buckets:
            bucket_path = self.base_dir / bucket_name
            if not bucket_path.exists():
                continue
            for path in sorted(item for item in bucket_path.rglob("*") if item.is_file()):
                objects.append(
                    {
                        "bucket": bucket_name,
                        "object_name": str(path.relative_to(bucket_path)).replace("\\", "/"),
                        "size_bytes": path.stat().st_size,
                        "updated_at": path.stat().st_mtime,
                    }
                )
        return {"endpoint": self.endpoint, "bucket": bucket, "objects": objects, "status": "simulated", "backend": "local"}

    def create_bucket(self, bucket_name: str) -> Dict[str, Any]:
        if self._client is not None:
            try:
                self._client.create_bucket(Bucket=bucket_name)
                return {"bucket": bucket_name, "status": "created", "backend": "s3"}
            except (BotoCoreError, ClientError) as error:
                if self.mode == "real":
                    raise RuntimeError(f"Unable to create bucket '{bucket_name}': {error}") from error
        bucket_path = self.base_dir / bucket_name
        bucket_path.mkdir(parents=True, exist_ok=True)
        return {"bucket": bucket_name, "path": str(bucket_path), "status": "created", "backend": "local"}

    def upload_file(self, bucket: str, file_path: str, target_name: str | None = None) -> Dict[str, Any]:
        source = Path(file_path)
        if not source.is_file():
            raise FileNotFoundError(f"Upload source does not exist: {source}")
        object_name = target_name or source.name
        if self._client is not None:
            try:
                self._client.upload_file(str(source), bucket, object_name)
                return {"bucket": bucket, "source": str(source), "object_name": object_name, "status": "uploaded", "backend": "s3"}
            except (BotoCoreError, ClientError) as error:
                if self.mode == "real":
                    raise RuntimeError(f"Unable to upload '{source}' to '{bucket}/{object_name}': {error}") from error
        target = self.base_dir / bucket / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return {"bucket": bucket, "source": str(source), "target": str(target), "object_name": object_name, "status": "uploaded", "backend": "local"}

    def download_file(self, bucket: str, object_name: str, destination: str) -> Dict[str, Any]:
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self._client is not None:
            try:
                self._client.download_file(bucket, object_name, str(dest))
                return {"bucket": bucket, "object_name": object_name, "destination": str(dest), "status": "downloaded", "backend": "s3"}
            except (BotoCoreError, ClientError) as error:
                if self.mode == "real":
                    raise RuntimeError(f"Unable to download '{bucket}/{object_name}': {error}") from error
        source = self.base_dir / bucket / object_name
        if not source.is_file():
            raise FileNotFoundError(f"Object does not exist: {bucket}/{object_name}")
        shutil.copyfile(source, dest)
        return {"bucket": bucket, "object_name": object_name, "destination": str(dest), "status": "downloaded", "backend": "local"}

    def simulate_uploads(self, files: list[tuple[str, str]]) -> list[Dict[str, Any]]:
        self.list_buckets()
        return [self.upload_file(bucket, local_path) for bucket, local_path in files]
