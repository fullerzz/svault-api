import logging
from pathlib import Path

import aioboto3
from icecream import ic
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig

from svault_api.models import S3Object, UserUploadFile

BUCKET_NAME: str = "fullerzz-media"  # TODO: Load from env
REGION: str = "us-west-1"
UPLOAD_DIR: Path = Path.cwd() / "svault_api/uploads"
logging_config = LoggingConfig(
    root={"level": logging.getLevelName(logging.INFO), "handlers": ["console"]},
    formatters={"standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
)
logger = logging_config.configure()()


async def write_tmp_file(user_file: UserUploadFile) -> str:
    path: Path = UPLOAD_DIR / user_file.filename
    logger.info(f"Writing tmp file to {path!s}")
    with path.open(mode="wb") as f:
        f.write(user_file.file_content)
    return f"{path!s}"


async def del_tmp_file(tmp_file_path: str) -> None:
    del_path: Path = Path(tmp_file_path)
    del_path.unlink()
    logger.info("Deleted tmp file")


class S3Client:
    def __init__(self) -> None:
        self.session = aioboto3.Session()

    async def upload(self, file: UserUploadFile) -> S3Object:
        logger.info(f"Uploading file to S3: {file.filename}")
        async with self.session.client("s3", region_name=REGION) as client:
            tmp_file_path: str = await write_tmp_file(file)
            key: str = file.filename
            try:
                await client.upload_file(
                    tmp_file_path,
                    BUCKET_NAME,
                    key,
                )
                logger.info("File successfully uploaded to S3")
            except Exception as ex:
                logger.exception(f"Error uploading file to S3: {file.filename}")
                raise HTTPException(detail=f"Error uploading file to S3 - {ex!r}") from ex
            finally:
                await del_tmp_file(tmp_file_path)
        return S3Object(
            bucket_name=BUCKET_NAME,
            key=key,
        )

    async def get_all_objects(self) -> list[S3Object]:
        objects: list[S3Object] = []
        async with self.session.client("s3", region_name=REGION) as client:
            try:
                paginator = client.get_paginator("list_objects_v2")
                page_iterator = paginator.paginate(Bucket=BUCKET_NAME)
                async for page in page_iterator:
                    for content in page["Contents"]:
                        ic(content)
                        objects.append(
                            S3Object(
                                bucket_name=BUCKET_NAME,
                                key=content["Key"],
                            )
                        )
            except Exception as ex:
                logger.exception("Error getting objects from S3")
                raise HTTPException(detail=f"Error getting objects from S3 - {ex!r}") from ex
        return objects
