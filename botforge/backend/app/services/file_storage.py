"""File storage abstraction layer.

Supports local filesystem (dev) and AWS S3 (production).
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

try:
    import aioboto3
    from botocore.exceptions import ClientError
except ImportError:
    aioboto3 = None  # type: ignore[assignment]
    ClientError = Exception  # type: ignore[assignment,misc]


class FileStorage(ABC):
    """Abstract base class for file storage backends"""

    @abstractmethod
    async def save(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        content: bytes | BinaryIO,
    ) -> str:
        """Save file to storage.

        Args:
            workspace_id: Workspace ID for organization
            document_id: Document ID for unique identification
            filename: Original filename
            content: File content (bytes or file-like object)

        Returns:
            Storage path/key for retrieval
        """
        ...

    @abstractmethod
    async def retrieve(self, storage_path: str) -> bytes:
        """Retrieve file from storage.

        Args:
            storage_path: Path/key returned from save()

        Returns:
            File content bytes
        """
        ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Delete file from storage.

        Args:
            storage_path: Path/key returned from save()
        """
        ...

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in storage.

        Args:
            storage_path: Path/key returned from save()

        Returns:
            True if file exists, False otherwise
        """
        ...


class LocalStorage(FileStorage):
    """Local filesystem storage for development"""

    def __init__(self, base_path: str = "uploads"):
        """Initialize local storage.

        Args:
            base_path: Base directory for file uploads
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        content: bytes | BinaryIO,
    ) -> str:
        """Save file to local filesystem."""
        # Create workspace directory
        workspace_dir = self.base_path / str(workspace_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Create document directory
        doc_dir = workspace_dir / str(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = doc_dir / filename

        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            with open(file_path, "wb") as f:
                f.write(content.read())

        # Return relative path for storage
        return str(file_path.relative_to(self.base_path))

    async def retrieve(self, storage_path: str) -> bytes:
        """Retrieve file from local filesystem."""
        file_path = self.base_path / storage_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")

        return file_path.read_bytes()

    async def delete(self, storage_path: str) -> None:
        """Delete file from local filesystem."""
        file_path = self.base_path / storage_path

        if file_path.exists():
            file_path.unlink()

            # Clean up empty directories
            try:
                file_path.parent.rmdir()  # Remove document dir if empty
                file_path.parent.parent.rmdir()  # Remove workspace dir if empty
            except OSError:
                # Directory not empty, that's fine
                pass

    async def exists(self, storage_path: str) -> bool:
        """Check if file exists in local filesystem."""
        file_path = self.base_path / storage_path
        return file_path.exists()


class S3Storage(FileStorage):
    """AWS S3 storage for production."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        use_instance_role: bool = True,
        access_key_id: str = "",
        secret_access_key: str = "",
    ):
        if aioboto3 is None:
            raise ImportError("aioboto3 is required for S3Storage: pip install aioboto3")
        self.bucket_name = bucket_name
        self.region = region
        self._session_kwargs: dict = {"region_name": region}
        if not use_instance_role and access_key_id:
            self._session_kwargs["aws_access_key_id"] = access_key_id
            self._session_kwargs["aws_secret_access_key"] = secret_access_key

    def _client(self):
        """Return an async S3 client context manager."""
        session = aioboto3.Session()
        return session.client("s3", **self._session_kwargs)

    async def save(
        self,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        content: bytes | BinaryIO,
    ) -> str:
        object_key = f"{workspace_id}/{document_id}/{filename}"
        body = content if isinstance(content, bytes) else content.read()
        async with self._client() as s3:
            await s3.put_object(Bucket=self.bucket_name, Key=object_key, Body=body)
        return object_key

    async def retrieve(self, storage_path: str) -> bytes:
        async with self._client() as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=storage_path)
            return await response["Body"].read()

    async def delete(self, storage_path: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=storage_path)

    async def exists(self, storage_path: str) -> bool:
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self.bucket_name, Key=storage_path)
                return True
            except ClientError:
                return False


def create_file_storage(
    storage_type: str = "local",
    base_path: str = "uploads",
    **kwargs,
) -> FileStorage:
    """Factory function to create file storage backend.

    Args:
        storage_type: 'local' or 's3'
        base_path: Base path for local storage
        **kwargs: Additional arguments for S3 (bucket_name, region, etc.)

    Returns:
        FileStorage implementation
    """
    if storage_type == "local":
        return LocalStorage(base_path=base_path)
    elif storage_type == "s3":
        return S3Storage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
