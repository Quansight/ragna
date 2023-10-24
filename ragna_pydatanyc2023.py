import os
import uuid
from typing import Any

from ragna.core import (
    Config,
    Document,
    EnvVarRequirement,
    PackageRequirement,
    RagnaException,
    Requirement,
)


class S3Document(Document):
    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [
            PackageRequirement("boto3"),
            EnvVarRequirement("AWS_ACCESS_KEY_ID"),
            EnvVarRequirement("AWS_SECRET_ACCESS_KEY"),
            EnvVarRequirement("AWS_REGION"),
            EnvVarRequirement("AWS_S3_BUCKET"),
        ]

    @classmethod
    def _session(cls):
        import boto3

        return boto3.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_REGION"],
        )

    @classmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        if not PackageRequirement("boto3").is_available():
            raise RagnaException()

        session = cls._session()
        s3 = session.client("s3")

        bucket = os.environ["AWS_S3_BUCKET"]
        response = s3.generate_presigned_post(
            Bucket=bucket,
            Key=str(id),
            ExpiresIn=config.api.upload_token_ttl,
        )

        url = response["url"]
        data = response["fields"]
        metadata = {"bucket": bucket}

        return url, data, metadata

    def is_readable(self) -> bool:
        session = self._session()
        s3 = session.resource("s3")

        import botocore.exceptions

        try:
            s3.Object(self.metadata["bucket"], str(self.id)).load()
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "404":
                return False

            raise RagnaException() from error

        return True

    def read(self) -> bytes:
        session = self._session()
        s3 = session.resource("s3")
        return s3.Object(self.metadata["bucket"], str(self.id)).get()["Body"].read()
