import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.errors.storage import StorageProviderError
from app.integrations.storage.base import SignedUpload, StorageProvider, StoredObject


class S3Storage(StorageProvider):
    """
    Amazon S3, with credentials from the standard AWS chain (environment,
    shared config, or the workload's role). Signature V4, regional endpoint.
    """

    name = "s3"

    def __init__(self):
        # The regional endpoint: signed links to the global one redirect,
        # which breaks browser uploads.
        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=f"https://s3.{settings.S3_REGION}.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )

    def create_upload(self, *, bucket, key, content_type, max_size_bytes, metadata, expires_in):
        fields = {
            "Content-Type": content_type,
            **{f"x-amz-meta-{name}": value for name, value in metadata.items()},
        }

        try:
            post = self._client.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields=fields,
                # Unlike GCS, every field must be listed as a condition too.
                Conditions=[
                    ["content-length-range", 1, max_size_bytes],
                    *({name: value} for name, value in fields.items()),
                ],
                ExpiresIn=int(expires_in.total_seconds()),
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 create_upload: {exc}") from exc

        return SignedUpload(url=post["url"], fields=post["fields"])

    def get_object(self, *, bucket, key):
        try:
            head = self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None

            raise StorageProviderError(log_reason=f"s3 get_object: {exc}") from exc
        except BotoCoreError as exc:
            raise StorageProviderError(log_reason=f"s3 get_object: {exc}") from exc

        return StoredObject(size_bytes=head["ContentLength"], content_type=head.get("ContentType"))

    def read_start(self, *, bucket, key, length):
        try:
            response = self._client.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{length - 1}")
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 read_start: {exc}") from exc

    def copy(self, *, bucket, source_key, target_key):
        try:
            self._client.copy_object(
                Bucket=bucket,
                Key=target_key,
                CopySource={"Bucket": bucket, "Key": source_key},
                MetadataDirective="COPY",
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 copy: {exc}") from exc

    def write(self, *, bucket, key, content, content_type):
        try:
            self._client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 write: {exc}") from exc

    def delete(self, *, bucket, key):
        # S3 deletes are idempotent: a missing key isn't an error.
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 delete: {exc}") from exc

    def create_download_url(self, *, bucket, key, content_type, content_disposition, expires_in):
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentType": content_type,
                    "ResponseContentDisposition": content_disposition,
                },
                ExpiresIn=int(expires_in.total_seconds()),
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderError(log_reason=f"s3 create_download_url: {exc}") from exc
