import sys
import traceback
from pathlib import Path

import aioboto3
from icecream import ic

from svault_api.models import S3Object, UserUploadFile

BUCKET_NAME: str = "fullerzz-media"  # TODO: Load from env
REGION: str = "us-west-1"
UPLOAD_DIR: Path = Path.cwd() / "svault_api/uploads"


async def write_tmp_file(user_file: UserUploadFile) -> str:
    path: Path = UPLOAD_DIR / user_file.filename
    ic(path)
    with path.open(mode="wb") as f:
        f.write(user_file.file_content)
    return f"{path!s}"


async def del_tmp_file(tmp_file_path: str) -> None:
    del_path: Path = Path(tmp_file_path)
    del_path.unlink()


class S3Client:
    def __init__(self) -> None:
        self.session = aioboto3.Session()

    async def upload(self, file: UserUploadFile) -> S3Object:
        async with self.session.client("s3", region_name=REGION) as client:
            tmp_file_path: str = await write_tmp_file(file)
            key: str = file.filename
            try:
                await client.upload_file(
                    tmp_file_path,
                    BUCKET_NAME,
                    key,
                )
            except Exception:  # TODO: Better exception handling
                _ex_type, _ex, tb = sys.exc_info()
                traceback.print_tb(tb)
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
            except Exception as ex:  # TODO: Better exception handling
                _ex_type, _ex, tb = sys.exc_info()
                traceback.print_tb(tb)
                print(repr(ex))
        return objects
