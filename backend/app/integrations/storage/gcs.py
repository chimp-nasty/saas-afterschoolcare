from datetime import timedelta

import google.auth
from google.api_core.exceptions import GoogleAPIError, NotFound
from google.auth.credentials import Signing
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.cloud import storage

from app.errors.storage import StorageProviderError
from app.integrations.storage.base import SignedUpload, StorageProvider, StoredObject


class GcsStorage(StorageProvider):
    """
    Google Cloud Storage, with Application Default Credentials:

    * Cloud Run: the service's own service account. It has no private key,
      so URLs are signed through the IAM API instead, which needs
      roles/iam.serviceAccountTokenCreator on itself.
    * Locally: `gcloud auth application-default login
      --impersonate-service-account=<that account>`, which signs the same way.
    """

    name = "gcs"

    def __init__(self):
        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        self._credentials = credentials
        self._client = storage.Client(credentials=credentials, project=project)

    def create_upload(self, *, bucket, key, content_type, max_size_bytes, metadata, expires_in):
        try:
            policy = self._client.generate_signed_post_policy_v4(
                bucket_name=bucket,
                blob_name=key,
                expiration=expires_in,
                conditions=[["content-length-range", 1, max_size_bytes]],
                # Each field is also a policy condition, so the browser
                # can't change them.
                fields={
                    "Content-Type": content_type,
                    **{f"x-goog-meta-{name}": value for name, value in metadata.items()},
                },
                **self._signing(),
            )
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs create_upload: {exc}") from exc

        return SignedUpload(url=policy["url"], fields=policy["fields"])

    def get_object(self, *, bucket, key):
        try:
            blob = self._client.bucket(bucket).get_blob(key)
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs get_object: {exc}") from exc

        if blob is None:
            return None

        return StoredObject(size_bytes=blob.size, content_type=blob.content_type)

    def read_start(self, *, bucket, key, length):
        try:
            return self._client.bucket(bucket).blob(key).download_as_bytes(start=0, end=length - 1)
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs read_start: {exc}") from exc

    def copy(self, *, bucket, source_key, target_key):
        source_bucket = self._client.bucket(bucket)

        try:
            # Small files: a single copy request; metadata comes along.
            source_bucket.copy_blob(source_bucket.blob(source_key), source_bucket, target_key)
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs copy: {exc}") from exc

    def delete(self, *, bucket, key):
        try:
            self._client.bucket(bucket).blob(key).delete()
        except NotFound:
            pass
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs delete: {exc}") from exc

    def create_download_url(self, *, bucket, key, content_type, content_disposition, expires_in):
        try:
            return self._client.bucket(bucket).blob(key).generate_signed_url(
                version="v4",
                method="GET",
                expiration=expires_in,
                response_type=content_type,
                response_disposition=content_disposition,
                **self._signing(),
            )
        except (GoogleAPIError, GoogleAuthError) as exc:
            raise StorageProviderError(log_reason=f"gcs create_download_url: {exc}") from exc

    def _signing(self) -> dict:
        """
        How to sign URLs. Credentials holding a key (or impersonating a
        service account) sign locally; Cloud Run's metadata credentials
        sign through IAM with the account's email and a fresh token.
        """
        if isinstance(self._credentials, Signing):
            return {}

        if not self._credentials.valid:
            self._credentials.refresh(Request())

        return {
            "service_account_email": self._credentials.service_account_email,
            "access_token": self._credentials.token,
        }
